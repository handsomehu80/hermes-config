#!/usr/bin/env python3
"""Build a SHA-256 diff between a fresh tarball-extracted tree (original)
and a sync_profile.py-produced staging tree, with the right normalizations:

  1. CRLF -> LF at hash time (Windows CRLF pitfall #8) so line-ending noise
     doesn't masquerade as content changes.
  2. Submodule path pre-filter (pitfall: 'Git submodules on remote cannot be
     written via Contents API') — we query the remote's recursive tree, find
     mode 160000 entries, and strip them from the diff entirely. The bundled
     push_via_contents_parallel.py does NOT auto-skip these; pre-filtering
     keeps the diff honest.
  3. PRESERVE_IN_REMOTE (currently just .gitignore) is excluded so the
     remote's own gitignore metadata never appears as a phantom change.

Output diff.json with the schema push_via_contents_parallel.py expects:
  {"new_paths": [...], "modified_paths": [...], "removed_paths": [...],
   "added": [...], "modified": [...], "removed": [...],
   "skipped_submodule": [...]}  # informational only

Usage:
    python build_clean_diff.py \\
      --repo handsomehu80/hermes-config \\
      --profile handsome_company_manager \\
      --original  /tmp/hermes-backup/hermes-config-original/<profile> \\
      --staging   /tmp/hermes-backup/hermes-config-staging/<profile> \\
      --out       /tmp/hermes-backup/diff.json

The --original dir MUST:
  1. Be freshly extracted from a current tarball (rm -rf + tar -xzf) —
     otherwise stale files from prior runs appear as spurious 'removed'
     entries. See SKILL.md "Stale extraction dir masks real deletions
     as spurious 404s" pitfall.
  2. Be PROFILE-SCOPED, i.e. point to the <profile>/ subdir of the
     tarball, NOT the whole-repo root. In multi-profile repos
     (handsome_company_manager + handsome_company_reviewer + ...) the
     tarball extracts every sibling profile; if --original is the root
     every sibling's files appear as phantom 'removed' entries.
     Fix: copy the profile subdir before diffing:
         cp -r /tmp/hermes-backup/original-<ts>/<profile> \\
               /tmp/hermes-backup/original-<profile>-only
         --original /tmp/hermes-backup/original-<profile>-only
     See SKILL.md "Scope --original to your profile subdir in multi-
     profile backup repos" pitfall.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

USER_AGENT = "hermes-config-backup-diff/1.0"
PRESERVE = {".gitignore"}


def sha_lf(p: Path) -> str:
    b = p.read_bytes()
    b = b.replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()


def walk(root: Path):
    for p in root.rglob("*"):
        if p.is_file():
            yield p.relative_to(root).as_posix()


def fetch_remote_submodule_paths(repo: str, branch: str, profile: str) -> set[str]:
    """Query /repos/<owner>/<repo>/git/trees/<branch>?recursive=1 and return
    the set of <profile>/... paths that are git submodule pointers
    (type='commit', mode='160000')."""
    out = subprocess.check_output(
        ["gh", "api", f"repos/{repo}/git/trees/{branch}?recursive=1"],
        text=True,
    )
    tree = json.loads(out).get("tree", [])
    return {
        e["path"].removeprefix(f"{profile}/")
        for e in tree
        if e.get("type") == "commit"
        and e["path"].startswith(f"{profile}/")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--profile", required=True, help="profile name (folder on remote)")
    ap.add_argument("--original", required=True, type=Path,
                    help="Freshly extracted remote tree (rm -rf first!). "
                         "MUST be profile-scoped (e.g. original-<ts>/<profile>/), "
                         "NOT the whole tarball root, in multi-profile repos.")
    ap.add_argument("--staging", required=True, type=Path,
                    help="sync_profile.py output (live profile -> staging)")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output diff.json path")
    ap.add_argument("--no-submodule-filter", action="store_true",
                    help="Skip remote submodule path detection (NOT recommended)")
    args = ap.parse_args()

    if not args.original.is_dir():
        print(f"ERROR: --original {args.original} is not a directory", file=sys.stderr)
        return 2
    if not args.staging.is_dir():
        print(f"ERROR: --staging {args.staging} is not a directory", file=sys.stderr)
        return 2

    print(f"Hashing original ({args.original})...")
    old_paths = {p: sha_lf(args.original / p) for p in walk(args.original)}
    print(f"Hashing staging ({args.staging})...")
    new_paths = {p: sha_lf(args.staging / p) for p in walk(args.staging)}

    # Submodule pre-filter
    if args.no_submodule_filter:
        submod = set()
        print("(submodule filter disabled)")
    else:
        try:
            submod = fetch_remote_submodule_paths(args.repo, args.branch, args.profile)
            print(f"Submodule subtrees under {args.profile}/: {sorted(submod)}")
        except Exception as e:
            print(f"WARN: could not fetch submodule paths from remote: {e}", file=sys.stderr)
            print("Proceeding without filter — review the diff for any paths", file=sys.stderr)
            print("under skills/.../scripts/ or similar git-submodule signatures.", file=sys.stderr)
            submod = set()

    def is_submodule_path(p: str) -> bool:
        return any(p == s or p.startswith(s + "/") for s in submod)

    def is_preserved(p: str) -> bool:
        return p in PRESERVE

    added = sorted(
        p for p in new_paths
        if p not in old_paths and not is_preserved(p) and not is_submodule_path(p)
    )
    removed = sorted(
        p for p in old_paths
        if p not in new_paths and not is_preserved(p) and not is_submodule_path(p)
    )
    modified = sorted(
        p for p in new_paths
        if p in old_paths
        and new_paths[p] != old_paths[p]
        and not is_preserved(p)
        and not is_submodule_path(p)
    )
    skipped_submodule = sorted(
        p for p in (set(new_paths) | set(old_paths))
        if is_submodule_path(p) and not is_preserved(p)
    )

    out = {
        # push_via_contents_parallel.py keys
        "new_paths": added,
        "modified_paths": modified,
        "removed_paths": removed,
        # natural / report-friendly aliases
        "added": added,
        "modified": modified,
        "removed": removed,
        "skipped_submodule": skipped_submodule,
    }
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"=== Diff ===")
    print(f"  added:    {len(added)}")
    print(f"  modified: {len(modified)}")
    print(f"  removed:  {len(removed)}")
    print(f"  skipped (submodule subtree): {len(skipped_submodule)}")
    print(f"  wrote {args.out}")

    # Sanity warn: if 'removed' is unexpectedly large, check the most likely
    # causes in priority order. Multi-profile scope is the #1 cause when the
    # tarball was freshly extracted and the remote contains sibling profiles.
    if len(removed) > 5 and not args.no_submodule_filter:
        # Try to bucket the removed entries by top-level dir to diagnose
        from collections import Counter
        topdirs = Counter(p.split("/", 1)[0] for p in removed).most_common(5)
        print()
        print("NOTE: 'removed' count is high. Common causes (check in order):")
        print("  1. MULTI-PROFILE SCOPE: --original is the WHOLE tarball root,")
        print("     not the profile-scoped subdir. Every sibling profile's files")
        print("     appear as 'removed'. Fix: cp -r <original>/<profile> <scoped>/")
        print("     then re-run with --original <scoped>. See SKILL.md 'Scope")
        print("     --original to your profile subdir in multi-profile backup")
        print("     repos' pitfall.")
        print("  2. STALE EXTRACTION: --original was not freshly extracted")
        print("     (rm -rf before tar -xzf). Stale files from prior runs")
        print("     appear as 'removed'. See SKILL.md 'Stale extraction dir")
        print("     masks real deletions' pitfall.")
        print()
        print("  Removed-entry top-level dirs (helps disambiguate):")
        for d, n in topdirs:
            print(f"    {d}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
