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

**Shadow-duplicate pattern:** if a profile has TWO crons with the same `name` differing only in case (for example `oneplusn-dev-task-polling` + `oneplusn-DEV-task-polling`), the lowercase prompt-driven variant is usually the real worker. The uppercase script-driven shadow may show `error`, or it may show `ok` while emitting only an empty-output marker. Therefore this `last_status` listing is only a first pass; confirm with output sizes or `scripts/check_pm_cron_liveness.py`.

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

4. **Shadow duplicate crons are real, and `last_status=ok` does not clear them.** A profile may have 3 lowercase real LLM jobs plus 3 uppercase `script`/`no_agent` shadows. Depending on the wrapper, an uppercase shadow may show `error` with `script failed` markers **or `ok` with `silent (empty output)` markers**. Surface this in §3 as 🟡 noise and classify from case-normalized duplicate names + `script`/`no_agent` + output size, not status alone. Use `scripts/check_pm_cron_liveness.py`; remove uppercase IDs after verification.

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

18. **`gh api --jq '.[] | {obj}'` returns NDJSON, not a JSON array** (learned 2026-07-17, blocked a real daily-report run). When the jq expression produces an object per input item WITHOUT wrapping it in `[...]` and WITHOUT a stringifying filter like `@tsv`, `gh` emits one JSON object per line (NDJSON). `json.loads(stdout)` then fails with `Extra data: line 2 column 1`. This bites you specifically when you want per-row post-processing in Python (e.g. count per user, format a table) — the obvious `--jq '.[] | {a, b, c}'` form is wrong. **Fix — pick the right output shape:**

    ```bash
    # OPTION A — emit a JSON ARRAY (one parseable blob, best for downstream JSON work)
    gh api .../comments --jq '[.[] | {created_at: .created_at, user: .user.login}]'

    # OPTION B — emit NDJSON of TSV rows (one record per line, easy to split+parse)
    gh api .../comments --jq '.[] | [.created_at, .user.login] | @tsv'
    ```

    Option B is what worked in this session for the per-user comment counter — line-split on `\n`, then split each line on `\t`. `collections.Counter(parsed_lines)` gave the §4 table directly. Option A is what §2.1 already uses (the `select(.pull_request == null)` example wraps in `[...]` — note the brackets). **Anti-pattern to avoid:** `--jq '.[] | {created_at, user: .user.login, body}'` (object, no brackets, no stringifier) — produces NDJSON that breaks `json.loads()` on the whole blob.

19. **`gh api .../comments?since=<ISO8601>` is the cleanest 24h comment filter** (learned 2026-07-17). Instead of fetching all comments and filtering client-side, pass `since=2026-07-16T15:00:00Z` directly to the API — GitHub filters server-side and returns only comments created at-or-after that timestamp. Combine with Option B from #18 (`@tsv`) for line-parseable per-user counts. **Anti-pattern:** fetching all comments and filtering via Python after — costs context budget on big repos, AND burns an extra API pagination cycle. Note: `since` for issues is `?since=` on the issues endpoint; for comments it's the same query param. Check the GitHub REST docs for which collection supports the filter (most do; per-PR and per-issue-issue comments do).

20. **`git log --pretty=format:%an` + `collections.Counter` gives the §4 commit table directly** (learned 2026-07-17). The §4 "每人当日贡献" row needs per-user commits in 24h. The reliable extraction:

    ```python
    import subprocess, collections
    r = subprocess.run(['git', '-C', '<work-dir>', 'log',
                        '--since=24 hours ago', '--pretty=format:%an'],
                       capture_output=True, text=True)
    c = collections.Counter(r.stdout.splitlines())
    for user, n in c.most_common():
        print(f"  {user:30s} | {n} commits")
    ```

    Same pattern works with `--since="7 days ago"` for the §5 cross-day trend baseline. Note `--since` uses the **host clock** (CST on Windows). If your §1 window is UTC-anchored, also pass an explicit `--since="2026-07-16T15:00:00Z"` so git and gh agree on the boundary (see #12). Don't combine `%an` with `%ae` in the format — keep one field per `Counter()` axis. Also note: this host's `git log --author` matches on email substring, so use `%an` (display name) for the §4 attribution and `Counter()` for aggregation; `--author` is only needed when filtering to a specific user.

21. **The cron-output dir is the source of truth for historical reports — search it, don't guess** (learned 2026-07-17, refines §2.2 #5 + #6). The actual recipe to find yesterday's daily report:

    ```python
    from pathlib import Path
    base = Path('C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output')
    for job_dir in base.iterdir():
        if not job_dir.is_dir(): continue
        for f in job_dir.iterdir():
            if f.suffix != '.md': continue
            try:
                content = f.read_text(encoding='utf-8', errors='ignore')
                if 'PM 项目日报' in content or 'PM项目日报' in content:
                    print(f"FOUND: {f}  ({f.stat().st_size} bytes)")
            except Exception: pass
    ```

    After locating the file, extract the §5 cross-day baseline by finding `## Response` (or `rfind('# ')`) and reading 2-3KB after it — the §5 cross-day table is in there. Don't try to identify "the most recent report" by filename sort alone — multiple crons dump `.md` files in the same dir tree (`pm-bihourly-status-report`, `pm-daily-evening-report`, plus employee `task-polling` runs), and date prefixes can collide if a cron fires twice in one day. **Always grep the content for the report's signature phrase** (`PM 项目日报` for daily, `PM 状态` for bi-hourly).

22. **Duplicate-cron detection: marker file COUNT + SIZE confirms the Known Fix #13 pattern** (learned 2026-07-17, corroborates SKILL.md Known Fix #13). Concrete recipe:

    ```python
    from pathlib import Path
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for job_dir in (Path('C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output')).iterdir():
        if not job_dir.is_dir(): continue
        n_24h = n_marker = 0
        for f in job_dir.iterdir():
            if f.suffix != '.md': continue
            if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) >= cutoff:
                n_24h += 1
                if f.stat().st_size < 1000:   # real LLM runs are 15-50 KB; markers 150-200 bytes
                    n_marker += 1
        if n_marker > n_24h * 0.5 and n_24h > 0:
            print(f"  {job_dir.name}  🔴 duplicate-registration ({n_marker}/{n_24h} files are <1KB markers)")
    ```

    In this session's run: dev profile showed `DEV-task-polling` job with 32/32 files as markers (100%), reviewer showed `REVIEW-task-polling` same — exactly matching the Known Fix #13 prediction. **If you see this in §3 of the daily, the system is functionally healthy but the cron list is lying to your health dashboard.** Surface as 🟡 with explicit cleanup steps (`hermes cron rm <uppercase-job-id>` for the 3 uppercase variants per profile).

23. **After N consecutive days of 摸鱼, escalate from "老板拍板" to a PM-direct-action menu** (learned 2026-07-18, third consecutive daily report with dev/reviewer at 🔴). The §3 risk rule says "连续 3 天摸鱼嫌疑 = 🔴 升级", but the upgrade target is **NOT** another round of "请老板拍板" decision points. If yesterday's §7 already gave 4 decision points and the boss responded to 0, today's §7 must be a **concrete PM-takeover menu** (A/B/C with time/cost/limitations per boss's A/B/C preference):

    | 升级动作 | 命令示例 | 时间 | 风险 |
    |---|---|---|---|
    | **PM 代合已判 PASS 的 PR** | `gh pr merge <N> --merge --body "PM 代合:reviewer 7-13 PASS 判决,阻塞 <D> 天"` | <2 min | 越权,但可逆 |
    | **PM 代开 dev 已 push 的分支** | `gh pr create --base main --head <branch> --title "<title>" --body "<body>"` | <2 min/分支 | 替 dev 立 PR,但 dev 后续可 push 触发 CI |
    | **PM reassign Issue** | 走两步 reassign,先在 Issue 上留 comment 解释原因,再 `--remove-assignee X --add-assignee Y` | <5 min | 改变铁律 1 流程,需明示 |

    **Trigger:** if any per-employee row in §4 carries the same assessment (摸鱼嫌疑 / 摸鱼升级) for **≥ 3 consecutive daily reports** AND the previous day's §7 decision points got 0 boss action, today's §7 must use this menu format. Frame as: **"若老板今晚 23:30 前无回应,PM 默认走 A 项代合 PR #14/#15;若 B 项, dev 09:00 cron 看到 'PM 已代开 PR' 后可继续 commit;若 C 项,PM 直接 reassign #19/#20 给 reviewer 自驱"**. Do NOT keep writing "请老板拍板" if the previous day's identical prompts got ignored — that's a passive escalation that doesn't move state.

24. **"Cron fires but 0 GH-side translation" needs response-aware classification** (refined 2026-07-24). The daily report must distinguish wrapper failure, live-but-silent protocol outcomes, stale-claim deadlock, and genuine reasoning thrash. **Full `.md` size is only a transport/liveness signal** because each real output repeats the giant skill prompt; a 60–100KB file can still have a final response of exactly `[SILENT]`.

| Cron envelope | Final payload after last `## Response` | GH-side state | §3 verdict |
|---|---|---|---|
| No output dir / 0 files in 24h | n/a | n/a | 🔴 cron did not fire / broken registration |
| File <1KB, usually `script` + `no_agent` | marker / empty | no artifacts | 🟡 uppercase duplicate-shadow noise |
| File ≥5KB | semantic `[SILENT]` | no assigned open Issue | 🟢 healthy idle |
| File ≥5KB | semantic `[SILENT]` | assigned Issue unchanged; last external signal is worker's own comment | 🔴 stale-claim / new-feedback deadlock — unblock the gate or add explicit external feedback |
| File ≥5KB | **non-silent** reasoning repeatedly | 0 commits / comments / PRs / Issue actions | 🔴 cron-thrashing — LLM reasons but does not translate to action |
| File ≥5KB | non-silent | matching GH artifact exists | 🟢 productive |

**Parsing rule:** split on the **last** `## Response` marker, not the first (the prompt may contain examples). Treat the outcome as semantic silent when the last non-empty line matches `\[SILENT\]?` case-insensitively. The optional closing bracket intentionally covers legacy/truncated outputs such as `[SILENT`; explanatory text followed by a final `[SILENT]` is also a silent protocol outcome. Never infer productivity from the full-file byte size.

**Recommended probe:** use the response-aware liveness script instead of hand-counting file sizes:

```bash
python scripts/check_pm_cron_liveness.py \
  --profile handsome_company_developer \
  --window-hours 24 \
  --task-polling-only --json
```

Read `counts.semantic_silent`, `counts.non_silent`, and `counts.response_unparsed`, then cross-check assigned Issues and GH artifacts. A high `real_llm` count with `semantic_silent == real_llm` is **not** cron-thrashing by itself.

**Verified correction (2026-07-24):** the dev worker produced 48 large LLM envelopes, but many responses were exact `[SILENT]`, legacy `[SILENT`, or explanatory text ending in `[SILENT]`. The latest response explicitly said both assigned Issues were unchanged and the last commenter was the worker itself. With 0 GH artifacts, the correct classification was **stale-claim/new-feedback deadlock**, not “50 substantive reasoning runs.” This is why response parsing must precede the productivity verdict.

25. **Open-PR age column in §2 surfaces "stuck after PASS" before it becomes a 7-day incident** (learned 2026-07-18, PR #14/#15 sat for 6 days after reviewer PASS judgment). When listing open PRs in §2, include the `updated_at` age as a column:

    ```bash
    gh pr list --repo <org>/<repo> --state open \
      --json number,title,author,additions,updatedAt \
      --jq '.[] | {n: .number, age: (.updatedAt | sub("T.*"; "") | strptime("%Y-%m-%d") | (now - mktime) / 86400 | floor)}'
    ```

    **Verdict thresholds (add to §3 risk table):**
    - PR open + reviewer PASS judgment but no merge, **age > 3 days** → 🔴 (boss must merge or PM must take over)
    - PR open + reviewer PASS judgment but no merge, **age 1-3 days** → 🟡
    - PR open + 0 reviewer comments, age > 7 days → 🟡 (reviewer stalled)
    - Issue open + assignee has not commented, age > 3 days → 🟡

    In 2026-07-18 §2, PR #14 (#14d) and PR #15 (#14d) both showed `merged=---` with reviewer PASS judgments from 7-13 — the `updatedAt` age column made the 6-day stuck state visually obvious at a glance. Without the age column, the row just reads "PR #14 OPEN" and the staleness hides behind the title text.

26. **"Boss non-response" pattern: 2 consecutive daily reports with 0 boss decisions = auto-escalate to PM-takeover** (learned 2026-07-18, corollary to #23). When §7 of the previous daily report had N decision points and §4 of today's report shows that **none of the boss's expected actions materialized** (e.g. "boss was expected to merge PR #14/#15 yesterday, didn't", "boss was expected to call out dev on #19, didn't"), the today's §3 must explicitly call out:

    ```
    | boss 24h 0 决策动作 + 4 项昨日决策点 0 回应 | 🔴 | 昨日 §7 决策 1-4 全部悬空,导致今日风险从 🟡×3 🔴×3 升级到 🟡×2 🔴×4 | 新发现 |
    ```

    This makes the escalation explicit in the cross-day trend (§5) and gives the boss a clear "you have 24h to respond or PM takes over" deadline. Without this row, the report reads as "same status as yesterday" and the boss has no signal that yesterday's silence made today worse.

27. **Open count drops while closed total is unchanged = deletion/removal, not closure** (learned 2026-07-22). A missing Issue can make the snapshot look healthier without producing a `closed_at` event. Compare the **set of Issue numbers** against yesterday, not only aggregate counts. For each missing number, run `gh issue view <N> --repo <org>/<repo> --json state,closed_at,title,number,labels`:
    - resolves as CLOSED → count as closure only if `closedAt` is inside the window;
    - resolves as OPEN, while `gh issue list` did not return it → **stale-list artifact**, NOT deletion; the issue is still open and must appear in §2's snapshot with a footnote `(verified open via gh issue view; gh issue list did not return it this fire — likely filter/cache cutoff)`; §5 Δ row = 0 (counted identically both days)
    - cannot resolve (HTTP 404), while yesterday's report proved it existed → report **deleted/removed**;
    - optionally query the organization audit log when permission allows, but if that query is unavailable, leave actor/time as **unknown**.
    Never attribute the deletion to boss/PM/dev/reviewer without evidence, and do not increment any person's Issue-action count. In §5 write the exact shape: `Open −1 / Closed +0 (#N disappeared, not closed)` for true deletion, or `Open 0 / Closed 0 (#N stale-list, still open)` for the stale-list artifact.
    
    **REFINEMENT (learned 2026-07-23, on Issue #2 false-open carry-forward):** Do NOT propagate yesterday's "消失未关闭" / "still open but missing" caption into today's snapshot without a fresh `gh issue view <N>` query. Yesterday's caption is descriptive of yesterday's evidence, not authoritative for today's classification. Real case: Issue #2 was carried forward from the 2026-07-22 daily's "Open Issue 数 −1 (#2 消失了,非关闭)" into today's §2 + §5 as if still OPEN, but no fresh `gh issue view 2` was run to confirm current state. The right action sequence is: (a) note the missing-from-list number, (b) `gh issue view <N> --json state,closed_at,title` for current truth, (c) classify per the three bullets above, (d) only then write the §2 row and §5 Δ. Skipping step (b) produces a fabricated OPEN count that the boss cannot audit against.

28. **PR author is not PR assignee.** The daily template has an `assignee` column, but `gh pr list --json author` only tells who opened the PR. Query both explicitly:
    ```bash
    gh pr list --repo <org>/<repo> --state all --limit 100 \
      --json number,author,assignees,mergeable,mergeStateStatus,updatedAt
    ```
    If `assignees` is empty, render `—` in the assignee column and, if useful, put `author <login>` in the “关键” column. Never copy `author.login` into `assignee`.

29. **Current `jobs.json` runtime fields use `_at` suffixes.** Modern Hermes cron records expose `last_run_at` / `next_run_at`; older snippets that read `last_run` / `next_run` may print `null` even while the job is healthy. Use a compatibility accessor:
    ```python
    last_run = job.get('last_run_at') or job.get('last_run')
    next_run = job.get('next_run_at') or job.get('next_run')
    ```
    Pair this with output-dir mtime; `last_status` alone still cannot distinguish a real LLM worker from an empty-output shadow duplicate.

30. **Do not print raw Git remotes during report collection.** Private remotes may embed `https://x-access-token:<PAT>@github.com/...`; `git remote -v` can leak credentials into cron output and the delivered report. Prefer `gh repo view <org>/<repo> --json nameWithOwner,url,defaultBranchRef,viewerPermission`. If a remote URL must be inspected, redact the URL userinfo before logging it.

31. **Re-query volatile state immediately before delivery.** Daily collection can take several minutes while employee crons continue firing. Just before final response, run a compact live check for: open Issue count/numbers, every open PR's `mergeable` + `mergeStateStatus`, and the 24h comment count. If any value changed, regenerate the affected rows. This is especially important before an A/B/C merge decision because `CLEAN ↔ DIRTY` can flip between initial collection and delivery.

32. **Validate the report structurally and count characters, not UTF-8 bytes.** Chinese text often uses three bytes per character, so file size is not the 2500-字 budget. Before delivery verify: H1 date header, sections `## 0` through `## 8`, current CST time, four top-line activity counts, per-person rows, R/Y/G distribution, tomorrow 09:00 CST trigger, and the exact closing sentence. A practical prose-budget check strips Markdown table syntax and whitespace, then requires the remaining character count `<= 2500`; if close to the limit, trim rather than argue about counting conventions.

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