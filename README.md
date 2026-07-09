# hermes-config

GitHub backups of Hermes agent configuration, organized one folder per profile.

## Layout

```
hermes-config/
├── handsome_company_manager/   ← active Hermes profile: 公司老板 / 1+N 数字员工
│   ├── config.yaml             (main agent config; secrets via env vars, never inlined)
│   ├── SOUL.md                 (role/persona definition)
│   ├── channel_directory.json  (chat channel routing)
│   ├── memories/               (USER.md + MEMORY.md)
│   ├── cron/jobs.json          (cron job definitions)
│   └── skills/                 (custom skills, all categories)
└── ...
```

## What's deliberately excluded

Per `.gitignore` inside each profile folder:

- `.env`, `*.key`, `*.pem` — secrets
- `state.db*` — session database
- `auth.lock`, `gateway.lock`, `gateway.pid` — runtime locks
- `audio_cache/`, `image_cache/`, `cache/`, `logs/`, `sessions/`, `plans/` — transient state
- `models_dev_cache.json` — large regenerable cache
- `.skills_prompt_snapshot.json` — prompt cache
- `skills/.usage.json*`, `.bundled_manifest`, `.curator_state`, `.archive/`, `.curator_backups/`, `.hub/` — skill curator metadata (regenerates)
- `cron/.tick.lock` — cron runtime lock

## Restoring a profile

This repo only stores *configuration*, not secrets. To restore on a fresh box:

1. Clone the repo
2. Recreate the `~/.hermes/profiles/<profile_name>/` tree from the cloned folder
3. Provide a fresh `.env` with the secrets referenced in `config.yaml`
4. Restart the Hermes gateway

Secrets referenced by env vars (see `config.yaml` → `secrets:` section) must be supplied out-of-band.