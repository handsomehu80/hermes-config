---
name: pdf-tools
description: "PDF tools: extract text from PDFs/scans (pymupdf, marker-pdf) AND edit PDF text/typos/titles (nano-pdf). Class-level umbrella for the most common PDF operations — read this first when the user mentions a PDF, then jump to the matching labeled section."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Documents, Extraction, OCR, Editing, Research, Productivity]
    absorbed_from: [ocr-and-documents, nano-pdf]
---

# PDF Tools

Class-level umbrella for the most common PDF operations. This skill folds together two previously separate skills (`ocr-and-documents` for text extraction, `nano-pdf` for text editing) — same domain, two distinct operations. Read the appropriate section below.

For **DOCX** use `python-docx` directly. For **PPTX** use the `powerpoint` skill. This umbrella covers **PDFs only**.

## Quick decision: which section do I need?

| The user wants to… | Section to load |
|---|---|
| Pull text, tables, images OUT of a PDF (scanned or text-based) | [Extract Text from PDFs](#extract-text-from-pdfs) |
| Fix a typo, change a title or date IN an existing PDF | [Edit PDF Text](#edit-pdf-text) |
| Split / merge / search / convert PDFs | [Extract Text from PDFs](#extract-text-from-pdfs) (pymupdf covers all of these natively) |

## When you have a URL, try `web_extract` first

If the PDF is reachable by URL:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies. Only use local extraction when: the file is local, `web_extract` fails, or you need batch processing.

---

## Extract Text from PDFs

**Quick start**:

```bash
# Lightweight, no models — works for text-based PDFs
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages

# Heavy OCR — needed for scanned PDFs, equations, complex layouts
python scripts/extract_marker.py document.pdf
python scripts/extract_marker.py document.pdf --json
python scripts/extract_marker.py scanned.pdf
python scripts/extract_marker.py document.pdf --use_llm
```

### Pick your extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| **Text-based PDF** | ✅ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ✅ |
| **Code blocks** | ❌ | ✅ |
| **Forms** | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ✅ |
| **Reading order detection** | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ |
| **EPUB** | ✅ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Default**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis. If the user needs marker-pdf capabilities but the system lacks ~5GB free disk:

> "This document needs OCR/advanced extraction (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can use `web_extract`, or I can try pymupdf which works for text-based PDFs but not scanned documents or equations."

### Install

```bash
pip install pymupdf pymupdf4llm
pip install marker-pdf
```

For marker-pdf, check disk space first:
```bash
python scripts/extract_marker.py --check
```

### Arxiv papers (special case)

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

### Split, merge, search (all pymupdf-native)

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")

# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")

# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

### Image-heavy PDFs (illustrated journals, scanned booklets)

When the PDF is a child's illustrated diary, family photo book, infographic collection, or any document where **the IMAGES carry the meaning** (not just the text), text extraction alone misses 80% of the content. Use the two-channel pattern:

```python
import pymupdf

doc = pymupdf.open("journal.pdf")
for i, page in enumerate(doc):
    text = page.get_text()           # channel 1: text layer
    images = page.get_images(full=True)
    for img in images:
        xref = img[0]
        base = doc.extract_image(xref)
        path = f"page{i+1:02d}.{base['ext']}"
        with open(path, "wb") as f:
            f.write(base["image"])
    if images:
        # vision analysis on the extracted image
        # ask: "Describe the drawing's content, colors, mood, and any text in it."
        pass
```

**Pitfall**: Some PDFs are full-page scans where the entire page IS one image. Skip the text channel entirely and rely on `vision_analyze` — or use `marker-pdf` for higher fidelity.

### Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned documents, equations, complex layouts — install only when needed
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use

---

## Edit PDF Text

For natural-language PDF edits — fix a typo, change a title, update a date on a specific page — use `nano-pdf` (pip-installable).

### Install

```bash
# Recommended (uv is already in Hermes)
uv pip install nano-pdf

# Or pip
pip install nano-pdf
```

### Usage

```bash
nano-pdf edit <file.pdf> <page_number> "<instruction>"
```

### Examples

```bash
# Change a title on page 1
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results' and fix the typo in the subtitle"

# Update a date on a specific page
nano-pdf edit report.pdf 3 "Update the date from January to February 2026"

# Fix content
nano-pdf edit contract.pdf 2 "Change the client name from 'Acme Corp' to 'Acme Industries'"
```

### Notes

- Page numbers may be 0-based or 1-based depending on version — if the edit hits the wrong page, retry with ±1
- Always verify the output PDF after editing (use `read_file` to check file size, or open it)
- The tool uses an LLM under the hood — requires an API key (check `nano-pdf --help` for config)
- Works well for text changes; complex layout modifications may need a different approach

---

## See Also

- `powerpoint` skill — for PPTX (not PDFs)
- `illustrated-journal-companion` skill — for the full pipeline of taking an illustrated PDF, polishing text, and producing multimedia companions (Suno music prompts + narration)
