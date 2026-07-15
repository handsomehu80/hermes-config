---
name: exploration-methodology
description: "Class-level umbrella for the throwaway-generation / exploration toolchain — pick the right sibling for the current stage (ideate, feasibility-spike, design-sketch). Three siblings cover the ideation → feasibility → mockup stages of 'see if this is worth building' before committing to a real plan. Each sibling is the deep-dive for one stage; this umbrella is the discovery index."
tags: [methodology, exploration, ideation, spike, sketch, mockup, prototype, feasibility, throwaway, gsd]
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [methodology, exploration, ideation, spike, sketch, mockup, prototype, feasibility, throwaway, gsd]
    related_skills: [ideation, spike, sketch, writing-plans]
---

# Exploration & Throwaway-Generation Toolchain

Discovery index for the Hermes Agent **exploration family** — three siblings covering the "I'm not sure yet, let me feel this out" stages of building software/creative work, before committing to a real implementation plan. Same shape as GSD's `gsd-ideation` / `gsd-spike` / `gsd-sketch` trio, adapted as Hermes-native standalone versions.

> **Use this umbrella as a discovery index, NOT as a substitute for loading the sibling.** Each sibling is a substantial class-level skill; reading this index tells you which one to load for the current stage.

## How the three compose — typical flow

```
┌──────────────────────────────────────────────────────────────────┐
│  1. ideation        "I want to make something"                   │
│                       ↓ generate 3 project ideas + constraints  │
│  2. spike           "Is this idea feasible?" (code)              │
│     sketch          "What could this look like?" (UI/HTML)       │
│                       ↓ validated direction                     │
│  3. writing-plans  "OK, build it" → bite-sized plan              │
│  4. software-methodology → execute with TDD + subagents          │
└──────────────────────────────────────────────────────────────────┘
```

`ideation` starts from a blank slate; `spike` and `sketch` start from a chosen direction and validate from different angles (technical feasibility vs visual direction). Both `spike` and `sketch` produce disposable artifacts in `spikes/<NNN>-<topic>/` or `sketches/<NNN>-<stance>/` directories — throw them away once the direction is chosen, do NOT promote them into production code.

## Quick decision table — which sibling do I load?

| You're at this stage of "feel this out"... | Load |
|---|---|
| Don't have an idea yet — want project suggestions from creative constraints | [`ideation`](#ideation) |
| Have an idea, want to validate technical feasibility (will it work? which approach wins?) | [`spike`](#spike) |
| Have an idea, want to see 2-3 design directions before locking the UI | [`sketch`](#sketch) |
| Done exploring, ready for a real implementation plan | Use [`writing-plans`](../writing-plans/SKILL.md) instead — not a sibling here |

---

## ideation

**When to load:**

- User says "give me a project idea", "I want to build something", "I'm bored", "inspire me"
- User has tools/capabilities but no direction
- Working at the very beginning of a creative session
- Cross-domain prompts: code, art, hardware, writing, anything

**The deep-dive skill** covers: the "constraint + direction = creativity" formula, the constraint library (random pick vs matched to domain/mood), interpreting constraints broadly (a coding prompt can become a hardware project), generating 3 concrete project ideas per session, the user's job to pick one and start building.

**Do NOT use for:** anything where the user already has a specific idea — go to `spike` (feasibility) or `writing-plans` (ready to build) instead.

---

## spike

**When to load:**

- User says "let me try this", "spike this out", "before I commit to Y", "is this even possible?"
- Comparing 2+ technical approaches (A vs B vs C — same question, different libraries)
- Need to validate a feasibility question that no amount of docs-reading will answer
- "Frontier mode": previous spikes exist and you're picking the next thing to probe

**The deep-dive skill** covers: the 4-stage loop (decompose → research → build → verdict), the Given/When/Then framing for each feasibility question, the `spikes/<NNN>-<topic>/README.md + main.py` directory layout per spike, parallel comparison-spike pattern (002a/002b/002c) with `delegate_task` fan-out, the head-to-head comparison table, the `## Verdict: VALIDATED | PARTIAL | INVALIDATED` close pattern.

**Sibling alternate:** if the same idea needs UI/UX exploration instead of code-feasibility exploration, use [`sketch`](#sketch) in parallel.

**Do NOT use for:** anything with a known answer (just do research), production work (use `writing-plans`), post-validation (jump to implementation).

---

## sketch

**When to load:**

- User says "sketch this screen", "show me what X could look like", "compare layout A vs B", "give me 2-3 takes"
- Comparing 2-3 visual/UX directions before locking the design
- Need disposable HTML mockups (NOT production code) for a stakeholder review
- "Frontier mode": previous sketches exist and you're picking the next thing to mockup

**The deep-dive skill** covers: the 4-stage loop (intake → variants → head-to-head → pick winner), the three intake questions (feel, references, core action), single-axis variant design stance (NOT color-swap variants), the `sketches/<NNN>-<stance-name>/index.html + README.md` per-variant layout, `browser_navigate` + `browser_vision` for visual verification, the head-to-head comparison table, the `sketches/themes/tokens.css` shared-token convention.

**Sibling alternate:** if the same idea needs code-feasibility exploration instead of UI/UX exploration, use [`spike`](#spike) in parallel.

**Do NOT use for:** production HTML artifacts (use `claude-design` instead — one polished build, not 2-3 disposable variants), diagrams (use `architecture-diagram` / `excalidraw`), when the design is already locked (just build it).

---

## Boundary rules shared by all three

These come from the GSD project (the methodology source for `spike` and `sketch`) and apply to all three siblings:

- **Throwaway is the design.** A spike that takes 2 days to "clean up for production" was a bad spike. Same for sketches. The whole point is disposable.
- **Bias toward something the user can interact with.** Spikes and sketches fail when the only output is a log line or screenshot — the user wants to *feel* the output working. Default choices, in order: runnable CLI → minimal HTML page → small web server → unit test with recognizable assertions.
- **Disk stays clean.** Each spike/sketches folder is independent — no symlinking, no shared modules, no `core/` directory. Hardcode everything.
- **Head-to-head over solo.** When 2+ approaches answer the same question (spike) or 2+ visual directions answer the same brief (sketch), build them ALL then compare. The comparison IS the deliverable, not the individual builds.
- **`spike` and `sketch` may run in parallel.** If a feature needs both code-feasibility and UI-feasibility exploration (e.g., "should we use Server-Sent Events and what would the dashboard look like"), dispatch each as a separate `delegate_task` and synthesize.

## See also

- [`software-methodology`](../software-methodology/SKILL.md) — the umbrella for the production path (plan → test → execute → review). Pick from this umbrella once exploration is done.
- [`writing-plans`](../writing-plans/SKILL.md) — the bite-sized-task plan format used after a direction is locked. `ideation` / `spike` / `sketch` produce IDEAS and DIRECTION; `writing-plans` produces the commit-ready plan.
- [`kanban-orchestrator`](../devops/kanban-orchestrator/SKILL.md) — for distributing exploration across multiple agents when the scope warrants.
