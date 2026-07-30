# PM Task-Polling Gate: Fresh Identity, Assignment, and Feedback Checks

Use this runbook for a **task-polling** fire only. It is not a substitute for the PM bi-hourly or daily status-report references.

## 1. Run the three gates in order

1. **Identity gate:** read the active profile's credential once (never print it), call `GET /user`, and assert the returned login equals the employee persona in the team manifest. Do this before querying Issues; a valid token for the wrong account produces a plausible but false empty queue.
2. **Repository gate:** call `GET /repos/{org}/{repo}` with the same persona credential and require HTTP 200. A direct collaborator may be reachable even when `/user/repos` does not list the repository; the per-repository probe is authoritative before writes.
3. **Assignment gate:** query `GET /repos/{org}/{repo}/issues?state=open&assignee={persona}&per_page=100`, then remove entries with a non-null `pull_request` field. The Issues API includes pull requests because GitHub models them as Issues.

Cache the credential and identity for the rest of the run. Do not use the local `gh auth status` login as the persona filter or as proof that comments will be authored by the persona.

## 2. The zero-queue branch is deliberately side-effect-free

If the filtered assignment list is empty:

- do not search broad `@mentions`, inspect closed Issues, or start PM orchestration;
- do not add comments, labels, assignments, or state files merely to announce the empty queue;
- finish with exactly `[SILENT]` and nothing else.

This is a successful poll, not a degraded one. The identity and repository gates still need to pass so that an auth or access failure is not mistaken for an empty queue.

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