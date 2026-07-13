# Per-Agent Identity & Credential Verification

Distilled from a real ops session (2026-07-13) where a negative test accidentally wiped a live `GITHUB_TOKEN` from a `~/.hermes/profiles/<name>/.env`. The fix was a fail-fast verifier that boots before any gateway process starts.

## Why This Exists

Every 1+N employee carries its own GitHub identity:

- `GITHUB_TOKEN` — PAT for `gh issue edit --add-assignee`, `gh issue comment`, etc.
- `GITHUB_USERNAME` — the employee's GitHub login (e.g. `handsome-hudeveloper`)
- `GITHUB_EMAIL` — noreply format `<github_id>+<login>@users.noreply.github.com`

These three must stay consistent. Drift happens silently: cron poll wakes up, runs `gh issue list @me`, gets an empty result, sleeps again — and the team spends a polling cycle before anyone notices. Worse: the employee might still AUTHENTICATE (some GitHub endpoints accept the token) but comment / assign under the wrong identity, which breaks the iron-rule "only-reviewer-can-close" assumption.

## The Fail-Fast Verifier

`scripts/verify_github_identity.sh <profile-name>` calls `gh api /user` with the profile's stored token, parses out `{login, id}`, and cross-checks against `.env`'s `GITHUB_USERNAME` and `GITHUB_EMAIL`. Exit codes:

| Exit | Meaning |
|------|---------|
| 0    | OK — token ↔ username ↔ email all match |
| 2    | Missing profile name argument |
| 3    | `.env` not found at expected path |
| 4    | `gh api /user` failed (bad token, network, no `gh`) |
| 5    | `/user` response didn't parse |
| 10   | login mismatch (token is not the right person) |
| 11   | email mismatch (noreply format wrong) |
| 12   | api id is not a positive integer |

## Wire It Into `start.sh`

For each `agents/<name>/start.sh`, after `hermes profile use "$PROFILE_NAME"` and before `hermes gateway start`:

```bash
PROFILE_NAME="$name"
hermes profile use "$PROFILE_NAME"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Path assumes the canonical oneplusn install layout:
#   <hermes_root>/skills/productivity/oneplusn/scripts/verify_github_identity.sh
VERIFY="$(dirname "$SCRIPT_DIR")/../../../../skills/productivity/oneplusn/scripts/verify_github_identity.sh"
[ -f "$VERIFY" ] || VERIFY="$HOME/.hermes/profiles/$PROFILE_NAME/skills/productivity/oneplusn/scripts/verify_github_identity.sh"

bash "$VERIFY" "$PROFILE_NAME" || {
  echo "[✗] identity check failed for $PROFILE_NAME; gateway NOT started" >&2
  exit 1
}

exec hermes gateway start
```

## The Big Pitfall: Don't sed -i a Live .env

**This is what caused the 2026-07-13 incident.** I designed a negative test by running `sed -i "s|^GITHUB_TOKEN=.*|GITHUB_TOKEN=*** ...|xargs -I {} sed -i` against the actual file, which had bash-quoting issues that turned the line into `GITHUB_TOKEN=` (empty). The token was GONE from `.env`, and:

- handoff.yaml only stored `github_token_first8: github_pat_11...` (truncated, intentional security choice)
- Windows Credential Manager did not have a copy
- Python keyring (`auth.json`) only had LLM API keys, not GitHub PATs
- WMI couldn't read another process's env block (no admin shell + Win32 restrictions)
- The running gateway (PID 5352) had it in memory but Windows doesn't expose cross-process env

**Recovery took a manual paste from the boss.**

**Rule:** any test, lint, or transformation on a credential file MUST operate on a copy in `/tmp/`, never the live file. If you need a "wrong" .env for a negative test:

```bash
# CORRECT
cp ~/.hermes/profiles/<name>/.env /tmp/test-<name>.env
sed -i 's|^GITHUB_TOKEN=.*|GITHUB_TOKEN=*** etc.)
```

## MSYS / Windows Git-Bash Gotchas

1. **Path translation on `gh api`**: leading `/` in `gh api /repos/foo/bar` gets rewritten to a Windows filesystem path by MSYS. Use either:
   ```bash
   MSYS_NO_PATHCONV=1 gh api /repos/foo/bar
   # OR prefer `gh issue view`, `gh repo view` — they take repo paths not API paths
   ```

2. **HERMES_HOME is profile-aware**: when you `hermes profile use handsome_company_manager`, `HERMES_HOME` becomes `~/.hermes/profiles/handsome_company_manager/`. The verifier walks one level up to find the root; manual paths need the same correction.

3. **Quoting `$GITHUB_TOKEN` in `gh api`**: the verifier sets `GH_TOKEN="$GITHUB_TOKEN"` (not `GH_TOKEN=*** ... exit code instead of leaking the token string in an error.

## Tightening .env Permissions (icacls 600 equivalent)

Default Windows ACLs often grant `BUILTIN\Users:R` to user profile files, which is broader than needed for credentials. Lock to Administrator + SYSTEM:

```cmd
icacls "%LOCALAPPDATA%\hermes\profiles\<name>\.env" /inheritance:r /grant:r "Administrator:(R)" /grant:r "SYSTEM:(R)"
```

Verify with:

```cmd
icacls "%LOCALAPPDATA%\hermes\profiles\<name>\.env"
```

Should show only `Administrator` and `SYSTEM` entries.

## Why the Email Format `<id>+<login>@users.noreply.github.com` Matters

GitHub noreply emails are deterministic: any GitHub user can receive mail at `<numeric_id>+<login>@users.noreply.github.com`. The `id` is stable for the lifetime of the account. By storing this format in `.env` and verifying it against `api /user`'s `id`, we get a cross-check that catches:

- Token from wrong account pasted in
- Username typo
- Old token from a renamed/migrated account

If GitHub ever changes the noreply format, this check is the canary that flags it.

## Recovery When a Token Is Lost

1. Boss opens GitHub → Settings (under the employee's account) → Developer settings → Personal access tokens
2. Either paste the existing token from password manager, or generate a new one (scopes: `repo`, `read:org` minimum)
3. Append `GITHUB_TOKEN=<token>` to `.env` (or rewrite the full file — write_file is OK since you're providing the value, not editing in place)
4. `hermes gateway restart` (or run `start.sh` again — the verifier will re-check)
5. Run verifier standalone: `bash scripts/verify_github_identity.sh <profile>` — should print `[✓]`

## Per-Cycle Operational Checklist (add to weekly maintenance)

```bash
for prof in handsome_company_manager handsome_company_developer handsome_company_reviewer; do
  bash scripts/verify_github_identity.sh "$prof" || echo "  [BLOCK] $prof identity broken"
done
```

If any profile fails, the boss either re-pastes a token or rotates one in GitHub before any cron tick wakes up an unkeyed agent.

## See Also

- `SKILL.md` — "Per-Agent Credential & Identity Hygiene" section (with start.sh wiring snippet)
- `deployment-checklist.md` — pre-deploy auth verification (related: `gh auth status` for boss account)
- `claude-package-to-hermes-skill` — Anti-Patterns section (general "verify before trusting" porting rule)