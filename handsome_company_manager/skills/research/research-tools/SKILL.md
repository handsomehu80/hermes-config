---
name: research-tools
description: "Research toolkit: arXiv academic paper search and download (with Semantic Scholar citation context), blogwatcher RSS/Atom feed monitoring, Karpathy-style LLM Wiki (persistent interlinked markdown knowledge base with cross-references and lint), and Polymarket prediction-market queries (search markets, prices, orderbooks, history, trades). Class-level umbrella covering the four most common research operations."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, arxiv, papers, semantic-scholar, citations, rss, blogwatcher, feeds, monitoring, wiki, knowledge-base, karpathy, polymarket, prediction-markets, market-data]
---

# Research Tools

Class-level umbrella for the four most common research operations in Hermes. Each section below is a complete playbook for that domain — no need to load another skill.

## Quick decision table

| The user wants to… | Section |
|---|---|
| Find / download / read an arXiv paper, get citation context | [arxiv Papers](#arxiv-papers-search--download--citation-context) |
| Monitor blogs, RSS/Atom feeds, podcast feeds for new content | [Feed Monitoring (blogwatcher)](#feed-monitoring-blogwatcher) |
| Build a persistent, cross-linked markdown knowledge base from sources | [Knowledge Base (LLM Wiki)](#knowledge-base-llm-wiki-karpathy-pattern) |
| Look up prediction-market odds / Polymarket prices | [Prediction Markets (Polymarket)](#prediction-markets-polymarket) |

If unsure which applies, default to keywords the user used:
- "paper", "arxiv", "scholar", "citation", "published" → arxiv
- "feed", "rss", "monitor blog", "subscribe to", "new post" → blogwatcher
- "wiki", "knowledge base", "notes", "remember this", "ingest" → LLM Wiki
- "polymarket", "prediction market", "odds", "betting odds" → Polymarket

---

## arxiv Papers — search / download / citation context

Search and retrieve academic papers from arXiv via their free REST API. No API key, no dependencies — just `curl`. Pair with Semantic Scholar for citations, references, and recommendations.

### Quick reference

| Action | Command |
|---|---|
| Search papers | `curl "https://export.arxiv.org/api/query?search_query=all:QUERY&max_results=5"` |
| Get specific paper | `curl "https://export.arxiv.org/api/query?id_list=2402.03300"` |
| Read abstract (web) | `web_extract(urls=["https://arxiv.org/abs/2402.03300"])` |
| Read full paper (PDF) | `web_extract(urls=["https://arxiv.org/pdf/2402.03300"])` |
| Citation count | `curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=citationCount,influentialCitationCount"` |
| Helper script | `python scripts/search_arxiv.py "GRPO reinforcement learning" --max 10 --sort date` |

### Searching the arXiv API

Returns Atom XML. Parse with the helper script (`scripts/search_arxiv.py`) or inline Python:

```bash
curl -s "https://export.arxiv.org/api/query?search_query=all:GRPO+reinforcement+learning&max_results=5&sortBy=submittedDate&sortOrder=descending" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for i, entry in enumerate(root.findall('a:entry', ns)):
    title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
    arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
    print(f'{i+1}. [{arxiv_id}] {title}')
    print(f'   PDF: https://arxiv.org/pdf/{arxiv_id}')
"
```

### Query syntax

| Prefix | Searches | Example |
|---|---|---|
| `all:` | All fields | `all:transformer+attention` |
| `ti:` | Title | `ti:large+language+models` |
| `au:` | Author | `au:vaswani` |
| `abs:` | Abstract | `abs:reinforcement+learning` |
| `cat:` | Category | `cat:cs.AI` |
| `co:` | Comment | `co:accepted+NeurIPS` |

Boolean operators: `+` joins AND, `OR` for OR, `ANDNOT` for exclusion, `"..."` for exact phrase. Example: `au:hinton+AND+cat:cs.LG`.

### Sort and pagination

| Parameter | Values |
|---|---|
| `sortBy` | `relevance`, `lastUpdatedDate`, `submittedDate` |
| `sortOrder` | `ascending`, `descending` |
| `start` | Result offset (0-based) |
| `max_results` | Number of results (default 10, max 30000) |

### Common categories

| Category | Field |
|---|---|
| `cs.AI` | Artificial Intelligence |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `cs.LG` | Machine Learning |
| `cs.CR` | Cryptography and Security |
| `stat.ML` | Machine Learning (Statistics) |
| `math.OC` | Optimization and Control |
| `physics.comp-ph` | Computational Physics |

Full list: <https://arxiv.org/category_taxonomy>

### Helper script

`scripts/search_arxiv.py` handles XML parsing and provides clean output:

```bash
python scripts/search_arxiv.py "GRPO reinforcement learning"
python scripts/search_arxiv.py "transformer attention" --max 10 --sort date
python scripts/search_arxiv.py --author "Yann LeCun" --max 5
python scripts/search_arxiv.py --category cs.AI --sort date
python scripts/search_arxiv.py --id 2402.03300
python scripts/search_arxiv.py --id 2402.03300,2401.12345
```

No dependencies — stdlib only.

### Reading paper content

```bash
# Abstract page (fast, metadata + abstract)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper (PDF → markdown)
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# BibTeX generation: see the search_arxiv.py helper output, or curl + parse
curl -s "https://export.arxiv.org/api/query?id_list=1706.03762" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
root = ET.parse(sys.stdin).getroot()
entry = root.find('a:entry', ns)
if entry is None: sys.exit('Paper not found')
title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
authors = ' and '.join(a.find('a:name', ns).text for a in entry.findall('a:author', ns))
year = entry.find('a:published', ns).text[:4]
raw_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
print(f'@article{{{title.replace(\" \", \"_\")}_{year},')
print(f'  title = {{{title}}}, author = {{{authors}}}, year = {{{year}}}')
print(f'  eprint = {{{raw_id}}}, archivePrefix = {{arXiv}}')
print('}')
"
```

### Semantic Scholar — citations, references, recommendations

arXiv doesn't provide citation data. Use the **Semantic Scholar Graph API** (free, no key, 1 req/sec).

```bash
# Paper details + citations
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,referenceCount,influentialCitationCount,year,abstract" | python3 -m json.tool

# Who cited this paper
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,authors,year&limit=10" | python3 -m json.tool

# What this paper cites (references)
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/references?fields=title,authors,year&limit=20" | python3 -m json.tool

# Recommendations (POST with positive/negative paper IDs)
curl -s -X POST "https://api.semanticscholar.org/recommendations/v1/papers/" \
  -H "Content-Type: application/json" \
  -d '{"positivePaperIds": ["arXiv:2402.03300"], "negativePaperIds": []}' | python3 -m json.tool

# Author profile
curl -s "https://api.semanticscholar.org/graph/v1/author/search?query=Yann+LeCun&fields=name,hIndex,citationCount,paperCount" | python3 -m json.tool
```

Useful fields: `title`, `authors`, `year`, `abstract`, `citationCount`, `referenceCount`, `influentialCitationCount`, `isOpenAccess`, `openAccessPdf`, `fieldsOfStudy`, `externalIds` (contains arXiv ID, DOI, etc.).

### ID versioning — preserve the version you read

- `arxiv.org/abs/1706.03762` always resolves to the **latest** version.
- `arxiv.org/abs/1706.03762v1` points to a **specific** immutable version.
- When generating citations, preserve the version suffix you actually read — a later version may substantially change content.
- The API `<id>` field returns the versioned URL (e.g. `http://arxiv.org/abs/1706.03762v7`).

### Withdrawn papers

Papers can be withdrawn after submission. The `<summary>` field will contain a withdrawal notice. Always check the summary before treating a result as a valid paper — metadata may be incomplete.

### Rate limits

| API | Rate | Auth |
|---|---|---|
| arXiv | ~1 req / 3 seconds | None needed |
| Semantic Scholar | 1 req / second | None (100/sec with API key) |

### Complete research workflow

1. **Discover**: `python scripts/search_arxiv.py "your topic" --sort date --max 10`
2. **Assess impact**: `curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=citationCount,influentialCitationCount"`
3. **Read abstract**: `web_extract(urls=["https://arxiv.org/abs/ID"])`
4. **Read full paper**: `web_extract(urls=["https://arxiv.org/pdf/ID"])`
5. **Find related work**: `curl -s ".../paper/arXiv:ID/references?fields=title,citationCount&limit=20"`
6. **Get recommendations**: POST to Semantic Scholar recommendations endpoint
7. **Track authors**: `curl -s ".../author/search?query=NAME"`

---

## Feed Monitoring (blogwatcher)

Track blog and RSS/Atom feed updates with the `blogwatcher-cli` tool. Supports automatic feed discovery, HTML scraping fallback, OPML import, and read/unread article management.

### Install `blogwatcher-cli`

| Platform | Command |
|---|---|
| Go (any) | `go install github.com/JulienTant/blogwatcher-cli/cmd/blogwatcher-cli@latest` |
| Docker (named volume) | `docker run --rm -v blogwatcher-cli:/data -e BLOGWATCHER_DB=/data/blogwatcher-cli.db ghcr.io/julientant/blogwatcher-cli scan` |
| Linux amd64 binary | `curl -sL https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_linux_amd64.tar.gz \| tar xz -C /usr/local/bin blogwatcher-cli` |
| macOS Apple Silicon | Replace `linux_amd64` with `darwin_arm64` in the URL above |
| macOS Intel | Replace `linux_amd64` with `darwin_amd64` in the URL above |

DB lives at `~/.blogwatcher-cli/blogwatcher-cli.db` by default (lost on Docker container restart — use a volume).

**Migrating from old `Hyaxia/blogwatcher`:** rename `~/.blogwatcher/blogwatcher.db` → `~/.blogwatcher-cli/blogwatcher-cli.db`. Binary name changed from `blogwatcher` to `blogwatcher-cli`.

### Common commands

**Manage blogs:**
```bash
blogwatcher-cli add "My Blog" https://example.com
blogwatcher-cli add "My Blog" https://example.com --feed-url https://example.com/feed.xml
blogwatcher-cli add "My Blog" https://example.com --scrape-selector "article h2 a"  # HTML scrape fallback
blogwatcher-cli blogs
blogwatcher-cli remove "My Blog" --yes
blogwatcher-cli import subscriptions.opml   # bulk from OPML (Feedly/Inoreader/NewsBlur)
```

**Scan and read:**
```bash
blogwatcher-cli scan                  # all blogs
blogwatcher-cli scan "My Blog"        # one blog
blogwatcher-cli articles              # unread
blogwatcher-cli articles --all        # all
blogwatcher-cli articles --blog "My Blog"
blogwatcher-cli articles --category "Engineering"
blogwatcher-cli read 1                # mark read
blogwatcher-cli unread 1              # mark unread
blogwatcher-cli read-all              # mark all read
blogwatcher-cli read-all --blog "My Blog" --yes
```

### Environment variables

All flags have env equivalents with `BLOGWATCHER_` prefix:

| Variable | Purpose |
|---|---|
| `BLOGWATCHER_DB` | Path to SQLite database |
| `BLOGWATCHER_WORKERS` | Concurrent scan workers (default 8) |
| `BLOGWATCHER_SILENT` | Only print "scan done" |
| `BLOGWATCHER_YES` | Skip confirmation prompts |
| `BLOGWATCHER_CATEGORY` | Default article filter by category |

### Notes

- Auto-discovers RSS/Atom feeds when `--feed-url` isn't given.
- Falls back to HTML scraping if RSS fails and `--scrape-selector` is configured.
- Categories from feeds are stored and filterable.
- Import bulk from OPML files exported by Feedly, Inoreader, NewsBlur, etc.
- `blogwatcher-cli <command> --help` for all flags.

---

## Knowledge Base (LLM Wiki — Karpathy pattern)

Build and maintain a persistent, compounding knowledge base as interlinked markdown files. Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Unlike RAG (which rediscovers knowledge per query), the wiki **compiles** knowledge once and keeps it current — cross-references are already there, contradictions are flagged, synthesis reflects everything ingested.

**Division of labor:** Human curates sources and directs analysis. Agent summarizes, cross-references, files, and maintains consistency.

### When this activates

- User asks to create, build, or start a wiki or knowledge base
- User asks to ingest, add, or process a source into their wiki
- User asks a question and an existing wiki is present at the configured path
- User asks to lint, audit, or health-check their wiki
- User references their wiki, knowledge base, or "notes" in a research context

### Wiki location

Set via `WIKI_PATH` env var (e.g. in `~/.hermes/.env`). Default: `~/wiki`. The wiki is just a directory of markdown files — open in Obsidian, VS Code, or any editor. No database, no special tooling required.

### Architecture: three layers

```
wiki/
├── SCHEMA.md           # Conventions, structure rules, domain config
├── index.md            # Sectioned content catalog with one-line summaries
├── log.md              # Chronological action log (append-only, rotated yearly)
├── raw/                # Layer 1: Immutable source material
│   ├── articles/       # Web articles, clippings
│   ├── papers/         # PDFs, arxiv papers
│   ├── transcripts/    # Meeting notes, interviews
│   └── assets/         # Images, diagrams referenced by sources
├── entities/           # Layer 2: Entity pages (people, orgs, products, models)
├── concepts/           # Layer 2: Concept/topic pages
├── comparisons/        # Layer 2: Side-by-side analyses
└── queries/            # Layer 2: Filed query results worth keeping
```

- **Layer 1 — Raw Sources:** immutable. Agent reads but never modifies these.
- **Layer 2 — The Wiki:** agent-owned markdown files. Created, updated, cross-referenced by the agent.
- **Layer 3 — The Schema:** `SCHEMA.md` defines structure, conventions, and tag taxonomy.

### Resuming an existing wiki — ALWAYS orient first

When the user has an existing wiki, orient before doing anything:

1. Read `SCHEMA.md` — understand the domain, conventions, tag taxonomy.
2. Read `index.md` — learn what pages exist and their summaries.
3. Scan recent `log.md` (last 20–30 entries) — understand recent activity.

For large wikis (100+ pages), also `search_files` for the topic at hand before creating anything new. Skipping orientation causes duplicates and missed cross-references.

### Initializing a new wiki

1. Determine the wiki path (`$WIKI_PATH` or ask the user; default `~/wiki`)
2. Create the directory structure above
3. Ask the user what domain the wiki covers — be specific
4. Write `SCHEMA.md` customized to the domain
5. Write initial `index.md` with sectioned header
6. Write initial `log.md` with creation entry
7. Confirm the wiki is ready and suggest first sources to ingest

### SCHEMA.md template

```markdown
# Wiki Schema

## Domain
[What this wiki covers — e.g., "AI/ML research", "personal health", "startup intelligence"]

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `transformer-architecture.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** on pages synthesizing 3+ sources, append `^[raw/articles/source-file.md]`
  at the end of paragraphs whose claims come from a specific source. Optional on single-source pages.

## Frontmatter
  ```yaml
  ---
  title: Page Title
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | comparison | query | summary
  tags: [from taxonomy below]
  sources: [raw/articles/source-name.md]
  confidence: high | medium | low        # how well-supported the claims are
  contested: true                        # set when the page has unresolved contradictions
  contradictions: [other-page-slug]      # pages this one conflicts with
  ---
  ```
```

### Raw frontmatter

```yaml
---
source_url: https://example.com/article
ingested: YYYY-MM-DD
sha256: <hex digest of the raw content below the frontmatter>
---
```

The `sha256:` lets future re-ingest detect drift — recompute on re-ingest, skip if identical, flag drift if different.

### Page thresholds

- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside the domain
- **Split a page** when it exceeds ~200 lines
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

### Update policy — contradictions

1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report

### Core operation: ingest a source

1. **Capture the raw source** to `raw/<subdir>/<descriptive-name>.md` (URL → `web_extract`; PDF → `web_extract`; paste → save). Add raw frontmatter (`source_url`, `ingested`, `sha256`).
2. **Discuss takeaways** with the user (skip in automated/cron contexts).
3. **Check what already exists** — search `index.md` and `search_files` for the entities/concepts mentioned. The difference between a growing wiki and a pile of duplicates.
4. **Write or update wiki pages** following Page Thresholds, Update Policy, and cross-reference (every page links to ≥2 others via `[[wikilinks]]`).
5. **Update navigation** — add new pages to `index.md`, append to `log.md`: `## [YYYY-MM-DD] ingest | Source Title`.
6. **Report what changed** — list every file created or updated.

A single source can trigger updates across 5–15 wiki pages. This is normal — it's the compounding effect.

### Querying the wiki

1. Read `index.md` to identify relevant pages.
2. For wikis with 100+ pages, also `search_files` for key terms.
3. Read the relevant pages.
4. Synthesize an answer from compiled knowledge. Cite the wiki pages: "Based on [[page-a]] and [[page-b]]..."
5. File valuable answers back — if substantial comparison / deep dive / novel synthesis, create a page in `queries/` or `comparisons/`. Skip trivial lookups.
6. Update `log.md` with the query and whether it was filed.

### Lint checklist

1. **Orphan pages:** find pages with no inbound `[[wikilinks]]`.
2. **Broken wikilinks:** `[[links]]` pointing to non-existent pages.
3. **Index completeness:** every wiki page should appear in `index.md`.
4. **Frontmatter validation:** all required fields present, tags in taxonomy.
5. **Stale content:** pages whose `updated` date is >90 days older than the most recent source mentioning the same entities.
6. **Contradictions:** pages on the same topic with conflicting claims; surface `contested: true` / `contradictions:` frontmatter for review.
7. **Quality signals:** list pages with `confidence: low` or single-source claims without a confidence field.
8. **Source drift:** recompute sha256 of `raw/` files, flag mismatches.
9. **Page size:** flag pages >200 lines.
10. **Tag audit:** list all tags in use, flag any not in `SCHEMA.md` taxonomy.
11. **Log rotation:** if `log.md` exceeds 500 entries, rotate to `log-YYYY.md`.
12. **Report findings** grouped by severity (broken links > orphans > drift > contested > stale > style).
13. **Append to log.md:** `## [YYYY-MM-DD] lint | N issues found`.

### Bulk ingest

When ingesting multiple sources at once, batch the updates: read all sources first, identify entities across all, check existing pages for all (one search pass), create/update pages in one pass, update `index.md` once at the end, write a single log entry.

### Archiving

When content is fully superseded or domain scope changes: create `_archive/`, move page to `_archive/<original-path>`, remove from `index.md`, update any pages that linked to it (replace wikilink with plain text + "(archived)"), log the archive action.

### Obsidian integration

The wiki directory works as an Obsidian vault out of the box — `[[wikilinks]]` render as clickable links, Graph View visualizes the network, YAML frontmatter powers Dataview queries, `raw/assets/` holds images referenced via `![[image.png]]`. Set Obsidian's attachment folder to `raw/assets/`, install Dataview plugin for queries.

For headless machines, use `obsidian-headless` to sync the vault via Obsidian Sync without a GUI.

### Pitfalls

- **Never modify files in `raw/`** — sources are immutable.
- **Always orient first** — read SCHEMA + index + recent log before any operation.
- **Always update index.md and log.md** — these are the navigational backbone.
- **Don't create pages for passing mentions** — follow Page Thresholds.
- **Don't create pages without cross-references** — every page must link to ≥2 others.
- **Frontmatter is required** — enables search, filtering, staleness detection.
- **Tags must come from the taxonomy** — freeform tags decay into noise.
- **Keep pages scannable** — split pages >200 lines.
- **Ask before mass-updating** — confirm scope if ingest touches 10+ pages.
- **Rotate the log** when it exceeds 500 entries.
- **Handle contradictions explicitly** — don't silently overwrite.

---

## Prediction Markets (Polymarket)

Query prediction market data from Polymarket using their public REST APIs. All endpoints are read-only and require zero authentication.

### When to use

- User asks about prediction markets, betting odds, or event probabilities
- User wants to know "what are the odds of X happening?"
- User asks about Polymarket specifically
- User wants market prices, orderbook data, or price history
- User wants to monitor or track prediction market movements

### Quick reference

```bash
# Search markets
python scripts/polymarket.py search "election"

# Top trending by volume
python scripts/polymarket.py trending --limit 10

# Market details by slug
python scripts/polymarket.py market will-trump-win-2024

# Current price for a token (Yes/No)
python scripts/polymarket.py price 12345...

# Orderbook depth
python scripts/polymarket.py book 12345...

# Price history
python scripts/polymarket.py history 0xabc... --interval all --fidelity 50

# Recent trades
python scripts/polymarket.py trades --limit 10 --market 0xabc...
```

### Key concepts

- **Events** contain one or more **Markets** (1:many relationship).
- **Markets** are binary outcomes with Yes/No prices between 0.00 and 1.00.
- Prices ARE probabilities: price 0.65 means the market thinks 65% likely.
- `outcomePrices` field: JSON-encoded array like `["0.80", "0.20"]`.
- `clobTokenIds` field: JSON-encoded array of two token IDs [Yes, No] for price/book queries.
- `conditionId` field: hex string used for price history queries.
- Volume is in USDC (US dollars).

### Three public APIs

1. **Gamma API** at `gamma-api.polymarket.com` — Discovery, search, browsing.
2. **CLOB API** at `clob.polymarket.com` — Real-time prices, orderbooks, history.
3. **Data API** at `data-api.polymarket.com` — Trades, open interest.

Full endpoint reference with curl examples: see [`references/api-endpoints.md`](references/api-endpoints.md).

### Typical workflow

1. **Search** using the Gamma API public-search endpoint.
2. **Parse** — extract events and their nested markets.
3. **Present** market question, current prices as percentages, and volume.
4. **Deep dive** if asked — use `clobTokenIds` for orderbook, `conditionId` for history.

### Presenting results

Format prices as percentages for readability:
- `outcomePrices ["0.652", "0.348"]` → "Yes: 65.2%, No: 34.8%"
- Always show the market question and probability.
- Include volume when available.

Example: `"Will X happen?" — 65.2% Yes ($1.2M volume)`.

### Parsing double-encoded fields

The Gamma API returns `outcomePrices`, `outcomes`, and `clobTokenIds` as JSON strings inside JSON responses. In Python: `json.loads(market['outcomePrices'])` to get the actual array. The `scripts/polymarket.py` helper handles this for you.

### Rate limits

Generous — unlikely to hit for normal usage:

| API | Limit |
|---|---|
| Gamma | 4,000 req / 10 sec |
| CLOB | 9,000 req / 10 sec |
| Data | 1,000 req / 10 sec |

### Limitations

- Read-only — does not support placing trades.
- Trading requires wallet-based crypto authentication (EIP-712 signatures).
- Some new markets may have empty price history.
- Geographic restrictions apply to trading but read-only data is globally accessible.

---

## See also

- `obsidian` skill — if the user wants their wiki/notes in an Obsidian vault specifically (the wiki pattern is Obsidian-compatible out of the box; obsidian covers other vault operations).
- `domain-knowledge-base` skill — Jupyter-driven, structured knowledge bases in Python (different paradigm from the markdown wiki).
- `kanban-orchestrator` + `multi-profile-team` — for "research → write-up → review" multi-agent flows that hand research findings to a synthesis worker.
- `web_extract` — used heavily above for fetching arxiv abstracts, PDFs, and any URL.