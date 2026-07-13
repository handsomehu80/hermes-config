# Hindsight bank — quick reference

Authoritative config keys and runtime details for the Hindsight memory provider
bundled with Hermes Agent (`hindsight-all 0.8.4`, `hindsight-api 0.8.4`).

## Config files

| Path | Purpose |
|---|---|
| `~/.hermes/hindsight/config.json` | Hindsight provider config (mode, bank_id, LLM) |
| `~/.hermes/profiles/<profile>/config.yaml` | Hermes-side `memory.provider: hindsight` switch |
| `~/.hermes/profiles/<profile>/.env` | API keys (`MINIMAX_CN_API_KEY`, etc.) |
| `~/.hindsight/profiles/<profile>/` | Per-profile runtime data (lock, log, db) |
| `~/.hindsight/profiles/<profile>.log` | Daemon subprocess log — first place to look on failure |

## Hindsight `config.json` schema (key fields)

```json
{
  "mode": "local_embedded",        // cloud | local_embedded | local_external
  "llm_provider": "minimax",        // see valid list below
  "llm_base_url": "https://api.minimaxi.com/v1",
  "llm_model": "MiniMax-M3",
  "bank_id": "hermes",              // static fallback; can be templated
  "recall_budget": "mid",           // low | mid | high
  "timeout": 120,
  "idle_timeout": 300
}
```

## Valid `llm_provider` values (daemon whitelist)

From `hindsight_api/engine/llm_wrapper.py` line ~645:

```
openai, groq, ollama, ollama-cloud, gemini, anthropic, lmstudio, llamacpp,
vertexai, openai-codex, claude-code, mock, none, minimax, deepseek, litellm,
litellmrouter, bedrock, volcano, openrouter, requesty, zai, opencode-go,
atlas, fireworks, nous
```

`openai_compatible` is **not** on this list. The Hermes plugin README mentions
it for the provider, but the daemon rejects it. For an OpenAI-compatible
endpoint, use the `minimax` provider with `llm_base_url` set, or whichever
named provider matches the actual API (e.g. `groq` for Groq, `openrouter` for
OpenRouter).

## Env vars consumed by the daemon subprocess

Set these in the **parent** process environment before constructing
`HindsightEmbedded`:

| Env var | Purpose |
|---|---|
| `HINDSIGHT_API_LLM_PROVIDER` | Provider name (must be on the whitelist) |
| `HINDSIGHT_API_LLM_MODEL` | Model identifier |
| `HINDSIGHT_API_LLM_API_KEY` | API key for the LLM provider |
| `HINDSIGHT_API_LLM_BASE_URL` | Override endpoint for OpenAI-compatible APIs |
| `HINDSIGHT_API_LOG_LEVEL` | `critical` / `error` / `warning` / `info` / `debug` / `trace` |
| `HINDSIGHT_EMBED_DAEMON_IDLE_TIMEOUT` | Seconds before idle daemon exits (set via `idle_timeout=` arg) |
| `HINDSIGHT_EMBED_API_DATABASE_URL` | Optional override for the embedded Postgres URL |

The parent also needs `HINDSIGHT_LLM_API_KEY` set if the LLM key isn't already
in the daemon's environment from a different source.

## Common failure log signatures

| Log message | Cause | Fix |
|---|---|---|
| `ValueError: Invalid LLM provider: openai_compatible` | Provider not on daemon whitelist | Use `minimax` (or another valid name) + `llm_base_url` |
| `PostgreSQLBackend is not initialized. Call initialize() first.` | Embedded `pg0` failed to start (common on Windows) | Switch to `local_external` or `cloud`; not recoverable in a short cron |
| `⏳ Waiting for daemon... (180s elapsed)` then `✗ Daemon Failed (Timeout)` | Daemon subprocess couldn't start within timeout | Check `~/.hindsight/profiles/<profile>.log` for the root cause above |
| `Address already in use` / port 9807 collision | Stale `.lock` file in `~/.hindsight/profiles/` | `rm ~/.hindsight/profiles/*.lock` then retry |

## Python API surface (cheat sheet)

From `HindsightClient` (the high-level client returned by `HindsightEmbedded.client`):

- `client.list_banks()`
- `client.create_bank(bank_id=...)` / `client.delete_bank(bank_id=...)`
- `client.get_bank_config(bank_id=...)`
- `client.retain(bank_id=..., content=...)` / `client.retain_batch(...)`
- `client.list_memories(bank_id=..., limit=...)`
- `client.recall(bank_id=..., query=...)`
- `client.reflect(bank_id=..., query=...)` — **this is the optimization step**
- `client.list_mental_models(bank_id=...)` / `client.get_mental_model(...)` / `client.create_mental_model(...)` / `client.refresh_mental_model(...)`

Async variants exist as `arecall`, `aretain`, `areflect`, etc. for batch use.

## Quick local-embedded smoke test

```python
import os
from hindsight.embedded import HindsightEmbedded

# assume MINIMAX_CN_API_KEY + MINIMAX_CN_BASE_URL already in env
os.environ["HINDSIGHT_API_LLM_PROVIDER"] = "minimax"
os.environ["HINDSIGHT_API_LLM_MODEL"]    = "MiniMax-M3"

he = HindsightEmbedded(
    profile="default",
    llm_provider="minimax",
    llm_api_key=os.environ["MINIMAX_CN_API_KEY"],
    llm_model="MiniMax-M3",
    llm_base_url=os.environ.get("MINIMAX_CN_BASE_URL"),
    idle_timeout=30,
)
print(he.url)                      # raises RuntimeError if daemon didn't start
print(he.client.list_banks())
he.close()
```

If this prints a URL and bank list in <60s, the bank is healthy.
If it raises `RuntimeError: Failed to start daemon for profile '...'`,
read `~/.hindsight/profiles/<profile>.log` for the underlying error.
