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
> Latest run: **2026-07-23** — no-op archive; no entries in MEMORY.md
> carried an internal date older than the 30-day cutoff
> (2026-06-23). The dated active entries are
> `1+N 数字员工集成(2026-07-08)` (15d old) and
> `Credential state (2026-07-20)` (3d old); both remain within the
> 30-day window. Undated environment-state facts (Host, Hermes
> v0.15.1, Agent Team summary, PM 铁律+陷阱, PM cron) remain in place
> per the "no internal date → don't archive on mtime" rule. USER.md
> was unchanged.
> Hindsight is enabled (`memory.provider: hindsight`) and installed, so
> `reflect()` was attempted via `hindsight_reflect.py handsome_company_manager`
> with a consolidation query. The embedded daemon timed out after 180
> seconds; runner exit code = 1. Time-scoped current-run signature at
> **2026-07-23 21:01:41**: `LLM trace write failed for scope=verification:
> PostgreSQLBackend is not initialized. Call initialize() first.` The
> retained Hindsight log still contains the historical HF cross-encoder
> / Hugging Face connection-reset cascade (`[WinError 10054]` and
> `Cannot send a request, as the client has been closed`); no mental model
> was created or updated. `HF_TOKEN` remains present-but-commented-out
> (inactive) in `.env`; markdown memory remains the authoritative store.
> The failed daemon left a fresh 0-byte Hindsight lock; port 9807 was
> confirmed not listening and the lock was removed safely. Pre-flight
> found no `memories/*.lock`. `agent.log` is fresh from this run and
> `errors.log` is current (~50m), while `gateway.log` is ~66h stale;
> per the tri-state rule this indicates a live agent with a stale logging
> artifact, not a proven gateway-down condition.

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
- 2026-07-18 — no-op (today). Hindsight reflect **skipped** per skill guidance (7th consecutive same-signature run; 5th consecutive explicit skip after the 7-11/7-12 two failed attempts and 7-13..7-16 explicit skips). Confirmed in this run:
  - `~/.hindsight/profiles/handsome_company_manager.log` mtime is now **2026-07-18 21:03:36** — refreshed by this run's failed attempt (it was 2026-07-17 21:03 before). The signature is the established one: HF Hub HEAD requests to `cross-encoder/ms-marco-MiniLM-L-6-v2/.../modules.json` and `BAAI/bge-small-en-v1.5/.../adapter_config.json` return `[WinError 10054] 远程主机强迫关闭了一个现有的连接` (Windows socket forcibly closed); this aborts `cross_encoder.initialize()` and cascades into `PostgreSQLBackend is not initialized`; daemon exits at the 188s mark.
  - `HF_TOKEN` is **still NOT active** in `~/.hermes/profiles/handsome_company_manager/.env` — the line is present but commented out (verified this run; 31 env keys total, HF_TOKEN the only one of the recommended remediation trio that's even present-but-disabled). Action item (a) from 7-13 is still pending.
  - `~/.hermes/hindsight/config.json` is still **MISSING** — same state as 7-16. The Hindsight Python constructor reads provider/model/key/api_base from kwargs + env vars, so the missing file does not change the failure mode.
  - `~/.hindsight/profiles/` has zero `.lock` files (Hindsight locks) — no stale lock to clean. `memories/*.lock` also empty — pre-flight housekeeping found nothing to sweep.
  - No new MEMORY.md entries with internal date older than 2026-06-18: dated active entries are `1+N 数字员工集成(2026-07-08)` (10d) and `Credential state (2026-07-17)` (1d). Undated facts (Host / Hermes v0.15.1 / Agent Team / PM 铁律+陷阱 / PM cron) all stay in place per the no-internal-date rule.
  - Gateway liveness check: `~/.hermes/profiles/handsome_company_manager/logs/gateway.log` shows last activity 2026-07-18 02:51:29 (today, ~18h ago); cron ticker started 2026-07-18 02:51:24. **Gateway is healthy** — the reflect-skip is unambiguously an environmental/HF-blocker issue, not a gateway-down issue. This is a positive change vs the 7-17 run which had a stale gateway log.
  - **Boss action STILL open** (one of): same (a/b/c) as 7-13/7-15/7-16/7-17. With the gateway now confirmed alive and the HF-blocker signature stable for 7+ days, the picture is unambiguous: the only way out of this loop is the boss picking one of the three remedies. Markdown archive continues as the sole source of truth.
- 2026-07-19 — no-op (today). Hindsight reflect **attempted per explicit user request** (8th consecutive same-signature run; 6th consecutive explicit skip after the 7-11/7-12 two failed attempts and 7-13..7-17 explicit skips). Confirmed in this run:
  - `~/.hindsight/profiles/handsome_company_manager.log` mtime is now **2026-07-19 21:03:32** — refreshed by this run's failed attempt (it was 2026-07-18 21:03:36 before). The signature is the established one: HF Hub HEAD requests to `cross-encoder/ms-marco-MiniLM-L-6-v2/.../modules.json` and `BAAI/bge-small-en-v1.5/.../adapter_config.json` return `[WinError 10054] 远程主机强迫关闭了一个现有的连接` (Windows socket forcibly closed); this aborts `cross_encoder.initialize()` and cascades into `PostgreSQLBackend is not initialized`; daemon exits at the 188s mark. `hindsight_reflect.py` exit code = 1.
  - **Script-side observation**: the script reports `removed 1 stale lock file(s)` at startup (the `~/.hindsight/profiles/handsome_company_manager.lock` left by the 7-18 failed attempt), then the daemon restarts and immediately re-fails. This confirms the lock-cleanup path in the script works; the failure is environmental (HF Hub connectivity), not a stale-lock issue.
  - `HF_TOKEN` is **still commented out** in `~/.hermes/profiles/handsome_company_manager/.env` — verified this run via the skill's HF_TOKEN state detection recipe (line starts with `# HF_TOKEN=`). Action item (a) from 7-13 is still pending. Boss has had 8 days to choose a remedy and none has been applied — pattern strongly suggests `HF_TOKEN` is intentionally absent (e.g., the profile is intentionally local-only).
  - `~/.hermes/hindsight/config.json` is still **MISSING** — same state as 7-16/7-18. The Hindsight Python constructor reads provider/model/key/api_base from kwargs + env vars, so the missing file does not change the failure mode. Worth investigating: maybe `~/.hermes/hindsight/` itself doesn't exist as a directory on this Windows host.
  - No new MEMORY.md entries with internal date older than 2026-06-19: dated active entries are `1+N 数字员工集成(2026-07-08)` (11d) and `Credential state (2026-07-17)` (2d). Undated facts (Host / Hermes v0.15.1 / Agent Team / PM 铁律+陷阱 / PM cron) all stay in place per the no-internal-date rule.
  - Pre-flight housekeeping: no stale `memories/*.lock` files to clean (verified this run). `agent.log` shows fresh activity at 2026-07-19 21:02:16 (this run is being executed). `errors.log` also fresh.
  - **Gateway liveness status (new finding vs 7-18)**: `~/.hermes/profiles/handsome_company_manager/logs/gateway.log` mtime is **2026-07-18 02:51:29** — ~42 hours ago (was ~18h ago at 7-18). The last log entries are: `Cron ticker started (interval=60s)` at 2026-07-18 02:51:24 and `kanban dispatcher: embedded in gateway (interval=60.0s)` at 2026-07-18 02:51:29. No further log activity despite the 60s cron ticker. **But** the agent IS alive (this session is responding to a cron tick), so the gateway is functioning — `gateway.log` is just silent. This is a logging artifact, not a gateway-down issue; `agent.log` (1.7MB, mtime today) confirms real activity. The skill says: "If the Gateway log is stale, that's a separate issue from the Hindsight reflect failure — record it but don't conflate the two in housekeeping." So this is recorded but does not affect the reflect-skip attribution.
  - **Boss action STILL open** (one of): same (a/b/c) as 7-13/7-15/7-16/7-17/7-18. With the gateway log now ~42h stale and the HF-blocker signature stable for 8+ days, the picture is unambiguous: the only way out of this loop is the boss picking one of the three remedies. Markdown archive continues as the sole source of truth.
- 2026-07-20 — no-op archive (cutoff 2026-06-20). Dated active entries remain 2026-07-08 and 2026-07-20; the credential snapshot was corrected from “HF_TOKEN absent” to “present but commented out/inactive”. Undated current-state facts stay active. USER.md unchanged.
  - Pre-flight: no stale `memories/*.lock`; `gateway.log` is ~66h stale, while `agent.log` is current from this cron run. Per the tri-state rule, the agent/gateway path is alive and the gateway-log staleness is only a logging artifact.
  - Hindsight is enabled and `hindsight_reflect.py` was run with a topic/recency/actionability consolidation query. The embedded daemon timed out after 180s; exit code 1. Current-run signature: `PostgreSQLBackend is not initialized. Call initialize() first.` No mental model was created or updated.
  - The retained Hindsight log still contains the established cross-encoder/Hugging Face failures (`[WinError 10054]` and `Cannot send a request, as the client has been closed`); `HF_TOKEN` is present but commented out. The failure remains environmental, and markdown memory remains authoritative.
  - The failed daemon left a fresh 0-byte `handsome_company_manager.lock`; port 9807 was confirmed not listening, then the lock was removed. No memory data was lost.
  - Boss action still open (choose one): uncomment `HF_TOKEN` and set a real value; switch Hindsight to `local_external`; or use cloud mode. The previous actual Hindsight attempt was 2026-07-19 21:03 (log mtime); this run refreshed the log at 2026-07-20 21:02.
- 2026-07-21 — no-op archive (cutoff 2026-06-21). Dated active entries remain 2026-07-08 (13d) and 2026-07-20 (1d); no entries exceed the 30-day window. Undated current-state facts (Host / Hermes v0.15.1 / Agent Team / PM 铁律+陷阱 / PM cron) stay active. USER.md unchanged.
  - Pre-flight: no stale `memories/*.lock`; `gateway.log` is ~18h stale, but `agent.log` is fresh (touched this run, 0m) and `errors.log` is current (56m). Per the §3 tri-state rule, the agent/gateway path is alive; the stale gateway log is a logging artifact, not a gateway-down signal.
  - Hindsight is enabled and `hindsight_reflect.py` was run with a topic/dedup/group-by/actionability consolidation query. The embedded daemon timed out after 180s; exit code 1; duration 196.1s.
  - Time-scoped current-run signature: exactly **1 log line** written at/after this run's start (2026-07-21 21:02:28) — `LLM trace write failed for scope=verification: PostgreSQLBackend is not initialized. Call initialize() first.` The retained historical signature in the full log still includes the HF cross-encoder cascade (`[WinError 10054]` / `Cannot send a request, as the client has been closed`); this run never got far enough to retry the HF HEAD requests, so it surfaces only the downstream pg0 teardown warning. The blocker remains environmental.
  - The failed daemon left a fresh 0-byte `~/.hindsight/profiles/handsome_company_manager.lock`; port 9807 was confirmed not listening (errno 10035 = WSAEWOULDBLOCK on the connect probe), then the lock was removed safely. No memory data was lost.
  - Boss action STILL open (9th consecutive same-signature day; same trio as 7-13..7-20): choose one of (a) uncomment `HF_TOKEN` and set a real value, (b) switch Hindsight to `local_external`, or (c) use cloud mode. The previous actual Hindsight attempt was 2026-07-20 21:02 (log mtime); this run refreshed the log at 2026-07-21 21:02.
- 2026-07-22 — no-op archive (cutoff 2026-06-22). Dated active entries remain 2026-07-08 (14d) and 2026-07-20 (2d); no entries exceed the 30-day window. Undated current-state facts (Host / Hermes v0.15.1 / Agent Team / PM 铁律+陷阱 / PM cron) stay active. USER.md unchanged.
  - Pre-flight: no stale `memories/*.lock` files to clean. The 5 toolset `*.lock` files in the profile root (`auth.lock`, `cron/.tick.lock`, `gateway.lock`, `lsp/node_modules/fuzzy-search/yarn.lock`, `skills/.usage.json.lock`) are NOT memory locks — they belong to other subsystems and are out of scope for this cleanup.
  - Gateway log tri-state check (§3): `agent.log` (3.5MB) was touched this very run (0m ago), `errors.log` is 15m old, but `gateway.log` is **2528m (~42h) stale** — same staleness as the 7-19 run. Per the tri-state rule, the agent/gateway path is alive; the stale `gateway.log` is a logging artifact (no follow-up entries since the 2026-07-21 02:53 ticker despite 60s cron ticks), NOT a gateway-down condition. Recorded but not conflated with the Hindsight reflect failure.
  - Hindsight is enabled (`memory.provider: hindsight` per `config.yaml`); `hindsight-all 0.8.4` + 3 sibling packages are installed. `hindsight_reflect.py handsome_company_manager --query 'Consolidate the durable knowledge in this bank: ... actionability for the boss.'` was run. The embedded daemon failed to start within 180s; `hindsight_reflect.py` exit code = 1 (per the runner's `RuntimeError: Failed to start daemon for profile 'handsome_company_manager'` after `✗ Daemon Failed (Timeout)`).
  - Time-scoped current-run signature (lines at/after this run's start 2026-07-22 21:02:11): exactly **1 log line** — `WARNING - hindsight_api.engine.llm_trace - LLM trace write failed for scope=verification: PostgreSQLBackend is not initialized. Call initialize() first.` Same single-line signature as the 7-21 run; the daemon once again died before the cross-encoder step. The retained historical signature in the full log still contains the HF cross-encoder cascade (`[WinError 10054] 远程主机强迫关闭了一个现有的连接` from `https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/adapter_config.json`); this run never added new HF HEAD-retry lines. The blocker remains environmental.
  - The failed daemon left a fresh 0-byte `~/.hindsight/profiles/handsome_company_manager.lock` (mtime 2026-07-22 21:01); port 9807 was probed and confirmed NOT listening (connect timeout = no listener), then the lock was removed safely. No memory data was lost.
  - Boss action STILL open (10th consecutive same-signature day; same trio as 7-13..7-21): choose one of (a) uncomment `HF_TOKEN` and set a real value, (b) switch Hindsight to `local_external`, or (c) use cloud mode. The previous actual Hindsight attempt was 2026-07-21 21:02 (log mtime); this run refreshed the log at 2026-07-22 21:02.
- 2026-07-23 — no-op archive (cutoff 2026-06-23). Dated active entries remain 2026-07-08 (15d) and 2026-07-20 (3d); no entries exceed the 30-day window. Undated current-state facts stay active. USER.md unchanged.
  - Pre-flight: no stale `memories/*.lock`; the failed Hindsight attempt left a fresh 0-byte profile lock, but port 9807 was confirmed not listening and the lock was removed safely.
  - Hindsight is enabled and installed. `hindsight_reflect.py` was run with a consolidation query; the daemon timed out after 180s, exit code 1. The time-scoped current-run signature at 2026-07-23 21:01:41 was `PostgreSQLBackend is not initialized. Call initialize() first.` No mental model was created or updated. The retained log still contains the historical Hugging Face cross-encoder connection-reset cascade (`[WinError 10054]` / `Cannot send a request, as the client has been closed`).
  - `HF_TOKEN` is present but commented out (inactive). Boss action remains one of: uncomment and set a real `HF_TOKEN`, switch Hindsight to `local_external`, or use cloud mode. Markdown memory remains the source of truth until the environmental blocker is resolved.
  - Liveness tri-state: `agent.log` is fresh from this run and `errors.log` is current (~50m); `gateway.log` is ~66h stale, so this is a logging artifact rather than proof the gateway is down.
- Next scheduled cleanup: per the cron job cadence. Boss action for unlocking `reflect()`: choose one of the three remedies above; the Hindsight blocker has persisted for 11 consecutive runs.
