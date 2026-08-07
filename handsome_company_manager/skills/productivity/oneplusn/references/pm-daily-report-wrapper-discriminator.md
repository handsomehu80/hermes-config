---
name: pm-daily-report-wrapper-discriminator
description: When PM daily report cron output dir mixes real reports (5–10KB) with wrapper dumps (50–115KB), classify by size + §5 numeric content before treating a file as the §5 cross-day baseline. Walk back through mtime-sorted files until a real report is found, then label the report header "vs <last-real-date> 最近真基线 (<today-date> wrapper 漂移无对比值)" instead of pretending "yesterday".
version: 1.0.0
---

# PM Daily Report Wrapper-Discriminator + Cross-Day Baseline Fallback

## Why This Exists

The `pm-daily-evening-report` cron (`0cbfcf7b360e` in the default deployment) output dir accumulates a mix of two file shapes:

- **Real reports**: 5–10KB, all 9 sections (`## 0.`–`## 8.`) populated, §5 跨日趋势 rows have actual numbers (e.g. `| 2 / 13 |`)
- **Wrapper dumps**: 50–115KB, §0 = literal `[≤ 100 字]`, §5 = literal `...` placeholders, body is a regurgitation of the loaded `oneplusn` SKILL.md verbatim

When `sorted(daily.glob("*.md"), key=mtime, reverse=True)[0]` is a wrapper, blindly using it as the "yesterday" baseline for §5 cross-day Δ produces fabricated Δ rows (`... / ... / ...`) that the boss will read and trust. Verified on the 2026-08-07 PM daily fire: 27 files in `0cbfcf7b360e/`, only 2 are real reports (`2026-08-04_15-05-30.md` 6420B + `2026-08-05_15-01-13.md` 5253B); the other 25 are wrappers in the 50K–115K range. The mtime-newest file (`2026-08-06_15-05-15.md` 111461B) is a wrapper — using it as the §5 baseline would have produced `| ... | ... | ... |` rows and zero useful Δ info.

## Three-Layer Discriminator

Run all three for a confidence-checked classification. The third (regex on §5 row content) is the authoritative one.

### Layer 1 — File size (cheap early-out)

```python
size = f.stat().st_size
is_likely_wrapper = size > 50_000
is_likely_real = size < 15_000
```

Note: this is a heuristic, not a definition. A real report can occasionally be 20–30KB if it includes long PR detail tables; a wrapper can occasionally be 30–40KB on a smaller load. Use size to filter the candidate set, not to make the final call.

### Layer 2 — §0 placeholder check (cheapest precise test)

```python
import re
m0 = re.search(r'##\s*0\.\s*今日一句话总结\s*\n+([\s\S]+?)(?=\n##\s)', txt)
if m0 and m0.group(1).strip() == '[≤ 100 字]':
    # Wrapper — the LLM hit the template and never replaced the placeholder
    is_wrapper = True
```

This is the most reliable single signal because the wrapper's §0 is almost always the literal `[≤ 100 字]` placeholder from the template — real reports never leave it untouched (the boss would notice).

### Layer 3 — §5 numeric-row regex (authoritative)

```python
m5 = re.search(r'##\s*5\.\s*跨日趋势[\s\S]+?(?=\n##\s*\d|\Z)', txt)
is_real = bool(m5 and re.search(r'\|\s*\d+\s*\|', m5.group(0)))
```

A real §5 row looks like `| Open Issue / Closed Issue | 2 / 13 | 2 / 13 | 0 / 0 |` — has actual numbers. A wrapper §5 has only `| ... | ... | ... |` — never contains standalone digits in cells. If `re.search(r"\|\s*\d+\s*\|", m5.group(0))` returns None, the file is a wrapper, full stop.

## Full Classification Recipe

```python
import re
from pathlib import Path
import datetime

daily = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/0cbfcf7b360e")
now_utc = datetime.datetime.now(datetime.timezone.utc)

def classify(f):
    txt = f.read_text(encoding="utf-8", errors="replace")
    size = len(txt)
    m0 = re.search(r'##\s*0\.\s*今日一句话总结\s*\n+([\s\S]+?)(?=\n##\s)', txt)
    m5 = re.search(r'##\s*5\.\s*跨日趋势[\s\S]+?(?=\n##\s*\d|\Z)', txt)
    placeholder_0 = bool(m0 and m0.group(1).strip() == '[≤ 100 字]')
    has_numeric_5 = bool(m5 and re.search(r'\|\s*\d+\s*\|', m5.group(0)))
    return {
        "size": size,
        "placeholder_0": placeholder_0,
        "has_numeric_5": has_numeric_5,
        "is_real": (size < 50_000) and (not placeholder_0) and has_numeric_5,
        "is_wrapper": (size > 50_000) or placeholder_0 or not has_numeric_5,
    }

files = sorted(daily.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
results = [(f.name, classify(f)) for f in files[:10]]
for name, r in results:
    print(f"{name:30s} size={r['size']:>6}  p0={r['placeholder_0']!s:5s}  n5={r['has_numeric_5']!s:5s}  real={r['is_real']!s:5s}  wrap={r['is_wrapper']}")

# Find the most recent real report for §5 baseline
last_real = next(f for f in files if classify(f)["is_real"])
print(f"\n[LAST REAL] {last_real.name}  mtime={datetime.datetime.fromtimestamp(last_real.stat().st_mtime, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
```

## Cross-Day Δ Baseline Fallback

When §5 wants to compare "yesterday" vs "today":

1. Get `today = sorted(daily.glob('*.md'), key=mtime, reverse=True)[0]`
2. Classify `today` — if `is_wrapper`, find the **previous** real report (skip back through `files[1:]` until `is_real`).
3. Label the §5 row in the new report header explicitly. Do NOT write "vs 昨日" when the prior file is a wrapper — boss will trust it. Use instead:
   - `vs 8-05 最近真基线(8-06 wrapper 漂移无对比值)`
   - `vs 8-04 唯一真基线(8-05/8-06 双 wrapper 漂移)`
4. If the wrapper streak is ≥3 days, the §5 table itself should add a meta-row:
   ```
   | 漂移期日报数(自 <first-real-date>) | 0 | <count> | +<count> |
   ```
   This makes the drift visible to the boss without you having to explain it in prose.

## §0 Sentence-Template Patterns That Identify Wrappers

Beyond the literal `[≤ 100 字]` placeholder, wrappers can be classified by their §0 shape — they tend to repeat template phrases like:

- "24h 0 业务动作:0 commits(全为 dev+reviewer auto config-backup);..." (then trail off with skill-content regurgitation)
- A real §0 has a clear "结论" verb structure: "**0 业务动作; 死锁 N d; 老板真空 ≥M 日; 决策点 X 悬空**" — terse, period-separated, ends cleanly.

If §0 is >300 chars AND the first 100 chars don't end in a period or semicolon, suspect a wrapper even if size is borderline. Add a fourth discriminator layer if needed: `is_likely_wrapper = (len(m0.group(1)) > 300 and re.search(r'[。;！？\n]\s*\n', m0.group(1)))`.

## Cleanup Hygiene After Writing

When staging temp JSON snapshots in the daily output dir during a cron fire (`_today_snapshot.json`, `_prs_detail.json`, `_prs_events.json`, etc.), `unlink()` them after the final report is written. Otherwise:

- Next cron fire's `glob("*.md")` will count them as report files (size is tiny but they're not real reports)
- File-sort by mtime gets polluted (the JSON files have similar mtime to the real report)
- `size` heuristic in Layer 1 misclassifies (a 200B JSON is <15K so it's "real" by size alone)

```python
from pathlib import Path
daily = Path("C:/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_manager/cron/output/0cbfcf7b360e")
for f in daily.glob("_*.json"):
    f.unlink()
    print(f"[CLEANUP] removed {f.name}")
```

## What To Do If All Recent Reports Are Wrappers (3+ Day Drift)

This is a real risk on a sustained drift: if the PM task-polling cron itself has drifted for 3+ days, the daily cron will drift too (same root cause — LLM dumps skill content instead of executing the prompt). Detection + recovery:

1. **Check task-polling health first**: `ls <profile_home>/cron/output/<task-polling-id>/` — if those files are all 60–100KB and contain skill content, the underlying drift is in task-polling, not daily. Fix that first.
2. **Manual recovery via `execute_code`**: bypass the cron LLM entirely. The PM daily report recipe is small enough (~6KB of structured text) that you can author it directly from `urllib.request` API calls + manual §0/§5 prose. See `references/manual-cron-recovery.md` for the pattern.
3. **Don't keep re-running the cron** — the drift is structural (loaded SKILL.md dominates the LLM context); one more fire will produce one more wrapper, not a real report.
4. **Patch the cron prompt**: see the `oneplusn` SKILL.md Operational Maintenance → "Pitfall: Cron LLM drift into skill-content regurgitation" section for the 4 fix paths (rewrite prompt / reduce skill context / split bash+LLM / bypass cron entirely).

## Canonical Discrimination Output (Verified 2026-08-07)

```
2026-08-07_15-00-42.md  size=6084    p0=False n5=True   real=True   wrap=False   ← TODAY (newly written)
2026-08-06_15-05-15.md  size=111461  p0=True  n5=False  real=False  wrap=True
2026-08-05_15-13-31.md  size=112327  p0=True  n5=False  real=False  wrap=True
2026-08-05_15-01-13.md  size=5253    p0=False n5=True   real=True   wrap=False   ← LAST REAL (used as §5 baseline)
2026-08-04_15-05-49.md  size=114028  p0=True  n5=False  real=False  wrap=True
2026-08-04_15-05-30.md  size=6420    p0=False n5=True   real=True   wrap=False
```

→ §5 baseline for the 8-07 daily was correctly set to **8-05 最近真基线** (with 8-06 noted as wrapper 漂移无对比值), not "昨日 8-06".

## See Also

- `oneplusn` SKILL.md → "Operational Maintenance" → "Daily" — the operational context for the daily cron
- `oneplusn` SKILL.md → "Pitfall: Cron LLM drift into skill-content regurgitation" — the upstream cause of wrapper dumps
- `references/pm-daily-evening-report.md` §5 #17 — daily report timezone + cross-day window rationale (the wrapper-drift issue is a separate but related pitfall)
- `references/manual-cron-recovery.md` — recovery recipe when cron LLM has drifted for many days
