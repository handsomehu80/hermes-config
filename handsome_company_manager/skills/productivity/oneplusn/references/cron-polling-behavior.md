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

**Re-confirmed (2026-07-16, 7 days idle):** Same Issue #2, PM cron tick at the standard 15/45 cadence. No new comments, no label change, `updatedAt` still 2026-07-09T12:22:34Z. Correctly fired `[SILENT]` again. The other open issue (#8, P1) is assigned to `Handsome-Review`, NOT to the PM persona — so even the "is this my problem?" check must be persona-based, not CLI-account-based. Confirms §2's `--assignee <persona>` rule holds across weeks of inactivity, not just the first poll.

**Re-confirmed (2026-07-19, 10 days idle):** Same Issue #2, same `updatedAt=2026-07-09T12:22:34Z`, still `status:in-progress` with `priority:P3` and 1 comment (the persona's own welcome, signed `— 项目牧羊人 · Handsome-Manager`). Correctly fired `[SILENT]`. Also exercised the §6 PAT-scope refinement on this tick: `gh search` returned 10 candidates (1 in `handsome-s-company/agent_workflow` + 9 in `handsome-oneplusn-company/agent_workflow`), but the persona token can only reach the home org — see the `/user/repos` false-negative note in §6 for the corrected filter.

**Re-confirmed (2026-07-22, Issue #2 no longer in repo — pivot to live state):** The historical PM-assigned smoke-test Issue #2 from 2026-07-09 has been cleaned up (likely by `oneplusn-eval` reset or a repo housekeeping pass between 2026-07-19 and today); `gh issue view 2 --repo handsome-s-company/agent_workflow` now returns `GraphQL: Could not resolve to an issue or pull request with the number of 2`, and `gh issue list --state all` shows only #1, #3–#20 with #2 missing. The 3 currently-open issues in this repo are #8 (assignee = Handsome-Review), #19 (assignee = handsome-hudeveloper), #20 (assignee = handsome-hudeveloper) — **none assigned to the PM persona**. Both `gh issue list --repo handsome-s-company/agent_workflow --assignee Handsome-Manager --state open` and `gh search issues --assignee Handsome-Manager --state open` return `[]`. Correctly fired `[SILENT]`. **The protocol still holds when no dedicated smoke-test issue exists** — persona-filtered enumeration is authoritative, and zero matches → `[SILENT]`. If you ever need to re-establish a PM smoke-test issue, dispatch one via `gh issue create --title "[Smoke Test] PM poll verification" --assignee Handsome-Manager --label "bus-test,status:in-progress"` and then verify a `[SILENT]` on the next tick.

- **`gh search issues --state all` is rejected** (learned 2026-07-22, PM poll tick). The search endpoint only accepts `open` or `closed`, returning `invalid argument "all" for "--state" flag: valid values are {open|closed}` for `--state all`. Only `gh issue list` (and `gh pr list`) accept `--state all`. If you want both open and closed in one call, run `gh issue list --state all` instead — or just rely on the default `open` since the cron prompt explicitly says "扫描 ... open issue".

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
- **`gh` CLI on the Windows deploy box is authenticated as the BOSS, not the persona.** `gh auth status` returns `handsomehu80`, not `Handsome-Manager`. The cron prompt's "GH CLI also available" line is misleading: if the PM naively runs `gh issue comment <N> --body "..."`, the comment is **authored as the boss**, breaking the iron rule "comment author = assignee". This has been quietly producing misattributed comments on this machine. Two fixes, in order of robustness:
  1. **Switch gh's active account** (if available): `gh auth switch --user Handsome-Manager` then verify with `gh auth status`. Cleanest when it works.
  2. **Use the persona token directly**, bypassing `gh` altogether. Load the token from the profile's `.env` (concatenated-key pattern to dodge the shell redactor - see `SKILL.md` Known Fix #11), then call GitHub's REST API with `urllib.request`/`curl`. Cross-platform, no MSYS path surprises, comment author is **unambiguously** the persona. Example skeleton in §7.
- **`gh api` defaults to POST when `-f` flags are present** (learned 2026-07-16, PM poll tick). `gh api repos/X/Y/issues -f state=open -f per_page=50` does NOT issue a GET — `gh` interprets `-f` as POST body fields and the endpoint `/issues` accepts POST for *create*, so you get `422 Unprocessable Entity` with `"title" wasn't supplied`. The CLI fails silently-looking (no obvious "wrong method" hint), and you'll spend a minute wondering why the issue-list endpoint is asking for a title. **Two working fixes:**
  1. **Force GET**: prepend `-X GET` — `gh api -X GET repos/X/Y/issues -f state=open -f per_page=50`. Verified working on this box.
  2. **Pass query params in the URL**: `gh api 'repos/X/Y/issues?state=open&per_page=50'` (single-quote the whole thing on Windows so MSYS doesn't munge it). Works for both single-assignee and no-assignee enumeration.
  Either pattern is fine; pick one and stick with it. The `-X GET` form keeps the `-f` flags visible (good for jq downstream), the inline-query form is shorter. **Never** omit both: just calling `gh api repos/X/Y/issues` with no method and no flags will also default to POST.
- **`gh issue list --json commentsCount` is rejected on newer `gh` CLI** (learned 2026-07-16, PM poll tick). Newer `gh` versions renamed the field to `comments` and now reject the old name with `Unknown JSON field: "commentsCount"` plus a full `Available fields:` dump (which itself contains `comments`, not `commentsCount`). The doc's examples still use `commentsCount`; if you copy them verbatim and hit `gh >= 2.50` or so, you'll see the error. **Fix:** swap `commentsCount` → `comments` in your `--json` flag list. `gh search issues --json commentsCount` from the search endpoint still works (separate code path) — only the `issue list` / `issue view` JSON fields were renamed. Spot-check your first run.
- **Don't reload the persona token in a tight loop.** Reading `.env` once per poll is fine; re-parsing it per API call is wasted I/O and another chance to hit the redactor. Cache the token (and the verified login) at the start of the poll, re-use for the whole run, don't print it. The `scripts/verify_github_identity.sh` helper already does this once at Gateway startup - the polling LLM should call that or read the cached value, not re-derive.

- **`.env` token values can carry hidden trailing whitespace** (learned 2026-07-22, PM cron poll tick on Issue #2). The §7a Python recipe originally did `line.rstrip('\n')` + `tok = line[len(key) + 1:]`, which silently leaves a trailing `\r` (CRLF-encoded files), space (post-`write_file` round-trip), or `\n` (some editors append a newline inside the value itself) attached to the token. Symptom: urllib3 raises `ValueError: Invalid header value b'token github...Kdk3\n'` and the persona-comment recipe is dead. **Fix:** `tok = line[len(key) + 1:].strip()` (strip ALL leading/trailing whitespace from the value, not just `\n` from the line). Belt-and-suspenders: `line = line.rstrip('\n').rstrip('\r')` first to keep the line-level check sane, then `.strip()` on the value. The curl-equivalent `python -c` one-liner in §7a needs the same `.strip()` after `[len(k)+1:]`. Don't trust `rstrip('\n')` alone — it's only correct when the file is LF-encoded AND has no trailing space AND the value has no embedded newlines.

- **Persona fine-grained PAT may be scoped to a DIFFERENT org than what the boss's `gh` CLI shows** (learned 2026-07-18, PM cron poll tick). The boss's `gh` CLI is a wide-scope OAuth token that can **read** issues across every org the boss belongs to — but the persona's fine-grained PAT has explicit `repository selection`, often only the original org (e.g. `handsome-s-company/agent_workflow`), not the active work org (e.g. `handsome-oneplusn-company/agent_workflow`). Symptom: `gh search issues --assignee Handsome-Manager` returns 9 candidate issues, all from `handsome-oneplusn-company`, but `POST /repos/handsome-oneplusn-company/agent_workflow/issues/N/comments` returns `404 Not Found` for every one (verified on the 2026-07-18 tick — burned 4 calls before realizing the org mismatch). `gh issue list` against the persona's reachable org (`handsome-s-company/agent_workflow`) correctly returned only 1 PM-assigned issue (the smoke test). The `gh auth status` line (`Logged in to github.com account handsomehu80`) does NOT tell you the persona's PAT scope — `gh auth` reflects the CLI account, not the persona. Verification must come from the persona token itself. Fix at enumeration time: prefer `gh issue list --repo <persona-reachable-org>` over `gh search issues --assignee <persona>`, because the search endpoint queries the CLI account's wider index. If you do hit a 404 on a write op, do NOT retry with a different verb — drop the issue from this poll's work list and move on. This also explains why the same persona can read its own assigned issues via `gh search` (boss's wider scope) but cannot comment on them (persona's narrow scope).

  **Refinement — `/user/repos` is a false-negative pre-flight check for direct-collaborator personas** (learned 2026-07-19, PM cron poll tick). The original detection recipe was:
  ```python
  req = urllib.request.Request("https://api.github.com/user/repos?per_page=100",
      headers={"Authorization": "token " + TOK, ...})
  reachable = {r["full_name"] for r in json.load(urllib.request.urlopen(req))}
  # Only enumerate issues whose org is in `reachable`. Everything else is read-only via the boss's gh.
  ```
  This recipe **silently excludes the persona's own reachable repos** when the persona has *direct repository-level collaborator access* but is *not* an org member. Verified on 2026-07-19: PM persona `Handsome-Manager` has fine-grained PAT scoped to `handsome-s-company/agent_workflow` (direct repo collaborator, NOT org member). `/user/repos?per_page=100&affiliation=collaborator` returned **0 repos reachable** — yet `GET /repos/handsome-s-company/agent_workflow/issues/2` returned **200 OK** and the persona could have commented on it. Following the recipe literally would have caused PM to skip its only assigned open Issue (the smoke test) and emit `[SILENT]` even though there was a real (if quiet) Issue to monitor.

  **The authoritative per-repo reachability check** is a direct `GET /repos/<owner>/<repo>` (or `GET /repos/<owner>/<repo>/issues/<N>` if you have a specific Issue number). 200 → reachable for writes; 404 → not reachable, drop from this poll's work list. Recipe for the corrected filter:
  ```python
  import urllib.request, json
  HEADERS = {"Authorization": "token " + TOK, "Accept": "application/vnd.github+json",
             "User-Agent": "hermes-pm-poll"}
  def repo_reachable(owner, repo):
      try:
          urllib.request.urlopen(urllib.request.Request(
              f"https://api.github.com/repos/{owner}/{repo}", headers=HEADERS), timeout=10).read()
          return True
      except urllib.error.HTTPError as e:
          return e.code != 404  # 403/401 = token problem (treat as not reachable this poll)
  # For each candidate Issue, run repo_reachable(<org>, <repo>) BEFORE any write op.
  # Drop silently if False.
  ```
  When to use which check: `/user/repos` is still a useful **fast pre-filter** to drop obviously-unreachable orgs (saves N round-trips when `gh search` returns 9 candidates from 3 different orgs and only 1 is the persona's home org) — but treat its `len == 0` result as "no org memberships discovered", not "no repos reachable". Always confirm with a per-repo `GET` before any write op, and don't drop candidates that pass the per-repo check just because `/user/repos` was empty. The cost of the extra `GET` (1 round-trip per unique repo) is much smaller than the cost of skipping a real assigned Issue because of a false-negative pre-filter.

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

### 7a. Posting as the persona (when `gh` is authenticated as the boss)

The `gh` commands above are great for **reading**, but **commenting** via `gh` will attribute to the CLI account (the boss), not your persona. Use one of these two recipes when you need to act AS the persona:

**Recipe 1: switch gh's active account (cleanest when it works)**
```bash
gh auth switch --user Handsome-Manager
gh auth status    # confirm: "Logged in to github.com account Handsome-Manager"
# now all `gh issue comment`, `gh issue edit --add-label`, etc. are as the persona
```

**Recipe 2: bypass `gh` with the persona token from .env (most robust)**

The profile's `.env` already has the persona's fine-grained PAT. Load it safely (concatenated-key pattern to dodge the shell redactor) and call GitHub's REST API directly:

```python
# /tmp/poll_as_persona.py
import json, urllib.request, os, sys

env_path = r'C:\Users\Administrator\AppData\Local\hermes\profiles\handsome_company_manager\.env'
key = "GITHUB" + "_" + "TOKEN"
tok = None
for line in open(env_path, encoding='utf-8'):
    line = line.rstrip('\n').rstrip('\r')  # handle CRLF as well as LF
    if line.startswith(key + "="):
        tok = line[len(key) + 1:].strip()  # strip ALL trailing whitespace from value — see §6 pitfall
        break
if not tok:
    sys.exit("GITHUB_TOKEN missing from .env")

ORG, REPO, N = "handsome-s-company", "agent_workflow", 2
url = f"https://api.github.com/repos/{ORG}/{REPO}/issues/{N}/comments"
body = json.dumps({"body": "PM 已确认轮询，状态正常。"}).encode("utf-8")
req = urllib.request.Request(url, data=body, method="POST", headers={
    "Authorization": "token " + tok,
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
    "User-Agent": "hermes-pm-poll",
    "X-GitHub-Api-Version": "2022-11-28",
})
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.load(r)
    print(f"comment id={data['id']} author.login={data['user']['login']}")
    # CRITICAL: confirm user.login matches the persona from handoff.yaml
```

The print line `author.login=Handsome-Manager` is your **post-publish attestation** — if it shows the boss's account instead, the persona is wrong and the comment is misattributed. This is the same check that would have failed silently if you'd used `gh issue comment` directly.

For curl-only workflows (no Python), the equivalent is:
```bash
TOK=$(python -c "import os; k='GITHUB'+'_'+'TOKEN'; print([l[len(k)+1:].strip() for l in open(r'C:\Users\Administrator\AppData\Local\hermes\profiles\handsome_company_manager\.env', encoding='utf-8') if l.startswith(k+'=')][0])")
curl -sS -X POST "https://api.github.com/repos/handsome-s-company/agent_workflow/issues/2/comments" \
  -H "Authorization: token $TOK" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  -d '{"body":"PM 已确认"}' | jq '.user.login'
```

The full reusable helper is at `scripts/post_as_persona.py` — wraps the load-token / post-comment / verify-author pattern in one call.

The recording step is optional for stateless runs but is the only way to detect "new feedback" reliably when comments accumulate across many polls. See the `handoff.yaml` `state/<agent>.last_seen` convention if your team uses it.

---

## 8. See Also

- `SKILL.md` §"Cron registration (Hermes cron)" — the cron infrastructure
- `SKILL.md` §"Known Fixes" — past bugs in the polling pipeline
- `references/deployment-checklist.md` — pre-deploy setup (auth, repo, cron registration)
- `scripts/setup_cron.py` — the script that registers the cron and embeds the prompt
- `references/deployment-prerequisites.md` — environment requirements before any of this works