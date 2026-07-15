# Hindsight 0.8.4 — `openai_compatible` provider rejected, MiniMax CN endpoint mismatch

The plugin README (`plugins/memory/hindsight/README.md`) at the "Local Embedded LLM"
table documents `openai_compatible` as a valid `llm_provider` value. The installed
hindsight-client **0.8.4** daemon (`hindsight_api/engine/llm_wrapper.py:616-643`) does
**not** accept that value — its `valid_providers` list is hard-coded and was tightened
between 0.4.x and 0.8.x. The README is stale.

This produces a **silent failure** for any profile with `memory.provider=hindsight`:
the daemon dies at startup, `retain()` / `reflect()` / `recall()` never run, and the
caller sees an empty bank indistinguishable from "no data yet." The
`memory-cleanup` cron (one of the three daily crons per employee) is the most visible
casualty because its prompt explicitly says *"if hindsight is installed, invoke its
optimization capability"* — that invocation quietly fails and the cron reports
"nothing to do" while the underlying cause is a config bug.

This affects **all profiles globally** because `~/AppData/Local/hermes/hindsight/config.json` is
shared, not per-profile. (Note: the config lives in the Hermes install root,
NOT `~/.hermes/hindsight/config.json` — that path does not exist on this
host. The daemon LOG path `~/.hindsight/profiles/<profile>.log` IS correct
as written below; only the config path was wrong before 2026-07-14.) One fix
unblocks dev / reviewer / manager / architect / tester / insight / research /
security — at the cost of re-pushing the corrected provider into per-profile
`config.yaml` via `oneplusn upgrade`.

## Symptoms

1. **Cron output:** memory-cleanup returns "[SILENT] / nothing to optimize" even on
   a profile whose `MEMORY.md` clearly has content that should be retained/refined.
2. **Daemon log:** `~/.hindsight/profiles/<profile>.log` contains the traceback ending
   in:
   ```
   File ".../hindsight_api/engine/llm_wrapper.py", line 645, in __init__
       raise ValueError(f"Invalid LLM provider: {self.provider}. ...")
   ValueError: Invalid LLM provider: openai_compatible. Must be one of: openai, groq,
   ollama, ollama-cloud, gemini, anthropic, lmstudio, llamacpp, vertexai, openai-codex,
   claude-code, mock, none, minimax, deepseek, litellm, litellmrouter, bedrock,
   volcano, openrouter, requesty, zai, opencode-go, atlas, fireworks, nous
   ```
3. **Stale lock file:** `~/.hindsight/profiles/<profile>.lock` (size 0) sits next to
   the log and must be cleaned up before retrying, otherwise HindsightEmbedded
   reuses the dead daemon.
4. **No pg0 instance:** `~/.pg0/instances/hindsight-embed-<profile>/` does not exist
   (compare with profiles whose hindsight is working — e.g. manager may show a
   directory tree even if its own startup also failed downstream).
5. **WAL hint:** if the daemon partially started before failing, you'll see a
   `winloop` / asyncio / huggingface_hub "client closed" error in the log as a
   secondary symptom — that's the LLM call being aborted because the engine never
   finished initializing.

## Detection (cheap, runs from cron)

```bash
# Is hindsight broken for this profile?
LOG="$HOME/.hindsight/profiles/<profile>.log"
if [ -f "$LOG" ] && grep -q "Invalid LLM provider" "$LOG"; then
    echo "HINDSIGHT_BROKEN: $(grep -m1 'Invalid LLM provider' "$LOG")"
    echo "Fix path: see references/hindsight-config.md"
fi
```

The cron should **not** attempt to fix the global config from inside an employee
session — that's a boss-level decision affecting all profiles. The right cron
behavior is:
1. Skip the optimization step.
2. Append a one-line breadcrumb to `<profile>/memories/MEMORY.md` with the
   diagnosis + fix path.
3. Emit the breadcrumb in the cron output so the boss sees it on the next
   daily report.

## Repair (boss-level, do once)

1. **Edit `~/AppData/Local/hermes/hindsight/config.json`** to use a valid provider
   name. (This is the Hermes install root's `hindsight/config.json`, NOT
   `~/.hermes/hindsight/config.json` — the latter does not exist on this host.
   Confirmed against the live filesystem on 2026-07-14.) The boss's MiniMax CN
   setup (`https://api.minimaxi.com/v1`) has two clean choices:

   **Option A — `litellm`** (generic openai_compatible shim, broadest compatibility):
   ```json
   {
     "mode": "local_embedded",
     "llm_provider": "litellm",
     "llm_base_url": "https://api.minimaxi.com/v1",
     "llm_model": "MiniMax-M3",
     "bank_id": "hermes",
     "recall_budget": "mid",
     "timeout": 120,
     "idle_timeout": 300
   }
   ```

   **Option B — `minimax` provider with explicit base_url override**:
   ```json
   {
     "mode": "local_embedded",
     "llm_provider": "minimax",
     "llm_base_url": "https://api.minimaxi.com/v1",  // overrides default api.minimax.io
     "llm_model": "MiniMax-M3",
     "bank_id": "hermes",
     "recall_budget": "mid",
     "timeout": 120,
     "idle_timeout": 300
   }
   ```
   ⚠️ Without the explicit `llm_base_url` override, `minimax` defaults to
   `https://api.minimax.io/v1` (international endpoint) — auth will fail against
   the CN endpoint.

2. **Ensure the API key env var exists.** Per the README, the LLM key is read from
   `HINDSIGHT_LLM_API_KEY` in `~/.hermes/.env` (NOT `HINDSIGHT_API_KEY`, which is
   for cloud mode). For MiniMax CN, this should be the same value as
   `MINIMAX_CN_API_KEY`:
   ```bash
   grep -q '^HINDSIGHT_LLM_API_KEY=' ~/.hermes/.env || \
       echo "HINDSIGHT_LLM_API_KEY=$MINIMAX_CN_API_KEY" >> ~/.hermes/.env
   ```

3. **Clean up daemon residue from failed startups:**
   ```bash
   rm -f ~/.hindsight/profiles/*.lock
   rm -f  ~/.hindsight/profiles/*.log       # optional; the next start will rewrite
   ```

4. **Verify the daemon actually starts and a bank is created:**
   ```bash
   python -c "
   from hindsight import HindsightEmbedded
   c = HindsightEmbedded(
       profile='<profile>',
       llm_provider='litellm',
       llm_api_key='<key>',
       llm_model='MiniMax-M3',
       llm_base_url='https://api.minimaxi.com/v1',
       idle_timeout=300,
       log_level='warning',
   )
   print('version:', c.get_version())   # should return within ~30s
   c.close()
   "
   # Then check the bank exists:
   python -c "
   from hindsight import HindsightEmbedded
   c = HindsightEmbedded(profile='<profile>', llm_provider='litellm',
                         llm_api_key='<key>', llm_model='MiniMax-M3',
                         llm_base_url='https://api.minimaxi.com/v1')
   print('banks:', c.list_banks())
   "
   ```
   First call spins up the daemon + downloads embedding models + initializes
   pg0 — expect **30-90 seconds** the first time. Subsequent calls are sub-second.

5. **Refresh per-profile `config.yaml`** so the `memory.provider=hindsight`
   declaration is no longer aspirational:
   ```bash
   oneplusn upgrade --work-dir <team> --all --modules hindsight
   ```
   This rewrites each agent's `config.yaml` memory block from the (now-correct)
   global config and updates the `memory_provider` field in `handoff.yaml`.

6. **Confirm by re-running the memory-cleanup cron.** Next 21:00 tick should
   see the daemon start cleanly, retain current `MEMORY.md` content into the
   bank, and (optionally) `reflect()` to synthesize — instead of emitting
   "nothing to optimize."

## Why this hit the reviewer profile specifically (2026-07-13)

The first-ever `oneplusn-rev-memory-cleanup` tick fired at 21:00 on 2026-07-13.
The cron tried to spin up `HindsightEmbedded(profile='handsome_company_reviewer',
...)` to exercise the "hindsight optimization" half of its prompt. The daemon
refused with the `Invalid LLM provider: openai_compatible` error. The cron
cleaned up the residual lock/log, appended a breadcrumb to `MEMORY.md`, and
reported the diagnosis in its stdout. Net result: zero data was lost (no
old memories existed to archive anyway — profile was 3 days old), but the
optimization half of the task silently no-oped.

The manager profile's log shows the same daemon-init failure pattern, so this
is a global config issue, not a per-profile one. Fix once at the boss level.

## See Also

- `plugins/memory/hindsight/README.md` — plugin docs (note: README is stale on
  the `openai_compatible` provider name; daemon behavior is authoritative).
- `scripts/upgrade_agent.py` — the `oneplusn upgrade --modules hindsight`
  path that refreshes per-profile `config.yaml` memory block.
- Known Fix #10 in `SKILL.md` — the skill-level summary of this issue.