# Cron Health Audit — verified pattern (learned 2026-07-15)

When a PM bi-hourly or daily report suspects cron issues, this is the canonical verification recipe. Use it instead of guessing from `gh issue list` or `git log`.

## What it answers

1. Is the employee `LLM-side` actually running, or has the cron gone silent?
2. Is the `script wrapper` around the cron broken (Known Fix #13)?
3. Are there duplicate cron registrations (uppercase + lowercase)?
4. Is `last_status` in `jobs.json` lying (because the wrapper exits 1 even when the LLM ran fine)?

## Output structure to know

Each cron tick produces **two files** in `<profile_home>/cron/output/<job_id>/`:

| File | Size | Content |
|---|---|---|
| `YYYY-MM-DD_HH-MM-SS.md` (real run) | 15-50 KB | Full LLM prompt + response. Contains `## Response` section, even if response is `[SILENT]`. |
| `YYYY-MM-DD_HH-MM-SS.md` (status marker) | 150-200 bytes | Just the wrapper's exit-status block. Contains `Status: ok` / `silent (empty output)` / `script failed`. |

**The 1000-byte size threshold reliably separates them.** Marker files are always < 250 bytes; LLM runs are always > 5 KB (because the prompt includes the full SKILL.md).

## Verified audit snippet (Python, Windows-safe)

```python
from pathlib import Path
import datetime, json
from collections import Counter

base = Path("C:/Users/Administrator/AppData/Local/hermes/profiles")
SINCE = datetime.datetime.utcnow() - datetime.timedelta(hours=24)

def audit(profile_name, label):
    pdir = base / profile_name / "cron/output"
    files = [p for p in pdir.rglob("*.md")
             if datetime.datetime.fromtimestamp(p.stat().st_mtime) >= SINCE]
    counts = Counter()
    real_runs = 0
    for p in files:
        if p.stat().st_size < 1000:  # marker file
            txt = p.read_text(encoding='utf-8', errors='replace')
            if "script failed" in txt: counts["script failed"] += 1
            elif "silent (empty output)" in txt: counts["silent"] += 1
            elif "ok" in txt: counts["ok"] += 1
            else: counts["other"] += 1
        else:
            real_runs += 1
    print(f"{label}: markers={dict(counts)} real_runs={real_runs}")
    return counts, real_runs

audit("handsome_company_manager", "PM")
audit("handsome_company_developer", "DEV")
audit("handsome_company_reviewer", "REVIEWER")
```

## Interpretation

| Marker pattern | Real-run count | Diagnosis |
|---|---|---|
| All `ok` | Matches schedule × 24h | Healthy |
| All `silent` | Matches schedule × 24h | LLM running, no work to claim — healthy idle |
| All `script failed` | 0 | **Wrapper broken**, LLM never reached |
| Mixed `silent` + `script failed` | 0 | **Duplicate registration** (Known Fix #13): lowercase job did the LLM work, uppercase job's wrapper exited 1 |
| All `other` | 0 | Wrapper script not even producing status markers — check Gateway logs |

## Cross-check against jobs.json

`last_status` from `jobs.json` can lie if the wrapper exits 1. Always cross-reference:

```python
import json
for prof in ["handsome_company_manager", "handsome_company_developer", "handsome_company_reviewer"]:
    jj = base / prof / "cron/jobs.json"
    d = json.loads(jj.read_text(encoding='utf-8'))
    for j in d["jobs"]:
        print(f"[{prof:35}] {j['name']:40} script={j.get('script')} no_agent={j.get('no_agent')} last_status={j.get('last_status')}")
```

**Healthy profile:** all jobs `no_agent=False, script=None` with `last_status=ok` and matching marker counts.

**Duplicate-registration symptom:** you'll see BOTH `oneplusn-rev-task-polling` (lowercase, `script=None, last_status=ok`) AND `oneplusn-REVIEW-task-polling` (uppercase, `script=poll.sh, last_status=error`). Same prompt, same schedule, two registrations.

## Fix the duplicate

```bash
# Get the uppercase job IDs
python -c "import json; d=json.load(open(r'C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/jobs.json',encoding='utf-8')); \
  [print(j['id'], j['name']) for j in d['jobs'] if j['name'].isupper() or any(c.isupper() for c in j['name'].split('-')[1] if c)]"

# Remove each uppercase job (only the uppercase ones — keep lowercase as the real worker)
hermes cron rm <uppercase-job-id>
hermes cron rm <uppercase-job-id>
hermes cron rm <uppercase-job-id>

# Then restart the profile's Gateway so the new jobs list takes effect
powershell -NoProfile -Command "Stop-Process -Name hermes-gateway -Force"
powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'Hermes_Gateway_<profile>'"
```

## Why the script wrapper exits 1

The poll.sh that the uppercase REVIEW-* jobs invoke uses `set -e` plus `gh api /repos/...` (leading slash). MSYS rewrites that leading slash to a Windows filesystem path → command not found → script exits 1. The lowercase jobs don't have this problem because they invoke the LLM directly without the wrapper. Fix the wrapper itself by removing the leading slash from `gh api` calls (or adding `MSYS_NO_PATHCONV=1` — but the cleanest fix is to delete the uppercase jobs entirely since the lowercase ones are already doing the work).

## When to run this

- Every PM bi-hourly status report (see Operational Maintenance in SKILL.md)
- Before any "is the team working?" question from the boss
- After `oneplusn sync` to verify the regenerated registration didn't introduce duplicates
- After `hermes cron add` to verify no duplicate slipped in