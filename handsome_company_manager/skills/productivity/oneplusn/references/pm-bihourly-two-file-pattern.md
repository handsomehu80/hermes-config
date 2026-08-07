# PM Bihourly Two-File Pattern

> Companion to `oneplusn` SKILL.md §"Pitfall: Cron LLM drift into skill-content regurgitation" — verified PM #247 (2026-08-07).

## The pattern

Each PM bihourly cron fire produces **two** `.md` files in the output dir within seconds of each other:

| File kind | Size range | Contents |
|---|---|---|
| **wrapper** | 3-9 KB | The actual report body — canonical title (`# 📊 PM 双小时状态报告 #N(...)`) + §0–§7 sections. This is the deliverable. |
| **dump** | 80-115 KB | The LLM regurgitates the loaded skill content verbatim (entire oneplusn SKILL.md body) before its final answer. Contains the same report at the tail end, but buried under 80+ KB of skill noise. |

Verified across **315+ files** in PM bihourly output dir `d26c66fbbdd0`. Wrappers cluster 3-9 KB, dumps cluster 95-115 KB. The bimodal distribution is bimodal with no overlap (gap between ~9 KB and ~80 KB).

## The right way to pick the deliverable file

```python
from pathlib import Path
bihourly = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/d26c66fbbdd0")
files = sorted(bihourly.glob("*.md"), key=lambda x: x.stat().st_size)
wrapper = files[0]   # smallest = the deliverable
dump = files[-1]     # largest = the skill regurgitation
```

**Sort by file size ascending, take the smallest.** Do NOT sort by mtime — both files have near-identical mtime (within ~6 seconds of each other).

Filenames use CST local-time; mtime is UTC. The wrapper filename pattern: `YYYY-MM-DD_HH-MM-SS.md` where HH is CST hour (e.g., a 22:01 UTC fire writes `2026-08-07_06-01-XX.md`).

## Why this matters

A future agent (or this same agent on its next fire) needs to:
- Extract N from the previous report's title (`# 📊 PM 双小时状态报告 #N(...)`) to number the current report
- Verify report structure (§0-§7 sections present)
- Cross-check Δ vs previous report

If the agent sorts by mtime and picks the latest file, it gets the **dump** — 100+ KB of skill content with the real report buried at the tail. The N-extraction regex still works (the title is in the tail), but parsing the whole dump wastes context and may confuse the LLM into thinking the previous report contained skill headings (false drift signal).

If the agent sorts by size and picks the smallest, it gets the **wrapper** directly — clean, structured, no skill noise.

## Applies to other cron dirs?

Same pattern likely holds for:
- `cef7e567` (PM task-polling) — wrappers ~5-15 KB real responses, dumps ~80-115 KB skill regurgitations. The 82225-byte measurement in the SKILL.md drift section refers to the dump.
- `0cbfcf7b` (PM daily-evening-report) — same bimodal pattern expected.

Pattern probably does NOT hold for:
- `74ebd0a0` (config-backup) — verified separately: outputs are consistently 1-2 KB silent markers, no large dumps (the config-backup prompt does not load the full SKILL.md).
- `99674315` (memory-cleanup) — same as config-backup.

## Cross-references

- SKILL.md §"Pitfall: Cron LLM drift into skill-content regurgitation" — drift detection rules, size thresholds (now stale; re-baseline monthly)
- SKILL.md §5 #16 — N-extraction recipe (canonical title regex + fallback chain)
- SKILL.md §5 #17 — `urllib.request` direct GitHub API call (bypasses `gh` CLI / redactor)
- `references/cron-output-dir-picker.md` — picking the right output dir (different problem: picking among 5+ UUID-named dirs in `cron/output/`)