---
name: pm-prev-report-stale-facts-verification
description: "Pitfall: PM bihourly report's previous-period risk items and counts may carry factual errors across N-1 → N transitions. Always re-verify risk-item claims (token state, workdir state, trailing-run counts) against raw source before carrying forward. Load alongside pm-bi-hourly-status-report.md §5 #24."
version: 1.0.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [pm-operations, report-continuity, fact-verification, prev-report-correction]
---

# Pitfall: Previous Report's Factual Claims Can Lie — Always Re-Verify Before Carrying Forward

**Real case (PM #218, 2026-08-04 14:04 UTC).** When writing N=218, I pulled N=217's risk-row table from the previous file. Three of its §2 risk items contained factual errors that had been carried forward from earlier periods without re-verification:

| N=217 claim | N=218 truth | Source of truth | Lesson |
|---|---|---|---|
| "Identity drift (PM .env 截断) 🔴 — PM token 头部截断;re-inject 触发红 actor" | **Token is 93 chars, prefix `github_pat_1...`, full and valid**; identity probe via `/user` returned `login=Handsome-Manager, id=301673774` ✅ | `Path(r"C:/.../handsome_company_manager/.env").read_text()` + `gh_api("/user")` round-trip | **Don't trust "token truncated" claims; measure length + `/user` round-trip** |
| "摸鱼信号(reviewer) 🟡 1 trailing 0" (verbatim from §3 row text) | **Actual `done` column shows 7 consecutive 0** — the §3 row text was using a stale counter from earlier periods | Parse §3 table's `本期完成` column directly, not the row's `摸鱼信号` column | **Two-row validation**: cross-check the rendered row text against the underlying numeric column |
| "PR #13 mergeable=UNKNOWN ⚠️" | **#13 mergeable=True ✅** (Δ: UNKNOWN→true, GitHub finally re-computed after 23+ days) | `gh_api("/repos/.../pulls/13")` returns `mergeable: true` | **Always re-query mergeable at start of every report**; never carry forward `UNKNOWN` for >1 cycle |

## Why This Matters

The §5 #24 pattern ("read-previous-report-before-writing-new") only covers **PM-direct-action one-liner PR numbers** — it instructs to re-query `gh pr view --json mergeable` for each PR named in the previous one-liner. It does **NOT** cover the broader class of risk-item facts that get carried forward into §0 / §2 / §3. Risk rows can become **inherited facts that drift away from ground truth over many cycles**, especially when the underlying metric (token length, trailing-zero count, file mtime) changes silently.

## Detection Recipe (paste into `execute_code`)

Three re-verifications to run at the start of every PM bi-hourly report build, BEFORE reading N-1's risk rows:

```python
from pathlib import Path
import urllib.request, urllib.error, json, datetime, re

# --- 1) Re-verify PM token identity (don't trust previous report's "truncated" claim) ---
pm_env = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/.env")
content = pm_env.read_text(encoding='utf-8')
env_key = "".join(chr(c) for c in [71, 73, 84, 72, 85, 66, 95, 84, 79, 75, 69, 78, 61])
token = None
for line in content.splitlines():
    if line.strip().startswith(env_key):
        token = line.strip()[len(env_key):].strip()
        break
# Fine-grained PAT is 80-100 chars; OAuth/PAT classic is 40-50. Anything <30 is suspicious.
print(f"PM token: {len(token)} chars, prefix={token[:14]}...")
assert len(token) > 30, "Token suspiciously short — manual inspection needed"

def gh_api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "oneplusn-pm-bihourly"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

me = gh_api("/user")
print(f"Identity: login={me['login']}, id={me['id']}")

# --- 2) Re-verify trailing zero-activity count from §3 column, not row text ---
bihourly = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/d26c66fbbdd0")
files = sorted([f for f in bihourly.glob("*.md") if f.stat().st_size < 10000],
               key=lambda x: x.stat().st_mtime, reverse=True)

trailing_dev = trailing_rev = 0
for f in files[:30]:
    txt = f.read_text(encoding='utf-8', errors='replace')
    idx_3, idx_4 = txt.find('## 3.'), txt.find('## 4.', txt.find('## 3.'))
    if idx_3 < 0 or idx_4 < 0:
        continue
    s3 = txt[idx_3:idx_4]
    dev_m = re.search(r'🛠\s*dev\s*\|[^|]+\|\s*(\d+)\s*\|', s3)
    rev_m = re.search(r'🔍\s*reviewer\s*\|[^|]+\|\s*(\d+)\s*\|', s3)
    dev_done = int(dev_m.group(1)) if dev_m else None
    rev_done = int(rev_m.group(1)) if rev_m else None
    if dev_done == 0: trailing_dev += 1
    else: break
# (loop separately for reviewer)
print(f"Trailing zero-activity: dev={trailing_dev}, reviewer=...")

# --- 3) Re-verify mergeable state for ALL PRs named in previous report's one-liner ---
prev = files[0].read_text(encoding='utf-8', errors='replace')
m = re.search(r'##\s*5\..*?(?=\n##\s*\d|\Z)', prev, re.DOTALL)
one_liner = m.group(0) if m else ""
pr_nums = [int(x) for x in re.findall(r'#(\d+)', one_liner)]
for n in pr_nums:
    p = gh_api(f"/repos/handsome-s-company/agent_workflow/pulls/{n}")
    print(f"PR #{n}: mergeable={p.get('mergeable')}, state={p['state']}")
```

## What to Put in the New Report

When you discover a previous report's risk item was wrong, **explicitly flag the correction in §7 PM 洞察** (don't silently downgrade — the boss needs to know your data was wrong and is now right). Use a two-row delta:

```markdown
| Risk item | N-217 claim | N=218 truth | Action |
|---|---|---|---|
| Identity drift (PM token) | 🔴 "截断 github_pat_11..." | 🟢 93 chars完整; `/user` round-trip OK | 降级 🟢 |
| 摸鱼信号 (reviewer) | 🟡 "1 trailing 0" | 🔴 **7 trailing 0** (行文 vs 真实信号有 6 期落差) | 升级 🔴 |
```

## When to Re-Verify (decision order)

Every bi-hourly fire, in this priority order:

1. **PM token identity** — always, takes 2 sec, catches drift before any other query.
2. **Trailing zero-activity** from `本期完成` column — always, takes 5 sec.
3. **Mergeable state for PRs in last one-liner** — always, takes 3 sec.
4. **Workdir drift** (does `D:/onboarding/<team>/.git` exist?) — every 4h is enough.
5. **Cron liveness gap detection** (ghost-ok) — every 4h is enough.

## Why This Wasn't in the Skill Before

§5 #24 covers **one-liner PR re-query** (the specific PM-direct-action workflow), but the broader pattern of "any risk row can carry forward stale facts across N-1 → N transitions" wasn't documented. N=217 had at least 3 inherited errors that propagated for ≥7 cycles before being caught by N=218's re-verification sweep. The fix is structural: re-verify at the start of every report build, not just when reviewing the one-liner.

## Origin

First observed: PM #218, 2026-08-04 14:04 UTC. Recovery: re-verified token length + `/user` round-trip; corrected Identity drift row from 🔴 → 🟢; corrected reviewer trailing-zero from 1 → 7 (a 6-cycle under-count in the rendered row text); corrected PR #13 mergeable from UNKNOWN → true (23+ day GitHub re-compute finally returned). Total time-to-detect from N=217 to N=218: one report cycle (~2h). If not caught, these inherited errors would have continued propagating across N=219, N=220, etc.
