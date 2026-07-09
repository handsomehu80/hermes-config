# Kanban Command Quick Reference

A condensed command reference for the `hermes kanban` family of commands. Use this when you need a quick lookup; the SKILL.md has the patterns, this is the syntax.

---

## Task creation

```bash
# Minimal
hermes kanban create "title" --assignee <profile> --body "..."

# With parent link (repeatable)
hermes kanban create "title" --assignee <profile> --parent $T1 --parent $T2 --body "..."

# Get the task_id back as JSON
hermes kanban create "..." --assignee eng --json | jq -r .task_id

# Goal mode (open-ended, worker runs until judge approves)
hermes kanban create "..." --assignee ast --goal --goal-max-turns 15 --body "..."

# Specify workspace type
hermes kanban create "..." --assignee eng --workspace worktree --branch wt/feature-x
hermes kanban create "..." --assignee eng --workspace dir:C:/projects/myapp
# (default is 'scratch', which is ephemeral)

# Triage (PM-created, specifier refines before ready)
hermes kanban create "..." --assignee ast --triage

# Custom max retries (default is 2)
hermes kanban create "..." --assignee eng --max-retries 5

# Tenant namespace (for multi-tenant boards)
hermes kanban create "..." --assignee eng --tenant project-x
```

## Task inspection

```bash
# List all tasks
hermes kanban list
hermes kanban list --status ready
hermes kanban list --json | jq '.[] | select(.assignee=="eng")'

# Single task detail
hermes kanban show <ID>

# Full event log (what the worker did, including diffs)
hermes kanban log <ID>

# Run history (each dispatch attempt)
hermes kanban runs <ID>

# Live tail of worker output
hermes kanban tail <ID>      # may timeout on long tasks
```

## Task state transitions

```bash
# Manual completion (rarely needed; workers do this)
hermes kanban complete <ID> --summary "..." --metadata '{...}'

# Manual block
hermes kanban block <ID> "reason here"

# Unblock a stuck task
hermes kanban unblock <ID> --reason "..."

# Reclaim (abort current worker, reset to ready)
hermes kanban reclaim <ID>

# Reassign to a different profile
hermes kanban reassign <ID> <new-profile> --reclaim

# Edit task metadata
hermes kanban edit <ID>

# Promote (todo → ready, used manually for triage)
hermes kanban promote <ID>
```

## Task cleanup

```bash
# Archive (hide from default list view)
hermes kanban archive <ID>

# Stats across all tasks
hermes kanban stats
```

## Dispatcher control

```bash
# Manual tick (force dispatcher to run once)
hermes kanban dispatch

# Standalone daemon (foreground, for debugging)
hermes kanban daemon --foreground
hermes kanban daemon --interval 30        # 30s tick
hermes kanban daemon --max 5              # cap spawns per tick
hermes kanban daemon --verbose            # log each tick

# Configuration
hermes config set kanban.dispatch_in_gateway true
hermes config set kanban.dispatch_interval_seconds 30
hermes config set kanban.failure_limit 3
hermes config set kanban.max_concurrent_workers 5
```

## Board management

```bash
# List boards
hermes kanban boards

# Initialize a new board (one-time)
hermes kanban init
```

## Common `jq` queries

```bash
# Get just task IDs
hermes kanban list --json | jq -r '.[].task_id'

# Get ready tasks only
hermes kanban list --json | jq -r '.[] | select(.status=="ready") | .task_id'

# Get tasks by assignee
hermes kanban list --json | jq -r '.[] | select(.assignee=="eng") | "\(.task_id) \(.title)"'

# Get tasks with parent links
hermes kanban list --json | jq -r '.[] | select(.parents | length > 0) | "\(.task_id) <- \(.parents | join(\",\"))"'
```

## Capturing task_id for parent links

```bash
# The most reliable pattern
T1=$(hermes kanban create "T1: research" --assignee ast --body "..." --json | jq -r .task_id)
echo "T1 = $T1"

T2=$(hermes kanban create "T2: implement" --assignee eng --parent $T1 --body "..." --json | jq -r .task_id)
echo "T2 = $T2"

# Verify the parent link
hermes kanban show $T2 | grep -A1 parents
# Expected:
#   parents:   ['t_<T1_ID>']

# Verify the child auto-promotes after parent done
hermes kanban show $T2 | grep status
# Should become 'ready' (not 'todo') once T1 is 'done'
```

## Capturing multiple parents (for synthesis tasks)

```bash
# Two research lanes feed one synthesis
T1=$(hermes kanban create "research: cost" --assignee ast --body "..." --json | jq -r .task_id)
T2=$(hermes kanban create "research: perf" --assignee ast --body "..." --json | jq -r .task_id)
# Both run in parallel (no link between them)
hermes kanban create "synthesize" --assignee pm --parent $T1 --parent $T2 --body "..."

# Verify both parents are referenced
hermes kanban show <synthesis_id> | grep -A1 parents
# Expected:
#   parents:   ['t_<T1_ID>', 't_<T2_ID>']
```

## Notification routing

```bash
# Enable cross-profile notifications (delivered to the home channel)
hermes config set notification_sources '["*"]'                # all profiles
hermes config set notification_sources '["default","pm"]'      # specific profiles

# Subscribe/unsubscribe a profile
hermes kanban notify-subscribe
hermes kanban notify-list
hermes kanban notify-unsubscribe
```

## Error message cheatsheet

| Error | Cause | Fix |
|-------|-------|-----|
| `kanban: unknown parent task(s): t_xxx` | Parent ID is wrong, placeholder, or in a different board | Check `hermes kanban show <id>` exists; remove placeholder; check board context |
| `usage: ... --parent: expected one argument` | `--parent` not given an argument, or used without repeating | Re-run with `--parent $T1 --parent $T2`, not space-separated |
| Smart approval denied on `hermes gateway restart` | Trying to restart gateway | Don't restart; trust the next tick to pick up new config |
| Card stuck in `todo` with parent in `blocked` | eng used `kanban_block(review-required)` | See Pitfall P2; unblock manually or fix eng SOUL.md |
| Worker respawns on unblock and immediately completes | Normal behavior, not an error | Accept the cost; consider Pitfall P2 fix |
| `kanban.db` growing large | Old archived tasks accumulating | `hermes kanban archive` for cleanup; backup kanban.db periodically |
