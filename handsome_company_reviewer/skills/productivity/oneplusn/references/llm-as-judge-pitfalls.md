# LLM-as-Judge / Evaluator Pitfalls

Captured from a real cron tick (2026-07-13 21:46, reviewer) running the Issue #10 Ralph loop PoC end-to-end. The PoC uses an LLM as the "evaluator" sub-agent that reads a fresh-context set of evidence (git diff, scratchpad, test output) and returns a PASS / NEEDS_WORK verdict. Several fragility modes emerged that apply broadly to any LLM-as-judge verifier pattern, not just Ralph loop.

## Pitfall 1 — Verdict / reason text disagreement (first-word parsing is fragile)

The `poc/evaluator.sh` (line 69-71) parses the evaluator's reply by taking the **first word** of the `result` field:

```python
text = str(raw.get("result") or "").strip()
first = text.splitlines()[0].strip().upper() if text else ""
verdict = "PASS" if first == "PASS" else "NEEDS_WORK"
```

This works as long as the LLM consistently writes its verdict keyword on the first line. **It does not always.** Observed in the actual run on Issue #10 (`evaluator-raw.json`):

```json
"result": "\n\nPASS\n\n## 证据\n\n**验收标准逐项核对：**\n\n...\n\n**结论：** 文档本身完全满足规范,但 scratchpad 状态表明 builder 尚未真正执行 `hello_test.sh` 并将结果记录到 scratchpad 中——这属于验收标准第 5 项的缺失。由于验收标准明确要求\"运行并记录验证结果\",而现有证据中无此证据,应判定为 NEEDS_WORK。"
```

- First word after `.strip()`: `PASS` → verdict recorded as PASS
- Last paragraph: "应判定为 NEEDS_WORK" → human reading would conclude NEEDS_WORK
- Loop exits 0 (PASS), the next issue gets queued, but the actual work wasn't truly done per the evaluator's own reasoning

This is a **silent false-negative in reverse** — the verifier said "this looks OK on the surface, but really isn't, here's why" and the parser trusted the surface word. The loop closes successfully and downstream processes trust the verdict.

**Fix options:**

1. **Structured JSON output.** Force the evaluator to return a JSON object: `{"verdict": "PASS", "reason": "...", "issues": [...]}` — and parse it as JSON, not as text. LLM structured outputs are not 100% reliable but are far more parseable than free text + first-word heuristic.
2. **Two-section format with parser-side consistency check.** Require `## Verdict` line + `## Reasoning` section, then assert that no `NEEDS_WORK` / `BLOCK` / `REJECT` keywords appear inside the Reasoning section when verdict is PASS. If inconsistency, force verdict to NEEDS_WORK + reason = "verdict/reason inconsistent, please human review".
3. **Pre-commit sanity check.** In `evaluator.sh`, after parsing verdict, run a second-pass LLM call (much cheaper: "does this reasoning text actually support PASS? yes/no") and OR the two verdicts.

**Practical recommendation:** option 1 + option 2 combined. Structured JSON for machine consumption, two-section text for human readability, parser-side consistency check as safety net.

## Pitfall 2 — `>verifier-budget-exceeded` sentinel format (aspirational vs actual)

PM and Issue body referenced `>verifier-budget-exceeded` as the expected sentinel for budget-cap events (markdown blockquote with a machine-readable sentinel name, intended for a future Iron Rule #7 programmatic detector). The **actual** implementation in `poc/ralph-loop.sh` (line 273-279) writes a markdown **heading**:

```bash
{
  printf '## Ralph loop 预算熔断\n\n'
  printf -- '- Issue：#%s\n' "$ISSUE_NUMBER"
  printf -- '- 轮次：%s\n' "$ITERATION"
  printf -- '- 累计费用：`%s USD`\n' "$TOTAL"
  printf -- '- 预算上限：`%s USD`\n\n' "$BUDGET_USD"
  printf '%s\n' '外层 loop 已在启动 evaluator 前停止，未继续产生调用。'
} > "$COMMENT_FILE"
```

A programmatic detector doing `grep '^>verifier-budget-exceeded'` will miss this entirely. This is a real gap between the documentation contract and the implementation. Iron Rule #7 ("per-tick spend cap, gateway-enforced, violation interrupts the tick") cannot be enforced by an external detector without changing the implementation.

**Fix:** add the sentinel as the **first line** of the budget-exceeded comment, before the human-readable body. Belt-and-suspenders:

```bash
{
  printf '%s\n' '>verifier-budget-exceeded'
  printf '%s\n' ''
  printf '%s\n' '## Ralph loop 预算熔断'
  ...
} > "$COMMENT_FILE"
```

The sentinel line is what the detector matches; the heading is what humans see. Same approach applies to other verifier events (e.g. `>verifier-needs-work`, `>verifier-stop-requested`, `>verifier-max-iterations`).

**This pattern (sentinel + human-readable body in one comment) is the recommended template for any verifier system that needs both machine detection and human readability.** Document the sentinel set in the verifier's prompt + the detector's regex side, and never let one drift from the other without an update to both.

## Pitfall 3 — Verifier prompt rigidity ("first iteration PASS" doesn't validate the verifier itself)

The 7-test unit suite (`tests/test_ralph_loop.py`) exercises:

- 1 builder + 1 evaluator → PASS path (exit 0, state right)
- 2 builders + NEEDS_WORK → max iterations path (exit 3)
- `stop` keyword in Issue comment → early termination (exit 4)
- budget exhaustion before evaluator → exit 2
- remaining budget below CLI minimum → evaluator skipped
- scratchpad template has 4 required sections
- evaluator's `--disallowedTools` includes Write/Edit (with a captured-claude fixture)

**What it does NOT exercise:** that the evaluator's verdict is correct when the builder's work is genuinely incomplete. The fake evaluator hardcodes PASS or NEEDS_WORK based on `FAKE_EVAL_VERDICT` env var — there's no "real LLM disagreed with itself" test case. So Pitfall 1 (verdict/reason disagreement) cannot be caught by the existing suite.

**Fix:** add a test case that mocks a real LLM disagreement pattern (e.g. fake evaluator returns `"PASS\n\n## 证据\n\n...结论:应判定为 NEEDS_WORK"`) and assert that the parser detects the inconsistency and downgrades to NEEDS_WORK. This is a 10-line test addition.

## Cross-Reference

- `git-push-and-self-close.md` — the related workflow for landing verifier reports as deliverables; if your verifier flags a failed PoC, the report itself still needs to land in the repo before the issue closes.
- Known Fixes #9 (employee PAT access) — verifier cron output is delivered to the same place as cron output; access failures will mask verifier results as `[SILENT]`.