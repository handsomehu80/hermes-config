---
name: pm-bihourly-n-extraction
description: "PM bi-hourly report N-extraction pitfalls: full-width Chinese parens in titles, drift-dump + real-report coexistence in same dir, and the resulting N-counting off-by-one. Companion to the oneplusn SKILL.md §'PM bi-hourly data-quality'."
---

# PM Bi-hourly N-Extraction Pitfalls (learned 2026-08-07, PM #248)

Companion to the oneplusn SKILL.md `Title-format drift fallback` block. Three subtle traps that broke N-extraction in the PM #247 → #248 transition. Capture them here as a reference, not in the SKILL.md body, because the SKILL.md is at the 100 KB limit and these are session-specific data-quality recipes.

## Pitfall 1 — Paren style alternates ASCII vs full-width Chinese

Real production titles alternate between ASCII `(` and full-width Chinese `（`:

| N | Filename | Title fragment |
|---|---|---|
| 245 | `2026-08-07_04-01-54.md` | `# 📊 PM 双小时状态报告 #245(2026-08-07 04:01 UTC)` (ASCII) |
| 246 | `2026-08-07_06-01-24.md` | `# 📊 PM 双小时状态报告 #246（2026-08-06 22:01 UTC）` (full-width) |
| 247 | `2026-08-07_08-02-39.md` | `# 📊 PM 双小时状态报告 #247（2026-08-07 00:02 UTC）` (full-width) |

The SKILL.md primary regex `r'#\s*📊\s*PM\s+双小时状态报告\s*#\s*(\d+)\s*\('` only matches ASCII `(`. N=246 and N=247 were both missed on the initial detection. **Fix**: use the character class `[(（]` in both primary and fallback 1 patterns:

```python
PAREN = r'[(（]'
m = re.search(rf'#\s*📊\s*PM\s+双小时状态报告\s*#\s*(\d+)\s*{PAREN}', txt)
if not m:
    m = re.search(rf'#\s*状态报告\s*#\s*(\d+)\s*{PAREN}', txt)
```

Same `[(（]` substitution belongs in any other regex that wants to match the date bracket in PM-report titles (`daily-evening-report.md`, the cron-prompt header that the LLM emits, etc.).

## Pitfall 2 — Bi-hourly drift dump coexists with real report in same dir

The PM bihourly cron dir (`<profile_home>/cron/output/<job-id>/`) contains **two files per fire**: a 100-115 KB skill-content drift dump (the wrapper envelope + loaded SKILL.md regurgitated) AND a 3 KB real report body (the actual LLM-produced §0-§6 report). Both are written on the same tick; the drift dump has the **later** mtime because it's the final wrapper output.

So `sorted(files, key=mtime, reverse=True)[0]` picks the WRONG file (drift dump), and the regex either fails or matches a stale N from the skill-content pollution. Confirmed at PM #248: `files[0]` was 106 KB skill dump, `files[1]` was 3 KB real report.

**Fix**: pick the smallest file that has a real-report structure. Two recipes:

```python
# Option A: classify by size + heading presence, then pick the real report
files = sorted(bihourly.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
txt = None
for f in files:
    cand = f.read_text(encoding="utf-8", errors="replace")
    is_real = (len(cand) < 50_000
               or ("双小时状态报告" in cand and "## 1." in cand))
    if is_real:
        txt = cand
        break
if txt is None:
    txt = files[0].read_text(encoding="utf-8", errors="replace")

# Option B: secondary sort by size ascending — real reports (3 KB) come before drift dumps (100+ KB)
files = sorted(bihourly.glob("*.md"), key=lambda x: (x.stat().st_mtime, x.stat().st_size), reverse=True)
```

**Heuristic summary** (verified PM #248):
- Real report: 2.5 - 4 KB, contains `# 📊 PM 双小时状态报告 #N(` and `## 0.` through `## 7.`
- Drift dump: 100 - 115 KB, contains 2+ of `## Pitfall` / `## Operational` / `## Hard Constraints` / `## Known Fixes` / `## Per-Agent` / `## PM Mode` headings (skill-content regurgitation)

## Pitfall 3 — N-counting off-by-one when fallback fires

When the primary + fallback 1 regex both miss (e.g., drift dump loaded instead of real report), the SKILL.md recommends `len(sorted .md files) + 1` as a "rough lower bound". But this over-counts because:

- Each fire produces 2 files (drift dump + real report)
- Files from previous days persist in the dir
- A 2-day-old bi-hourly dir has ~24 fires × 2 files = 48 files, so `len + 1 = 49` is wildly wrong

**Fix order** for next PM cron fire: (1) pick the real report (Pitfall 2), (2) try the paren-tolerant regex (Pitfall 1), (3) only as last resort use file-count + 1 and flag `Δ unverified` in the report header. Never use `len(files)+1` without flagging.

## Verification recipe

After every bi-hourly fire, run this:

```python
from pathlib import Path
import re
bihourly = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/d26c66fbbdd0")
files = sorted(bihourly.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
print(f"Top 5 files by mtime:")
for f in files[:5]:
    txt = f.read_text(encoding="utf-8", errors="replace")
    PAREN = r'[(（]'
    m = re.search(rf'#\s*📊\s*PM\s+双小时状态报告\s*#\s*(\d+)\s*{PAREN}', txt)
    n = m.group(1) if m else "?"
    print(f"  {f.name}: size={len(txt):>6}  N={n}")
```

If any file in the top 5 has `N=?` but is also small (<10 KB) and contains `## 0.`, the regex is still missing the paren-style variant. Add `[(（]` and re-verify.

## Cross-references

- SKILL.md §"Title-format drift fallback" — primary + fallback 1 patterns
- SKILL.md §"Pitfall: Cron LLM drift into skill-content regurgitation" — the broader drift phenomenon
- `references/pm-bi-hourly-data-quality.md` — DQ-1 / DQ-2 / DQ-3 (PR fields, `[SILENT]` tail discriminator, urllib cross-check)