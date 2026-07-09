---
name: claude-package-to-hermes-skill
description: "Migrate a Claude Code .claude/ package (slash commands + Skill subfolder) into a Hermes-native skill (SKILL.md + scripts/ + bash wrappers in ~/AppData/Local/hermes/bin/ + cron jobs). Use when a user has a .claude/commands + .claude/skills directory they want to expose to Hermes Agent CLI as invocable commands, or when authoring a oneplusn-style multi-agent team system. Captures the integration pattern: command-md-as-prompt becomes a oneplusn-style bash wrapper that calls scripts/ directly; sub-skills fold into the parent's references/ as historical context; cron jobs route through `hermes cron create --script` rather than raw crontab."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [claude-code, migration, skill-authoring, bash-wrappers, oneplusn, hermes-cli]
    related: [oneplusn, multi-profile-team, hermes-agent, pptx-generation-and-visual-qa]
---

# Claude Code .claude/ Package → Hermes Skill Migration

How to take a `.claude/` package (slash commands + Skill subfolders) — as written for Claude Code users — and expose it to **Hermes Agent CLI** as invocable bash commands + a loadable skill.

This pattern is the basis of the `oneplusn` skill (1+N 数字员工) integration at `~/AppData/Local/hermes/skills/productivity/oneplusn/`. Use this skill when you need to port a similar .claude/ package, or when authoring a new oneplusn-style multi-agent team.

## The Two-Layer Pattern

```
.claude/                          →  Hermes native
─────────────────────────────────────────────────────────
.claude/commands/foo.md           →  ~/AppData/Local/hermes/bin/foo + bin/foo-{bar,baz}
  (slash command prompt)              (bash wrapper that runs python script)
                                 →  loadable by LLM via SKILL.md description
                                 →  in chat: "use oneplusn init" auto-loads skill

.claude/skills/X/SKILL.md         →  folded into one master SKILL.md
  (sub-skill)                         (parent skill holds the architecture)
                                 →  sub-skill SKILL.md goes to references_X/SKILL.md
                                     as historical context, not loaded by default
```

The key insight: in Claude Code, slash commands are *prompts sent to the LLM*. In Hermes, bash wrappers are *commands the user runs*. The mapping is 1:1 — each command's `instructions` section becomes the bash wrapper's argument parser and the Python script's logic.

## Step-by-Step Migration

### 1. Inventory the .claude/ Source

```bash
# Show structure
find /path/to/.claude -type f -name "*.md" -o -name "*.py" | sort
# Show the README
cat /path/to/.claude/README.md
```

You need:
- Main `README.md` — overall architecture, command index
- `commands/<name>.md` files — the actual slash command prompts
- `skills/<sub-skill>/SKILL.md` — sub-skill documentation
- `skills/<sub-skill>/scripts/*.py` — the executable code
- `skills/<sub-skill>/references/*` — templates, prompts, etc.

### 2. Create the Master Skill

```
~/AppData/Local/hermes/skills/<category>/<name>/
├── SKILL.md                # master skill (loaded by LLM when user mentions the system)
├── scripts/                # copied from .claude/skills/*/scripts/
├── references_<sub>/       # sub-skill docs, kept as historical reference
├── commands_<name>/         # original command .md files (also historical)
└── USAGE.md                # migration guide
```

The `SKILL.md` must have proper YAML frontmatter:

```yaml
---
name: oneplusn
description: "1+N digital company — boss + N AI employees. ..."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [one-person-company, digital-employees, ...]
    related: [multi-profile-team, ...]
---
```

The `description` is what the LLM uses to match — write it as a user-need description, not a feature list.

### 3. Apply Bug Fixes to the Scripts

The .claude/ package was written for Claude Code, not Python directly. Expect these:

| Bug | Fix |
|-----|-----|
| `python3 --version` (Windows Store fake alias) | Use `python -c "import sys; print(sys.version_info[0], sys.version_info[1])"` |
| `gh` CLI marked "recommended" but actually required | Re-classify as required, fail the dep check if missing |
| No input validation (empty string accepted) | Add `ask_email()` / `ask_username()` helpers with format checks |
| Raw crontab instructions | Use `hermes cron create --script <file> --no-agent` |
| `git config user.name` not set on first init | Auto-derive from `handoff.yaml` boss info, set in local repo |
| `git config` fails when not in a git repo | Init first, then configure |
| `Path("/c/...")` misinterpreted as `C:\c\...` on Windows Python | Use `Path("C:/...")` or pre-compute Windows paths |
| `ln -sf` doesn't work in git-bash on Windows | Use `cp` to make wrapper copies |
| Bash wrapper hardcodes `--interactive` / `--force-prompt` | Audit the underlying script's argparse: if it short-circuits to interactive_mode() on that flag, the wrapper must only pass it when CLI args are absent, otherwise `--name/--role/etc.` get silently swallowed |

### 4. Write the Bash Wrapper

The single `oneplusn` script lives in `~/AppData/Local/hermes/bin/`. It handles two invocation styles:

- `oneplusn <subcommand> <args>` — main style
- `oneplusn-<subcommand> <args>` — copied-style (Windows fallback)

```bash
#!/usr/bin/env bash
set -euo pipefail

find_skill_dir() {
    for d in \
        "$HOME/AppData/Local/hermes/skills/<cat>/<name>" \
        "$HOME/.local/share/hermes/skills/<cat>/<name>"; do
        [[ -d "$d/scripts" ]] && { echo "$d"; return 0; }
    done
}
SKILL_DIR="$(find_skill_dir)"
[[ -z "$SKILL_DIR" ]] && { echo "[✗] 找不到 skill"; exit 1; }

# Windows PATH fix
[[ "$OSTYPE" =~ msys|cygwin|win32 ]] && \
    export PATH="/c/Program Files/GitHub CLI:$PATH"

cmd="${1:-help}"

# Override: if invoked as oneplusn-X, treat as subcommand X
prog="$(basename "$0")"
[[ "$prog" == oneplusn-* ]] && cmd="${prog#oneplusn-}"

# Only shift if cmd came from arg (not from prog override)
[[ "$prog" != oneplusn-* ]] && shift 2>/dev/null || true

case "$cmd" in
    help) cat <<'EOF'
...
EOF
    ;;
    init) python "$SKILL_DIR/scripts/init.py" --work-dir "$WD" "${@}" ;;
    status) python "$SKILL_DIR/scripts/status.py" --work-dir "$WD" "${@}" ;;
    *)
        # Default: treat as "oneplusn $1" — pass to script
        python "$SKILL_DIR/scripts/main.py" "$cmd" "${@}"
        ;;
esac
```

Then create copies for each subcommand:

```bash
# Linux/macOS:
for cmd in init add status; do ln -sf oneplusn "oneplusn-$cmd"; done
# Windows (git-bash): ln -sf doesn't work, use cp:
for cmd in init add status; do cp oneplusn "oneplusn-$cmd"; done
chmod +x oneplusn*
```

### 5. Register Cron Jobs via `hermes cron`

Replace raw crontab instructions with `hermes cron create`:

```bash
# Polling: every 30 min, no-agent (script stdout delivered directly)
hermes cron create "30m" \
    --name "oneplusn-poll-dev01" \
    --script "oneplusn-poll.sh" \
    --workdir "/d/test-1plusn-team" \
    --no-agent
```

Use `--no-agent` for watchdog-style scripts (memory/disk/reap alerts) where you don't need LLM in the loop. Use default (with `--skill <name>`) for jobs that need the LLM to process script output.

### 6. Write the Eval Suite

The .claude/ package likely has an `evals.md` spec with 16+ tests. Most require real GitHub/Hermes — not automatable. Pick the **local-only** subset:

- Schema validation (handoff.yaml structure)
- Path/script existence checks
- Render-and-inspect (run sync, check README contains sections)
- Idempotency (run twice, no duplicates)
- Cache logic (mock network with cache files)
- Cron argument parsing (without actually running gh)

**Hard rule**: tests must NOT pollute the user's real dirs. Use `tempfile.mkdtemp()` for work_dir, cleanup in `finally`.

Path gotchas on Windows for the eval:
- `Path("/c/Users/...")` is interpreted as `C:\c\Users\...` (BAD)
- `Path("C:/Users/...")` is correct (Windows)
- Use `str(Path("...").resolve())` for absolute paths in subprocess calls

```python
SCRIPTS_DIR = Path("C:/Users/Administrator/AppData/Local/hermes/skills/<name>/scripts")

def win_path(p: Path) -> str:
    if os.name != "nt":
        return str(p)
    return str(p.resolve())  # critical: resolve() to drop the bad /c/ prefix
```

### 7. End-to-End Verification

```bash
# 1. Skill is recognized
hermes skills list | grep <name>

# 2. CLI works (all 3 invocation styles)
<cmd> help
<cmd> <subcommand> --work-dir /tmp/test
<cmd>-<subcommand> /tmp/test

# 3. Cron is registered
hermes cron list

# 4. Evals pass
<cmd>-eval

# 5. Sample render test (no remote calls)
<cmd> sync --work-dir /tmp/test --no-push
cat /tmp/test/README.md
```

## Anti-Patterns to Avoid

- ❌ **Forgetting to make `set -euo pipefail` the first line of bash wrapper** — silent errors in the wrapper will confuse users
- ❌ **Mixing the original .claude/ package and the Hermes version** — pick one canonical source. The .claude/ stays at `D:\onboarding` as source of truth; the Hermes version is derivative. When you fix a bug, sync both.
- ❌ **Skipping the eval suite** — without it, regression bugs (like my `git check-ignore` fail) hide until production
- ❌ **Trusting `--keep` / `--no-push` flags without testing** — they should change behavior visibly. Verify with a separate run.
- ❌ **Putting secrets in code** — handoff.yaml stores the boss's PAT Token. The eval/gitignore layer must prevent it being committed. Test `git check-ignore handoff.yaml` succeeds.
- ❌ **Using `pattern  # comment` in .gitignore** — Git 5+ does NOT support inline comments. Use separate `# comment` lines.
- ❌ **Bash wrapper unconditionally passing `--interactive`** — the original .claude/ slash command was prompt-only, so the ported Python script short-circuits on `--interactive` and ignores every other arg. If you always pass it, `oneplusn add --name dev-01 --role developer` silently falls back to interactive prompts and the user gets a blank-name error. Correct shape: only pass `--interactive` if the user gave no `*name*` / `*role*` flag. Patch BOTH `oneplusn` and `oneplusn-<sub>` (the Windows copies) — they are independent files.

## Critical Path Conventions for Subprocess on Windows

This is the most common footgun. The patterns:

| Path style | When it works | When it fails |
|---|---|---|
| `/c/Users/...` in bash | ✓ git-bash | ✗ Python `Path()` (becomes `C:\c\...`) |
| `C:/Users/...` in Python | ✓ `Path()`, ✓ `subprocess.run([..., str(path), ...])` | ✗ `subprocess.run(shell=True)` (depends) |
| `C:\Users\...` in bash | ✓ cmd.exe | ✗ git-bash without `MSYS_NO_PATHCONV=1` |
| `os.path.abspath('C:/...')` | ✓ | works everywhere |

Always test the path style against the actual interpreter that will consume it.

## Done Criteria (Bash Wrapper Quality Bar)

Your wrapper is ready when:

- [ ] `oneplusn help` (no args) shows clean command catalog
- [ ] `oneplusn <sub> --work-dir X` runs the subcommand with the right script
- [ ] `oneplusn-<sub> X` (no extra arg) runs the same subcommand (proves the symlink/copy fallback works)
- [ ] `oneplusn <sub> --help` shows the underlying script's help (proves args pass through)
- [ ] `oneplusn <sub> --name foo --role bar` does NOT prompt for name/role (proves CLI args aren't swallowed by an always-on `--interactive`)
- [ ] Each subcommand has at least 1 eval test in `oneplusn_eval.py` that passes
- [ ] Cron jobs show in `hermes cron list` with `Workdir` set
- [ ] `.gitignore` is auto-created when work-dir becomes a git repo, AND `git check-ignore <secret-file>` returns 0
- [ ] `hermes skills list | grep <name>` shows the skill as `enabled`

## See Also

- `oneplusn` — the canonical example this skill pattern was extracted from
- `multi-profile-team` — the in-process Hermes team pattern (vs. GitHub Issues external team)
- `pptx-generation-and-visual-qa` — another end-to-end skill with a built-in visual QA pass
- `hermes-agent` — full CLI reference for `hermes cron`, `hermes skills`, etc.
