# Case Study: mdlinkcheck CLI Build (2026-06-03)

End-to-end validation of a 4-profile team (pm / eng / qa / ast) using the workflow described in the parent skill. This is the canonical "did it actually work" record — copied into the skill so future agents can pattern-match on real timings, real artifacts, and the real failure mode that surfaced the parent-link trap.

## The Task

User-facing request: "Implement a Python CLI tool that scans a markdown file for `[text](url)` links, sends HTTP HEAD to each, and reports broken ones."

## Cards Created (4-card chain)

```
T1 (ast)  research: markdown link parser libraries
T2 (eng)  implement mdlinkcheck CLI        parent=T1
T3 (qa)   write tests + regression          parent=T2
T4 (pm)   report to user                    parent=T3
```

## Real Timings (clock time, not LLM-thinking time)

| Card | Assignee | Run time | Wall clock | Outcome |
|------|----------|----------|------------|---------|
| T1   | ast      | 194s     | 21:36→21:39 | Recommended `markdown-it-py`; corrected the user's "mistune C-accelerated" assumption (v3.x is pure Python) |
| T2   | eng      | 625s + 147s re-spawn | 21:40→21:50 (block) → 21:56→21:58 (complete) | Shipped 337-line CLI, sample.md, 24 unit tests, 100% from-clean green. **Blocked with `review-required`** per its SOUL.md, then PM unblocked and eng re-spawned to complete. |
| T3   | qa       | 531s     | 21:59→22:08 | 30 additional tests, 54/54 combined green in 0.25s, coverage 55%→99% |
| T4   | pm       | 216s     | 22:08→22:12 | Summary report, 3 known limitations, 3 next-step options |

**End-to-end wall clock:** 21:35 → 22:12 = **37 minutes** for a complete research→implement→test→report cycle.

## Artifacts (where to look)

After T2:
```
C:/temp/mdlinkcheck/
├── mdlinkcheck.py            11,305 bytes  (337 lines: argparse + markdown-it-py + urllib HEAD)
├── sample.md                  1,669 bytes  (49 lines covering 7 link categories)
└── test_mdlinkcheck.py        7,286 bytes  (24 unit tests, no real network)
```

After T3 (qa additions):
```
C:/temp/mdlinkcheck/
├── mdlinkcheck.py
├── sample.md
├── test_mdlinkcheck.py        (eng's original 24 tests)
├── tests/
│   ├── __init__.py
│   └── test_mdlinkcheck.py    19,982 bytes  (qa's additional 30 tests)
└── .coverage
```

Real CLI run on sample.md:
```
Total: 12 | Valid: 3 | Failed: 3 | Skipped: 4 (mailto, tel, anchor, relative)
- 404:   httpbin.org/status/404
- timeout: httpbin.org/status/500
- DNS error: nonexistent-host-9k2x.invalid
```

## The Failure Mode That Surfaced the Trap

T2 (eng) called `kanban_block(reason="review-required: ...")` after shipping. T2's status went to `blocked`, NOT `done`. T3 (qa) was parent-linked to T2 and stayed in `todo` — the dispatcher's auto-promotion only fires on `done`, not `blocked`.

Symptoms:
```
✓ t_fcdac120  done      ast                   smoke-test
✓ t_34a6d8ab  done      ast                   T1: research
⊘ t_ba92f8b6  blocked   eng                   T2: implement     ← eng finished, but blocked
◻ t_84df770a  todo      qa                    T3: write tests   ← stuck, parent never reached done
◻ t_43616b33  todo      pm                    T4: report        ← ditto
```

PM unblocked:
```bash
hermes kanban unblock t_ba92f8b6 --reason "PM accept: code shipped at C:/temp/mdlinkcheck/, QA review (T3) will verify and unblock with verdict."
```

This re-spawned the eng worker. The worker read the comment thread, saw the work was done, called `kanban_complete` after 147s. T2 → `done`, T3 auto-promoted to `ready`, dispatcher picked it up. Total dead time: ~6 minutes (the wait + 147s re-spawn).

## What I'd Do Differently Next Time

Edit the eng profile's SOUL.md to use the `kanban_complete` + comment-marker pattern instead of `kanban_block(review-required)`:

```markdown
# In eng/SOUL.md — handoff convention
For review-required handoffs on cards with downstream children:
  1. Drop structured metadata + "review-required" marker into a kanban_comment
  2. Call kanban_complete (not kanban_block) so downstream auto-promotes
  3. Reviewer reads the comment thread to see the review-required flag

This avoids the parent-link trap documented in kanban-orchestrator pitfalls.
```

The other place this lesson lives: the `kanban-orchestrator` skill (Parent-link + review-required trap section) and `kanban-worker` skill (Review-required handoff trap section). All three cross-reference so a future session finds it no matter which skill loads first.

## What Worked Well

- 4-card dependency chain auto-promoted cleanly once the trap was unblocked
- Each worker's handoff comment was rich enough to read without re-doing the work
- ast's correction of the user's "C-accelerated" assumption was high-value unsolicited input
- qa found real edge cases (relative URLs, anchor links, mailto/tel, image syntax) that eng missed
- All 4 profiles ran on the same `MiniMax-M3` model — model differentiation is optional, not required

## What Could Be Improved

- Dispatch tick is 60s — a 15-30s tick would halve the wait between cards
- PM's unblock-and-respawn burned 147s of dead time; fixable in eng's SOUL.md as noted above
- No notification routing configured — user had to poll `hermes kanban list` manually
- The 4 cards ran essentially serially (each waited for the prior); for parallel work, multiple independent cards can fan out without parent links

## Reproduce This

To re-run a similar validation, the minimal recipe:
1. 4 profiles + Kanban dispatcher configured (Phases 1-4 of the parent skill)
2. Smoke test passes (Phase 5)
3. Create the 4-card chain with the body shapes from this case study, substituting your tool's requirements for the link-checker requirements
4. End-to-end wall clock of ~30-40 min is normal for a small CLI tool build with tests
