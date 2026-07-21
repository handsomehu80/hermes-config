# GitHub Polling Commands — Copy-Pasteable

All snippets assume `gh` CLI is authenticated (`gh auth status` to confirm). Use `--jq` to filter. Always prefer REST `/issues` endpoints over `gh issue list` outside a git repo context.

## Discover assigned open issues

```bash
# Cross-repo, no git context required
gh api '/issues?filter=assigned&state=open' \
  --jq '.[] | {number, title, updated_at, comments, html_url, repo: .repository_url}'

# Specific login (REST search)
gh api 'https://api.github.com/search/issues?q=is:open+assignee:handsomehu80' \
  --jq '.items[] | {number, title, updated_at, comments, html_url, repo: .repository_url}'

# GraphQL alternative when REST returns empty
gh api graphql -f query='query {
  search(query: "is:open assignee:handsomehu80", type: ISSUE, first: 50) {
    issueCount
    nodes { ... on Issue {
      number title updatedAt url
      repository { nameWithOwner }
      comments(first: 0) { totalCount }
    } }
  }
}' --jq '.data.search'
```

## Broader search (bot persona mismatch)

```bash
# Issues where you participated in any form (comments, mentions, labels)
gh api 'https://api.github.com/search/issues?q=is:open+involves:handsomehu80' \
  --jq '.items[] | {number, title, updated_at, comments, html_url, repo: .repository_url, assignee: .assignee.login, assignees: [.assignees[].login]}'
```

## Per-issue deep state

```bash
OWNER=handsome-s-company
REPO=agent_workflow
NUM=2

# Main fields (assignee, labels, comment count, updated_at)
gh api /repos/$OWNER/$REPO/issues/$NUM \
  --jq '{number, title, state, updated_at, comments, assignee: .assignee.login, assignees: [.assignees[].login], labels: [.labels[].name]}'

# Comments — last_comment_id is .[-1].id
gh api /repos/$OWNER/$REPO/issues/$NUM/comments \
  --jq '[.[] | {id, user: .user.login, created_at, updated_at, body_preview: (.body[0:120])}]'

# Events — label/reassignment/close (not all bump updated_at)
gh api /repos/$OWNER/$REPO/issues/$NUM/events \
  --jq '[.[] | {event, created_at, actor: .actor.login, label: .label.name}]'
```

## Notifications (separate channel)

```bash
gh api '/notifications' \
  --jq '[.[] | {id, reason, subject: .subject.title, updated_at, repository: .repository.full_name}]'
```

## Sourcing the anchor from previous cron output

The previous cron run's recorded output IS the anchor — no separate state file needed for fixtures that genuinely don't drift. Example anchor fields derived from `cron/output/<job-id>/<timestamp>.md`:

```
comments = 1
updated_at = 2026-07-09T12:22:34Z
last_comment_id = 4925026442
labels = ["type:feature", "status:in-progress", "priority:P3"]
last_event = labeled "status:in-progress" by handsomehu80 @ 2026-07-09T12:22:34Z
```

## Quick state-hash for drift detection

```bash
# Stable hash of issue state for fast drift check
gh api /repos/$OWNER/$REPO/issues/$NUM \
  --jq '{c: .comments, u: .updated_at}' \
  | shasum -a 256 | awk '{print $1}'
```

## Common errors and fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `fatal: not a git repository` | `gh issue list` outside a repo | Use `gh api /issues?filter=assigned` |
| Empty results on `assignee:<login>` | Bot persona posts via user's token | Use `involves:<login>` or direct repo query |
| `assignee:@me` returns 0 in GraphQL | @me qualifier doesn't match bot personas | Use literal login in query string |
| Events endpoint returns older events than comments | Events API is event-type-ordered, not time-ordered | Sort by `created_at` before selecting last |
| `/notifications` empty but issue was mentioned | Notifications may be marked read automatically | Check `last_read_at` vs issue `updated_at` |

## Pagination note

REST `/issues?filter=assigned&state=open` returns only the first 30 by default. For larger queues:

```bash
gh api '/issues?filter=assigned&state=open&per_page=100' --jq '...'
# Follow Link: rel="next" header if present
```