# PM Mode Research — Canonical Report Skeleton

Use this template after parallel subagent delegation in PM Mode (see SKILL.md §PM Mode: Team-Led Strategic Analysis). Each section has a length budget and format guidance.

---

## 0. Short Conclusion (≤200 字)

Lead with the answer, not the buildup. The boss wants the punchline first. End with a numeric score (e.g., "X / 10") or a concrete recommendation.

---

## 1. Context / Definition Frame (table-heavy)

A 2-4 row comparison or definition table. Name the layers, the actors, the dates. The boss thinks in tables, not prose.

---

## 2. Technical Mechanism (the "how it works" section)

Lead with the pseudocode or core diagram. Then a table of the 3-5 decision points that determine quality. For each: what it decides, how to engineer it, failure symptom.

---

## 3. Relative Comparison to Previous Paradigm (the "delta" section)

Pick 3 specific scenarios (e.g., single bug / long task / multi-agent). For each: old approach vs new approach vs the engineering delta. Always end with a one-sentence summary.

---

## 4. Trend / Industry Pulse (data-driven)

Cite real numbers from real sources (AIEWF, Greptile, Sonar, CodeRabbit, etc.). Three reading angles: ratio / gap / trend. Always include the citation URL inline.

---

## 5. Risk Picture (concrete cases, not platitudes)

| Failure category | Real incident | Implication |
|---|---|---|

Minimum 5 rows. Each incident must be sourced (issue tracker, post-mortem, talk, paper). Avoid generic risks — every row must be a real event.

---

## 6. Fit-to-Our-Architecture (scoring)

Score each Loop Engineering component (or analogous framework component) against our 1+N system. Include a "max gap" identification (the single missing piece). End with numeric total (X / 10).

---

## 7. Improvement Roadmap (Phase 1 / 2 / 3 with cost & risk)

A table with: measure / what / why / cost / risk. Order by ROI. Distinguish 必做 (must-do) vs 建议 (recommended) vs 可选 (optional). Phase 1 = 0-30 days, Phase 2 = 30-60, Phase 3 = 60-90.

---

## 8. Three Next-Step Options (A/B/C table for boss)

| Option | What I'd do | Time | Boss's cost |
|---|---|---|---|

Always offer three: usually (A) write GitHub Issues for team to pick up async, (B) implement myself and deliver code, (C) draft a training / planning artifact. Pick concrete deliverables, not abstract tasks.

**Stop after this section.** Do not auto-execute. Boss picks by letter.

---

## 9. Citations

Numbered list. URL + one-line contribution. Minimum 5 citations for any non-trivial analysis. Only URLs that were actually fetched via `web_extract` / `web_search` during this task.

---

## Output Style Reminders

Boss's communication style (per user profile):

- **Extremely terse Chinese** ("在干什么", "approve", "先看看b", "作张图")
- Wants execution + delivered artifact, not discussion
- Decision-making: one-word direction when given a menu
- **Hates approval/permission friction** — once "approve" given, proceed without re-asking
- Workflow preference: condensed A/B/C tables with time/quality/limitations, picks by letter or content

Format guidance for PM Mode reports:

- **Tables > prose** for any comparison
- **Citations inline** when used, full list at end (not footnoted)
- **Real URLs**, not paraphrases of URLs
- **Stop and ask** at decision points — don't auto-pick
- **No fluff intros** like "Let me start by..." — go straight to substance
- **No boilerplate conclusions** like "In conclusion, AI is changing..." — end with the concrete next move