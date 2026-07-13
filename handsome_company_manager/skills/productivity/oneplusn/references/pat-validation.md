# Per-employee GitHub PAT validation

Use this procedure when onboarding a digital employee, replacing its token, or diagnosing GitHub polling failures. The goal is to prove three separate facts without ever printing the token: the credential is valid, it belongs to the intended employee, and it can access the private workflow repository.

## Why `gh auth status` is not enough

A machine can have several credential sources at once:

- `GH_TOKEN` / `GITHUB_TOKEN` in the process environment
- the employee profile's `.env`
- a GitHub CLI keyring login, often the boss account

Environment tokens take precedence over the keyring. Also, editing `.env` does not mutate the environment of an already-running Hermes/Gateway process. This can produce misleading results: `gh auth status` may show the boss keyring account, or a stale placeholder from the parent process, while the file contains a different token.

## Required validation sequence

1. Identify the intended employee account and repository from `handoff.yaml`.
2. Confirm the profile `.env` contains `GITHUB_TOKEN`, but do not print its value.
3. Read the token from that file inside a short-lived verifier and call `GET https://api.github.com/user`.
4. Require the returned `login` to equal the employee's `github_username` case-insensitively.
5. With the same file-loaded token, call `GET /repos/{org}/{repo}`.
6. Require repository access and sufficient permissions before restarting the Gateway or enabling polling.
7. Restart the employee Gateway so it loads the new `.env`, then manually run one polling job as a smoke test.

Passing `/user` alone is insufficient. A valid fine-grained PAT can still return `404` for a private repository when that repository was not selected, the organization has not approved the token, or the employee lacks repository access.

## Safe verifier (Windows / Git Bash compatible)

This script prints metadata only; it never prints the credential. Replace paths and expected names, not the token itself.

```bash
python - <<'PY'
import json, pathlib, re, urllib.error, urllib.request

ENV_FILE = pathlib.Path("C:/Users/Administrator/AppData/Local/hermes/profiles/EMPLOYEE/.env")
EXPECTED_LOGIN = "Employee-GitHub-Login"
ORG = "your-org"
REPO = "agent_workflow"

text = ENV_FILE.read_text(encoding="utf-8-sig", errors="ignore")
m = re.search(r"(?m)^\s*GITHUB_TOKEN\s*=\s*(.*?)\s*$", text)
token = m.group(1).strip().strip('"').strip("'") if m else ""
if not token or token in {"github_pat_", "ghp_", "TOKEN_HERE"}:
    raise SystemExit("FAIL: missing or placeholder GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "oneplusn-pat-check",
}

def get(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"FAIL: {url} returned HTTP {exc.code}") from None

user = get("https://api.github.com/user")
login = user.get("login", "")
print(f"token_valid=True token_owner={login}")
if login.casefold() != EXPECTED_LOGIN.casefold():
    raise SystemExit(f"FAIL: expected {EXPECTED_LOGIN}, got {login}")

repo = get(f"https://api.github.com/repos/{ORG}/{REPO}")
permissions = repo.get("permissions") or {}
print(f"repo_access=True repo={repo.get('full_name')} permissions={permissions}")
if permissions and not (permissions.get("push") or permissions.get("admin") or permissions.get("maintain")):
    raise SystemExit("FAIL: repository is visible but token lacks write permission")
PY
```

If shell heredocs are unsuitable, save the same logic as a temporary Python file and run it with `python` (not `python3` on this Windows host).

## Fine-grained PAT checklist

For the employee account's PAT:

- Resource owner: the target organization
- Repository access: select `agent_workflow` (or the actual workflow repository)
- Issues: read and write
- Contents: read and write when employees edit repository files
- Pull requests: read and write when the workflow uses PRs
- Metadata: read
- Organization members: read when assignment/member lookup requires it
- Organization approval: completed if the organization requires owner approval

## Fresh-process rule

After changing a profile `.env`:

- Do not trust the current shell's inherited `GITHUB_TOKEN`.
- Validate by reading the file directly as above.
- Restart the relevant Gateway/profile before the next cron run.
- Run one polling job manually and verify the GitHub comment/assignment is authored by the intended employee.

Never store PAT values in `handoff.yaml`, logs, skill files, memory, command output, or status reports.
