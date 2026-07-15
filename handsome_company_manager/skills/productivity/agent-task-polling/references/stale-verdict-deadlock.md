# Stale-Verdict Deadlock — Diagnostic & Resolution

When a cron-driven polling agent returns `[SILENT]` for hours on end while open Issues assigned to it remain untouched, the reflex is to suspect "cron died" or "Gateway crashed". On the 2026-07-15 PM bi-hourly report, both diagnoses turned out to be **wrong**. The actual cause was a *semantic* deadlock — the cron was firing every 30 min, the LLM was executing, the JSON output was being written — but the LLM was correctly classifying the situation as "no actionable work" under the existing anchor-state-short-circuit rule, while both sides of a NEEDS_WORK/待修 conversation waited for each other to move first.

This file is the diagnostic and the candidate Iron Rule #8 fix.

---

## Symptoms (any one is a strong signal)

1. **Cron output dir is fresh** — `<profile_home>/cron/output/<job_id>/` has new `.md` files dated within the expected tick interval.
2. **Last line of every recent `.md` is `[SILENT]`** — the LLM ran and explicitly chose to be silent.
3. **There are OPEN Issues assigned to this agent** — `gh issue list --assignee @me` returns non-empty.
4. **The most recent comment on those Issues is from the OTHER agent** — e.g. reviewer's "NEEDS_WORK — waiting on dev to fix" comment, with no subsequent comment from the polling agent.
5. **Hours pass with no anchor drift** — the polling agent keeps seeing "no new comments since my last" and returning `[SILENT]`.

If symptoms 1-5 all hold, the cron is healthy and the LLM is executing correctly — the **anchor-state short-circuit is producing a false negative** because the wait-signal (the other side's verdict) doesn't look like "new feedback" from this agent's perspective.

---

## The Diagnostic Recipe

Run all of these from any shell on the host. They're cheap, all read-only, and don't require the agent's profile to be active.

### Step 1: Is the cron actually firing?

```bash
ls -lat "<profile_home>/cron/output/" | head -5
# find the job_id directory for the agent's task-polling cron
ls -lat "<profile_home>/cron/output/<job_id>/" | head -5
```

**Heuristic:** if the most recent `.md` is within the expected tick interval (e.g. < 35 min for a 30-min cron), cron is firing.

### Step 2: Is the LLM executing?

```bash
# Most recent .md file size should be > 1 KB (the skill dump alone is ~50 KB; pure [SILENT] responses are ~80 KB)
ls -l "<profile_home>/cron/output/<job_id>/" | tail -3
```

**Heuristic:** if recent `.md` files are > 50 KB, the LLM is executing. If they're < 1 KB or empty, the script is crashing before the LLM runs (different problem — check the script's stderr).

### Step 3: Is the LLM returning [SILENT]?

```bash
tail -c 200 "<profile_home>/cron/output/<job_id>/<latest>.md"
# look for the literal string "## Response\n\n[SILENT]" at the tail
```

**Heuristic:** if the tail ends with `## Response\n\n[SILENT]`, the LLM decided to be silent. This is correct per the `[SILENT]` protocol, but may be the wrong decision if there are open assigned Issues with stale verdicts.

### Step 4: Are there open assigned Issues?

```bash
gh issue list --assignee @me --state open --json number,title,updatedAt
```

**Heuristic:** non-empty result + step 3 = stale-verdict deadlock (if last_verdict_age > Nh).

### Step 5: What is the last_verdict state?

```bash
gh issue view <N> --json comments --jq '.comments | sort_by(.createdAt) | reverse | .[0] | {author: .author.login, age_hours: ((now - (.createdAt | fromdateiso8601)) / 3600 | floor), body: .body[0:120]}'
```

**Heuristic:** if `author != self` AND `age_hours > 24` AND Issue is still open AND no comments from `self` since → stale-verdict deadlock is the diagnosis.

---

## The Real-World Transcript (2026-07-15)

| Signal | Observed |
|---|---|
| Cron output `.md` count | 51 files in last 24h for dev; 24 for reviewer |
| Most recent `.md` | dev `2026-07-15_16-02-31.md` (2 min before report), reviewer `2026-07-15_15-45-01.md` (15 min before) |
| `.md` file size | ~80 KB dev, ~50 KB reviewer (LLM executing, not crashing) |
| Last `.md` tail | `## Response\n\n[SILENT]` for both agents |
| Open Issues assigned to dev | #8 (NEEDS_WORK, last comment by reviewer at 2026-07-13T15:30Z) |
| Last comment by self on #8 | none (never commented — dev was assigned but waiting on reviewer's verdict to land) |
| Time since reviewer's NEEDS_WORK verdict | ~46 hours |
| Team activity delta vs prior 2h report (#11) | zero — same PRs unmerged, same Issues open, same silence |

**Wrong initial diagnosis (PM report #11):** "Gateway died." Reasoning was based on "no GitHub activity for 21h" — true but missing the cron-output-dir check.

**Correct diagnosis (PM report #12):** the cron ticker is healthy; both agents' LLM is healthy; both correctly classify the situation as "no new feedback" under the existing rule; the existing rule is **wrong for asymmetric wait states**.

---

## Why the Existing Rule Fails

The current `[SILENT]` decision rule is:

> If the latest comment on this Issue is from me, OR there are no comments yet, OR the latest comment is older than my anchor → `[SILENT]`.

The flaw: "no comments from the OTHER side since my last one" looks identical to "no new feedback" — but in a NEEDS_WORK/待修 loop, the OTHER side's last comment IS the wait-signal. From the polling agent's perspective, the comment "reviewer: NEEDS_WORK, please fix X and re-run" is **not new feedback** (no new comments arrived since it was posted), but it IS **work waiting for me**.

---

## Candidate Iron Rule #8 — Stale-Verdict Ping

Add to every employee's `RULES.md`:

> **Rule #8 (Stale-Verdict Ping):** If an Issue is assigned to me, in `state: open`, has at least one comment from another agent dated >48h ago, AND no comment from me in the issue's history → emit ONE ping per 24h that says "this Issue has been waiting Xh for my action, please confirm whether work is needed". Do NOT silently skip. The ping goes to a `[stalled]` log channel (not GitHub Issues, to avoid noise) but the PM profile's bi-hourly report surfaces any open pings.

**Implementation in poll-template:**

```python
def should_ping_stale_verdict(issue, self_login, now):
    comments = issue.get("comments", [])
    if not comments:
        return False  # first-touch — different rule
    last_other = next((c for c in reversed(comments)
                       if c["author"]["login"] != self_login), None)
    if not last_other:
        return False  # I commented last — not stale
    age_h = (now - parse_iso(last_other["createdAt"])).total_seconds() / 3600
    return age_h > 48
```

**Alternative (lighter):** don't add Iron Rule #8 yet — instead, the **PM profile's bi-hourly report** treats "0 external activity for N hours AND cron firing correctly AND open assigned Issues exist" as a 🔴 deadlock signal in §2 of the report. This puts the diagnosis burden on PM (already a structured observer) without changing per-employee poll behavior. Tradeoff: PM catches the deadlock at 2h cadence instead of real-time.

---

## Related Lessons from This Session

1. **The UPPERCASE cron job duplicate pattern** (`oneplusn-DEV-*` / `oneplusn-REVIEW-*` showing `last_status=error` while lowercase `oneplusn-dev-*` / `oneplusn-rev-*` show `last_status=ok` and actually fire correctly) — caused by earlier on-boarding scripts registering jobs in two naming conventions. The duplicate `last_status=error` is a *stale* state field, not a real error. Diagnostic: check `<profile_home>/cron/output/<job_id>/` for fresh `.md` files. If fresh, the `last_status=error` field is lying; the script is firing. Fix path: `hermes cron delete <id>` for the duplicate job ids, then verify only the lowercase job remains.

2. **Cron liveness ≠ team liveness** — three states, not two:
   - **Cron dead** → no new `.md` files in output dir → restart Gateway
   - **Cron alive + LLM executing + `[SILENT]`** → either genuinely no work OR stale-verdict deadlock; check for open assigned Issues
   - **Cron alive + LLM executing + doing work** → healthy

3. **PM bi-hourly reports should distinguish these three states explicitly** in §2 红黄绿灯风险 so the boss can tell "system healthy, team idle" from "system dead" at a glance.

---

## See Also

- `SKILL.md` §Decision Matrix — extended with the 4th row for stale-verdict deadlock
- `SKILL.md` §Anti-Patterns — 7th entry: "Stale-verdict deadlock"
- `references/github-polling-commands.md` — the Step 4-5 commands here
- `oneplusn/references/pm-bi-hourly-status-report.md` §2.5 — extended cron liveness check (3-state)