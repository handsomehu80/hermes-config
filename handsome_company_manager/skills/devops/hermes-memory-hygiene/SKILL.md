---
name: hermes-memory-hygiene
description: Periodic memory cleanup and optimization for Hermes Agent profiles. Use when a cron job or user requests archiving 30+ day old memories, when MEMORY.md needs pruning, or when the Hindsight bank should be reflect-optimized. Covers the 3-file memory model, archive header conventions, and Hindsight bank integration pitfalls.
category: devops
---

# Hermes Memory Hygiene

Maintain the durable memory of a Hermes profile — markdown memory files plus the optional Hindsight bank — on a cron cadence or on user request. Triggered by scheduled jobs ("清理记忆", "memory cleanup", "30-day archive") or explicit cleanup requests.

## When to use

- Cron-triggered 30-day memory archive
- User asks to "clean memory", "归档旧记忆", "memory hygiene"
- Manual pruning of stale operational facts in `MEMORY.md`
- Optional: trigger Hindsight `reflect()` (LLM-powered cross-memory synthesis) on the active bank

## Memory model

Every Hermes profile has its own memory store at:
```
~/.hermes/profiles/<profile>/memories/
├── MEMORY.md          # active operational memory (≤ memory_char_limit, default 2200)
├── MEMORY_ARCHIVE.md  # rotated-out facts (30+ day old or session-finished)
└── USER.md            # timeless user profile (preferences, style, communication)
```

- `MEMORY.md` is injected into the agent's context as a "memory" prompt on every turn. Keep it lean.
- `USER.md` is loaded separately as user-profile data. **Do not archive based on mtime alone** — it stores timeless facts.
- `MEMORY_ARCHIVE.md` is the destination for facts that are no longer current but might be needed for archaeology. Each section should start with a `## YYYY-MM-DD — title` heading.

The `memory()` tool is the normal write path, but **it is not always available** — in cron contexts it often returns "Memory is not available. It may be disabled in config or this environment." When that happens, fall back to direct file edits with `read_file` / `patch` / `write_file`. The on-disk files are the durable source of truth either way.

## 30-day archive workflow

1. **Compute the cutoff**: today minus 30 days (e.g. 2026-07-10 → cutoff 2026-06-10).
2. **Survey `MEMORY.md` line by line.** Entries are separated by `§` and may carry an internal date in parentheses (e.g. `1+N 数字员工集成(2026-07-08)`). If no internal date is present, treat the entry as current environment state — **do not** archive based on file mtime.
3. **Move** any entry whose internal date is before the cutoff to `MEMORY_ARCHIVE.md`. Preserve the entry text verbatim; prepend a `## YYYY-MM-DD — title` heading if not already present.
4. **Update the archive header** to record this run:
   ```markdown
   > Archived by the 30-day cleanup cron. Active cutoff: any entry whose
   > internal date is older than 30 days from "now" gets moved here.
   > ...
   > Latest run: **YYYY-MM-DD** — <one-line summary of what moved or "no-op">.
   ```
5. **Update the housekeeping section** at the bottom with `Last run: YYYY-MM-DD — <summary>`.
6. **Leave `USER.md` alone** unless the user-profile facts themselves are changing. Mtime ≠ validity.

If the survey finds no 30+ day entries, just update the header + housekeeping (record the no-op). Do not invent entries to archive.

## Hindsight reflect (advanced organization)

When `memory.provider: hindsight` is set in the active profile's `config.yaml` and the bank is reachable, call `reflect()` to consolidate stored memories into a fresh mental model. This is Hindsight's optimization capability.

### Detect
```yaml
# ~/.hermes/profiles/<profile>/config.yaml
memory:
  memory_enabled: true
  provider: hindsight
```
```json
// ~/.hermes/hindsight/config.json
{
  "mode": "local_embedded",
  "bank_id": "hermes",
  "llm_provider": "minimax",
  "llm_model": "MiniMax-M3",
  "llm_base_url": "https://api.minimaxi.com/v1"
}
```

### Try
```python
import os
from pathlib import Path

# Load LLM key from the active profile's .env
for line in Path("~/.hermes/profiles/<profile>/.env").expanduser().read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

api_key  = os.environ["MINIMAX_CN_API_KEY"]
base_url = os.environ.get("MINIMAX_CN_BASE_URL", "https://api.minimaxi.com/v1")

# CRITICAL: set provider env var BEFORE spawning the daemon subprocess
os.environ["HINDSIGHT_API_LLM_PROVIDER"] = "minimax"
os.environ["HINDSIGHT_API_LLM_MODEL"]    = "MiniMax-M3"
os.environ["HINDSIGHT_API_LLM_API_KEY"]  = api_key
os.environ["HINDSIGHT_API_LLM_BASE_URL"] = base_url

# Clean up any stale .lock from prior failed daemon attempts
import glob
for lock in glob.glob(os.path.expanduser("~/.hindsight/profiles/*.lock")):
    try: os.remove(lock)
    except OSError: pass

from hindsight.embedded import HindsightEmbedded
he = HindsightEmbedded(
    profile="<profile>",
    llm_provider="minimax",     # NOT "openai_compatible" — see pitfalls
    llm_api_key=api_key,
    llm_model="MiniMax-M3",
    llm_base_url=base_url,
    idle_timeout=30,
    log_level="warning",
)

# Short-circuit if the bank is empty (never-used profile)
mems = he.client.list_memories(bank_id="hermes", limit=1)
if not (getattr(mems, "memories", None) or (isinstance(mems, dict) and mems.get("memories"))):
    print("bank is empty; nothing to reflect on")
else:
    he.client.reflect(bank_id="hermes", query="Consolidate the durable knowledge in this bank")

he.close()
```

### Pitfalls
- **`openai_compatible` is NOT a valid `llm_provider`** in Hindsight's daemon, even though the plugin config may list it. The valid set is: `openai, groq, ollama, ollama-cloud, gemini, anthropic, lmstudio, llamacpp, vertexai, openai-codex, claude-code, mock, none, minimax, deepseek, litellm, litellmrouter, bedrock, volcano, openrouter, requesty, zai, opencode-go, atlas, fireworks, nous`. For `MiniMax-M3` at `api.minimaxi.com/v1` use `minimax` + `llm_base_url=…/v1`. The fastest confirmation is the previous-run log at `~/.hindsight/profiles/<profile>.log` — search for `Invalid LLM provider`.
- **Stale `.lock` files** in `~/.hindsight/profiles/` block daemon start. Remove them before retrying.
- **Cross-encoder reranker download can fail after LLM init succeeds.** Hindsight's `local_embedded` mode pulls a CrossEncoder model from HuggingFace during `memory.initialize()`. On hosts with restricted/timeout-prone HF access, this fails with `RuntimeError: Cannot send a request, as the client has been closed.` (or any `httpx` "client closed" error in `cross_encoder.initialize()`). The provider override above is correct — that error is *past* LLM init. **Skip `reflect()` and fall back to markdown archive** for this cron. Do not retry in the same run; the fix is environmental (`HF_TOKEN` for higher rate limits, HF mirror, or `mode: local_external` / `cloud`).
- **Embedded PostgreSQL** (`pg0`) may fail to initialize on some Windows hosts with `PostgreSQLBackend is not initialized. Call initialize() first.`. If the log shows this, the bank is unreachable in the current cron — skip `reflect()` and rely on the markdown archive only. The fix is environmental (separate Hindsight container via `local_external`, or `cloud` mode), not something to retry.
- **Bank may be empty** for a profile that has never used Hindsight. The daemon will start fine, but `reflect()` returns a degenerate result. Check `list_memories` first and short-circuit.
- **Daemon startup is slow** (60–180s on Windows). Set `idle_timeout=30` so the daemon exits promptly when done. The embedded client blocks on a port binding, so the parent process won't return until the daemon comes up.
- **Env vars are read by the daemon subprocess from its own environment**, not just the config dict you pass. Always set `HINDSIGHT_API_LLM_PROVIDER` / `HINDSIGHT_API_LLM_MODEL` / `HINDSIGHT_API_LLM_API_KEY` / `HINDSIGHT_API_LLM_BASE_URL` in the parent process env **before** constructing `HindsightEmbedded`.
- **General skip rule for `reflect()`**: if the daemon fails to start or the bank is unreachable for *any* environmental reason (network, model download, embedded DB, port binding, missing creds), record the failure signature in `MEMORY_ARCHIVE.md` housekeeping and stop. The markdown archive is the durable source of truth — a skipped `reflect()` does not lose data, only defers the optimization step.

## Verification

- [ ] `MEMORY.md` contains no entries with an internal date before the cutoff
- [ ] `MEMORY_ARCHIVE.md` header records the latest run date and a one-line summary
- [ ] Housekeeping section at the bottom of `MEMORY_ARCHIVE.md` updated
- [ ] If Hindsight `reflect()` ran: `client.list_mental_models(bank_id="hermes")` shows a fresh entry
- [ ] `USER.md` unchanged (only update on actual user-profile changes, not on mtime)

## Files

- `references/hindsight-bank.md` — Hindsight config schema, full `llm_provider` list, env-var matrix, and log signatures for common failure modes
- `scripts/hindsight_reflect.py` — re-runnable `reflect()` runner. Loads the profile `.env`, overrides provider env vars, clears stale locks, starts the daemon, calls `reflect()`, and reports new vs existing mental models. Use instead of pasting the recipe above.

### Quick re-run

```bash
python scripts/hindsight_reflect.py <profile>            # uses defaults
python scripts/hindsight_reflect.py <profile> --query "Reorganize by topic"
```

Exit codes: `0` = reflect ran (or bank was empty + correctly skipped), `1` = daemon failed to start (see `~/.hindsight/profiles/<profile>.log`), `2` = missing API key in profile `.env`, `3` = `hindsight` package not importable.
