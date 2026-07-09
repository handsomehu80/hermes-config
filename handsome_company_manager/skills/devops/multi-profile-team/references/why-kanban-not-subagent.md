# Why Kanban + Profiles, Not subagent (delegate_task)

When a user asks for a "team of agents" or "persistent specialist roles", use **separate Hermes profiles communicating via Kanban**, NOT `delegate_task` subagents. The two patterns look superficially similar but solve different problems.

## Side-by-side

| Dimension | `delegate_task` (subagent) | Kanban dispatcher (profile team) |
|---|---|---|
| Lifecycle | Bounded by parent API loop | Outlives parent; restartable |
| Process model | Same process as parent | Separate `hermes -p <name>` subprocess |
| Context | Shared parent's context window | Isolated context, scratch workspace |
| Memory | Shared with parent | Per-profile memory (independent) |
| Failure recovery | Killed with parent | Card reclaims to ready queue, retry |
| Concurrent execution | Sequential (parent blocks) | Up to `kanban.max_concurrent_workers` (default 3) |
| Audit trail | In parent's transcript | Persistent SQLite events table |
| Best for | "I need a quick second opinion on X" | "I want a code engineer I can keep dispatching to" |

## Three failure modes if you use subagent for a team

1. **No persistence.** Subagent lives only inside the parent's `delegate_task` call. The next request restarts from zero — no "remember last time we built the auth flow".
2. **No concurrency.** `delegate_task` is synchronous; the parent blocks. The team ends up serial even when two workers could run in parallel.
3. **No recovery.** When the parent session ends (timeout, crash, user closes the terminal), every subagent dies. No way to resume the auth flow tomorrow.

## When subagent IS the right tool

- A reasoning sub-task inside the parent's work ("check this code for X bug", "summarize this 10-page doc")
- Anything that completes in < 5 minutes
- Anything that doesn't need to outlive the current turn

## The "team" mental model the user has

When a user says "I want a team of agents", they usually mean: 2-4 named roles with distinct personalities and skills, where the same engineer handles "the next coding task" the same way as the last one. This is **role-as-persistent-identity**, which maps to profiles. Subagent can't model this.

If the user is asking for a quick parallel sub-task instead, use subagent — don't over-engineer.

## When to use both

A profile can itself call `delegate_task` internally for short reasoning sub-tasks. Example: an eng worker spawning a quick "review this regex for safety" sub-call before committing code. That's fine. The profile is the persistent identity; delegate_task is one of its tools.
