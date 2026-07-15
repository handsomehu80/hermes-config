# Cron Tick Evidence Audit

Concrete commands for the 3-part audit on a self-NEEDS_WORK wait tick. The reviewer-cron-tips SKILL.md gives the WHY; this file gives the HOW. Captured 2026-07-14 across reviewer cron ticks at 22:13 / 22:42 / 23:13 on Issue #8.

## Why a 3-part audit (not just comments + updatedAt)

`gh issue view` only surfaces comments + updatedAt. The `updatedAt` timestamp bumps when the issue body, title, labels, assignees, milestones, or state changes — but **NOT** when project-board automation moves the issue, **NOT** when a cross-issue `referenced` event fires, **NOT** when a `mentioned` notifier fires. The events API is the only signal that catches these. Past ticks relying on comments-only have missed real activity; always run all 3 parts.

## Setup: env loading (mandatory, defeats token-redaction pitfall)

Hermes `terminal()` substitutes literal `***` for any token-shaped value when emitting bash commands (oneplusn Known Fix § Pitfall 3). **Always use `execute_code` with Python `subprocess.run(env=...)`** so the env dict passes through verbatim.

```python
import subprocess, os, json
from pathlib import Path

env_path = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_reviewer/.env")
env_vars = {}
for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_vars[k.strip()] = v.strip().strip('"').strip("'")

gh_token = env_vars.get("GITHUB_TOKEN") or env_vars.get("GH_TOKEN") or os.environ.get("GH_TOKEN", "")
gh_env = {**os.environ, **env_vars, "GH_TOKEN": gh_token}
```

**Sanity-check pre-flight** before trusting the rest of the audit:

```python
subprocess.run(["gh", "api", "user", "--jq", ".login"], env=gh_env, capture_output=True, text=True, timeout=30)
# must print "Handsome-Review" (NOT "handsomehu80" = boss OAuth fallback per Known Fix #11)
subprocess.run(["gh", "api", "repos/handsome-s-company/agent_workflow"], env=gh_env, capture_output=True, text=True, timeout=30)
# must exit 0; no leading slash on Windows git-bash (MSYS rewrites it)
```

## Part 1 — Comments + updatedAt (cheap path)

```python
result = subprocess.run(
    ["gh", "issue", "view", "8", "--repo", "handsome-s-company/agent_workflow",
     "--json", "number,title,state,updatedAt,comments,labels,assignees"],
    env=gh_env, capture_output=True, text=True, timeout=30,
)
iss = json.loads(result.stdout)
# iss['updatedAt'], len(iss['comments']), [a['login'] for a in iss['assignees']]
```

Output (Issue #8, 2026-07-14T23:13Z):
- `updatedAt=2026-07-13T15:30:38Z` (unchanged from verdict)
- `comments=2` (both Handsome-Review)
- `assignees=['Handsome-Review']`
- `labels=['type:verification', 'status:in-progress', 'priority:P1']`

## Part 2 — Full events audit

```python
result = subprocess.run(
    ["gh", "api", "repos/handsome-s-company/agent_workflow/issues/8/events"],
    env=gh_env, capture_output=True, text=True, timeout=30,
)
events = json.loads(result.stdout)

verdict_ts = "2026-07-13T15:30:38Z"
recent = [e for e in events if e['created_at'] > verdict_ts]
print(f"events since verdict: {len(recent)}")  # should be 0 in static state
```

What the events API catches that comments + updatedAt miss:

| Event type | Bumps updatedAt? | Adds comment? |
|---|---|---|
| `assigned` / `unassigned` | yes | no |
| `labeled` / `unlabeled` | yes | no |
| `milestoned` / `demilestoned` | yes | no |
| `closed` / `reopened` | yes | no |
| `renamed` / `edited` | yes | no |
| `referenced` (cross-issue mention) | **no** | **no** |
| `mentioned` (notifier event) | **no** | **no** |
| `added_to_project_v2` / `project_v2_item_status_changed` | **no** | **no** |

Last three rows are the gotchas — they're real activity (someone referenced or board-moved the issue) but invisible to the cheap path.

**Noise filter:** project_v2 events from `github-project-automation[bot]` fire on every status move and can drown the signal. Filter them out when checking for human activity:

```python
human_recent = [e for e in recent if not e['actor']['login'].endswith('[bot]')]
```

## Part 3 — Blockers-in-recent-commits check

```python
result = subprocess.run(
    ["gh", "api", "repos/handsome-s-company/agent_workflow/commits?sha=main&per_page=20"],
    env=gh_env, capture_output=True, text=True, timeout=30,
)
commits = json.loads(result.stdout)

recent = [c for c in commits if c['commit']['author']['date'] > verdict_ts]
# Inspect each commit's message for blocker-relevant terms
blocker_terms = ["tick_end.py", "BudgetMiddleware", "write_scratchpad", "run_tick_end", "WinError 206"]
hits = [c for c in recent if any(t in c['commit']['message'] for t in blocker_terms)]
print(f"recent commits touching blockers: {len(hits)}")  # should be 0
```

**Use `commit.author.date` (not `commit.committer.date`)** for the since-filter — author date is the actual creation time and is immutable; committer date can be rewritten by rebase and lies.

To be thorough, also fetch the files-changed for each recent commit and grep for blocker file paths:

```python
for c in recent[:10]:
    sha = c['sha']
    files_result = subprocess.run(
        ["gh", "api", f"repos/handsome-s-company/agent_workflow/commits/{sha}"],
        env=gh_env, capture_output=True, text=True, timeout=30,
    )
    files = json.loads(files_result.stdout).get('files', [])
    paths = [f['filename'] for f in files]
    relevant = [p for p in paths if any(t in p for t in blocker_terms)]
    if relevant:
        print(f"  {sha[:8]} {c['commit']['author']['date']} touches {relevant}")
```

This catches commits whose message doesn't mention the blocker but whose diff does (silent refactors, incidental file moves, etc.).

## Time math + threshold reasoning

```python
from datetime import datetime, timezone

verdict_ts = datetime(2026, 7, 13, 15, 30, 38, tzinfo=timezone.utc)
now_utc = datetime.now(timezone.utc)
elapsed = now_utc - verdict_ts
elapsed_h = elapsed.total_seconds() / 3600
threshold_met = elapsed.total_seconds() >= 86400
print(f"elapsed: {elapsed_h:.2f}h  24h threshold: {'MET' if threshold_met else f'NOT MET (need {24-elapsed_h:.2f}h more)'}")
```

## Decision matrix

| Audit result | Elapsed | Decision |
|---|---|---|
| All 3 silent (no comments / events / relevant commits) | < 24h | `[SILENT]`, breadcrumb flags "next tick to re-evaluate" |
| All 3 silent | 24h-25h (just crossed) | `[SILENT]` with "FIRST TICK PAST 24h" note, OR bump-comment per dispatcher cadence |
| All 3 silent | >= 25h | Strong case for bump-comment OR PM escalation per SKILL pitfall #6 |
| Wait condition MET (commits touch blockers, blockers closed, PM reassigned) | any | Process the issue |
| External activity (boss comment, label change, body edit) | any | Override self-wait, process |
| Dev commit touches BLOCKER files but no merge / no verification yet | any | `[SILENT]`, breadcrumb notes "dev started blocker fix, wait for merge + verification" |

## Pitfalls captured

1. **`commit.author.date` vs `commit.committer.date`.** Author is immutable creation time; committer can be rewritten by rebase. Use author for the since-filter.
2. **Project V2 events from automation bot.** Filter `actor.login` ending in `[bot]` to avoid noise from status moves.
3. **`updatedAt` is misleading on issues with project board automation.** A label change via project moves the status without bumping updatedAt. Always cross-check with the events API.
4. **`gh api .../commits?sha=main`** vs unprefixed. The `?sha=main` query param is required when the default branch isn't `main`; `gh api .../commits` alone 404s in that case. Observed on this repo which has `main` as default but the unprefixed form still failed at one point during this session.
5. **The events API is per-issue, not per-repo.** If your wait condition spans multiple issues, run the events check on each one separately.

## Breadcrumb template

Append a single line per tick to `<profile>/logs/poll-access.log`:

```
[YYYY-MM-DDTHH:MM:SS+08:00] cron tick — pre-flight OK (gh api user=Handsome-Review, repo=<org>/<repo>). 0 actionable (1 open assigned: #N [P?][...] <title>; comments=K (last-self verdict @ <verdict-ts>, ~X.Xh ago); updatedAt=<verdict-ts> (unchanged for X.Xh); events audit: zero new activity since verdict — no new comments, no label changes, no assignee changes, no body edits). My own NEEDS_WORK explicit wait-for-<who> still unmet. Recent commits since verdict: <sha> <author> @ <date> "<msg>", ... — none touch <blocker files>. Per polling heuristic self-NEEDS_WORK-with-explicit-wait: respect instruction, do NOT bump. [<X.Xh < 24h | 24h threshold JUST crossed>] [SILENT]
```

Keep each tick's breadcrumb to ~3-6 lines. Don't restate the threshold arithmetic if the previous tick already did — focus on what's NEW since prior tick.