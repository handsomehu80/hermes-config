# Hermes CLI / Fresh-Context Evaluator Pitfalls (Windows arg-length + call-site scan + terminal token-redaction)

Captured from a real cron tick (2026-07-13 23:31, reviewer) running the Issue #8 P1 joint verification of PR #14 (`gateways/budget_middleware.py`) + PR #15 (`agents/developer/hooks/tick_end.py`). Two fragility modes emerged that any reviewer will hit the first time they try to run a real fresh-context evaluator on a non-trivial diff. Pitfall 3 (added 2026-07-14) was hit during the post-verdict silent cron tick when trying to re-probe the GitHub repo.

## Pitfall 1 — `hermes chat --query <large-prompt>` fails with `WinError 206` on Windows

**Symptom:** the evaluator subprocess dies before the model is ever invoked:

```text
File "C:\...\subprocess.py", line 1538, in _execute_child
    hp, ht, pid, tid = _winapi.CreateProcess(executable, args, ...)
FileNotFoundError: [WinError 206] 文件名或扩展名太长。
```

`HermesCliEvaluator.__call__` (in `agents/developer/hooks/tick_end.py:169-194`) builds a single prompt containing the full scratchpad + git diff + test output, then passes it as `hermes chat --query <prompt>`. On Windows, `CreateProcess` has a hard limit of ~32K characters on the command line. The combined Issue #8 diff was **1336 insertions** — large enough to blow the limit; the model never started.

**Reproduction:**

```bash
# Construct a large prompt deterministically
python -c "
prompt = '\n'.join(['# heading ' + str(i) + ' lorem ipsum ' * 50 for i in range(2000)])
print(len(prompt))
"
# Expect: ~250,000 characters — well over WinError 206 threshold

# Confirm the failure mode
hermes chat --query "$(python -c 'print("x" * 50000)')" --toolsets evaluator-readonly --ignore-rules --max-turns 1
# Expect: WinError 206, model never runs
```

**Fix options (in order of preference):**

1. **Stdin / file-based prompt** — change `HermesCliEvaluator` to write the prompt to a tempfile and pass it via a new `--query-file` flag (added to `hermes-agent` if missing). Then `subprocess.run` carries the file path, which is short and unaffected by argv limits. This is the only correct long-term fix for the team evaluator.
2. **Compress the evidence** before the prompt is built — instead of the full git diff, pass `git diff --stat` + the list of changed files + a structured call-out of the body's verification bullets. The evaluator doesn't need the raw text to render a verdict; it needs the test output and a high-signal diff summary. Cuts argv size by 80–95% in most cases. Use this as a stop-gap until option 1 lands.
3. **Run on Linux/macOS only** — WinError 206 is Windows-specific. The team's evaluation harness is mostly reviewed on a Windows host, so this is operationally unacceptable. Document it as a constraint, do not adopt as the fix.
4. **Skip the real evaluator entirely** for large evidence sets and rely on adapter-level deterministic tests + production call-site scan (see Pitfall 2). Use the real evaluator only for the small-prompt cases where it adds genuine signal.

**Detection during a cron tick:**

```bash
# If the real evaluator subprocess fails with WinError 206, fall back to:
#   1. adapter-level scenario tests (deterministic, always run)
#   2. production call-site scan (see Pitfall 2)
#   3. report "real evaluator N/A due to argv limit" with the file paths so future dev work has a clear blocker
# Do NOT silently PASS the issue just because the unit tests are green.
```

**Observed in this profile (2026-07-13 23:31).** The reviewer cron tick produced three evaluator verdicts on the same evidence set:
- Full diff (1336 lines, ~200KB combined prompt) → `WinError 206` before model launch
- Compact `git diff --stat` (~1.5KB) → model launched, returned `STATUS: NEEDS_WORK` with the reason "缺少对 budget middleware 不干扰正常路径的端到端验证"
- Small NEEDS_WORK scenario (~500 bytes) → model launched, returned `STATUS: NEEDS_WORK` with the correct English+Chinese-blended reason

The first failure mode is silent at the cron level — `subprocess.run` raises, the cron script catches, and the next layer has no way to distinguish "model said PASS" from "model never started." Always test the argv size before relying on the evaluator verdict in the verification report.

## Pitfall 2 — Production call-site scan (catches "library not wired" before adapter-only PASS lies to you)

**The blind spot:** a feature can have 100% adapter-level test coverage (its `BudgetMiddleware` class works in isolation, all 20 unit tests pass, the `ruff` + `compileall` runs are clean) and still be **completely absent from the production dispatcher / cron lifecycle** — meaning the next real cron tick can run the agent without ever touching the new code. The reviewer who only runs the unit tests will sign a PASS verdict on a feature that does not exist at runtime.

**The pattern:** before signing off, scan the worktree for production call sites of the new module's symbols. Exclude the module itself, its tests, and any dry-run helper. Zero production call sites = "feature ships as a library, not a closed loop" = `NEEDS_WORK` regardless of how green the unit tests are.

```python
# scripts/scan_production_callsites.py
from pathlib import Path

EXCLUDE_DIRS = {".git", "__pycache__"}
EXCLUDE_FILES = {
    Path("gateways/budget_middleware.py"),       # the module itself
    Path("tests/test_budget_middleware.py"),    # unit tests
    Path("tools/evaluator_dry_run.py"),         # dry-run helper
    Path("tmp/issue-8-joint-verification.py"),  # reviewer's own verification script
    # ... add per-tick exclusions for any reviewer-authored helper
}
SYMBOLS = ["BudgetMiddleware", "write_scratchpad", "run_tick_end"]


def production_callsites(repo_root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {sym: [] for sym in SYMBOLS}
    for path in repo_root.rglob("*.py"):
        rel = path.relative_to(repo_root)
        if rel in EXCLUDE_FILES or any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for sym in SYMBOLS:
            if sym in text:
                hits[sym].append(str(rel).replace("\\", "/"))
    return hits


if __name__ == "__main__":
    import json
    import sys
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    result = production_callsites(repo)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    any_hit = any(result.values())
    sys.exit(0 if any_hit else 2)
```

**Run before writing the verification verdict:**

```bash
python scripts/scan_production_callsites.py .
# Expect (for a fully-wired feature):
# {"BudgetMiddleware": ["hermes/dispatcher.py", "hermes/cron_lifecycle.py"], ...}
# If any symbol has [] as its value, the feature is a library, not a closed loop
```

**How to use the result in the verdict:**

| Call-site result | Verdict | Reasoning |
|---|---|---|
| All symbols have ≥ 1 hit | PASS (or partial — check the call is a real lifecycle hook, not just an import) | Library is wired into production |
| Some symbols have 0 hits | NEEDS_WORK | Library is partially wired; the missing symbols are bypassable at runtime |
| All symbols have 0 hits | NEEDS_WORK (always, regardless of unit-test green) | Library is unwired; the feature ships as dead code at runtime |

**Important: the call-site scan is a necessary but not sufficient signal.** A symbol can have a hit that is itself a test fixture or a one-shot script. Cross-check each hit by reading the surrounding function:

```bash
# Quick check: every hit is a real lifecycle hook, not a test or fixture
for hit in $(jq -r '.BudgetMiddleware[]' hits.json); do
  echo "--- $hit ---"
  grep -n -B2 -A2 'BudgetMiddleware' "$hit"
done
```

**Observed in this profile (2026-07-13 23:31).** The P1 dual-implementation of per-tick budget + scratchpad/evaluator had:

```json
{
  "BudgetMiddleware": [],
  "write_scratchpad": [],
  "run_tick_end": []
}
```

All three symbols shipped as standalone libraries, with zero production dispatcher / cron lifecycle hits. The 20/20 unit tests were honest about the library's correctness but completely silent about its integration gap. The reviewer verdict had to be `NEEDS_WORK` despite the green unit tests. Without the call-site scan, the verdict would have been `PASS`, and the boss would have learned the truth in the next 90-min cron tick window when a real `$47K ping-pong` incident (the reason this whole feature exists) hit and the new library didn't fire.

## Pitfall 3 — `terminal()` redacts token values to literal `***`, breaking `source <(grep …)` env loading

**Symptom:** you `source` a profile `.env` (e.g. `source <(grep -v '^#' "$ENV" | sed 's/^/export /')`) to load `GITHUB_TOKEN`, then run `GH_TOKEN=*** gh api user`. The shell command renders fine in the tool input, but the actual `export GITHUB_TOKEN=…` line gets re-rendered with the token value masked as `***` by the time bash executes it. Result: `GITHUB_TOKEN` is set to the literal three-character string `***`, and GitHub returns `HTTP 401 Bad credentials`. The username field usually round-trips fine (it's not a secret), so the `.env` *looks* loaded — only the token failed.

**Reproduction (looks correct in input but fails at runtime):**

```bash
# Token renders fine in the tool input, but '***' in the executed command
source <(grep -v '^[[:space:]]*#' "$ENV" | grep -v '^[[:space:]]*$' | sed 's/^/export /')
GH_TOKEN=*** gh api user --jq '{login: .login, id: .id}'
# Expect: {"message":"Bad credentials", "status":401}
```

**Fix — use `execute_code` + Python `subprocess.run(env=…)`:**

```python
import subprocess, os, json

env_path = r"C:\Users\Administrator\AppData\Local\hermes\profiles\<agent>\.env"
env_vars = {}
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            env_vars[k.strip()] = v.strip()

# Explicit env dict sidesteps the shell-rendering layer entirely
merged = {**os.environ, **env_vars, 'GH_TOKEN': env_vars['GITHUB_TOKEN']}

result = subprocess.run(
    ['gh', 'api', 'user', '--jq', '{login: .login, id: .id}'],
    env=merged, capture_output=True, text=True, shell=True,
)
identity = json.loads(result.stdout)
assert identity['login'] == env_vars['GITHUB_USERNAME'], "PAT/username mismatch"
```

**Why this works:** the `execute_code` sandbox receives the Python source as text, runs it in-process, and only emits the *output* of `subprocess.run` — never re-renders the source. The token value passes through `env_vars['GITHUB_TOKEN']` → `merged` → `subprocess.run(env=…)` without ever being exposed to the terminal-rendering layer that does the `***` substitution.

**Detection signals (any one means the pre-flight is lying):**

1. `gh api user` returns `Bad credentials` but `gh auth status` shows you logged in as someone else (boss's OAuth token, not the employee's PAT) — the shell `export` round-trip silently failed and the subprocess fell back to ambient credentials.
2. `gh api repos/<org>/agent_workflow` returns HTTP 401 instead of 200 with push permission.
3. `gh api user --jq .login` returns `handsomehu80` (or whatever boss account is in the keyring) instead of the agent's expected `Handsome-Review` / `Handsome-Manager` / `handsome-hudeveloper` — the .env didn't load and the subprocess fell back to the keyring.

**Diagnostic before assuming the env loaded correctly:**

```python
# In execute_code, sanity-check the env vars before using them
assert 'GITHUB_TOKEN' in env_vars, ".env missing GITHUB_TOKEN"
assert env_vars['GITHUB_TOKEN'].startswith('gh'), f"token doesn't look like a GitHub PAT: {env_vars['GITHUB_TOKEN'][:4]}…"
print(f"Loaded: login={env_vars['GITHUB_USERNAME']} token_prefix={env_vars['GITHUB_TOKEN'][:12]} (len={len(env_vars['GITHUB_TOKEN'])})")
```

**Observed in this profile (2026-07-14 00:11, reviewer cron).** Tried `source <(grep … | sed 's/^/export /')` first; `gh api user` returned `{"message":"Bad credentials","status":401}`. Switched to `execute_code` + `subprocess.run(env=merged)`: `{"id":301659611,"login":"Handsome-Review"}` — identity confirmed, pre-flight passed, poll proceeded normally. The 401-vs-200 difference between the two patterns is the only way to tell whether the env actually loaded; the rendered shell command looks identical.

**When to skip this and use `terminal()` anyway:** if the `.env` only contains non-secret config (URLs, log levels, timeouts, model names), `source` + `export` works fine — only token-bearing vars get the `***` rendering treatment. For any token-driven probe (the oneplusn pre-flight, OAuth flows, API calls with Bearer tokens), always reach for `execute_code` first.

**Generalization:** the `***` substitution is a Hermes terminal-output redaction for *any* string matching common secret shapes (long base64-ish blobs, anything starting with `gh*`, `sk_*`, `AKIA*`, etc.). Even passing the token as an inline arg (`GH_TOKEN=*** gh api user`) is unsafe because the rendered command still contains `***`. The `execute_code` + `subprocess.run(env=…)` pattern is the only reliable workaround short of patching Hermes terminal to suppress redaction for known-safe contexts.

## Cross-Reference

- `git-push-and-self-close.md` — same Git Data API atomic-commit pattern used to land the verification report on a firewalled Windows host (where `git push` is blocked but `api.github.com` works).
- `llm-as-judge-pitfalls.md` — the verdict/reason parsing + sentinel format pitfalls that the fresh-context evaluator can hit even when argv size is fine. Pitfall 1 above is "evaluator never starts"; the LLM-as-judge file covers "evaluator starts but the verdict is unreliable."
- `employee-repo-access.md` — covers the "PAT authenticates but can't see org repo" failure mode (HTTP 404), which is the next domino after Pitfall 3's "PAT authenticates" pre-flight passes.
- `reviewer-cron-tips` (sibling skill) — operational notes specific to the handsome_company_reviewer profile, including the same `WinError 206` pitfall observed from the cron side and the multi-issue tick pattern this scan fits into.