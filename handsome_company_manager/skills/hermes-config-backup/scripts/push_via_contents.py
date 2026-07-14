#!/usr/bin/env python3
"""Push a Hermes config backup via the GitHub Contents API (one commit per file).

This is the fallback path used when `git push` is blocked (e.g. github.com:443
firewalled) but `api.github.com` and `codeload.github.com` work. See
references/api-fallback-when-git-blocked.md in the parent skill for the
full reproduction recipe.

Usage:
  export GH_TOKEN=$(gh auth token)             # or rely on `gh auth token` call
  python push_via_contents.py \\
    --repo handsomehu80/hermes-config \\
    --synced-root C:/path/to/hermes-config-new/handsome_company_manager \\
    --diff C:/path/to/diff.json \\
    --branch main

Rate limit: ~3 sec/file via urllib. 114 files ≈ 5-6 min.
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
            txt = resp.read().decode("utf-8")
            return json.loads(txt) if txt.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code} {e.read().decode('utf-8', 'replace')}") from e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo, e.g. handsomehu80/hermes-config")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--synced-root", required=True, type=Path,
                    help="Path to the synced profile directory (the working tree)")
    ap.add_argument("--diff", required=True, type=Path,
                    help="Path to diff.json with 'new_paths' and 'modified_paths' lists")
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"),
                    help="Date string for the commit message (default: today)")
    args = ap.parse_args()

    diff = json.loads(args.diff.read_text())
    changes = diff["new_paths"] + diff["modified_paths"]
    if not changes:
        print("Nothing to commit.")
        return 0

    token = gh_token()
    profile_name = args.synced_root.name

    print(f"Repo: {args.repo}  Branch: {args.branch}")
    print(f"Will commit {len(changes)} files via Contents API "
          f"(+{len(diff['new_paths'])} new, ~{len(diff['modified_paths'])} modified)")

    success, failures = 0, []
    t0 = time.time()
    for i, rel in enumerate(changes, 1):
        # Always use forward slashes for the API path
        api_rel = rel.replace("\\", "/")
        api_path = f"{profile_name}/{api_rel}"
        local = args.synced_root / rel
        try:
            content = local.read_bytes()
        except Exception as e:
            failures.append((rel, f"read: {e}"))
            continue
        b64 = base64.b64encode(content).decode("ascii")
        body = {
            "message": f"backup: {api_path} (cron, {args.date})",
            "content": b64,
            "branch": args.branch,
        }
        # For modified files, fetch current SHA first
        try:
            meta = req("GET", f"/repos/{args.repo}/contents/{api_path}?ref={args.branch}", token)
            body["sha"] = meta["sha"]
        except RuntimeError as e:
            if "404" in str(e):
                pass  # new file
            else:
                failures.append((rel, f"sha-check: {str(e)[:200]}"))
                continue
        try:
            req("PUT", f"/repos/{args.repo}/contents/{api_path}", token, body)
            success += 1
        except RuntimeError as e:
            failures.append((rel, str(e)[:300]))
        if i % 10 == 0 or i == len(changes):
            elapsed = time.time() - t0
            print(f"  [{i}/{len(changes)}] {success} ok, {len(failures)} fail ({elapsed:.0f}s)")

    elapsed = time.time() - t0
    print()
    print(f"=== RESULT ===")
    print(f"Success: {success}/{len(changes)}   Failures: {len(failures)}   Elapsed: {elapsed:.1f}s")
    if failures:
        print("\nFailure details (first 20):")
        for rel, err in failures[:20]:
            print(f"  {rel}: {err}")
    # Persist a result manifest
    manifest = {
        "repo": args.repo,
        "branch": args.branch,
        "date": args.date,
        "success": success,
        "failures": failures,
        "elapsed_sec": round(elapsed, 1),
    }
    args.diff.with_name("contents_result.json").write_text(json.dumps(manifest, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
