# Cron Polling Behavior — How Each Employee's `task-polling` Run Should Behave

This is the **runtime playbook for the LLM that fires every 30 min on each digital employee's `task-polling` cron job**. The cron's prompt (from `scripts/setup_cron.py`) is one sentence; this file is what the LLM needs to honor that prompt correctly across many runs.

> **The cron prompt (verbatim)**:
> `轮询分配给你的 GitHub Issue：扫描 assignee 为自己的 open issue，对有新反馈的逐个处理；没有任务则静默退出，不发送任何通知。`

Translated: poll your assigned open Issues; process any that have new feedback; if no tasks, **silently exit and send no notification**.

---

## 1. The `[SILENT]` Delivery Protocol (CRITICAL)

When the cron job finishes and there is **nothing to deliver** (no new feedback to acknowledge, no work to report), respond with **exactly**:

```
[SILENT]
```

And nothing else. No markdown, no preamble, no apology, no summary. The Hermes cron subsystem uses this token as a control signal to suppress delivery. If you mix it with content (`"All clear this round. [SILENT]"` or `"[SILENT]\nNo issues today."`), the system either delivers the whole mess OR fails the suppression check — both are wrong.

When you DO have content to deliver, write your normal report — do not prepend `[SILENT]`.

**Verification:** the response should literally match the regex `^\[SILENT\]\s*$` if and only if you intend suppression.

---

## 2. The Two Identities (gh CLI vs. Bot Persona)

Each digital employee has **two distinct GitHub identities** that must NOT be conflated:

| Identity | Where it lives | What it's for |
|---|---|---|
| **Local `gh` CLI account** | `gh auth status` output | The token under which `gh` API calls run (e.g. `handsomehu80`). Set by the boss once per shell. |
| **Bot persona GitHub username** | `handoff.yaml` `agents/<name>.github_username` | The username that gets assigned Issues and shows up as the actor in Issue events (e.g. `Handsome-Manager`). |

**The bug to avoid:** running `gh search issues --assignee handsomehu80` returns zero hits, because **no Issue is assigned to the CLI account** — they're assigned to the persona. Use the persona username from `handoff.yaml`:

```bash
# WRONG — assignee of issues is NOT the local CLI login
gh search issues --assignee handsomehu80 --state open

# RIGHT — issues are assigned to the persona account
gh search issues --assignee Handsome-Manager --state open
```

If you don't know the persona username, read it from handoff.yaml:
```bash
gh_user=$(yq '.agents.pm-01.github_username' handoff.yaml)
gh search issues --assignee "$gh_user" --state open
```

---

## 3. Detecting "New Feedback" (the actual decision)

"New feedback" is **not** the same as "comments exist". A comment from your own previous run does not count.

**Heuristic (cheapest to most reliable):**

1. **Fetch the open issue list** assigned to the persona via `gh search issues --assignee <persona>`.
2. **For each candidate Issue**, fetch the comments via `gh issue view <n> --repo <org>/<repo> --json comments` or `gh api repos/<org>/<repo>/issues/<n>/comments`.
3. **Compare against a baseline**: the last-acknowledged state from the previous run. For a stateless run (e.g. first time, or after restart), use the **latest comment author**: if it's your persona username (e.g. `Handsome-Manager`), there is no NEW feedback from anyone else — the comment was already yours.
4. **Process only Issues where the latest comment is NOT from your persona** (i.e., someone else wrote something you haven't acknowledged yet).

**Do not rely solely on `commentsCount`** — it only tells you the number, not the author. The smoking-gun example:

| commentsCount | last comment author | What it means | Action |
|---|---|---|---|
| 0 | — | Issue newly assigned, never acked | Add welcome comment (assignment is itself the feedback signal) |
| 1 | persona | Your own previous welcome comment | `[SILENT]` |
| 1 | someone else | Real new feedback | Process per role |
| N | persona | You already replied N times, no one else | `[SILENT]` |
| N | other | New feedback since your last reply | Process |

---

## 4. The First-Run Welcome (assignment itself is feedback)

When an Issue appears in your assigned list for the **first time** (commentsCount=0), the assignment event IS the feedback signal — you must acknowledge it by:

1. Posting a **welcome / claim comment** explaining you're taking ownership.
2. Adjusting labels per the role's rules (e.g. PM moves `status:todo` → `status:in-progress`).
3. **Do NOT remove yourself as assignee** — that's how multi-agent reaping works (you'd just bounce it back to PM).

Save the issue's last-acknowledged state (last comment ID, last event timestamp) so subsequent runs can detect new feedback without re-processing.

---

## 5. The Smoke-Test Pattern (expected to be quiet for many polls)

Smoke-test issues — those with `[Smoke Test]` or `[冒烟]` in the title, or assigned via `oneplusn-eval` — are **expected to produce zero new feedback** across most polls. Once you've added your welcome comment, every subsequent poll should hit the `[SILENT]` path until someone (a human or another employee) adds a real comment.

If `[SILENT]` keeps firing for days on the same smoke-test Issue, **that is correct behavior**, not a polling bug. Do not "fix" it by commenting again or cycling labels.

**Verified pattern (2026-07-10):** Smoke Test Issue #2 in `handsome-s-company/agent_workflow` was assigned to `Handsome-Manager` on 2026-07-09. PM's welcome comment at 2026-07-09T12:22:24Z, last activity 2026-07-09T12:22:34Z. The next day's poll at the same offset fired `[SILENT]` because no one else had commented. Correct.

---

## 6. Pitfalls

- **Don't merge `[SILENT]` with content.** Either `[SILENT]` and nothing else, or a normal report. Never `"Done. [SILENT]"` or `"[SILENT]\nNo new issues."`.
- **Don't use the local CLI login as the `--assignee` filter.** Use the persona username from handoff.yaml.
- **Don't trigger on `commentsCount` alone.** A high count with the last comment by your own persona is not new feedback.
- **Don't trigger on persona-mismatch alone when comments are signed in-body.** If `gh auth status` logs in as the boss's CLI account but the comment body ends with `— 项目牧羊人 · Handsome-Manager` (or any persona signature), GitHub records `author.login` as the CLI account, NOT the persona. A naive `last_comment.author != my_persona` check will then falsely flag "new feedback" on every poll and cause an infinite reply loop. The reliable heuristic is: read the **body signature** or maintain a `state/<agent>.last_seen` baseline (last comment ID). The `§5` smoke-test pattern is what this looks like in practice.
- **Don't self-reassign on a smoke-test Issue.** If the Issue title contains `[Smoke Test]` / `[冒烟]`, leave assignee alone — the test is to verify you STAY assigned and process correctly.
- **Don't comment on every poll.** Each poll that finds no new feedback should produce zero new outbound activity (comments / labels / assignments).
- **Don't trust `gh search` JSON for comment authorship.** It returns `commentsCount` but no per-comment authors — fetch the full list with `gh issue view --json comments` when you actually need to decide.
- **Don't read `~/.hermes/profiles/<other>/...` from another profile's cron.** Each cron runs inside its own profile's data root (`$HOME` differs per profile). Cross-profile reads are intentional siloed.
- **`gh issue edit --add-comment` does NOT exist.** Posting a comment is a separate command: `gh issue comment <N> --repo <org>/<repo> --body-file <path>` (or `--body "..."`). `gh issue edit` only takes `--add-label`, `--add-assignee`, `--add-sub-issue`, `--add-blocked-by`, `--add-blocking`, `--body`, etc. — no comment flag. Trying `--add-comment` returns `unknown flag: --add-comment` and a usage dump.
- **`gh issue view --json subIssues` / `blockedBy` / `closingIssues` return a nested GraphQL `{nodes:[...], totalCount:N}` shape, NOT a flat array.** The naive `.subIssues[].number` jq returns null. Use `.subIssues.nodes[].number` or `.subIssues.nodes | length`. Applies to all `IssueConnection`-typed fields — if a `--json` query returns `expected an object but got: array`, it almost always means you forgot the `.nodes` step.
- **On Windows MSYS git-bash, `/tmp/<file>` is NOT a valid target.** `write_file` to `"/tmp/foo.txt"` resolves to `D:\tmp\foo.txt`, and bash's `cat /tmp/foo.txt` fails with `No such file or directory`. Always use absolute Windows paths: write to `D:/tmp/foo.txt`, then read via `$(cat "D:/tmp/foo.txt")` or pass directly to `gh ... --body-file "D:/tmp/foo.txt"`. macOS/Linux `/tmp/foo.txt` works unchanged.

---

## 7. Quick Reference Commands

```bash
# 1. Read persona username from handoff.yaml (this employee's GitHub identity)
GH_USER=$(yq ".agents.${PROFILE_NAME}.github_username" handoff.yaml)

# 2. Find open issues assigned to ME (the persona, not the CLI login)
gh search issues --assignee "$GH_USER" --state open \
  --json number,title,repository,updatedAt,url,commentsCount,assignees

# 3. For each candidate, fetch full comments to find the latest author
gh issue view "$N" --repo "$ORG/$REPO" --json comments

# 4. To post a comment (welcome / progress / status report) use the DEDICATED
#    command — `gh issue edit --add-comment` does NOT exist:
gh issue comment "$N" --repo "$ORG/$REPO" --body-file "/tmp/comment_$N.txt"
# (or use --body "..." for short text; --body-file for multi-line / Chinese / markdown)

# 5. Sub-issue + dependency wiring (PM uses these when decomposing tasks):
gh issue edit <PARENT> --add-sub-issue <CHILD>          # CHILD becomes a sub-issue of PARENT
gh issue edit <CHILD>  --add-blocked-by <BLOCKER>       # CHILD waits on BLOCKER
gh issue edit <CHILD>  --add-blocking   <BLOCKED>       # (mirror direction)

# 6. To READ sub-issue / blocking state, remember the nested GraphQL shape:
gh issue view "$N" --repo "$ORG/$REPO" --json subIssues,blockedBy \
  | jq '{subIssues: [.subIssues.nodes[].number], blockedBy: [.blockedBy.nodes[].number]}'

# 7. After processing, optionally record the last-acknowledged state
#    (last comment ID + last event timestamp) so the next poll has a baseline
```

The recording step is optional for stateless runs but is the only way to detect "new feedback" reliably when comments accumulate across many polls. See the `handoff.yaml` `state/<agent>.last_seen` convention if your team uses it.

---

## 8. See Also

- `SKILL.md` §"Cron registration (Hermes cron)" — the cron infrastructure
- `SKILL.md` §"Known Fixes" — past bugs in the polling pipeline
- `references/deployment-checklist.md` — pre-deploy setup (auth, repo, cron registration)
- `scripts/setup_cron.py` — the script that registers the cron and embeds the prompt
- `references/deployment-prerequisites.md` — environment requirements before any of this works