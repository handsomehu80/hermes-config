---
name: cron-output-dir-picker
description: "Correct heuristic for picking the right cron output dir under <profile_home>/cron/output/ — fixes the §5 #24 'max by file count' bug in pm-bi-hourly-status-report.md where the task-polling dir (523 files, every 30min) is picked instead of the bi-hourly dir (109 files, every 2h)."
version: 1.0.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [pm-operations, cron-liveness, file-picking, bug-fix]
---

# Cron Output Dir Picker — Correct Heuristic

**This file documents a bug + fix in `pm-bi-hourly-status-report.md` §5 #24.**

The §5 #24 recipe for "Read the previous 2h report's §0/§5 BEFORE writing the new one" includes this line:

```python
# Pick the dir with the most .md files (the bihourly dir, not the polling dirs)
bihourly_dir = max((d for d in out.iterdir() if d.is_dir()), key=lambda d: len(list(d.glob("*.md"))))
```

**This heuristic is INVERTED** — it picks the WRONG dir. Discovered during PM bi-hourly report #111 on 2026-07-23.

## Why "max by file count" picks the wrong dir

The PM profile `handsome_company_manager` has 5 cron output dirs under `<profile_home>/cron/output/`:

| Friendly name | Schedule | Typical file count | File size mix |
|---|---|---|---|
| `oneplusn-PM-task-polling` (cef7e567ee17) | every 30 min (15/45 offset) | **523** | mostly shadow markers (~166B) + real LLM (~64KB) |
| `oneplusn-PM-config-backup` (74ebd0a04527) | daily 20:00 CST | 11 | all real LLM (~67KB) |
| `oneplusn-PM-memory-cleanup` (996743153888) | daily 21:00 CST | 10 | all real LLM (~67KB) |
| `pm-bihourly-status-report` (d26c66fbbdd0) | every 2h (offset 0) | **109** | all real LLM (~70KB) |
| `pm-daily-evening-report` (0cbfcf7b360e) | daily 15:00 CST | 10 | all real LLM (~72KB) |

The task-polling dir wins on file count by ~5x because it fires 4x/hour vs bihourly's 1x/2h. So `max by count` reads a 64KB `[SILENT]` polling response (not a bi-hourly report), and the staleness check silently fails.

## The correct heuristic (3 options, in preference order)

### Option 1 — Friendly-name match (most robust)

Read the first line of each dir's most recent `.md` (`# Cron Job: <friendly-name>`) and filter to the cron you're looking for. Robust across re-registration where the hash changes.

```python
from pathlib import Path

out = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output")
real_llm_dirs = []
for d in out.iterdir():
    if not d.is_dir():
        continue
    files = list(d.glob("*.md"))
    if not files:
        continue
    first_line = files[0].read_text(encoding="utf-8", errors="replace").splitlines()[0]
    real_llm_dirs.append((d, first_line.replace("# Cron Job: ", "")))
bihourly_dir = next(d for d, name in real_llm_dirs if "bihourly" in name.lower())
```

### Option 2 — Filter by max file size > 50KB

Real LLM outputs are 50-100KB. Shadow marker files are 166-200B. This excludes polling dirs that contain shadow markers.

```python
out = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output")
real_llm_dirs = []
for d in out.iterdir():
    if not d.is_dir():
        continue
    files = list(d.glob("*.md"))
    if not files:
        continue
    biggest = max(files, key=lambda f: f.stat().st_size)
    if biggest.stat().st_size > 50_000:
        first_line = files[0].read_text(encoding="utf-8", errors="replace").splitlines()[0]
        real_llm_dirs.append((d, first_line.replace("# Cron Job: ", "")))
# Either match friendly name or pick the dir with most consistent size
bihourly_dir = next(d for d, name in real_llm_dirs if "bihourly" in name.lower())
```

### Option 3 — Schedule pattern in mtimes

Bihourly dirs have files exactly 2h apart; polling dirs have files 30min apart. More expensive to compute but unambiguous.

```python
import statistics

def is_bihourly_cadence(d: Path) -> bool:
    files = sorted(d.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
    if len(files) < 3:
        return False
    deltas = []
    for i in range(len(files) - 1):
        deltas.append(files[i].stat().st_mtime - files[i+1].stat().st_mtime)
    median_delta = statistics.median(deltas)
    # 2h = 7200s ± 5 minutes
    return abs(median_delta - 7200) < 300
```

## When to use each

- **Default to Option 1** (friendly-name match). It's the most portable and doesn't depend on file size assumptions.
- **Use Option 2** when you have many crons and want to filter out shadow-marker dirs in bulk.
- **Use Option 3** only when friendly-name extraction is broken (e.g. header format changed).

## Verification

After picking the dir, always sanity-check by reading the latest file and confirming it matches expected content:

```python
reports = sorted(bihourly_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
latest = reports[0].read_text(encoding="utf-8")
# Should contain "## Response" + a substantial section (not just "[SILENT]")
assert "## Response" in latest, "Not a real LLM report"
assert len(latest) > 30_000, f"Report too small ({len(latest)}B) — picked the wrong dir?"
```

If `len(latest) < 30_000` (smaller than expected for a real PM bi-hourly report), you picked a polling dir. Re-pick with the friendly-name filter.

## See Also

- `pm-bi-hourly-status-report.md` §5 #24 — original recipe (buggy, see this file)
- `pm-bi-hourly-status-report.md` §2.8 — Cron output dir → friendly job name disambiguation
- `pm-bi-hourly-status-report.md` §2.12 — per-friendly-name liveness classifier (also uses size-based classification)
- SKILL.md "Known Fixes #13" — uppercase shadow cron duplicates explain the file-size bimodality