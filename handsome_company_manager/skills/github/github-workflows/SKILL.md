---
name: github-workflows
description: "GitHub workflows: auth, issues, PRs, code review, repo management, codebase inspection. Each section is the canonical playbook for that workflow — works with `gh` CLI when installed, falls back to `git` + `curl` with personal access tokens or SSH keys."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Pull-Requests, Issues, Code-Review, Repositories, CI/CD, Releases, Actions, git, gh-cli]
    related_skills: [codebase-inspection]
---

# GitHub Workflows

This umbrella skill covers the full agent-side GitHub workflow. It folds together five previously separate skills (github-auth, github-issues, github-pr-workflow, github-code-review, github-repo-management) plus shared infrastructure. **For deep dives on each workflow, see the linked reference files — the SKILL.md is the index, the references are the playbooks.**

## When to Use

- User asks you to interact with GitHub (clone, push, open PR, review code, file an issue, manage releases, run Actions)
- User wants to set up GitHub auth on a new machine (HTTPS tokens, SSH keys, or `gh` CLI)
- User wants a complete PR lifecycle (branch → commit → push → CI → review → merge)
- User asks for a code review, an issue triage, or a release workflow

## Quick Auth Detection (used by every workflow)

The same auth snippet is the starting point for `issues.md`, `pr-workflow.md`, `code-review.md`, and `repo-management.md`. Drop it in at the top of any GitHub script:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

If `gh` is installed and authenticated, use it — it handles auth, pagination, and JSON. Otherwise `git` + `curl` + the token works the same way for 95% of operations. Full auth setup options (HTTPS, SSH, OAuth, gh CLI login) are in `references/auth.md`.

## The Five Workflows

| Workflow | Reference | When to load |
|---|---|---|
| **Auth & setup** | [`references/auth.md`](references/auth.md) | First time on a new machine, or when `gh auth status` fails. HTTPS tokens, SSH keys, `gh auth login`, env-var fallbacks. |
| **Issues** | [`references/issues.md`](references/issues.md) | Create, list, triage, label, assign, comment, close, search. Includes bug-report and feature-request templates. |
| **Pull Requests** | [`references/pr-workflow.md`](references/pr-workflow.md) | Branch → commit → push → open PR → monitor CI → auto-fix failures → merge. CI troubleshooting recipes in `references/ci-troubleshooting.md`. |
| **Code Review** | [`references/code-review.md`](references/code-review.md) | Review local diffs before push, review open PRs, leave inline comments, submit formal approve/request-changes reviews. |
| **Repo Management** | [`references/repo-management.md`](references/repo-management.md) | Clone, create, fork, set up branch protection, manage secrets, create releases, trigger Actions workflows, manage gists. API endpoint cheatsheet in `references/github-api-cheatsheet.md`. |
| **Cron Polling** | [`references/cron-polling.md`](references/cron-polling.md) | Periodic / scheduled GitHub scans (assignee diffs, comment counters). Bot-vs-human identity, `gh api` vs `gh search` reliability, "new since last poll" state patterns, self-reply-loop avoidance, multi-source triangulation before `[SILENT]`. |

For LOC/architecture analysis of a repo (not GitHub API), see the sibling skill [`codebase-inspection`](../codebase-inspection/SKILL.md) which uses `pygount` for language breakdowns and code-vs-comment ratios.

## Cross-Cutting Infrastructure

These files are shared across the workflows and live in this umbrella:

| File | Purpose |
|---|---|
| `scripts/gh-env.sh` | Source-able bash helper that exports `GH_OWNER`, `GH_REPO`, `GITHUB_TOKEN` from the same auth-detection logic above. `source` it at the top of any script that needs these vars. |
| `references/ci-troubleshooting.md` | Common CI failure patterns + fixes (test fail, lint fail, dependency conflict, timeout). |
| `references/conventional-commits.md` | Commit message format reference (feat:, fix:, refactor:, etc.) used in PR creation. |
| `references/github-api-cheatsheet.md` | Condensed REST endpoint reference (issues, pulls, actions, releases, gists) for `curl` fallbacks. |
| `references/review-output-template.md` | Markdown template for PR review summaries (Critical / Warnings / Suggestions / Looks Good). |
| `templates/bug-report.md` | Drop-in issue template for bug reports. |
| `templates/feature-request.md` | Drop-in issue template for feature requests. |
| `templates/pr-body-bugfix.md` | PR body template (links issue, describes fix, test plan). |
| `templates/pr-body-feature.md` | PR body template (summary, motivation, test plan). |

## Common Patterns

These commands show up identically across workflows — copy them as starting points.

### Detect auth method
```bash
gh auth status 2>/dev/null && echo "gh" || echo "no gh"
```

### Extract owner/repo
```bash
echo "$(git remote get-url origin)" | sed -E 's|.*github\.com[:/]||; s|\.git$||'
```

### Check CI on the current commit
```bash
gh pr checks --watch   # interactive
# or
gh run list --branch $(git branch --show-current) --limit 5
```

### Post a PR comment
```bash
gh pr comment <NUMBER> --body "..."
```

### Submit a formal review
```bash
gh pr review <NUMBER> --approve --body "LGTM"
gh pr review <NUMBER> --request-changes --body "See inline comments."
```

## See Also

- [`codebase-inspection`](../codebase-inspection/SKILL.md) — LOC/language analysis (separate concern, not GitHub API)
- `references/auth.md` — full auth setup walkthrough (HTTPS, SSH, `gh` CLI)
- `references/pr-workflow.md` — most common end-to-end use case
- `references/code-review.md` — review checklist (correctness, security, quality, testing, performance, docs)
