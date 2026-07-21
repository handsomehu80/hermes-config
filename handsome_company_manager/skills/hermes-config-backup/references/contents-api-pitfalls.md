# Contents API & Git Data API Pitfalls (2026-07-14)

The SKILL.md's "Contents API vs Git Data API" choice matrix and "Known API failure modes" list are necessary but not sufficient. Three real-world issues hit during a 158-file backup on 2026-07-14 that aren't covered anywhere else in the skill. Document them here so the next push doesn't waste 40 minutes rediscovering them.

## Pitfall 1: Git Data API tree creation fails at 60+ entries even with the chunked fallback

**What happens:**

- All 172 blobs create successfully (~3s each, ~9 min total).
- `POST /git/trees` with `base_tree=<current>` + 172 entries → HTTP 422 `GitRPC::BadObjectState` (the documented failure).
- Script's chunked fallback (chunks of 30) runs:
  - Chunk 1 (entries 0-29) → OK
  - Chunk 2 (entries 30-59) → OK
  - Chunk 3 (entries 60-89) → HTTP 422 `{"message":"tree.path contains a malformed path component"}`
- The path in chunk 3 is **known-clean** (no control chars, no `\\`, no `//`, all ASCII). The error is wrong: GitHub's tree-creation endpoint is internally inconsistent on the third chained `base_tree` call for unknown reasons.
- Manual isolation confirms every path in chunk 3 creates a valid single-entry tree. The failure is NOT in the path.

**Reproduction:**

1. Stage 60+ files, get the current `base_tree` SHA via `GET /repos/{owner}/{repo}/git/commits/{ref}`.
2. Call `POST /repos/{owner}/{repo}/git/trees` with `{"base_tree": <base>, "tree": <60 entries>}` → 422.
3. Call with `{"base_tree": <base>, "tree": <1 entry>}` (any of the 60) → 200.
4. Repeat for each entry in the 60-entry batch — all succeed individually.
5. Call `POST /repos/{owner}/{repo}/git/trees` with `{"base_tree": <base>, "tree": <30 entries>}` → 422.

**Workaround:** give up on the single-commit push and fall back to Contents API. The "Contents API vs Git Data API" choice matrix's ">150 files → Git Data API" recommendation is wrong on Windows — **use Contents API for any batch size when on the API-fallback path**. Yes, it's N commits and noisy history. Yes, that's still better than a stuck tree.

**Skill change:** matrix should say "any size → Contents API on the API-fallback path" with the chunked-tree failure as the explicit reason.

## Pitfall 2: Contents API PUT race on parallel siblings in a new directory

**What happens:**

When you `PUT /repos/{owner}/{repo}/contents/{path}` and the parent directory doesn't exist yet, GitHub auto-creates it. The parent is a tree object, and a tree's SHA changes with every successful PUT inside it.

If two workers both PUT files into the same NEW directory in parallel:
- Worker A: `PUT /contents/newdir/file1` — auto-creates `newdir` (SHA=X), PUT succeeds.
- Worker B (running concurrently): `PUT /contents/newdir/file2` — tries to update `newdir` (now at SHA=X), but B's last-seen SHA was the pre-create value (Y). GitHub returns 409 `{"message":"is at X but expected Y"}`.
- One of them wins. The other fails.

Sequential processing of the same 30 files into the same new dir: all 30 succeed. Parallel processing of the same 30: ~60% success rate (varies by timing).

**Reproduction:**

1. Pick 30 files in the same new directory.
2. `ThreadPoolExecutor(max_workers=4).map(push, files)` — see ~12 failures, all 409 with "is at X but expected Y".
3. Loop sequentially over the same 30 files — all 30 succeed.

**Fix: group by parent dir, parallelize across dirs.**

```python
from collections import defaultdict
by_dir = defaultdict(list)
for rel in changes:
    parent = str(Path(rel).parent)
    by_dir[parent].append(rel)

with ThreadPoolExecutor(max_workers=N) as ex:
    futures = {ex.submit(push_dir_seq, d, fs): d for d, fs in by_dir.items()}
    for fut in as_completed(futures):
        fut.result()  # each dir processed sequentially
```

The `push_via_contents_parallel.py` script in this skill's `scripts/` directory implements this. Verified at 4 workers / 5 dirs / 158 files / ~3 min on 2026-07-14.

**Why 4 workers is the right default:** the rate-limit ceiling is 5000/hr authenticated = 1.4 req/sec. 4 workers × ~0.65 f/s = 2.6 f/s, ~25% of the budget. Don't go above 8 workers or you'll start hitting 429s.

## Pitfall 3: Local `skills/<x>/scripts/.git/` and git submodules on the remote

Two related issues, both of which cause a successful-looking local walk to fail in the PUT:

### 3a. `.git/` directories inside custom skills

A custom skill may have its own internal git repo (e.g. `skills/productivity/oneplusn/scripts/.git/`). The default exclusion list does NOT include `.git/` (only top-level profile `.git` would be — but this is one level deeper).

Symptom: the local walk collects 32+ files under `skills/.../scripts/.git/objects/XX/...` and tries to back them all up. The push then wastes ~3 minutes on these files (they're never going to be useful in the backup) and pollutes the diff with noise.

**Fix:** add `skills/.git/`, `skills/*/scripts/.git/`, and any other nested `.git` paths to the exclusion list. Better: walk with a hard exclusion of ANY `.git` directory at any depth:

```python
EXCLUDE_DIRS_AT_ANY_DEPTH = {'.git'}
# In the os.walk loop:
dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS_AT_ANY_DEPTH]
```

### 3b. Git submodules on the remote

The remote `hermes-config` repo may have a `handsome_company_manager/skills/<name>/scripts/` entry whose tree object is `type: "commit"` and `mode: "160000"` — a git submodule. Locally, the corresponding path is a regular directory. When the Contents API tries to PUT a file at that path, GitHub returns 409 `{"message":"Sorry, a file exists where you're trying to create a directory"}` because the path is occupied by a submodule, not a tree.

**Detection before the push:**

```python
import subprocess
tree = json.loads(subprocess.check_output(
    ['gh', 'api', 'repos/<owner>/<repo>/git/trees/main?recursive=1'], text=True))
submodules = {e['path'] for e in tree['tree'] if e.get('type') == 'commit'}
# Any local file under a submodule path cannot be pushed via Contents API.
# Skip them from the diff.
for rel in changes:
    if any(rel.startswith(s + '/') or rel == s for s in submodules):
        changes.remove(rel)
```

**Decision: don't try to overwrite a submodule.** Submodules have their own versioning. The local content under a submodule path is owned by the submodule's own repo, not by hermes-config. Backups should respect that boundary — the submodule is a deliberate pointer, not a misconfiguration. (If the boss wants to flatten it, that's a separate operation requiring `git rm --cached` + a force-push, not part of a normal backup.)

**Historical note:** the previous 2026-07-13 PM backup committed `skills/productivity/oneplusn/scripts/` as a SUBMODULE in the remote, even though the local profile has it as a regular dir. This means subsequent backups have been silently failing for that path (409 on every attempt) — the script's failure list might be hiding it. Always check the remote tree's `type` field, not just the file count, when reconciling.

## Other small things learned the same day

- **Cron output `*.md` files** (`cron/output/<job_id>/<timestamp>.md`) can be in the hundreds on a busy profile. They're chat history of cron LLM runs. Backing them up is fine but they grow fast. Consider excluding them for production deployments where space matters — they're regenerable.
- **`auth.json` is sensitive** (contains `MINIMAX_CN_API_KEY` reference with `source: env:...` and other credential-pool metadata). The 2026-07-13 backup committed it. If the current request explicitly requires excluding sensitive files, or the target repo is public, remove the legacy remote `auth.json` in the same backup run via the Contents API and add `auth.json` to the profile `.gitignore`; otherwise do not silently rewrite history—report the legacy file and propose a separate cleanup.
- **`feishu_seen_message_ids.json`** and `gateway_state.json` are runtime state and should be excluded, but the 2026-07-13 backup included both. If the remote has them, leave them alone for now; future cleanups can remove.
- **Per-file commit messages are noisy but they're the only safe Contents API pattern** when the push script can't dedup by SHA. The previous curator's pattern is `backup: <path> (cron, <date>)` — match that.
- **`Path` on Windows returns WindowsPath with backslashes** in `str()`. Always use `Path.as_posix()` or `.replace("\\", "/")` before comparing or hashing. This bit the parallel script's `str(Path(rel).parent)` log messages (display only, no functional impact).
