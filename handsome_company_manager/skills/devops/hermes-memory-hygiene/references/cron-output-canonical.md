# Cron output canonical structure (memory-cleanup cron fire)

This reference documents the **clean** output structure for the
`oneplusn-PM-memory-cleanup` cron fire (and equivalent per-profile memory-cleanup
crons on other profiles). Use it as the authoring target for a new run **and** as
the drift discriminator when verifying a past run.

## File location & naming

- Output path: `<profile_home>/cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md`
- Filename uses **CST**, not UTC. mtime is always epoch-UTC.
- Example: `2026-08-06_21-07-41.md` was written at 21:07 CST = 13:07 UTC.
- See oneplusn skill §5 #20 ("`datetime.utcnow()` returns local time, NOT UTC,
  on Windows") — same CST-vs-UTC convention applies here as to daily-evening.

## Canonical structure (~5–10KB target)

```
# <Profile> 记忆清理报告 #N(<CST-datetime> CST = <UTC-datetime> UTC)

## 摘要
1–3 lines: cleanup verdict + artifact state + next-step pointer.

## Current MEMORY state
- File-by-file char-count table (file | chars | budget | % | mtime)
- Dated entries table (date | age | STAYS / ARCHIVE / DEEP-ARCHIVE)

## 30-day archive execution result
- Cutoff date (= now − 30d)
- Step-by-step: scanned files, computed cutoffs, what moved (or "no-op")
- For "no-op" cases, brief WHY (e.g., "all entries within 30-day window")
- Reference to MEMORY_ARCHIVE.md header + housekeeping entry that were updated

## Hindsight reflect() attempt (only when cron-prompt-override rule applies)
- Pre-flight: venv python path, import test exit code, port 9807 status
- Daemon run: exit code, elapsed seconds, daemon signal
- Time-scoped current-run signature (post-start-time log lines, not historical)
- For long-skip runs: re-ranked (a/b/c) remediation table with "Diagnostic
  implication" sub-bullet naming any new log line and the gate it implies

## Action items (boss side, non-blocking)
- 1–3 items, each ≤1 line

## Meta
- Cron name + id + schedule + fire datetime
- Profile name
- Next-cron cadence pointer
```

Skeletal total: **5–10KB**. Anything substantially larger is a drift signal.

## Drift discriminator

A *drifted* cron output (LLM regurgitated loaded skill content rather than executing):

- **Size**: 60–100KB (vs the 5–10KB canonical target)
- **Skill-heading matches**: ≥2 of:
  `["## Pitfall", "## Operational", "## Hard Constraints",
    "## Known Fixes", "## Per-Agent", "## PM Mode"]`
- **Last-line check**: tail ends with verbatim SKILL.md text instead of a clean
  report boundary (e.g., end of `## Meta` block + `---` separator).
- **`last_status` is uninformative**: cron fires, LLM responds, `last_status=ok` —
  drift hides behind normal-looking cron metrics. Always check the response content.

A *clean* cron output:

- **Size**: 5–10KB
- **Skill-heading matches**: 0 (report is original prose, not skill regurgitation)
- **Last-line check**: ends with a clear report boundary or cron meta block.

### Detection snippet (paste into `execute_code`)

```python
from pathlib import Path

out_dir = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/<profile>/cron/output/<job_id>/")
SKILL_HEADINGS = ["## Pitfall", "## Operational", "## Hard Constraints",
                  "## Known Fixes", "## Per-Agent", "## PM Mode"]
files = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
for f in files[:3]:
    txt = f.read_text(encoding="utf-8", errors="replace")
    is_drift = len(txt) > 50_000 and sum(1 for h in SKILL_HEADINGS if h in txt) >= 2
    print(f"{f.name}  size={len(txt):>6}  drift={is_drift}")
```

A clean run shows `drift=False`; a drifted run shows `drift=True` and the same
file is 60–100KB instead of 5–10KB.

## Why a clean run produces a small file

The memory-cleanup cron touches exactly five things:

1. Inspect `MEMORY.md` + `USER.md` (each ≤2.2KB).
2. Inspect `MEMORY_ARCHIVE.md` to find prior housekeeping entries.
3. Call Hindsight `reflect()` at most once (60–180s daemon cost — does NOT add to
   the cron output size; only to wall-clock duration).
4. Append one housekeeping entry (~4KB) to `MEMORY_ARCHIVE.md`.
5. Write one cron-output file (~5KB).

Total expected artifact size: ~10KB plus a one-entry extension of the archive.
A 60–100KB file means the LLM reproduced the loaded oneplusn skill body instead
of executing the workflow — common failure mode when skill context dominates
the prompt window. See oneplusn SKILL.md §"Pitfall: Cron LLM drift into
skill-content regurgitation" for the cross-cron version of this diagnosis.

## Common authoring mistakes that push output into drift territory

- **Quoting SKILL.md content into the cron output instead of citing it.** When
  describing what the cron does, name the workflow step (e.g., "ran
  `verify_housekeeping_structure.py <profile>`") — do NOT inline the section
  prose.
- **Adding long troubleshooting guides to the cron output.** The cron output is
  a *status report*, not a postmortem. If something unusual happened, name it
  in 1–2 lines and reference the `MEMORY_ARCHIVE.md` housekeeping entry for the
  full detail.
- **Re-running the diagnostic recipe inline.** State the *result* of
  pre-flight checks, not the Python code that ran them.

If your draft cron output exceeds 15KB, you have almost certainly drifted.
Re-read the SKILL.md body to ground yourself, then re-author with the canonical
structure above.

## Cross-references

- **oneplusn SKILL.md** §"Pitfall: Cron LLM drift into skill-content regurgitation"
  — same drift discriminator applied across all LLM-driven PM crons (bi-hourly,
  daily-evening, task-polling, config-backup, memory-cleanup).
- **oneplusn SKILL.md** §5 #20 — CST-vs-UTC filename + mtime convention.
- **SKILL.md §"Hindsight reflect"`" in this skill** — full reflect() recipe and
  the cron-prompt-override rule that determines whether reflect() even runs.
- **SKILL.md §"Verification"`"** — the post-run checklist (size/heading check
  is the new item, integrated into the existing checklist as the "Cron output
  sanity check" line).
