# Memory Archive

> Archived by the 30-day cleanup cron. Active cutoff: any entry whose
> internal date is older than 30 days from "now" gets moved here.
> Re-survey / re-validate these notes before reusing them — the world
> may have moved on since the date on the line.
>
> Restoration rule: if a fact here is still true and useful, summarize
> the durable part back into MEMORY.md (drop the date). Do not just
> copy old entries back in — they were archived for a reason.
>
> Latest run: **2026-07-12** — no entries in MEMORY.md carried an
> internal date older than the 30-day cutoff (2026-06-12). Only
> dated entry in MEMORY.md is the 2026-07-08 `1+N 数字员工集成`
> note (4 days old) — kept in active memory. All other MEMORY.md
> entries are undated environment-state facts (host, model, API
> keys, agent team, user trust rule) and stay in place per the
> "no internal date → don't archive on mtime" rule. USER.md
> (mtime 2026-06-05) is left in place — it stores timeless
> user-profile facts (preferences, communication style), not
> dated operational memory, so the mtime-based rule does not
> apply. Hindsight `reflect()` attempted for advanced organization
> — same environmental failure as 2026-07-11 (cross-encoder
> HF Hub download + embedded PostgreSQL init), see housekeeping.

---

## 2026-06-03 — Toolset state snapshot

Web (Tavily) ✓ enabled, browser (agent-browser + Playwright Chromium)
✓ enabled, browser-cdp still ⚠, image_gen/video_gen ⚠ (need FAL_KEY),
x_search ⚠ (need XAI key), moa ⚠ (need OPENROUTER key), computer_use
enabled but macOS-only (won't work on this Windows host). All other
toolset gaps were by design at the time — require their own platform
credentials.

*Note for next survey*: toolsets evolve. Re-check each ⚠ with the
current `hermes tools` output before assuming the gap still exists.

---

## 2026-06-03 — Agent Team end-to-end validation

4-profile Agent Team (pm/eng/qa/ast) at
`~/AppData/Local/hermes/profiles/`. Kanban dispatcher embedded in
gateway (`kanban.dispatch_in_gateway=true`), 60s tick.

Validation artifact: `mdlinkcheck` CLI build — 37 min, 54/54 tests
pass, 99% coverage.

Manual location: `~/AppData/Local/hermes/USAGE.md`.

**Pitfall observed**: `eng` profile uses `kanban_block(review-required)`
which traps parent-linked QA tasks. PM must unblock manually, or fix
SOUL.md. Worth re-testing against current kanban worker code before
trusting this trick.

---

## Archive housekeeping

- Created: 2026-07-09 (cleanup cron).
- 2026-07-09 — moved 2026-06-03 entries (validation history + toolset snapshot).
- 2026-07-10 — no-op.
- 2026-07-11 — no-op (no 30+ day entries in MEMORY.md). Hindsight reflect attempted.
  - Hindsight daemon failed to start: `RuntimeError: Cannot send a request, as the client has been closed.` during `cross_encoder.initialize()` (HF Hub model download for the reranker step). Per skill guidance, this is environmental — not retryable in this cron. Falling back to markdown archive only.
  - Provider override applied successfully: `openai_compatible` (the invalid value in `~/.hermes/hindsight/config.json`) was overridden to `minimax` via `HINDSIGHT_API_LLM_PROVIDER` env var. The provider validation no longer fails — the daemon gets past LLM init before tripping on the cross-encoder download.
- Next scheduled cleanup: per the cron job cadence.
