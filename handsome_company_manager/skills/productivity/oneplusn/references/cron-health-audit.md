# Cron Health Audit — verified pattern (learned 2026-07-15)

When a PM bi-hourly or daily report suspects cron issues, this is the canonical verification recipe. Use it instead of guessing from `gh issue list` or `git log`.

## What it answers

1. Is the employee `LLM-side` actually running, or has the cron gone silent?
2. Is the `script wrapper` around the cron broken (Known Fix #13)?
3. Are there duplicate cron registrations (uppercase + lowercase)?
4. Is `last_status` in `jobs.json` lying (because the wrapper exits 1 even when the LLM ran fine)?

## Output structure to know

A scheduled minute can create outputs in **different job-ID directories** when duplicate registrations coexist: the lowercase prompt-driven job writes a large LLM envelope, while the uppercase `script`/`no_agent` shadow writes a tiny status marker. Do not assume that every logical tick produces two files in one directory.

| File class | Typical size | Content | What it proves |
|---|---:|---|---|
| LLM envelope | ≥5 KB (often 60–110 KB as skills grow) | Repeated prompt + final `## Response` payload | The LLM path ran; **not** that useful work occurred |
| Wrapper marker | 150–250 bytes (<1KB) | `Status: ok`, `silent (empty output)`, or `script failed` | Only the script wrapper's terminal status |

**The 1000-byte threshold reliably separates wrapper markers from LLM envelopes, but it does not classify productivity.** To classify the outcome, extract text after the **last** `## Response` marker and distinguish semantic `[SILENT]` from non-silent responses; then verify GH-side artifacts.

## Verified audit command (Windows-safe)

Use the maintained response-aware probe rather than reimplementing size heuristics:

```bash
python scripts/check_pm_cron_liveness.py --all --window-hours 24 --task-polling-only --json
```

For each job, inspect:

- `counts.marker` — wrapper markers (<1KB)
- `counts.real_llm` — LLM envelopes (liveness only)
- `counts.semantic_silent` — exact `[SILENT]`, legacy `[SILENT`, or explanatory response ending in `[SILENT]`
- `counts.non_silent` — responses that may represent work; still verify GitHub artifacts
- `counts.response_unparsed` — envelope lacked a parseable final response marker

The script also case-normalizes friendly names, maps `REVIEW → rev`, and separates uppercase shadows from lowercase workers.

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