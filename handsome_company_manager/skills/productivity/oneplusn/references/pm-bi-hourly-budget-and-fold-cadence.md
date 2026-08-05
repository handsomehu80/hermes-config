# PM Bi-Hourly: 1500 字 Budget Enforcement + Fold Cadence Real-Case

Two lessons from the PM bi-hourly cron run cycle that the loaded SKILL.md (100KB+) cannot inline further without restructuring.

## 1. Enforce the 1500 字 budget BEFORE `write_file`, not after

The cron prompt says "总长控制在 1500 字以内" but the SKILL.md body never enforced it. A draft composed from the standard 6 sections + §5 (with full PM-direct-action one-liner + Δ table) routinely runs **2200-2800 chars** when nothing is folded. If you only notice the overshoot after `write_file`, you'll rewrite and produce **two consecutive files in `<job_id>/` within ~30 seconds**, both with the same report number but different content. Future runs reading the dir see the discarded first file as "drift" / "extra artifact", and your own N=219 file list shows two near-identical filenames.

**Fix**: enforce the budget BEFORE the first write. Count `len(report)` in Python (Chinese chars are already single code points; `len()` is the right metric). If >1500, apply the fold in this exact order:

1. Collapse §5 to single-line reminder (≤40 字: `gh pr merge 13 14 15 --merge` + brief rationale)
2. Compress §1 to a single table row per work item, drop nested columns
3. §3 to bare-dash `—` for empty cells instead of `无 / 0 commit / 0 评论 / 0 PR`
4. Drop `注:` annotations
5. Shorten §2 risk details to one-line each

Recount and only then `write_file`.

**Real case (PM #219, 2026-08-04 16:02 UTC)**: first write 2552 chars → second write 1456 chars, 25-second gap. Pattern is reproducible every cycle when the template is applied without budget verification. Two near-identical filenames: `2026-08-05_00-02-20.md` (3514B, dropped) and `2026-08-05_00-02-45.md` (1956B, kept).

## 2. The fold IS the budget enforcement — apply progressively as silence extends

**Real-case sequence** (boss-merge-PR deadlock, observed 2026-07-13 → 2026-08-04):

| N | §5 form | Approx §5 字数 | Trigger |
|---|---|---|---|
| ~197 | Full A/B/C menu | ~250 | Deadlock first detected, escalate with options |
| ~203 | Condensed (one-liner + 1-line Δ verdict) | ~120 | After 1 consecutive ignored A/B/C |
| ~213 | Announced upcoming fold in §7 | ~120 | "下次若仍未动,我将折叠 §5 为单行" |
| ~215-217 | Same announcement repeated | ~120 | Boss continued non-response |
| 218 | First fold executed | ~120 | §5 down to one-liner + brief verdict |
| **219** | Single-line reminder executed | **<40 字** | Full fold: `gh pr merge 14 15 13 --merge` + "22+ 天静默 = 知情选择" |

**Pattern to internalize**: do NOT wait for explicit "now I should fold" — the fold is the budget enforcement mechanism, not a separate step. Apply the fold whenever the silence run extends AND the current §5 form is already at the previous fold level. Threshold rules from pitfall #20 of SKILL.md:

- N=1-2 reports after deadlock detected → full one-liner (~250 字) with Δ table
- N=3 reports → condensed (~120 字)
- N=4+ reports → single-line reminder (≤40 字)
- N=8+ reports → single-character reminder (only safe if prior 4 reports have been folded without boss engagement)

**Re-allocation rule**: when §5 shrinks, the freed character budget moves to §2 (new risk rows for any silent drift) and §7 (analysis of why the silence might be intentional — "沉默进入常态化 — 你不再需要 A/B/C,只需要'按回车'或'明确叫停'").

**The "silence-as-choice" reframing**: after 5+ consecutive reports with no GH activity AND no boss response, the situation is no longer "stuck" — it is "boss has been informed and is choosing not to act". PM should explicitly call this out in §7 to anchor the boss's choice, and §5 should drop the words "urgent" / "紧急" / "请立刻".

**Companion caution**: `scripts/count_consecutive_zero_activity.py --window N` reports `trailing_run=0 [green] no trailing zeros` when §3 text in the latest report already shows "连续 16 期 0" — the script's classification logic does not match what the report text says; PM should treat the script's verdict as informational only and count zero-activity streaks manually from the §3 rows, OR patch the script to parse the trailing-run number from the §3 row text itself (e.g., regex `连续 (\d+) 期`).

**Do NOT** ever stop emitting §5 entirely or skip the report — the boss may still want to monitor and any future action needs the §1/§3 context for situational awareness.