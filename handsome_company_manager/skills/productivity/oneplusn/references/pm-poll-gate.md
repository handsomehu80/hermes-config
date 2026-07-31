# PM Task-Polling Gate: Fresh Identity, Assignment, and Feedback Checks

Use this runbook for a **task-polling** fire only. It is not a substitute for the PM bi-hourly or daily status-report references.

## 0. Scope: bind the persona to ONE org/repo (the cross-org contamination trap)

Digital employees created during `oneplusn init` may exist under **multiple GitHub orgs simultaneously** — typically the real `{org}/{repo}` plus a bootstrap-test org (e.g. `handsome-oneplusn-company/agent_workflow`) left over from a sandbox `oneplusn init` run. A bare `assignee:{persona}` query returns the union of every org where that login has an open Issue, which looks like real work but is out-of-scope for this profile.

**Rule:** for every task-polling tick, treat ONE canonical `{org}/{repo}` pair as the persona's operating scope (recorded in `handoff.yaml` / profile `SOUL.md`; mirrored in `state/last-seen-{persona}.json` `poll_source` — never derive scope from `gh auth status`, which is the human/boss account on this host). Always include `repo:{org}/{repo}` in any search API call:

```bash
# Correct: scope-qualified search (only canonical org/repo)
COUNT_A=$(gh api "search/issues?q=repo:{org}/{repo}+assignee:{persona}+is:open+is:issue" \
  --jq '.total_count')

# Wrong: unscoped search returns cross-org noise and looks like real triage
COUNT_BAD=$(gh api "search/issues?q=assignee:{persona}+is:open+is:issue" --jq '.total_count')
```

**Verified case (PM task-polling tick, 2026-07-30):** unscoped search returned **11 hits**, all in `handsome-oneplusn-company/agent_workflow` (a sibling test org from oneplusn init); the persona's canonical scope `handsome-s-company/agent_workflow` returned **0** — same persona, two different queues. Without the scope qualifier the PM would have falsely claimed there was work to do and produced 11 false dispatches. Always cross-check Source A (scope-qualified search) against Source B (repo enumerator at §1 gate 3) before drawing any conclusion about queue size.

## 1. Run the three gates in order

1. **Identity gate:** read the active profile's credential once (never print it), call `GET /user`, and assert the returned login equals the employee persona in the team manifest. Do this before querying Issues; a valid token for the wrong account produces a plausible but false empty queue.
2. **Repository gate:** call `GET /repos/{org}/{repo}` with the same persona credential and require HTTP 200. A direct collaborator may be reachable even when `/user/repos` does not list the repository; the per-repository probe is authoritative before writes.
3. **Assignment gate:** query `GET /repos/{org}/{repo}/issues?state=open&assignee={persona}&per_page=100`, then remove entries with a non-null `pull_request` field. The Issues API includes pull requests because GitHub models them as Issues.

Cache the credential and identity for the rest of the run. Do not use the local `gh auth status` login as the persona filter or as proof that comments will be authored by the persona.

## 2. The zero-queue branch is deliberately side-effect-free

If the filtered assignment list (gate 3 above) is empty:

- do not search broad `@mentions`, inspect closed Issues, or start PM orchestration;
- do not add comments, labels, assignments, or state files merely to announce the empty queue;
- finish with exactly `[SILENT]` and nothing else.

This is a successful poll, not a degraded one. The identity and repository gates still need to pass so that an auth or access failure is not mistaken for an empty queue.

**Triage-pool pitfall (PR-filter required for "unassigned open" too):** when you also enumerate the unassigned open Issues (`GET /repos/{org}/{repo}/issues?state=open&per_page=100`, no `assignee=` filter), apply the **same** `pull_request == null` filter before counting. PRs returned by that endpoint look like a "triage backlog" but are not Issues; without the filter you will mis-classify a healthy queue as work to do. Verified case (PM task-polling tick, 2026-07-30): `/repos/.../issues?state=open` returned 5 entries, **3 of which were PRs** (#13/#14/#15, `pull_request` field populated); real Issue count was 2 (the same dev-self-stale pair already on the reaper's docket and not new feedback). The previous tick's `state/last-seen-pm.json` reported `open_total_repo: 2` because it never enumerated unassigned — a state-file field that under-counts the triage pool is a real source of drift, and the canonical probe's PR-filtered recompute is the corrective check.

## 2a. Triple-source cross-check before `[SILENT]`

A bare "filtered assignment list is empty" claim from gate 3 is necessary but not sufficient — one source can lie (stale search index, wrong-scope drift, last-state-file under-counting). Cross-verify against three independent sources before emitting `[SILENT]`:

```bash
# Source A — scope-qualified search API (per §0; bounded to canonical org/repo)
COUNT_A=$(gh api "search/issues?q=repo:{org}/{repo}+assignee:{persona}+is:open+is:issue" \
  --jq '.total_count')

# Source B — repo enumerator (authoritative, no search-index delay; PR-filtered per §2)
COUNT_B=$(gh api "repos/{org}/{repo}/issues?assignee={persona}&state=open&per_page=100" \
  --jq '[.[] | select(.pull_request == null)] | length')

# Source C — last-state anchor; if previous tick wrote state/last-seen-{persona}.json,
#            read its recorded `open_assigned_to_me` and confirm zero
COUNT_C=$(jq -r '.queue.open_assigned_to_me // empty' \
  "$WORK_DIR/state/last-seen-{persona}.json" 2>/dev/null || echo "0")
```

All three zero, plus a separate PR-filtered check of the unassigned pool (gate 3's analog without the `assignee=` filter), is the strongest pre-`[SILENT]` evidence short of per-issue events-endpoint audits. If any source disagrees, treat as "work to do" and investigate — do not paper over disagreement with `[SILENT]`.

When you have a `pm_poll.py` (canonical probe script under `profile/skills/productivity/oneplusn/scripts/` or `tmp/`), it writes the post-tick JSON automatically; consult `state/last-seen-{persona}.json` as Source C instead of re-deriving. When the previous tick wrote `tick_decision: [SILENT]` and Source A/B/C all agree, write the same decision and reason back to the state file in the same shape so the next tick can skip re-deriving from scratch.

## 3. Process only actionable feedback

For each assigned open Issue:

- fetch the full comment list, not just a count;
- use a persisted last-seen comment/event baseline when available;
- on a first-seen Issue with zero comments, treat the assignment as feedback: post one Chinese claim/welcome comment and apply the role's permitted label transition while retaining the assignee;
- otherwise, act only when feedback is newer than the baseline and came from someone else;
- if the CLI account is different from the persona, inspect an in-body persona signature or the persisted comment ID before deciding that a boss-authored API comment is new. Do not create a reply loop from author mismatch alone.

When action is required, comment before reassigning, keep exactly one assignee, and report the concrete artifact/decision rather than a generic acknowledgement.

## 4. End-of-run verification

A normal actionable run should leave a traceable GitHub artifact: comment ID/author, label or assignee change, and the Issue number. A no-work run should leave no outbound GitHub mutation and should be represented solely by the exact `[SILENT]` response. If the identity or repository gate fails, report the blocker instead of emitting `[SILENT]`.

See also `references/cron-polling-behavior.md` for the full persona-vs-CLI distinction, smoke-test behavior, and posting-as-persona examples.