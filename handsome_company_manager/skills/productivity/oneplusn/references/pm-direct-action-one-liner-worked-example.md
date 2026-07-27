---
name: pm-direct-action-one-liner-worked-example
description: "Verified worked example of the §2.10 PM-direct-action one-liner from PM #156 (2026-07-27). The canonical copy-pasteable merge plan after 7 consecutive bi-hourly reports of boss-merge-PR deadlock. Use as the template shape when the next ≥3-consecutive 2h cycle fires against the same deadlock — pair with pm-bi-hourly-status-report.md §2.10 for the structural rules."
version: 1.0.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [pm-direct-action, boss-merge-pr-deadlock, one-liner, worked-example]
---

# §2.10 PM-Direct-Action One-Liner — Verified Worked Example (PM #156, 2026-07-27)

The structural rules for the PM-direct-action one-liner live in
`pm-bi-hourly-status-report.md` §2.10. This file is the **canonical real-world
example** that the rule produces when applied against a 7-consecutive-report
boss-merge-PR deadlock. Future PM agents should reproduce the structure
exactly when they hit the same escalation threshold (3+ consecutive 2h reports
without boss action).

---

## The Trigger Conditions (all three must hold)

1. **3+ consecutive 2h reports have flagged the same boss-merge-PR deadlock** —
   confirmed by walking `<profile_home>/cron/output/<pm-bihourly-job-id>/*.md`
   and reading each report's §2 红黄绿灯 risk row.
2. **Boss has not picked any A/B/C option from prior reports** — the same
   decision has been offered for ≥2 cycles with no resolution. A/B/C menus
   stop being useful past this point.
3. **The unblock action is on the boss, not an employee** — the gating PRs
   have reviewer-PASS already (per the matching closed Issues). Only the
   `gh pr merge` keystroke (or rebase + push for CONFLICTING ones) is missing.

When all three hold, the next report ships a **copy-paste-able one-liner**
instead of an A/B/C menu. The shift is automatic and silent — no need to
ask the boss for permission to escalate.

---

## The Pre-Flight: Re-Verify Mergeable State JUST BEFORE Writing the One-Liner

Per `pm-bi-hourly-status-report.md` §2.9 + §2.13, never copy-paste a previous
report's mergeable verdict. Always re-query with per-PR `gh pr view` calls
(GitHub-side, fresh) — bulk `gh pr list --json mergeable` returns `UNKNOWN`
for all PRs (cache-not-primed trap). Canonical one-shot pre-flight:

```bash
for n in 13 14 15; do
  gh pr view "$n" --repo <org>/agent_workflow \
    --json number,state,mergeable,mergeStateStatus,headRefName,additions \
    --jq '"PR#\(.number) | state=\(.state) mergeable=\(.mergeable) mergeStateStatus=\(.mergeStateStatus) +\(.additions) \(.headRefName)"'
done
```

**Field interpretation (recap of §2.9):**

| `mergeable` | `mergeStateStatus` | Action |
|---|---|---|
| `MERGEABLE` | `CLEAN` | Direct `gh pr merge <N> --merge --delete-branch` |
| `MERGEABLE` | `BEHIND` | `git fetch && git rebase origin/main && git push --force-with-lease` then merge |
| `CONFLICTING` | `DIRTY` | Rebase first, then merge |
| `CONFLICTING` | `BLOCKED` | Check required checks (rare on this repo) |
| `UNKNOWN` | `UNKNOWN` | Wait 30s and re-query, or fall back to `git merge-tree` |

---

## The Δ vs Previous One-Liner Table (Required for Consecutive Reports)

When the same one-liner is being emitted for the Nth consecutive 2h cycle, the
report MUST include a Δ table showing current vs previous-cycle verdict. If
any PR flipped state (CLEAN↔CONFLICTING), the one-liner MUST be re-emitted
with rebase steps added or removed. State can flip in either direction
between cycles (PR #15 was MERGEABLE on PM #51 and CONFLICTING on PM #52 due
to PR #18 merging into `main` in between, per `pm-bi-hourly-status-report.md`
§2.9 verified-real-case table).

```markdown
**先查最新 mergeable 状态(本 tick 已验证,本表即权威):**

| PR | mergeable | mergeStateStatus | updatedAt | 处置 |
|---|---|---|---|---|
| #13 | MERGEABLE | CLEAN | 2026-07-13T13:44:52Z (332.3h 前) | ✅ 直接合 |
| #14 | CONFLICTING | DIRTY | 2026-07-13T13:54:22Z (332.2h 前) | ⚠️ 需 rebase |
| #15 | CONFLICTING | DIRTY | 2026-07-13T14:14:15Z (331.8h 前) | ⚠️ 需 rebase |
```

The "处置" column is the **boss-action instruction** for each row, not just
a status label. The boss reads this table to know what to do for each PR.

---

## The One-Liner Itself — Three Sequential Bash Blocks

The one-liner is split into **three sequential steps** so the boss can paste
them one at a time and verify each step's success before moving to the next.
Combining them into a single mega-command risks mid-execution failures that
leave the repo in a half-merged state.

```bash
# === 1) PR #13 — 直接合并(零冲突),1 个 keystroke 解锁后续验证 ===
gh pr merge 13 --auto --squash --body "Insight: Ralph loop PoC E2E verification report (Issue #10/#11). PM-direct-action per bi-hourly #156."

# === 2) 派单 dev 立即 rebase #14/#15(命令已就绪) ===
gh issue comment 14 --body "PM-direct-action #156: \`gh pr checkout 14 && git rebase origin/main && git push --force-with-lease\`  — 解除与 main 的冲突,reviewer PASS 状态不变。"
gh issue comment 15 --body "PM-direct-action #156: \`gh pr checkout 15 && git rebase origin/main && git push --force-with-lease\`  — 解除与 main 的冲突,reviewer PASS 状态不变。"

# === 3) #14/#15 rebase 后(CLEAN 转过来)再粘贴: ===
# gh pr merge 14 --auto --squash --body "P1 USD/token budget circuit breaker. PM-direct-action. Closes #6."
# gh pr merge 15 --auto --squash --body "P1 scratchpad + fresh-context evaluator. PM-direct-action. Closes #7."
```

**Step design rationale (cite this in the report so the boss sees the chain):**

- **Step 1 = CLEAN PRs only.** Zero conflict risk, maximum unlock value. PR #13's merge
  brings the Insight E2E verification report into main, which is a non-controversial
  deliverable. Doing this first means the next report can already cite "PR #13 merged"
  as a confirmed unblock, even if #14/#15 stall.
- **Step 2 =派单 dev to rebase.** The dev is the one who knows the intent of their
  branch — PM should NOT auto-rebase. Comment on the PR's linked Issue so the rebase
  request shows up in dev's normal polling tick.
- **Step 3 = merge after rebase.** These commands are commented out by default because
  the rebase in Step 2 takes time (dev may need to resolve conflicts, run tests,
  push --force-with-lease). Boss pastes them only after seeing the rebase commits land.

**Why not `--merge` but `--auto --squash`?** The `--auto` flag uses GitHub's auto-merge
feature (waits for required checks, then merges). On this repo there are no required
checks configured (verified `gh pr view --json statusCheckRollup`), so `--auto` resolves
immediately. `--squash` collapses multi-commit PRs into a single merge commit, keeping
`main` history clean. If the boss prefers merge-commit history, switch to `--merge`.

---

## The "Why This Time" Justification Block

A reader of a single bi-hourly report has no context for why this report
includes a one-liner and prior reports offered A/B/C. Always include a
2-3 sentence justification so the boss (or a future agent reading the
report) understands the escalation trigger:

```markdown
**为什么这次直接 one-liner 不再 A/B/C:**前 7 期报告(#150~#155)连续 7 次
提同样 A/B/C 选项无人拍板,本次按 RULES §"3+ 连续 = 强制 PM-direct-action"
出 one-liner。老板只剩 1 个决定:**"粘不粘"**。
```

This block is what transforms the one-liner from "another option" into "the
escalation conclusion". The boss reads it and understands: this is the
last-cycle form, not a repeat. A/B/C was offered 7 times; one-liner is the
8th-cycle-and-later form.

---

## The §6 Closing Line — Make Action Painted as "1 Minute of Effort"

The report's §6 (不需要老板操作 unless 🔴) should explicitly close with the
time/effort estimate of the one-liner, so the boss sees the cost as minimal:

```markdown
🔴 **需要老板操作**:本节 §5 one-liner。粘 #13 合并(30 秒)+ 派单 dev rebase(60 秒),
两个动作 1 分钟内可解 14 天死锁。**不动手 = 死锁继续,下次报告同态再升级。**
```

**Frame as "1 minute of effort"** — this is the single most important framing
in the report. The boss's hesitation to act is almost always about "do I
have time to think this through", not "is the action right". Naming a 1-minute
cost removes the friction.

---

## Anti-Patterns to Avoid (From Real #156 Build)

1. **Don't bury the one-liner in §6.** It goes in §5 (PM 洞察) or right
   under the §0 一页速读 table where the boss is already looking. §6 is the
   closing reminder, not the action.
2. **Don't include `git push --force` — use `--force-with-lease` always.**
   `--force-with-lease` detects if a teammate pushed to the branch while
   the boss was rebasing, and refuses to clobber it. The cost is zero; the
   benefit is non-zero.
3. **Don't run the rebase step automatically.** Dev is the one who knows
   the intent of their branch. The one-liner tells the boss what to paste;
   the boss decides whether to rebase themselves or assign dev to rebase.
4. **Don't list the one-liner with placeholders like `<PR1>` — boss can't
   mentally resolve 5 placeholders.** List the actual numbers (13, 15, 14).
5. **Don't use `--merge` when `--auto --squash` would suffice.** The `--auto`
   flag is safer (waits for required checks) and `--squash` keeps history clean.
6. **Don't emit a §3 摸鱼信号 verdict that contradicts the one-liner.** If
   dev is in a stale-claim loop (§5 #23) because of the gating PRs, the §3
   row should say "🔴 stale-claim loop (Nd, fix: unblock gating PRs)" — NOT
   "🔴 摸鱼". The boss needs to see the unblock action, not "dev is slacking".

---

## Worked-Example Trace (PM #156 Build, 2026-07-27 10:02 UTC)

- **Trigger**: report #155 (2h prior) was the 7th consecutive 🔴 boss-merge-PR
  deadlock. Same A/B/C menu offered 7 times. Boss had not picked. Pre-flight
  re-query confirmed #13 CLEAN, #14/#15 CONFLICTING (state unchanged from
  prior cycle's Δ).
- **Δ table**: emitted with all 3 PRs, "处置" column set to direct-merge vs
  rebase-first.
- **One-liner**: 3 sequential bash blocks (Step 1 = #13 merge, Step 2 =派单
  dev to rebase #14/#15, Step 3 = commented merge commands for after rebase).
- **Justification**: "前 7 期 A/B/C 无人拍板,本起按 3+ 连续规则升级" 2-sentence block.
- **§6 close**: "粘 #13 合并(30 秒)+ 派单 dev rebase(60 秒),两个动作 1 分钟内
  可解 14 天死锁。不动手 = 死锁继续,下次报告同态再升级。"

Result: the report was delivered to the Feishu home channel. The next report
(PM #157, 2026-07-27 12:02 UTC) will need to either: (a) cite "PR #13 merged,
rebase in progress" if the boss acted, or (b) re-emit the same one-liner with
no Δ if the boss did not act. If the boss does not act after 3 more cycles
(PM #159, ~6h later), the next escalation is a hard `gh pr merge` automatic
attempt by the PM bot itself (out of scope for §2.10 but a future iron-rule
candidate).

---

## Generalization: When to Skip A/B/C and Ship a One-Liner

| Boss-action-shaped deadlocks | Employee-action-shaped deadlocks |
|---|---|
| Boss-merge-PR (this file) | AND-trigger between employees (§5 #23) |
| Boss-approve-issue | Reviewer-stale-verdict (派单 reviewer) |
| Boss-decide-Px-priority | Dev-stale-claim (派单 dev to push) |

The PM-direct-action one-liner is ONLY appropriate for boss-action-shaped
deadlocks. For employee-action-shaped deadlocks, the right move is **派单
the other side to break the dependency** (see `pm-operations-playbook.md`),
not a one-liner. The discriminator: who has the unblock authority?

- If only the boss can do X (merge a PR, approve a budget, pick a priority),
  the one-liner is correct.
- If any employee can do X (push a commit, close an Issue, run a check),
  派单 that employee — don't escalate to the boss.

This is the §2.7 "4th state of the cron-liveness classification" — boss-merge-PR
deadlock is a distinct class from the AND-trigger deadlock, and the fix recipe
is different.
