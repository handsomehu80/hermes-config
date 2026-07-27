---
name: count-consecutive-zero-activity-script-bug
description: "Documented bug in scripts/count_consecutive_zero_activity.py (fixed 2026-07-27 PM #156) where _read_section_3 matched the cron prompt template's §3 placeholder table instead of the LLM's filled-in §3. Symptom, root cause, fix verification recipe, and the script's updated docstring are all captured here. Read this whenever the count_consecutive_zero_activity.py verdict looks inconsistent with the actual report content — it might be hitting the same trap."
version: 1.0.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [bug, pm-operations, count-consecutive-zero-activity, template-vs-response, getcha]
---

# `count_consecutive_zero_activity.py` — Template-vs-Response Matching Bug (Fixed 2026-07-27 PM #156)

## Symptom

The script returns `trailing_run=0` and `[green] no trailing zeros` for every
recent report, even when the same reports' actual §3 摸鱼信号 column shows
`🔴 连续多期无产物` in 6+ consecutive cycles. PM-direct-action escalation
delays because the script's verdict says "no consecutive zeros = no
deadlock", when the actual filled-in reports show consecutive zeros.

Reproduction observed in PM #156 (2026-07-27):

```text
$ python scripts/count_consecutive_zero_activity.py --window 6
====================================================================================================
PM bi-hourly report — trailing 0-activity run per role
====================================================================================================

  DEV  trailing_run=0  zeros_in_window=0/6  verdict=[green] no trailing zeros (last cycle had activity)
    [OK] #155  ... | 🛠 dev | handsome-hudeveloper | ... | commits / 评论 / PR | 0 = 摸鱼,3+ = 良好 |
    [OK] #154  ... | 🛠 dev | handsome-hudeveloper | ... | commits / 评论 / PR | 0 = 摸鱼,3+ = 良好 |
    ...

  REVIEWER  trailing_run=0  zeros_in_window=0/6  verdict=[green] no trailing zeros (last cycle had activity)
    [OK] #155  ... | 🔍 reviewer | Handsome-Review | ... | 同上 | 同上 |
    ...

  PM  trailing_run=0  zeros_in_window=0/6  verdict=[green] no trailing zeros (last cycle had activity)
    [OK] #155  ... (not in report)
    ...
```

**Smoking gun**: every dev/reviewer row's last column shows the literal text
`0 = 摸鱼,3+ = 良好` — that's the **template placeholder text** from the cron
prompt body, NOT the actual report's 摸鱼信号 column. Manual §3 read
of the same reports confirmed 6+ consecutive `🔴 连续多期无产物` and
`🔴 连续多期无产物，验证停滞` signals.

## Root Cause

The cron output file structure (what gets written to
`<profile_home>/cron/output/<pm-bihourly-job-id>/<timestamp>.md`) is:

```text
# Cron Job: pm-bihourly-status-report        ← line 0: wrapper header
[loaded oneplusn SKILL.md content ~64 KB]
[cron prompt body — includes the 报告模板]    ← contains a "## 3. 每人贡献" table with placeholder rows
## Response                                 ← marker between prompt and LLM body
[actual LLM response — the real report]      ← contains the filled-in "## 3. 每人贡献" with real data
```

The OLD `_read_section_3(txt)` used `re.search(r"##\s*3\..*?(?=\n##\s+\d|\Z)",
txt, re.DOTALL)` — `re.search` returns the FIRST match in the file, which
is the prompt template's `## 3. 每人贡献(本期 2h)` table. The template's
rows use literal placeholder text like:

```text
| 🛠 dev | handsome-hudeveloper | ... | commits / 评论 / PR | 0 = 摸鱼,3+ = 良好 |
| 🔍 reviewer | Handsome-Review | ... | 同上 | 同上 |
| 🐑 PM | 你(我) | ... | 派单 / 拍板 / 报告 | — |
```

None of these template rows match the script's `ZERO_PATTERNS`:

```python
ZERO_PATTERNS = [
    r"🔴\s*stale-claim",
    r"🔴\s*摸鱼嫌疑",
    r"🟡\s*无活动",
    r"🟡\s*计划内等待",
    r"0 commit / 0 评论 / 0 PR",
    r"0 commit/评论/PR",
    r"本期完成\s*[|]\s*0\s*[|]",
]
```

So every row returns `is_zero=False` → `trailing_run=0` → "[green] no
trailing zeros". The script looked healthy when the system was in real
deadlock.

## Fix (Applied)

Mirror the `_read_report_n` pattern: restrict the §3 search to text after
the last `## Response` marker. The patched `_read_section_3`:

```python
def _read_section_3(txt: str) -> list[tuple[str, str]]:
    """Return [(role_key, row_text)] from the §3 每人贡献 table.

    Looks for the section header `## 3.` AFTER the last `## Response` marker
    so we parse the LLM's actual filled-in report, not the cron prompt body's
    template table (which also contains a `## 3. 每人贡献` header with literal
    placeholder text like `0 = 摸鱼,3+ = 良好`).

    Patched 2026-07-27 PM #156: previous `re.search` (first match) silently
    matched the prompt template's §3 placeholder table instead of the actual
    filled-in report.
    """
    last_response = txt.rfind("## Response")
    if last_response < 0:
        return []
    body = txt[last_response:]
    m = re.search(r"##\s*3\..*?(?=\n##\s+\d|\Z)", body, re.DOTALL)
    if not m:
        return []
    section = m.group(0)
    # ... rest unchanged ...
```

The fix is 5 lines of code: anchor on `last_response`, slice `body` to
post-Response, then run the same regex on the body. No other functions
need to change.

## Diagnostic to Catch This in the Future

If `count_consecutive_zero_activity.py --window 6` returns
`trailing_run=0` for ≥6 reports but you manually read those reports' §3
and see consecutive `🔴` signals, the script is matching the wrong section.
Cross-check recipe:

```python
from pathlib import Path
import re
out = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/<pm-bihourly-job-id>")
files = sorted(out.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:6]
for f in files:
    txt = f.read_text(encoding="utf-8", errors="replace")
    # Restrict to post-Response (correct behavior)
    post = txt.rfind("## Response")
    real = txt[post:] if post >= 0 else txt
    # Find the dev row in §3
    matches = re.findall(r"🛠\s*dev.*", real)
    if matches:
        print(f"{f.name}: {matches[0][:200]}")
```

If the post-Response dev rows show `🔴 连续多期无产物` consistently but the
script's table row shows `0 = 摸鱼,3+ = 良好` (template placeholder), the
script bug is back — apply the fix again or check the script version.

## Why the Bug Was Invisible for So Long

The bug only manifests when the script's verdict disagrees with the
human-readable reality, AND when the PM is not actively cross-checking. The
script's `[green]` verdict is plausible-sounding: "no trailing zeros" reads
as "team is active", which is what the PM wants to believe when nothing
is moving. The boss-merge-PR deadlock is exactly the state where
**nothing moving is the symptom** — and a script that says "all clear" in
that state is a green-light to inaction.

**Generalized lesson**: any script that parses cron output files MUST
restrict its search to the post-`## Response` body. The prompt template's
sections (e.g. `## 3. 每人贡献(本期 2h)`, `## §1 进度矩阵`, `## §2 红黄绿灯风险`)
are structurally identical to the LLM response's sections, but with
template placeholder content. A `re.search` (first match) will find the
template, not the response. Always anchor on the last `## Response`
marker first.

This applies to:
- `_read_section_3` (fixed here)
- Any future helper script that parses bi-hourly output files
- The same trap may exist in `check_pm_cron_liveness.py` (TODO: verify
  that script's §0-§6 parsers all restrict to post-Response)

## Real Impact (PM #156)

The bug masked the boss-merge-PR deadlock that the PM had been actively
trying to escalate for 7 consecutive 2h cycles. The script's
`trailing_run=0` verdict implied "no 摸鱼", which the PM could have cited
as "system is healthy, no action needed" — except the manual §3 read showed
otherwise, and the §1 进度矩阵 + §2 风险表 showed 3 PRs in CONFLICTING state
unmerged for 14 days. The PM-direct-action one-liner was still emitted
based on the manual evidence, not the script verdict. After the fix, the
script's verdict aligns with the manual evidence, and future cycles can
trust the script.

## Verification Recipe (Run After Applying the Fix)

```bash
# Run the script and check the row text — it should show actual report
# content like "🔴 连续多期无产物", NOT the template "0 = 摸鱼,3+ = 良好"
python scripts/count_consecutive_zero_activity.py --window 6
```

If the row text contains `🔴 连续多期无产物` or similar real report signals,
the fix is working. If it still shows `0 = 摸鱼,3+ = 良好`, the script
is matching the template again — re-apply the fix.

## See Also

- `scripts/count_consecutive_zero_activity.py` — the patched script, with
  the fix's rationale embedded in `_read_section_3`'s docstring.
- `pm-bi-hourly-status-report.md` §5 #22 (N-extraction recipe) — same
  post-`## Response` restriction pattern, used to extract report N from
  the title in the response body, not from the template.
- `pm-bi-hourly-status-report.md` §2.5 (4-state cron-liveness classification)
  — the framework that should be cross-checked when the script's verdict
  looks inconsistent with reality.
