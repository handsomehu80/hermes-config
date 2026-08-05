# PM Bihourly: Long-Idle PR `mergeable=UNKNOWN` Staleness

> Companion to `pm-bi-hourly-data-quality.md` (`DQ-4`). The existing `oneplusn` SKILL.md pitfall §2.10 covers **(a)** upstream-merge-induced CONFLICTING flips and **(b)** silent force-push flips. This file covers the **third staleness class** that emerged on the 2026-08-04 PM #217 run: **PRs idle long enough that GitHub itself no longer has a current `mergeable` verdict**.

## Verified Case (2026-08-04, PM #217)

**Setup (from N=216, 2026-08-04 18:03 CST):**

> | #13 | Insight Ralph loop PoC 验证报告 | PR | **open** | boss | mergeable=true ✅ +917 |
> | #14 | per-tick USD/token budget circuit breaker | PR | **open** | dev | mergeable=false ❌ +435(需 rebase) |
> | #15 | per-tick scratchpad + evaluator harness | PR | **open** | dev | mergeable=false ❌ +901(需 rebase) |

**Verified N=217 (2026-08-04 20:09 CST, 2h later, fresh `gh pr view --json mergeable,mergeStateStatus`):**

```
PR #13: state=open, mergeable=UNKNOWN, mergeStateStatus=UNKNOWN, head=feat/issue-10-ralph-loop-poc, updated=2026-07-13T13:44:52Z (+917)
PR #14: state=open, mergeable=UNKNOWN, mergeStateStatus=UNKNOWN, head=feat/issue-6-budget-middleware, updated=2026-07-13T13:54:22Z (+435)
PR #15: state=open, mergeable=UNKNOWN, mergeStateStatus=UNKNOWN, head=feat/issue-7-evaluator-harness, updated=2026-07-13T14:14:15Z (+901)
```

ALL THREE PRs shifted from "verified verdict" (per N=216's claim) to `UNKNOWN`/`UNKNOWN` in 2 hours. The shift was NOT a merge QUEUE flip — it's the same `mergeable` field that previously returned `true`/`false`. Two real possibilities:

1. **GitHub's mergeable field is computed on-demand and GC'd after inactivity** — a 22-day-old PR (last `updated_at` 2026-07-13) has no recent push event, so the cached mergeable verdict is dropped. The PR still exists with `state=open`, but `mergeable` is no longer cached.
2. **The previous report's "true ✅" verdict was from a different source** — possibly `git merge-tree` (local) or a stale cached value. The N=216 report cited `mergeable=true ✅` for #13 with no warning that the source was local, not GitHub-side. PM #217's fresh query shows the GitHub-side truth.

## Why This Bites

The PM-direct-action one-liner pattern (SKILL.md §2.10) is built on the assumption that `gh pr view --json mergeable` is the **authoritative source** for "is this PR mergeable right now?". When `mergeable=UNKNOWN` for ALL PRs in a deadlock, the one-liner degenerates:

- ❌ Cannot say "merge #13" — boss will paste the command and either get a UNKNOWN error OR trigger a recompute that yields CONFLICTING.
- ❌ Cannot say "rebase #14/#15" — the rebase instruction assumes CONFLICTING; for UNKNOWN, the rebase is the right move **but** the conflict surface is unknown.
- ❌ Cannot say "wait one more cycle" — the next cycle may also return UNKNOWN (no push event to trigger recompute).

## The Fix (Verified in PM #217 one-liner)

**Step 1: Always re-query `gh pr view --json mergeable,mergeStateStatus` before emitting a one-liner**, even if the previous report claimed a known verdict. The previous report's verdict is only safe to carry forward when it's < 14 days old AND the PR's `updated_at` is within 7 days.

**Step 2: When `mergeable=UNKNOWN`, do NOT pretend to know the verdict.** The PM-direct-action one-liner must explicitly call out:

> ⚠️ `mergeable=UNKNOWN` (PR idle 22+ days; GitHub hasn't recomputed). Boss must first force a recompute:
>
> ```bash
> # Option A: comment-trick (cheapest)
> gh pr comment <N> --body "🔄 wake merge queue"
>
> # Option B: trivial commit (if comment doesn't trigger)
> git fetch origin
> git checkout feat/<branch>
> git commit --allow-empty -m "chore: ping merge queue"
> git push
>
> # Then re-query:
> gh pr view <N> --json mergeable,mergeStateStatus
> ```
>
> After recompute, the verdict is reliable and the standard one-liner applies.

**Step 3: Update the §2.10 Δ table to a 4-state classification:**

| State | Meaning | Action |
|---|---|---|
| `CLEAN` | mergeable=true, mergeStateStatus=clean | Proceed with `gh pr merge --merge` |
| `CONFLICTING` | mergeable=false, mergeStateStatus=dirty | Rebase first, then merge |
| `UNKNOWN` (this file) | mergeable=null/UNKNOWN, mergeStateStatus=UNKNOWN | Force recompute before merge |
| `MERGED` | state=closed, mergedAt set | Closed-loop; remove from one-liner |

**Step 4: When the ENTIRE §2.10 list is UNKNOWN**, the one-liner must shift from "merge these 3 PRs in order" to "first do these 3 preflight `gh pr comment` / empty-commit tricks, THEN re-query, THEN merge". PM-direct-action burns more keystrokes but the boss can still paste-line + execute.

## Companion Lessons (PM #217 same run)

- **`count_consecutive_zero_activity.py` handles "healthy idle → traffic drop" correctly** — verified for reviewer. Earlier N=210/N=209 reported reviewer as "🟢 healthy idle / 无新验证目标", then N=211+ reported "🔴 0 活动". The script correctly resets the trailing-run counter when an earlier row has the "healthy idle" classification (it doesn't count those as zeros). When reviewer hit 0 without the "healthy idle" prefix, the script counted it as a real zero. PME reported `trailing_run=1` because only ONE recent report had the unclassified zero — the older "healthy idle" reports correctly didn't accumulate. **Pattern**: when the same role has been both "healthy idle" AND "zero activity" in the trailing window, the script's verdict = the count of unclassified zeros only. PM should still read the §3 rows manually to confirm the classification.
- **N=220 archival trigger cadence works** — N=213 first previewed the N=220 trigger, N=215 reaffirmed, N=216 announced "剩 4 期 ≈ 8h", N=217 reports "剩 3 期 ≈ 6h". The countdown is monotonically decreasing as designed. If the boss doesn't act by N=220, the PM-direct-action auto-archive mechanism (close #19/#20 + PR comments + handoff.yaml update) is pre-armed.
- **Uppercase `REVIEW-*` shadow jobs have `last_status=error` + 190-byte "script failed" markers** (verified 2026-08-04): `REVIEW-task-polling` / `REVIEW-config-backup` / `REVIEW-memory-cleanup` all show `last_status=error` with ~190-byte output files containing `Mode: no_agent (script) / Status: script failed / Script exited with code 1`. The lowercase `rev-*` jobs are doing the real work (100KB+ payloads). The error state is consistent across all 3 reviewer shadows — they don't actually break anything because lowercase jobs are intact. Cleanup is `hermes cron rm <UPPERCASE-job-id>` for each.
- **`hermes cron list / run` is profile-scoped** — confirmed N=217: PM's cron list shows PM jobs only; to see dev/reviewer jobs, `hermes profile use <name>` first. The current path-based `python scripts/check_pm_cron_liveness.py` walks `<profile_home>/cron/jobs.json` directly, bypassing the CLI scope issue.

## Verification Recipe (replay-able)

```bash
# 1. Re-query long-idle PRs
for n in 13 14 15; do
  gh pr view $n --repo handsome-s-company/agent_workflow \
    --json number,state,mergeable,mergeStateStatus,headRefName,updatedAt
done

# 2. If UNKNOWN, force recompute on #13 (cheapest path)
gh pr comment 13 --repo handsome-s-company/agent_workflow \
  --body "🔄 wake merge queue (PM #217 preflight)"

# 3. Wait 30-60s, re-query
sleep 30
gh pr view 13 --repo handsome-s-company/agent_workflow \
  --json mergeable,mergeStateStatus

# 4. Update §2.10 Δ table with the new verdict before emitting next one-liner
```

## When to Update the SKILL.md Pitfall

The current `oneplusn` SKILL.md is **101,373 characters, over the 100 KB limit**. Patching requires a SKILL.md split: hoist the (a)/(b) PM-direct-action staleness content into a new `references/pm-bi-hourly-data-quality.md` (alongside existing DQ-1/DQ-2/DQ-3) and add a one-line See Also pointer. Until that refactor lands, THIS FILE is the canonical home for the (c) long-idle PR UNKNOWN case. The next SKILL.md slim-down migration should preserve the (c) bullet verbatim.
