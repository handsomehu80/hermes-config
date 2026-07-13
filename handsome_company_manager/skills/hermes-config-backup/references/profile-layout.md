# Hermes Profile Directory Anatomy

A Hermes profile lives at `~/.hermes/profiles/<name>/` (Linux/macOS) or `%LOCALAPPDATA%\hermes\profiles\<name>\` (Windows). Each profile is a self-contained agent configuration: persona, skills, cron jobs, channel routing, memories. Below is the canonical layout as observed on real profiles, annotated **DURABLE** (back this up) vs **TRANSIENT** (regenerable, exclude from backup).

## Top-Level Files

| File | Type | Notes |
|---|---|---|
| `config.yaml` | DURABLE | Main agent config. `api_key` fields are usually empty strings — secrets go in `.env`. |
| `SOUL.md` | DURABLE | Role/persona definition. Custom system prompt. |
| `channel_directory.json` | DURABLE | Chat channel routing (Telegram, Discord, WeChat, etc.). |
| `memories/` | DURABLE | User profile + durable memory bank. |
| `cron/jobs.json` | DURABLE | Cron schedule definitions (one JSON per job). |
| `skills/` | DURABLE (filtered) | Custom-installed skills only. See `.bundled_manifest` filter below. |
| `.env` | **EXCLUDE** | API keys, OAuth tokens. **Never commit.** |
| `auth.lock`, `gateway.lock`, `gateway.pid` | **EXCLUDE** | Runtime lock files. |
| `state.db`, `state.db-shm`, `state.db-wal` | **EXCLUDE** | Runtime state database (conversations, session metadata). |
| `gateway_state.json` | **EXCLUDE** | Runtime gateway state. |
| `channel_directory.json.lock` | **EXCLUDE** | Runtime lock. |
| `cache/`, `audio_cache/`, `image_cache/`, `logs/`, `sessions/`, `plans/`, `workspace/` | **EXCLUDE** | Regenerable caches and transient state. |
| `gateway-service/`, `home/`, `pairing/`, `weixin/` | **EXCLUDE** | Runtime/pairing state, possibly creds in `weixin/accounts/`. |
| `models_dev_cache.json` | **EXCLUDE** | Model metadata cache. |
| `pairing/` | **EXCLUDE** | OAuth pairing state. |
| `skins/` | DURABLE (empty usually) | UI skins — usually empty; back it up if populated. |
| `hooks/` | DURABLE (empty usually) | Custom shell hooks — back it up if populated. |
| `audio_cache/`, `image_cache/` | **EXCLUDE** | TTS/image generation caches. |

## `memories/` — What's Here

| File | Type | Notes |
|---|---|---|
| `USER.md` | DURABLE | User profile (preferences, environment, stable facts). |
| `MEMORY.md` | DURABLE | Active memory bank (durable facts). Updated frequently. |
| `MEMORY_ARCHIVE.md` | DURABLE | Archived entries from 30-day cleanup cron. Header marks archive cutoff. |

All three files are safe to commit — they contain user-curated knowledge, no secrets.

## `cron/` — What's Here

| File | Type | Notes |
|---|---|---|
| `jobs.json` | DURABLE | All cron job definitions (one JSON document, jobs array). |
| `.tick.lock` | **EXCLUDE** | Lock file held while a tick is being processed. |
| `output/` | **EXCLUDE** | Per-job runtime output directory (one subdir per job ID). |

`jobs.json` is safe to commit but **review for secrets first** — if a job's `script` or `prompt` references an API key inline, sanitize it.

## `skills/` — Custom vs Bundled

`skills/` contains both bundled skills (shipped with Hermes, reinstallable from upstream) and user-installed custom skills. **Only the custom ones should be backed up.**

The `skills/.bundled_manifest` file lists every skill that came with the bundle as `name:hash` lines. To get the set of custom skills:

```python
from pathlib import Path
manifest = Path('<profile>/skills/.bundled_manifest').read_text()
bundled = {line.split(':')[0] for line in manifest.splitlines() if ':' in line}
all_skills = {d.name for d in Path('<profile>/skills').iterdir() if d.is_dir() and not d.name.startswith('.')}
custom = sorted(all_skills - bundled)
```

### Skill internal files to exclude

Even for custom skills, the following metadata files are regenerable and should be excluded:

- `skills/.usage.json` — usage tracking
- `skills/.usage.json.lock` — lock
- `skills/.bundled_manifest` — bundled skills list (filter input, not backup data)
- `skills/.curator_state` — curator bookkeeping
- `skills/.curator_backups/` — curator's own backups
- `skills/.archive/` — archived skills
- `skills/.hub/` — skill hub cache

## Canonical `.gitignore` Template

Use this as the starting `.gitignore` for a new profile backup directory. It's the consolidated convention observed on real backups.

```gitignore
# Sensitive files - NEVER commit
.env
.env.*
*.key
*.pem
*.p12
*.pfx
secrets.*
auth.lock
*.lock
gateway.lock
gateway.pid
state.db
state.db-shm
state.db-wal

# Transient caches and runtime state
audio_cache/
image_cache/
cache/
logs/
sessions/
plans/
workspace/
gateway-service/
home/
pairing/
weixin/
memory_sessions/

# Large regenerable caches
models_dev_cache.json
*.cache

# Skill metadata (regenerable)
skills/.usage.json
skills/.usage.json.lock
skills/.bundled_manifest
skills/.curator_state
skills/.curator_backups/
skills/.archive/
skills/.hub/

# Prompt snapshot (regenerable)
.skills_prompt_snapshot.json

# Cron tick lock
cron/.tick.lock
cron/output/

# OS / editor cruft
.DS_Store
Thumbs.db
desktop.ini
*.swp
*.swo
*~
.idea/
.vscode/
__pycache__/
*.pyc
```

## Sizing Expectations

A typical profile backup (custom skills + memories + cron) weighs **~5-20 MB**. If yours is dramatically larger, you likely backed up cached bundles or runtime state. Run:

```bash
cd /tmp/hermes-backup/hermes-config/<profile>
du -sh */ | sort -h | tail -10
```

The biggest entry should usually be `skills/` (~5-15 MB for a handful of custom skills). Anything larger, or entries like `cache/`, `logs/`, `sessions/` appearing at all, indicates a sync script bug.