# 4-Profile Team Recipe (pm / eng / qa / ast)

Battle-tested 4-role split for an "engineering + research" team. Validated end-to-end in June 2026 on a real coding task (mdlinkcheck CLI) and a real research task (China curriculum KB). Total 8-10 kanban cards, ~30-40 minutes wall time per cycle.

## Commands (run once, in order)

```bash
# 1. Create profiles (descriptions are read by the kanban decomposer)
hermes profile create pm  --clone --description "PM orchestrator: receives user requirements, decomposes into Kanban cards, routes to specialists, monitors progress, reports results"
hermes profile create eng --clone --description "Software engineer: writes production code with TDD, implements features assigned via Kanban, hands off to QA with structured metadata"
hermes profile create qa  --clone --description "Test engineer: writes test cases, runs test suites, validates engineer handoffs, creates bug-fix cards on failure"
hermes profile create ast --clone --description "Assistant researcher: handles research, documentation, web lookups, and miscellaneous supporting work for the team"

# 2. Initialize Kanban
hermes kanban init

# 3. Write SOUL.md for each (see soul-md-patterns.md in this skill)
# 4. Differentiate toolsets (see toolset-matrix section below)
# 5. Enable dispatcher
hermes config set kanban.dispatch_in_gateway true

# 6. Smoke test (1-2 minutes)
hermes kanban create "smoke-test: respond with 'pong'" --assignee ast --body "Just reply with the word 'pong' via kanban_complete."

# Wait 60-90s, then:
hermes kanban show <task_id>   # expect: status=done, summary contains 'pong'
```

## Toolset matrix (per profile)

| Profile | terminal | file | code_exec | browser | web | vision | tts | image_gen | delegate | cronjob |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| pm (orchestrator) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| eng (engineer) | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| qa (tester) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| ast (researcher) | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

Common to all: skills, todo, memory, session_search, clarify. Also common: homeassistant / spotify / x_search / moa / video / video_gen / yuanbao / homeassistant are all disabled (not relevant to engineering/research work).

Disable via:
```bash
hermes -p pm  tools disable terminal file code_execution browser web image_gen video tts delegation cronjob messaging vision homeassistant spotify computer_use x_search moa
hermes -p eng tools disable web browser image_gen video tts homeassistant spotify x_search moa messaging delegation cronjob
hermes -p qa  tools disable web image_gen video tts homeassistant spotify x_search moa messaging delegation cronjob
hermes -p ast tools disable terminal tts homeassistant spotify x_search moa messaging delegation cronjob vision image_gen video computer_use
```

Takes effect on next worker spawn (not mid-session).

## Worker runtime budgets (observed)

| Role | Typical card | Wall time | Notes |
|---|---|---|---|
| pm | Synthesis / report | 200-400s | Lightweight; mostly reads + writes text |
| ast | Research | 200-500s | Slow if web search is heavy |
| eng | Implementation (50-200 lines) | 600-1500s | Includes code generation + tests + self-review |
| eng | Block + re-spawn (review-required) | +100-200s | Wasted cycle; prefer kanban_complete |
| qa | Validate existing work | 300-600s | Reads a lot, writes little |

Total per 4-card pipeline: 30-50 minutes wall time (with dispatcher parallelism, eng and ast often overlap).

## Common dispatcher behavior

- Tick interval: 60s (configurable via `kanban.dispatch_interval_seconds`)
- Heartbeat: every 1 minute from running worker
- Failure limit: 2 consecutive crashes before auto-block
- Profile name typos: silently drop the card (always verify with `hermes profile list`)

## See also

- `soul-md-patterns.md` in this skill — full SOUL.md templates per role
- `why-kanban-not-subagent.md` in this skill — design rationale
