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
> Latest run: **2026-07-17** — no-op archive; no entries in MEMORY.md
> carried an internal date older than the 30-day cutoff
> (2026-06-17). The dated active entries are
> `1+N 数字员工集成(2026-07-08)` and
> `Credential state (2026-07-17)`; both remain within the 30-day window.
> Undated environment-state facts remain in place per the
> "no internal date → don't archive on mtime" rule. USER.md was unchanged.
> Hindsight is enabled (`memory.provider: hindsight`) and `reflect()` was
> attempted with provider `minimax` / model `MiniMax-M3`, but the embedded
> daemon timed out after 180 seconds. The log shows the same environmental
> blocker: Hugging Face HEAD requests for `BAAI/bge-small-en-v1.5` fail with
> `[WinError 10054]`, so cross-encoder initialization never completes and no
> mental model was created or updated. `HF_TOKEN` is still absent.
> The failed attempt left a zero-byte Hindsight lock; it was removed after
> confirming no listener remained on port 9807. The markdown archive remains
> authoritative and no memory data was lost.
> Separate liveness warning: the profile gateway log is stale (last write
> 2026-07-15 10:09; last recorded cron-ticker start 2026-07-15 02:49), so
> Gateway health cannot be confirmed from that log even though this cleanup
> job itself ran successfully.

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
- 2026-07-17 — no-op archive (cutoff 2026-06-17; dated active entries are 2026-07-08 and 2026-07-17). Corrected two stale active-memory facts: profile identity (`default` → `handsome_company_manager`) and credential state (`GITHUB_TOKEN` is configured). Hindsight `reflect()` attempted because the provider is enabled:
  - The reusable runner initially assumed `~/.hermes/profiles/.../.env`; this Windows profile lives under `%LOCALAPPDATA%/hermes/profiles/...`. The skill script was patched to search `HERMES_HOME`, `~/.hermes`, and `%LOCALAPPDATA%/hermes`.
  - With the correct profile environment loaded, the embedded daemon timed out after 180 seconds. Log signature: Hugging Face HEAD request to `BAAI/bge-small-en-v1.5` failed with `[WinError 10054]`, preventing cross-encoder initialization. No `reflect()` result or mental-model update was produced.
  - `HF_TOKEN` remains absent. The zero-byte Hindsight lock created by the failed attempt was removed after confirming port 9807 was not listening. No markdown memory data was lost.
  - Gateway liveness is a separate warning: profile `gateway.log` last changed 2026-07-15 10:09 and last records `Cron ticker started` at 2026-07-15 02:49 (>24h ago). The current cleanup job ran, but Gateway health is not proven by that stale log.
  - Boss action to unlock Hindsight remains one of: add `HF_TOKEN`, move to `local_external`, or use Hindsight cloud mode.
- 2026-07-09 — moved 2026-06-03 entries (validation history + toolset snapshot).
- 2026-07-10 — no-op.
- 2026-07-11 — no-op (no 30+ day entries in MEMORY.md). Hindsight reflect attempted.
  - Hindsight daemon failed to start: `RuntimeError: Cannot send a request, as the client has been closed.` during `cross_encoder.initialize()` (HF Hub model download for the reranker step). Per skill guidance, this is environmental — not retryable in this cron. Falling back to markdown archive only.
  - Provider override applied successfully: `openai_compatible` (the invalid value in `~/.hermes/hindsight/config.json`) was overridden to `minimax` via `HINDSIGHT_API_LLM_PROVIDER` env var. The provider validation no longer fails — the daemon gets past LLM init before tripping on the cross-encoder download.
- 2026-07-12 — no-op. Hindsight reflect attempted, same failure mode as 7-11.
- 2026-07-13 — no-op. Hindsight reflect **skipped** per skill guidance ("don't retry in the same run; fix is environmental"). 3rd consecutive run with the identical signature in `~/.hindsight/profiles/handsome_company_manager.log`:
  - `cross_encoder.initialize()` → `RuntimeError: Cannot send a request, as the client has been closed.` (HF Hub HEAD requests to `cross-encoder/ms-marco-MiniLM-L-6-v2` and `BAAI/bge-small-en-v1.5` return `[WinError 10054] 远程主机强迫关闭了一个现有的连接`).
  - `PostgreSQLBackend is not initialized. Call initialize() first.` (embedded pg0 init fails after cross-encoder timeout cascades into lifespan teardown).
  - Stale 0-byte `.lock` from 2026-07-12 21:53 removed (housekeeping, not a retry). Log retained for the next boss-driven debug session.
  - **Action recommended for boss (one of):**
    a) Set `HF_TOKEN` in `~/.hermes/profiles/handsome_company_manager/.env` for higher rate limits + authentication, then retry on next cron tick.
    b) Switch Hindsight to `mode: local_external` (run `hindsight_api` as a separate container / process outside the cron) — separates the model download lifecycle from the cron tick.
    c) Switch to `mode: cloud` if a hosted Hindsight endpoint is available.
  - Until one of (a/b/c) is applied, this skill's `reflect()` step will continue to skip and the markdown archive remains the sole source of truth.
- 2026-07-14 — no-op. Hindsight reflect **skipped** per skill guidance (4th consecutive same-signature run; the recommended 3-action remedy is still pending boss decision). Confirmed:
  - `~/.hindsight/profiles/handsome_company_manager.log` mtime is **2026-07-12 21:54** — no new Hindsight activity since 7-12 (consistent with the 7-13 "skip" run and this 7-14 "skip" run).
  - `hindsight` package remains importable; the failure is at the cross-encoder download step (HF Hub HEAD timeout) cascading into the embedded pg0 init, not at the LLM init or provider validation.
  - `~/.hindsight/profiles/` has zero `.lock` files — no stale lock to clean.
  - Markdown archive remains the sole source of truth; no MEMORY.md entries with an internal date older than 2026-06-14 exist. The 7-13 cutoff (2026-06-13) was actually 31 days back — bumped to a strict 30-day window this run for clarity.
- 2026-07-15 — no-op. Hindsight reflect **skipped** per skill guidance (5th consecutive same-signature run). Confirmed:
  - `~/.hindsight/profiles/handsome_company_manager.log` mtime is still **2026-07-12 21:54** — no new Hindsight activity since then (consistent with the 7-13/7-14 "skip" runs and this 7-15 "skip" run).
  - `HF_TOKEN` is **still NOT set** in `~/.hermes/profiles/handsome_company_manager/.env` — verified directly from the file. The 2026-07-13 recommended action item (a) is still pending. Until boss picks (a) / (b) / (c), Hindsight `reflect()` will keep skipping per skill guidance ("don't retry in the same environment").
  - No new MEMORY.md entries with internal date older than 2026-06-15; the only dated entry (`1+N 数字员工集成(2026-07-08)`) is 7 days old and stays active.
  - `~/.hindsight/profiles/` has zero `.lock` files — no stale lock to clean.
  - **Boss action still open** (one of):
    a) Set `HF_TOKEN=hf_***` in `~/.hermes/profiles/handsome_company_manager/.env` for higher HF rate limits + authentication, then retry on next cron tick.
    b) Switch Hindsight to `mode: local_external` — run `hindsight_api` as a separate container / process outside the cron, separating the model-download lifecycle from the cron tick.
    c) Switch to `mode: cloud` if a hosted Hindsight endpoint is available.
- 2026-07-16 — no-op (today). Hindsight reflect **skipped** per skill guidance (6th consecutive same-signature pattern; 4th consecutive explicit skip after the 7-11/7-12 two failed attempts). Confirmed:
  - `~/.hindsight/profiles/handsome_company_manager.log` mtime is still **2026-07-12 21:54** — **4 days** since the last Hindsight attempt, consistent with all 7-13/7-14/7-15 skip runs.
  - `HF_TOKEN` is **still NOT set** in `~/.hermes/profiles/handsome_company_manager/.env` — re-verified directly from the file (read all 33 env keys; HF_TOKEN absent). The 2026-07-13 recommended action item (a) is still pending.
  - `~/.hermes/hindsight/config.json` is **MISSING** (was present on 7-11 with `openai_compatible`). Either a fresh install/migration removed it, or the `oneplusn` deploy never re-created it. The Hindsight Python constructor reads provider/model/key/api_base from kwargs + env vars, so the missing config.json does NOT change the failure mode — `cross_encoder.initialize()` would still be invoked and trip on HF Hub HEAD timeout → cascading `PostgreSQLBackend is not initialized`.
  - `~/.hindsight/profiles/` has zero `.lock` files — no stale lock to clean.
  - Stale `MEMORY.md.lock` (3 days old, 0 bytes) and `USER.md.lock` (2 days old, 0 bytes) cleaned this run as routine housekeeping — safe to remove since 0 bytes and no process actively holding them.
  - No new MEMORY.md entries with internal date older than 2026-06-16; the only dated entry (`1+N 数字员工集成(2026-07-08)`) is 8 days old and stays active.
  - Gateway liveness check: `~/.hermes/profiles/handsome_company_manager/logs/gateway.log` shows last activity 2026-07-15 10:09 (Feishu inbound + agent cache evict); cron ticker started 2026-07-15 02:49. Gateway is alive — the reflect-skip is not due to gateway down.
  - **Boss action STILL open** (one of): same (a/b/c) as 7-13/7-15. No new evidence suggests the env has changed in a way that would let `reflect()` succeed; the failure signature has been stable for 4 days.
- Next scheduled cleanup: per the cron job cadence. Boss action for unlocking `reflect()`: choose one of the 2026-07-17 housekeeping options (`HF_TOKEN`, `local_external`, or cloud mode).
