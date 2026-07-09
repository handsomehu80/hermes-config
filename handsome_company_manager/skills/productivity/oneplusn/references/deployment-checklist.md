# 1+N Digital Employees — Pre-Deployment Checklist

Distilled from a real first-deploy session (2026-07-09). Use BEFORE you start running `oneplusn init` so you can pre-emptively ask for every blocker at once, instead of bouncing the user through one missing input at a time.

## The Blocker Chain (in dependency order)

Each blocker blocks the NEXT step. Don't promise progress past step N until step N is unblocked.

| # | Step | What it produces | What blocks it |
|---|---|---|---|
| 1 | `oneplusn deps` | confirms hermes/python/git/gh/PyYAML installed | missing package — user must install |
| 2 | `create_org.py --interactive` OR hand-written handoff.yaml | boss/email/username/org/repo populated | user must supply: boss email, boss GitHub username, org name (new or existing), repo name (default `agent_workflow`) |
| 3 | `gh auth login` (boss account) | `gh` CLI can hit the org + repo | user must run `gh auth login` in THIS shell — token is per-shell, not per-user. Verify with `gh auth status` and a second-channel check (browser). |
| 4 | `gh repo create` (or verify existing) | the `agent_workflow` repo exists on GitHub | boss account must have write access to the org. Verify org membership: `gh api /orgs/<org>/members --jq '.[].login'` |
| 5 | `oneplusn add <name> --role X --github-username <gh-user>` × N | N employees registered with profile + SOUL + RULES + cron | each employee needs its own GitHub username + email. Without that, `gh issue edit --add-assignee` can't assign work to them. |
| 6 | `hermes cron create` × N | polling jobs live in `state.db`, survive restarts | cron registration is local — no external blocker once step 5 is done |

## Pre-Flight Question Bundle

When the user says "deploy the 1+N team" or similar, ask for ALL of these in one round:

```
1. 你的 boss GitHub 用户名是?    (例如 handsomehu80)
2. 你的 boss 邮箱是?            (通知 + handoff 标记用)
3. Org 名?                      (新自建 / 现成 / 个人账号下)
4. 仓库名?                      (默认 agent_workflow,通常不用改)
5. gh 已登录了吗?               (要求: 你当前这个 shell,不只是另一个窗口)
6. 起步上几个员工?              (dev + rev 最少;全栈 8 人最多)
7. 每个员工的 GitHub 用户名?    (可以是真实账号,也可以是 PAT 占位账号)
   (没想好可先 0,后面 oneplusn add 增量加)
```

If the user can't answer all of them at once, prioritize 1-5 (everything from there down the chain blocks). Step 6-7 can be deferred.

## Verifying gh Auth (when user says "I'm logged in")

The most common false-positive in this workflow: user runs `gh auth login` in a *different* terminal/window, then reports back. Token state is per-shell. Two independent checks:

```bash
# Check 1: CLI in this shell
gh auth status

# Check 2: browser (if browser tools available)
browser_navigate https://github.com/settings/tokens
# → if redirects to /login, NOT authenticated from this session's POV
```

If both fail, the user must run `gh auth login` again in THIS shell, OR export `GH_TOKEN=...` here:

```bash
gh auth login --web      # easiest — opens URL, paste code back
gh auth login --with-token <<< "ghp_..."  # for PAT
export GH_TOKEN="ghp_..."  # if they have it from another terminal
```

## Known Bug: --interactive Swallows --name

**Hit during 2026-07-09 deployment.** The `oneplusn-add` bash wrapper used to always pass `--interactive` to `onboard_agent.py`. The script short-circuits to `interactive_mode()` whenever `--interactive` is set, ignoring `--name`/`--role` from CLI. Result: `oneplusn add --name dev-01 --role developer` silently prompts for name and errors with `[✗] 名字不能为空`.

**Fix** (applied): wrapper only passes `--interactive` when `--name` is absent. Patch both `oneplusn` and `oneplusn-add` (Windows copies).

**Test**: `oneplusn add --name smoke-test --role developer` should NOT prompt for name or role. If it does, the wrapper still has the bug — patch it again.

See `claude-package-to-hermes-skill` Anti-Patterns section for the general porting rule.

## Sequence to Run After All Blockers Unblocked

```bash
# 1. Verify deps
oneplusn deps

# 2. Verify auth + org membership
gh auth status
gh api /orgs/<org>/members --jq '.[].login' | grep <boss-username>

# 3. Verify or create repo
if ! gh repo view <org>/<repo> &>/dev/null; then
    gh repo create <org>/<repo> --private --description "1+N digital employee workflow bus"
fi

# 4. Onboard employees (one per call)
oneplusn add --work-dir <team> --name dev-01 --role developer \
    --github-username <gh-user> --github-email <email>

oneplusn add --work-dir <team> --name rev-01 --role reviewer \
    --github-username <gh-user> --github-email <email>

# 5. Verify team state
oneplusn status --work-dir <team>

# 6. Register cron polling per employee (off-set minutes so they don't all fire at :00)
hermes cron create "30m" --name "oneplusn-poll-dev-01" \
    --script oneplusn-poll.sh --workdir <team> --no-agent
hermes cron create "30m" --name "oneplusn-poll-rev-01" \
    --script oneplusn-poll.sh --workdir <team> --no-agent

# 7. Verify cron registered
hermes cron list | grep oneplusn

# 8. Self-verification
oneplusn-eval
```

## What NOT to Skip

- **Don't commit handoff.yaml** — it has the boss's PAT. `.gitignore` should auto-block it (verify with `git check-ignore handoff.yaml`).
- **Don't onboard employees before gh auth** — the script will fail trying to verify the GitHub account exists.
- **Don't trust "I'm logged in" without checking** — see "Verifying gh Auth" above.

## See Also

- `SKILL.md` Known Fixes #8 — `--interactive` swallowing bug (with patch details)
- `claude-package-to-hermes-skill` Anti-Patterns — the same bug as a general porting pitfall
- `references_org/`, `references_agent/` — detailed phase-by-phase runbooks from the source `.claude/` package