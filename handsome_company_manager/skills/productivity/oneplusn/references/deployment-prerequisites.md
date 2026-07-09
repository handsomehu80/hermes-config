# 1+N 数字员工 — Production Deployment Prerequisites

Captured 2026-07-09 during first real deploy attempt. Before running `oneplusn init --interactive`, the following must be true on the host.

## Hard blockers (verify first)

```
✓ hermes ≥ 0.15.x           hermes --version
✓ python ≥ 3.10             python -c "import sys; print(sys.version_info[:2])"
✓ git                       git --version
✓ gh ≥ 2.0                  gh --version
✓ PyYAML                    python -c "import yaml; print(yaml.__version__)"
✓ gh auth login             gh auth status  →  Logged in to github.com as <user>
✓ /d or work-drive          700 MB+ free; git init must succeed
```

Run `oneplusn deps` to verify all at once.

## Boss account (1 required)

- GitHub account with **Org owner** permission on the target org (or ability to create one)
- Email address (for issue notifications)
- PAT or `gh auth login` session — needed by `create_org.py` to call `gh org create` / `gh repo create`

## Digital employee accounts (N required)

This is the part that's not obvious from the SKILL.md. **Each employee needs its OWN GitHub account**, not just the boss's PAT. Why: `gh issue edit --add-assignee dev-01` requires `dev-01` to exist on GitHub.com as a user. The boss account cannot self-assign-as-someone-else.

Two viable patterns:

| Pattern | Pros | Cons |
|---|---|---|
| N real GitHub accounts (one per employee) | Clean audit trail, each cron uses its own gh auth context, can revoke independently | Account creation overhead, email per employee |
| 1 boss account + N PATs (one per employee, all owned by boss) | Cheap setup, fast | All actions look like "boss" on GitHub, assignment still works because gh issue edit takes any valid username |
| Skip GitHub entirely, use a local file bus | Quickest demo, no external deps | Loses the GitHub mobile/UI surface; cron polling logic still works against a JSON file |

For the user's actual situation (2026-07-09): path-of-least-resistance is "1 boss account + N PATs per employee" — keeps the GitHub-side assignment semantics without account-spam.

## Required inputs to `create_org.py`

Either via `--interactive` or as CLI flags:

```
--boss-username   <github-username>
--boss-email      <email>
--org-name        <org-slug>
--repo-name       <repo-slug, default: agent_workflow>
--boss-token      <PAT, optional if gh auth login already active>
```

The script writes `handoff.yaml` and patches the work-dir's `.gitignore`.

## Deploy sequence (verified)

```bash
# 1. Pick work-dir (D:\1plusn-team or similar)
mkdir -p /d/1plusn-team && cd /d/1plusn-team
git init -q && git config user.name "1+N Boss" && git config user.email "boss@1plusn.local"

# 2. gh auth
gh auth login   # web flow OR paste a PAT

# 3. Org + repo + handoff
python .../scripts/create_org.py --interactive    # fill boss/email/org

# 4. Employees (each needs its own gh account OR shared PAT strategy)
oneplusn add --work-dir /d/1plusn-team --role developer --name dev-01 \
  --github-username dev-01 --github-email dev-01@example.com
oneplusn add --work-dir /d/1plusn-team --role reviewer --name rev-01 \
  --github-username rev-01 --github-email rev-01@example.com

# 5. Push repo + README
oneplusn sync --work-dir /d/1plusn-team

# 6. Register cron
hermes cron create "30m" --name oneplusn-poll-dev01 \
  --script oneplusn-poll.sh --workdir /d/1plusn-team --no-agent
# (repeat per employee)
hermes cron create "1h" --name oneplusn-reaper \
  --script oneplusn-reap.sh --workdir /d/1plusn-team --no-agent

# 7. Verify
oneplusn status --work-dir /d/1plusn-team
hermes cron list | grep oneplusn
oneplusn-eval
```

## Eval expectations after first deploy

`oneplusn-eval` runs 10 tests against a temp sandbox. Expect 9-10/10:

- EVAL-08 (SOUL fetch mock) sometimes fails — it depends on a remote fetch returning the right shape. If the upstream `jnMetaCode/agency-agents-zh` repo changes its README, EVAL-08 needs an updated mock. Not a deployment blocker.
- The other 9 are deterministic and should be green. If any fail, investigate before going live.

## Known wrapper bug, fixed 2026-07-09

`oneplusn add --name X --role Y` was silently falling back to interactive mode because `oneplusn-add` and `oneplusn` both hardcoded `--interactive` in their case statement. Patched in both files. See `../SKILL.md` Known Fix #8. If you see "[✗] 名字不能为空" when you supplied `--name`, your wrapper is pre-patch — re-apply the fix.