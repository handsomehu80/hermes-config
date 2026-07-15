# Git Push & Self-Close Workflow (when team workspace has no `origin` remote)

Captured from a real cron tick (2026-07-13 18:18, reviewer) where the team workspace `D:\onboarding\handsome-s-company` has a local git repo but **no `origin` remote configured**. Files are pushed to the org repo via GitHub Contents API, not `git push`. This is the standard pattern for oneplusn team workspaces that are initialized as bare local repos and managed centrally via `oneplusn sync` (which only handles the README).

## The Setup

```bash
$ cd <work-dir>
$ git remote -v
# (empty — no origin)

$ git log --oneline -3
91c007a Add insight-feasibility-scorecard.md (Issue #9)
e8a8366 自动加 .gitignore 保护敏感路径
dfc6235 更新团队 README (2026-07-12 22:54:54)
```

The boss manages the GitHub-side via `oneplusn sync` (which re-generates README.md from handoff.yaml and pushes that one file). Employees who need to land other files (audit reports, scripts, code from verification work, etc.) push via Contents API.

## The Workflow: 6 Steps for "Write, Push, Comment, Close"

When an issue is dispatched to you and your task body instructs you to produce a file in the org repo, follow this 6-step sequence. The order matters — if you skip step 4 (push) the boss won't see the deliverable; if you skip step 5 (comment) iron rule 2 is violated.

### Step 1 — Do the work locally
Write the file under `<work-dir>/` (e.g. `docs/insight-feasibility-scorecard.md`). This is the working tree of the local git repo, so files persist across cron ticks.

### Step 2 — Update label per iron rule 6
```bash
gh issue edit <N> --repo <org>/agent_workflow \
    --remove-label "status:todo" \
    --add-label "status:in-progress"
```

### Step 3 — Commit locally (optional but recommended for traceability)
```bash
cd <work-dir>
git add <path-to-file>
git commit -m "Add <file-name> (Issue #<N>)

<one-paragraph summary of what was done>"
```
The commit lands in the local repo. Note the commit SHA for the issue comment (helps the boss cross-reference if they clone the work-dir).

### Step 4 — Push to GitHub via Contents API
This is the **only** way to land files when there's no `origin` remote. The Contents API PUTs the file with the new content + commit metadata. Use Python or `gh api` directly:

```bash
# Via Python (handles binary-safe base64 + JSON cleanly):
python <<'PY'
import base64, json, subprocess
with open('<path-to-file>', 'rb') as f:
    content_b64 = base64.b64encode(f.read()).decode()
payload = {
    'message': '<commit message>',
    'content': content_b64,
    'branch': 'main'
}
result = subprocess.run(
    ['gh', 'api', '-X', 'PUT',
     '/repos/<org>/agent_workflow/contents/<path-to-file>',
     '--input', '-'],
    input=json.dumps(payload),
    capture_output=True, text=True
)
print('STDOUT:', result.stdout[:200])
print('RC:', result.returncode)
PY
```

A successful PUT returns JSON with a `content.sha` and `content.html_url`. **Save the SHA** — it's the canonical identifier for the file on GitHub. Note that this is the BLOB SHA, not the commit SHA; the local git commit SHA and the GitHub-side SHA are different identifiers for different things.

### Step 5 — Post structured comment on the issue (iron rule 2: comment-before-close)
```bash
gh issue comment <N> --repo <org>/agent_workflow --body "$(cat <<'COMMENT'
🔍 **<Role> 交付 (Issue #<N> — <short title>)**

## 做了什么
- <bullet 1>
- <bullet 2>
- <bullet 3>

## 产出
- **文件:** `<path-to-file>` (<size> <units>, <word-count> words)
- **推送:** Contents API 推到 main, blob sha `<blob-sha>`
- **本地 commit:** `<local-commit-sha>` (可选)

## 评分 / 结果 / 关键发现
<structured summary>

## 判决
✅ **通过自验证,close #<N>** (issue body 明确授权 only-reviewer-can-close + 自验后 close)

— <Agent-Name> (<role> 员工) @ <ISO8601-timestamp>
COMMENT
)"
```

### Step 6 — Update label and self-close (only if issue body explicitly authorizes)
Per iron rule 4, "reviewer can close simple self-created issues after passing review" AND when the issue body explicitly says "完成后可自 verify 后 close" or "only-reviewer-can-close". Read the body carefully — many issues require PM approval, in which case stop after step 5 and reassign.

**Body-granted override of the default rule.** The default `RULES.md` 铁律 4 says "老板创建的 / 复杂的 Issue → 等审批，assign 给老板，确认后再关". However, **if the Issue body explicitly grants self-close authority to the reviewer** (e.g. body line 2 says "本 Issue 由 reviewer 自验后可自 close (only-reviewer-can-close)", or PM's reassign comment includes "完成后可自 close" without a follow-up approval step), the body grant overrides the default rule. This is the boss's intentional delegation — the body is the contract.

**How to recognize the override:** search the body + all comments for these phrases:
- "自 close" / "self close" / "self-close" / "self-close 授权"
- "only-reviewer-can-close"
- "可自 verify 后 close" / "reviewer 验证后 close"
- "完成后 reviewer 直接 close"
- PM reassign comment without any "请把结果交给 PM 拍板" follow-up

If found → proceed to self-close in step 6. If absent and the issue was created by PM/boss → reassign to PM after step 5 (do NOT self-close; iron rule 4 default applies).

**Audit trail.** Always include the body-grant quote in the close comment so future debugging doesn't need to re-read the body:

```bash
gh issue close <N> --repo <org>/agent_workflow --comment "$(cat <<'COMMENT'
✅ Reviewer 自 close(Issue body 第 N 行明确授权: "<quote the body line>" + only-reviewer-can-close 铁规)。PR #<X> 已开,<deliverable summary>。<改进建议 link>。
— @<Agent-Name>
COMMENT
)"
```

This way the close event is self-documenting: anyone reading the timeline sees both the body grant and the close in adjacent comments, with no ambiguity.

```bash
# Update label to done
gh issue edit <N> --repo <org>/agent_workflow \
    --remove-label "status:in-progress" \
    --add-label "status:done"

# Self-close with a one-line summary
gh issue close <N> --repo <org>/agent_workflow \
    --comment "✅ <Role> 自验通过,close #<N>。产出:<one-line summary>。Per only-reviewer-can-close 铁规 + issue body 自验后 close 授权。"
```

## Multi-file config backups when `git push` is flaky

For a config backup containing several files, prefer one **atomic Git Data API commit** over multiple Contents API PUTs when HTTPS `git push` repeatedly resets or times out:

1. Read `refs/heads/main` and save its current SHA.
2. Create one blob per file with `POST /git/blobs`.
3. Create a tree with `POST /git/trees`, using the latest remote tree as `base_tree`.
4. Create one commit with `POST /git/commits`; set its only parent to the SHA from step 1.
5. Advance `refs/heads/main` with `PATCH /git/refs/heads/main` and `force: false`.
6. Re-read the branch SHA and each file's blob SHA before reporting success.

**Windows CRLF pitfall:** if the files were already committed locally, base64-encode the bytes from `git show <commit>:<path>`, not `Path.read_bytes()` from the working tree. Git may have normalized CRLF to LF in the committed blob; using working-tree bytes creates different blob/tree SHAs.

**Concurrent cron pitfall:** another employee may advance `main` while the backup runs. Never force-update the ref. If the PATCH is rejected as non-fast-forward, re-read the newest remote parent and recreate the tree/commit on top of it. The rebased GitHub commit SHA may differ from the original local commit SHA; report the verified **remote** SHA. Do not reset or rewrite the shared local branch, which another cron may be using.

## Common Pitfalls

1. **Forgetting the `branch` field in the Contents API payload.** The default branch on a freshly-created org repo is `main`, but if the team has renamed it (e.g. to `master`), PUT will silently land in the wrong branch. Always pass `branch` explicitly. Check `handoff.yaml` `repository.default_branch` to be sure.

2. **CRLF vs LF on Windows.** When pushing a `.md` file from Windows via Contents API, the file will be LF on GitHub-side (the API normalizes). When you `git pull` the same file, git may warn `LF will be replaced by CRLF`. This is harmless but noisy. To silence, set `core.autocrlf=input` in the local repo config.

3. **Files > 100 KB.** Contents API rejects files larger than 100 KB in a single PUT. The scorecard from this session was 26.5 KB, well under. For larger files (e.g. full code dumps), use `git import` via a temporary clone: clone the org repo locally, commit, push (this requires a one-time `gh auth setup-git` + a real PAT in `origin`, which is the boss's job, not the reviewer's).

4. **Step 2 label update before step 4 push.** If the push fails and you've already updated the label to `status:in-progress`, the issue is in a confused state (label says work in progress, but no deliverable exists). **Either** revert the label on push failure, **or** do step 4 first and step 2 after. The order in this doc (step 2 → 4) assumes low push-failure probability; in flaky-network environments, swap the order.

5. **The `gh api` PUT does not preserve directory creation.** If `docs/` doesn't exist on the org repo, PUTting `docs/insight-feasibility-scorecard.md` will create both the directory and the file in one call (Contents API handles this transparently). But if you PUT multiple files into a fresh directory, each PUT re-validates the path; the first succeeds with the implicit mkdir, the rest succeed normally. No special handling needed.

## When to Use This Workflow vs. `oneplusn sync`

| Situation | Use Contents API | Use `oneplusn sync` |
|---|---|---|
| Audit reports / scorecards / deliverables | ✅ | ❌ |
| README updates (the team's source-of-truth page) | ❌ | ✅ |
| Code committed by dev / reviewer as part of PR | ❌ (use PR flow) | ❌ |
| Handoff.yaml changes | ❌ | ✅ (sync regenerates README from handoff) |
| One-off scripts in `scripts/` | ✅ | ❌ |

**Rule of thumb:** `oneplusn sync` is for the team's "identity" files (handoff.yaml + README). Everything else is the employee's responsibility via Contents API.

## Observed in this Profile (2026-07-13)

The reviewer cron tick at 18:18 followed this exact 6-step sequence for issue #9:
1. Wrote `docs/insight-feasibility-scorecard.md` (26,508 bytes, 4200 words)
2. `gh issue edit 9 --remove-label status:todo --add-label status:in-progress`
3. Local git commit `91c007a`
4. Contents API PUT → blob sha `1ebf00d9fd9c468ec4ae0d71a1c6d3a8b8ccd72f`
5. `gh issue comment 9` with structured deliverable summary
6. `gh issue edit 9 --remove-label status:in-progress --add-label status:done` + `gh issue close 9 --comment "..."`

End state: issue #9 CLOSED with `status:done` label, deliverable visible at `https://github.com/handsome-s-company/agent_workflow/blob/main/docs/insight-feasibility-scorecard.md`, comment thread at `https://github.com/handsome-s-company/agent_workflow/issues/9#issuecomment-4956901298`.

## Cross-Reference

- `employee-repo-access.md` — pre-flight check for `gh api` access; if the employee PAT can't see the org repo, **no step of this workflow will work**. Run that recipe first.
- `deployment-checklist.md` — covers the initial boss-side `gh auth` setup but does not cover the Contents API workflow; the original package's per-employee push model assumed an `origin` remote that was never actually configured in the field.
