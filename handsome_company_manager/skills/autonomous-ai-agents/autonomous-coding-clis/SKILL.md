---
name: autonomous-coding-clis
description: "Delegate coding to external autonomous coding CLIs — Claude Code (Anthropic), Codex (OpenAI), OpenCode (provider-agnostic). Class-level umbrella for 'give me a coding CLI and let it run'. Each sibling skill is the deep-dive for one CLI; this umbrella picks the right one."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [coding-agent, delegation, autonomous-coding, claude-code, codex, opencode, subagent]
---

# Autonomous Coding CLIs — Pick One

Class-level umbrella for **external autonomous coding CLIs** that Hermes can drive via `terminal`. This umbrella is the **discovery index** — it's not meant to be loaded as a whole. Each section below names the dedicated skill that has the full flag reference, session model, and quirks.

> **Note:** For delegating to **Hermes itself** (spawning another `hermes` process, profiles, multi-agent flows, configuration, gateway setup), use the **`hermes-agent`** skill instead. That umbrella covers the entire "configure and operate Hermes" surface; this one is only for *external* coding CLIs.

| The user wants to… | Section to load |
|---|---|
| Use Claude Code (Anthropic) for a coding task | [Claude Code](#claude-code) |
| Use Codex (OpenAI) for a coding task | [Codex](#codex) |
| Use OpenCode (provider-agnostic, open-source) | [OpenCode](#opencode) |

Not sure which CLI to pick? Quick guidance:

| Property | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Vendor / model | Anthropic (Claude Sonnet/Opus/Haiku) | OpenAI (Codex models) | Provider-agnostic (any OpenRouter/Claude/GPT/etc.) |
| Best for | General coding, multi-turn refactor, deep review | Batch issue fixing, parallel PRs | Open-source / local / multi-provider portability |
| One-shot mode | `claude -p "<task>"` | `codex exec "<task>"` | `opencode run "<task>"` |
| Interactive mode | tmux-driven REPL | tmux-driven REPL | tmux-driven REPL |
| Session continuity | `--resume <id>` / `--continue` | saved sessions in `~/.codex/sessions` | `-c` / `-s <id>` |
| Self-test | `claude doctor` | (no built-in; smoke-test via prompt) | `opencode --version` + `opencode auth list` |

All three share the same basic shape: a coding task → a binary on a TTY → optionally review → return a diff. They differ in flag names, auth model, and session storage.

---

## Claude Code

**Use the `claude-code` skill** when:

- User says "use Claude Code" or "claude code" / "claude cli"
- User wants Anthropic's coding agent specifically
- Task requires extended multi-turn refactor / review with Claude's slash commands
- Need PTY-driven REPL with `/resume`, `/compact`, `/review`, etc.

The `claude-code` skill has the complete Claude Code v2.x flag reference, PTY dialog handling (workspace trust + permissions dialog), print-mode JSON output schemas (single + streaming), session continuation, parallel Claude instances, custom subagents, MCP integration, hooks, and Windows-specific quirks.

Install: `npm install -g @anthropic-ai/claude-code`

**Load** `claude-code` directly when starting work; this umbrella should not be loaded as a substitute.

---

## Codex

**Use the `codex` skill** when:

- User says "use Codex" or "codex cli" / "codex" (in the OpenAI CLI sense, **not** the food)
- User wants OpenAI's coding agent for batch / parallel / PR-review patterns
- Task fits the bounded-task Kanban-lane convention

The `codex` skill covers the `codex exec` one-shot pattern, `--full-auto` vs `--yolo`, PR review in temp clones, parallel worktree issue fixing, batch PR review, and the **Kanban codex-lane** pattern (deprecated `kanban-codex-lane` content is folded in as `references/kanban-codex-lane-pattern.md`).

Install: `npm install -g @openai/codex`

**Load** `codex` directly when starting work.

---

## OpenCode

**Use the `opencode` skill** when:

- User says "use OpenCode" / "opencode cli"
- User wants provider-agnostic, open-source coding agent (avoid vendor lock-in)
- Task needs to swap providers mid-flow without changing anything else
- Heavy use of OpenRouter-style multi-model routing

The `opencode` skill covers `opencode run` one-shot pattern, interactive TUI on `background=true, pty=true`, common flags (`--model`, `--thinking`, `--variant`), session resumption via `opencode -c` / `-s`, parallel workdir pattern, and the warning **never use `/exit`** — that's a different command entirely.

Install: `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`

**Load** `opencode` directly when starting work.

---

## See Also

- `hermes-agent` skill — for delegating to Hermes itself (NOT one of these CLIs)
- `subagent-driven-development` skill — for orchestrating **any** of these CLIs (or subagents) with two-stage review (spec compliance + code quality) per task
- `requesting-code-review` skill — pre-commit verification pipeline (security scan + baseline tests + independent reviewer subagent + auto-fix loop). Works with output from any of the three CLIs.
- `kanban-worker` skill — the dispatcher/lifecycle side; pairs with `codex` for the codex-lane pattern
