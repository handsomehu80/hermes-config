# Employee PAT Repo Access — Diagnosis & Repair

Captured from a real failure mode: cron tick for `handsome_company_reviewer` (2026-07-13 03:10) emitted `[SILENT]` not because there were no tasks, but because the reviewer's PAT in its profile `.env` could not resolve the org's private repo at all. Same root cause as the "GH 身份错位" note in the 2026-07-12 22:51 review session — and as at least three prior `[SILENT]` cron runs in the session log.

## Symptom

When an employee's cron tick polls GitHub, both CLI and REST fail with the same family of errors:

```bash
$ gh issue list --repo <org>/agent_workflow --assignee @me --state open
GraphQL: Could not resolve to a Repository with the name '<org>/agent_workflow'. (repository)

$ gh api /repos/<org>/agent_workflow
{"message":"Not Found","documentation_url":"https://docs.github.com/rest/...","status":"404"}
```

Compare with the **boss's account** under the same shell:

```bash
$ gh api /repos/<org>/agent_workflow
{"n":"agent_workflow","private":true,"vis":"private"}    # OK — repo visible
```

If boss sees it and the employee doesn't, the employee's PAT is missing collaborator / org membership on that repo. **This is the canonical signal — not "nothing to do".**

## Why It Happens

The `onboard_agent.py` flow generates each employee's GitHub account + PAT, writes it into `<work-dir>/agents/<name>/.env`, and records the username in `handoff.yaml`. But it does **not** automatically invite the new account as a collaborator on the org's repo. If the boss forgets the manual step (GitHub web UI → repo Settings → Collaborators → Add people), the new account's PAT is valid but has no access to the target repo.

Past deployments "worked" by accident — the cron happened to inherit the boss's `GH_TOKEN` from the keyring or from another env source, masking the issue. The moment the cron correctly loads the employee's own `.env`, the issue surfaces.

## Detection (cheap, run before doing any real work)

```bash
# In the employee's cron tick — first call of the tick:
TOKEN_ISSUER=$(gh api user --jq .login)
EXPECTED_REPO_VIEW=$(gh api "/repos/<org>/agent_workflow" --jq '.name // empty' 2>&1)
if [ -z "$EXPECTED_REPO_VIEW" ]; then
    echo "[⚠] $TOKEN_ISSUER cannot see <org>/agent_workflow — PAT lacks repo access" >&2
    # Cron tick continues with [SILENT] per task instructions
fi
```

The `gh api /repos/...` call is the cheapest probe. 404 / GraphQL "Could not resolve" = access missing. JSON object = fine.

**Two probes, not one.** `/repos/<org>/agent_workflow` returning 404 can mean either "PAT bad" (401, won't reach here) or "PAT fine, no collaborator". Run `gh api /user` first to confirm the token authenticates; then `/repos/...` to confirm the access. Without this disambiguation, you can waste cycles chasing an access fix when the real problem is a revoked PAT.

Also: the employee's `.env` typically has `GITHUB_TOKEN=` (not `GH_TOKEN=`). `gh` CLI accepts both, but export both to be safe: `export GH_TOKEN="$GITHUB_TOKEN"`.

## Fix (run as boss, once per missing employee)

```bash
# As boss (org owner / admin):
gh api /repos/<org>/agent_workflow/collaborators/<employee-github-username> \
    -X PUT -f permission=push
# → 201 Created on success; 404 if the boss isn't an org admin

# Verify from the employee's side:
export GH_TOKEN=<employee PAT>
gh api /repos/<org>/agent_workflow --jq .name    # should print agent_workflow
gh api "/repos/<org>/agent_workflow/issues?assignee=<employee>&state=open" \
    --jq 'length'                                # should be 0 or N (a number)
```

Web UI alternative (if `gh api` PUT returns 404 / "Must be an admin"):
1. Boss opens https://github.com/orgs/<org>/repositories
2. Click `<repo>` → Settings → Collaborators and teams → Add people
3. Type the employee's GitHub username → choose role (Write is enough for cron)

## What to Emit from the Cron Tick When Access Is Missing

**Still emit `[SILENT]`** — the task header explicitly says "没有任务则静默退出,不发送任何通知", and an empty polling result is the user-facing contract regardless of cause.

But add a **stderr-only warning** so future debugging doesn't have to repeat the diagnosis:

```bash
if [ -z "$REPO_VISIBLE" ]; then
    echo "[⚠ $(date -Iseconds)] $(gh api user -q .login) cannot see <org>/agent_workflow — PAT missing repo access; see references/employee-repo-access.md" >&2
    # Final stdout: exactly "[SILENT]"
    printf '[SILENT]'
    exit 0
fi
```

This keeps the user-facing delivery channel quiet (the cron system filters `[SILENT]`), while leaving a breadcrumb for future debugging.

### Concrete breadcrumb location (Hermes cron)

In Hermes cron runs, the LLM's final response **is** the delivery channel — there is no separate stderr sink that survives the session. To leave a breadcrumb, append to a per-profile log file:

```bash
PROFILE_LOG="$HOME/AppData/Local/hermes/profiles/<agent>/logs/poll-access.log"
mkdir -p "$(dirname "$PROFILE_LOG")"
echo "[$(date -Iseconds)] cron tick — <agent> PAT authenticated (login=<login>) BUT cannot see <org>/agent_workflow (HTTP 404). Boss fix needed: gh api /repos/<org>/agent_workflow/collaborators/<employee> -X PUT -f permission=push" >> "$PROFILE_LOG"
```

Why a file and not stderr: cron delivery strips everything except the final response, and Hermes session DB retention isn't guaranteed across runs. A per-profile log under `logs/` survives indefinitely and is grep-able from the boss's shell.

### Escalation when the condition is recurring

If the same access failure is detected in **3+ consecutive cron runs** (e.g. 03:40, 04:10, current on the same day), the next cron run should consider escalating: post a single notification to the PM agent (or any reachable collaborator) with the boss's repair command, instead of silently emitting `[SILENT]` again. The cron contract says "no work → no notification", but **persistent broken tooling is not "no work" — it's a blocked workstream** and the boss needs to know.

Heuristic for "consecutive" without keeping state in the cron itself: read the tail of the log file. If the last 3 entries all carry the same `[⚠]` line for the same repo, escalate; otherwise emit `[SILENT]` as normal.

```bash
LOG="$HOME/AppData/Local/hermes/profiles/<agent>/logs/poll-access.log"
RECENT_FAILURES=$(tail -5 "$LOG" 2>/dev/null | grep -c "cannot see <org>/agent_workflow")
if [ "$RECENT_FAILURES" -ge 3 ]; then
    # Escalate — post a comment or notify PM
    gh issue comment <pm-tracking-issue> --body "⚠ Reviewer cron has been blocked by missing repo access for $RECENT_FAILURES consecutive runs. Boss fix: gh api /repos/<org>/agent_workflow/collaborators/<employee> -X PUT -f permission=push"
fi
```

The exact escalation target (PM Issue? Boss's Telegram? weixin?) depends on the team's config — pick whichever channel the PM uses for routine cross-team alerts.

## Cross-Reference

- `deployment-checklist.md` — pre-flight question bundle covers the boss's `gh auth` step, but does **not** cover the per-employee invite step. Add a reminder there too.
- Past reviewer cron sessions (`session_search query=repo access review`): all show 404 + `[SILENT]` after the boss finished the smoke test (#5) and handed #5 back to the boss. The reviewer's token has never been granted collaborator access in this org — this is a persistent misconfiguration, not a one-off.
- The handoff.yaml `agent_type: hermes` block records `github_username` per employee — that username is what the boss must invite.