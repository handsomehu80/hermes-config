---
name: hermes-setup-audit
description: "Audit and optimize a Hermes Agent install — diagnose config health, fix missing tools (browser, web search, image gen), and reach a productive working state. Use when user asks to 'check Hermes config', 'optimize Hermes', 'set up a new Hermes machine', or 'why is tool X not working'."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, audit, configuration, optimization, browser, playwright, tavily, diagnostics]
    related: [hermes-agent]
---

# Hermes Setup Audit

Playbook for taking a Hermes Agent install from "shipped" to "productive". Complement to the `hermes-agent` skill (which is the command reference). This skill is the workflow.

## When to Use

Triggers (load this skill):
- "Check Hermes configuration / config"
- "Optimize / tune Hermes setup"
- "Set up a new Hermes install"
- "Why is tool X not working" (browser, web search, image gen, etc.)
- "Make Hermes fully work" / "fix the warnings in hermes doctor"

Do NOT use:
- One-off CLI command lookups → use `hermes-agent` skill
- Single-tool config questions (e.g. "how to set Tavily") → use `hermes-agent` skill
- Gateway/messaging platform setup → use `hermes-agent` skill gateway section

## The 4-Command Diagnostic Combo

When auditing, run these **in parallel** in one round-trip. Each one shows a different facet of state; together they form a complete picture.

```bash
hermes doctor                  # health, advisories, external tools, tool availability
hermes status --all            # component status, auth providers, gateway, jobs, sessions
hermes config check            # env var gaps with arrows to which tools they unlock
hermes tools list              # toolset enable/disable per platform
```

After running, cross-reference ⚠ warnings to fixes using the gotchas below. Re-run after each fix to confirm.

## Common Gotchas

### Browser tool needs TWO installs (all platforms)

`hermes doctor` says "agent-browser not installed (run: npm install)" — misleading. You actually need:

```bash
npm install -g agent-browser
npx playwright install chromium
```

Only after BOTH does doctor show `✓ browser` and `✓ Playwright Chromium`. The `agent-browser` CLI is the wrapper; Playwright + Chromium is the engine. `browser-cdp` is a separate (more advanced) tool that may need extra setup and is often left ⚠.

`agent-browser` package is published by Vercel (npm: `agent-browser`, currently 0.27.x). Works on Linux/macOS/Windows. The Playwright Chromium download is ~112 MB — plan time.

### Web search needs BOTH config key + .env

Setting `TAVILY_API_KEY` in `.env` alone is NOT enough. The doctor still shows `⚠ web (missing ...)` until you also set:

```bash
hermes config set web.search_backend tavily
```

Same pattern for other backends: `exa`, `parallel`, `firecrawl`. Without `web.search_backend`, hermes never dispatches to the API key.

Backends ranked by agent-friendliness (free tier):
- **Tavily** — 1000 req/month, clean responses, designed for agents
- **Exa** — 1000 req/month, semantic search, best for research
- **Firecrawl** — 500 credits/month, best for deep web scraping
- **Parallel** — alternative backend

### Approvals: smart mode is the productivity sweet spot

Default is `manual` (prompts before every command flagged destructive). Most users want `smart`:

```bash
hermes config set approvals.mode smart
```

`smart` uses an auxiliary LLM to auto-approve low-risk commands and prompt on high-risk. `off` (= `--yolo`) bypasses everything but does NOT turn off secret redaction (those are independent toggles).

### Secret redaction must be set in config, not env (mid-session)

`security.redact_secrets` is snapshotted at import time. Flipping it from a tool call's `export HERMES_REDACT_SECRETS=...` does NOT affect the running process. Users must change it in config and start a new session.

### PII redaction is a separate toggle

`privacy.redact_pii` controls PII hashing in gateway messages. Default off. Independent of secret redaction. Don't conflate them when debugging redaction issues.

## Fresh-Install Optimization Checklist

After running the diagnostic, the highest-leverage fixes in order:

1. **Memory** — call the `memory` tool, write 5-7 fact batches covering: (a) user identity, (b) host env, (c) installed tools, (d) configured API keys, (e) toolset state, (f) gateway/messaging state. Batched separately, not one giant blob — the tool returns incremental success entries and you can see usage % climb.

2. **Smart approval** — `hermes config set approvals.mode smart`

3. **Browser tool** — `npm install -g agent-browser` + `npx playwright install chromium`

4. **Web search** — pick a backend (Tavily/Exa/Firecrawl), add API key to `.env`, set `web.search_backend`

5. **GitHub token** — add `GITHUB_TOKEN=*** to `.env` to lift from 60 → 5000 req/hr

6. **Fallback providers** — skip unless you have ≥2 providers; otherwise the fallback list is empty and there's nothing to do

7. **Skills hub** — `hermes skills list` initializes `~/.hermes/skills/hub/` on first run

## User API Key Recommendations

When the user has to pick a web backend, default to **Tavily** unless they have a specific reason otherwise. For image gen, the default backend is **FAL** (set `FAL_KEY`). For X/Twitter search, **xAI/Grok** (`XAI_API_KEY`).

If the user doesn't have keys, ask whether to skip or to set up a free tier. Don't pressure them into it.

## Verification

After fixes, re-run the 4-command diagnostic combo. Compare counts of ✓ vs ⚠. Remaining ⚠ items should be features that require their own platform credentials (Discord token, FAL key, xAI key, etc.) — those are by design, not bugs. Communicate that to the user so they know the gap is intentional, not a failure.

## Related

- `hermes-agent` — full CLI reference, provider list, security toggles
- `~/.hermes/config.yaml` — config keys live here
- `~/.hermes/.env` — API keys live here (write-only, read-protected)
- `hermes doctor --fix` — auto-fixes what's mechanically possible; not a substitute for the playbook above but a useful first pass
