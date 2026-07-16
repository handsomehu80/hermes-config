# PM Daily Evening Report — Recurring Day-End Cadence

This is the **playbook for the PM profile (`handsome_company_manager`) when the boss schedules a recurring once-per-day end-of-day status report**. Distinct from both the 30-min `task-polling` cron and the 2h status report — this is a **24h-window retrospective** delivered to the boss's home channel, typically at 23:00 CST (15:00 UTC).

> **The cron prompt (paraphrased from the 2026-07-15 deployment):**
> "你是 PM @Handsome-Manager,每晚 23:00 CST(15:00 UTC)给老板交付一份**当日项目日报**。这是当日总结 + 当前快照 + 风险趋势 + 明日期望 + 老板决策点。比双小时报告更全面。"

---

## 1. What This Is and What It Isn't

| Cadence | Trigger | Output | Window | Budget |
|---|---|---|---|---|
| **30-min task-polling cron** (per employee) | `hermes cron` 30-min tick | `[SILENT]` or per-issue work action | 实时 | n/a |
| **2h status report** (PM only) | `hermes cron` 2h tick | Bilingual digest to home channel | 2h rolling | ≤1500 字 |
| **Daily evening report** (PM only) | `hermes cron` 24h tick (15:00 UTC = 23:00 CST) | End-of-day summary + Δ vs yesterday | **last 24h** | **≤2500 字** |
| **PM Mode** (on-demand) | Boss message in chat | Multi-perspective strategic analysis | n/a | varies |

**Decision rule:** if the cron prompt says "当日" / "日报" / "每晚" / 24h window, this is the daily report. If it says "每 2 小时" / "本期 N" / 2h window, use the bi-hourly playbook (`references/pm-bi-hourly-status-report.md`). If single Issue, that's task-polling.

---

## 2. Data Collection — What Differs From the 2h Report

The 2h report's commands (sections 2.1–2.5 of `references/pm-bi-hourly-status-report.md`) mostly work. **Three daily-report-specific gotchas**:

### 2.1 `gh api .../issues` returns PRs too — filter by `pull_request` field

**Lesson learned 2026-07-15:** `gh api repos/<org>/<repo>/issues` returns BOTH Issues AND PRs in one payload. PRs are issues with a `pull_request: { url, ... }` key. If you count `[.[] | .number]` naively, you'll inflate open count by 3-5 (PR #13/#14/#15 always count as "open issues" in this shape).

**Fix:** always filter for real issues:

```bash
gh api repos/<org>/<repo>/issues?per_page=100 --jq '
  [.[] | select(.pull_request == null) | {number, state, title, assignees, labels, updated_at, created_at, closed_at}]'
```

The `pull_request == null` predicate is the discriminator. `gh issue list` (the CLI wrapper) already filters this for you, but raw `gh api` does not.

### 2.2 Cross-day baseline — read yesterday's report from `cron/output/<job_id>/`

**Lesson learned 2026-07-15:** the daily report's "Δ vs yesterday" section is most accurate when you read yesterday's actual report file, not your memory of it. The 2h reports live in `<profile_home>/cron/output/<bihourly_job_id>/*.md`; the daily report (when installed) lives in the same dir tree under a different `<daily_job_id>`.

**Pattern:**

```bash
# 1. find the daily report's job_id
python -c "import json; d=json.load(open(r'<profile_home>/cron/jobs.json',encoding='utf-8')); \
  [print(j['id'],j['name']) for j in d['jobs'] if 'daily' in j['name'].lower()]"

# 2. list output files; pick the second-to-last (yesterday's report)
ls <profile_home>/cron/output/<daily_job_id>/ | sort

# 3. read yesterday's body — skip past the giant skill prompt by finding the
#    first "# " header AFTER the "## Response" marker
python -c "
import re
content = open('<file>',encoding='utf-8').read()
# Most outputs end with the skill prompt followed by '## Response' then the actual report
idx = content.rfind('# ')
body = content[idx:]
print(body[:5000])  # first 5KB is usually the 1-page summary + progress matrix
"
```

**On first run:** if no yesterday report exists (cron was just installed), label §5 explicitly: **"首次日报,无对比基线"** — do NOT fabricate numbers from imagination.

### 2.3 `last_status=None` vs `last_status=error` — different signals

**Lesson learned 2026-07-15:** when auditing crons per profile, distinguish three states:

| `last_status` | Meaning | Action |
|---|---|---|
| `"ok"` | Cron fired and LLM succeeded | Healthy |
| `"error"` | Cron fired but LLM/script failed | Inspect last `.md` output for traceback |
| `null` (None) | Cron has never fired (just registered, or ticker hasn't ticked yet) | Wait one tick; if still None after 24h, the cron registration is broken |

**Zombie cron pattern:** if a profile has TWO crons with the same `name` differing only in case (e.g. `oneplusn-dev-task-polling` + `oneplusn-DEV-task-polling`), the lowercase variant usually has `ok` (working) and the uppercase has `error` (path mismatch / script not found). Surface this in the daily report's risk table — it bloats the cron list and confuses the dashboard.

**Detection one-liner:**

```bash
python -c "import json; d=json.load(open(r'<profile_home>/cron/jobs.json',encoding='utf-8')); \
  [print(j['name'],j['schedule']['display'],j.get('last_status','null')) for j in d['jobs']]"
```

---

## 3. The Report Template (boss-provided, do not reformat)

```markdown
# 📅 PM 项目日报 — YYYY-MM-DD(CST)

## 0. 今日一句话总结
[≤ 100 字]

## 1. 今日做了什么(24h)
| 时段 | 事件 | 贡献方 |
| 12:38 | ... | dev / reviewer / PM / boss |

## 2. 当前快照(Issue + PR 全表)
| # | 标题 | 类型 | 状态 | assignee | 关键 |

## 3. 红黄绿灯风险
| 风险项 | 等级 | 详情 | 趋势(相比昨日) |

## 4. 每人当日贡献
| 角色 | 账号 | commits | 评论 | PR 动作 | Issue 动作 | 综合评估 |
| 🛠 dev | <login> | ... | ... | ... | ... | 良好 / 摸鱼嫌疑 / 离线 |
| 🔍 reviewer | <login> | ... | ... | ... | ... | 同上 |
| 🐑 PM | 我 | ... | ... | ... | ... | — |
| 👑 boss | <login> | ... | ... | ... | ... | — |

## 5. 跨日趋势(对比昨日报告)
| 维度 | 昨日 | 今日 | Δ |
| Open Issue 数 | ... | ... | ... |
| Closed Issue 数 | ... | ... | ... |

## 6. 明日期望触发(老板需要知道)
| 时点 | 期望事件 |
| 明日 09:00 | dev cron 触发 → 应回评论 #16 ... |

## 7. 老板决策点(需要你拍板)
- [ ] 决策 1:...
- [ ] 决策 2:...

## 8. 不需要老板操作(除非标 🔴)
```

**Strict rules (from boss's hard constraints):**

1. **不要凭印象** — all data from real command output.
2. **不要越俎** — observe + report only.
3. **不要编造** — if query fails, say "未能拉取".
4. **摸鱼信号 (per-employee, 24h window):**
   - 0 commits + 0 comments + 0 PR actions + 0 Issue actions = **摸鱼嫌疑**
   - 0 业务活动 + cron 应触发但无产出 = **同**
   - 连续 3 天 = 🔴 升级
5. **报告总长 ≤ 2500 字** — daily can be longer than 2h, but still hard ceiling.
6. **投递**:cron 自动投递到 feishu home channel; final response IS the report.
7. **首次跑**:无昨日对比,标"首次日报,无对比基线"。

---

## 4. Mandatory Data Points (must appear in every daily report)

The boss explicitly listed these as required:

- **当前时间(CST)** — date header + the section times within the body
- **当日 commits 数 / Issue 数 / PR 数 / 评论数** — top of §1
- **每人 commit / 评论 / PR / Issue 计数** — §4 row per person
- **风险等级分布**(红 / 黄 / 绿 各几个)— bottom of §3
- **明日第一个 cron 触发时点** — §6 first row (明早 dev cron = 09:00 CST = 01:00 UTC)

---

## 5. Pitfalls (LESSONS LEARNED — 2026-07-15 first run)

1. **`gh api .../issues` returns PRs too.** Without `select(.pull_request == null)` filter, your §2 issue table will show PR #13/#14/#15 as "open issues" and the OPEN count will be wrong by 3-5. Always filter.

2. **Yesterday's baseline may not exist.** If the daily cron was installed today, there's no "yesterday" file. Don't invent the comparison — label §5 as "首次日报,无对比基线" and skip the Δ column for the rows where you have no source.

3. **`last_status=None` is NOT the same as `last_status=error`.** A `None` cron may just be "registered but hasn't ticked yet" (check output dir for any `.md` file; if 0 files exist, it never fired). An `error` cron fired and failed (check last `.md` for traceback). Don't conflate them in the risk table.

4. **Zombie crons are real.** On the 2026-07-15 deployment, dev profile had 6 cron jobs (3 lowercase healthy + 3 uppercase `error`) and reviewer had the same pattern. The uppercase variants are leftovers from earlier deploy attempts with different script paths. Surface this in §3 as 🟡 risk: "6 zombie crons with last_status=error, need cleanup via `hermes cron delete`".

5. **The cron report payload is huge.** Each `cron/output/<job_id>/*.md` file includes the entire skill prompt (47-81KB) followed by `## Response` then the actual report. Don't read the whole file — find the `## Response` marker or `rfind('# ')` to skip to the body. Reading 80KB of prompt per yesterday-report costs you context budget fast.

6. **The PM's daily report is a separate cron job from the bi-hourly one.** On the 2026-07-15 deployment, both `pm-bihourly-status-report` (`0 */2 * * *`) and `pm-daily-evening-report` (`0 15 * * *`) were registered. The bi-hourly runs 12×/day; the daily runs once. If the daily cron has `last_status=None`, it likely hasn't fired yet — first fire is the next 15:00 UTC. Don't be alarmed by `None`.

7. **Cross-day comparison is "Δ vs yesterday's SNAPSHOT", not "Δ vs what the boss expects".** If yesterday's report said "PR #14 OPEN, dev to merge next cron", and today's report still says "PR #14 OPEN", the Δ column shows +0 and the risk is 🟡 "stuck from yesterday". Don't escalate to 🔴 unless the issue aged past a known threshold (e.g. PR open >7 days).

8. **Don't repeat yesterday's full body.** The boss reads both reports; a verbatim copy is waste. Use the cross-day Δ table to highlight what changed, and link to yesterday's report (or its commit) for the static context.

9. **Issue-event filter for created/closed in 24h** needs `closed_at` (not `updated_at`). A 5-day-old Issue that got a comment yesterday has `updated_at = yesterday` but `closed_at = null`. For "closed today" use `closed_at >= 24h ago`.

10. **CST timezone shift** — the `git log --since="24 hours ago"` works on the host clock (which is CST on this Windows). The `gh api` timestamps are UTC. Always convert in the report headers (`13:06 (08:06 UTC)`) so the boss doesn't have to do timezone math.

11. **`今日做了什么(24h)` window is UTC-anchored, not CST calendar day** (learned 2026-07-15 first run). The PM daily cron fires at **15:00 UTC = 23:00 CST**, so the "24h window" is `[15:00 UTC D-1, 15:00 UTC D]`. An event at 16:19 CST on D-1 (= 08:19 UTC) is **OUTSIDE** the 24h window — it belongs in the previous day's report, not today's. On 2026-07-15 I mis-listed the Snake PR #18 merge (08:19 UTC) in §1 "今日做了什么" when it was actually from the prior 24h window. **Fix:** in §1's caption write the window in BOTH zones: `今日做了什么(24h, 2026-07-14 15:00 UTC → 2026-07-15 15:00 UTC = 7-14 23:00 CST → 7-15 23:00 CST)`. Before including any event, verify its **UTC** timestamp falls inside `[15:00 UTC D-1, 15:00 UTC D]`. Events from "yesterday CST afternoon" go in §5 (cross-day trend), not §1.

12. **`git log --since="24 hours ago"` and `gh api .../commits?since=X` give DIFFERENT windows** (learned 2026-07-15). Git uses host clock (CST), `gh api` uses UTC. From 23:00 CST 7-15, `git --since="24h ago"` = since 23:00 CST 7-14, but `gh api ...?since=2026-07-14T15:00:00Z` = since 15:00 UTC 7-14 (= 23:00 CST 7-14) — they happen to match here, but **don't rely on it**. If the cron fires at a time when CST and UTC aren't 8h apart (e.g. a future DST change, or a different deployment timezone), the windows diverge by hours and §1 will contain inconsistent events. **Fix:** pick ONE reference clock (recommend UTC for cross-tool consistency) and convert everything else to it. Use `git log --since="2026-07-14T15:00:00Z"` instead of `--since="24 hours ago"` so git and gh use the same boundary.

13. **Cross-day Δ must compare SNAPSHOTS at the SAME clock, not rolling-window diffs** (learned 2026-07-15). §5 "Δ vs yesterday" compares `state at 15:00 UTC today` vs `state at 15:00 UTC yesterday`. Don't derive Δ by diffing event-streams ("commits in last 24h" minus "commits in 24-48h ago") — boundary events double-count or get missed. **Fix:** every Δ-row in §5 should be `gh issue list --state open --json number | jq length` at the moment of writing, snapshotted in both reports. The Δ column shows `(today - yesterday)`, with the sign indicating direction.

14. **First-day report label is mandatory** (refinement of #2). When §5 has no real yesterday baseline, write the section header as `## 5. 跨日趋势(对比昨日报告 — 首次日报,无对比基线)`. Don't quietly skip the section; don't fabricate numbers. If you have *some* data from yesterday's cron-output dir (even partial), label it `部分基线` and only show Δ rows where you have both endpoints.

15. **`gh issue list --json comments` returns an ARRAY of comment OBJECTS, not a count** (learned 2026-07-16). When you run `gh issue list ... --json number,comments`, the `comments` field comes back as `[{id, author, body, ...}, ...]` — an array of full comment records — not an integer count. Using it in an f-string with `{cmts:>2}` blows up with `TypeError: unsupported format string passed to list.__format__`. **Fix options:**
    - Drop `comments` from the `--json` list and count separately via `gh api 'repos/<org>/<repo>/issues/comments?since=...' | jq length`
    - If you keep it, convert with `cmts = len(i.get('comments') or [])` before formatting
    - Don't assume any field name in `--json` is a count — `--json reactions`, `--json labels` also return arrays of objects, not counts

16. **`gh issue list --json` uses camelCase; `gh api .../issues/comments` uses snake_case** (learned 2026-07-16). Same data point has different key names depending on which gh surface you query:
    - `gh issue list --json` → `createdAt`, `updatedAt`
    - `gh api 'repos/<org>/<repo>/issues/comments'` → `created_at`, `updated_at`, `user` (object, not `author`)
    
    Mixing the two in one script (e.g. listing issues via CLI then paging comments via API) requires per-source key names. **Fix:** pick one source and stick with it, or write a tiny adapter:
    ```python
    def normalize_camel(d): return {k.replace('At','_at'): v for k,v in d.items()}
    ```

17. **Cron schedule is interpreted in LOCAL time, not UTC** (learned 2026-07-16, contradicts the deployment intent). The `pm-daily-evening-report` job has `schedule: "0 15 * * *"`. The deployment spec claims this means "15:00 UTC = 23:00 CST", but on this Windows host the cron ticker runs the schedule in **local CST time**. The job's `last_run` timestamps (e.g. `2026-07-16T15:08:02+08:00`) confirm it fires at **15:00 CST = 07:00 UTC**, not 23:00 CST. **Consequence:** the §6 "明日期望触发" table and §1 "今日做了什么" window need to be anchored to the ACTUAL fire time, not the UTC interpretation. If your windows are `[15:00 UTC D-1, 15:00 UTC D]`, they're off by 8 hours. **Fix options (any one):**
    - Re-anchor the 24h window to the actual local fire time (e.g. `[2026-07-15 15:00 CST, 2026-07-16 15:02 CST]`) and convert UTC event timestamps to CST before comparing
    - Fix the cron schedule to `0 23 * * *` for 23:00 CST (= 15:00 UTC) — but this requires editing `jobs.json` AND restarting the Gateway (see SKILL.md "Gateway restart is required to pick up newly-registered cron jobs")
    - Verify `last_run` timestamp in jobs.json before assuming the schedule interpretation; on Windows + Hermes cron it has been local-time
    
    Don't trust the schedule string alone. Cross-check with the most recent `cron/output/<job_id>/*.md` timestamp.

---

## 6. Daily-Report-Specific Operational Checks

When generating the daily, also surface:

| Check | Command | When to flag |
|---|---|---|
| **Zombie crons** | `python -c "import json; ..."` (see §2.3) | Any cron with `last_status == "error"` AND no recent `.md` output |
| **Cron liveness (last fire)** | `ls -lt <profile_home>/cron/output/<job_id>/ \| head -2` | Output dir newest file >2× schedule period old |
| **Workdir drift** | per `SKILL.md` §"Pitfall: Cron workdir drift..." | `os.path.isdir(cron['workdir'])` is False |
| **Identity drift** | `bash scripts/verify_github_identity.sh <profile>` | Exit 10/11/12 |
| **Open PR drift** | `gh pr list --state open --json number,updatedAt` | Any PR `updated_at > 7 days ago` |
| **Stale Issue drift** | per-employee: `gh issue list --assignee <login> --state open --json updatedAt` | Any `updated_at > 24h ago` |

---

## 7. See Also

- `SKILL.md` §"Operational Maintenance" — the daily/weekly cadence
- `SKILL.md` §"PM Operations: Managing the 1+N Team Day-to-Day" — the 派单/监控/审计/拍板/升级 moves
- `SKILL.md` §"Pitfall: Cron workdir drift is silent until it isn't" — when cron liveness check fails
- `references/pm-bi-hourly-status-report.md` — the 2h playbook; daily borrows §2.1–2.5 data commands + §5 pitfalls
- `references/pm-operations-playbook.md` — 拍板/重派 templates referenced in §7 of the daily
- `references/cron-polling-behavior.md` — what each per-employee cron does (not the PM report itself)