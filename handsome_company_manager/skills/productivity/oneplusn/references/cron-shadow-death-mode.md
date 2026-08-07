# Cron Shadow Death Mode — Beyond the "marker-emitting" states

A third failure mode for the uppercase-shadow duplicate cron registrations documented in the `oneplusn` SKILL.md (pitfall #13 / Known Fix #13). Complements the existing two states (`script failed` exit-1 markers, `silent (empty output)` exit-0 markers).

## Symptom (verified 2026-08-06, PM bi-hourly #245 run, reviewer profile)

Three reviewer `REVIEW-*` shadow dirs (`aeb3e3129882` task-polling, `923e1810fa5f` config-backup, `b3def0a867b1` memory-cleanup) had last-fired mtimes of **11475–11988 minutes ago (~8.0–8.3 days)** — **no recent marker files** at all, just historical `script failed` entries dated 2026-07-29 and earlier.

Meanwhile the lowercase `rev-*` counterparts in the **same** reviewer profile continued firing normally (task-polling 20-min age, config-backup 7.9h, memory-cleanup 6.9h). And the `DEV-*` shadow dirs in the developer profile **also kept firing** (0.1–6.9h ages). So the death mode is **profile-specific**, not universal.

## Why this is more confusing than marker-emission

When a shadow emits markers every cycle, `last_status=error` is at least fresh and dashboard alarms stay accurate. When a shadow DIES, `last_status` shows the LAST error from days ago — easy to mistake for "still firing but failing" — while the cron has been silent for a week. A health dashboard that trusts `last_status` will misclassify the death as a recent failure.

## Detection recipe

Run during the cron liveness walk (per `references/pm-bi-hourly-status-report.md` §2.5):

```python
from pathlib import Path
import datetime

profile_home = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/<name>/cron/output")
now = datetime.datetime.now(datetime.timezone.utc)

for d in profile_home.iterdir():
    if not d.is_dir():
        continue
    files = sorted(d.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        continue
    latest = files[0]
    age_hours = (now - datetime.datetime.fromtimestamp(latest.stat().st_mtime, tz=datetime.timezone.utc)).total_seconds() / 3600
    # Try to read the wrapper header for friendly name
    try:
        head = latest.read_text(encoding="utf-8", errors="replace")[:200]
        import re
        m = re.search(r"# Cron Job:\s*(\S+)", head)
        friendly = m.group(1) if m else "?"
    except Exception:
        friendly = "?"

    state = "HEALTHY" if age_hours < 2 else ("STALE" if age_hours < 24*7 else "DEAD")
    print(f"  {d.name[:12]}  {friendly:35s}  age={age_hours:6.1f}h  state={state}")
```

Classify:
- **age < 2h**: HEALTHY (fired on schedule)
- **2h ≤ age < 24×7h**: STALE (emitting markers, expected for shadow dirs)
- **age ≥ 24×7h = 168h**: **DEAD** — uppercase shadow that's stopped firing entirely

## Fix (same as marker-emission shadows)

```bash
hermes cron rm oneplusn-REVIEW-task-polling
hermes cron rm oneplusn-REVIEW-config-backup
hermes cron rm oneplusn-REVIEW-memory-cleanup
oneplusn sync --work-dir <team>
```

## Why might one profile die while another doesn't?

Hypotheses (unverified — needs debugging if it recurs):

1. **Different registration timing**: the reviewer REVIEW-* jobs may have been registered earlier and accumulated more consecutive failures before any check. Hermes cron may have a retry-cap that, when hit, stops scheduling.
2. **Profile-specific Hermes config**: the reviewer's `<profile_home>/config.yaml` may have stricter cron retry/backoff settings.
3. **Same script, different wrapper**: the `oneplusn-poll.sh` wrapper is shared across profiles, but the `script: true` + `no_agent: true` config in `jobs.json` is per-profile. If the reviewer's wrapper invocation has any subtle difference (e.g., a missing env var on the reviewer's `.env`), it may fail at a stage that the dev profile tolerates.

To investigate a new occurrence: diff the `jobs.json` entries for the dead shadow vs a healthy shadow of the same job type across profiles. Look for `script` path differences, `no_agent` flags, env vars, and command-line arg shape.

## Status

**Confirmed in production once (2026-08-06, PM #245)**. Not yet promoted into the main SKILL.md body because the file is already at the 100,000-character `skill_manage` patch limit. Should be folded into pitfall #13 during the next skill-split pass that breaks the SKILL.md into a smaller core + per-section reference files.