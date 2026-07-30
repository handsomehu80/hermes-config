---
name: pm-bi-hourly-data-quality
description: "Data-accuracy pitfalls specific to the PM bi-hourly status report — GitHub API shape quirks, file-tail discriminator rules, and recipe corrections that prevent silent corruption of report content."
version: 1.0.0
parent_skill: oneplusn
metadata:
  hermes:
    tags: [pm-operations, status-report, data-quality, github-api, drift-detection]
---

# PM Bi-Hourly Data-Quality Pitfalls

Addendum to `references/pm-bi-hourly-status-report.md`. Two pitfalls discovered during PM bi-hourly runs that are **silent data corruptions** — the report looks fine but the numbers are wrong. Future PM bi-hourly runs must internalize both.

---

## DQ-1. PR `additions`/`deletions` return 0 from list endpoint, real values from detail endpoint (learned 2026-07-29, PM #186 bi-hourly run)

**Symptom**: §1 进度矩阵 shows `+0 -0` for every PR even when the PRs obviously contain large commits. Real case (PM #186): PR #13 / #14 / #15 / #18 all came back as `+0 -0` from the list endpoint, but the actual values are `+917 / +435 / +901 / +1091` — if you only used the list endpoint, the §7 Δ表 and §1 detail rows would be silently wrong, and the boss would have no idea PR #13 carries 917 lines of validation report.

**Cause**: GitHub REST API `/repos/<org>/<repo>/pulls?state=all` (the **list** endpoint) returns the PR summary object, which has `additions=0, deletions=0, changed_files=0, commits=0` for *every* PR regardless of real diff size. This is documented GitHub behavior: the list endpoint deliberately omits diff stats for performance. Only `/repos/<org>/<repo>/pulls/<N>` (the **detail** endpoint) populates these fields, and only when called per-PR.

**Fix** (mandatory for any bi-hourly report that uses line counts):

```python
def gh_api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "oneplusn-pm-poll"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 1. List endpoint — for state/head/title only
prs_list = gh_api("/repos/<org>/<repo>/pulls?state=all&per_page=100")

# 2. Per-PR detail fetch — for additions/deletions/changed_files/commits/comments/review_comments/mergeable
prs_detail = []
for pr in prs_list:
    n = pr['number']
    d = gh_api(f"/repos/<org>/<repo>/pulls/{n}")
    prs_detail.append(d)  # now has real +N/-N/files=N values
```

**Alternative** (use `gh` CLI when account is clean): `gh pr list --json number,additions,deletions,changedFiles` — `gh` CLI proxies to the detail endpoint per row and returns real values. But this requires the `gh` CLI account to match the persona (see DQ-2 below for why that's a problem in practice).

**Verification**: after the loop, assert `sum(p.get('additions', 0) for p in prs_detail) > 0` for any repo with real PRs. If the sum is exactly 0 and there are non-empty PRs, the list endpoint was used and you have the bug.

---

## DQ-2. `[SILENT` (no closing `]`) is a valid silent-exit, not drift (learned 2026-07-29, PM #186 bi-hourly run)

**Symptom**: dev task-polling outputs in `<profile_home>/cron/output/<task-polling-job-id>/` end with `[SILENT\n` — the closing `]` is missing because the LLM trimmed it on token boundaries. The §5 #3 exclusion in the main SKILL.md says "the final response after `## Response` marker is exactly `[SILENT]`", which would mistakenly classify this as drift and trigger a false-positive PM-direct-action alert.

**Real case (PM #186)**: dev `42173ac76d3f` (828 files) and rev `3bab1b6dc5a3` (834 files) — dev tail consistently ends `[SILENT\n` (missing closing `]`), rev tail consistently ends `[SILENT]\n` (clean). Both are correct silent-exits, just with slightly different LLM tokenization. Without the lenient check, dev would be flagged as drifted every cycle.

**Fix** — replace the strict `[SILENT] == tail` check with a flexible regex:

```python
import re

# Strict (current main SKILL.md §5 #3 wording)
is_silent_strict = tail.strip() == "[SILENT]"

# Lenient (this fix) — accept [SILENT] OR [SILENT (no closing bracket, with newline-tail)
is_silent_lenient = bool(re.search(r"\[SILENT\]?\s*$", tail.rstrip()))

# Use is_silent_lenient for drift classification. Only flag as drift if the tail
# contains something OTHER than [SILENT] (or [SILENT+whitespace).
```

**Companion rule**: when the LLM emits `[SILENT]`, sometimes the closing `]` lands on the next line as a lone char, or the whole bracket is dropped. Both are semantically equivalent — the LLM correctly chose the silent-exit protocol. The drift discriminator is "did the LLM continue past `[SILENT]` with content?" — a verbose investigation report is drift; bare `[SILENT` followed by EOF is correct.

**Test**: when you encounter a `42173ac76d3f`-style output (dev profile), do NOT panic-remove the cron job or escalate. Tail-check with the lenient regex, classify as `healthy-idle`, and move on.

---

## DQ-3. Cross-check `gh` CLI account vs urllib.request token (already known, see skill #15 / #17)

When the PM cron runs on a Windows host where `gh auth status` returns the **boss** account (`handsomehu80`) instead of PM (`Handsome-Manager`), every `gh issue list` / `gh pr list` call in the cron LLM context will return the boss's view of the repo. This is the root cause of the §5 #23 "stale-claim deadlock" pattern: cron fires, LLM dumps skill content, never actually calls `gh`, never notices the wrong account.

The fix is to **always build reports via `urllib.request` + the profile's `.env` token**, bypassing `gh` entirely. The identity probe (`GET /user` → assert `login == expected`) MUST be the first API call in every bi-hourly cycle.

This is already documented in `references/pm-bi-hourly-status-report.md` §2.4 and the main SKILL.md Known Fix #17. Re-stating here because DQ-1 and DQ-2 both rely on it — without the urllib.request path, you can't even detect DQ-1 (PR line counts) reliably.

---

## When to Load This File

- Every PM bi-hourly cron fire (paired with `pm-bi-hourly-status-report.md`)
- When debugging "report looks fine but numbers are obviously wrong" complaints
- When tuning the §5 #3 drift discriminator (the lenient [SILENT] regex lives here, not in the main skill)
- When the boss asks "why does dev's cron output have `[SILENT` instead of `[SILENT]`?"