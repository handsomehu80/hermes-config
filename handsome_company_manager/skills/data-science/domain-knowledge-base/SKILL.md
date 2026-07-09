---
name: domain-knowledge-base
description: "Build a structured, Git-friendly knowledge base for a domain (curriculum, regulations, medical protocols, API reference, legal contracts, etc.) using a multi-agent team. Use when the user wants a machine-readable + human-readable reference. Covers the full pipeline: research, design, schema+validator, content, visualization."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [knowledge-base, ontology, curriculum, schema, reference, data-model]
---

# Domain Knowledge Base Construction

Build a structured knowledge base as a **multi-file JSON dataset** that is:
- **Git-friendly** — single files under 5MB, diffable, no DB
- **Machine-readable** — JSON Schema validated
- **Human-readable** — auto-generated Markdown + HTML + knowledge graph
- **Extendable** — adding a new grade/subject requires only a new file

The pattern applies to any domain with hierarchical concepts (curricula, regulatory frameworks, technical specs, medical taxonomies). Worked example below is the China 1-6 primary school 语数英 curriculum; reuse the schema for other domains.

## When to use this skill

- User wants a structured knowledge base for a domain
- User has a "scope X across Y levels" pattern (grades, certifications, categories, versions)
- The domain has prerequisite relationships worth mapping
- Need a stable JSON source that humans can also read
- Will eventually want to query ("give me the 3rd-grade addition-with-carry concept and 5 example problems")

## When NOT to use

- The user just wants a flat list (use a single Markdown)
- Domain has no natural hierarchy (use a spreadsheet)
- Will be queried by an LLM agent (skip the schema work, just write the Markdown and use RAG)

## Pipeline (6 phases)

### Phase 1: Research (ast)

Two parallel research cards:
- **Domain structure** — official taxonomy, level/sub-level breakdown, counts per category
- **Schema inspiration** — 2-3 existing public datasets / schemas in the same domain, extract their key fields, recommend one

Output: 2 Markdown reports, each under 2000 words, in the kanban workspace.

### Phase 2: Design synthesis (PM)

Combine the two research outputs into a single design doc covering:
- Scope (what is in, what is out)
- Directory structure
- Node schema (with field rationale)
- Edge schema (relationship types)
- Content per subject/category (counts, breakdown)
- 5-stage implementation roadmap
- 3-5 decision points for the user

User approves the design before any implementation begins. Do not dispatch implementation on a "what do you think we should build?" question — get a design sign-off first.

### Phase 3: Schema + validator (eng)

Build the empty skeleton FIRST, before any content:
- Directory tree per the design
- `nodes.schema.json` (full JSON Schema with field constraints)
- `edges.schema.json`
- `tools/validate_kb.py` with: id uniqueness, dangling references, prerequisite DAG (topo sort + cycle detection), per-filter modes (`--subject`, `--grade`)

Why this order: the validator catches every mistake the content workers will make. Without it, content-level errors (cycle, dangling prereq) only surface at QA time, and you will be re-running content jobs.

### Phase 4: Content (ast, often multi-stage)

Pilot one slice (one grade or one category) and validate. Estimate total content count from research. Then fan out:

```
phase 1: A1 = schema + validator (eng)
phase 2: A2 = pilot grade (ast)   ─┐
phase 3: A3 = qa-validate pilot   ─┘
phase 4: B1 = remaining grades for subject A (ast)
phase 5: B2 = qa-validate B1
phase 6: C1 = subject B grade 1-2 (ast, parallel to C2)
phase 7: C2 = subject C grade 1-2 (ast, parallel to C1)
phase 8: C3 = qa-validate C1+C2
```

Do not run all content generation in one giant card. The LLM context window is the limit; 30-50 nodes per ast card is a good budget. Beyond that, quality drops and retries multiply.

### Phase 5: Visualization (ast or eng)

After content is in:
- **Markdown guide** — readable by teachers/students/parents, NOT JSON-aware
- **HTML version** — same content, navigable TOC, print stylesheet
- **Knowledge graph** — Mermaid or Graphviz, 6 subgraph blocks for 6 themes, color-coded

These can be one kanban card (PM-agent generates all three from the same source).

### Phase 6: Validation (qa, end-to-end)

Final pass:
- Run validator on entire dataset
- Count nodes/edges, verify per-grade distribution
- Check edge types balance (too many `prerequisite` and not enough `part_of`/`related` suggests the content worker does not know the schema)
- Spot-check 10 nodes manually for accuracy
- Verify all `prerequisite` chains are DAG (no cycles)

## Schema (reusable)

```json
{
  "id": "<domain>.g<level>.<slug>",
  "subject": "<domain-enum>",
  "grade": <int-level>,
  "title": "<中文标题>",
  "kind": "concept | lesson | exercise | standard",
  "description": "<markdown, 50-150 字>",
  "prerequisites": ["<id>", ...],
  "part_of": "<id>",
  "related": ["<id>", ...],
  "difficulty": 1-5,
  "cognitive_level": "了解 | 理解 | 掌握 | 应用",
  "standard_ref": "<official-code>",
  "textbook_versions": ["<editions>"],
  "tags": ["<free>"]
}
```

Edges (separate file):

```json
{ "from": "<id>", "to": "<id>", "type": "prerequisite | part_of | related | teaches | assesses" }
```

## Pitfalls (read these)

### LLM-generated MCQ answer text must match an option exactly

When generating multiple-choice questions via LLM, the `answer` field often comes back as a paraphrased value (e.g., `"6 个面"`) that does not match any option text (e.g., `"C. 6 个"`). The validator flags this; user cannot grade the question.

**Fix in the content card body:** explicitly require answer to be either `"A"`, `"B"`, `"C"`, `"D"` OR the full option text `"C. 6 个"`. Add to the QA checklist: "for every choice question, answer must be a substring of one option's text."

### LLM-generated explanations sometimes under-spec

If the spec says "explanation 30-80 字", workers will produce 24-29 字 explanations at the low end. Acceptable but mark as warning in QA; do not reject. Be flexible on length, strict on accuracy.

### Cross-references in description must use IDs

Workers will write descriptions like "需要先学 100 以内不进位加法" — the concept name in Chinese. That is a doc, not a reference. The validator cannot catch it. Push for: in the `prerequisites` field, use IDs (`math.g2.add.100_no_carry`), not names.

### Pool.json and by_concept/ drift

If you have `by_concept/<id>.json` files AND a `pool.json` aggregate, regenerate pool from by_concept after every fix. Hand-editing pool.json is a fast path to divergence.

### Topo check must be in the validator

A knowledge graph with cycles in `prerequisites` is broken (you cannot learn A to B to C to A). The validator must do topological sort + cycle detection. Do not trust content workers to write DAG-shaped data without checking.

### Do not trust the worker's "done" word

After 30+ minutes of generation, an LLM will sometimes claim "done" with 80% of the content. Always re-validate file counts and node counts after `kanban_complete` — do not trust the summary alone.

## Reference files

- `references/curriculum-2022-china.md` — China 2022 课标 structure summary (worked example)
- `templates/nodes-schema.json` — starter JSON Schema (drop in, customize `subject` enum)
- `templates/edges-schema.json` — starter
- `scripts/build_pool.py` — merge `by_concept/*.json` into `pool.json`
- `scripts/validate_kb.py` — full validator template (uniqueness, refs, topo, choice-answer match)

## Related skills

- `agent-team-orchestration` — for the multi-profile kanban team pattern
- `kanban-orchestrator` and `kanban-worker` (bundled) — for kanban mechanics
