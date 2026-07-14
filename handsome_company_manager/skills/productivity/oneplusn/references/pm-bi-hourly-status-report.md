# PM Bi-Hourly Status Report — Recurring Operational Cadence

This is the **playbook for the PM profile (`handsome_company_manager`) when the boss schedules a recurring every-2-hours status report**. Distinct from both the 30-min `task-polling` cron (which executes work or returns `[SILENT]`) and from `PM Mode` (on-demand strategic analysis). The 2h report is a **scheduled, read-only observation report** delivered to the boss's home channel.

> **The cron prompt (paraphrased from real 2026-07-14 deployment):**
> "你是 PM @Handsome-Manager,每 2 小时主动给老板交付一次项目状态报告。这是第 N 期。从当前时间计数。SILENT 协议:无新内容时回复 `[SILENT]`(且仅此),绝不与内容混用。"

---

## 1. What This Is and What It Isn't

| Cadence | Trigger | Output | Toolset | Failure mode if confused |
|---|---|---|---|---|
| **30-min task-polling cron** (per employee) | `hermes cron` 30-min tick | `[SILENT]` or per-issue work action | gh API as persona | Treated as 2h report → boss gets 24× daily spam |
| **2h status report** (PM only) | `hermes cron` 2h tick | Bilingual status digest to home channel | read-only `gh issue list`/`pr list`/`git log` | Treated as task-polling → PM stops doing actual orchestration |
| **PM Mode** (on-demand) | Boss message in chat | Multi-perspective strategic analysis with A/B/C menu | `delegate_task` (2-3 subagents) | Treated as 2h report → PM burns tokens on deep research twice daily |

**Decision rule:** if the boss asked "what's happening across the team" / "give me the dashboard" / scheduled a cron with "2h report" in the prompt, this is the 2h report. If they asked "should we add a new employee" or "analyze our architectural trend", use `PM Mode`. If a single Issue needs action, that's task-polling.

---

## 2. Data Collection Commands (the real ones that work on Windows git-bash)

The template's commands hit three pitfalls on this host. The fix for each is below.

### 2.1 `gh issue list` — works, use this shape

```bash
cd <team-work-dir>
gh issue list --repo <org>/agent_workflow --state all \
  --json number,title,state,assignees,labels,updatedAt \
  --jq '.[] | "#\(.number) [\(.state)] \(.title[0:50]) | asg=\([.assignees[].login] | join(",")) | lbl=\([.labels[].name] | join(",")) | upd=\(.updatedAt)"'
```

`--jq` with a projection template keeps the output bounded. The `head -200` mentioned in the template is a guardrail only — most repos have <50 issues.

### 2.2 `gh pr list` — works, same shape

```bash
gh pr list --repo <org>/agent_workflow --state all \
  --json number,title,state,mergedAt,additions,deletions,author,updatedAt \
  --jq '.[] | "#\(.number) [\(.state)] \(.title[0:60]) | author=\(.author.login) | +\(.additions)/-\(.deletions) | upd=\(.updatedAt) | merged=\(.mergedAt // "—")"'
```

### 2.3 `git log --since="2 hours ago"` — returns empty if the work-dir is the wrong repo

**Pitfall:** the cron job's `workdir` may point at the team work-dir (e.g. `D:\onboarding\handsome-s-company`) while you actually want commits from `<org>/agent_workflow` (the actual workflow repo). On the 2026-07-14 deployment, the team work-dir IS the cloned `agent_workflow` repo, so `git log` works there. On other deployments, `cd` into the right repo first.

If `git log --since="2 hours ago"` returns empty:
1. **Check the cwd is a git repo with a recent log** — `git log -1 --pretty=fuller` to see the last commit.
2. **If the workdir is wrong** (`os.path.isdir(workdir)` returns False), the cron silently fires with cwd = profile home. Fix per `SKILL.md` §"Pitfall: Cron workdir drift is silent until it isn't".

### 2.4 `gh api repos/<org>/<repo>/issues/comments` — TWO gotchas

**Gotcha A: MSYS path rewrite.** `gh api /repos/...` rewrites the leading `/` to a Windows filesystem path on git-bash. Always pass a path WITHOUT a leading slash, or use `MSYS_NO_PATHCONV=1`:

```bash
# WRONG: error "invalid API endpoint: 'C:/Program Files/Git/repos/...'"
gh api /repos/<org>/<repo>/issues/comments

# RIGHT
gh api repos/<org>/<repo>/issues/comments
# or
MSYS_NO_PATHCONV=1 gh api /repos/<org>/<repo>/issues/comments
```

**Gotcha B: default returns only 30 comments in ascending order, then breaks the time-window filter.** This is the lesson from 2026-07-14: filtering the default response for `created_at >= "<2h ago>"` returned EMPTY even though there were 2 comments in the 2h window — the default `gh api .../comments` returns the OLDEST 30 comments, not the NEWEST. To get recent comments, you must explicitly request descending sort + a high page size:

```bash
# WRONG: returns oldest 30 ascending — recent 2h activity may be excluded
gh api repos/<org>/<repo>/issues/comments \
  --jq '.[] | select(.created_at >= "2026-07-14T08:01:39Z")'

# RIGHT: explicitly request the most recent 100, descending
gh api "repos/<org>/<repo>/issues/comments?per_page=100&sort=created&direction=desc" \
  --jq '.[] | select(.created_at >= "2026-07-14T08:01:39Z") | "[\(.created_at)] \(.user.login) on issue-url=\(.issue_url) | \(.body[0:80])"'
```

Compute the 2h-ago boundary explicitly so it's reproducible across runs:

```bash
date -u -d "2 hours ago" "+%Y-%m-%dT%H:%M:%SZ"   # on this host
# 2026-07-14T08:01:39Z
```

### 2.5 Bonus: cron liveness check

Verify the PM's own cron is actually firing (vs. silently dead due to the `workdir` pitfall above):

```bash
ls -la "/c/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/" | tail -5
# expect: new .md files dated every ~30 min (the task-polling cron, not 2h)
# if last file is >2h old, the cron ticker may have died — restart the Gateway
```

---

## 3. The Report Template (the boss's preferred format)

Stick to the exact structure the boss provided. Don't reformat. Boss has been explicit they "love short reports, not long ones" (≈1500 字 ceiling per issue).

```markdown
# 📊 PM 双小时状态报告 #N(YYYY-MM-DD HH:MM UTC+8 或 UTC)

## 0. 一页速读
| 类别 | 健康度 | 关键事实 |
| 整体项目 | 🟢/🟡/🔴 | 一句话 |
| Loop Engineering 主线 | 🟢/🟡/🔴 | 各项状态 |
| Snake 实战(或当前主线) | 🟢/🟡/🔴 | 设计/实施/验证 |

## 1. 进度矩阵(Issue / PR)
| # | 标题 | 类型 | 状态 | assignee | 关键 |

## 2. 红黄绿灯风险
| 风险项 | 等级 | 详情 |

## 3. 每人贡献(本期 2h)
| 角色 | 账号 | 本期完成 | 本期动作 | 摸鱼信号 |
| 🛠 dev | <login> | ... | commits/评论/PR | 0=摸鱼, 3+=良好 |
| 🔍 reviewer | <login> | ... | 同上 | 同上 |
| 🐑 PM | 我 | ... | 派单/拍板/报告 | — |

## 4. 下次触发(2h 后)
| 时点 | 期望事件 |

## 5. PM 洞察(1-3 句,不要超)
[concrete observation, not boilerplate]

## 6. 不需要老板操作(除非标 🔴)
[explicit "no action needed" close]

— PM @<handle> · 第 N 期完成
```

**Strict rules from the boss:**
1. **不要凭印象** — all data from real command output, no fabrication.
2. **不要越俎** — don't write code, merge PRs, close Issues, edit PR comments.
3. **不要编造** — if a query fails, say "未能拉取" explicitly.
4. **直接 final response = 报告本身** — system auto-delivers; do NOT use `send_message`.
5. **总长 ≤ 1500 字** — boss loves small reports, not novels.
6. **摸鱼信号** — dev/reviewer with 0 commit + 0 评论 + 0 PR action in 2h = "无活动,待观察"; two consecutive 0-activity reports = "🔴 摸鱼嫌疑".
7. **风险等级** — 🔴 阻塞交付 / 🟡 进度慢但有推进 / 🟢 健康.

---

## 4. Computing "Activity in 2h" (the 摸鱼 calculation)

Per-employee activity in the 2h window = sum of:

- `git log --since="2h ago" --author="<name or email>"` — count commits
- `gh api .../comments?per_page=100&sort=created&direction=desc` filtered to last 2h — count comments where `user.login == <employee_github_username>`
- `gh pr list --state all --json author,updatedAt` filtered to last 2h — count PRs where `author.login == <employee>` OR the PR was merged in the window with the employee's author

**Per-role thresholds** (from the boss's hard rules):
- `0` → "无活动,待观察"
- `1-2` → "正常"
- `3+` → "良好/活跃"

**Cross-employee handoff (the 2h-ratchet):** if dev was active 2h ago and the work landed in reviewer's lap, and reviewer has been active since, that's NOT a 摸鱼 signal for either — it's the handoff completing. The report should describe the handoff state, not flag either side as idle.

---

## 5. Pitfalls (LESSONS LEARNED — 2026-07-14 first run)

1. **Don't trust "everything is closed" from a quick `gh issue list` head check.** The first run on 2026-07-14 saw "all issues closed" in 8 of 8 visible rows, but #8 (P1 verification + 铁规 #7 policy) was still OPEN, and 3 PRs (#13/#14/#15) were OPEN. Always count OPEN issues explicitly and the 4-quarter summary at the top.

2. **Don't label a report "all green" just because the headline milestone (e.g. Snake PoC) passed.** Snake was 🟢 but the Loop Engineering 铁规 #7 policy work is still 🟡. The 一页速读 table must show the WORST grade for the system, not the best.

3. **The 2h boundary is strict.** Comments exactly at the boundary (`==` instead of `>=`) get included with `>=`, excluded with `>`. Always use `>=` so nothing slips through.

4. **Don't pre-write the report before verifying data exists.** The 2h-window filter on the default `gh api` returned empty (Gotcha B above), which would have produced a "no activity" report. Always verify the filter actually returned rows before drafting.

5. **`[SILENT]` is for task-polling, not for the 2h report.** If the 2h report has no new content, the right move is a brief "all quiet, system stable" summary — NOT `[SILENT]`. The boss explicitly wants the 2h report delivered as a checkpoint, not a delivery-suppression signal. Suppression is reserved for the 30-min per-employee task-polling cron.

6. **Numbering the reports: count from the cron install, not from the conversation start.** If the cron was installed on day 1 and has been running 7 days at 12×/day, this is report #84, not #1. If the cron was installed today, start at #1 and count up. Read `<profile_home>/cron/jobs.json` and look for the first output `.md` file to anchor the count if unsure.

7. **The MSYS `gh api` gotcha hits this report too**, not just task-polling. The fix (drop leading slash, or `MSYS_NO_PATHCONV=1`) is the same.

8. **`date` is the right tool for the 2h boundary**, not mental math. Boss timestamps every event explicitly; the boundary in the report must match a real `date -u -d "2 hours ago"` output, not a guess.

9. **Report length is a hard ceiling, not a guideline.** Boss's hard rule: 1500 字 max. The 一页速读 + 进度矩阵 + 风险表 + 贡献表 + 下次触发 + 洞察 6 sections, when tight, fit in ~1000-1200 字. Add a 风险 section only if there's actual risk; pad with "no risks" rows only if the template demands them.

10. **The PM is allowed to do nothing in 2h, and that IS a signal.** If dev is firing and reviewer is firing, the PM may legitimately have zero direct action — the 摸鱼 signal only applies to dev/reviewer, not PM. The PM's column in §3 should list "派单 / 拍板 / 报告" actions; "none" is a valid value and means "team is self-driving, PM is observing".

---

## 6. The 5 Numbers That Always Go in §0 (一页速读)

Every 2h report must include the 5 numbers below in the 健康度 table. The boss checks them first:

| Number | Where it comes from |
|---|---|
| Total Issues (open / closed split) | `gh issue list --state all --json state --jq '[.[] \| .state] \| group_by(.) \| map({(.[0]): length}) \| add'` |
| Total PRs (merged / open split) | `gh pr list --state all --json state --jq '[.[] \| .state] \| group_by(.) \| map({(.[0]): length}) \| add'` |
| Last commit age | `git log -1 --pretty=format:"%ai"` and compute Δt from now |
| Last Issue/PR activity (2h window) | comment count from §2.4 |
| Number of 🔴 items in §2 | count from the 风险 table |

---

## 7. See Also

- `SKILL.md` §"PM Operations: Managing the 1+N Team Day-to-Day" — the move-by-move playbook (派单/监控/审计/拍板/升级)
- `SKILL.md` §"PM Mode: Team-Led Strategic Analysis" — for on-demand deep analysis with subagents (NOT this cadence)
- `references/cron-polling-behavior.md` — the 30-min task-polling cron, with the MSYS `gh api` gotcha and the `[SILENT]` protocol
- `references/windows-msys-tooling.md` §Pitfall 4 — MSYS path rewrite (the `MSYS_NO_PATHCONV=1` fix)
- `references/pm-operations-playbook.md` — full worked examples of dispatch / audit / 拍板
- `SKILL.md` §"Pitfall: Cron workdir drift is silent until it isn't" — when `git log` returns empty in the wrong workdir
