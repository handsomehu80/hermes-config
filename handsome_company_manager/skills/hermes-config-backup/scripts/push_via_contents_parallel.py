#!/usr/bin/env python3
"""Push a Hermes config backup via the GitHub Contents API, PARALLEL across parent dirs.

Why this exists: the bundled `push_via_contents.py` runs sequentially and
the Git Data API variant (`push_via_git_data_api.py`) chunks out at 60+
entries with an unfixable `tree.path contains a malformed path component`
422. For >30 files you want both speed AND reliability — that's this
script.

Design:
  - Group files by parent directory.
  - Submit ONE future per parent dir.
  - Inside each future, process files SEQUENTIALLY (avoids the
    Contents API "is at X but expected Y" 409 race that parallel siblings
    trigger when auto-creating a shared new directory).
  - Workers = N threads = N parent dirs in parallel.

The race is subtle: the Contents API auto-creates parent directories, and
a directory is just a tree object whose SHA changes with every successful
PUT inside it. Two workers both PUTing siblings in the same NEW dir see
each other's "is at" SHAs and one of them gets 409'd. The fix is to
serialize within each dir, parallelize across dirs.

Usage:
  python push_via_contents_parallel.py \\
    --repo handsomehu80/hermes-config \\
    --synced-root C:/path/to/profile \\
    --diff C:/path/to/diff.json \\
    --branch main \\
    --workers 4

Where `diff.json` is {"new_paths": [...], "modified_paths": [...]} with
forward-slash paths RELATIVE to `--synced-root`.

The repo <-> synced-root relationship: the script's `api_path` is built
as `<synced-root.name>/<rel>`, so `--synced-root` must be a directory
whose basename equals the profile folder name on the remote (e.g.
`handsome_company_manager`).

Verified working: 2026-07-14 PM backup, 158 files across 5 parent dirs,
~3 min wall time at 4 workers.
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
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

USER_AGENT = "hermes-config-backup-parallel/1.0"
DEFAULT_FAIL_LOG = "push_failures.log"


def gh_token() -> str:
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def req(method: str, path: str, token: str, body: dict | None = None,
        timeout: int = 30, max_retries: int = 3) -> dict:
    """Single API call. Retries 409/429/5xx with exponential backoff."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(f"https://api.github.com{path}", data=data,
                               method=method, headers=headers)
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                txt = resp.read().decode("utf-8")
                return json.loads(txt) if txt.strip() else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (409, 429, 500, 502, 503, 504):
                # transient — retry with backoff
                time.sleep(0.5 * (2 ** attempt))
                last_err = f"{e.code} {body}"
                continue
            raise RuntimeError(f"{method} {path} -> {e.code} {body}") from e
    raise RuntimeError(f"{method} {path} -> retry-exhausted last={last_err}")


def push_one(rel: str, local: Path, profile_name: str, repo: str,
             branch: str, token: str, date: str,
             fail_log: str | None = None) -> tuple[str, str]:
    """PUT one file via Contents API. Returns (rel, 'ok' | error_msg)."""
    api_path = f"{profile_name}/{rel.replace(chr(92), '/')}"
    try:
        content = local.read_bytes()
    except Exception as e:
        err = f"read: {e}"
        if fail_log:
            _log(fail_log, rel, err)
        return rel, err
    b64 = base64.b64encode(content).decode("ascii")
    body = {
        "message": f"backup: {api_path} (cron, {date})",
        "content": b64,
        "branch": branch,
    }
    # Modified files: fetch current SHA first (required by Contents API for updates)
    try:
        meta = req("GET", f"/repos/{repo}/contents/{api_path}?ref={branch}", token)
        body["sha"] = meta["sha"]
    except RuntimeError as e:
        if "404" in str(e):
            pass  # new file
        else:
            err = f"sha-check: {str(e)[:200]}"
            if fail_log:
                _log(fail_log, rel, err)
            return rel, err
    try:
        req("PUT", f"/repos/{repo}/contents/{api_path}", token, body)
        return rel, "ok"
    except RuntimeError as e:
        err = str(e)[:300]
        if fail_log:
            _log(fail_log, rel, err)
        return rel, err


def _log(fail_log: str, rel: str, err: str) -> None:
    with open(fail_log, "a", encoding="utf-8") as f:
        f.write(f"{rel}\t{err[:300]}\n")


def push_dir_sequential(parent_dir: str, files_in_dir: list[str],
                         profile_name: str, synced_root: Path,
                         repo: str, branch: str, token: str,
                         date: str, fail_log: str | None
                         ) -> list[tuple[str, str]]:
    """Process all files in ONE parent dir sequentially. The key to avoiding
    the 409 race: one dir = one thread = one writer = no concurrent auto-
    creates of the same parent dir."""
    results = []
    for rel in files_in_dir:
        local = synced_root / rel
        r, s = push_one(rel, local, profile_name, repo, branch, token, date, fail_log)
        results.append((r, s))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo, e.g. handsomehu80/hermes-config")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--synced-root", required=True, type=Path,
                    help="Path to the profile directory (basename = profile name on remote)")
    ap.add_argument("--diff", required=True, type=Path,
                    help="Path to diff.json with 'new_paths' and 'modified_paths' (forward-slash relative)")
    ap.add_argument("--workers", type=int, default=4,
                    help="ThreadPoolExecutor workers (= concurrent parent dirs). 4 is a safe default.")
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    ap.add_argument("--fail-log", default=DEFAULT_FAIL_LOG,
                    help="Path to per-failure log file (overwritten each run)")
    args = ap.parse_args()

    if args.fail_log:
        open(args.fail_log, "w", encoding="utf-8").close()

    diff = json.loads(args.diff.read_text())
    changes = diff["new_paths"] + diff["modified_paths"]
    if not changes:
        print("Nothing to commit.")
        return 0

    token = gh_token()
    profile_name = args.synced_root.name

    # Group by parent dir (use forward slashes consistently)
    by_dir: dict[str, list[str]] = defaultdict(list)
    for rel in changes:
        rel = rel.replace("\\", "/")
        parent = str(Path(rel).parent) if "/" in rel else "."
        by_dir[parent].append(rel)

    print(f"Repo: {args.repo}  Branch: {args.branch}  Workers: {args.workers}")
    print(f"Will commit {len(changes)} files in {len(by_dir)} parent dirs "
          f"(serial within dir, parallel across dirs)")
    top = sorted(by_dir.items(), key=lambda x: -len(x[1]))[:5]
    for d, fs in top:
        print(f"  {d}: {len(fs)} files")

    success = 0
    failures: list[tuple[str, str]] = []
    t0 = time.time()
    completed = 0
    total = len(changes)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(push_dir_sequential, d, fs, profile_name, args.synced_root,
                     args.repo, args.branch, token, args.date, args.fail_log): d
            for d, fs in by_dir.items()
        }
        for fut in as_completed(futures):
            d = futures[fut]
            results = fut.result()
            for rel, status in results:
                completed += 1
                if status == "ok":
                    success += 1
                else:
                    failures.append((rel, status))
            elapsed = time.time() - t0
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (total - completed) / rate if rate > 0 else 0
            print(f"  [{completed}/{total}] {success} ok, {len(failures)} fail "
                  f"({elapsed:.0f}s, {rate:.2f} f/s, ETA {eta:.0f}s)  [dir done: {d}]",
                  flush=True)

    elapsed = time.time() - t0
    print()
    print(f"=== RESULT ===")
    print(f"Success: {success}/{len(changes)}   Failures: {len(failures)}   Elapsed: {elapsed:.1f}s")
    if failures:
        print("\nFailure details (first 30):")
        for rel, err in failures[:30]:
            print(f"  {rel}: {err[:200]}")
    manifest = {
        "repo": args.repo,
        "branch": args.branch,
        "date": args.date,
        "success": success,
        "failures": failures,
        "elapsed_sec": round(elapsed, 1),
    }
    args.diff.with_name("contents_parallel_result.json").write_text(json.dumps(manifest, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
