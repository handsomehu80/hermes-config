#!/usr/bin/env python3
"""Sync a Hermes profile directory into a backup repo working tree.

Mirrors durable profile files into REMOTE_PATH while honoring the canonical
.gitignore exclusions. Deletes entries in REMOTE that no longer exist in the
profile (so custom-skill removals propagate). Preserves REMOTE/.gitignore if
the profile doesn't have one (it's repo metadata, not user data).

Usage:
    export PROFILE_PATH="$USERPROFILE/AppData/Local/hermes/profiles/<name>"  # Windows
    export PROFILE_PATH="$HOME/.hermes/profiles/<name>"                       # Linux/macOS
    export REMOTE_PATH="/tmp/hermes-backup/hermes-config/<name>"
    python sync_profile.py

Cross-platform: uses pathlib + shutil (no rsync, no platform-specific shell).
Tested on Windows 10 Git Bash and Linux. Safe to re-run idempotently.
"""
from __future__ import annotations

import os
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

# Directories to skip entirely (canonical exclusions from the .gitignore convention)
EXCLUDE_DIRS = {
    'audio_cache', 'image_cache', 'cache', 'logs', 'sessions', 'plans',
    'workspace', 'gateway-service', 'home', 'pairing', 'weixin',
    'memory_sessions', '.git', '__pycache__',
    '.curator_backups', '.archive', '.hub', '.idea', '.vscode',
    'output',  # cron/output is per-job runtime output
}

# Files to skip entirely (exact match)
EXCLUDE_FILES = {
    '.env', 'auth.lock', 'gateway.lock', 'gateway.pid',
    'state.db', 'state.db-shm', 'state.db-wal',
    'models_dev_cache.json', 'gateway_state.json',
    '.skills_prompt_snapshot.json',
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
    '.usage.json', '.usage.json.lock', '.bundled_manifest',
    '.curator_state', '.tick.lock',
}

# Glob patterns (matched via fnmatch)
EXCLUDE_GLOBS = (
    '*.key', '*.pem', '*.p12', '*.pfx', '*.lock',
    '*.swp', '*.swo', '*~', '*.pyc', '*.cache',
    '.env', '.env.*', 'secrets.*',
)

# Never overwrite the remote's own .gitignore (repo metadata, not user data)
PRESERVE_IN_REMOTE = {'.gitignore'}


def is_excluded(name: str) -> bool:
    if name in EXCLUDE_DIRS or name in EXCLUDE_FILES:
        return True
    return any(fnmatch(name, pat) for pat in EXCLUDE_GLOBS)


def sync(src: Path, dst: Path) -> tuple[int, int, int]:
    """Recursively mirror src into dst with exclusions.

    Returns (files_copied, dirs_created, entries_removed).
    """
    src = Path(src)
    dst = Path(dst)
    if not src.is_dir():
        raise SystemExit(f'PROFILE_PATH does not exist or is not a directory: {src}')

    files_copied = dirs_created = removed = 0
    dst.mkdir(parents=True, exist_ok=True)

    # First pass: ensure allowed src entries exist in dst
    wanted: set[str] = set()
    for entry in src.iterdir():
        if is_excluded(entry.name):
            continue
        wanted.add(entry.name)
        src_p, dst_p = entry, dst / entry.name
        if entry.is_dir():
            dst_p.mkdir(parents=True, exist_ok=True)
            dirs_created += 1
            fc, dc, rm = sync(src_p, dst_p)
            files_copied += fc
            dirs_created += dc
            removed += rm
        else:
            shutil.copy2(src_p, dst_p)
            files_copied += 1

    # Second pass: remove dst entries that aren't wanted (deletions propagate)
    for entry in list(dst.iterdir()):
        if entry.name in PRESERVE_IN_REMOTE:
            continue
        if entry.name not in wanted:
            if entry.is_dir() and not any(entry.iterdir()):
                # Only remove empty dirs; non-empty dirs are likely intentional repo content
                entry.rmdir()
                removed += 1
            elif entry.is_dir():
                # Recurse to clean non-empty dirs of unwanted entries
                _, _, rm = sync(src, entry) if False else (0, 0, _prune_unwanted(entry, wanted))
                removed += rm
            else:
                entry.unlink()
                removed += 1

    return files_copied, dirs_created, removed


def _prune_unwanted(dst_dir: Path, sibling_wanted: set[str]) -> int:
    """Recursively remove anything in dst_dir whose name isn't in sibling_wanted."""
    removed = 0
    for entry in list(dst_dir.iterdir()):
        if entry.name not in sibling_wanted and entry.name not in PRESERVE_IN_REMOTE:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed += 1
    return removed


def main() -> int:
    profile = os.environ.get('PROFILE_PATH')
    remote = os.environ.get('REMOTE_PATH')
    if not profile or not remote:
        print('ERROR: Set PROFILE_PATH and REMOTE_PATH environment variables.', file=sys.stderr)
        print('Example (Windows):', file=sys.stderr)
        print('  set PROFILE_PATH=%USERPROFILE%\\AppData\\Local\\hermes\\profiles\\<name>', file=sys.stderr)
        print('  set REMOTE_PATH=C:\\path\\to\\repo\\<name>', file=sys.stderr)
        return 2

    src = Path(profile)
    dst = Path(remote)
    fc, dc, rm = sync(src, dst)
    print(f'Synced {src} -> {dst}')
    print(f'  files copied:   {fc}')
    print(f'  dirs created:   {dc}')
    print(f'  entries removed: {rm}')

    # Top-level summary for the cron report
    print('\n=== Top-level entries ===')
    for p in sorted(dst.iterdir()):
        if p.name in PRESERVE_IN_REMOTE:
            continue
        if p.is_dir():
            size = sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
            print(f'  {p.name + "/":<32} {size:>12,} bytes')
        else:
            print(f'  {p.name:<32} {p.stat().st_size:>12,} bytes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())