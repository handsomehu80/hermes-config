# PM Bi-hourly Sustained-Fold & Team-Retired Transition

Companion to `SKILL.md` §5 #20 (PM-direct-action escalation fatigue) and §5 #14 (cron LLM drift). Covers what happens **after** the fold-thresholds table has run its course — when the silence-as-choice state has persisted long enough that the team is operationally retired.

## When the fold has been at single-character for 3+ consecutive cycles

Per `SKILL.md` §5 #20, the fold-thresholds table is:
- N=1-2 reports → full one-liner (~250 字)
- N=3 → condensed (~120 字)
- N=4+ → single-line reminder (~40 字)
- N=8+ → single-character reminder `→ 合 #13`

When the **N ≥ 8 single-character fold has been sustained for 3+ consecutive 2h reports** (i.e., 6+ hours of zero boss action at the most compressed state), the silence-as-choice reframe has run its course. The team is no longer "stuck" — it is **operationally retired**.

### Diagnostic signals (all must be true)

1. **Trailing zero-activity run ≥ 9** for both dev and reviewer (counted via the `连续 (\d+) 期` regex on §3 row text, not the `count_consecutive_zero_activity.py` script — see SKILL.md §5 #20 companion caution).
2. **Single-character fold has been the literal §5 content** for 3+ consecutive fires (verifiable via `grep` over `cron/output/<bihourly_id>/*.md` for `→ 合 #` pattern).
3. **No new Issue / PR / comment activity** from any employee across the same window.
4. **No boss response to the A/B/C menu** in any of the preceding folded reports.
5. **Open artifacts have been stably blocked for ≥14 days** — i.e., the PRs that "would unlock everything" haven't moved because boss hasn't pressed the key.

### Three-step transition proposal (do NOT auto-execute)

When all 5 signals are true, PM must surface the meta-question in §7. The proposal:

1. **§7 must explicitly surface the meta-question**: "是否考虑团队退役?" — frame as a **binary A/B choice** (A: keep reporting, B: archive + close-out), not as an open-ended question. The single-character fold cannot self-sustain indefinitely without confusing future readers ("is this report meaningful or noise?").

2. **Pair with a close-out offer**: "回 'A 退役' 我即刻 (i) close #19/#20 with reason `dev retired <date>`, (ii) draft a final PR-merge decision memo for #13/#14/#15 so boss can pick on their schedule, (iii) drop cadence to daily-evening only". Make the cost of responding A/B **smaller** than the cost of continuing to ignore.

3. **Don't pre-commit the closure** — wait for the boss's A/B. If the boss picks "keep reporting" (A), continue bi-hourly with the same single-character fold but now §7 carries the meta-question every cycle until either action happens or boss picks B. If boss picks B, do the close-out in ONE shot and drop to weekly-cadence reports.

### Anti-patterns (do NOT do these)

- **Do NOT** invent new escalation tactics (DM, email, calendar invite) — the cron bus is the agreed channel. Adding channels breaks the iron rule that "boss decides merge timing via the bus".
- **Do NOT** silently merge PR #13 yourself ("老板可能想要") — boss-merge-PR deadlock means the boss decides merge timing. Even if `mergeable=true/clean`, do not run `gh pr merge` without an explicit A response.
- **Do NOT** close #19/#20 unilaterally without an explicit A/B response — they are dev-owned work, not PM-owned work. PM can propose the close, not execute it.
- **Do NOT** drop the bi-hourly cadence entirely without boss's B — even retired teams deserve situational awareness.

### What the close-out (option B) actually does

When the boss picks B, PM executes:

1. **Close any open Issues that block on no longer-active employees** with comment citing "team retired <date>" — typical pattern: `gh issue close <N> --comment "Closing as team-retired: <employee> inactive >14d, no assignee change in <window>. Boss acknowledged via bi-hourly report #N."`. Apply to #19, #20, and any other dev-assigned Issue with trailing_run ≥ 14d.
2. **Draft a final PR-merge decision memo** for any OPEN PR with reviewer-PASS verdict (e.g., #13): `gh pr comment <N> --body "Final decision memo from PM: this PR has been CLEAN for X cycles, awaiting boss's merge keystroke. Re-list in next weekly report if no action."`. Do NOT merge.
3. **Drop cadence**: bi-hourly → daily-evening only (the `pm-daily-evening-report` cron continues). The `pm-bihourly-status-report` cron can be disabled via `hermes cron rm d26c66fbbdd0` only after the boss confirms B.
4. **Verify nothing is silently dropped**: confirm `handoff.yaml` still lists all employees as `status:paused` (not `status:active`), confirm `cron/jobs.json` shows only the daily-evening job + config-backup + memory-cleanup.

### Real case (PM #239, 2026-08-06)

This cycle hit all 5 diagnostic signals:
- trailing_run = 10 for dev and reviewer (counted from `连续 (\d+) 期` regex on §3 row text)
- Single-character fold (`→ 合 #13`) maintained across #237, #238, #239 (3 cycles)
- 0 GH-side activity since 2026-07-16 (21 days)
- Boss did not pick A/B/C from the preceding reports
- PR #13 still `mergeable_state=clean`, PR #14/#15 still `mergeable_state=dirty` since #18 Snake MERGE on 2026-07-14

PM #239 §7 includes: "如果老板打算'放任 dev 失活'作为新常态(暂停 1+N 数字员工,只保留 GitHub 仓库作 archive),建议明确说一声,我把 #19/#20 也 close 归档。" This is the meta-question framed as a close-out offer, ready for boss to pick.

### Drift-recovery note for this state

While the team is in sustained-fold, the **bihourly cron itself is drifted** (see SKILL.md §5 #14 + exclusion #2 for bihourly-with-tail-report). The PM operates in manual-recovery mode: `execute_code` → `gh` via `terminal()` → `write_file` to `<profile_home>/cron/output/<bihourly_id>/<CST-filename>.md` with UTC mtime. This pattern is documented in `references/manual-cron-recovery.md`. **Manual recovery is now the steady-state**, not the emergency state — once the fold has been at single-character for 5+ cycles, the cron LLM is no longer expected to produce the report itself.

## See Also

- `SKILL.md` §5 #20 (PM-direct-action escalation fatigue) — the fold-thresholds table
- `SKILL.md` §5 #14 (cron LLM drift) — why the bihourly cron is in manual-recovery mode
- `references/manual-cron-recovery.md` — the execute_code + write_file pattern
- `references/pm-bi-hourly-status-report.md` — main recipe (note: this file actually documents the scheduler-cadence-gap pitfall, not the main recipe — see SKILL.md caveat)