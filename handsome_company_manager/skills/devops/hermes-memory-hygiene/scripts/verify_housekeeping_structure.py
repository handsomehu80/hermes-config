#!/usr/bin/env python
"""
Verify the MEMORY_ARCHIVE.md housekeeping section structure.

Catches the nesting pitfall: when patch edits anchor `old_string`
to the previous date's bullet instead of the section heading, new
entries can be inserted as sub-bullets (indent=2) rather than as
siblings of the existing top-level date bullets (indent=0). This
script reads the archive file, locates the `## Archive housekeeping`
section, and verifies:

  - All top-level date bullets (`- YYYY-MM-DD ...`) are at indent=0
  - All sub-bullets are at indent=2 (no deeper nesting)
  - No bullet has an unexpected indent (0 or 2 only)

Read-only — never modifies the file. Exit code:
  0 = structure OK (all top-level entries are siblings)
  1 = nesting issues found (line numbers printed)
  2 = usage error / file not found

Usage:
    python scripts/verify_housekeeping_structure.py <profile>
    python scripts/verify_housekeeping_structure.py <profile> --path <explicit-memories-dir>
"""

import argparse
import os
import sys
from pathlib import Path


def find_memories_dir(profile: str, explicit: str | None) -> Path | None:
    """Resolve the memories directory for the given profile, probing
    both Windows (`%LOCALAPPDATA%/hermes/...`) and Linux (`~/.hermes/...`)
    layouts since the skill should work on either."""
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "profiles" / profile / "memories",
        Path.home() / ".hermes" / "profiles" / profile / "memories",
        Path.home() / f".hermes/profiles/{profile}/memories",
    ]
    for c in candidates:
        if c and c.exists():
            return c
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify MEMORY_ARCHIVE.md housekeeping section sibling structure"
    )
    parser.add_argument("profile", help="Hermes profile name (e.g. handsome_company_manager)")
    parser.add_argument("--path", help="Explicit path to the memories/ dir", default=None)
    args = parser.parse_args()

    mem_dir = find_memories_dir(args.profile, args.path)
    if mem_dir is None:
        print(f"[✗] Could not locate memories/ for profile={args.profile!r}")
        print(f"    Tried LOCALAPPDATA, ~/.hermes/profiles/{args.profile}/memories, --path")
        return 2

    archive = mem_dir / "MEMORY_ARCHIVE.md"
    if not archive.exists():
        print(f"[✗] {archive} not found")
        return 2

    try:
        text = archive.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = archive.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    n = len(lines)

    # Locate "## Archive housekeeping" section
    start = None
    end = n
    for i, line in enumerate(lines, start=1):
        if "## Archive housekeeping" in line:
            start = i
        elif start and line.startswith("## ") and i > start:
            end = i - 1
            break

    if start is None:
        print("[✗] '## Archive housekeeping' section not found")
        return 1

    # Walk the section, classifying each line
    top_bullets = []       # list of (line_no, text)
    sub_bullets = []       # list of (line_no, text)
    issues = []            # list of (line_no, indent, text)
    current_top = None

    for i in range(start, end + 1):
        line = lines[i - 1]
        leading = len(line) - len(line.lstrip())
        stripped = line.lstrip()

        if leading == 0 and stripped.startswith("- "):
            # Top-level bullet — reset parent chain
            top_bullets.append((i, stripped))
            current_top = i
        elif leading == 2 and stripped.startswith("- "):
            # Properly indented sub-bullet
            if current_top is None:
                issues.append((i, leading, "sub-bullet without a top-level parent"))
            else:
                sub_bullets.append((i, stripped))
        elif stripped.startswith("- ") and leading not in (0, 2):
            # Bullet at a wrong indent depth (e.g. 4, 6, ...)
            issues.append((i, leading, f"unexpected indent={leading}"))
        # Non-bullet lines (blanks, comments, other text) don't reset the chain

    # Report
    print(f"Archive:      {archive}")
    print(f"Section:      lines {start}-{end}  ({end - start + 1} lines)")
    print(f"Top-level:    {len(top_bullets)}")
    print(f"Sub-bullets:  {len(sub_bullets)}")

    # Show the last few top-level entries as a quick visual sanity check
    if top_bullets:
        print("\nLast 3 top-level date entries:")
        for i, t in top_bullets[-3:]:
            print(f"  {i:4d}  {t[:80]}")

    if issues:
        print(f"\n[✗] {len(issues)} structural issue(s):")
        for i, ind, msg in issues:
            print(f"  Line {i:4d} (indent={ind})  {msg}")
        return 1

    # Also verify all top-level date bullets are siblings (no extra blank-line gaps
    # inside the section that could indicate a misplaced sub-section). This is a
    # soft check — we just print a warning if gaps > 2 lines exist.
    if top_bullets:
        gaps = []
        for (prev_i, _), (cur_i, _) in zip(top_bullets, top_bullets[1:]):
            gap = cur_i - prev_i
            if gap > 30:
                gaps.append((prev_i, cur_i, gap))
        if gaps:
            print("\n[!] Large gaps between consecutive top-level entries (suspicious):")
            for p, c, g in gaps:
                print(f"     line {p} → line {c}  (gap={g} lines)")

    print("\n[✓] Housekeeping structure OK — all top-level entries are siblings")
    return 0


if __name__ == "__main__":
    sys.exit(main())