---
name: research-tools
description: "Research toolkit: arXiv papers (search/extract), blogwatcher (RSS/Atom feed monitoring), llm-wiki (Karpathy knowledge-base building + cross-linked markdown), polymarket (prediction-market queries). Class-level umbrella for the four most common research operations — pick the labeled section that matches the task."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, arxiv, rss, feeds, wiki, knowledge-base, prediction-markets]
---

# Research Tools

Class-level umbrella for the four most common research operations in Hermes. This skill is the **discovery index** — it's not meant to be loaded as a whole. Each section below names a deeper skill you should actually load for the task.

| The user wants to… | Section to load |
|---|---|
| Search / download arXiv papers, extract full text | [Arxiv Papers](#arxiv-papers) |
| Monitor RSS / Atom feeds from blogs / papers / podcasts | [Monitor Feeds (blogwatcher)](#monitor-feeds-blogwatcher) |
| Build a persistent, cross-linked markdown knowledge base from any source | [Build a Knowledge Base (llm-wiki)](#build-a-knowledge-base-llm-wiki) |
| Look up prediction-market odds / Polymarket prices | [Prediction Markets (Polymarket)](#prediction-markets-polymarket) |

Each section is **a pointer to the dedicated skill**, not a replacement. The dedicated skills (arxiv, blogwatcher, llm-wiki, polymarket) are kept as standalone skills with full SKILL.md content. Use this umbrella only when the user mentions "research" generically and you need to pick the right one.

---

## Arxiv Papers

**Use the `arxiv` skill** when the user asks:

- "Find me a paper on X" / "search arxiv for Y" / "latest arxiv on Z"
- "Summarize this arxiv paper: <URL or ID>"
- "Download this arxiv PDF"
- "What's trending on arxiv this week?"

The `arxiv` skill wraps `web_search` + `web_extract` + (optional) `hf` for HuggingFace-distributed checkpoints. No local install needed.

Quick start:

```
# Search abstracts
web_search(query="arxiv GRPO reinforcement learning 2026")

# Read abstract page
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Read full PDF
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
```

For full workflows (date filters, citation export, batch download), load the `arxiv` skill directly.

---

## Monitor Feeds (blogwatcher)

**Use the `blogwatcher` skill** when the user asks:

- "Watch this blog for new posts" / "monitor this RSS feed"
- "Cron job: check Hacker News every 4 hours"
- "Alert me when a specific author publishes"
- Any RSS / Atom / JSON-feed monitoring question

The `blogwatcher` skill uses the local `blogwatcher-cli` (Python) binary — install once, then add subscriptions like:

```bash
blogwatcher add "https://blog.example.com/feed.xml" --name "Example Blog"
blogwatcher add "https://export.arxiv.org/rss/cs.AI" --name "arxiv cs.AI"
blogwatcher list
blogwatcher check   # pull latest from all subscriptions
```

For batch subscription patterns, cron integration, or watch-and-summarize pipelines, load the `blogwatcher` skill directly.

---

## Build a Knowledge Base (llm-wiki)

**Use the `llm-wiki` skill** when the user asks:

- "Build me a knowledge base" / "start a wiki on X"
- "Ingest this article / paper / transcript into my wiki"
- "What does my wiki say about X?"
- "Lint my wiki" / "find broken links in my wiki"
- References an existing wiki at `$WIKI_PATH`

`llm-wiki` implements Karpathy's persistent-compounding-KB pattern: ingest sources once, get cross-linked markdown pages with provenance, contradictions flagged, and queries that compile rather than re-discover. It's a workflow skill — the agent reads, writes, and maintains the wiki across sessions.

For wiki structure, ingestion flow, lint rules, and Obsidian integration, load the `llm-wiki` skill directly.

---

## Prediction Markets (Polymarket)

**Use the `polymarket` skill** when the user asks:

- "What are the odds of X happening?" / "what does Polymarket say about Y?"
- "List current markets on topic Z"
- "Show me price history for market <id>"
- Orderbook or trade-flow questions about Polymarket specifically

The `polymarket` skill queries the public REST APIs (Gamma / CLOB / Data) — all read-only, zero auth, generous rate limits.

Quick start:

```bash
# Search markets via Gamma API
curl -s "https://gamma-api.polymarket.com/markets?search=election" | jq
```

For the full endpoint reference, probability formatting, and double-encoded field parsing, load the `polymarket` skill directly.

---

## See Also

- `obsidian` skill — if the user wants their wiki/notes in an Obsidian vault specifically (llm-wiki is Obsidian-compatible out of the box; the obsidian skill covers other Obsidian operations)
- `domain-knowledge-base` skill — Jupyter-driven, structured knowledge bases in Python (different paradigm from llm-wiki's markdown wiki)
- `kanban-orchestrator` + multi-profile-team — for "research → write-up → review" multi-agent flows that hand research findings to a synthesis worker
