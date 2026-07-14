#!/usr/bin/env python3
"""Push a Hermes config backup via the Git Data API as a SINGLE atomic commit.

This is the path to use when you want one commit in the repo's history
(instead of N commits via the Contents API). **Caveat:** GitHub's tree
creation can fail with HTTP 422 `GitRPC::BadObjectState` when 100+ blobs
are created in tight succession. If that happens, fall back to
`push_via_contents.py` in the same scripts/ directory.

Usage:
  python push_via_git_data_api.py \\
    --repo handsomehu80/hermes-config \\
    --synced-root C:/path/to/hermes-config-new/handsome_company_manager \\
    --diff C:/path/to/diff.json \\
    --commit-message-file C:/path/to/msg.txt
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def gh_token() -> str:
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def req(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "hermes-config-backup/1.0",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(f"https://api.github.com{path}", data=data,
                               method=method, headers=headers)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code} {e.read().decode('utf-8', 'replace')}") from e


def create_blob(rel: str, local: Path, token: str, repo: str) -> dict:
    content = local.read_bytes()
    return req("POST", f"/repos/{repo}/git/blobs", token,
              {"content": base64.b64encode(content).decode("ascii"),
               "encoding": "base64"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--synced-root", required=True, type=Path)
    ap.add_argument("--diff", required=True, type=Path)
    ap.add_argument("--commit-message-file", required=True, type=Path)
    args = ap.parse_args()

    diff = json.loads(args.diff.read_text())
    changes = diff["new_paths"] + diff["modified_paths"]
    if not changes:
        print("Nothing to commit.")
        return 0

    token = gh_token()
    profile_name = args.synced_root.name
    message = args.commit_message_file.read_text(encoding="utf-8")

    print(f"Repo: {args.repo}  Branch: {args.branch}")
    print(f"Will commit {len(changes)} files in a SINGLE atomic commit")

    # 1. Get current main SHA
    ref = req("GET", f"/repos/{args.repo}/git/refs/heads/{args.branch}", token)
    current_sha = ref["object"]["sha"]
    print(f"  current SHA: {current_sha[:12]}")

    # 2. Get current tree
    commit = req("GET", f"/repos/{args.repo}/git/commits/{current_sha}", token)
    base_tree = commit["tree"]["sha"]
    print(f"  base tree:  {base_tree[:12]}")

    # 3. Create blobs
    print(f"  creating {len(changes)} blobs...")
    tree_entries = []
    t0 = time.time()
    for i, rel in enumerate(changes, 1):
        local = args.synced_root / rel
        try:
            blob = create_blob(rel, local, token, args.repo)
        except Exception as e:
            print(f"  [{i}/{len(changes)}] blob fail: {rel}: {e}")
            continue
        tree_entries.append({
            "path": f"{profile_name}/{rel.replace(chr(92), '/')}",
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })
        if i % 25 == 0 or i == len(changes):
            elapsed = time.time() - t0
            print(f"  [{i}/{len(changes)}] {len(tree_entries)} ok ({elapsed:.0f}s)")

    # 4. Create new tree (with fallback chunking on 422)
    print(f"  creating new tree with {len(tree_entries)} entries...")
    try:
        new_tree = req("POST", f"/repos/{args.repo}/git/trees", token,
                      {"base_tree": base_tree, "tree": tree_entries})
        new_tree_sha = new_tree["sha"]
    except RuntimeError as e:
        if "422" not in str(e):
            raise
        # Fallback: split into chunks
        print(f"  base_tree FAILED with 422; chunking at 30 entries...")
        prev_tree = base_tree
        chunk = 30
        for j in range(0, len(tree_entries), chunk):
            t = req("POST", f"/repos/{args.repo}/git/trees", token,
                   {"base_tree": prev_tree, "tree": tree_entries[j:j+chunk]})
            prev_tree = t["sha"]
            print(f"    chunk {j//chunk + 1}: -> {t['sha'][:12]}")
        new_tree_sha = prev_tree
    print(f"  new tree:   {new_tree_sha[:12]}")

    # 5. Create commit
    new_commit = req("POST", f"/repos/{args.repo}/git/commits", token,
                    {"message": message, "tree": new_tree_sha,
                     "parents": [current_sha]})
    new_commit_sha = new_commit["sha"]
    print(f"  new commit: {new_commit_sha[:12]}")

    # 6. Update ref
    req("PATCH", f"/repos/{args.repo}/git/refs/heads/{args.branch}", token,
        {"sha": new_commit_sha, "force": False})
    print(f"  done. main -> {new_commit_sha[:12]}")

    manifest = {
        "method": "git-data-api",
        "commit": new_commit_sha,
        "tree": new_tree_sha,
        "files_committed": len(tree_entries),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    args.diff.with_name("git_data_api_result.json").write_text(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
