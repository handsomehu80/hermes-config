---
name: hermes-skill-porting
description: Port an external agent package (Claude Code `.claude/`, Cursor `.cursorrules/`, Codex `.codex/`, generic bash + skill bundles) into Hermes's `~/AppData/Local/hermes/skills/` system. Covers the 7-step porting workflow, 6 Windows-specific gotchas (Python path resolution, `ln -sf` failure, `MSO_SHAPE.RECTANGLE` border, gitignore inline-comment syntax, Microsoft Store python3 alias, PowerPoint file-lock), eval-driven verification, and references a worked example (oneplusn). Use when the user asks to integrate / port / fork / adapt an existing AI agent workflow package into Hermes, OR when loading `oneplusn` (which was built using this exact playbook) and you'd like the methodology behind its structure.
version: 0.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [meta, porting, integration, hermes-agent, claude-code, skill-authoring]
    related: [hermes-agent, oneplusn, multi-profile-team]
---

# Porting External Agent Packages into Hermes

When you find a well-built AI agent workflow (typically a Claude Code `.claude/` package, a Cursor `.cursorrules/` bundle, or a custom bash + skill distribution) and want to integrate it into Hermes, **do not try to make the original run unmodified.** Hermes has its own skill model, command surface, cron system, and platform conventions. A clean port requires architectural adaptation.

This skill is the playbook. It was written immediately after porting `D:\onboarding` (the `oneplusn` 1+N digital-company package, Claude Code `.claude/` format) into Hermes — see the worked-example walkthrough in `references/oneplusn-walkthrough.md`.

## When to use this

- User says "把这个 .claude 包移植到 Hermes" / "集成这个 agent 包"
- User references an external package URL or repo and says "用起来" / "跑起来" / "做成 skill"
- User wants to *fork* a Claude package (modify behavior) rather than *adopt* it (call it as-is)
- You're loading `oneplusn` for the first time and want to understand the integration decisions

## When NOT to use this

- The user just wants to *run* a Claude package — they need Claude Code installed; not a Hermes concern
- The deliverable is reading / light-editing an existing file — no porting needed
- The source is already a Hermes skill — use `skill_manage(action='patch')` to extend instead of re-architecting

---

## The 7-step porting workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. SCAN  — inventory the source: skills/, commands/, scripts/      │
│ 2. ADAPT — pick "integrate" (fork into Hermes skill format)        │
│ 3. LIFT  — copy scripts/ + commands/ to skill's scripts/ subfolder │
│ 4. WRAP  — author SKILL.md, references, USAGE.md                   │
│ 5. SHIM  — write bash wrappers in ~/AppData/Local/hermes/bin/      │
│ 6. CRON  — port any schedule-driven pieces to `hermes cron`        │
│ 7. EVAL  — write a `oneplusn-eval`-style sandbox test (10 cases)   │
└─────────────────────────────────────────────────────────────────────┘
```

### Step 1 — Scan

Identify every artifact the package ships with:

- `commands/<name>/*.md` (Claude slash-command prompts)
- `skills/<name>/SKILL.md` (Claude skill docs)
- `skills/<name>/scripts/*.py` (Python invoked from skills)
- `install.sh` / `setup.sh` / `Makefile` (entrypoint)
- `README.md` (assumed, often outdated — re-read it as a hint, not source of truth)
- Templates or fixtures the scripts read

Output of step 1: a 1-page inventory table. For oneplusn that was:

```
D:\onboarding\
├── README.md                        (9.6 KB, claims many features — verify each)
├── install.sh                        (2.8 KB, sets up email/GitHub/Org)
├── .claude/
│   ├── commands/oneplusn/*.md        (8 commands, each ~3-5 KB)
│   ├── skills/oneplusn-org-setup/SKILL.md
│   ├── skills/oneplusn-org-setup/scripts/create_org.py
│   ├── skills/oneplusn-agent-onboarding/SKILL.md
│   ├── skills/oneplusn-agent-onboarding/scripts/onboard_agent.py
│   ├── skills/oneplusn-agent-onboarding/scripts/setup_cron.py
│   ├── skills/oneplusn-agent-upgrade/SKILL.md
│   └── skills/oneplusn-agent-upgrade/scripts/upgrade_agent.py
```

### Step 2 — Adapt (the architecture decision)

Pick one of four:

| Mode | What you do | When |
|------|-------------|------|
| **A. Adopt (verbatim)** | Install Claude Code and `cd` into the package; don't touch Hermes | User just wants to use Claude Code |
| **B. Replace** | Throw out the package; build Hermes-native from scratch using its README as requirements | Package design is broken or doesn't fit Hermes's model |
| **C. Mirror** | Keep the package's structure; replicate each `.claude/commands/foo.md` as a Hermes skill 1:1 | Package is small, stable, and matches Hermes semantics well |
| **D. Fork + integrate (recommended)** | Re-architect as a Hermes skill (single SKILL.md + sub-doc `references_*`); keep original under `references_<orig>/` as historical reference; port scripts/ to the skill's `scripts/` | Package is medium-large (5+ files), has its own scripts that need bug fixes, and the user wants a single entry point |

For oneplusn I picked D: 8 command files became 8 bash shims, 3 skill docs collapsed into 1 SKILL.md with sub-doc references, scripts ported (with bug fixes) to the new `scripts/` directory.

### Step 3 — Lift

Move (don't copy!) the package's scripts into your new skill's `scripts/`:

```bash
SKILL=~/AppData/Local/hermes/skills/<category>/<name>
mkdir -p "$SKILL"/{scripts,references,templates,bin}

# Lift (preserve original) — NEVER modify the source during this step
cp <source>/scripts/*.py "$SKILL/scripts/"
cp <source>/.claude/commands/*.md "$SKILL/references_commands/"
cp <source>/.claude/skills/*/SKILL.md "$SKILL/references_skills/"
```

Keep the originals untouched in `references_*` directories so the user can audit what changed. Diff your fixes against the original line-by-line.

### Step 4 — Wrap

Author the new SKILL.md using the canonical pattern:

1. **Frontmatter:** `name`, `description`, `version`, `platforms`, `metadata.hermes.tags`, `metadata.hermes.related`
2. **When to Use** (3+ concrete trigger phrases from the user's actual language)
3. **When NOT to Use** (specifically exclude the confused-with-this cases)
4. **Architecture at a Glance** (one ASCII diagram — user-validated in oneplusn)
5. **Phased Workflow** (table mapping package phases to skill commands + sub-doc directories)
6. **How to Execute** (Hermes-native bash commands the user can copy-paste)
7. **Hard Constraints** (don't try to bypass — these are the rules the package's README glosses over)
8. **Known Fixes vs the source** (every bug you patched in scripts/, with line number if possible)
9. **Operational Maintenance** (weekly + monthly + on-event)
10. **Self-verification** (eval test catalog, what each test catches)
11. **See Also** (links to related skills)

If your ported package has a long USAGE doc, put it in `USAGE.md` (not in SKILL.md) — SKILL.md is the index, USAGE.md is the deep walkthrough. The agent reads both on demand.

### Step 5 — Shim

Bash wrappers in `~/AppData/Local/hermes/bin/`. The pattern:

```bash
#!/usr/bin/env bash
# ~/AppData/Local/hermes/bin/<name>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HERE/../../skills/<category>/<name>" && pwd)"
prog="$(basename "$0")"

# Default to master, dispatch to sub-command
case "$prog" in
  <name>)          CMD="${1:-help}"; shift || true ;;
  <name>-init)     CMD="init"; shift ;;
  <name>-add)      CMD="add"; shift ;;
  # ... one case per sub-command
  *)               CMD="help" ;;
esac

export <ENV_VAR>="$SKILL_DIR"
python "$SKILL_DIR/scripts/main.py" "$CMD" "$@"
```

**Windows gotcha:** `ln -sf` does NOT create a real symlink on git-bash Windows. Use `cp` instead:

```bash
for sub in init add upgrade status edit sync delete eval; do
  cp ~/AppData/Local/hermes/bin/<name> ~/AppData/Local/hermes/bin/<name>-$sub
done
```

Each copy has the same content but a different filename, so `basename $0` resolves correctly inside the case block.

### Step 6 — Cron (if the package has scheduled work)

Don't use bare crontab. Use Hermes cron:

```bash
hermes cron create \
  --name "<name>-poll-<agent>" \
  --schedule "30m" \
  --script "<name>-poll.sh" \
  --workdir <team_dir> \
  --no-agent
```

The `--no-agent` flag skips the LLM entirely — the script IS the job and its stdout is delivered verbatim. Use this pattern for heartbeat / poll-and-act / sweep loops that have a fixed output shape. For reasoning-heavy cron jobs (summarize feed, draft daily briefing, pick interesting items), omit `--no-agent` so the LLM runs each tick.

For scripts that need parameters, prefer **environment variables** (`ONEPLUSN_HANDOFF=<path>`) over argv — cron runs `script.sh` directly, not through a wrapper. Document the env vars in SKILL.md §Hard Constraints.

### Step 7 — Eval

Author a `scripts/<name>_eval.py` that runs N automated tests against a temp sandbox. Pattern:

```python
import tempfile, shutil, sys
from pathlib import Path

def make_sandbox():
    return Path(tempfile.mkdtemp(prefix="<name>-eval-"))

def eval_<NN>_check_<thing>(sandbox):
    # ... assert state
    return True  # or raise AssertionError with detail

def main():
    sandbox = make_sandbox()
    try:
        for test in [eval_01, eval_02, ..., eval_10]:
            try:
                test(sandbox)
                print(f"✓ {test.__name__}")
            except AssertionError as e:
                print(f"✗ {test.__name__}: {e}")
                sys.exit(1)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

if __name__ == "__main__":
    main()
```

The eval must cover at least: schema validation, idempotency, OS-portable behavior (paths), and any "auto-managed" side files (`.gitignore`, config files, cache).

For oneplusn: 10 tests (`EVAL-01` through `EVAL-10`) covering schema, field completeness, role validation, README generation, sync idempotency, gitignore completeness + idempotency, SOUL cache hit/miss, reaper fallback, dep-check. All green → integration is shippable.

---

## The 6 Windows gotchas (and fixes)

These all surfaced during the oneplusn port. They will recur for any package that ships Python scripts.

### Gotcha 1 — `python3` is the Microsoft Store alias

On Windows 10+, `python3 --version` returns "Python 3.x" via a stub that opens the Microsoft Store to install Python. This breaks any dep-check that uses `python3 --version`.

**Fix:** Use `python -c "import sys; print(sys.version_info[:2])"` instead. Also detect the Microsoft Store redirect string ("Microsoft Store") and fail loudly.

### Gotcha 2 — `Path("/c/Users/...")` resolves wrong on nt

Python's `pathlib.Path` on Windows treats `/c/Users/...` as a relative-ish path under drive C, ending up as `C:\c\Users\...` (note the doubled `C:\c`). This is not where the actual `C:\Users` lives.

**Fix:** Use `Path("C:/Users/...")` or `os.path.abspath(os.path.expanduser("~"))`. When writing cross-platform code, prefer `os.path.expanduser("~")` over path-string manipulation.

```python
# WRONG on Windows:
sandbox = Path(f"/tmp/oneplusn-eval-{uuid.uuid4()}")   # becomes C:\tmp\...

# RIGHT:
sandbox = Path(tempfile.mkdtemp(prefix="oneplusn-eval-"))   # always works
```

### Gotcha 3 — `ln -sf` doesn't symlink on git-bash

Symlinks on Windows require admin privileges OR Developer Mode. git-bash silently creates a copy (or fails). Either way, `basename $0` returns the wrong string and sub-command dispatch breaks.

**Fix:** Use `cp`. Document in the bash wrapper comment. Same fix for all multi-binary wrappers.

### Gotcha 4 — `gh` requires manual PATH export on Windows

`gh` installed via `winget` or `choco` lands in `C:\Program Files\GitHub CLI\`, which is NOT in default `$PATH`. Add to `~/.bashrc`:

```bash
export PATH="/c/Program Files/GitHub CLI:$PATH"
```

Document this in the skill's "Hard Constraints" so the next user knows.

### Gotcha 5 — gitignore parser doesn't support inline comments

**Not Windows-specific**, but you WILL hit it on any port involving auto-generated `.gitignore`. The pattern:

```gitignore
handoff.yaml  # boss PAT
```

is treated by Git's gitignore parser as ONE pattern `handoff.yaml  # boss PAT`, which never matches anything. Inline `# comment` syntax is NOT supported in gitignore.

**Fix:** Two-line pattern:

```gitignore
# boss PAT
handoff.yaml
```

When generating gitignore entries programmatically, use a list of `(comment, pattern)` pairs and emit them as alternating single-line comments and single-line patterns.

### Gotcha 6 — PowerPoint file-lock via win32com

If your ported package produces `.pptx` files (or you need to render PPT), the COM automation leaves the file locked. Subsequent writes fail with `PermissionError: [Errno 13]`.

**Fix:** Run `taskkill /F /IM POWERPNT.EXE` between regenerations. See `pptx-generation-and-visual-qa` for the full pattern.

---

## Worked example — `oneplusn`

The full walkthrough of how this playbook was applied to `D:\onboarding` lives in `references/oneplusn-walkthrough.md`. Use it as a worked example when you tackle a new porting job.

Key decisions made:
- **Mode D** (fork + integrate): 8 commands → 8 bash shims, 3 skill docs → 1 SKILL.md with sub-doc references
- **Sub-doc structure** preserved under `references_*` (auditable diff)
- **Eval-first**: 10 tests, all green before declaring integration done
- **Memory updated** (not just skill): the MEMORY entry records the integration decision + 4 bug fixes
- **Cron converted** from crontab to `hermes cron --no-agent`

---

## See also

- `hermes-agent` — full `hermes` CLI reference (`hermes config`, `hermes cron`, `hermes profile`, `hermes skills install`)
- `oneplusn` — the worked-example product of this playbook
- `pptx-generation-and-visual-qa` — covers the .pptx-file-lock variant (Gotcha 6)
- `references/oneplusn-walkthrough.md` — full worked-example diff