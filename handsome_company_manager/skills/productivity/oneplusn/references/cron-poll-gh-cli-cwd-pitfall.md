# Pitfall: `gh issue list` returns 0 from wrong cwd, but `gh api` returns the real count

**Learned 2026-08-04, PM task-polling tick.**

## Symptom

PM cron LLM runs `gh issue list --assignee @me --state open --json ...` and gets 0 issues back. The cron tick concludes "no work" and emits `[SILENT]`. But the next 2h report (or a direct `gh api repos/<org>/<repo>/issues` probe) reveals the repo has 15+ open issues — most of them assigned to the dev, several to the reviewer, plus a few closed-but-recently-active Issues. The PM misread the state and missed whatever escalation was waiting.

## Root cause

On Windows git-bash, `gh` resolves the active repo from cwd via `git rev-parse --show-toplevel` (or equivalent). When the cron LLM's `terminal()` shell is at a cwd that isn't the team work-dir (e.g. `~`, `/tmp`, or a fresh Hermes session default that landed at `C:/Users/Administrator`), the repo-context detection fails silently and `gh issue list` returns 0.

The same cwd sensitivity affects:
- `gh issue list` (all variants)
- `gh pr list` (all variants)
- `gh workflow list`
- `gh run list`
- `gh label list`
- Any other `gh <noun> list` form that needs a repo context

`gh api repos/<org>/<repo>/...` and `gh repo view <org>/<repo>` always work because the path is explicit.

## Reproduction

```bash
# In a terminal whose cwd is NOT the team work-dir:
cd ~                                          # or any non-repo directory
gh issue list --assignee Handsome-Manager --state open --json number
# → 0 issues (WRONG, repo has 2 open)

# Same shell, but explicit path:
gh api repos/handsome-s-company/agent_workflow/issues?state=all\&per_page=50 \
  --jq '[.[] | select(.pull_request == null) | {n: .number, s: .state, asgn: [.assignees[].login]}]'
# → 15 issues, including 2 open assigned to handsome-hudeveloper
```

## Fix order (use the simplest that works)

1. **`cd "<work-dir>" && gh issue list ...` in the same `terminal()` call** — keeps cwd correct for the one call. Simplest, no flag dependency. Recommended default.
2. **Pass `--repo <org>/<repo>` explicitly** to every `gh issue list` / `gh pr list` / `gh workflow list` invocation. Works regardless of cwd. Slightly more verbose but explicit.
3. **Fall back to `gh api repos/<org>/<repo>/issues?state=all&per_page=50 | python -c "..."`** when (1) and (2) are impractical. Always works, but requires the slice-and-parse pattern from pitfall #18 in the main skill.

## Sanity-check recipe (first run of every cron tick)

```bash
# 1. Confirm cwd is the work-dir
pwd
# 2. Confirm gh can see the repo from cwd
gh repo view --json name --jq '.name'
# 3. (If 1 or 2 fails) re-run with explicit --repo
gh issue list --repo handsome-s-company/agent_workflow --assignee Handsome-Manager --state open
```

If `gh repo view` from cwd says "not a git repository" or returns nothing, the cwd is wrong — use `--repo` or `gh api` for the rest of the tick.

## Decision order (generalized)

> **Explicit-path API > explicit `--repo` CLI flag > cwd-dependent CLI.**

The cwd-dependent forms should be the LAST resort, not the first. When in doubt during a polling tick, prefer `gh api` (always works) over `gh issue list` (cwd-dependent).

## Why this didn't bite before

The bi-hourly report cron, daily-evening report cron, and config-backup cron all have their `workdir` field set to the team work-dir (or to the profile home) in `jobs.json`, so the LLM shell starts in the right directory. The task-polling cron's `workdir` is the SAME — but the LLM was running `terminal()` calls from the default cwd without `cd` first, hitting the cwd-sensitivity bug. The fix: always start task-polling shell commands with `cd "<work-dir>" && ...` or use `--repo` / `gh api` explicitly.

## Related pitfalls in the main skill

- #14 (MSYS path translation for `gh api /repos/...` with leading slash) — different bug, same `gh api` workaround family
- #17 (`urllib.request` as last-resort GitHub API client) — works when `gh` cwd is also broken
- #18 (`gh api | python -c` slice-and-parse) — companion to `gh api` when stderr leaks into stdout
