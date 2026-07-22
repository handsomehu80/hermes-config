---
name: pm-bi-hourly-status-report
description: "PM's recurring every-2-hours status report playbook — data collection, 3-state classification, report template, pitfalls."
version: 1.5.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [pm-operations, status-report, cron, deadlock-detection]
---

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

`--jq` with a projection template keeps the output bounded. The `head -200` mentioned in the template is a guardrail only — most repos have <50 issues. **Do NOT add `comments` to the field list** — see §5 pitfall #17 (15-50 KB blob defeats `head`).

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

### 2.5 Cron liveness check (3-state classification, learned 2026-07-15)

The 2026-07-14 report (#11) incorrectly diagnosed "team silent 21h" as "cron ticker died". The 2026-07-15 report (#12) corrected this: cron was firing perfectly every 30 min and the LLM was returning `[SILENT]` correctly under the existing rule. The fix is to upgrade the liveness check from "is cron firing?" to a **4-state classification** (3 + the boss-merge deadlock from §2.7) that distinguishes healthy-idle, stale-verdict-deadlock, boss-merge-PR-deadlock, and cron-dead.

```bash
# Step A: cron firing? — check output dir for fresh .md files
ls -lat "/c/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output/" | head -5
# find the job_id subdir, then:
ls -lat "/c/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output/<job_id>/" | head -5

# Step B: LLM executing? — check file size (skill dump alone is ~50 KB; pure [SILENT] responses are ~80 KB)
# recent .md files < 1 KB = script crashed before LLM (different problem)
# recent .md files > 50 KB = LLM ran

# Step C: LLM verdict — tail the latest .md, look for "## Response\n\n[SILENT]"
tail -c 300 "/c/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output/<job_id>/<latest>.md"

# Step D: open assigned Issues for the agent under check
gh issue list --assignee @me --state open --json number,title,updatedAt --jq '.[] | "#\(.number) [\(.updatedAt)] \(.title[0:60])"'

# Step E: open PRs waiting on boss-merge (§2.7 signal)
gh pr list --state all --json number,title,state,reviewDecision,updatedAt \
  --jq '.[] | select(.state == "OPEN") | "#\(.number) [\(.updatedAt)] rev=\(.reviewDecision // "—") | \(.title[0:60])"'
```

**4-state classification (use this in §2 of every 2h report):**

| Cron firing? | LLM executing? | LLM verdict | Open assigned Issues? | Open PRs waiting on boss-merge? | Diagnosis | 报告标注 |
|---|---|---|---|---|---|---|
| ✅ fresh .md | ✅ >50 KB | `[SILENT]` | ❌ none | ❌ none | healthy idle | 🟢 |
| ✅ fresh .md | ✅ >50 KB | `[SILENT]` | ✅ open + last_verdict_age > 48h + last_verdict_actor ≠ self | ❌ none | **stale-verdict deadlock** | 🔴 |
| ✅ fresh .md | ✅ >50 KB | `[SILENT]` | ✅ open with "等 PR 合并" condition | ✅ ≥1 OPEN > 24h with reviewer PASS | **boss-merge-PR deadlock** (§2.7) | 🔴 (with PM-fix recipe) |
| ✅ fresh .md | ✅ >50 KB | doing work | any | any | healthy active | 🟢 |
| ❌ no new .md | — | — | any | any | **cron dead / Gateway down** | 🔴 |
| ✅ fresh .md | ❌ <1 KB or empty | — | any | any | **script crashed** | 🔴 |

The 🟢/🔴 label in §2 红黄绿灯风险 should reflect the diagnosis, not just activity. **Two consecutive 2h reports where the diagnosis is "stale-verdict deadlock" or "boss-merge-PR deadlock" → escalate to PM intervention** (派单 in #8 / Iron Rule #8 ping, or PM-direct-action merge summary — see §2.7).

### 2.6 UPPERCASE cron job duplicate trap (learned 2026-07-15)

Discovered in `handsome_company_developer/cron/jobs.json`: the `last_status` field can lie when there are duplicate cron job registrations with different name casings.

**Symptom:** `oneplusn-DEV-task-polling` (UPPERCASE) shows `last_status=error`, but `oneplusn-dev-task-polling` (lowercase) shows `last_status=ok` AND its output dir is full of fresh `.md` files. The "error" is a stale state field from an earlier registration; the script is actually firing fine.

**Diagnostic:** `last_status=error` alone is not enough. Always pair with the output-dir freshness check (§2.5 Step A) before declaring cron dead.

**Fix path (only if confirmed false alarm):** `hermes cron delete <job_id>` for the duplicate job, then verify only one registration remains. Do NOT trust `last_status` as the sole signal — it's a state field that lags the actual firing.

**Canonical 5-line health check (run for each profile before the report):**

```python
import json, os
for prof in ['handsome_company_developer','handsome_company_reviewer','handsome_company_manager']:
    p = f'C:/Users/Administrator/AppData/Local/hermes/profiles/{prof}/cron/jobs.json'
    if not os.path.isfile(p): print(prof, 'NO jobs.json'); continue
    d = json.load(open(p, encoding='utf-8'))
    for j in d['jobs']:
        wd = j.get('workdir','')
        out_dir = os.path.join(f'C:/Users/Administrator/AppData/Local/hermes/profiles/{prof}', 'cron/output', j.get('id','?'))
        latest = ''
        if os.path.isdir(out_dir):
            files = sorted(os.listdir(out_dir))
            if files: latest = files[-1]
        wd_ok = 'OK' if (not wd or os.path.isdir(wd)) else 'MISSING'
        print(f"  {j['name'][:40]:<40} sched={j['schedule'].get('display','?')[:12]:<12} last_status={str(j.get('last_status','null'))[:8]:<8} wd={wd_ok} latest_output={latest}")
```

This is the §3 contribution-table backbone: each row's "本期动作" can now cite the latest `.md` filename + verdict, not just "0 action".

### 2.7 Boss-merge-PR deadlock — distinct from AND-trigger between employees (added 2026-07-18)

The SKILL.md "PM Operations: Pitfalls" describes the **AND-trigger between employees** deadlock (Issue body says "等 #X close" + both X and Y owned by different employees互相等). There is a SECOND deadlock class that looks identical from above but has a different unblock path: **boss-merge-PR deadlock**.

**Shape:**
- Reviewer writes `Verified and closed by reviewer (PASS, PR #N 可合并)` on the Issue → Issue is CLOSED.
- The PR itself stays in `OPEN` state because **nobody** ran `gh pr merge #N` — reviewer's RULES say they validate, not merge.
- Downstream Issues (e.g. #8 verifier, #19/#20 follow-up) were dispatched with conditions like "等 #N merged 后启动" or depend on the PR's main-line code.
- Dev can't push follow-up commits until the PR is merged (otherwise the new branch diverges from main).
- Boss has not noticed or has been deferring. The PM is the only one who sees the full picture.

**Symptoms** (all three must hold):
- Cron firing for dev + reviewer + PM ✅
- LLM returning `[SILENT]` for all three ✅
- `gh pr list --state all` shows N PRs (N≥1) with `state=OPEN` > 24h AND the matching Issues `state=CLOSED` ✅
- `gh pr view <N> --json reviewDecision,comments` shows reviewer already wrote PASS in Issue comment

**Why the existing 3-state classification misses this:** the §2.5 table labels "[SILENT] + open assigned Issues with `last_verdict_age > 48h` from OTHER side" as 🔴 **stale-verdict deadlock** — accurate label, but the fix recipe in §2.5 says "派单 reviewer to independently verify any PASSED-but-unmerged PR". That's reviewer-side action; the **boss-side action gap** is invisible until the PM notices reviewer already PASSed and is just waiting for the merge.

**Fix recipe (PM-direct-action, escalate after 2 consecutive 2h reports):**
1. Run `gh pr list --state all --json number,title,state,reviewDecision,additions,comments` to enumerate stuck PRs.
2. For each PR with `state=OPEN` and `reviewDecision` ≠ null (reviewer approved) OR reviewer wrote "PASS" in linked Issue comments, draft a one-liner merge plan.
3. Use the new 4th state in §2.5: **boss-merge-PR deadlock** — label 🔴, but with explicit **PM-fix recipe = "review the 3 PRs, write a `gh pr merge 14 15 13` ready-to-paste line for the boss"** rather than waiting for the boss to act.
4. After 2 consecutive 2h reports showing this state, stop asking the boss A/B/C and **deliver the merge command as part of the report**. Frame it as "copy-paste this to unblock everything" — the boss has 1 keystroke left.

**Reference concrete case (2026-07-18 PM #N):** PR #14 (+435 lines), PR #15 (+901), PR #13 (+917) all OPEN > 5 days; reviewer wrote PASS on Issues #6/#7 (now CLOSED). Dev's #19/#20 follow-up branches sat idle 57h waiting for the PRs to land. Boss had not selected any A/B/C option from prior bi-hourly reports. PM's escalation: "I'll review PR #13/#14/#15 content, draft a merge-ready summary, and include the one-liner in the next report. Boss copy-paste → all 4 Issues unblock."

### 2.8 Cron output dir → friendly job name disambiguation (added 2026-07-18)

Each `<profile_home>/cron/output/<job_id>/` directory is named by a **hashed job_id** (e.g. `42173ac76d3f`), not the friendly job name (`oneplusn-dev-task-polling`). When the bi-hourly diagnostic walks these dirs to verify cron liveness, you cannot tell which friendly job a dir belongs to from the path alone.

**Recipe to map hash → friendly name:**

```python
from pathlib import Path
out_root = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output")
for d in sorted(out_root.iterdir()):
    if not d.is_dir():
        continue
    files = sorted(d.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        continue
    # First line of any .md is "# Cron Job: <friendly-name>"
    first_line = files[0].read_text(encoding="utf-8", errors="replace").splitlines()[0]
    print(f"{d.name}  →  {first_line}")
```

Output shape: `42173ac76d3f  →  # Cron Job: oneplusn-dev-task-polling`. Use this to verify the §2.5 freshness check is reading the right job (e.g. confirm you're inspecting `oneplusn-dev-task-polling`, not `oneplusn-DEV-task-polling` — see §2.6).

**Reliability:** use `execute_code` with `pathlib.Path` rather than `terminal()` with `cat`/`ls`. Per parent SKILL.md "Known Fixes #14", MSYS rewrites Windows paths even with `MSYS_NO_PATHCONV=1`. `pathlib.Path` from `execute_code` is the only fully-reliable way to walk `C:/Users/.../hermes/profiles/...` paths.

---

## 2.12 The "fastest-mtime trap" — per-friendly-name liveness for oneplusn employees (added 2026-07-19, PM #54)

The §2.5 "Cron liveness check" recipe assumes a single output dir per profile. **That assumption is wrong for every oneplusn employee.** Per §2.6, each task-polling / config-backup / memory-cleanup job is registered TWICE under both `oneplusn-dev-…` (lowercase, real LLM) and `oneplusn-DEV-…` (uppercase, wrapper-shadowed marker). So `cron/output/` typically has **6 dirs per profile**, not 3.

### The trap in detail

Both registrations fire at the same wall-clock minute (same schedule). The "fastest mtime file across all dirs" heuristic — which is the lightest-weight sanity check for §2.5 Step A — picks the **wrong dir**:

```
ls -lat <profile>/cron/output/*/*.md | head -1
# → picks 06d40e2e1a85/<latest>.md (oneplusn-DEV-task-polling)
#   size=166B  Status: silent (empty output)
# → PM diagnoses "cron dead", but actually it's picking the shadow-dup marker
#   the real LLM run is one mtime-millisecond behind it in the lowercase dir
```

The wrong dir wins ties because the wrapper's `hermes run … | tee …` writes the marker file first, and the lowercase `hermes run …` invocation finishes 200-500ms later. Both are "fresh" by Step A's standard; the wrong one is "fresher".

Real case (2026-07-19 PM #54): the `handsome_company_developer` profile had **256 marker files** (166B each, ALL `silent`) in the UPPERCASE dir, while the matching LOWERCASE dir had **296 real LLM runs at 102678B each**. Step A's mtime-only check produced "0 LLM runs in 2h, cron appears dead" — the opposite of reality.

### The right check: per-friendly-name classifier

Use `scripts/check_pm_cron_liveness.py` (re-runnable, exits non-zero if any **selected** real job is dead). For the 2h report, filter to polling jobs; daily backup/cleanup jobs are not expected to fire in every 2h window:

```bash
# Canonical PM bi-hourly check: 30-minute polling jobs only
python scripts/check_pm_cron_liveness.py --profile handsome_company_developer --window-hours 2 --task-polling-only

# Separate full-profile audit: 26h covers daily backup/cleanup jobs with schedule jitter
python scripts/check_pm_cron_liveness.py --profile handsome_company_developer --window-hours 26

# Sample polling-only output:
# PM cron liveness for handsome_company_developer (window=2h, since 2026-07-18T20:00Z)
#   real jobs=1  shadow-dups=1  healthy=1  dead=0
#   friendly name                       verdict                markers small LLM-runs
#   oneplusn-dev-task-polling           🟢 alive (real LLM)         0     0       4
#   oneplusn-DEV-task-polling           DUPLICATE-shadow (noise)    4     0       0
```

### Mixed-cadence and reviewer-alias traps

- **Never interpret `--window-hours 2` without `--task-polling-only` as an employee-health verdict.** It includes daily config-backup/memory-cleanup jobs, which correctly have zero output in most 2h windows; the aggregate exit code will be non-zero even while task polling is healthy.
- Use `--window-hours 26` for all-job audits so daily schedules have a jitter buffer.
- Historical reviewer duplicates use asymmetric names: working `oneplusn-rev-*` versus shadow `oneplusn-REVIEW-*`. The probe canonicalizes `REVIEW → rev`; do not count the uppercase marker-only row as a second real reviewer job.

The script's `n_real_jobs` and `n_healthy` numbers are exactly what §3 摸鱼信号 needs. The `latest real` column gives the timestamp to cite in §3's "本期动作" row. The "DUPLICATE-shadow" rows are reported but flagged as **noise** — they don't affect the §2.5 4-state classification (they don't represent the LLM-side; they're Known Fix #13 wrapper artifacts).

### Decision rule for the 2h report

| Script output | §3 摸鱼信号 value | §2 红黄绿灯 label |
|---|---|---|
| `n_healthy == n_real_jobs` (all real jobs alive) | "cron tick @ HH:MM CST = NNNB LLM, [SILENT] exit" | 🟢 healthy OR per §2.5/§2.7 |
| `n_healthy < n_real_jobs` (1+ real job dead) | "🔴 cron-dead on `<friendly-name>`, no fresh output >2h" | 🔴 cron dead, restart Gateway |
| `n_real_jobs == 0` (no jobs at all) | "(profile unregistered)" | 🔴 misconfigured |

### Anti-pattern

**Don't** write a custom mtime-only inline check. The `dir → friendly-name` mapping (`§2.8`) and the `size-threshold` classification (`cron-health-audit.md`) are non-trivial; oneplusn employees have **6 dirs not 3**, and a smoke check that "looks" correct can be wrong for days before anyone notices. The script exists so the PM bi-hourly check is **deterministic**, not heuristic.

### Pair with the existing §2.5 recipe

This section does not replace §2.5 — it's the oneplusn-specific implementation of §2.5 Step A/B for cron output dirs. Once you have the per-friendly-name classifier output, the §2.5 4-state classification still applies (the script's verdict just tells you which row to label 🟢 alive vs 🔴 dead). Use both.

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

**Refinement to rule 6 (learned 2026-07-15):** "0 活动" alone is no longer sufficient — must distinguish "0 活动 + cron dead" (🔴 cron died, restart Gateway) from "0 活动 + cron firing + [SILENT]" (🟢 healthy OR 🔴 stale-verdict deadlock). Use the 4-state classification in §2.5 to label correctly.

**Refinement to rule 6 (added 2026-07-18):** when the 4-state classification returns "boss-merge-PR deadlock" (§2.7), the label is 🔴 but the §6 A/B/C menu is **optional** — escalate to PM-direct-action merge summary after 2 consecutive 2h reports.

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

**Cron-firing silent clarification (learned 2026-07-15):** a dev/reviewer returning `[SILENT]` on every cron tick while cron is firing is NOT 摸鱼 if there are no open assigned Issues with stale verdicts (i.e. genuine idle). It IS the stale-verdict deadlock if there are open assigned Issues with `last_verdict_age > 48h` from the OTHER side. Always run the §2.5 4-state classification before tagging "摸鱼".

---

## 5. Pitfalls (LESSONS LEARNED)

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

11. **Don't diagnose "cron dead" from "no GitHub activity" alone (added 2026-07-15).** The PM #11 report made this error. The correct diagnostic is the 4-state classification in §2.5 — check output-dir freshness + LLM verdict tail + open assigned Issues + open PRs waiting on boss-merge. "No GitHub activity for 22h" can mean: (a) cron dead, (b) stale-verdict deadlock, (c) boss-merge-PR deadlock, (d) genuinely no work AND no assigned open Issues. Four very different states with four very different fixes.

12. **UPPERCASE cron duplicates show stale `last_status=error` (added 2026-07-15).** When historical on-boarding scripts registered jobs in two naming conventions, the duplicate UPPERCASE jobs carry stale error state from earlier failures even when the actual script is firing fine. Pair `last_status=error` with the §2.5 freshness check before acting on it.

13. **Cross-check PRs against closed Issues (added 2026-07-15).** PR #14 / #15 were OPEN 24h+ while Issues #6 / #7 were already CLOSED — the "Issue closed ≠ PR merged" anti-pattern. Always include a PR column in the 进度矩阵 with explicit `state` (OPEN/MERGED/CLOSED), and flag in §2 any PR that has been OPEN > 24h with its Issue already closed.

14. **`gh issue list --json comments` returns an ARRAY, not a count** (added 2026-07-16). When you query `gh issue list ... --json number,comments`, the `comments` field is `[{id, author, body, ...}, ...]` — an array of full comment records, not an integer count. The §2.1 commands avoid this by using `--jq` projection explicitly, but if you ever want a comment count via `gh issue list --json`, drop `comments` from the field list and use `gh api 'repos/<org>/<repo>/issues/comments?per_page=100&...'` (with the §2.4 pagination fix) instead. Same trap exists for `--json reactions`, `--json labels`, and `--json assignees` — all return arrays of objects, never counts.

15. **`gh issue list --json` uses camelCase keys; `gh api` uses snake_case** (added 2026-07-16). Same data point has different names depending on which gh surface you query:
    - `gh issue list --json` → `createdAt`, `updatedAt`
    - `gh api 'repos/<org>/<repo>/issues/comments'` → `created_at`, `updated_at`
    
    If you mix the two surfaces in one report (e.g. §2.1 uses CLI, §2.4 uses API), use per-source key names or normalize. The §2.1 `--jq` projection in this file uses the camelCase keys; the §2.4 `--jq` projection uses snake_case — both are correct for their respective source. Don't mix them.

16. **`execute_code`'s Python `subprocess.run(cwd=...)` fails with WinError 267 on phantom Windows subdirs** (added 2026-07-17, PM #154 run). The cron prompt's example path `cd /d/onboarding/handsome-s-company` is correct on this deployment (the team work-dir IS the repo root — there is NO `agent_workflow/` subdir). When I tried to "be helpful" and `subprocess.run(['git', 'log', ...], cwd='D:/onboarding/handsome-s-company/agent_workflow')` from `execute_code`, Python crashed with `NotADirectoryError: [WinError 267] 目录名称无效` because the subdir doesn't exist. **Fix:** for `git log` and other cwd-sensitive commands, always use `terminal()` (which respects MSYS path translation) rather than `subprocess.run(cwd=...)` from `execute_code`. Pattern:
    ```python
    # WRONG from execute_code — WinError 267 on missing subdir
    subprocess.run(['git', 'log', '--since=2h', '...'], cwd='D:/path/agent_workflow', capture_output=True)

    # RIGHT — terminal() handles MSYS correctly AND you can verify cwd first
    #   1. ls /d/onboarding/<team>/  (verify no extra subdir beyond agents/ etc.)
    #   2. cd /d/onboarding/<team> && git log --since=2h --pretty=format:"%h | %ai | %s" | head -30
    ```
    The same trap waits for any `cd /d/<team>/<maybe-subdir>` invocation. When the prompt template mentions a subdir, **always `ls` the parent first**. The §2.3 work-dir drift diagnostic catches the *symptom* (empty git log) but not the *cause* (cwd pointed at a path that never existed).

17. **`gh issue list --json ...,comments,assignees,labels` returns a 15-50 KB blob that defeats `head`** (added 2026-07-17, PM #154 run). With `--json comments` in the field list, every issue row embeds its **full** comment thread as nested objects (id, author, body up to several KB each, createdAt, etc.). On the 2026-07-17 dataset (16 issues, 2 with 7 comments each), the raw JSONL output was ~15 KB on one line — `head -200` returned the same line, nothing useful. Two fixes:

    ```bash
    # Option A — drop comments from --json, get rest compact; separately use gh api for comment counts
    gh issue list --repo <org>/agent_workflow --state all \
      --json number,title,state,assignees,labels,updatedAt \
      --jq '.[] | "#\(.number)|\(.state)|\([.assignees[].login]|join(","))|\([.labels[].name]|join(","))|\(.updatedAt)|\(.title[0:50])"'

    # Option B — from execute_code, json.loads() the full stdout and project in Python
    # (the §2.1 --jq above is faster, but if you need body content too, B is the way)
    ```

    The cron template's `| head -200` guardrail is a legacy from `gh issue list --json number,title,state,...` (no comments). When you add `comments` to the field list, `head` becomes a no-op. Always pair `head` with `--jq` projection that emits one row per issue.

### 2.9 PR merge-readiness diagnostic (added 2026-07-18, refined 2026-07-22)

When the §2.7 boss-merge-PR deadlock is suspected, two questions must be answered before drafting a merge one-liner: **(a) is each PR actually mergeable?** and **(b) which PRs are clean vs need rebase?**

**The fastest one-shot check: query BOTH `mergeable` AND `mergeStateStatus` in a single `gh pr view` call.** `mergeStateStatus` is the actionable field — it tells you WHY (DIRTY = needs rebase, BEHIND = needs fetch+rebase, BLOCKED = required check failed, CLEAN = ready, UNKNOWN = GitHub hasn't computed). `mergeable` alone is boolean (true/false/UNKNOWN) and loses the WHY.

```bash
# Canonical one-shot pre-flight for all stuck PRs at once
for n in 13 14 15; do
  gh pr view $n --repo <org>/agent_workflow \
    --json number,state,mergeable,mergeStateStatus,headRefName,baseRefName,additions,createdAt,updatedAt \
    --jq '"\(.number) | state=\(.state) mergeable=\(.mergeable) mergeStateStatus=\(.mergeStateStatus) +\(.additions) \(.headRefName) -> \(.baseRefName)"'
done
```

**Field interpretation table:**

| `mergeable` | `mergeStateStatus` | meaning | action |
|---|---|---|---|
| `MERGEABLE` | `CLEAN` | clean merge candidate, GitHub agrees | `gh pr merge <N> --merge` direct |
| `MERGEABLE` | `BEHIND` | main moved ahead; fast-forward / rebase will fix | `git fetch && git rebase origin/main && git push --force-with-lease` then merge |
| `CONFLICTING` | `DIRTY` | real conflict, needs rebase resolution | rebase + resolve + push + merge |
| `CONFLICTING` | `BLOCKED` | required check failed (rare on this repo — no CI configured) | check `gh pr view <N>` body for required checks |
| `UNKNOWN` | `UNKNOWN` | GitHub hasn't computed yet (no Actions / slow rate-limit) | wait 30s and re-query, or fall back to `git merge-tree` (§2.9 fallback) |

**Fallback when `git fetch origin` succeeds — use `git merge-tree` for a deterministic, side-effect-free conflict check:**

```bash
# Verify base ref exists locally first
cd <team-work-dir>
git fetch origin --quiet   # may time out on this host — see "Fallback when git fetch fails" below

# For each OPEN PR, compute merge-base against origin/main and pipe to merge-tree
PR_BRANCH="origin/<pr-branch>"   # e.g. origin/feat/issue-6-budget-middleware
BASE=$(git merge-base origin/main "$PR_BRANCH")
git merge-tree "$BASE" origin/main "$PR_BRANCH" | head -20
```

`merge-tree` output interpretation:
- Contains `<<<<<<<` markers, `changed in both`, or `CONFLICT (...)` → **CONFLICTING** — needs rebase before merge
- Contains only `added in remote` / `added in local` lines with no conflict markers → **clean merge candidate**
- Empty or shows only added-side hunks → trivially clean

The merge-base + merge-tree invocation never touches the working tree — safe to run from any cron context, no risk of half-merged state. **But** when `git fetch origin` times out (Failed to connect to github.com:443 — seen on 2026-07-21 PM #81), `merge-tree` operates on stale local `origin/main` and produces a wrong verdict. **In that case, `gh pr view --json mergeable,mergeStateStatus` is the sole authority** — `gh` uses its own authenticated HTTPS path via `~/.config/gh/hosts.yml`, separate from git's fetch path. Don't fail the report when fetch is unreachable; note it in §5 and ship the `gh pr view` verdict.

**Verified-working real case (2026-07-22 PM run, current session):**

```text
PR # 13 state=OPEN   mergeable=MERGEABLE mergeStateStatus=CLEAN       +  917 createdAt=2026-07-13
PR # 14 state=OPEN   mergeable=CONFLICTING mergeStateStatus=DIRTY     +  435 createdAt=2026-07-13
PR # 15 state=OPEN   mergeable=CONFLICTING mergeStateStatus=DIRTY     +  901 createdAt=2026-07-13
```

This is the canonical "1 clean + 2 dirty" pattern. The PM-direct-action one-liner (§2.10) must reflect this split:
- **PR #13** → direct `gh pr merge 13 --merge`
- **PR #14 + #15** → `git rebase origin/main && git push --force-with-lease` first, then merge

**Earlier real case (2026-07-18 PM #51, replaced by 2026-07-22):**

| PR | branch | mergeable (gh) | git merge-tree result | action |
|---|---|---|---|---|
| #13 | `feat/issue-10-ralph-loop-poc` | UNKNOWN | clean (no markers) | merge directly |
| #14 | `feat/issue-6-budget-middleware` | UNKNOWN | **CONFLICTING** on `docs/budget-middleware.md` | rebase first |
| #15 | `feat/issue-7-evaluator-harness` | UNKNOWN | clean (no markers) | merge directly |

**Important caveat — state can flip between reports in EITHER direction** (added 2026-07-22, real case). PR #14 and #15 were `MERGEABLE` on the 2026-07-19 PM #52 report (per the §2.10 staleness check); they flipped to `CONFLICTING` by 2026-07-22 even though no new PR was merged to main in between (only config-backup commits). Suspected cause: GitHub periodically recomputes mergeable state when any push event touches main, and the daily cron-backup pushes are exactly such events. **The previous report's `mergeable` verdict is NOT safe to copy-paste into a new one-liner** — always re-query the same day, and the Δ vs previous one-liner table (§2.10) is the explicit cross-check. When `mergeStateStatus=DIRTY`, rebase first; when `CLEAN`, merge directly.

This is the **only reliable pre-flight check** for the PM-direct-action one-liner (§2.10).

### 2.10 PM-direct-action one-liner template (added 2026-07-18)

When the §2.7 escalation fires (≥2 consecutive 2h reports showing boss-merge-PR deadlock), the report should ship a **copy-paste-able merge one-liner**, not another A/B/C menu. Template shape:

```bash
# Step 1: merge PRs that the §2.9 diagnostic flagged as clean
cd <team-work-dir> && \
  MSYS_NO_PATHCONV=1 gh pr merge <N1> --merge --delete-branch && \
  MSYS_NO_PATHCONV=1 gh pr merge <N2> --merge --delete-branch && \
  echo "✅ Step 1 complete — clean PRs merged"

# Step 2: rebase + merge any CONFLICTING PRs (one at a time, force-with-lease to fail safely)
git fetch origin && git checkout <pr-branch> && \
  git rebase origin/main && git push --force-with-lease && \
  MSYS_NO_PATHCONV=1 gh pr merge <N3> --merge --delete-branch && \
  echo "✅ Step 2 complete — rebase + merge done"

# Expected downstream effects (write into the report as "what unlocks after merge"):
# - Issue #X1+#X2 reviewer-PASSed → truly CLOSED (was reviewer-closed but PR was floating)
# - dev sees PR land → pushes #Y1+#Y2 follow-up commit → applies for close
# - reviewer starts #Z verifier's 4-scenario E2E
# - #Z pass → 6 铁规 + #7 (per-tick spend cap iron rule) gets入库
```

**Ordering rationale (cite this in the report so the boss sees the chain):**
1. Clean PRs first — they unlock downstream employees fastest, no rebase risk.
2. CONFLICTING PR last — the rebase might surface other issues that need a follow-up cycle.
3. Use `--force-with-lease` not `--force` — if a teammate pushed to the branch while you were rebasing, lease detects it and refuses.
4. Always `--delete-branch` — keeps the repo clean; dev's follow-up commits should go on a new branch off main anyway.

**Frame in the report as:** "本起转 PM-direct-action(§2.10 模板),老板按一下即可,不需要再做 A/B/C 决策。连续 N 期 A/B/C 无响应已触发升级条件。"

**Escalation threshold (refinement of §2.7):**
- **2 consecutive 2h reports showing boss-merge-PR deadlock** → recommended PM-direct-action
- **3+ consecutive 2h reports** → **required** PM-direct-action one-liner (A/B/C menus stop being useful past this point; boss has had enough chances to decide and is choosing inaction)
- The shift from "推荐" to "强制" is automatic and silent — the report just includes the one-liner from §2.10 instead of an A/B/C menu.

**Anti-patterns to avoid:**
- Don't write the one-liner with placeholders like `<PR1>` — boss can't mentally resolve 5 placeholders. List the actual numbers (13, 15, 14).
- Don't include `git push --force` — use `--force-with-lease` always.
- Don't run the rebase step automatically — dev is the one who knows the intent of their branch. The one-liner tells the boss what to paste; the boss decides whether to rebase themselves or assign dev to rebase.
- Don't bury the one-liner in §6 — it goes in §5 (PM 洞察) or right under the §0 一页速读 table where the boss is already looking.

### 2.11 `gh api --paginate > file.json` corrupts multi-page JSON (added 2026-07-18)

When you need to enumerate the **full** history of a paginated endpoint (e.g. all issue events for "last activity" diagnostics), `--paginate` writes **multiple JSON arrays** to stdout, one per page, concatenated. `json.loads()` on the combined output fails with `Invalid control character` or `Extra data` at the boundary.

**Don't:**

```bash
# WRONG — two JSON arrays glued together, json.loads fails at boundary
gh api "repos/<org>/<repo>/issues/events?per_page=100" --paginate > events.json
python -c "import json; json.load(open('events.json'))"   # JSONDecodeError
```

**Do — fetch pages explicitly:**

```bash
# RIGHT — explicit page-by-page fetch, each page is a valid single JSON array
gh api "repos/<org>/<repo>/issues/events?per_page=100&page=1" > events_p1.json
gh api "repos/<org>/<repo>/issues/events?per_page=100&page=2" > events_p2.json
# Stop when page N returns [] (no more results)

python -c "
import json
items = []
for p in ['events_p1.json', 'events_p2.json']:
    raw = open(p, encoding='utf-8').read().strip()
    if raw:
        items.extend(json.loads(raw))
print(f'Total events: {len(items)}')
recent = [x for x in items if x['created_at'] >= '2026-07-18T12:01:00Z']
print(f'Since 2h cutoff: {len(recent)}')
"
```

**Alternative: `gh api ... | jq -s 'add'`** — works but only if `jq` is installed (often missing on Windows). Explicit per-page calls + python merge is the cron-safe path.

**Why `--paginate` is fine for `--jq` (single command) but breaks for file redirection:** `--paginate` + `--jq` processes each page internally and emits a single merged stream. `--paginate > file` writes the raw response bodies, one array per page, no merging. Different code paths, different outputs.

**Generalized rule:** if the response is small enough to fit on one page (`per_page=100` and total count < 100), `--paginate` is fine. As soon as the dataset crosses 1 page, switch to explicit `?page=N` and merge yourself.

**Symptom when you got it wrong:** `JSONDecodeError: Invalid control character at: line 1 column 20001 (char 20000)` — almost always a `--paginate` boundary, not a real malformed-JSON problem. Switch to explicit page calls and the parse succeeds.

18. **The "完成但未沟通" pattern: dev commits but does not open the PR** (added 2026-07-17, PM #154 run). Observed in #19/#20: dev landed first commits (`710ec41`, `bcbd1ce`) on feature branches 19h before report time, but at report time: Issue still OPEN, no PR opened, no PR-review tag flipped, no comment posted on the Issue body saying "PR ready at #N". Same Issue-update and Issue-comment timestamps stayed pinned to "接单 ack" 19h earlier. **Diagnostic signal:** if `git log --all --since=24h` shows N+ commits by dev but `gh pr list --state all` shows the same N as 24h ago, dev has settled into "commit-only" mode without the wiring step. **§2.5 4-state label:** this is NOT 摸鱼 (cron is firing, dev IS active per git) — it's a workflow-state stall that needs the PM to nudge dev with "open the PR" + assign reviewer, not a fresh dispatch. PM §5 洞察 should call this out explicitly so the boss sees the handoff is half-done, not that dev is idle.

19. **`gh api .../issues/comments?per_page=N` returns `issue_url`; `split("/")[-3]` gives the repo name, not the issue number** (added 2026-07-17, PM #155+ run). Common off-by-2 bug. Each bulk-comment row carries `issue_url = "https://api.github.com/repos/<org>/<repo>/issues/<N>"`. Splitting on `/` gives 8 segments: `.[-1]` = `N` (issue number), `.[-2]` = `"issues"`, `.[-3]` = `<repo>` (e.g. `"agent_workflow"`). Symptom in `--jq` output: `"issue":"agent_workflow"` instead of `"issue":"19"`. Same trap applies to any `issue_url` from a comment payload (single-issue call, PR review comment, etc.). Always use `.[-1]` for the issue number. The §2.4 template renders `issue_url` as part of a label string (not an extracted number), so it sidesteps the trap; but if you want the bare integer for `sort_by(.issue)` or numeric filtering, use `.issue_url | split("/") | .[-1] | tonumber`.

20. **When the 2h window returns 0 events, expand to 4h/12h before tagging 摸鱼** (added 2026-07-17, PM #155+ run). The cron template's hard rule is "0 commit + 0 评论 + 0 PR action in 2h = 摸鱼" but that verdict is only reliable AFTER distinguishing genuine idle from "the 2h window doesn't overlap a tick". Any 2h window covers 4 per-employee 30-min cron ticks, so an honest 摸鱼 verdict needs **all 4 ticks** to have been silent. If your 2h window covers a deliberate quiet period (e.g. all-night CST for a China-based team, or between-sprint lulls), expand the window:
    ```bash
    ISO_2H=$(date -u -d "2 hours ago"  "+%Y-%m-%dT%H:%M:%SZ")
    ISO_4H=$(date -u -d "4 hours ago"  "+%Y-%m-%dT%H:%M:%SZ")
    ISO_12H=$(date -u -d "12 hours ago" "+%Y-%m-%dT%H:%M:%SZ")

    N_2H=$(gh api ".../comments?since=$ISO_2H&per_page=100&sort=created&direction=desc" | jq length)
    [ "$N_2H" -eq 0 ] && {
      N_4H=$(gh api  ".../comments?since=$ISO_4H&per_page=100&..."  | jq length)
      N_12H=$(gh api ".../comments?since=$ISO_12H&per_page=100&..." | jq length)
      echo "2h empty; 4h=$N_4H, 12h=$N_12H — last activity ~$(( $(date +%s) - $(date -d "$ISO_12H" +%s 2>/dev/null || echo 0) ))s ago"
    }
    ```
    If 12h shows N≥1 and 2h shows N=0, the team is **healthy between sprints** — not 摸鱼. Report this as "expanded window shows last activity at `<YYYY-MM-DDTHH:MM:SSZ>`, Δt = Nh"; the §3 contribution table's 摸鱼信号 column should show "🟡 0 (extended window shows activity at <time>)". Reserve the 摸鱼 flag for the genuine case: 12h empty on a team with open assigned Issues (stale-verdict-deadlock from §2.5).

22. **Never emit a literal "#N" or "#N+1" placeholder in the report title — always fill in the actual number (learned 2026-07-19, PM #63 run).** §5 #6 above says to count from cron install (read `<profile_home>/cron/jobs.json`, find first `.md` to anchor). The pitfall: in recent bi-hourly reports in `cron/output/d26c66fbbdd0/`, several reports wrote `#N` or `#N+1` *literally* as the title placeholder instead of the resolved integer. Example: report at 18:03 CST wrote `#61`; report at 20:03 CST wrote `#N+1` (a placeholder, not a number); the next reader can't tell whether the count is 62, or "N+1 where N is from the previous report", or "N+1 where N is the cron lifetime count". **Always resolve to an integer before publishing.** If unsure, walk the report dir by mtime, count `.md` files since the first one (anchor), and use that integer. The regex `#\s*(\d{1,3})(?:\s|\(|期|UTC|CST)` will pollute results with PR numbers (13/14/15) if applied to the report's own body — anchor on the title alone, or count `.md` files by mtime to be safe.

21. **The "[SILENT] = 摸鱼" false positive: cron-firing + LLM-silent ≠ idle (added 2026-07-18).** A common PM error: see "0 commits + 0 comments in 2h" → tag 摸鱼. But the [SILENT] cron output (see §2.5 Step C) shows the LLM is doing exactly what its skill says to do when there's no new feedback: return `[SILENT]`. The diagnostic chain is: (1) §2.5 Step A confirms cron firing (fresh .md in output dir); (2) §2.5 Step B confirms LLM executing (file > 50KB); (3) §2.5 Step C confirms LLM verdict (`[SILENT]`); (4) §2.5 Step D shows open assigned Issues, if any. Only after ALL four checks should you tag 摸鱼. In the 2026-07-18 PM run, both dev and reviewer were returning `[SILENT]` correctly under the skill — not 摸鱼, but "waiting for boss to merge PRs" (boss-merge-PR deadlock per §2.7). The §3 contribution-table row should show "0 commit / 0 评论" but with the §2.5 4-state label (e.g. "🟢 healthy idle" or "🔴 boss-merge-PR deadlock"), NOT "🔴 摸鱼". Reserve "🔴 摸鱼" for the case where Steps A-C confirm cron firing + LLM executing + LLM doing real work BUT no GH-side artifacts AND no boss-merge-PR deadlock — i.e. employee is genuinely idle despite having open work.

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

**Added 2026-07-15:** add a 6th number when relevant — **cron liveness diagnosis** from §2.5. If "stale-verdict deadlock", the 6th row should say so explicitly (e.g. "team deadlock: 22h49m since last external action, cron firing every 30min, LLM [SILENT]"). Boss uses this to distinguish "system down" from "team stuck waiting on each other".

**Added 2026-07-18:** the 6th number, when boss-merge-PR deadlock is the diagnosis, should also include the **merge-readiness line**: e.g. "boss-merge-PR deadlock: PR #14/#15/#13 all reviewer-PASSed; `gh pr merge 14 15 13` is the one-line unblock". This makes the §6 A/B/C menu optional instead of required.

---

## 7. See Also

- `SKILL.md` §"PM Operations: Managing the 1+N Team Day-to-Day" — the move-by-move playbook (派单/监控/审计/拍板/升级)
- `SKILL.md` §"PM Mode: Team-Led Strategic Analysis" — for on-demand deep analysis with subagents (NOT this cadence)
- `references/cron-polling-behavior.md` — the 30-min task-polling cron, with the MSYS `gh api` gotcha and the `[SILENT]` protocol
- `references/windows-msys-tooling.md` §Pitfall 4 — MSYS path rewrite (the `MSYS_NO_PATHCONV=1` fix)
- `references/pm-operations-playbook.md` — full worked examples of dispatch / audit / 拍板
- `agent-task-polling/references/stale-verdict-deadlock.md` — full diagnostic + Iron Rule #8 candidate (referenced from §2.5)
- `SKILL.md` §"Pitfall: Cron workdir drift is silent until it isn't" — when `git log` returns empty in the wrong workdir

## 8. Pitfall: `execute_code` XML-tag parameter trap (added 2026-07-21, PM #87)

When passing Python code as the `code` parameter to `execute_code`, **NEVER include literal `</code>`, `</invoke>`, or any other XML-like closing tag inside the code value**. The parser is NOT strict XML — it takes the raw string between the parameter tags and writes it verbatim to a temp `.py` file. If `</code>` appears inside your parameter string, the resulting Python file contains a stray `</code>` line and Python raises `SyntaxError: invalid syntax`.

**Symptom (verbatim from the 2026-07-21 PM #87 run, 3 consecutive identical failures):**

```
File "C:\\Users\\Administrator\\AppData\\Local\\Temp\\hermes_sandbox_<hash>\\script.py", line NN
    </code>
    ^
SyntaxError: invalid syntax
```

The error always points at line N where `</code>` appeared literally in your parameter string. Often line N is the last line of the file — Python has no problem with the actual code above; only the trailing `</code>` poisons it.

**Fix when triggered:**

1. End the code parameter with the LAST line of Python code. Do NOT add `</code>`, `</invoke>`, or any other closing tag after it.
2. Verify your closing pattern is exactly `last_python_line</parameter>` — NOT `last_python_line</code></invoke></invoke>`.
3. If you've already failed 2-3 times on the same call, stop trying `execute_code` and write the script to disk via `terminal()` instead: `python -c "open('/tmp/my_script.py','w',encoding='utf-8').write('...')" && python /tmp/my_script.py`. The disk path bypasses the parameter parser entirely.

**Applies broadly:** every `execute_code` call in this Hermes environment, not just the PM cron. The 3-strikes loop is silent and wastes tool budget — embed the rule on first use, before sending the parameter.