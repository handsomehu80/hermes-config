#!/usr/bin/env python
"""
build_pool.py — merge exercises/by_concept/*.json into a single pool.json.

Usage:
    python build_pool.py [--root <kb_root>]

The KB root defaults to the parent directory of the script (../).
The script will:
1. Read every exercises/by_concept/*.json file
2. Verify id uniqueness
3. Sort by id (deterministic order)
4. Write exercises/pool.json as a single JSON array

If --check is passed, instead of writing, it just reports stats and exits
non-zero if any error.

Run after any fix to a by_concept file, before re-running the validator.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="KB root directory (default: parent of scripts/)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check; do not write pool.json",
    )
    args = parser.parse_args()

    root = Path(args.root)
    by_concept_dir = root / "exercises" / "by_concept"
    pool_path = root / "exercises" / "pool.json"

    if not by_concept_dir.exists():
        print(f"ERROR: {by_concept_dir} does not exist", file=sys.stderr)
        return 1

    files = sorted(by_concept_dir.glob("*.json"))
    if not files:
        print(f"ERROR: no .json files in {by_concept_dir}", file=sys.stderr)
        return 1

    pool = []
    seen_ids = {}
    errors = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  [JSON] {f.name}: {e}", file=sys.stderr)
            errors += 1
            continue

        ex_id = data.get("id")
        if not ex_id:
            print(f"  [ID]   {f.name}: missing 'id' field", file=sys.stderr)
            errors += 1
            continue
        if ex_id in seen_ids:
            print(
                f"  [DUP]  {f.name}: id '{ex_id}' also in {seen_ids[ex_id].name}",
                file=sys.stderr,
            )
            errors += 1
            continue
        seen_ids[ex_id] = f
        pool.append(data)

    pool.sort(key=lambda x: x.get("id", ""))

    print(f"Loaded {len(pool)} exercises from {len(files)} files")
    print(f"Errors: {errors}")

    # Per-field stats
    by_type = {}
    by_difficulty = {}
    by_grade = {}
    for ex in pool:
        by_type[ex.get("type", "?")] = by_type.get(ex.get("type", "?"), 0) + 1
        by_difficulty[ex.get("difficulty", "?")] = (
            by_difficulty.get(ex.get("difficulty", "?"), 0) + 1
        )
        by_grade[ex.get("grade", "?")] = by_grade.get(ex.get("grade", "?"), 0) + 1

    print(f"  by type       : {by_type}")
    print(f"  by difficulty : {by_difficulty}")
    print(f"  by grade      : {by_grade}")

    if errors:
        return 1

    if args.check:
        print("OK (--check, no write)")
        return 0

    pool_path.parent.mkdir(parents=True, exist_ok=True)
    pool_path.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {pool_path} ({pool_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
