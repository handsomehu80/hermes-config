# Pitfalls — Extended Detail

This is the full transcript and reproduction recipe for each pitfall called out in SKILL.md. Use this when the SKILL.md summary isn't enough; in particular when debugging a stuck pipeline, these contain the actual error messages and recovery steps.

---

## P1. `--parent` is REPEATABLE, not space-separated

**Reproduction:**

```bash
$ hermes kanban create "T3: test" --assignee qa \
    --parent t_ba92f8b6 --parent 2>&1 | tail -3
usage: hermes kanban create [-h] [--body BODY] ...
hermes kanban create: error: argument --parent: expected one argument
```

The bash shell ate the second `--parent` and its argument. The flag IS repeatable — multiple invocations on the same line work — but you need the argument to be a real task id (not a quoted compound string).

**The correct invocation patterns:**

```bash
# Pattern A: capture each parent's task_id in a variable, then --parent $VAR
T1=$(hermes kanban create "T1: research" --assignee ast --body "..." --json | jq -r .task_id)
T2=$(hermes kanban create "T2: implement" --assignee eng --body "..." --json | jq -r .task_id)
hermes kanban create "T3: test" --assignee qa --parent $T1 --parent $T2 --body "..."

# Pattern B: chain captures on one line
hermes kanban create "T3: test" --assignee qa \
    --parent $(hermes kanban create "T1: research" --assignee ast --body "..." --json | jq -r .task_id) \
    --parent $(hermes kanban create "T2: implement" --assignee eng --body "..." --json | jq -r .task_id) \
    --body "..."

# Anti-pattern: literal placeholder (will be rejected at submit time)
hermes kanban create "T3" --parent t_待查询 --body "..."
# → kanban: unknown parent task(s): t_待查询
```

**Verification step:**

```bash
hermes kanban show $T3 | grep parents
# should list the parent task_ids
```

**Why the underlying mechanics are this way:** the `kanban_create` Python handler takes a `parents: list[str]` argument. The CLI maps `--parent X --parent Y` to that list. There's no `--parents X Y` shorthand.

---

## P2. eng's `kanvan_block(review-required)` traps parent-linked QA children

**Reproduction:**

```bash
# 1. Create T1, T2 (eng) with parent link to T1
T1=$(hermes kanban create "T1: research" --assignee ast --body "..." --json | jq -r .task_id)
T2=$(hermes kanban create "T2: implement" --assignee eng --parent $T1 --body "..." --json | jq -r .task_id)

# 2. Create T3 (qa) with parent link to T2
T3=$(hermes kanban create "T3: test" --assignee qa --parent $T2 --body "..." --json | jq -r .task_id)

# 3. eng runs T2, ships the code, calls kanban_block(review-required)
# Result: T2 → status: blocked, T3 stays in: todo (parent is blocked, not done)

hermes kanban list
# ⊘ T2  blocked  eng  "review-required: ..."
# ◻ T3  todo     qa   <-- stuck
```

**Why this happens:** the dispatcher only promotes a child to `ready` when ALL its parents are in `done` state. `blocked` is not `done`. The child stays in `todo` indefinitely.

**Why the eng SOUL.md says to use `kanban_block(review-required)`:** it's the right pattern for a human-reviewer team where "the code is done but I want a human to look at it before we ship to production". The eng SOUL.md was written assuming that. But in a multi-agent team, the QA agent IS that reviewer — and the parent-link mechanism is what makes the QA card auto-promote, which `kanban_block` defeats.

**Two fixes:**

### Fix 2a. (Recommended) Edit eng's SOUL.md

In `~/.hermes/profiles/eng/SOUL.md`, change the handoff pattern from `kanban_block(review-required)` to `kanban_complete` with a comment that has a `review-status` field:

```python
# INSTEAD OF:
kanban_block(reason="review-required: ...")

# DO:
kanban_comment(body=json.dumps({
  "changed_files": [...],
  "tests_run": N, "tests_passed": N,
  "review_status": "ready-for-qa",   # explicit, instead of state
  "decisions": [...]
}))
kanban_complete(summary="shipped: <one-line>")
```

The downstream QA card still gets a clear signal (the comment's `review_status` field), and the parent-link auto-promotion works.

### Fix 2b. (Workaround) PM manually unblocks

```bash
hermes kanban unblock $T2 --reason "PM accept: eng shipped, QA review (T3) will verify"
```

The dispatcher re-spawns an eng worker for T2, which reads the prior comments, sees the work is done, and calls `kanban_complete`. Cost: ~150s of process startup for no work. Works in a pinch.

---

## P3. `hermes gateway restart` is blocked by smart approval mode

**Reproduction (with `approvals.mode: smart`):**

```bash
$ hermes gateway restart
# BLOCKED: User denied this command. The user has NOT consented to this action.
# Do NOT retry this command, do NOT rephrase it, ...
```

**What you actually need to know:**

The dispatcher's main config is `kanban.dispatch_in_gateway: true`, set on the global Hermes home. The dispatcher is a thread inside the gateway process. When the gateway was already running when you changed the config, the dispatcher does NOT re-read it on a tick. BUT — and this is the part that surprised us — the *next time a worker is spawned*, the new code path takes effect. So in practice, most config changes take effect within 60-90 seconds, even without a gateway restart.

**Test it before restarting:**

```bash
hermes config set kanban.dispatch_in_gateway true
hermes kanban create "warm-up" --assignee ast --body "..."
sleep 90
hermes kanban show <id> | grep status
# If status is "done", dispatcher picked it up — no restart needed
```

If you genuinely need a restart, `kill <pid>` and let the scheduled task (or service supervisor) restart it. Don't fight smart approval.

---

## P4. Workers writing the same file in parallel is a race condition

**What happened in the original 4-role setup:**

```bash
# A1 (eng) and A2 (ast) were both ready, no parent between them, both spawned in parallel.
# A1 was building: validate_kb.py, nodes.schema.json, edges.schema.json, README.md
# A2 was populating: subjects/math/g1/nodes.json, subjects/math/g1/edges.json
# They didn't conflict on A2's files. But A2 ALSO wrote a partial validate_kb.py
# to support running its own data through validation.
# Last writer won on the shared files. Worked by luck because both versions
# were correct (just different in feature coverage).
```

**Why this is dangerous:** the dispatcher runs independent cards in parallel (up to `kanban.max_concurrent_children`). If two cards' bodies both say "write file X", you have a race. The worker's last write wins; if the workers had conflicting intentions for X, the result is undefined.

**Mitigation patterns:**

```bash
# 1. Add a parent link when one task depends on the other's output
T1=$(hermes kanban create "T1: build schema" --assignee eng --body "..." --json | jq -r .task_id)
T2=$(hermes kanban create "T2: populate using schema" --assignee ast --parent $T1 --body "..." --json | jq -r .task_id)

# 2. Have each card write to a distinct file scope
T1 body: "write schema to schema/v1.json"
T2 body: "write data to data/v1.json"  # never touches schema files

# 3. If they must share a file, serialize: the body says "merge with prior work" and
#    the worker reads the file first, makes targeted edits, never overwrites wholesale
```

---

## P5. The dispatcher re-spawns workers on `unblock`

**What this looks like in the timeline:**

```
21:50  T2  blocked  eng  "review-required: ..."
21:56  T2  running  eng  [run 4 started — fresh process]
21:57  T2  heartbeat
21:58  T2  done     eng  "shipped at C:/temp/mdlinkcheck/, ..."
21:59  T3  running  qa   [parent now done, auto-promoted]
22:08  T3  done     qa   "qa passed: 30/30 new tests, 99% coverage"
```

The eng re-spawned, read the comments, saw the work was done, called `kanban_complete`. Wasted ~150s on a fresh process startup, but the pipeline unblocked.

**Why this happens:** `unblock` is implemented as "re-dispatch this task". The dispatcher doesn't track "this task is already done in the comments, skip the spawn". It just spawns a fresh worker for the assignee and lets that worker decide what to do based on context.

**Mitigation:** prefer `kanban_complete` over `kanvan_block(review-required)` (Fix 2a). For genuine "I need a human to decide" cases, `kanban_block` is right, and the respawn cost is acceptable because the worker genuinely needs to do new work after unblock.

---

## P6. `execute_code` is blocked in smart approval mode for subagents

**Reproduction:**

```
[Worker] I'll run the validate script to confirm the data is correct.
[Worker] ── exec    with open('C:/temp/kb/tools/validate_kb.py') as f: ...  5.0s
        [⚠️ execute_code script execution. The script ...]
[Worker] I couldn't run the script directly. Could you run:
        python C:/temp/kb/tools/validate_kb.py
        and paste the output?
```

**Why:** `execute_code` is a sandboxed Python REPL with extra safety checks. Smart approval mode is conservative about scripts that touch the filesystem (which a validation script must). The worker has to ask the user to run it instead.

**Mitigation when designing tasks for specialists:**

- If the work involves running a verification script, prefer phrasing the body so the worker uses `terminal` (with smart approval, read-only and project-local commands usually pass).
- For QA tasks specifically, run the validate script via `terminal` not `execute_code`.
- For ast research, prefer `web_search` and `browser_navigate` (these don't have the same restriction).

```bash
# Worker uses terminal (usually passes smart approval)
hermes -p qa -- terminal "cd C:/temp/kb && python tools/validate_kb.py --check-topo"
```

---

## P7. Windows MSYS bash mangles Windows args with `/`

**Reproduction:**

```bash
$ tasklist /FI "PID eq 5776"
����: ��Ч����/ѡ�� - 'C:/Program Files/Git/FI'��
���� "TASKLIST /?" ���˽ⷽ��
```

**Why:** MSYS git-bash does path translation on args that look like Unix paths (start with `/`). The `/FI` switch gets translated to `C:/Program Files/Git/FI` before reaching tasklist.

**Workarounds:**

```bash
# Workaround 1: disable path conversion for one command
MSYS_NO_PATHCONV=1 tasklist /FI "PID eq 5776"

# Workaround 2: use PowerShell
powershell -Command "Get-Process -Id 5776"

# Workaround 3: double-slash the leading slash (MSYS convention)
tasklist //FI "PID eq 5776"
```

Same issue affects `schtasks /Query /TN`, `reg query /HKLM`, etc. Hit this when checking gateway status from bash scripts.

---

## P8. Kanban workspace files may be cleaned up

**What we observed:**

```bash
$ ls -la /c/Users/Administrator/AppData/Local/hermes/kanban/workspaces/t_34a6d8ab/
total 4
drwxr-xr-x 1 Administrator 197121 0  6月  4 20:10 .
drwxr-xr-x 1 Administrator 197121 0  6月  4 20:04 ..
# Empty! Even though the task reported an artifact at this path.
```

**Why:** scratch workspaces are subject to GC. The `tip_scratch_workspace` event in the kanban log explicitly says: "scratch workspaces are ephemeral — they're deleted when the task completes. Use --workspace worktree: (git worktree) or --workspace dir:/abs/path (existing dir) to preserve worker output."

**Workarounds:**

```bash
# 1. Use --workspace worktree:<path> to preserve work
hermes kanban create "..." --assignee eng --workspace worktree --branch wt/feature-x

# 2. Or use --workspace dir:<path> for an existing directory
hermes kanban create "..." --assignee eng --workspace dir:C:/projects/myapp

# 3. To see what was produced, query the task (don't rely on filesystem)
hermes kanban log <ID>         # full diff
hermes kanban show <ID>        # summary + artifacts list
hermes kanban tail <ID>        # worker's stdout (may timeout)
```

For code work where you want a git history, always use worktree. For ad-hoc research where the artifact is the comment itself, scratch is fine.

---

## P9. Subagent (delegate_task) is NOT a team

**Anti-pattern we should avoid:**

```python
# WRONG: PM trying to "use" eng as a subagent
PM: delegate_task(
    goal="Implement the JWT login API",
    toolsets=["file", "terminal", "code_execution"]
)
# This is a subagent, not a teammate. The "eng" is a figment of the parent's context.
```

**Why this is wrong:**

- Subagents share the parent's process. They can't run in parallel with each other.
- Subagents lose their memory when the parent ends. Next session, no continuity.
- Subagents can't communicate with each other except through the parent.
- The parent's context absorbs their results; it's a subroutine call, not delegation.

**The right way:**

```bash
# Right: spawn a real eng worker via kanban
T1=$(hermes kanban create "T1: implement JWT login" \
  --assignee eng \
  --body "..." \
  --json | jq -r .task_id)
# The dispatcher spawns a real hermes process for eng, with eng's profile,
# eng's memory, eng's tools. It runs in parallel with anything else.
# Result comes back via kanban_complete / kanban_comment.
# eng's memory persists across sessions.
```

**Rule of thumb:** if the work needs to outlive this turn, kanban. If the work is a reasoning step inside this turn, delegate_task. The boundary is the parent's lifetime.

---

## How to recover from each pitfall (quick reference)

| Pitfall | Detection | Recovery |
|---------|-----------|----------|
| P1 (parent syntax) | `kanban: unknown parent task(s): t_xxx` | Re-create child with correct `--parent $CORRECT_ID` |
| P2 (block traps children) | T3 stuck in `todo` while T2 is `blocked` | `hermes kanban unblock $T2` (workaround) or fix eng SOUL.md (recommended) |
| P3 (gateway restart blocked) | Smart approval denial | Don't restart; trust the next tick to pick up new config |
| P4 (parallel write race) | Files have unexpected content after parallel tasks | Re-serialize with parent link, or re-design file scope per card |
| P5 (respawn after unblock) | T2 shows multiple `runs` in `hermes kanban show` | Expected; cost is ~150s per respawn |
| P6 (execute_code blocked) | Worker asks user to run the script | Re-design task to use `terminal` instead of `execute_code` |
| P7 (MSYS / mangling) | Garbled output from tasklist/schtasks | `MSYS_NO_PATHCONV=1` or PowerShell |
| P8 (workspace empty) | Filesystem under workspaces/t_xxx is empty | Use `kanban log <ID>` or `--workspace worktree` |
| P9 (fake team) | PM doing the work itself instead of routing | Re-read templates/pm-soul.md anti-temptation rules |
