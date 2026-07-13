---
name: agent-task-polling
description: Cron-driven polling pattern for AI agent task intake — detect new feedback on assigned work, compare against anchor state, process or silently exit. Anchor-state short-circuit, cross-system identity resolution, dual REST/GraphQL fallback, GitHub `gh` CLI gotchas. Use when the agent runs as a scheduled task that scans a queue (GitHub issues, tickets, queue entries) for new work.
---

# Agent Task Polling

The proven pattern for AI agent cron jobs that scan a queue for new work: **anchor-state short-circuit** — track last-seen state per task, only do work on diff, suppress output when nothing changed.

## When to Use This Pattern

- Cron fires every 15–60 min to scan a queue for new work
- Need to suppress notification when nothing has changed (cron delivery defaults to notify)
- Source system exposes a queryable API and supports state comparison

## Core: Anchor-State Short-Circuit

Capture a per-task anchor before doing any work:

- Identifier (URL / ID / queue position)
- `updated_at` / last-modified timestamp
- Comment count + last comment ID (or analogous "last activity" marker)
- Labels / status fields (sorted for stable comparison)
- Last event (actor, type, timestamp)

**Compare each field against the anchor:**
- All anchor fields match → output `[SILENT]` → no notification
- Any field differs → process the diff → structured report

This pattern has run 100+ consecutive polls successfully on a stable smoke-test fixture with no change, producing zero noise. The anchor can be sourced from the previous cron run's recorded output — no separate state file required for fixtures that genuinely don't drift.

## GitHub Implementation

`gh issue list --assignee @me` **fails outside a git repo** ("fatal: not a git repository") and `gh search issues --assignee @me` returns empty for non-standard assignees (bot personas). Use REST `/issues?filter=assigned` instead — it works cross-repo with no git context.

```bash
# Cross-repo assigned issues (no git context required)
gh api '/issues?filter=assigned&state=open' \
  --jq '.[] | {number, title, updated_at, comments, html_url, repo: .repository_url}'

# Specific login via REST search
gh api 'https://api.github.com/search/issues?q=is:open+assignee:<login>' \
  --jq '.items[] | {number, title, updated_at, comments, html_url}'

# GraphQL alternative when REST returns empty
gh api graphql -f query='query {
  search(query: "is:open assignee:<login>", type: ISSUE, first: 50) {
    nodes { ... on Issue { number title updatedAt url
      repository { nameWithOwner }
      comments(first: 0) { totalCount } } }
  }
}'

# Per-issue deep state (REST)
gh api /repos/<owner>/<repo>/issues/<n>            # main fields + assignee
gh api /repos/<owner>/<repo>/issues/<n>/comments   # comment IDs + bodies
gh api /repos/<owner>/<repo>/issues/<n>/events     # label/reassignment/close events

# Notifications — separate channel for @mentions, review requests
gh api '/notifications' \
  --jq '[.[] | {id, reason, subject: .subject.title, updated_at, repository: .repository.full_name}]'
```

## Assignee Identity Resolution

The session's GitHub login (e.g. `handsomehu80`) often differs from the bot persona recorded on issues (e.g. `Handsome-Manager`). The bot may post via the user's OAuth token without having its own GitHub login — `assignee:<session-login>` will miss it.

**Resolution steps:**
1. Get session login: `gh api /user --jq '.login'`
2. Get issue assignee(s): `gh api /repos/.../issues/<n> --jq '.assignee.login, .assignees[].login'`
3. If session login ≠ issue assignee, broaden the search:
   - `involves:<session-login>` (any participation: comments, mentions, labels)
   - Direct `<org>/<repo>` queries for known fixture repos
4. Cache the resolved identity in the anchor so subsequent polls don't re-resolve

## Decision Matrix

| Notifications | Anchor drift | Action |
|---------------|--------------|--------|
| empty | none | output `[SILENT]` |
| empty | yes | process the drift → structured report |
| non-empty | any | investigate each notification |

## Output Format (cron delivery)

- Cron job delivery: reply text only — the runtime handles routing
- `[SILENT]` (exact string, nothing else) suppresses notification when nothing to report
- Drift detected: structured report including issue number, repo, URL, anchor→current diff, and recommended action

## Anti-Patterns

- **Reporting "no issues found" every poll** → user gets spammed with noise
- **Recomputing the full diff each poll** instead of comparing to anchor → wasteful
- **Hard-coding the assignee login** → breaks when the bot persona or token rotates
- **Skipping the `events` endpoint** → misses label changes that don't bump `updated_at`
- **Skipping `/notifications`** → misses @mentions and review requests that don't appear in assigned issues
- **Loading anchor from a separate state file** when the previous cron output already records it → unnecessary I/O

## Pitfalls

- `gh issue list --assignee @me` errors with "fatal: not a git repository" outside a repo. Use REST.
- `assignee:@me` in GraphQL search may not match bot personas. Resolve the literal login first.
- `updated_at` does not change for label-only events on some issue types — always check events.
- REST `/issues?filter=assigned` may paginate silently — set `?per_page=100` and follow `Link: rel="next"` for large queues.
- `gh api graphql` exits non-zero on a successful query with warnings — don't conflate exit code with success when checking GraphQL output.

## See Also

- `references/github-polling-commands.md` — copy-pasteable API snippets with output examples
- `templates/anchor-state.json` — anchor state template