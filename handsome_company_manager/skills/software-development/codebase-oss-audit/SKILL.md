---
name: codebase-oss-audit
description: Deep audit of an OSS package, dotfile bundle, or third-party skill/command toolchain (e.g. .claude/, ~/.hermes/, npm pkg source, downloaded skill installer) BEFORE adopting it. Methodology = 6-section report (architecture / claims-vs-implementation / security / runtime test / gaps / verdict). Use when user says "评估一下 X", "看看这个包", "deep dive into <dir>", or asks "should we adopt X?". Produces a numbered finding list the user can address top-down.
---

# OSS Codebase Audit

A structured pass to read AND test an external package before adopting it. Goes deeper than a code review and lighter than a security audit. You read the documentation, cross-check claims against implementation, run the system on a sandbox, and produce a categorized report the user can use to decide: adopt-as-is, fork-and-fix, or build-from-scratch.

## When this skill applies

- User says "look at this thing" / "eval X" / "看看 X 怎么样" / "should we adopt <pkg>?"
- New dotfile/toolchain clone appears on disk (e.g. `D:\onboarding\.claude\`, `~/.claude/commands/*`, a public skill bundle)
- User is choosing between a community package and building an internal version

## When it does NOT apply

- Single-file or single-PR review → use `requesting-code-review`
- Your own internal code → standard TDD / subagent-driven-development
- Security-only audit requiring threat model → find/use a formal security review skill
- "Can you debug this script?" — that's `systematic-debugging`, not adoption

## The 6-section audit report

Always deliver in this structure. Numbered finding prefix lets the user reference issues by ID later.

### §1 Architecture (read-only, no execution)

Confirm the documented diagram matches the file tree:

- Read top-level `README.md`. Capture: stated goal, layered diagram, command/skill/role counts.
- Walk every directory declared in the diagram. Verify each file exists; flag docs that reference missing files.
- For every command/skill name, read at least the frontmatter. Distinguish: "claims to invoke Skill X" vs "actually calls Skill X."
- Map dependency tiers (required / recommended / optional). For each "optional," decide if it's actually required.

### §2 Claims vs. implementation (highest bug yield)

Cross-check documentation against the actual call chain:

- For every "X does Y" claim, locate the call site. Does the call go through the documented layer (e.g. routing through Skill), or jumps straight to a script?
- For every "this .md is the literal prompt sent to the LLM" pattern, check whether the runtime actually invokes the .md as context, or just executes the bash inside it.
- Verify OS-specific claims ("works on Windows", "Linux supported") by attempting to run on that platform.
- Identify platform-baked assumptions: `#!/usr/bin/env python3` resolves to Microsoft Store stub on Windows; `bash` shebangs need git-bash or WSL on Windows; `applescript` only macOS; etc.

### §3 Security & secrets

Find where credentials leak:

- Search for `token / pat / api_key / secret` writes. Where does each get stored? Is the file `.gitignore`d?
- Read every cronjob / scheduler / sync definition. Verify it explicitly excludes `.env`, `*token*`, `*key*`, `*secret*` from any push/backup/log.
- Check repo-level `.gitignore`. Common misses: `handoff.yaml`, `state.db`, `*.local.yaml`, `agents/*/`.
- Enumerate the permission scopes each tool requests vs. what the README claims it requests.
- Concurrency: where multiple actors write the same config file, search for any lock/serialization. If absent, flag as risk.

### §4 Runtime test (highest bug yield, requires execution)

Run the system on a known-clean directory (NOT in the user's real home). Capture evidence:

- Use `install.sh` or equivalent and verify it deploys cleanly.
- Run the dep check first. Document every false-positive (script says "✓ installed" but isn't) and false-negative (script says "✗ missing" but is).
- For interactive prompts, write a fake stdin (see `references/fake-stdin-pattern.md`) and pipe it. Capture what happens with nonsensical inputs (empty, `n`, `y`, garbage).
- Hit each milestone: handoff file generated, agent onboarded, cron registered, sync executed. Stop at credentialed steps; don't fake those.
- Document the minimum sane input set needed to reach each milestone.

### §5 Limitations, gaps, unknowns

Surface what's NOT in the codebase but the user will eventually need:

- Lifecycle: what happens when the upstream repo is gone? Is there a local fallback?
- Latency: polling cadence = ? Hard floor on "urgent" task pickup = ?
- Collision: two actors claim the same work item — detection / resolution story?
- Cleanup: dead task / orphan process / stuck lock — recovery story?
- Observability: when something silently fails, can you diagnose post-mortem?
- Migration: v1 → v2 schema versioning? Onboarding path for a new operator?

### §6 Verdict & next-action menu

End every report with this. Three options, one line each — user picks with a single letter:

- **A: Adopt as-is** — works for the user's stated use case without changes
- **B: Fork-and-fix** — list 3–7 most valuable patches; rough effort estimate
- **C: Build from-scratch** — OSS doesn't earn its place; rebuild the design from zero

## Anti-patterns

- ❌ Reading every file exhaustively. Skim layout, deep-read claims, run install. 80/20: 5–10 critical files contain 80% of bugs.
- ❌ Spending all the time in §1. Most findings live in §2 and §4.
- ❌ Treating "install.sh runs" as "system works". Install is weakest signal; §4 runtime is strongest.
- ❌ Reporting only positives. The user wants the gap list, or they wouldn't be auditing.
- ❌ Verbose reports. Bullet points; tables for many issues; one concrete fix per critical issue.
- ❌ Single-tool reliance. Combine `read_file` + `search_files` + `terminal` + `web_search` (for canonical docs URLs).

## Pitfalls log (sessions that ran this skill)

### 2026-07 — `D:\onboarding\.claude\` (1+N 数字员工 package, 3 skills + 8 commands)

7 issues found in §2 + §3 + §4 alone:
1. `gh` marked "recommended" in README but required by cron (`gh issue list` every 30 min) → mislabel, should be "required".
2. `create_org.py` uses `python3 --version`; on Windows resolves to MS Store stub that returns "Python was not found…" but the check still passes → false-positive dep detection.
3. PyYAML detection uses `python3 -c "import yaml"`, again going through the broken stub. The user's working venv has PyYAML but the check fails → false-negative.
4. Email input has no `@` validation; garbled values flow downstream and produce invalid `handoff.yaml`.
5. Interactive prompts with empty-string defaults consume the next input line as the new value — confuses piped-CI scenarios and stuck sessions.
6. `command/*.md` files call scripts directly (`python3 scripts/create_org.py …`) without loading the Skill layer the architecture diagram describes → claims-vs-reality gap.
7. Token written into `handoff.yaml`, but README never mentions adding it to `.gitignore` — secret leakage if anyone `git init` the workdir.

OS-specific workaround observed: GitHub CLI (`gh`) on Windows must be on `PATH` before install checks; choco installs it to `C:\Program Files\GitHub CLI\` which is NOT on git-bash's default PATH. Add `export PATH="/c/Program Files/GitHub CLI:$PATH"` to `~/.bashrc`.

## Supporting files

- `references/fake-stdin-pattern.md` — how to pipe canned input into interactive CLIs to test edge-case handling
- `references/checklist.md` — tick-box copy of the 6-section audit for the actual run
