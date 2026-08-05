# Cron Output Dir Picker — Bihourly vs Task-Polling

> The `oneplusn` SKILL.md §5 #24 pitfall notes that `max by file count` is INVERTED for picking the bihourly output dir — task-polling fires every 30 min so it accumulates ~5× more files than the bihourly dir. `max(count)` reads a 64 KB `[SILENT]` polling response instead of the bi-hourly report. This file records the canonical correction.

## Option 1 (Recommended) — Friendly-name match via cron wrapper header

Every cron LLM output file opens with a header like:

```
# Cron Job: pm-bihourly-status-report
**Job ID:** d26c66fbbdd0
**Run Time:** 2026-08-04 12:09:34
**Schedule:** 0 */2 * * *
```

So the canonical recipe is: **read the first line of every file in `cron/output/`**, match the substring `pm-bihourly-status-report` (or whatever the friendly name is — `oneplusn-pm-task-polling`, `oneplusn-PM-config-backup`, etc.), and pick the dir whose files all carry that header. For the bihourly cron specifically, the file is `cron/output/d26c66fbbdd0/`.

```python
from pathlib import Path
out_root = Path.home() / "AppData/Local/hermes/profiles/handsome_company_manager/cron/output"
target_name = "pm-bihourly-status-report"
for d in out_root.iterdir():
    if not d.is_dir():
        continue
    files = sorted(d.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        continue
    head = files[0].read_text(encoding="utf-8", errors="replace").splitlines()[0]
    if target_name in head:
        bihourly_dir = d
        break
```

This is robust because (a) the cron wrapper's `# Cron Job: <name>` header is set by the wrapper at registration time, never drifts, and (b) the matching is content-based, not name-based, so UUID-named dirs are handled correctly.

## Option 2 — Size + heading discriminator

When the friendly-name header is unreliable (rare, but observed when the LLM rewrites the wrapper header), fall back to size + section heading:

- bihourly reports: 100–110 KB, contain `# 📊 PM 双小时状态报告 #N` + `## 0`–`## 6` or `## 7` sections
- task-polling: 15–95 KB (LLM-shaped), contain `[SILENT]` or `[ISSUE-N]`

Pick the dir whose files have the bihourly discriminator.

## Option 3 — Schedule frequency

Equivalent to "max by file count" but inverted: count files per dir, then divide by schedule frequency. Bihourly = 12 fires/day; task-polling = 48 fires/day. A bihourly dir has ~4× fewer files than a task-polling dir of the same age. Use this as a sanity check, not a primary selector.

## What NOT to do

- ❌ `max(dir.iterdir() for dir in dirs, key=len)` — picks the WRONG dir (~5× more files in task-polling).
- ❌ `min(by file count)` — picks the worker's quiet cron (maybe config-backup one-shots-per-day).
- ❌ `max(by mtime)` — both dirs have similar recent mtimes; doesn't actually disambiguate.

## PM #217 (2026-08-04) confirmation

The script `scripts/check_pm_cron_liveness.py` correctly maps to the bihourly dir via the cron wrapper's `Cron Job: pm-bihourly-status-report` header. The `d26c66fbbdd0` UUID is the canonical id; the wrapper header is the canonical friendly name. Verified on the 2026-08-04 20:09 CST run.

## Companion learned note (PM #217, 2026-08-04)

The `count_consecutive_zero_activity.py` script correctly handles the "healthy idle → traffic drop" transition for the same role. Earlier reports (N=210/N=209) marked reviewer as "🟢 healthy idle / 无新验证目标" — the script does NOT count those as zeros. When reviewer later hit 0 activity without the "healthy idle" prefix (N=211+), only the unclassified zeros accumulate. So a role's trailing_run reflects "real zero activity" history, not "always silent". Rule of thumb: when reading the script's trailing_run for a role that was previously "healthy idle", the number is the count of UNCLASSIFIED zeros after the last classified-zero row — manually scroll the §3 rows to confirm the classification breakpoint.
