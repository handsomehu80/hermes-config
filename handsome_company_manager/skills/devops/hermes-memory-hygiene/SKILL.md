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

Every Hermes profile has its own memory store under the active Hermes home:
```
<HERMES_HOME>/profiles/<profile>/memories/
├── MEMORY.md          # active operational memory (≤ memory_char_limit, default 2200)
├── MEMORY_ARCHIVE.md  # rotated-out facts (30+ day old or session-finished)
└── USER.md            # timeless user profile (preferences, style, communication)
```

Layout differs by install: Linux/legacy installs commonly use `~/.hermes`; current Windows named-profile installs commonly use `%LOCALAPPDATA%/hermes` (for example `C:/Users/<user>/AppData/Local/hermes`). Do not hardcode `~/.hermes` on Windows. Resolve `HERMES_HOME` first, then probe both layouts. The bundled `scripts/hindsight_reflect.py` follows this search order.

- `MEMORY.md` is injected into the agent's context as a "memory" prompt on every turn. Keep it lean.
- `USER.md` is loaded separately as user-profile data. **Do not archive based on mtime alone** — it stores timeless facts.
- `MEMORY_ARCHIVE.md` is the destination for facts that are no longer current but might be needed for archaeology. Each section should start with a `## YYYY-MM-DD — title` heading.

The `memory()` tool is the normal write path, but **it is not always available** — in cron contexts it often returns "Memory is not available. It may be disabled in config or this environment." When that happens, fall back to direct file edits with `read_file` / `patch` / `write_file`. The on-disk files are the durable source of truth either way.

## 30-day archive workflow

1. **Compute the cutoff**: today minus 30 days (e.g. 2026-07-10 → cutoff 2026-06-10).
2. **Survey `MEMORY.md` line by line.** Entries are separated by `§` and may carry an internal date in parentheses (e.g. `1+N 数字员工集成(2026-07-08)`). If no internal date is present, treat the entry as current environment state — **do not** archive based on file mtime.
   - **Reconcile facts directly re-verified during this run.** A cleanup often inspects current config, credential-presence state, or profile identity as part of pre-flight. If that direct evidence contradicts an active dated snapshot, correct the active entry and refresh its internal date; do not preserve a known-false fact merely because it is still inside the 30-day window. Keep the correction narrow and evidence-backed. Example: `HF_TOKEN absent` must become `present but commented out (inactive)` when the `.env` state detector proves that shape. Reflect the correction in the archive header and housekeeping summary.
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

### Housekeeping section structure pitfall (learned 2026-07-16)

The `MEMORY_ARCHIVE.md` housekeeping block grows by appending one `- YYYY-MM-DD — ...` bullet per cron run. **Patch edits must insert at the top level (sibling to prior dates), not as a sub-bullet of the previous date.** A real failure observed: the 7-15 entry was inherited as a sub-bullet under 7-14 (a previous patch matched a too-narrow `old_string` and captured the 7-14 bullet as context), and then 7-16 nested inside 7-15 — a 3-level nesting that is structurally wrong.

**Prevention:** when appending a new run entry, anchor `old_string` to the `## Archive housekeeping` heading + the first `- Created:` line, NOT to the last date's bullet. Verify after edit that all date entries are siblings at the same indentation level (no extra leading spaces before `- YYYY-`). If a nesting bug is found, rewrite the entire `## Archive housekeeping` block at once with all entries at the same level. Run `python scripts/verify_housekeeping_structure.py <profile>` for an automated check (exit code 0 = siblings OK, 1 = nesting issues found with line numbers).

#### `patch` tool fuzzy matching silently truncates multi-line indented replacements (learned 2026-07-30, PM memory-cleanup cron run)

The `patch(mode='replace')` tool uses 9-strategy fuzzy matching — when your `old_string` is a 20-line block but contains a uniquely-matching sub-string (e.g., one sub-bullet's full text), the matcher may match ONLY that sub-string and replace just that one line, silently leaving the rest of your intended replacement unapplied. Real case (2026-07-30): I tried to insert a new top-level `- 2026-07-30` housekeeping entry by anchoring `old_string` to the unique "Markdown archive remains the authoritative store. Will keep skipping reflect()..." sub-bullet of the 7-29 entry and replacing it with itself + blank line + new entry (17 more lines). The patch tool returned `success` and modified the file, but inspection showed only ONE sub-bullet's text inside the new entry's body was updated. The new `- 2026-07-30` entry itself was wrongly indented (2-space prefix) — exactly the nesting pitfall above, but introduced via a different mechanism.

**Why this happens**: the patch tool's fuzzy matcher finds the *smallest* unique match first. If any sub-string of your `old_string` is unique in the file, the matcher uses that sub-string as the match and replaces just the corresponding region — not the entire `old_string`. The `success` result + the small diff in tool output both suggest "all good", but only the unique sub-string region was actually touched.

**Symptoms when this has fired**:
- `patch` returns `success` with `files_modified: 1`, but the visible diff in the tool output is much smaller than your intended change (e.g., 1 line changed when you expected 17).
- Manual inspection shows the wrongly-indented block is still in the file (the indented content you tried to fix is still indented), but a single unrelated sub-bullet's text was updated.
- `verify_housekeeping_structure.py` exits non-zero because the nesting bug is still present.

**Recovery** when this fires:
1. **Detection**: after every `patch` call whose `old_string` contains a multi-line block (≥5 lines) with unique-looking text inside it, immediately read back the affected section (`read_file offset=N limit=M` or `pathlib.read_text()`) and confirm the entire intended change landed. Do NOT trust the `success` result alone.
2. **Recovery via `execute_code` + `pathlib`**:
   ```python
   from pathlib import Path
   p = Path("<file_path>")
   content = p.read_text(encoding='utf-8')
   lines = content.splitlines()
   # Strip N leading spaces from affected line indices (0-indexed, inclusive)
   for i in range(start, end):
       if lines[i].startswith(' ' * N):
           lines[i] = lines[i][N:]
   new_content = '\n'.join(lines)
   if content.endswith('\n') and not new_content.endswith('\n'):
       new_content += '\n'
   p.write_text(new_content, encoding='utf-8')
   ```
   This is the only reliable path when `patch` fuzzy matching has gone wrong. `patch` is NOT safe to "fix with another patch" — the same fuzzy matching issue will recur on the recovery edit.

3. **Prevention** — three patterns that survive the fuzzy matcher:
   - **Atomic via `execute_code`**: do the full read/modify/write in one Python block. Bypasses `patch` entirely.
   - **Split into small patches**: do one short unique-anchor patch per insertion (≤3 lines per `old_string`). Each patch's `old_string` is small enough that fuzzy matching can't truncate it meaningfully.
   - **`write_file` to a temp file then rename**: write the corrected file from scratch, verify the diff matches your intent, then move it into place.

The "anchor to `## Archive housekeeping` heading + first `- Created:` line" advice above works for SIMPLE patches but is not robust against fuzzy matching when the new entry has unique-looking text in its sub-bullets. Combine with `verify_housekeeping_structure.py` immediately after every patch — that's the only reliable verification signal.

## Pre-flight housekeeping (always do before the archive sweep)

These are tiny, fast checks that catch problems BEFORE they cascade into the archive decision. Skipping them has caused silent zombie states in past runs.

1. **Stale `memories/*.lock` cleanup.** The `memory()` tool writes 0-byte `<file>.lock` siblings on every edit; if a previous tool call crashed mid-write, the lock stays. Check:
   ```python
   from pathlib import Path
   from datetime import datetime
   mem_dir = Path("~/.hermes/profiles/<profile>/memories").expanduser()
   for lock in mem_dir.glob("*.lock"):
       st = lock.stat()
       age_days = (datetime.now() - datetime.fromtimestamp(st.st_mtime)).days
       if st.st_size == 0 and age_days >= 1:
           lock.unlink()  # safe — 0 bytes means no actual lock content
   ```
   This is **distinct** from `~/.hindsight/profiles/*.lock` (covered later under the reflect pitfalls). Do not confuse the two — `memories/*.lock` = markdown write lock, `~/.hindsight/profiles/*.lock` = Hindsight daemon lock.

2. **Gateway liveness sanity check.** Before declaring a Hindsight skip, confirm the Gateway is actually alive so the skip can't be misattributed to "gateway down":
   ```python
   from pathlib import Path
   from datetime import datetime
   log = Path("~/.hermes/profiles/<profile>/logs/gateway.log").expanduser()
   if log.exists():
       last_mtime = datetime.fromtimestamp(log.stat().st_mtime)
       age_minutes = (datetime.now() - last_mtime).total_seconds() / 60
       # Expect fresh activity within last 60 minutes if cron is healthy
   ```
   Last `Cron ticker started (interval=60s)` line should be within the last 24h. If the Gateway log is stale, that's a separate issue from the Hindsight reflect failure — record it but don't conflate the two in housekeeping.

3. **Distinguish "gateway.log silent" from "gateway dead" (added 2026-07-19).** A stale `gateway.log` does NOT prove the gateway is dead — the cron ticker may simply have stopped writing to that file (INFO-level logging dropped, log rotation, or the cron handler redirected). Real observed case: on the 2026-07-19 run, `gateway.log` mtime was **~42 hours stale** (was ~18h on 7-18, has been quietly deteriorating for several days), yet the cron was firing normally — this very session was started BY a cron tick. The signal that disambiguates is `agent.log` (and to a lesser extent `errors.log`), both of which sit beside `gateway.log` and are written by the agent loop, not the cron ticker:
   ```python
   from pathlib import Path
   from datetime import datetime
   logs = Path("~/.hermes/profiles/<profile>/logs").expanduser()
   for name in ("agent.log", "errors.log"):
       p = logs / name
       if p.exists():
           age = (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).total_seconds() / 60
           print(f"  {name:14s} mtime age: {age:.0f}m")
   ```
   **Tri-state diagnosis:**
   - `gateway.log` stale, `agent.log` **fresh** → gateway is alive; `gateway.log` is just not being written to anymore (logging config change or rotation). This is a logging artifact, not a gateway-down condition. Record the staleness in housekeeping but do NOT attribute it to the reflect failure or to any cron-pipeline bug.
   - `gateway.log` stale AND `agent.log` stale → real gateway-down issue. Investigate `errors.log`, `gateway-exit-diag.log`, and the scheduled task that should be restarting it.
   - `gateway.log` fresh → all good, no follow-up needed.
   The "positive change vs the 7-17 run which had a stale gateway log" wording in earlier housekeeping assumed `gateway.log` was authoritative; that assumption has been invalidated by the 2026-07-19 observation. Always check `agent.log` as the secondary signal before declaring gateway health.

## Hindsight reflect (advanced organization)

When `memory.provider: hindsight` is set in the active profile's `config.yaml` and the bank is reachable, call `reflect()` to consolidate stored memories into a fresh mental model. This is Hindsight's optimization capability.

### Detect

**Source of truth is the profile `config.yaml`, NOT `~/.hermes/hindsight/config.json`.** The Hindsight Python constructor reads `llm_provider` / `llm_model` / `llm_api_key` / `llm_base_url` from its own kwargs + env vars, so the global `config.json` is just one of several config paths and may be absent on a freshly-migrated profile.

```yaml
# ~/.hermes/profiles/<profile>/config.yaml — AUTHORITATIVE
memory:
  memory_enabled: true
  provider: hindsight
```

```json
// ~/.hermes/hindsight/config.json — OPTIONAL
// Present on many profiles; ABSENT on freshly-migrated ones.
// If missing, the Python constructor's kwargs/env vars still drive everything.
{
  "mode": "local_embedded",
  "bank_id": "hermes",
  "llm_provider": "minimax",
  "llm_model": "MiniMax-M3",
  "llm_base_url": "https://api.minimaxi.com/v1"
}
```

**Detection recipe** — check profile yaml first; only check the json if you need to verify defaults:
```python
import yaml
cfg = yaml.safe_load(Path("~/.hermes/profiles/<profile>/config.yaml").expanduser().read_text())
hindsight_enabled = cfg.get("memory", {}).get("provider") == "hindsight"
# If False: skip the entire reflect section — Hindsight isn't wired up.
```

### Try
```python
# Pre-flight: confirm we're running under the venv python that has hindsight installed.
# Bare `python` from PATH will return exit 3 ("No module named 'hindsight'") on
# Windows named-profile installs because hindsight lives only in the venv at
# <hermes-agent>/venv/Lib/site-packages/hindsight/. Detect this BEFORE doing
# any other work — if hindsight isn't importable from sys.executable, the import
# failure masks the real HF-blocker signature (cross-encoder / pg0 / port).
import sys, importlib.util
if not importlib.util.find_spec("hindsight"):
    print(f"ERROR: hindsight not importable from sys.executable={sys.executable}", file=sys.stderr)
    print("  On Windows named-profile installs, hindsight lives only in the venv.", file=sys.stderr)
    print("  Re-run with the venv python:", file=sys.stderr)
    print("    <hermes-agent>/venv/Scripts/python.exe scripts/hindsight_reflect.py <profile>", file=sys.stderr)
    sys.exit(3)

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
- **`hindsight` lives ONLY in the Hermes venv on Windows named-profile installs** (learned 2026-07-27, PM cron run). The package is at `<hermes-agent>/venv/Lib/site-packages/hindsight/`, NOT in any system site-packages. Bare `python` from PATH returns exit 3 with `ERROR: HindsightEmbedded not importable: No module named 'hindsight'` — which **short-circuits BEFORE the daemon starts and masks the real HF-blocker signature** (cross-encoder / pg0 / port). If you see exit 3, first check `sys.executable` — if it doesn't end in `venv/`, you're running the wrong interpreter. **Always invoke with the venv python explicitly:**
  ```bash
  # Windows (git-bash / MSYS):
  "$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe" scripts/hindsight_reflect.py <profile>
  # Or absolute path:
  "C:/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" scripts/hindsight_reflect.py <profile>
  # Linux/macOS:
  "$HOME/.local/share/hermes/hermes-agent/venv/bin/python" scripts/hindsight_reflect.py <profile>
  ```
  The `scripts/hindsight_reflect.py` runner now auto-detects this and re-execs to the venv python when found (look for `re-exec'ing to <venv python>` in stderr). If the re-exec fails too, the venv itself may be broken — re-install with `uv pip install --python <venv> hindsight-all`.
- **Missing `~/.hermes/hindsight/config.json` is NOT a failure signal.** It is one of several config paths; the Python constructor reads provider/model/key/api_base from kwargs + env vars (`HINDSIGHT_API_LLM_*`). If you see `config.json` absent on a freshly-migrated profile, do NOT panic — the daemon still tries to start. The actual failure modes are the same regardless: cross-encoder download, embedded pg0 init, env vars. The `config.json` only matters when the daemon's defaults need to differ from your constructor kwargs; if you're passing everything explicitly, the json file is redundant.
- **Stale `.lock` files** in `~/.hindsight/profiles/` block daemon start. Remove them before retrying. (Distinct from `~/.hermes/profiles/<profile>/memories/*.lock` — see Pre-flight housekeeping §1.)
- **A failed daemon attempt can leave a fresh 0-byte lock too.** Do post-attempt cleanup instead of waiting for the next cron: first probe the profile's configured Hindsight port (default embedded port is often `9807`). Only when the port is not listening and the lock is 0 bytes should you remove it. Never delete a non-empty lock or a lock belonging to a live listener. Record the port verdict and removal in housekeeping.
- **Hindsight logs are append-only across attempts; attribute errors by timestamp.** Before describing the current failure, record the attempt start time and inspect only log lines written at or after that time. A full-file search may find an old `[WinError 10054]` or cross-encoder traceback and falsely present it as today's signature. Report two layers when needed: (a) `current-run signature` from timestamp-matched lines/runner output, and (b) `retained historical signature` as context. Never collapse historical evidence into a current-run claim.
- **Failure signatures can evolve informatively between runs — compare against the last attempt, not just the historical baseline** (learned 2026-07-28, PM run #13). A long stretch of "same signature as yesterday" housekeeping entries can lull you into hopelessness, but each failed `reflect()` actually crosses some environmental gates before dying. A NEW warning that wasn't in the prior run's log is diagnostic gold — it means the daemon got **farther** than before. Real case: runs #1–#12 died during cross-encoder HF HEAD requests with `[WinError 10054]` / `Cannot send a request, as the client has been closed`; run #13 surfaced a new line never seen before — `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN ...` — proving the daemon now reaches the cross-encoder download phase, where it stalls on unauthenticated rate-limit + connection-reset. The new signature refines remedy selection: option (a) `set HF_TOKEN=*** becomes the most direct match instead of being one of three equally-plausible options. **Required housekeeping addition when a new signature appears** (insert as a sub-bullet under the date entry): a "Diagnostic implication" / "what changed vs prior run" line that (1) names the new warning, (2) states what gate it implies the daemon now reaches, and (3) re-ranks the (a/b/c) remediation options accordingly. **Generalization**: when the housekeeping entry would otherwise read "Xth consecutive same-signature run", first diff the current-run log lines against the **immediately prior** run's last 1-2KB of log content (use `Path.read_bytes()` offset trick or `tail -2KB` of the log). New lines = progress; identical lines = stuck. This converts a routine skip from "yet another failed attempt" into actual signal that refines the boss-action recommendation.
- **Cross-encoder reranker download can fail after LLM init succeeds.** Hindsight's `local_embedded` mode pulls a CrossEncoder model from HuggingFace during `memory.initialize()`. On hosts with restricted/timeout-prone HF access, this fails with `RuntimeError: Cannot send a request, as the client has been closed.` (or any `httpx` "client closed" error in `cross_encoder.initialize()`). The provider override above is correct — that error is *past* LLM init. **Skip `reflect()` and fall back to markdown archive** for this cron. Do not retry in the same run; the fix is environmental (`HF_TOKEN` for higher rate limits, HF mirror, or `mode: local_external` / `cloud`).
- **Embedded PostgreSQL** (`pg0`) may fail to initialize on some Windows hosts with `PostgreSQLBackend is not initialized. Call initialize() first.`. If the log shows this, the bank is unreachable in the current cron — skip `reflect()` and rely on the markdown archive only. The fix is environmental (separate Hindsight container via `local_external`, or `cloud` mode), not something to retry.
- **Bank may be empty** for a profile that has never used Hindsight. The daemon will start fine, but `reflect()` returns a degenerate result. Check `list_memories` first and short-circuit.
- **Daemon startup is slow** (60–180s on Windows). Set `idle_timeout=30` so the daemon exits promptly when done. The embedded client blocks on a port binding, so the parent process won't return until the daemon comes up.
- **Env vars are read by the daemon subprocess from its own environment**, not just the config dict you pass. Always set `HINDSIGHT_API_LLM_PROVIDER` / `HINDSIGHT_API_LLM_MODEL` / `HINDSIGHT_API_LLM_API_KEY` / `HINDSIGHT_API_LLM_BASE_URL` in the parent process env **before** constructing `HindsightEmbedded`.
- **General skip rule for `reflect()`**: if the daemon fails to start or the bank is unreachable for *any* environmental reason (network, model download, embedded DB, port binding, missing creds), record the failure signature in `MEMORY_ARCHIVE.md` housekeeping and stop. The markdown archive is the durable source of truth — a skipped `reflect()` does not lose data, only defers the optimization step.
- **Canonical script path is the skill bundle, not the profile's `scripts/` directory** (learned 2026-07-29, PM memory-cleanup cron run). The bundled runner lives at `<hermes-home>/profiles/<active-profile>/skills/devops/hermes-memory-hygiene/scripts/hindsight_reflect.py` (and `verify_housekeeping_structure.py` next to it). It does NOT live at `~/.hermes/profiles/<profile>/scripts/`, `~/AppData/Local/hermes/profiles/<profile>/scripts/`, `~/AppData/Local/hermes/scripts/`, or `~/AppData/Local/hermes/hindsight/` — those paths have been claimed by past housekeeping entries and verified-empty. The skill's "Files" section lists the canonical paths; never invent a `~/.hermes/profiles/<profile>/scripts/hindsight_reflect.py` and never claim it ran from such a path. When invoking, use the **absolute path** or the path relative to the skill bundle's `scripts/` directory. If you find yourself writing `hindsight_reflect.py <profile>` in a command line, resolve the full path first: `python <hermes-home>/profiles/<active-profile>/skills/devops/hermes-memory-hygiene/scripts/hindsight_reflect.py <profile>`.
- **Verify the canonical path with an explicit probe before declaring a script "absent on disk"** (learned 2026-07-30, PM memory-cleanup cron run). The 2026-07-29 housekeeping entry claimed `hindsight_reflect.py` is "not on disk" because the LLM author checked only non-canonical paths (`~/.hermes/profiles/<name>/scripts/`, `~/AppData/Local/hermes/hindsight/`, venv). The canonical path at `<hermes-home>/profiles/<active-profile>/skills/devops/hermes-memory-hygiene/scripts/hindsight_reflect.py` was never probed. Verified on 2026-07-30: the script DOES exist at the canonical path (9960B). The 7-29 "narrative drift" accusation was itself wrong. Rule: when asserting that a script the skill names is absent, run `Path("<canonical_path>").exists()` and `Path("<canonical_path>").stat().st_size` and record both results in housekeeping. If `True`, the prior claim was false — correct it with a self-correction note (don't silently overwrite). If `False`, the claim is verified and you can proceed with the alternative-path hypothesis. Don't conflate "I checked three wrong paths and didn't find it" with "the file doesn't exist anywhere."
- **In-process `HindsightEmbedded()` is a valid alternative when the script wrapper is missing or auto-reexec fails** (verified 2026-07-29, PM memory-cleanup cron run). The script is a thin wrapper around `HindsightEmbedded(profile, llm_provider, llm_api_key, llm_model, llm_base_url, idle_timeout, log_level)` — the LLM itself can `import hindsight; he = hindsight.HindsightEmbedded(...)` directly without needing the script on disk. This is the canonical fallback when (a) the skill bundle is not installed at the resolver's expected path, (b) the cron fires inside an LLM process that has the venv python in `sys.executable` already, or (c) the script's auto-reexec to the venv python fails. The skip guidance in this skill still applies — if the daemon fails after 60–180s, fall back to the markdown archive. The advantage of the in-process path is no argv-serialization cost and no `os.execv` race; the disadvantage is the LLM's `sys.executable` must already be the venv python (verify with `python -c "import sys; assert 'venv' in sys.executable"` before relying on it).
- **Long skip runs (≥7 consecutive same-signature days) require a re-ranked remediation table, not a repeat "skip per guidance" entry** (learned 2026-07-29, PM memory-cleanup cron run, observed N=14). After 7+ consecutive days of "skip per skill guidance", the housekeeping entry has TWO jobs: (1) re-rank the (a/b/c) trio from the 7-13 pitfall based on the latest log mutation, and (2) cite the specific new log line(s) that didn't appear in earlier runs. The 7-28 PM run surfaced a NEW line — `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads` — that did not appear in any of the 7-21..7-27 runs. This single line re-ranks option (a) `set HF_TOKEN=*** from "one of three equally-plausible remedies" to "the most direct match", because the new warning text essentially names the missing token. The re-ranking belongs in the housekeeping entry as a "Diagnostic implication" sub-bullet. The pitfall above ("Failure signatures can evolve informatively") already requires the diff against the immediately prior run; the long-run version adds the obligation to keep re-ranking as the log mutates. Don't let a long skip run devolve into identical "skip per guidance" entries — each new log line is diagnostic gold.
- **Before claiming prior LLM crons "fabricated" a script invocation, verify the script is genuinely absent from the canonical skill bundle path** (learned 2026-07-29, PM memory-cleanup cron run). Past housekeeping entries (7-22, 7-23, 7-28) describe invoking `hindsight_reflect.py handsome_company_manager` and report specific output ("Starting Daemon (handsome_company_manager @ :9807)" → "⏳ Waiting for daemon... (178s elapsed)" → "✗ Daemon Failed (Timeout)"). That output matches the script's actual runtime behavior, so the script WAS being invoked in those runs — the only drift was the path. The wrong inference is "previous LLM crons narrated the intent without executing it"; the right inference is "previous LLM crons used a non-canonical path that I cannot independently reproduce, but the outputs are consistent with the script running via absolute path or via the venv python + the in-process `HindsightEmbedded()` fallback." When asserting narrative drift, verify TWO things: (a) the script is absent from the canonical skill bundle path (i.e., `<hermes-home>/profiles/<active-profile>/skills/devops/hermes-memory-hygiene/scripts/hindsight_reflect.py`), AND (b) the output format cited in the prior entry is not present in the script's `print()` statements. If either check passes, the prior entry was likely genuine; if both fail, the prior entry can be flagged as narrative drift. Don't over-claim — past LLM crons are usually correct in their core assertions (daemon did fail, signature did match), only the implementation path may be mis-described.
- **Cross-profile `~/.hindsight/profiles/*.lock` mtime is a free liveness signal during pre-flight** (learned 2026-07-29, PM memory-cleanup cron run). When the active profile's `~/.hindsight/profiles/<your-profile>.lock` is absent and the daemon is down (port 9807 not listening), peek at the OTHER profiles' locks/last mtime to see if their cleanup cron is currently running. On 2026-07-29 13:05 UTC (the active PM cron tick), `~/.hindsight/profiles/handsome_company_developer.lock` was 0B with mtime 13:05:14 UTC and `dev.log` was 844B with mtime 13:05:44 UTC — i.e., the dev profile's cleanup cron was firing in parallel and had just failed. This is a useful cross-check: if multiple profiles are hitting the same daemon-startup failure at the same time, the cause is environmental (HF Hub, Windows socket behavior, etc.) rather than per-profile configuration. The `~/.hindsight/profiles/` directory is shared across all profiles on the host, so reads of file mtime are zero-cost. Filter the listing to identify the active profile (the one with the lock AND the log you've been studying) vs. neighbors (locks with different names). Neighbor profile failures are evidence the host environment is the cause, not an excuse to skip the active profile's housekeeping entry.

## Verification

- [ ] `MEMORY.md` contains no entries with an internal date before the cutoff
- [ ] `MEMORY_ARCHIVE.md` header records the latest run date and a one-line summary
- [ ] Housekeeping section at the bottom of `MEMORY_ARCHIVE.md` updated
- [ ] **All date entries in housekeeping are siblings at the same indentation level** (no nested `- YYYY-MM-DD` inside another date's bullet) — see Housekeeping structure pitfall above. Automated check: `python scripts/verify_housekeeping_structure.py <profile>`
- [ ] Pre-flight housekeeping ran: stale `memories/*.lock` files cleaned, Gateway log mtime checked, **and `agent.log` cross-checked** to disambiguate "log silent" from "gateway dead" (see Pre-flight §3)
- [ ] If Hindsight `reflect()` ran: `client.list_mental_models(bank_id="hermes")` shows a fresh entry
- [ ] If Hindsight `reflect()` skipped: housekeeping records (a) why skipped (failure signature or environmental gate), (b) what boss action items remain open, (c) when the previous actual Hindsight attempt was (log mtime)
- [ ] **Long skip runs (≥7 consecutive same-signature days)**: housekeeping entry contains a re-ranked (a/b/c) remediation table with the latest log mutation as the tie-breaker, AND a "Diagnostic implication" sub-bullet that names any new log line and what gate it implies the daemon now reaches. Don't let N≥7 entries devolve into identical "skip per guidance" text.
- [ ] **Cross-profile `~/.hindsight/profiles/*.lock` check**: during pre-flight, list the directory and note any neighbor profiles whose locks/logs have mtime within the last 5 minutes. Cross-profile simultaneous failures are evidence the host environment (HF Hub, WinError 10054, etc.) is the cause rather than per-profile configuration. Record the neighbor observation in housekeeping but don't use it as an excuse to skip the active profile's entry.
- [ ] Failure attribution is time-scoped: current-run signatures come from runner output or log lines at/after this attempt's start time; older appended log signatures are labeled historical context
- [ ] After a failed embedded-daemon attempt, any fresh 0-byte Hindsight lock was handled safely: verify the configured port is not listening before removal; otherwise leave it untouched
- [ ] Any active-memory fact contradicted by direct pre-flight evidence was corrected narrowly and its internal date refreshed; archive header/housekeeping describe the correction
- [ ] `USER.md` unchanged (only update on actual user-profile changes, not on mtime)

## HF_TOKEN state detection — distinguish absent vs commented vs empty

When reporting the `HF_TOKEN` remediation status in housekeeping, **don't say "absent" when the line is actually commented out or empty** — these three states imply different boss actions and conflating them wastes the boss's attention. Verification recipe (use on every Hindsight-skip housekeeping entry):

```python
from pathlib import Path
env = Path("~/.hermes/profiles/<profile>/.env").expanduser()
text = env.read_text(encoding='utf-8')
state = "absent"     # no HF_TOKEN=*** row at all
for line in text.splitlines():
    s = line.strip()
    if s.startswith("# HF_TOKEN"):
        state = "commented out"   # row present, prefix is '#'
        break
    if s.startswith("HF_TOKEN=***        val = s.split("=",1)[1].strip()
        state = "empty" if not val or val in ('""', "''") else "set"
        break
print(f"HF_TOKEN state: {state}")
```

Boss-action mapping:

| State | What boss has to do |
|---|---|
| `absent` | Add a new `HF_TOKEN=*** line |
| `commented out` | Uncomment the existing line **and** set a real value (two steps, easy to miss the second) |
| `empty` | Fill in the value on the existing line |
| `set` | Diagnose elsewhere — HF_TOKEN alone is not the blocker |

History from this skill's housekeeping: the 2026-07-11 .. 2026-07-17 entries all reported `HF_TOKEN` as "absent" / "NOT set". The 2026-07-18 run discovered the line is actually present-but-commented — a different shape than the entries had been implying. Future runs should classify before reporting.

## Files

- `references/hindsight-bank.md` — Hindsight config schema, full `llm_provider` list, env-var matrix, and log signatures for common failure modes
- `references/lock-file-cleanup.md` — the 3 distinct `.lock` families (`memories/*.lock` vs `~/.hindsight/profiles/*.lock`), detection recipe, housekeeping structure verification, gateway liveness vs Hindsight skip distinction
- `scripts/hindsight_reflect.py` — re-runnable `reflect()` runner. Loads the profile `.env`, overrides provider env vars, clears stale locks, starts the daemon, calls `reflect()`, and reports new vs existing mental models. Use instead of pasting the recipe above.
- `scripts/verify_housekeeping_structure.py` — reads `MEMORY_ARCHIVE.md`, locates the `## Archive housekeeping` section, and verifies all top-level date bullets are at the same indent level (siblings) with sub-bullets at exactly indent=2. Catches the nesting pitfall described above. Read-only — never modifies the file.

### Quick re-run

```bash
# Windows named-profile installs — use the venv python explicitly (hindsight
# lives only in <hermes-agent>/venv/Lib/site-packages/hindsight/):
"$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe" scripts/hindsight_reflect.py <profile>
"$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe" scripts/hindsight_reflect.py <profile> --query "Reorganize by topic"

# Linux/macOS:
"$HOME/.local/share/hermes/hermes-agent/venv/bin/python" scripts/hindsight_reflect.py <profile>

# Bare `python` may still work on legacy ~/.hermes installs where the package
# is reachable from PATH; on Windows named-profile installs it returns exit 3
# and the runner auto-re-execs to the venv python when found.
```

Exit codes: `0` = reflect ran (or bank was empty + correctly skipped), `1` = daemon failed to start (see `~/.hindsight/profiles/<profile>.log`), `2` = missing API key in profile `.env`, `3` = `hindsight` package not importable from the active Python. **Exit 3 on Windows named-profile installs almost always means "you ran bare `python`, but hindsight lives in the venv"** — the runner auto-detects this and re-execs to the venv python (look for `re-exec'ing to <venv python>` in stderr). If the re-exec still fails, the venv itself may be broken — re-install with `uv pip install --python <venv> hindsight-all`.
