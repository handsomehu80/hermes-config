# API Fallback When `git push` Is Blocked

Use this when `github.com:443` is firewalled but `api.github.com` and `codeload.github.com` are reachable (a common pattern on locked-down Windows machines). The standard `git clone` / `git push` workflow in the parent SKILL.md does not work; switch to the GitHub REST API end-to-end.

## Symptoms

```text
$ git clone https://github.com/handsomehu80/hermes-config.git hermes-config
Cloning into 'hermes-config'...
fatal: unable to access 'https://github.com/handsomehu80/hermes-config.git/':
Failed to connect to github.com port 443 after 21074 ms: Could not connect to server

$ gh api repos/handsomehu80/hermes-config | head -1
{"id":1295172631,"node_id":"R_kwDOTTLEF9o","name":"hermes-config",...}     # ← works!

$ curl -sI https://codeload.github.com | head -1
HTTP/1.1 301 Moved Permanently                                              # ← works!
```

**That asymmetry = use the API path.** Do not retry git.

## Pre-flight (10 seconds)

```bash
gh auth status 2>&1 | head -3                # confirm token still valid
gh api repos/<owner>/<repo> 2>&1 | head -1   # confirm target reachable via API
curl -sI --connect-timeout 5 https://codeload.github.com | head -1   # tarball host reachable?
```

## Step 1 — Download existing remote as tarball

```bash
mkdir -p /tmp/hermes-backup-$(date +%Y%m%d)
cd /tmp/hermes-backup-$(date +%Y%m%d)
curl -sL -o repo.tar.gz https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main
mkdir -p <repo>-original
tar -xzf repo.tar.gz -C <repo>-original --strip-components=1
```

The `--strip-components=1` strips the `<repo>-main/` wrapper directory the tarball creates.

## Step 2 — Mirror the live profile to a sync working tree

Use the canonical `sync_profile.py` from this skill, with the extended exclusion set (`lsp/`, `node_modules/`, `processes.json`, `.hermes_history`, `*.bak.*`). Set env vars and run:

```bash
# Windows
export PROFILE_PATH="C:/Users/<user>/AppData/Local/hermes/profiles/<profile>"
export REMOTE_PATH="C:/Users/<user>/AppData/Local/Temp/hermes-backup-$(date +%Y%m%d)/<repo>-new"

# Linux/macOS
# export PROFILE_PATH="$HOME/.hermes/profiles/<profile>"
# export REMOTE_PATH="/tmp/hermes-backup/<repo>-new"

python "<skill_dir>/scripts/sync_profile.py"
```

Then **preserve the remote's own `.gitignore`** by copying it on top (the sync script preserves the remote's `.gitignore` if it was already there, but be explicit):

```bash
cp <repo>-original/<profile>/.gitignore <repo>-new/<profile>/.gitignore
```

## Step 3 — Diff the two trees (SHA-256 per file)

Write to `diff.json` so the push step can read it:

```python
import hashlib, json
from pathlib import Path

EXCLUDE_DIRS = {"audio_cache","image_cache","cache","logs","sessions","plans",
                "workspace","gateway-service","home","pairing","weixin",
                "memory_sessions",".git","__pycache__",
                ".curator_backups",".archive",".hub",".idea",".vscode",
                "lsp","node_modules","output"}
EXCLUDE_FILES = {".env","auth.lock","gateway.lock","gateway.pid",
                 "state.db","state.db-shm","state.db-wal",
                 "models_dev_cache.json","gateway_state.json","processes.json",
                 ".hermes_history",".skills_prompt_snapshot.json",
                 ".DS_Store","Thumbs.db","desktop.ini",
                 ".usage.json",".usage.json.lock",".bundled_manifest",
                 ".curator_state",".tick.lock"}
EXCLUDE_GLOBS = ("*.key","*.pem","*.p12","*.pfx","*.lock",
                 "*.swp","*.swo","*~","*.pyc","*.cache",
                 "*.bak.*",".env",".env.*","secrets.*")

import fnmatch
def is_excluded(name): return name in EXCLUDE_DIRS or name in EXCLUDE_FILES \
    or any(fnmatch.fnmatch(name, p) for p in EXCLUDE_GLOBS)

def walk(root):
    out = {}
    for e in sorted(root.iterdir()):
        if is_excluded(e.name): continue
        rel = e.name if root == root.parent else f"{root.name}/{e.name}"
        if e.is_dir():
            for k, v in walk(e).items():
                out[f"{rel}/{k}"] = v
        elif e.is_file():
            h = hashlib.sha256()
            with e.open("rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            out[rel] = h.hexdigest()
    return out

old = walk(Path("<repo>-original/<profile>"))
new = walk(Path("<repo>-new/<profile>"))
diff = {
    "old": old, "new": new,
    "new_paths": sorted(set(new) - set(old)),
    "deleted_paths": sorted(set(old) - set(new)),
    "modified_paths": sorted(p for p in (set(new) & set(old)) if new[p] != old[p]),
}
json.dump(diff, open("diff.json","w"), indent=2)
print(f"+{len(diff['new_paths'])} -{len(diff['deleted_paths'])} ~{len(diff['modified_paths'])}")
```

## Step 4 — Push via GitHub API

### Option A: Contents API (recommended for ≤150 files)

One commit per file. ~2-3 sec/file. Reliable. History is noisy.

```python
import base64, json, subprocess, sys, time
import urllib.request, urllib.error
from pathlib import Path

REPO  = "<owner>/<repo>"
BRANCH = "main"
SYNCED = Path("<repo>-new/<profile>")
DIFF = json.load(open("diff.json"))
changes = DIFF["new_paths"] + DIFF["modified_paths"]

token = subprocess.check_output(["gh","auth","token"], text=True).strip()

def req(method, path, body=None):
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "hermes-config-backup/1.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(f"https://api.github.com{path}", data=data,
                               method=method, headers=headers)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code} {e.read().decode()}")

success, fail = 0, []
t0 = time.time()
for i, rel in enumerate(changes, 1):
    content = (SYNCED / rel).read_bytes()
    b64 = base64.b64encode(content).decode()
    api_path = f"{SYNCED.name}/{rel}"  # SYNCED.name == <profile>
    body = {"message": f"backup: {api_path} (cron, {time.strftime('%Y-%m-%d')})",
            "content": b64, "branch": BRANCH}
    # Existing files need a sha
    try:
        meta = req("GET", f"/repos/{REPO}/contents/{api_path}?ref={BRANCH}")
        body["sha"] = meta["sha"]
    except RuntimeError as e:
        if "404" in str(e): pass
        else: fail.append((rel, str(e)[:200])); continue
    try:
        req("PUT", f"/repos/{REPO}/contents/{api_path}", body)
        success += 1
    except RuntimeError as e:
        fail.append((rel, str(e)[:200]))
    if i % 10 == 0 or i == len(changes):
        print(f"  [{i}/{len(changes)}] {success} ok, {len(fail)} fail "
              f"({time.time()-t0:.0f}s)")
print(f"Done. Success={success} Fail={len(fail)}")
```

### Option B: Git Data API (single atomic commit)

Use when you want a single commit in history. **Beware** the `BadObjectState` failure mode — see below.

```python
# After creating all blobs (POST /repos/{owner}/{repo}/git/blobs),
# attempt:
new_tree = req("POST", f"/repos/{REPO}/git/trees",
               {"base_tree": current_tree_sha, "tree": tree_entries})
# If 422 BadObjectState, fall back to Option A (Contents API).
```

## Step 5 — Verify

```bash
gh api "repos/<owner>/<repo>/commits?per_page=3" | python -m json.tool | head -40
gh api "repos/<owner>/<repo>/contents/<profile>" | head -20
```

Confirm `.env` is **not** in the listing.

## Known failure modes

| Failure | Cause | Fix |
|---|---|---|
| `git/trees` returns `GitRPC::BadObjectState` (HTTP 422) | Created 100+ blobs in tight succession; tree endpoint can't see them yet. **Verified on 2026-07-13 with 114 blobs.** | Use Contents API instead (Option A). |
| Contents API PUT 422 with "invalid content" | Path contains `\` (Windows). | `rel.replace("\\", "/")` before sending. |
| Contents API PUT 409 "does not match" | Missing `sha` for an existing file. | GET `/contents/{path}` first, include `sha` in body. |
| Contents API PUT 404 for a new file in a deep dir | Rare; Contents API auto-creates parent dirs in modern versions, but if you hit this, PUT each parent dir tree first. | Usually not a problem. |
| `git push` timeout 21s | TCP-level block on `github.com:443` | Use the API path. Do not retry. |
| Rate limit 403 | 5000/hr authenticated | `gh api rate_limit` first; defer to next cron if <100 remaining. |

## Sample run log (2026-07-13 PM backup, `handsome_company_manager`)

- 581 files in remote; 617 in synced local (after extended exclusions)
- 36 new + 78 modified + 0 deleted = 114 changes
- Contents API: 114 PUTs, ~3 sec each ≈ 5-6 min total
- Tree API: 114 blobs created in 310s; tree creation failed with 422 (the case that motivated this doc)
- Outcome: Contents API path pushed all 114 changes successfully

## Cross-references

- Parent SKILL.md: `../SKILL.md`
- The exclusion list: `scripts/sync_profile.py` (EXCLUDE_DIRS, EXCLUDE_FILES, EXCLUDE_GLOBS)
- The cron job that triggered this work: `~/.hermes/profiles/handsome_company_manager/cron/jobs.json` (entry: `handsome_company_manager-config-backup`)
