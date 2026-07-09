---
name: multi-profile-team
description: "Set up and operate a multi-profile Hermes agent team — create role-differentiated profiles (PM, engineer, QA, assistant), wire them through the Kanban dispatcher, and run end-to-end multi-step work that survives restarts. Use when user asks for 'an agent team', 'PM + engineer team', 'multi-agent collaboration', or wants a persistent team structure rather than single-shot delegate_task work."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, profiles, kanban, team, orchestration, persistent-roles]
    related: [kanban-orchestrator, kanban-worker, hermes-agent, hermes-setup-audit]
---

# Multi-Profile Team

Class-level playbook for building and running a persistent team of Hermes agent profiles that collaborate via the Kanban dispatcher. Distinct from `delegate_task` (synchronous subagent, one-shot) and from tmux-spawned long-lived sessions (interactive only). This skill is the **team setup and operational pattern**; `kanban-orchestrator` covers what the orchestrator profile does; `kanban-worker` covers what each worker should know.

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
- Backup: copy `~/AppData/Local/hermes/profiles/` and `~/AppData/Local/hermes/kanban.db`
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
- `templates/4card-chain.sh` — script that creates the canonical 4-card T1→T2→T3→T4 chain
- `templates/pilot-first.sh` — script for skeleton+pilot-data→verify (used by case-study-knowledge-base)
- `templates/pm-soul.md` — starter SOUL.md for the PM orchestrator role
- `templates/eng-soul.md` — starter SOUL.md for the engineer role
- `templates/qa-soul.md` — starter SOUL.md for the QA reviewer role
- `templates/ast-soul.md` — starter SOUL.md for the assistant/researcher role
