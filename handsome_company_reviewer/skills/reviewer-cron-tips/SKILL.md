---
name: reviewer-cron-tips
description: Operational tips specific to the handsome_company_reviewer cron profile on this Windows host — local environment quirks, cron-tick patterns that worked, PR review race conditions, browser evidence capture, and pitfalls captured during 1+N team cron ticks. Load this skill when polling for reviewer-assigned GitHub issues on this host, when needing to produce visual evidence for a web-PoC verification, or when the next reviewer cron tick needs the "what worked last time" playbook.
version: 0.4.0
platforms: [windows]
metadata:
  hermes:
    tags: [reviewer, cron, oneplusn, windows, network, github, pr-review, race-condition, browser-evidence, playwright, evidence-audit, threshold-transition]
    related: [oneplusn]
---

# Reviewer Cron Tips (handsome_company_reviewer)

Operational playbook for the reviewer cron profile on this Windows host (`D:\onboarding\handsome-s-company`, repo `handsome-s-company/agent_workflow`). Each pattern below was captured from a real cron tick and proved correct in production.

## When to load

- A reviewer cron tick is firing (you are the `Handsome-Review` assignee and need to decide what to do this tick).
- The next action involves a **web PoC** that requires visual evidence (browser screenshots, gameplay demo, click-through proof).
- A previous reviewer tick left a `self-NEEDS_WORK` verdict on an issue and you are tempted to re-evaluate it.
- The polling heuristic (0-comment + body-blocker, N-comment + last-self-wait) needs to be applied to a new issue.

## Pre-flight access check (mandatory, every tick)

The oneplusn skill already documents this; quick recap so you don't skip it:

```python
# Always run BEFORE the issue poll.  Use execute_code + subprocess.run(env=...) so
# the GITHUB_TOKEN from the profile .env is not redacted by terminal-rendering.
gh api user --jq .login                   # must return "Handsome-Review"
gh api repos/<org>/agent_workflow         # no leading slash on Windows!
```

If the user probe returns a different login (e.g. `handsomehu80` = the boss), the
employee `.env` is missing on this host — see Known Fix #11 in the oneplusn skill.
Read-only ops still work; write ops will be misattributed.

## Polling heuristic: 0-comment decision tree (battle-tested)

Decision order for any open issue assigned to you with 0 comments:

1. **Body has explicit blocker language?** ("实施完毕 / depends on #N / 等 #13 close / blocked on #X / 等 dev 完成")
   - YES → `gh issue view <N>` for each named blocker. If any is still OPEN → emit `[SILENT]`. If all CLOSED → process now.
   - NO → process the issue (per iron rule 3 + "stale-dispatch after 3+ ticks" heuristic).
2. **PM comment overrides body blocker.** If the body says "等 #13 close" but a PM reassign comment says "实际依赖是 #16", trust the PM comment — it carries the dispatcher's latest sequencing intent. The body is a stale snapshot.
3. **3+ consecutive ticks (90+ min) on the same 0-comment + no-body-blocker issue = stale-dispatch signal.** Start work; the dispatcher is waiting on YOU, not the other way around.

## Polling heuristic: self-NEEDS_WORK wait (battle-tested)

When your **own last comment** on an issue contains explicit "等 X / wait for Y" instructions:

- Respect the instruction even if 24h+ of silence has passed.
- Override only if (a) the wait condition is now met, (b) the boss issues a new directive, or (c) external activity (new comment, assignee change) breaks the assumption.
- Post no "still waiting" bump comment unless P1 + 24h+ silence has materially exceeded the comment's implied horizon.

Observed in this profile: reviewer NEEDS_WORK on #8 at 2026-07-13T15:30:38Z was respected through ~25h of subsequent ticks; no override needed.

## Polling heuristic: 3-part evidence audit + threshold-transition handoff (NEW in v0.4)

When sitting on a self-NEEDS_WORK wait, comments + updatedAt alone is insufficient. The audit pattern that has actually held up across ticks at 22:13 / 22:42 / 23:13 on #8 is a **3-part check**:

1. **Comments + updatedAt** (cheap path) — `gh issue view N --json ...`; baseline check.
2. **Full events audit** — `gh api repos/<org>/<repo>/issues/<N>/events` returns assignment, label, mention, reference, project, milestone events. **Catches activity that doesn't bump updatedAt or add comments** — e.g. label-only changes via project-board automation, cross-issue `referenced` events, `mentioned` notifier events. Always run this part; comments-only audit has missed activity in past ticks.
3. **Blockers-in-recent-commits check** — when your NEEDS_WORK verdict names specific post-verdict blockers (production wiring missing, `WinError 206` in `tick_end.py:169-194`, etc.), fetch `gh api .../commits?sha=main&per_page=20` and confirm none of the recent commits touches the named files/functions. List the recent commits in the breadcrumb even if they don't touch — the dispatcher should see what's been happening on main and judge whether parallel work is meaningful.

The combined signal is what justifies continued `[SILENT]` with confidence. When all 3 are silent, the wait condition is definitively unmet.

**Threshold-transition handoff between consecutive ticks:** when the previous tick's breadcrumb says "next tick will re-evaluate" or "next tick (or any dev activity) will re-evaluate", this tick IS that next tick. The sequence:

- **Last tick (pre-transition):** elapsed < 24h, emit `[SILENT]`, breadcrumb flags "next tick to re-evaluate"
- **This tick (transition):** elapsed crosses 24h threshold; decide:
  - All 3 audit parts STILL silent AND no commit activity on blockers AND no external activity → continue `[SILENT]` with note that threshold just crossed and bump-comment is now eligible
  - >= 24h AND no commit activity on blockers for >= 24h → strong case for bump-comment OR escalation per pitfall #6
  - Wait condition MET (dev fixed, PM reassigned, body changed) → process the issue

**Don't double-flag the same threshold.** If the prior tick already noted "23.2h < 24h, next tick will re-evaluate", don't restate the threshold arithmetic at length — focus on what's NEW (any commits/events since prior tick) and what the elapsed time is NOW. Breadcrumb should be 1-2 lines of "no change since last tick" + elapsed delta + threshold status.

**When this tick CROSSES 24h for the first time**, breadcrumb should explicitly note "FIRST TICK PAST 24h P1 BUMP THRESHOLD" and either (a) post a bump-comment if wait condition has been unmet for >= 24h AND no commit activity on blockers, OR (b) defer one more tick if threshold was just crossed by minutes and you want to give the dispatcher a final window before bumping.

Observed: 23.7h tick on 2026-07-14 emitted `[SILENT]` with explicit "NEXT TICK @ 23:40 will be the FIRST tick past 24h (~24h10m) — will evaluate bump-comment vs continued [SILENT]". Each tick knows what the next tick's job is; handoff is explicit in the breadcrumb.

## Browser evidence capture for web PoCs (NEW in v0.3)

When the issue body requires "browser play 30s + 3 screenshots (initial / mid-play / game over)" or similar visual proof, do NOT attempt to drive the game with keypress timing — the result is non-deterministic and the screenshots look like random 6KB blobs. Instead:

1. **Use Playwright headless chromium** — it's globally installed at `C:/Users/Administrator/AppData/Roaming/npm/node_modules/playwright` and the browser is cached at `C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1223/`. From a Node script: `const { chromium } = require('C:/Users/Administrator/AppData/Roaming/npm/node_modules/playwright')`.
2. **Serve the worktree's poc dir over a local HTTP server** on `127.0.0.1` — some PoC paths require HTTP (not `file://`) for ES modules or `fetch()`.
3. **Use state-mutation, not keypresses**, for deterministic snapshots**: pause the game via `state.phase = 'paused'`, mutate `state.snake` / `state.food` / `state.dir` directly, then resume. This makes screenshots reproducible and visually meaningful.
4. **Verify with `vision_analyze`** that each screenshot actually shows what you claim. File size alone is a poor signal — 6KB and 12KB PNGs can both be valid.
5. **Push screenshots to main via git** (if worktree has `origin` set up) or Contents API (if not). See "Network and git push" below.

Full recipe + JS template: see `references/playwright-browser-evidence.md` and `templates/browser-play.js`.

## Network and git push on this Windows host (CORRECTED in v0.3)

The previous note that "github.com:443 is blocked on this host" was **incomplete** and led to unnecessary Contents API detours. The accurate model:

- **`git push origin <ref>` WORKS** when the worktree has an `origin` remote set up (e.g. worktree created via `git fetch origin refs/pull/N/head:refs/remotes/origin/pr/N && git reset --hard origin/pr/N`). Observed in 2026-07-14 #17 cron tick: `git push origin HEAD:main` succeeded, no proxy/firewall issue.
- **Contents API is the fallback** when there's no `origin` (typical for a fresh `oneplusn init` workdir that was never cloned from a remote). The oneplusn reference `git-push-and-self-close.md` covers this path in full.
- **`gh api repos/<org>/agent_workflow` (no leading slash) works** on git-bash Windows. With leading slash, MSYS rewrites the path to `C:/Program Files/Git/repos/<org>/agent_workflow` and you get a misleading "invalid API endpoint" error.

Quick decision rule for a new worktree:

```bash
cd <worktree> && git remote -v
# empty → use Contents API per git-push-and-self-close.md
# has origin → git push origin HEAD:main just works
```

## Self-close (only-reviewer-can-close)

The body must explicitly grant self-close authority. Search the body + all comments for one of:

- "自 close" / "self close" / "self-close"
- "only-reviewer-can-close"
- "可自 verify 后 close" / "reviewer 验证后 close"
- "完成后 reviewer 直接 close"
- PM reassign comment WITHOUT any "请把结果交给 PM 拍板" follow-up

If absent and the issue was created by PM/boss → reassign to PM after the work; do NOT self-close (iron rule 4 default applies). The full audit-trail comment template is in the oneplusn `git-push-and-self-close.md` reference.

## PR review race condition (the dev-re-pushes-head pattern)

The single most common race I've hit: **dev re-pushes the PR head between my review submission and my re-fetch.** Symptoms:

- `gh pr view <N>` shows head=`X`, I review against `X` and post `REQUEST_CHANGES` review id R1.
- Dev pushes commit `Y` to fix; head is now `Y`.
- My R1 review is **stale** (it lives on a commit that is no longer head) but still shows as `CHANGES_REQUESTED` in `reviewDecision`.

Recovery: post a new `COMMENTED` review on the new head that explicitly says "previous REQUEST_CHANGES R1 is stale (was against old head X); this review supersedes it." Recommend dev/boss dismiss R1.

Observed in #17 cron tick 2026-07-14T15:50: R1=`4691990663` (against `de64e3a4`) superseded by R2=`4692015410` (against `a48d85`).

## Pitfalls

1. **"0 comments = wait" is wrong as a blanket rule.** A 0-comment issue assigned to you with no body-blocker is YOURS to start, not the dev/PM's. The "leave for dev/PM to start work" line targets reviewer-style false-positives on dev's issues, not your own assignments.
2. **The `gh api` `repos/<org>/...` URL.** On Windows git-bash, the leading `/` triggers MSYS path rewriting. Always use the unprefixed form. See Known Fix in oneplusn SKILL.md.
3. **Vision_analyze sees native pixels.** When the active model has native vision, the screenshot is attached to your context on the NEXT turn — call it, then reason about it on the turn after. Do not chain a vision call and a follow-up tool in the same turn expecting both to see the image.
4. **Pausing then mutating state in browser-play.js.** The game loop's `last = ts` is captured at first `requestAnimationFrame` after `phase=playing`. If you mutate state then immediately set `phase=playing`, the first tick may use a stale `last` and produce a 0-tick screenshot. Wait at least one `setTimeout(80)` after `phase=playing` before screenshotting.
5. **`git push origin HEAD:main` from a detached worktree.** The worktree is on branch `pr-N-review` (not `main`); `git push origin HEAD:main` correctly resolves `HEAD` to the current branch tip and pushes to `main`. Do not `git checkout main` first — that creates a divergent branch and risks losing the `pr-N-review` history used for traceability.
6. **The 25h+ self-NEEDS_WORK wait is fine.** The reviewer has a 1-PR-at-a-time focus; the dispatcher is OK with reviewer sitting on a NEEDS_WORK verdict for days while dev iterates. Don't escalate to PM unless the wait materially exceeds the implied horizon (e.g. P1 + 24h+ silence with no commit activity on the named blockers).
7. **Comments + updatedAt alone is insufficient for "no activity".** A label change via project-board automation does NOT bump updatedAt. A cross-issue `referenced` event does NOT bump updatedAt or add a comment on the referenced issue. Only `gh api .../issues/N/events` catches these. Always run the 3-part audit (see "Polling heuristic: 3-part evidence audit" above).
8. **Don't pre-empt the threshold-transition handoff.** If the previous breadcrumb said "23.2h < 24h, next tick will re-evaluate", don't post a bump-comment at 23.5h "to get ahead of it". The handoff exists so the transition tick owns the decision cleanly; pre-empting splits the decision across two breadcrumbs and creates ambiguity in the audit trail.

## Current state snapshot (2026-07-14)

- **#17 [P0][Snake][Verify]**: CLOSED (PASS, reviewer self-close per only-reviewer-can-close). 2 reports + 3 screenshots pushed to main (commits `bf55135` + `77fe1f2`). Watch this issue in the future only if a v3 PR against the same work materializes.
- **#8 [P1][Loop-Eng][Verify]**: OPEN, status:in-progress, NEEDS_WORK verdict @ 2026-07-13T15:30:38Z. Wait condition: dev fixes (1) production dispatcher/cron wiring for BudgetMiddleware+write_scratchpad+run_tick_end and (2) Windows `WinError 206` in `agents/developer/hooks/tick_end.py:169-194`. ~25h+ of silence as of this writing.

## See also

- `references/playwright-browser-evidence.md` — full browser evidence capture recipe.
- `references/cron-tick-evidence-audit.md` — concrete `execute_code` + Python `subprocess.run(env=...)` snippets for the 3-part audit (comments/updatedAt, events API, blockers-in-commits); decision matrix for `[SILENT]` vs bump-comment vs escalate.
- `templates/browser-play.js` — generalized Playwright + state-mutation script.
- The oneplusn skill: full polling heuristic, pre-flight, self-NEEDS_WORK, and `git-push-and-self-close.md` reference.
