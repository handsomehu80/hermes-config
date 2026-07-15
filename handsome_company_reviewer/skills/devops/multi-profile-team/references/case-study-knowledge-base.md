# Case Study: 小学生 1-6 年级 主科 3 门 知识库 (2026-06-04)

Second end-to-end validation of the 4-profile team, this time on a **content/data** task (educational knowledge base) rather than a **code** task (mdlinkcheck). Demonstrates that the team pattern generalizes — and surfaces the pilot-first workflow as the right shape for content-heavy builds.

## The Task

User-facing request: "Build a knowledge base for Chinese elementary school (1-6 grade) main subjects (语文/数学/英语), aligned to 2022 课标. Agent team should think about how to design it."

## Card Graph (2 parallel research → synthesis → 3 sequential build)

```
T1 (ast)  research 课标结构 (1-6 年级 3 学科)  ─┐
                                               ├─→ T3 (pm) synthesize design doc
T2 (ast)  research 开源 KB schema  ─────────────┘
A1 (eng)  数据建模 + validate 脚本 (skeleton)  ─┐
                                               ├─→ A3 (qa) 验证数学 1-2 试点
A2 (ast)  数学 1-2 年级 30-50 概念 (pilot)  ───┘
```

**Key differences from the 4-card chain:**
- T1 + T2 are **parallel** (no parent link) — independent research lanes
- T3 is parent-linked to both T1 and T2, so it auto-promotes only when both arrive
- A1 + A2 are **parallel** — the skeleton doesn't block the pilot data
- A3 is parent-linked to A2 — verify the pilot, not the skeleton

This is the **pilot-first pattern** from the parent SKILL.md: build the smallest viable slice end-to-end, prove the validation flow works, then scale.

## Real Timings

| Card | Assignee | Run time | Wall clock | Outcome |
|------|----------|----------|------------|---------|
| T1   | ast      | 194s     | (parallel with T2) | Curriculum structure doc, 1-6 grade math 220-280 / chinese 350-450 / english 150-200 concept estimates |
| T2   | ast      | 359s     | (parallel with T1) | Compared Khan topictree / OpenStax CNX / 100tal / schema.org; recommended "Khan 树 + schema.org 语义" hybrid, 18-line TS interface |
| T3   | pm       | (synthesis, done in main session) | 12.8 KB design doc | `knowledge-base-design.md` with schema, directory layout, 5-phase roadmap |
| A1   | eng      | 1721s + 60s respawn | 20:21→20:50 + respawn | Built `C:/temp/kb/` skeleton: README, schema files, validate_kb.py |
| A2   | ast      | 1475s    | 20:22→20:47 (ran parallel with A1) | Wrote 39 math 1-2 nodes + 77 edges covering 6 themes (20以内加减 / 表内乘除 / 100以内加减 / 平面立体图形 / 时分元角分 / 位置方向分类). Also wrote a partial `validate_kb.py` (because A1 wasn't done) |
| A3   | qa       | 332s     | 20:48→20:53 | Ran `python tools/validate_kb.py` → exit 0. 39 nodes match schema, 50/50 prereqs resolved, topo OK, coverage report for the 6 themes |

**End-to-end wall clock:** T1/T2/T3 in the orchestration session (~10 min LLM time), then A1+A2+A3 ran in ~32 min wall clock (most of it concurrent A1+A2).

**Validate script modes verified manually:**
- `python tools/validate_kb.py` → 0 errors, 39 nodes, 77 edges
- `python tools/validate_kb.py --check-topo` → topological order OK across 51 edges
- `python tools/validate_kb.py --grade 1 --subject math` → 39 nodes match filter

## Artifacts (where to look)

```
C:/temp/kb/
├── README.md              3.4 KB, knowledge base overview
├── nodes.schema.json      4.9 KB, full JSON schema
├── edges.schema.json      1.9 KB
├── subjects/
│   ├── chinese/README.md
│   ├── math/README.md
│   │   └── g1/
│   │       ├── nodes.json 24 KB, 39 nodes
│   │       └── edges.json 17 KB, 77 edges
│   └── english/README.md
├── exercises/schema.md
├── standards/README.md
└── tools/validate_kb.py   ~150 lines, schema + topo + filter

C:/Users/Administrator/AppData/Local/hermes/plans/knowledge-base-design.md  12.8 KB design doc (T3 synthesis)
```

## What Worked Well

- **T1+T2 parallel research was the right move.** Two ast workers hit different sources in parallel; T3 had both deliverables to synthesize from. ~5-7 min saved vs serial.
- **A1+A2 parallel build.** The skeleton doesn't actually need to be done before the pilot data — ast wrote its own partial validate script when A1 wasn't ready, and the eng's later A1 delivery merged cleanly. A2's worker noted this and adapted.
- **Pilot-first caught the validation flow early.** A3 found that the schema was strict (good) and the data was clean (good). When phases B/C start, the validation pipeline is proven — no surprise rework at scale.
- **All 4 profiles ran on the same `MiniMax-M3` model.** The 39-node math 1-2 dataset is a content task where model quality matters less than the prompt; using the same model is fine. ast might benefit from a faster/cheaper model later, but no need to differentiate yet.
- **PM's T3 synthesis was done in the orchestration session, not as a Kanban card.** For small synthesis tasks (under ~3k tokens), it's faster to synthesize inline than to spin up a worker. The line is fuzzy; the 4-card pattern kicks in when synthesis needs its own context + tool access.

## What Could Be Improved

- **A1 and A2 both wrote to `validate_kb.py`** — A1's version won because it was the original assignee, but A2's partial work was wasted. For future parallel builds where two workers might both touch the same file, add a "single writer" rule to the dispatch body: "if file X exists when you start, read it first, don't overwrite."
- **A1 eng called `kanban_block(review-required)` → A3 had to wait for PM unblock → eng re-spawn wasted 60s.** Same trap as the mdlinkcheck case study. The fix (eng SOUL.md uses `kanban_complete` + comment marker for review-needed handoffs) is documented but not yet applied to this user's eng profile.
- **Dispatcher tick is 60s.** For Phase A's quick validations, a 15s tick would feel snappier. Lowered via `hermes config set kanban.dispatch_interval_seconds 15` if this user wants lower latency.
- **`smart` approval mode blocked `execute_code` in workers** — A2's worker wanted to run `validate_kb.py` itself but couldn't, so it asked the user to run it manually. A3 (qa) got past this somehow (maybe ran it during its own session). The workaround: if a worker role routinely needs to run scripts, set `approvals.mode: off` for that profile, not globally.
- **The full scope is 4-6 sessions of work** (math 1-6, chinese 1-6, english 1-6, plus validate). The pilot-first pattern is exactly the right discipline: prove the loop on math 1-2 (1 session), then fan out the rest.

## Reuse the Pattern

For any **content/data build with strict validation needs** (taxonomies, product catalogs, training data, documentation graphs), this is the shape:
1. T1+T2 parallel: domain research + format/schema research
2. T3 pm: design synthesis
3. A1+A2 parallel: build validation skeleton + build pilot data
4. A3 qa: validate pilot
5. (Repeat B/C/D for scaled data batches)

Total pilot cost: ~1 session (32 min wall clock + synthesis). Scaling cost per batch: ~1 session each, all parallelizable.

## See Also

- Parent SKILL.md → "Workflow Variants → Pilot-first" for the abstraction
- `templates/pilot-first.sh` for the executable recipe
- `references/case-study-mdlinkcheck.md` for the simpler 4-card chain (no parallel lanes, no pilot)
