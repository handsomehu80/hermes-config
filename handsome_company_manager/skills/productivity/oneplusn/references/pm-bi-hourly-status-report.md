---
name: pm-bi-hourly-status-report-cron-cadence-gap
description: "Pitfall: PM bihourly cron output dir shows multi-hour gap but jobs.json last_status=ok. Diagnose 'ghost ok' / scheduler-broken cadence. Load alongside pm-bi-hourly-status-report.md."
version: 1.0.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [pm-operations, cron-liveness, ghost-ok, scheduler-recovery]
---

# Pitfall: "Ghost OK" — Cron Jobs.json Lies About Liveness When Scheduler Is Broken

**Real case (PM #209, 2026-08-03 20:01 UTC).** Previous report was N=208 at 2026-08-04 02:01 UTC (UTC mtime = 2026-08-03 18:03). Next 8 scheduled fires (04:01, 06:01, 08:01, 10:01, 12:01, 14:01, 16:01, 18:01 UTC) all **missing** from the output dir. `jobs.json` for `pm-bihourly-status-report` reported `last_status=ok` throughout the gap. N=209 fired 7h+ late at 2026-08-03 20:01 UTC, breaking the 2h cadence.

## Symptom Cluster (all 3 must be true before you conclude "ghost ok")

1. `<profile_home>/cron/output/<job_id>/` shows a **gap > 1 normal interval** between consecutive `.md` files (use `Path.stat().st_mtime` — not filename — for gap calculation; filenames are CST, mtime is UTC).
2. `jobs.json` reports `last_status=ok` (and `last_run` is recent, OR is empty/null) for the affected job.
3. When the cron DOES eventually fire, the LLM produces a **healthy report** (canonical title, 6-section body, real GH data) — the LLM itself is fine, only the **scheduler is broken**.

## Distinguishing From Existing 4-State Classification

The current skill's §2.5 covers: healthy-idle / stale-verdict deadlock / boss-merge-PR deadlock / cron dead. **"Ghost OK" is a 5th state — between "healthy-idle" and "cron dead"**:

| State | Output dir activity | jobs.json | LLM quality | Severity |
|---|---|---|---|---|
| healthy-idle | every 2h | last_status=ok | healthy | 🟢 |
| **ghost-ok (NEW)** | **intermittent / spaced > 2× normal** | **last_status=ok (LIES)** | healthy when it fires | 🟡 |
| cron dead | no activity | last_status=error / None | n/a | 🔴 |
| stale-verdict / boss-merge deadlock | regular fires | last_status=ok | [SILENT] | depends |

## Detection Recipe (paste into `execute_code`)

```python
from pathlib import Path
import datetime, json

# 1) Find the bihourly output dir (filename pattern: <CST-timestamp>.md)
out_dir = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/d26c66fbbdd0")
files = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)

# 2) Walk back up to 8 most recent reports, compute gaps (in minutes, UTC)
now = datetime.datetime.now(datetime.timezone.utc)
gaps = []
prev_mt = None
for f in files[:8]:
    mt = datetime.datetime.fromtimestamp(f.stat().st_mtime, tz=datetime.timezone.utc)
    if prev_mt is not None:
        gap_min = (prev_mt - mt).total_seconds() / 60
        gaps.append((f.name, prev_mt.strftime('%H:%M UTC'), gap_min))
    prev_mt = mt

# 3) Flag if ANY gap > 2.5h (1.25× the normal 2h interval)
GHOST_THRESHOLD_MIN = 150
ghost_gaps = [(n, t, g) for (n, t, g) in gaps if g > GHOST_THRESHOLD_MIN]
print(f"Total reports scanned: {min(8, len(files))}")
print(f"Gaps > {GHOST_THRESHOLD_MIN} min: {len(ghost_gaps)}")
for n, t, g in ghost_gaps[:5]:
    print(f"  ⚠ {n} prev_mtime={t} gap={g:.0f}min ({g/60:.1f}h)")
```

## How to Recover

**Do NOT** wait for the cron to fix itself — `last_status=ok` lies will persist. Recovery sequence (verify from real production playbook, not theory):

1. **Confirm Gateway is alive**: `tasklist | grep -i hermes` should show the `hermes.exe` / `pythonw.exe` for this profile.
2. **Check gateway.log** for `Cron ticker started (interval=60s)` with a recent timestamp — if the last entry is > 1h old and there's no obvious restart, the ticker thread is wedged.
3. **Restart the Gateway**:
   ```powershell
   powershell -NoProfile -Command "Stop-Process -Name hermes-gateway -Force"
   # Re-trigger via Scheduled Task (don't manually start — Windows Task Scheduler will recreate with --replace mode)
   powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'Hermes_Gateway_<profile_name>'"
   ```
4. **Verify next fire**: wait one tick (60s), check `<profile_home>/cron/output/<job_id>/` for a new `.md` file.
5. **If restart didn't help**: check Windows Task Scheduler for the `Hermes_Gateway_<profile>` task — it may be in `Disabled` state or the `Last Run Result` may be non-zero.

## What to Put in the Report

When the current fire IS happening after a ghost-ok gap, emit:

```markdown
| **bi-hourly cron N 次未 fire ⚠** | 🟡 | 上一期 N=<X> 在 <ts>;此后 <scheduled-fire-count> 次预定 fire 全部缺失,jobs.json 显示 `last_status=ok` 但 output dir 真实中断 <gap-h>h。本期 = 漂移中断后**第一期**恢复 fire,需监控下次 <next-fire-ts> 是否如期 |
```

Do **NOT** count this as a real drift (#3 state "cron dead" would) — the LLM and prompt are healthy; only the scheduler is broken. Mark 🟡 (recovery is in flight), not 🔴.

## Why This Wasn't Caught Sooner (lesson for PM)

The skill's existing cron-liveness checks (4-state classification, size + heading-pattern, real-report-presence discriminator) all assume the cron **fires on schedule**. They verify what the LLM did during the last fire, not whether the last fire was timely. **Always pair the existing liveness checks with this gap-detection recipe** at the start of every PM bi-hourly report build. The first ~30 seconds of the recipe catches multi-hour scheduler breaks that would otherwise look "fine" for days.

## Origin

First observed: PM #209, 2026-08-03 20:01 UTC (N=208 at 2026-08-04 02:01 UTC → N=209 at 2026-08-03 20:01 UTC = 7h+ gap, 8 missing fires). Recovery path proven on the same fire (Gateway restart via PowerShell `Start-ScheduledTask`, verified next fire at 22:01 UTC was on schedule).
