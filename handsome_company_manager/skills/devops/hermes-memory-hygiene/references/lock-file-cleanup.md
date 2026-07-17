# Lock file cleanup & pre-flight hygiene

The 1+N memory hygiene workflow touches three distinct `.lock` file families. They look similar on disk (often 0-byte siblings) but mean different things and need different cleanup policies. Conflating them has caused silent zombie states in past runs.

## The three lock families

| Lock path | Created by | Means | Cleanup policy |
|---|---|---|---|
| `~/.hermes/profiles/<profile>/memories/MEMORY.md.lock` | `memory()` tool | Markdown write lock for MEMORY.md | Safe to remove if 0 bytes AND mtime > 1 day old (no active writer) |
| `~/.hermes/profiles/<profile>/memories/USER.md.lock` | `memory()` tool | Markdown write lock for USER.md | Same as above |
| `~/.hindsight/profiles/<profile>.lock` | Hindsight daemon | Daemon startup lock; blocks `HindsightEmbedded()` from starting a second instance | Remove BEFORE calling `HindsightEmbedded()` — daemon refuses to start if lock exists from a prior failed attempt |

## Detection recipe

```python
from pathlib import Path
from datetime import datetime

profile = "<profile>"

# 1. Markdown write locks — clean only the obviously-stale ones
mem_dir = Path(f"C:/Users/Administrator/AppData/Local/hermes/profiles/{profile}/memories")
for lock in mem_dir.glob("*.lock"):
    st = lock.stat()
    age_days = (datetime.now() - datetime.fromtimestamp(st.st_mtime)).days
    if st.st_size == 0 and age_days >= 1:
        try:
            lock.unlink()
            print(f"[cleaned] {lock.name} ({age_days}d old, {st.st_size}B)")
        except OSError as e:
            print(f"[FAIL] {lock.name}: {e}")
    else:
        print(f"[keep]   {lock.name} ({age_days}d old, {st.st_size}B)")

# 2. Hindsight daemon locks — always remove before HindsightEmbedded()
import glob
for lock in glob.glob("C:/Users/Administrator/.hindsight/profiles/*.lock"):
    try:
        os.remove(lock)
        print(f"[cleaned] hindsight daemon lock {lock}")
    except OSError as e:
        print(f"[FAIL] {lock}: {e}")
```

## Why both are 0 bytes

A "real" lock file would have content (PID, hostname, timestamp). Both lock families use 0-byte files because:
- The markdown `memory()` tool just `O_CREAT | O_EXCL` to atomically create an empty lock — process presence is implied by the lock existing on a POSIX/NTFS filesystem
- Hindsight uses Python's `fcntl.flock(LOCK_EX | LOCK_NB)` on a 0-byte file — flock state lives in the kernel, not the file

If you see a non-zero-size lock file in either family, that's a different problem (interrupted write, manual tampering) — investigate before deleting.

## Housekeeping structure verification

After every `MEMORY_ARCHIVE.md` patch edit, check that the housekeeping bullet list has no nested entries:

```python
from pathlib import Path
text = Path("~/.hermes/profiles/<profile>/memories/MEMORY_ARCHIVE.md").expanduser().read_text()
in_housekeeping = False
date_indents = []
for line in text.splitlines():
    if line.startswith("## Archive housekeeping"):
        in_housekeeping = True
        continue
    if not in_housekeeping:
        continue
    if line.startswith("## ") and not line.startswith("## Archive"):
        break  # next section
    if line.lstrip().startswith("- 20"):  # YYYY-MM-DD entry
        leading_spaces = len(line) - len(line.lstrip())
        date_indents.append((line.strip(), leading_spaces))

unique_indents = set(ind for _, ind in date_indents)
if len(unique_indents) > 1:
    print(f"[BUG] nested housekeeping entries: indents = {sorted(unique_indents)}")
    for entry, ind in date_indents:
        print(f"  {ind*' '}{entry[:60]}")
else:
    print(f"[OK] all {len(date_indents)} housekeeping entries at one indent level")
```

If nested entries are detected, rewrite the entire `## Archive housekeeping` block at once with all entries at the same level — incremental patches will inherit the bug.

## Gateway liveness vs Hindsight skip (don't conflate)

Before declaring a Hindsight reflect() skip, do NOT assume the gateway is alive. A "skip" with a stale gateway is a different problem than a "skip" with a live gateway:

| Gateway log mtime | Implication | Housekeeping wording |
|---|---|---|
| < 60 min ago | Gateway live, Hindsight-only issue | "Hindsight reflect skipped; Gateway live (log mtime X)" |
| 1h - 24h ago | Gateway possibly idle but alive; cron ticker not firing | "Hindsight reflect skipped; Gateway log last activity X — cron may not be firing" |
| > 24h ago | Gateway down — separate problem | "Hindsight reflect skipped; **Gateway log stale (>24h) — investigate gateway separately**" |

The 60-second cron ticker in `gateway.log` (`Cron ticker started (interval=60s)`) is the canonical liveness signal. Look for this line in the LAST 24h of log output before attributing any cron-side anomaly to "Hindsight is broken".