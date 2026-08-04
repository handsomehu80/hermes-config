# Bi-hourly Cron Output: Two Files Per Fire (Wrapper + Report)

**Learned 2026-08-04, PM #208.** Each `pm-bihourly-status-report` (and every other LLM-driven cron in the 1+N system) writes **TWO files** into `<profile_home>/cron/output/<job_id>/` within ~20 seconds of each other:

| File | Size | What it is | Newer? |
|---|---|---|---|
| **Wrapper** | ~50-110 KB | The cron wrapper writes the prompt template first — it inlines the full skill content + the **previous** report body as embedded prompt context for the next LLM turn | Yes (by ~20s) |
| **Report body** | ~3-5 KB | The actual LLM response — opens with the canonical `# 📊 PM 双小时状态报告 #N(...)` title + §0-§7 sections | No (older by ~20s) |

## Why This Matters for N-Extraction

The skill's N-extraction recipe (§16) tells you to read "the latest bi-hourly file" and run the regex. **Both files are valid sources**:

- The **wrapper** contains the regex-matchable title inside its embedded prompt section (because the wrapper embeds the previous report body as part of the next-run prompt).
- The **report file** has the title as its first `#` heading.

If you `sorted(bihourly.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[0]`, you get the **wrapper** (newer). The regex still works on it because the report body is embedded in the wrapper's prompt template.

## What NOT To Do

- **Do NOT filter by size** before running the regex (e.g. `if size > 10000: skip` — that would skip the wrapper and miss the N).
- **Do NOT try to find the "real" report file separately** — there's nothing to find; both files are valid.
- **Do NOT classify the wrapper as drift** — its large size is the prompt context, not LLM regurgitation. The report INSIDE the wrapper is real (canonical title + §0-§7 sections). The "drift" discriminator (§"Cron LLM drift into skill-content regurgitation") only fires when the LATEST output by mtime is the wrapper AND the wrapper's final answer (after `## Response`) is something other than `[SILENT]` or a real report.

## When to Prefer the Smaller File

Use the **smaller report file** (size < 10 KB) specifically when:

1. **Cross-referencing §7 insights** between reports (read both reports' §7, not the wrapper's embedded copies).
2. **Copying the §5 PM-direct-action one-liner verbatim** into the new report — the report file is the authoritative source; the wrapper's embedded copy might be from a slightly older state.
3. **Verifying canonical structure** (`# 📊 PM 双小时状态报告 #N(...)` title + `## 0`–`## 6` sections) — the report file shows this directly; the wrapper only embeds it as text.

For everything else (N-extraction, smoke test that the cron fired, counting files in the last N hours), the latest by mtime is fine — wrapper or report, both work.

## Canonical Recipe: Pick the Right File by Purpose

```python
from pathlib import Path
bihourly = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/<pm>/cron/output/<job_id>/")
all_files = sorted(bihourly.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)

# Latest by mtime — works for N-extraction (wrapper or report)
latest = all_files[0]

# Smaller report body — for cross-reference / §7 / §5 copy
report_bodies = [f for f in all_files if f.stat().st_size < 10_000]
latest_report = report_bodies[0] if report_bodies else latest
```

## Why Two Files Exist (Cron Architecture)

The cron wrapper writes the prompt file first (so it can be read by the LLM runner as input), then invokes the LLM, which writes its response to a separate file. Both files persist in the output dir for audit. The wrapper's prompt template embeds the **previous** report body so the next LLM turn has continuity context — that's why the wrapper is so large and why it contains the regex-matchable N.

This is by design, not a bug. Don't try to "fix" it by deleting the wrapper after the cron fires — the wrapper is the audit trail showing what prompt the LLM saw.
