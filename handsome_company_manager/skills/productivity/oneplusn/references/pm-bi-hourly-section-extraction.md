# Section-Header Extraction from PM Bihourly Files (LAST-match rule)

**Learned 2026-08-03 on PM #210 run.** Two structural traps when extracting structured data from prior bihourly report files (`<profile_home>/cron/output/<job_id>/*.md`).

## Trap 1: Skill-content pollution makes `## N.` regex hit skill body, not report body

The bihourly output files are **100–112 KB** because the cron LLM is given the **entire `oneplusn` SKILL.md as context** — the full body is dumped verbatim into the output file *before* the actual report body. So when you regex-search for `## 3.[^\n]*` to find the §3 每人贡献 section:

- **First match** = skill-content (a meta-mention of `## 3.` somewhere in the SKILL.md body, e.g. pos≈21690 in a 107 KB file referencing "the §3 row")
- **Last match** = real `## 3. 每人贡献` (e.g. pos≈105431 in the same file)

The N-extraction regex (`r'#\s*📊\s*PM\s+双小时状态报告\s*#\s*(\d+)\s*\('`) is structured to filter on emoji + `\(` so it doesn't need LAST-match. **Section-header extraction has no equivalent anchor** — the SKILL.md body literally says `## 3.` `## 5.` `## 7.` etc. when referencing these sections.

### Canonical pattern — use LAST match

```python
from pathlib import Path
import re

txt = Path(latest_md).read_text(encoding="utf-8", errors="replace")

# Find ALL §3 每人贡献 occurrences; take the LAST
matches = list(re.finditer(r'##\s*3\.\s*每人贡献[^\n]*', txt))
if matches:
    seg_start = matches[-1].start()       # ← ALWAYS last
    seg = txt[seg_start:seg_start+1500]
    # ...parse rows from seg...
```

### General rule

- **N/title extraction** (e.g. `PM 双小时状态报告 #N`) — FIRST match works because the anchor (`📊 PM` + `\(`) is specific to real report titles
- **`## N.` section header extraction** — LAST match required, because the SKILL.md body mentions each section number when referencing them
- Applies to: §1 进度矩阵, §2 红黄绿灯风险, §3 每人贡献, §4 下次触发, §5 PM-direct-action, §6 PM 洞察, §7 不需要老板操作
- Applies to: `scripts/count_consecutive_zero_activity.py` §3 row parser — verify it's using `findall` with a LAST-match strategy or it's silently parsing skill content (no real signal, no trailing_run counted)

### Detection recipe

```python
from pathlib import Path
import re

f = Path(r"C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output/<job-id>/2026-08-04_06-03-09.md")
txt = f.read_text(encoding='utf-8', errors='replace')
print(f"file size: {len(txt)}")
for m in re.finditer(r'##\s*3\.[^\n]*', txt):
    print(f"  pos={m.start():>6}  text: {m.group()[:80]}")
# Expected output: multiple matches; last is the real report §3
```

## Trap 2: "Ghost-ok" whole-hour cron family failure mode

**Observed 2026-08-03 on PM profile** — across the 5 cron jobs registered, three went stale together:

| Cron | Schedule | Last run (UTC) | Stale since |
|---|---|---|---|
| `pm-bihourly-status-report` | `0 */2 * * *` | 2026-08-04 04:05 | 18h gap |
| `pm-daily-evening-report` | `0 15 * * *` | 2026-07-31 15:06 | 4+ days |
| `oneplusn-PM-config-backup` | `0 20 * * *` | 2026-07-31 20:02 | 4+ days |
| `oneplusn-PM-memory-cleanup` | `0 21 * * *` | 2026-08-03 21:13 | OK |
| `oneplusn-PM-task-polling` | `15,45 * * * *` | 2026-08-04 05:46 | OK |

**Structural signature**: every cron whose minute-hand is `0` AND whose hour spec has no `*/N` component stopped firing; the ones with explicit minute offsets (`15,45`) or single-hour (`21`) survived.

### Hypothesis

The Gateway's cron ticker likely lost alignment with whole-hour crons during a restart window — the minute-hand comparison may be off-by-one on the boundary. Once alignment recovers, the crons fire on their own (verified: bi-hourly fired at 22:00 UTC after 18h gap, no manual intervention needed).

### Detection recipe

```bash
# Per job, check if there are recent .md files in the output dir
find "<profile_home>/cron/output/<job-id>/" -name "*.md" -mmin -180
# Empty result + jobs.json last_status=ok = ghost-ok
```

### Fix — do NOT manually re-add

- `hermes cron rm <job-id>` + `hermes cron add` — duplicate registration risk (Known Fix #13)
- Wait for the next scheduled fire (it WILL recover on its own)
- If mission-critical: trigger manually via `python ~/.hermes/scripts/<script>` with the right `.env` sourced
- Monitor: when one whole-hour cron goes ghost, expect all 3 to be in the same state — report as ONE "whole-hour cron family" row in `oneplusn status`, not 3 separate reds

### Distinguishing from Known Fix #13 (uppercase shadow duplicate)

| Signal | Known Fix #13 (uppercase shadow) | Whole-hour family ghost |
|---|---|---|
| `last_status` | ok OR error | ok |
| jobs.json entries | 2 per type (uppercase + lowercase) | 1 per type |
| Output dir file size | uppercase dir = ~200B markers; lowercase dir = real LLM output | empty (no files at all) |
| Trigger | bad wrapper registration | Gateway alignment loss |
| Fix | `hermes cron rm <uppercase-id>` | wait OR manual run script |

## See also

- `references/pm-bi-hourly-status-report.md` §5 #22 — multi-source N corroboration recipe
- `references/pm-bi-hourly-data-quality.md` — DQ-1 (PR additions 0 from list endpoint) and DQ-2 (`[SILENT]` tail discriminator)
- `references/cron-health-audit.md` — marker-file count recipe for detecting duplicate registration vs worker-dead
