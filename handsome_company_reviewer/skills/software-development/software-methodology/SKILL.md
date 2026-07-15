---
name: software-methodology
description: "Class-level umbrella for the obra/superpowers + GSD + Hermes software methodology toolchain — pick the right sibling for the current stage (plan, test, debug, review, delegate, spike, port). Each sibling skill is the deep-dive; this umbrella is the discovery index that tells you which one to load."
tags: [methodology, software-development, planning, testing, debugging, code-review, subagent, spike, porting, superpowers, gsd]
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [methodology, software-development, planning, testing, debugging, code-review, subagent, spike, porting, superpowers, gsd]
    related_skills: [writing-plans, test-driven-development, systematic-debugging, node-inspect-debugger, requesting-code-review, subagent-driven-development, spike, hermes-skill-porting]
---

# Software Methodology Toolchain

Discovery index for the Hermes Agent **software methodology family** — a coordinated set of class-level siblings, each one the deep-dive for a single stage of building software. The siblings are obra/superpowers roots (Plan / Test / Debug / Review / Delegate) plus Hermes-native additions (Spike for throwaway experiments, Porting for external agent packages).

> **Use this umbrella as a discovery index, NOT as a substitute for loading the sibling.** Each sibling has the detailed checklists, anti-patterns, and pitfalls for its stage; reading this index tells you which one to load.

## Quick decision table — which sibling do I load?

| You're at this stage of building software... | Load |
|---|---|
| Writing or reviewing an implementation plan, or the user invoked `/plan` | [`writing-plans`](#writing-plans) |
| About to write code (or modify existing code with regression risk) | [`test-driven-development`](#test-driven-development) |
| Hit a bug, test failure, or unexpected behavior you can't immediately explain | [`systematic-debugging`](#systematic-debugging) |
| Debugging a Node.js process specifically (CDP / `--inspect` workflow) | [`node-inspect-debugger`](#node-inspect-debugger) |
| Ready to verify a change before commit / push / "ship it" / "done" | [`requesting-code-review`](#requesting-code-review) |
| Executing an implementation plan task-by-task with two-stage review | [`subagent-driven-development`](#subagent-driven-development) |
| Want to feel out an idea with a throwaway experiment before committing | [`spike`](#spike) |
| Need to migrate an external agent package (`.claude/`, `.cursorrules/`, generic bash bundle) into Hermes | [`hermes-skill-porting`](#hermes-skill-porting) |

The siblings compose — a typical feature build hits Plan → Test → Delegate → Review (write a plan with `writing-plans`, enforce TDD on each task with `test-driven-development`, dispatch via `subagent-driven-development` which does spec+quality review, run `requesting-code-review` as the final pre-commit gate). The non-TDD ones (`spike`, `hermes-skill-porting`) substitute when the build is exploratory or hermes-internal.

---

## writing-plans

**When to load:**

- User asks for an implementation plan, a roadmap, a step-by-step breakdown
- User invokes `/plan`
- You're about to dispatch `subagent-driven-development` and need to author the plan first
- Decision is needed that requires structured comparison ("compare A vs B, recommend one")

**The deep-dive skill** covers: bite-sized task granularity (2-5 min each), the required plan header format, per-task TDD template, DRY/YAGNI/TDD principles, the execution handoff pattern via `subagent-driven-development`, **AND plan-mode turn behavior** (no-exec, save to `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`).

This umbrella recommends loading `writing-plans` any time a plan is the deliverable — its plan-mode subsection handles the turn-behavior rule automatically.

---

## test-driven-development

**When to load:**

- About to write any new production code (function, method, endpoint, script)
- About to modify existing code with regression risk
- Fixing a bug — write the regression test first per `systematic-debugging`'s Phase 4
- User says "add tests", "write tests for X", "I want this to be testable"

**The deep-dive skill** covers: the Iron Law (no production code without a failing test first), the Red-Green-Refactor cycle with explicit verification at each step, what counts as a good test (clear name, real code not mocks, edge cases), common rationalizations and why each fails, how TDD composes with `delegate_task` subagents.

---

## systematic-debugging

**When to load:**

- A test fails and you don't immediately see why
- Production bug report with non-obvious symptoms
- "This used to work" / "X doesn't work anymore" without obvious cause
- Multiple components, race conditions, intermittent failures
- The Rule of Three: 3+ fix attempts without a root cause → STOP, question the architecture

**The deep-dive skill** covers: the 4 phases (Root Cause Investigation → Pattern Analysis → Hypothesis + Testing → Implementation), the Iron Law (no fixes without root cause investigation FIRST), instrumenting multi-component systems, the "3+ fixes failed = architectural problem" diagnostic, integration with `test-driven-development` (write the failing test that reproduces the bug BEFORE fixing).

---

## node-inspect-debugger

**When to load:**

- Debugging a running Node.js process (server, daemon, long-lived script)
- You need to attach to a Node.js process via Chrome DevTools Protocol (`--inspect`, `--inspect-brk`)
- A Node process is hung, leaking, or producing unexpected output and you need live inspection (breakpoints, heap snapshots, async stack traces)
- Hermes itself (the Python agent) is fine; you specifically need a Node-side debugging tool

**The deep-dive skill** covers: the `node --inspect` and `--inspect-brk` startup flags, attaching Chrome DevTools to a running Node process, using the headless-DevTools CLI flow when no GUI is available, scripted breakpoints and introspection, debugging Node.js native addons or Node-side `hermes` plugins. Distinct from `systematic-debugging` because Node CDP has its own specific attach-and-step workflow.

**Do NOT use for:** Python/JS in-loop reasoning (use `systematic-debugging`), Hermes config issues (use `hermes-agent`), browser page inspection (use `browser_snapshot`/`browser_console` in-process tools).

---

## requesting-code-review

**When to load:**

- About to commit, push, or say "done" / "ship it" on a 2+ file change
- After each task in `subagent-driven-development` (the code-quality review stage)
- User says "verify", "review before merge", "should I commit?"
- Independent reviewer subagent for fresh-context review

**The deep-dive skill** covers: 8-step verification pipeline (get diff → static security scan → baseline tests/lint → self-review checklist → independent reviewer subagent → evaluate → auto-fix loop → commit with `[verified]` prefix), fail-closed JSON review format, common patterns to flag per language, the auto-fix-and-reverify cycle (max 2 attempts), how it composes with the two-stage review in `subagent-driven-development`.

**Skip for:** documentation-only changes, pure config tweaks, or when user explicitly says "skip verification".

---

## subagent-driven-development

**When to load:**

- You have an implementation plan ready and want to execute it with fresh-context subagents per task
- Tasks are mostly independent, quality matters more than speed, you want automated spec-compliance + code-quality review per task

**The deep-dive skill** covers: the per-task workflow (implementer subagent → spec-compliance reviewer → code-quality reviewer → mark complete), why fresh subagents per task (no context pollution), the `context-budget-discipline` reference (4-tier context degradation model) and `gates-taxonomy` reference (4 canonical gate types), red flags that break the pattern, integration with `writing-plans` (you write the plan, this skill executes it), `test-driven-development` (each implementer enforces TDD), `requesting-code-review` (this skill's two-stage review IS the code-review pipeline).

---

## spike

**When to load:**

- User says "let me try this", "spike this out", "before I commit", "quick prototype"
- Comparing 2+ approaches (A vs B vs C) before picking one
- Need to validate a feasibility question that no amount of docs-reading will answer
- Frontier mode: previous spikes exist and you're picking the next thing to probe

**The deep-dive skill** covers: the 4-stage spike loop (decompose → research → build → verdict), the Given/When/Then feasibility framing, comparison-spike pattern (002a vs 002b with parallel `delegate_task`), the `spikes/<NNN>-<topic>/README.md + main.py` directory layout, the `## Verdict: VALIDATED | PARTIAL | INVALIDATED` close pattern, the head-to-head comparison table for parallel spikes.

**Do NOT use for:** anything with a known answer (just do research), production work (use `writing-plans`), post-validation (jump to implementation).

---

## hermes-skill-porting

**When to load:**

- User has a `.claude/` package, `.cursorrules/` bundle, `~/.codex/` config, or generic bash+skill bundle they want to expose to Hermes
- You're adopting an external AI agent workflow and want it integrated as Hermes skill + bash wrappers + cron jobs
- User wants to fork (modify) an external package rather than adopt it unchanged

**The deep-dive skill** covers: the 7-step generic porting playbook (Scan → Adapt → Lift → Wrap → Shim → Cron → Eval), the standard Hermes-native skill layout (`scripts/`, `references_<sub>/`, `commands_<name>/`), the 6 Windows-specific gotchas (Python `python3` Store alias, `Path("/c/...")` doubling, `ln -sf` failure, `gh` PATH, gitignore inline comments, PowerPoint file-lock), eval-driven verification (oneplusn's 10-test pattern), the Claude-Code-specific two-layer sub-playbook (slash command → bash wrapper).

---

## See also

- [`autonomous-coding-clis`](../autonomous-ai-agents/autonomous-coding-clis/SKILL.md) — sibling umbrella for **external coding CLIs** (Claude Code, Codex, OpenCode). Same discovery-index pattern, different family (calling out to other agents vs. building software in-process).
- [`kanban-orchestrator`](../devops/kanban-orchestrator/SKILL.md), [`kanban-worker`](../devops/kanban-worker/SKILL.md) — for multi-agent work where each task is independent and dispatched by the Kanban scheduler; complements `subagent-driven-development` for synchronous in-loop delegation.
- [`multi-profile-team`](../devops/multi-profile-team/SKILL.md) — for persistent agent teams (PM / engineer / QA / researcher); uses Kanban as the durable bus.
- [`oneplusn`](../productivity/oneplusn/SKILL.md) — the GitHub-Issues variant of the persistent team pattern; jobs ship via cron polling instead of in-process Kanban dispatch.
