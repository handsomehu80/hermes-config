---
name: multi-profile-team
description: "Class-level umbrella for multi-agent team operations on Hermes — three coordinated sub-patterns: (1) Set up persistent profiles (PM/eng/qa/ast) wired through the Kanban dispatcher for in-process team work, (2) PM workflow for GitHub-Issues-based 1+N digital-employee teams (allocate / track / synthesize), (3) Worker polling pattern with anchor-state short-circuit for cron-driven task intake. Use when user asks for 'an agent team', 'PM + engineer team', 'multi-agent collaboration', or any distributed-team orchestration that survives restarts."
version: 2.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, profiles, kanban, team, orchestration, persistent-roles, pm-workflow, worker-polling, cron-intake, github-issues, anchor-state]
    related: [kanban-orchestrator, kanban-worker, hermes-agent, hermes-setup-audit]
    absorbed_from: [pm-team-orchestration, agent-task-polling]
---

# Multi-Profile Team

Class-level umbrella for multi-agent team operations on Hermes. Three coordinated sub-patterns, each its own labeled section below:

1. **§ Setup Workflow** — persistent profiles wired through the Kanban dispatcher for in-process team work (the original `multi-profile-team` content)
2. **§ PM Workflow — GitHub-Issues Variant** — PM-side allocate/track/synthesize rules for distributed 1+N digital-employee teams (folded in from the now-archived `pm-team-orchestration` skill)
3. **§ Worker Polling Pattern** — anchor-state short-circuit for cron-driven task intake (folded in from the now-archived `agent-task-polling` skill)

Distinct from `delegate_task` (synchronous subagent, one-shot) and from tmux-spawned long-lived sessions (interactive only). For the orchestration-side playbook see `kanban-orchestrator`; for worker-side pitfalls see `kanban-worker`.

## When to Use

Load this skill when the user asks for:
- "Build me an agent team" / "set up a multi-agent team"
- "I want a PM + engineer + QA workflow"
- "Make Hermes collaborate with itself on bigger tasks"
- A specific 2-5 role roster (PM/engineer/QA/researcher, etc.)

Do NOT use this skill for:
- Single-task delegation → use `delegate_task`
- One-off parallel reasoning subtasks → use `delegate_task` batch mode
- An already-set-up team (just use `hermes -p pm` and talk) → no skill load needed
- Inspecting/auditing one profile's config → use `hermes-agent` skill

## The Architecture in One Picture

```
                          user
                           │
                           ▼
              ┌────────────────────────┐
              │  PM (orchestrator)     │
              │  profile: pm           │
              │  tools: kanban,clarify │
              └────────────┬───────────┘
                           │ kanban_create
                           ▼
              ┌────────────────────────┐
              │   Kanban Board         │
              │   (SQLite: kanban.db)  │
              │   dispatcher in gateway│
              └─┬───────┬───────────┬──┘
                │       │           │
        ┌───────▼─┐ ┌───▼────┐ ┌────▼─────┐
        │ engineer│ │  QA    │ │assistant │
        │profile: │ │profile:│ │ profile: │
        │ eng     │ │  qa    │ │  ast     │
        └─────────┘ └────────┘ └──────────┘
```

**Key design choices that matter:**

1. **Each role = one profile.** Profiles give you independent config, memory, model, and toolset. The "team" is the union of N profiles, not N processes that happen to share a config dir.
2. **Communication = Kanban cards, not direct messages.** SQLite-backed, survives restarts, has audit trail. No in-memory handshaking.
3. **Dispatcher spawns on demand.** The `kanban` dispatcher (embedded in the gateway, tick interval `kanban.dispatch_interval_seconds`, default 60s) reads `ready` cards and spawns `hermes -p <assignee> chat -q "<card body>"` as a fresh subprocess. Idle team = no extra processes. Busy team = ≤ `kanban.max_concurrent_workers` workers (default 3).
4. **PM is a router, not a worker.** PM's tools are kanban + clarify + todo — it does not have terminal/file/code_execution. If a card needs code, PM doesn't write it; PM creates a card assigned to eng. This is the single most important design rule.

## Setup Workflow (8 phases, ~30-45 min end-to-end)

Run these in order. Each phase verifies the previous before moving on.

### Phase 0 — Prereqs

Already covered by `hermes-setup-audit`:
- `hermes doctor` is clean (or only has intentional ⚠ items)
- At least one provider configured (a model the workers will use)
- A web search backend if any role will do research (Tavily/Exa/Firecrawl)
- `approvals.mode` set (smart recommended)

### Phase 1 — Create the profiles

For each role, run:
```bash
hermes profile create <name> --clone --description "<one-sentence role description>"
```

The `--description` is the kanban decomposer's first-pass hint for routing, so write it as a role description, not a name. Examples:
- pm: "Project manager: receives user requirements, decomposes into Kanban cards, routes to specialists, monitors progress, reports results"
- eng: "Software engineer: writes production code with TDD, implements features assigned via Kanban, hands off to QA"
- qa:  "Test engineer: writes test cases, runs test suites, validates engineer handoffs, creates bug-fix cards on failure"
- ast: "Assistant researcher: handles research, documentation, web lookups, and miscellaneous supporting work"

Verify: `hermes profile list` shows all created profiles alongside `default`.

### Phase 2 — Write SOUL.md for each profile

Each profile's `SOUL.md` lives at `~/AppData/Local/hermes/profiles/<name>/SOUL.md`. The persona content here is the "how this role behaves" — it's the difference between a worker that knows its job and one that drifts into adjacent roles.

What to include (use `references/soul-md-template.md` for a starter):
- Role statement (1 sentence)
- Workflow on receiving a card (orient → work → handoff)
- Iron rules (anti-temptation: what this role never does)
- Handoff conventions (when to `complete` vs `block`, metadata shape)
- Tools this role does NOT need (cross-reference the toolset config)

**Critical: encode the review-required handoff convention in eng's SOUL.md** — see the parent-link trap in `kanban-orchestrator` pitfalls. Pick one pattern (kanban_complete + comment marker, OR kanban_block + PM unblock) and bake it in. Don't leave it to the worker's interpretation.

### Phase 3 — Differentiate toolsets

PM should have the minimum surface area (kanban + clarify + todo + session_search). Engineers and QA need terminal/file/code_execution. Researcher needs web/browser. Differentiation reduces prompt noise and prevents role drift (PM can't accidentally try to use terminal because the tool isn't loaded).

```bash
# PM: drop everything except routing
hermes -p pm tools disable terminal file code_execution browser web image_gen video tts \
  delegation cronjob messaging vision homeassistant spotify computer_use x_search moa

# Engineer: keep code tools, drop web/browsing (research is ast's job)
hermes -p eng tools disable web browser image_gen video tts homeassistant spotify \
  x_search moa messaging delegation cronjob

# QA: code tools + browser (UI verification)
hermes -p qa tools disable web image_gen video tts homeassistant spotify x_search \
  moa messaging delegation cronjob

# Assistant: research-first, no terminal
hermes -p ast tools disable terminal tts homeassistant spotify x_search moa \
  messaging delegation cronjob vision image_gen video computer_use
```

**Toolset changes need a fresh session to take effect** (snapshot at prompt build time). Document this in the team's USAGE.md so users don't get confused by apparent "the disable didn't work" symptoms.

### Phase 4 — Initialize Kanban

```bash
hermes kanban init
hermes kanban boards    # confirm 1 default board
hermes config set kanban.dispatch_in_gateway true    # embed dispatcher in gateway
```

`kanban.dispatch_in_gateway: true` means the gateway's main thread ticks the dispatcher every 60s (configurable via `kanban.dispatch_interval_seconds`). Without this, you'd need a separate `hermes kanban daemon` process.

**Restart implication:** gateway-level config changes need a gateway restart. With `approvals.mode: smart`, the restart command is blocked as "stateful" — either approve manually, set `approvals.mode: off` for setup phases only, or run a separate daemon. The end-to-end validation in `references/case-study-mdlinkcheck.md` shows that some gateway reads (the dispatch interval) hot-reload, so test before assuming you need a restart.

### Phase 5 — Smoke test (1 card)

Don't go straight to a 4-card dependency chain. Validate the dispatch path with one trivial card:

```bash
hermes kanban create "smoke-test: respond with 'pong'" \
  --assignee ast \
  --body "Confirm the dispatch flow works end-to-end."
```

Wait one tick + worker startup (~60-90s). Then:
```bash
hermes kanban list                # should show the card as ✓ done
hermes kanban show <task_id>      # see the worker's summary "pong"
hermes kanban tail <task_id>      # see the run events (claim, spawn, heartbeat, complete)
```

If the card stays in `ready` for >2 minutes, the dispatcher isn't ticking. Check `kanban.dispatch_in_gateway` is true and that the gateway is running. The dispatcher reads config on gateway startup; some changes hot-reload, some don't. When in doubt, run an isolated `hermes kanban daemon --verbose` in a separate terminal to see tick logs.

### Phase 6 — Real workload (4-card dependency chain)

This is where you validate the full parent-link → auto-promote flow. A "build a small CLI tool" task exercises the most patterns: research (ast) → implement (eng) → test (qa) → report (pm). See `references/case-study-mdlinkcheck.md` for a fully worked example (mdlinkcheck CLI build, 54/54 tests passing, 99% coverage, ~37min end-to-end).

The canonical 4-card pattern:
```bash
T1=$(hermes kanban create "research: <topic>" --assignee ast --body "..." --json | jq -r .task_id)
T2=$(hermes kanban create "implement: <thing>" --assignee eng --parent $T1 --body "..." --json | jq -r .task_id)
T3=$(hermes kanban create "test: <thing>" --assignee qa --parent $T2 --body "..." --json | jq -r .task_id)
hermes kanban create "report: <thing>" --assignee pm --parent $T3 --body "Summarize T1-T3 for the user."
```

Verify after each tick:
- T1 ready → running → done
- T2 auto-promotes from todo → ready when T1 hits done
- T3 ditto on T2
- Final report card ditto on T3

If any card is stuck in `blocked` instead of flowing to `done`, the eng used `kanban_block(review-required)` on a parent-linked card (see kanban-orchestrator pitfall). Fix: edit eng's SOUL.md to use `kanban_complete` + comment marker, or PM runs `hermes kanban unblock <id>` and the worker re-spawns to complete.

### Phase 7 — Write the team manual

Save `~/AppData/Local/hermes/USAGE.md` (or copy `references/usage-template.md`):
- Team roster and what each profile does
- Common Kanban templates (the 4-card chain above is the most reused)
- Monitoring commands (`hermes kanban list`, `hermes kanban tail <id>`, `hermes kanban stats`)
- Known pitfalls and their workarounds
- Escalation path: who unblocks a stuck card

### Phase 8 — End-to-end validation

Run one more real task end-to-end with the manual in hand. If a user is going to operate this team, they need to see it work once with their own eyes. The 37-minute mdlinkcheck build is a good template; pick a task that:
- Has a researchable question (ast does real work)
- Has a non-trivial implementation (eng does real work)
- Has testable output (qa does real work)
- Is small enough to complete in one sitting

## Anti-Patterns to Avoid

- **Trying to be a "generalist" team with 1 profile.** Defeats the role separation. If a single profile can do everything, the team is theater. Differentiate aggressively.
- **Giving PM terminal/file/code_execution.** PM will then "just fix this quickly" and stop routing. The role separation is the discipline. If a card needs code, that's an eng card, period.
- **Worker pool where all 4 profiles are the same model.** At least ast (research) and pm (routing) can run on a cheaper/faster model. Override per profile with `hermes -p <name> model`.
- **Forgetting the dispatcher is a tick loop.** New cards wait up to 60s (default) before pickup. Either lower `kanban.dispatch_interval_seconds` to 15-30s for low-latency workflows, or accept the delay.
- **Treating unblock as the "fix everything" hammer.** Unblock re-spawns the worker. If the underlying problem is wrong model, wrong toolset, or wrong SOUL.md, unblock just spends another 150s. Fix the root cause.

## Common Footguns (CLI mistakes that cost real time)

These are all mistakes observed in real runs. Each one stalled a workflow for 5-30 minutes.

### Menu letter collisions when offering multi-phase choices

When offering the user a multi-choice menu for project phases or sub-tasks, ALWAYS label each option with the **full path**, not just a single letter. Example:

```
A. 阶段 B = 数学 3-6 扩节点
B. 阶段 C = 语文 + 英语
C. 题目库 (按现有数学 1-2 生成)
D. 收工
```

If you just write `A / B / C / D` with one-line descriptions, the user will mix your menu letters with the design doc's own phase letters (A/B/C/D/E) and produce ambiguous follow-ups like "完成C后开展A" that you have to guess at. Bake the full path into the menu label.

### Memory is per-profile (don't save cross-profile state to memory)

Each profile has its own `memories/` directory. Information stored via the `memory` tool from one profile is **not** visible to another. Cross-profile information belongs in `kanban_comment` threads on the relevant card, not in any single profile's memory. (E.g. the eng worker learning "we use pytest with xdist" should NOT save that to eng's memory if QA also needs it — save to the codebase `AGENTS.md` or a `kanban_comment` instead.)

### `--parent` with placeholder text
When you write `--parent t_待查询` (or any fake ID) thinking you'll fill it in later, the command **succeeds** with no parent link. The downstream auto-promote never fires and you find out 30 minutes later.
```bash
# BAD — succeeds silently, no parent link
hermes kanban create "..." --parent t_FILL_THIS_IN

# GOOD — capture the real parent ID first, in one go
T2=$(hermes kanban create "..." --json | jq -r .task_id)
hermes kanban create "..." --parent "$T2"   # always pass a real ID
```

### `--parent` followed by shell pipe
The shell will happily parse `--parent 2>&1 | tail -3` — argparse sees `--parent` with no value, the create succeeds, and you get neither the parent link nor the tail output. This is the silent-failure sibling of the footgun above.
```bash
# BAD — argparse drops --parent, the pipe captures nothing useful
hermes kanban create "..." --parent $T1 2>&1 | tail -3

# GOOD — capture full output, then format separately
hermes kanban create "..." --parent "$T1" 2>&1 | tee /tmp/kb.log | tail -3
```

### `kanban complete` after `kanban_block`
If a card was blocked, calling `kanban complete` on it is a state-machine error in some Hermes versions. Use `unblock` first, let the worker re-spawn and call `complete` itself. Or just edit the SOUL.md to never use `block` for parent-linked cards (the cleanest fix; see the mdlinkcheck case study).

### `kanban unblock` re-spawns the worker
This is **expected behavior**, not a bug. The unblocked worker re-reads the card body + comment thread and decides whether the work is already done (and calls `kanban_complete`) or whether there's more to do. Plan for the 100-200s respawn overhead; don't unblock repeatedly hoping for a different outcome.

### `execute_code` / browser / `sudo` blocked by smart approval
Workers (eng, qa, ast) run inside the dispatcher and inherit the gateway's `approvals.mode`. If a worker needs to run a Python script (e.g., the knowledge base's `validate_kb.py`) and the approval classifier blocks it, the worker has no user to ask. The worker will either (a) rewrite the work to avoid the blocked tool, or (b) write the script and ask the human to run it manually via comment.

For a team that needs to run scripts autonomously, set `approvals.mode: off` for the team profiles (`hermes -p eng config set approvals.mode off`) or `hermes -p <name> tools disable` the risky tools so workers don't try to use them. The cost is reduced safety on those profiles.

## PM Workflow — GitHub-Issues Variant

The Kanban dispatcher (§ Setup Workflow) is the in-process pattern. There is also a **GitHub-Issues-based variant** where the PM profile dispatches work via `gh issue create`, workers poll GitHub for new assignments, and comments serve as the audit trail. This pattern fits teams that span **multiple machines or operator identities**, where each worker has its own GitHub login and SOUL.md and polls a shared repo. Use it instead of the Kanban dispatcher when:

- The team is genuinely distributed (different repos, different operators)
- The user wants the audit trail and discussion visible in GitHub UI
- Workers have their own bot personas on GitHub (not just profiles in one install)
- Existing tooling (e.g. oneplusn) was designed for GitHub-Issues dispatch

The PM-side workflow rules are identical in spirit — allocate, track, synthesize, never do the worker's job — but the verbs change.

### PM Role — Hard Rules

The user's two explicit rules (verbatim):

> "你的责任是分配好工作,同时管理好任务的进展"
> "不要越俎代庖,谁的活谁干"

Operationalized:

- **Allocate** — pick the right role for each task. Match the *action verb in the task body* to the *verb the SOUL was written for*. A developer SOUL cannot do critical design thinking; a reviewer SOUL cannot write production code.
- **Track** — at every checkpoint, ask "is each in-flight issue making expected progress?" Do not assume silence = stuck. Do not assume activity = healthy. Use the verification methodology below.
- **Synthesize** — only AFTER all in-flight issues are closed. The boss reads one deliverable, not five.
- **Never** — write code on behalf of developer, audit on behalf of reviewer, or take over a worker task because "it's faster". The cost is real even if it's invisible (next worker will deprioritize, next worker will assume PM handles it, team memory of who-does-what degrades).

### Right-Person / Right-Task Matrix

| Task action verb | Right role | Anti-pattern |
|---|---|---|
| "research / audit / critique / scorecard" | reviewer (or research-analyst SOUL) | PM doing it themselves; developer "since they're already in the file" |
| "implement / build / PoC / run a real thing" | developer | reviewer (because they want a fresh angle); PM (because they want it done right) |
| "verify / validate PoC / cross-check prior work" | reviewer | developer (since they built it — bias); PM (combines both audit + impl bias) |
| "synthesize / cross-cut / decide / write final report" | PM | anyone doing it themselves before all upstream work is closed |

If a task genuinely doesn't fit any existing role, **ask the boss which role to create** — don't invent a worker or assign to a mismatched role.

### Issue Dispatch Pattern

For each worker task, the GitHub Issue body must include:

1. **Title** with prefix `[<priority>][<topic>][<role>]` so the worker can grep for their own work easily. Example: `[P2][Insight][Reviewer] 审计 3 份报告`.
2. **Body sections**: 背景 / 输入(参考文件 URL) / 任务 / 验收标准 / 6 铁规提示 / 期望响应时间. The "期望响应时间" matters — it bounds when the worker should self-escalate if blocked.
3. **Single assignee** (`gh issue create --assignee <github_username>`). PM creates the issue; the worker's cron poll picks it up.
4. **Labels**: PM owns labels. `type:research / type:feature / type:verification / type:docs` + `priority:P1/P2/P3` + `status:todo/in-progress/review/done/blocked`.
5. **For dependent tasks**: include `等 #<blocker_issue_num> close 后再开干` in the body, NOT a separate "blocker" Issue. Reviewers respect the rule and won't claim early.

For multiple parallel tasks, create them in one terminal batch (parallel `gh issue create` calls). Don't sequentially issue + wait + issue + wait — that's micro-management.

### The "Wait for Team Then Synthesize" Workflow

This is a **batch-completion pattern**, not a streaming pattern. The PM does NOT synthesize partial outputs. The PM waits for **all** in-flight issues to close, then delivers a single integrated deliverable to the boss.

```
PM dispatch N issues  ──→  workers do work in parallel  ──→  PM observes (silently)
                                                            ↓
                                                    any closed? → continue waiting
                                                    any blocked? → surface to boss
                                                            ↓
                                                    all closed?  ──→  PM synthesizes
                                                            ↓
                                                    boss gets ONE deliverable
```

What PM does NOT do during the wait:
- ❌ Nudge workers with comments ("how's it going?")
- ❌ Synthesize partial outputs ("here's a draft while we wait")
- ❌ Pre-write the final report ("I'm getting started on the structure")
- ❌ Add new issues mid-flight ("oh also can you...")

What PM DOES during the wait:
- ✅ Silent observation: read new comments when they arrive
- ✅ Track state in `todo`: which issues are in_progress / done / blocked
- ✅ On `status:blocked` label: surface to boss immediately with options

What PM does AFTER all close:
- Read every deliverable file
- Cross-reference outputs for consistency (do the reviewer's audit and dev's PoC agree?)
- Produce a single "boss can use this directly" artifact — usually a markdown report + index of supporting files
- Report back with: what was delivered, where it lives, what the boss should do next

### Quality Verification Methodology ("是不是有人在摸鱼")

The user explicitly asked: "你要仔细检查每个 issue 完成的质量,是不是有人在摸鱼". This is **not optional** — it is the PM's job at every checkpoint. Distinguishing "real progress" from "stuck" from "shirking" requires specific evidence beyond just reading comment counts.

The 6-source evidence checklist:

| Source | Where to look | What it tells you |
|---|---|---|
| 1. **GitHub Issue comments** | `gh api /repos/<org>/<repo>/issues/<n>/comments` | Whether the worker is communicating. Frequency of updates vs claim time. |
| 2. **Git commits on default branch** | `git log --all --since="<claim_time>" --author=<worker>` | Whether code is actually being written. Empty + claim > 1 hour = red flag. |
| 3. **Open PRs** | `gh pr list --state all --author <worker>` | Whether work is being surfaced for review. Empty + multi-hour claim = red flag. |
| 4. **Workspace files** | `ls -la <repo>/workspaces/issue-<N>/` (if used) | Per-task working directory; presence of source files = real work in progress. |
| 5. **Scratchpad state** (Ralph-style) | `<workspace>/.ralph/` directory | Engineered trace of what the worker attempted, evaluated, decided. |
| 6. **Smoke test output** | Run the test script directly | Last-mile verification that what was committed actually runs. |

### Priority misrouting vs shirking — the critical distinction

When a worker shows "claim 9 hours ago, 0 progress on Issue A, but workspace has commits on Issue B", do NOT immediately call it shirking. The likely diagnosis is one of:

| Symptom | Likely diagnosis | NOT |
|---|---|---|
| Workspace commits on Issue B, 0 on Issue A | **Priority misrouting** — worker self-prioritized, possibly defensibly (B might be lower-friction to start) | shirking |
| Workspace empty, last comment is the claim | **Stuck** — gateway issue, model issue, tooling blocker | shirking |
| Workspace commits but no PR / no GitHub comment update | **Communication gap** — work done, no surfacing. Possibly iron-rules violation | shirking |
| Claim comment + nothing for hours + config backup cron still firing | **Gateway desync** — gateway alive, polling firing, but the worker turn is broken | shirking |
| Multiple claim comments, no real work, no smoke tests | **Possibly shirking** — but first check if the claim comments are genuine (some debugging probes look identical to claims) | — |

**Always investigate before labeling.** Run the workspace `ls`, check git log, look at scratchpad files, THEN form a hypothesis. The wrong call ("you're shirking!") damages trust with a worker who might genuinely be stuck on a tooling issue.

When you find priority misrouting, do not seize the work. Surface to the boss with:
- Evidence (which workspace has commits, which doesn't)
- Diagnosis (priority misrouted, P1 skipped for P2)
- 2-3 options the boss can pick from (A: nudge worker; B: open a new diagnostic issue; C: re-route the work)

### PM Workspace Pattern (recommended)

For each developer task, expect (or create) a per-issue workspace:

```
<repo>/workspaces/issue-<N>/
├── .git/                     # git repo, branch `feat/issue-<N>-<topic>`
├── hello.sh + hello_test.sh  # smoke-test artifacts (created early)
├── poc/                      # PoC scripts
│   ├── ralph-loop.sh
│   ├── evaluator.sh
│   └── scratchpad-template.md
├── docs/                     # local docs (before merge)
├── tests/                    # local tests
└── .ralph/                   # scratchpad state (Ralph-style)
    ├── builder-prompt-*.md
    ├── evaluator-prompt.md
    ├── evaluator-diff.txt
    └── comment-*.md          # prepared comments NOT YET posted to GitHub
```

PM signal: presence of `workspaces/issue-<N>/` with a recent commit timestamp means the worker is in active development. Absence means either not started or already merged + cleaned up.

### GitHub-Issues Pitfalls

- **Acting on assumption that silence = shirking.** Always check the 6 evidence sources first. 9 hours of silence with a real workspace + real commits = priority misrouting, not shirking.
- **Adding new tasks mid-flight.** Once the batch is dispatched, do not issue new asks until the batch closes. Mid-flight additions cause worker context fragmentation and break the batch-completion pattern.
- **Trusting self-reports in comments.** A comment saying "I'll have this done in 2 ticks" is a forecast, not evidence. Cross-check with commits + workspace files before believing.
- **Issuing to wrong role.** A developer SOUL cannot do critical design thinking; a reviewer SOUL cannot write production code. If you find yourself thinking "I'll just have the developer audit this real quick" — stop, that's reviewer's job.
- **Skipping the verification step because the worker said "done".** Workers can claim completion prematurely (Anthropic paper: "Claude would mark features complete after superficial testing"). The verification methodology is the PM's last defense against this.
- **Trying to be the reviewer when reviewer is available.** If you have a reviewer employee and you start auditing a PoC yourself, you are doing reviewer's job.
- **Calling `gh` from MSYS-bash without `MSYS_NO_PATHCONV=1`** — see claude-package-to-hermes-skill pitfall #3 for the fix.
- **Modifying worker `.env` files in-place from terminal** — terminal can read them (sandbox-bypass) but should treat them as immutable from PM's perspective. If a worker lost their credential, the worker (or boss) recovers it; PM surfaces the issue but doesn't paste the new PAT themselves.

## Worker Polling Pattern (cron-driven task intake)

Each worker runs as a cron job that scans a queue for new feedback on its assigned work. The proven pattern is **anchor-state short-circuit**: track last-seen state per task, only do work on diff, suppress output when nothing changed.

### When to apply this pattern

- Cron fires every 15–60 min to scan a queue for new work
- Need to suppress notification when nothing has changed (cron delivery defaults to notify)
- Source system exposes a queryable API and supports state comparison (GitHub Issues, GitHub Notifications, etc.)

### Core: Anchor-State Short-Circuit

Capture a per-task anchor before doing any work:

- Identifier (URL / ID / queue position)
- `updated_at` / last-modified timestamp
- Comment count + last comment ID (or analogous "last activity" marker)
- Labels / status fields (sorted for stable comparison)
- Last event (actor, type, timestamp)

**Compare each field against the anchor:**
- All anchor fields match → output `[SILENT]` → no notification
- Any field differs → process the diff → structured report

This pattern has run 100+ consecutive polls successfully on a stable smoke-test fixture with no change, producing zero noise. The anchor can be sourced from the previous cron run's recorded output — no separate state file required for fixtures that genuinely don't drift. A starter template is in `templates/anchor-state.json`.

### GitHub Implementation

`gh issue list --assignee @me` **fails outside a git repo** ("fatal: not a git repository") and `gh search issues --assignee @me` returns empty for non-standard assignees (bot personas). Use REST `/issues?filter=assigned` instead — it works cross-repo with no git context.

```bash
# Cross-repo assigned issues (no git context required)
gh api '/issues?filter=assigned&state=open' \
  --jq '.[] | {number, title, updated_at, comments, html_url, repo: .repository_url}'

# Specific login via REST search
gh api 'https://api.github.com/search/issues?q=is:open+assignee:<login>' \
  --jq '.items[] | {number, title, updated_at, comments, html_url}'

# GraphQL alternative when REST returns empty
gh api graphql -f query='query {
  search(query: "is:open assignee:<login>", type: ISSUE, first: 50) {
    nodes { ... on Issue { number title updatedAt url
      repository { nameWithOwner }
      comments(first: 0) { totalCount } } }
  }
}'

# Per-issue deep state (REST)
gh api /repos/<owner>/<repo>/issues/<n>            # main fields + assignee
gh api /repos/<owner>/<repo>/issues/<n>/comments   # comment IDs + bodies
gh api /repos/<owner>/<repo>/issues/<n>/events     # label/reassignment/close events

# Notifications — separate channel for @mentions, review requests
gh api '/notifications' \
  --jq '[.[] | {id, reason, subject: .subject.title, updated_at, repository: .repository.full_name}]'
```

Full copy-pasteable reference in `references/github-polling-commands.md`.

### Assignee Identity Resolution

The session's GitHub login (e.g. `handsomehu80`) often differs from the bot persona recorded on issues (e.g. `Handsome-Manager`). The bot may post via the user's OAuth token without having its own GitHub login — `assignee:<session-login>` will miss it.

Resolution steps:
1. Get session login: `gh api /user --jq '.login'`
2. Get issue assignee(s): `gh api /repos/.../issues/<n> --jq '.assignee.login, .assignees[].login'`
3. If session login ≠ issue assignee, broaden the search:
   - `involves:<session-login>` (any participation: comments, mentions, labels)
   - Direct `<org>/<repo>` queries for known fixture repos
4. Cache the resolved identity in the anchor so subsequent polls don't re-resolve

### Decision Matrix

| Notifications | Anchor drift | Action |
|---------------|--------------|--------|
| empty | none | output `[SILENT]` |
| empty | yes | process the drift → structured report |
| non-empty | any | investigate each notification |
| empty | none, BUT last_verdict_age > Nh AND last_verdict_actor ≠ self | **stale-verdict deadlock** → ping once, do NOT `[SILENT]` |

### Output Format (cron delivery)

- Cron job delivery: reply text only — the runtime handles routing
- `[SILENT]` (exact string, nothing else) suppresses notification when nothing to report
- Drift detected: structured report including issue number, repo, URL, anchor→current diff, and recommended action

### Stale-Verdict Deadlock (Iron Rule #8 candidate)

When side A writes a verdict ("NEEDS_WORK — waiting on side B"), and side B's poll template classifies that verdict as "no new feedback from A since my last comment" → side B returns `[SILENT]`. Side A's next poll does the symmetric check. **Both sides `[SILENT]` forever** despite the cron firing every tick and the LLM executing every time.

The anchor-state short-circuit assumes "no drift = no work" — that's true for **inert** state but **wrong for asymmetric wait states** (one side IS waiting on the other, but the wait-signal doesn't look like a new comment from the polling side's perspective).

Diagnose by reading the LAST line of the latest `<profile_home>/cron/output/<job_id>/*.md` — if it ends with `[SILENT]` AND `cron output` is fresh AND there are open issues assigned to the polling agent → that's deadlock, not cron death.

Fix pattern: include `last_verdict_actor` + `last_verdict_age_hours` in the anchor; if age > N hours AND last verdict was the OTHER side → emit a ping ("this Issue is X hours stale, please confirm whether action is needed") instead of `[SILENT]`. Iron Rule #8 candidate: *stale-verdict ping* — every open Issue with no anchor drift AND >48h since last verdict must emit one ping per 24h, not silent. Full diagnostic recipe and reproduction commands in `references/stale-verdict-deadlock.md`.

### Worker Polling Anti-Patterns

- **Reporting "no issues found" every poll** → user gets spammed with noise
- **Recomputing the full diff each poll** instead of comparing to anchor → wasteful
- **Hard-coding the assignee login** → breaks when the bot persona or token rotates
- **Skipping the `events` endpoint** → misses label changes that don't bump `updated_at`
- **Skipping `/notifications`** → misses @mentions and review requests that don't appear in assigned issues
- **Loading anchor from a separate state file** when the previous cron output already records it → unnecessary I/O

### Worker Polling Pitfalls

- `gh issue list --assignee @me` errors with "fatal: not a git repository" outside a repo. Use REST.
- `assignee:@me` in GraphQL search may not match bot personas. Resolve the literal login first.
- `updated_at` does not change for label-only events on some issue types — always check events.
- REST `/issues?filter=assigned` may paginate silently — set `?per_page=100` and follow `Link: rel="next"` for large queues.
- `gh api graphql` exits non-zero on a successful query with warnings — don't conflate exit code with success when checking GraphQL output.

## Workflow Variants

The 4-card chain (T1 ast → T2 eng → T3 qa → T4 pm) is the canonical pattern, but real work needs variations.

### Pilot-first (skeleton + pilot data → verify)

When the work is **building infrastructure for future content** (a knowledge base, a schema, a CLI framework), run a small pilot before committing to the full scope:

```
A1 (eng)  build skeleton: schema, validate script, empty files
A2 (ast)  fill pilot data: 1 grade, 1 subject, ~30 nodes  ─┐  parallel
                                                          ├─→ A3 (qa) verify pilot
A1 complete ◄────────────────────────────────────────────┘
```

If the pilot fails QA, fix the schema (A1) before scaling up. If it passes, you can confidently dispatch the rest of the content in parallel batches. The pilot-first pattern saved a 6-grade × 3-subject knowledge base build from catastrophic rework — the second case study in `references/case-study-knowledge-base.md` documents this.

For the recipe, see `templates/pilot-first.sh`.

### Parallel research + synthesis (no implementation)

When the deliverable is a **design doc, comparison report, or decision memo**, not code, drop the implementation stage:

```
T1 (ast) research area A  ─┐
                           ├─→ T3 (ast or pm) synthesize findings + decision
T2 (ast) research area B  ─┘
```

T1 and T2 run in parallel (no parent link). T3 is parent-linked to both, so it stays in `todo` until both arrive. T3 reads the comments + artifacts and produces the synthesis. No eng, no qa — the artifact IS the deliverable.

## Operational Maintenance

Weekly:
- `hermes kanban stats` — throughput, by-assignee breakdown
- `hermes kanban list | tail -30` — recent activity
- Archive completed cards older than 30 days

Monthly:
- `hermes doctor` per profile if it diverges from default
- Backup: copy `~/AppData/Local/hermes/profiles/` and `~/AppData/Local/hermes/kanban.db`. For a versioned, portable backup of one profile's *configuration* (config.yaml, SOUL.md, skills/, memories/, cron/jobs.json) to a GitHub repo with sensitive files excluded, see `references/profile-backup-to-github.md`.
- Check `kanban.db` size — if >100MB, archive aggressively

## See Also

- `kanban-orchestrator` — the PM's decomposition playbook + parent-link trap pitfall
- `kanban-worker` — worker-side pitfalls including the review-required handoff trap
- `hermes-agent` — full CLI reference for `hermes profile`, `hermes kanban`, `hermes config`
- `hermes-setup-audit` — bring a fresh install to productive state (run before team setup)
- `references/case-study-mdlinkcheck.md` — full end-to-end run log with timings (CLI tool build, 4-card chain, 37 min)
- `references/case-study-knowledge-base.md` — design+Phase A run for a 1-6 grade curriculum KB; demonstrates pilot-first pattern + ast↔qa+eng parallel research → synthesis workflow
- `references/pitfalls-detailed.md` — extended pitfall transcripts (P1–P9) with full reproduction recipes and recovery steps (folded in from the now-archived `multi-agent-team-setup` skill)
- `references/kanban-commands.md` — condensed `hermes kanban` CLI reference (task creation, inspection, completion, recovery verbs)
- `references/soul-md-template.md` — starter SOUL.md structure for any new role
- `references/usage-template.md` — skeleton team manual to copy and adapt
- `references/soul-md-patterns.md` — narrative SOUL.md examples per role (PM/eng/qa/ast) folded in from the now-archived `agent-team-orchestration` skill
- `references/4-profile-recipe.md` — battle-tested 4-role split with toolset matrix and observed runtime budgets, folded in from the now-archived `agent-team-orchestration` skill
- `references/why-kanban-not-subagent.md` — design rationale: why persistent profiles + Kanban dispatch rather than `delegate_task` subagents for "team" work
- `references/profile-backup-to-github.md` — recipe for backing up a single profile's config (excluding `.env`, `state.db*`, caches, skill-curator metadata) to a GitHub repo, including cron-context pitfalls (no `rm -rf`, no `execute_code`) and Windows HOME-override gotcha
- `references/github-polling-commands.md` — copy-pasteable GitHub REST/GraphQL snippets for cron-driven worker polling (folded in from the now-archived `agent-task-polling` skill)
- `references/stale-verdict-deadlock.md` — full diagnostic recipe + Iron Rule #8 candidate: cron firing but both sides `[SILENT]` indefinitely (folded in from the now-archived `agent-task-polling` skill)
- `references/loop-engineering-roadmap.md` — the team's 90-day Loop Engineering evolution plan, distilled from PM insight work (folded in from the now-archived `pm-team-orchestration` skill)
- `templates/4card-chain.sh` — script that creates the canonical 4-card T1→T2→T3→T4 chain
- `templates/pilot-first.sh` — script for skeleton+pilot-data→verify (used by case-study-knowledge-base)
- `templates/anchor-state.json` — anchor-state template for worker polling pattern (folded in from the now-archived `agent-task-polling` skill)
- `templates/pm-soul.md` — starter SOUL.md for the PM orchestrator role
- `templates/eng-soul.md` — starter SOUL.md for the engineer role
- `templates/qa-soul.md` — starter SOUL.md for the QA reviewer role
- `templates/ast-soul.md` — starter SOUL.md for the assistant/researcher role
