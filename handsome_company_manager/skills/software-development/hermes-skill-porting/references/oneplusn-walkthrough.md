# Walkthrough: Porting `D:\onboarding` (1+N digital company) into Hermes

This is the full worked example for the `hermes-skill-porting` playbook. Read it alongside SKILL.md when you want to see exactly how the 7-step workflow was applied to a real Claude Code `.claude/` package, with concrete commands, decisions, and bug fixes.

---

## Source

`D:\onboarding\` (9.6 KB README + 2.8 KB `install.sh` + `.claude/` tree)

## Inventory (Step 1)

```
D:\onboarding\
├── README.md                              (9.6 KB)
├── install.sh                              (2.8 KB, 5-step installer)
├── .claude/
│   ├── commands/oneplusn/
│   │   ├── init.md                         (org setup)
│   │   ├── add.md                          (add employee)
│   │   ├── upgrade.md                      (upgrade modules)
│   │   ├── status.md                       (team health)
│   │   ├── sync.md                         (push README)
│   │   ├── edit.md                         (edit employee)
│   │   ├── delete.md                       (remove employee)
│   │   └── help.md                         (catalog)
│   └── skills/
│       ├── oneplusn-org-setup/
│       │   ├── SKILL.md
│       │   └── scripts/create_org.py      (~16 KB, dep-check + handoff generator)
│       ├── oneplusn-agent-onboarding/
│       │   ├── SKILL.md
│       │   └── scripts/onboard_agent.py   (~12 KB, Profile + SOUL + RULES + Cron)
│       └── oneplusn-agent-upgrade/
│           ├── SKILL.md
│           └── scripts/upgrade_agent.py
```

## Architecture decision (Step 2)

**Mode D — fork + integrate.** Reasons:

- 8 command files + 3 skill docs + 3 Python scripts = ~25 files. Too large to mirror verbatim.
- Scripts have known bugs (discovered during Step 1 scan: `python3` Microsoft Store alias, `gh` marked recommended but actually required, no email/username validation).
- User wants to run from Hermes CLI, not Claude Code.

## Lift (Step 3)

```bash
SKILL=~/AppData/Local/hermes/skills/productivity/oneplusn
mkdir -p "$SKILL"/{scripts,references,templates,bin}

# Lift scripts (preserve originals for diff)
cp D:/onboarding/.claude/skills/oneplusn-org-setup/scripts/create_org.py      "$SKILL/scripts/"
cp D:/onboarding/.claude/skills/oneplusn-agent-onboarding/scripts/onboard_agent.py "$SKILL/scripts/"
cp D:/onboarding/.claude/skills/oneplusn-agent-upgrade/scripts/upgrade_agent.py "$SKILL/scripts/"

# Preserve command .md as references
cp -r D:/onboarding/.claude/commands/oneplusn "$SKILL/commands_oneplusn/"

# Preserve original skill docs as references (for diff)
for s in org-setup agent-onboarding agent-upgrade; do
  mkdir -p "$SKILL/references_${s//-/}/"  # references_org/ references_agent/ references_upgrade/
  cp D:/onboarding/.claude/skills/oneplusn-$s/SKILL.md "$SKILL/references_${s//-/}/"
done
```

## Wrap (Step 4)

Wrote `SKILL.md` (~148 lines) covering:
- When to Use / When NOT to Use
- Architecture diagram
- Phased workflow table
- How to Execute (bash wrappers)
- Hard Constraints (gh required, .env never committed, etc.)
- Known Fixes vs the source
- Operational Maintenance schedule
- Self-verification (10 eval tests)
- See Also

Plus `USAGE.md` (6.5 KB) — the deep walkthrough that mirrors the original README but with Hermes-specific paths and commands.

## Shim (Step 5)

```bash
HERMES_BIN=~/AppData/Local/hermes/bin
cat > "$HERMES_BIN/oneplusn" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HERE/../../skills/productivity/oneplusn" && pwd)"
prog="$(basename "$0")"
case "$prog" in
  oneplusn)          CMD="${1:-help}"; [ $# -gt 0 ] && shift ;;
  oneplusn-init)     CMD="init" ;;
  oneplusn-add)      CMD="add" ;;
  oneplusn-upgrade)  CMD="upgrade" ;;
  oneplusn-status)   CMD="status" ;;
  oneplusn-edit)     CMD="edit" ;;
  oneplusn-sync)     CMD="sync" ;;
  oneplusn-delete)   CMD="delete" ;;
  oneplusn-eval)     CMD="eval" ;;
  *)                 CMD="help" ;;
esac
export ONEPLUSN_SKILL_DIR="$SKILL_DIR"
python "$SKILL_DIR/scripts/oneplusn_main.py" "$CMD" "$@"
EOF
chmod +x "$HERMES_BIN/oneplusn"
```

Then `cp` for sub-commands (Windows ln-sf gotcha):

```bash
for sub in init add upgrade status edit sync delete eval; do
  cp "$HERMES_BIN/oneplusn" "$HERMES_BIN/oneplusn-$sub"
done
```

## Cron (Step 6)

Original package: `setup_cron.py` writes to crontab. Replaced with:

```bash
hermes cron create \
  --name "oneplusn-poll-dev-01" \
  --schedule "30m" \
  --script "oneplusn-poll.sh" \
  --workdir "D:\test-1plusn-team" \
  --no-agent

hermes cron create \
  --name "oneplusn-reaper" \
  --schedule "every 1h" \
  --script "oneplusn-reap.sh" \
  --workdir "D:\test-1plusn-team" \
  --no-agent
```

The `--no-agent` flag is critical here: the poll script is a fixed-shape watchdog (run `gh issue list @me`, claim, work, comment), no LLM needed per tick.

## Eval (Step 7)

`scripts/oneplusn_eval.py` — 10 tests, sandbox in tempdir:

| # | Test | What it catches |
|---|------|-----------------|
| EVAL-01 | handoff.yaml schema | top-level keys + agents[] |
| EVAL-02 | per-agent fields | name/role/port/status/etc |
| EVAL-03 | role validation | role ∈ {8 legal roles} |
| EVAL-04 | README generation | Mermaid + team table + Cronjob section |
| EVAL-05 | sync idempotency | re-running sync produces same template bytes |
| EVAL-06 | .gitignore completeness | handoff.yaml / agents/*/.env listed, git check-ignore passes |
| EVAL-07 | .gitignore idempotency | re-running doesn't duplicate entries |
| EVAL-08 | SOUL cache hit/miss | first fetch = network, second = local, content identical |
| EVAL-09 | reaper script | parses handoff, falls back to boss as PM |
| EVAL-10 | create_org.py --check-deps | doesn't crash |

Result: 10/10 PASS.

---

## Bug fixes applied during the port

These are documented in SKILL.md §"Known Fixes vs the .claude/ Source":

1. **create_org.py: dep check** — `python3 --version` → `python -c "import sys; print(sys.version)"` (defeats Microsoft Store alias)
2. **create_org.py: gh flag** — `recommended` → `required`
3. **create_org.py: input validation** — added `ask_email()` and `ask_username()` regex check
4. **onboard_agent.py: SOUL cache** — added `agents/{name}/soul-source.md` for offline-second-load
5. **create_org.py: gitignore auto-add** — `ensure_gitignore_for_oneplusn()` called after handoff generation
6. **oneplusn_sync.py: git config** — read user.name/email from handoff before git init
7. **oneplusn_sync.py: gitignore format** — split `# comment` and `pattern` onto separate lines

All 7 fixes applied via `patch` calls; diff against original preserved in `references_org/` and `references_agent/`.

## Decisions deferred

- Original `setup_cron.py` left as reference under `references_agent/` but NOT wired into the new bash shim. Hermes cron is the recommended path; the user can still call `setup_cron.py` manually if they want a traditional crontab.
- 8 command .md files preserved under `commands_oneplusn/` for reference. They are not invoked by Hermes; only the bash shim is. If the user later moves to Claude Code, they can reuse these.

## Outcome

- Skill at `~/AppData/Local/hermes/skills/productivity/oneplusn/SKILL.md`
- 9 bash wrappers at `~/AppData/Local/hermes/bin/oneplusn*`
- 2 cron jobs registered via `hermes cron create`
- Eval at 10/10
- MEMORY updated with the integration decision + 4 primary bug fixes
- This walkthrough + the main `SKILL.md` together are the playbook for the next porting job

Total wall time: ~37 minutes from raw `.claude/` to eval-green, including 2 visual-QA rounds on the original PPT and the integration work.

---

## Re-applying this playbook

For a new porting job (say, a `.cursorrules` package):

1. Run Step 1 scan → expect similar inventory shape (commands/, skills/, scripts/)
2. Mode D if multi-file; Mode C if small and stable
3. Lift scripts to new skill's `scripts/`; preserve originals under `references_*`
4. Wrap with SKILL.md following the canonical pattern
5. Shim bash wrappers using `case "$prog"` + `cp` for Windows sub-commands
6. Cron via `hermes cron` with `--no-agent` for fixed-shape work
7. Eval with ≥8 tests covering schema, idempotency, OS-portability, auto-managed side files
8. Update MEMORY with the integration decision