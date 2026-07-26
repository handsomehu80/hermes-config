# Manual Cron Recovery — when the LLM has drifted for many days

When a cron LLM has drifted (per the "Cron LLM drift into skill-content regurgitation" pitfall in SKILL.md) for many days, **`hermes cron list` still shows `last_status=ok`** but no actual work happens. The cron is functionally dead. Don't wait for the next tick to fix itself — perform the work directly from `execute_code` or another session.

## When to use this recipe

- `cron/output/<job_id>/` has N files (where N matches expected tick count) but every file is 60-100 KB of verbatim SKILL.md content with no real response
- The latest file's text after the **last `## Response` marker** is empty / `[SILENT]` / "I cannot..." type drift
- `hermes cron list` shows `last_status=ok` (because the LLM did respond, just with garbage)
- `git log origin/main --grep '<backup-keyword>'` returns nothing (or much older than expected)

The exact case this doc was written for: `oneplusn-PM-config-backup` had drifted for **7 consecutive days** (12 cron output files, all 64-80 KB of SKILL.md regurgitation, no actual backup commits). `last_status=ok` made it look healthy. The drift was undetectable from `hermes cron list` alone — only a content-classifier check (file size + heading-pattern + real-report-presence) caught it.

## Recovery recipe (config-backup example)

The cleanest manual recovery for a config-backup cron: run the same `sync_profile.py` from `hermes-config-backup` skill, then push via the existing work-dir's git remote. Avoid the cron LLM entirely.

### Step 1 — Confirm drift (don't act on guess)

```python
from pathlib import Path
SKILL_HEADINGS = ["## Pitfall", "## Operational", "## Hard Constraints",
                  "## Known Fixes", "## Per-Agent", "## PM Mode"]
out = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output/<job-id>/")
files = sorted(out.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
for f in files[:5]:
    txt = f.read_text(encoding='utf-8')
    is_dump = len(txt) > 50_000 and sum(1 for h in SKILL_HEADINGS if h in txt) >= 2
    print(f"{f.name}: size={len(txt):>6}  skill_dump={is_dump}")
```

If `skill_dump=True` for **all** of the last 5 files, you've confirmed drift. Single-instance drift is normal (one bad tick); consecutive drift is the symptom you need to recover from.

### Step 2 — Mirror profile → staging

Use the canonical sync script from the `hermes-config-backup` skill. Don't write your own — `scripts/sync_profile.py` has the correct exclusion list and `.gitignore` preservation.

```python
import os, subprocess
from pathlib import Path

PROFILE  = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>")
STAGING  = Path(r"C:/Users/Administrator/AppData/Local/Temp/hermes-backup/hermes-config/<profile>")
SCRIPT   = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/skills/hermes-config-backup/scripts/sync_profile.py")

env = os.environ.copy()
env["PROFILE_PATH"] = str(PROFILE)
env["REMOTE_PATH"]  = str(STAGING)
env["PYTHONUNBUFFERED"] = "1"

r = subprocess.run(['python', '-u', str(SCRIPT)], env=env, capture_output=True, text=True)
# Expect: files copied: ~500-600, dirs created: ~190, no errors
```

Verify staging has no sensitive files leaked:

```python
for f in STAGING.rglob('*'):
    if not f.is_file(): continue
    name = f.name
    assert not (name == '.env' or name.startswith('.env.') or
                name in {'auth.json','auth.lock','gateway.lock','gateway.pid',
                         'state.db','gateway_state.json','processes.json',
                         '.hermes_history'}), f"LEAK: {f}"
```

### Step 3 — Sync staging → git-tracked work-dir mirror

This team uses `D:/onboarding/<team>/hermes-config/<profile>/` as the in-repo mirror of the staging dir. Two syncs in series keeps `git diff` clean.

```python
env["PROFILE_PATH"] = str(STAGING)
WORK_MIRROR = Path(r"D:/onboarding/<team>/hermes-config/<profile>")
env["REMOTE_PATH"] = str(WORK_MIRROR)
subprocess.run(['python', '-u', str(SCRIPT)], env=env, capture_output=True, text=True)
```

### Step 4 — Pre-commit hygiene checks

```python
import subprocess
WORK = Path(r"D:/onboarding/<team>")

# (a) Confirm we're on main, not someone else's feature branch
r = subprocess.run(['git','-C',str(WORK),'branch','--show-current'], capture_output=True, text=True)
assert r.stdout.strip() == 'main', f"on branch {r.stdout.strip()!r}, abort"

# (b) Confirm the diff is bounded to OUR subdir (CRLF noise from sibling profiles is a separate problem)
r = subprocess.run(['git','-C',str(WORK),'status','--porcelain'], capture_output=True, text=True)
lines = r.stdout.strip().split('\n')
top_dirs = {l.split()[1].split('/')[0] for l in lines if l.startswith((' M','??',' D')) and l.split()[1].startswith('hermes-config/')}
# top_dirs should be a subset of {'hermes-config'} (NOT include 'workspaces' / 'tmp' — those are other employees' WIP)
assert top_dirs <= {'hermes-config'}, f"non-hermes-config dirs in diff: {top_dirs}"

# (c) No sensitive files in staged content
r = subprocess.run(['git','-C',str(WORK),'diff','--cached','--name-only'], capture_output=True, text=True)
for path in r.stdout.strip().split('\n'):
    bn = path.split('/')[-1]
    assert not (bn == '.env' or bn.startswith('.env.') or bn in {'auth.json','state.db'}), f"FORBIDDEN STAGED: {path}"
```

### Step 5 — Set author + commit + push (with sibling-race recovery)

```python
from datetime import datetime
now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

# Author = PM identity (or whatever the cron prompt says your GH is)
subprocess.run(['git','-C',str(WORK),'config','user.name',  '<Your GH login>'])
subprocess.run(['git','-C',str(WORK),'config','user.email', '<id>+<login>@users.noreply.github.com'])

# Stage ONLY your subdir (never `git add .` in a shared repo — see hermes-config-backup pitfall)
subprocess.run(['git','-C',str(WORK),'add','hermes-config/<profile>/'])

# Commit with the same message pattern other employee backups use (don't invent a new one)
msg = f"chore: back up <profile> Hermes config ({now})"
subprocess.run(['git','-C',str(WORK),'commit','-m', msg], capture_output=True, text=True)

# Push — may need 1-2 retries due to github.com:443 firewall (Windows)
for attempt in range(3):
    r = subprocess.run(['git','-C',str(WORK),'push','origin','main'], capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        break
    if 'fetch first' in r.stderr:
        # Race: sibling cron pushed between our commit and our push. See hermes-config-backup
        # SKILL.md "Sibling force-push discarded your commit — reflog recovery" pitfall.
        lost = subprocess.run(['git','-C',str(WORK),'reflog'], capture_output=True, text=True).stdout
        # Find YOUR commit subject in reflog, then reset --hard to it and cherry-pick the sibling's tip
        # (full recipe in hermes-config-backup pitfall)
        ...
    time.sleep(2)
```

### Step 6 — Verify on remote

```python
import subprocess, json, os
r = subprocess.run(['gh','api','repos/<org>/<repo>/commits?per_page=3'], capture_output=True, text=True, env=os.environ.copy())
commits = json.loads(r.stdout)
for c in commits:
    msg = c['commit']['message'].splitlines()[0]
    print(f"  {c['sha'][:10]}  {c['commit']['author']['name']:<22}  {msg}")
# Your commit must be at the tip (sha[0]).
```

Then verify no `.env` leaked:

```python
r = subprocess.run(['gh','api','repos/<org>/<repo>/contents/hermes-config/<profile>/.env'], capture_output=True, text=True, env=os.environ.copy())
assert r.returncode != 0, "LEAK: .env is in remote!"
```

## What NOT to do

- **Don't edit the cron prompt and re-run the cron** hoping it'll behave next time. If it's drifted 7 days, one rewrite won't break the pattern — the structural cause (loaded-skill size dominating context) is still present. The cron needs the same prompt-rewrite + skill-trim from the drift pitfall's fix paths 1+2 before it'll stop drifting.
- **Don't `hermes cron rm` then `hermes cron add` as a "reset"**. The new registration will have the same drift pathology. Fix the prompt first.
- **Don't claim the backup "succeeded" based on `hermes cron list` alone**. Always verify via `gh api repos/<org>/<repo>/commits?per_page=1` (timestamp + author match) that the remote actually received a commit. `last_status=ok` proves the LLM ran; it does NOT prove the LLM produced useful work.
- **Don't run multiple manual backups in quick succession** to "catch up". One push of the current state is correct; redundant commits with the same content pollute history and may be rejected by GitHub's repeated-commit detection.

## Long-term: prevent the recurrence

Once the cron is fixed, add a weekly health check to the operational maintenance routine:

```python
# Run this every Monday. If skill_dump=True on any of the last 5 outputs,
# the drift has recurred — re-apply drift fix paths 1+2 and re-verify.
from pathlib import Path
SKILL_HEADINGS = ["## Pitfall", "## Operational", "## Hard Constraints",
                  "## Known Fixes", "## Per-Agent", "## PM Mode"]
for d in (Path.home() / "AppData/Local/hermes/profiles/<profile>/cron/output").iterdir():
    if not d.is_dir(): continue
    files = sorted(d.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
    drift_count = sum(
        1 for f in files
        if len(f.read_text(encoding='utf-8')) > 50_000
        and sum(1 for h in SKILL_HEADINGS if h in f.read_text(encoding='utf-8')) >= 2
    )
    if drift_count >= 3:
        print(f"⚠️  {d.name}: {drift_count}/5 recent files are skill dumps")
```

## See Also

- SKILL.md "Pitfall: Cron LLM drift into skill-content regurgitation" — root cause + detection recipe (where the 4 fix paths live, including this manual-recovery recipe as fix path 4)
- `references/cron-health-audit.md` — `scripts/check_pm_cron_liveness.py` for the response-classifier approach (size + heading + real-report-presence)
- `hermes-config-backup` SKILL.md — full backup recipe; this doc only covers the manual-recovery subset
- `hermes-config-backup` SKILL.md "Sibling force-push discarded your commit" pitfall — when the manual-recovery push collides with sibling crons