---
name: powerpoint
description: "Create, read, edit .pptx decks, slides, notes, templates."
license: Proprietary. LICENSE.txt has complete terms
platforms: [linux, macos, windows]
---

# Powerpoint Skill

## When to use

Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions "deck," "slides," "presentation," or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill.

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` (or python-pptx fallback — see QA) |
| Edit or create from template | Read [editing.md](editing.md) |
| Create from scratch | Read [pptxgenjs.md](pptxgenjs.md), or use python-pptx (already installed on most hosts — see `python-pptx-from-scratch.md`) |

---

## Reading Content

```bash
# Text extraction
python -m markitdown presentation.pptx

# Visual overview
python scripts/thumbnail.py presentation.pptx

# Raw XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

---

## Editing Workflow

**Read [editing.md](editing.md) for full details.**

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

---

## Creating from Scratch

**Read [pptxgenjs.md](pptxgenjs.md) for full details.**

Use when no template or reference presentation is available.

---

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone. Consider ideas from this list for each slide.

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic. If swapping your colors into a completely different presentation would still "work," you haven't made specific enough choices.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent. Never give all colors equal weight.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content ("sandwich" structure). Or commit to dark throughout for a premium feel.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it — rounded image frames, icons in colored circles, thick single-side borders. Carry it across every slide.

### Color Palettes

Choose colors that match your topic — don't default to generic blue. Use these palettes as inspiration:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines

### Typography

**Choose an interesting font pairing** — don't default to Arial. Pick a header font with personality and pair it with a clean body font.

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- 0.5" minimum margins
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't skimp on size contrast** — titles need 36pt+ to stand out from 14-16pt body
- **Don't default to blue** — pick colors that reflect the specific topic
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning lines or shapes with text edges, set `margin: 0` on the text box or offset the shape to account for padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light text on light backgrounds or dark text on dark backgrounds
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides; use whitespace or background color instead

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step. If you found zero issues on first inspection, you weren't looking hard enough.

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

### Visual QA

**Don't re-render your own output without fresh eyes.** You've been staring at the code and will see what you expect. The fastest fix in this skill's setup is the built-in `vision_analyze` tool over each rendered PNG — pass it the file path and a defect-hunting prompt (see below). It is good enough for the typical 10-15 slide deck. Only escalate to a subagent when you need many eyes on many images in parallel, or a slide-by-slide rubric across 30+ slides.

Convert slides to images (see [Converting to Images](#converting-to-images)), then prompt `vision_analyze`:

```
Visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images:
1. /path/to/slide-01.jpg (Expected: [brief description])
2. /path/to/slide-02.jpg (Expected: [brief description])

Report ALL issues found, including minor ones.
```

### Verification Loop

1. Generate slides → Convert to images → Inspect
2. **List issues found** (if none found, look again more critically)
3. Fix issues
4. **Re-verify affected slides** — one fix often creates another problem
5. Repeat until a full pass reveals no new issues

**Do not declare success until you've completed at least one fix-and-verify cycle.**

For a deeper **pattern catalog** of overlap / cut-off / misalignment bugs (failure signature → root cause → fix recipe for 13 common patterns), see `references/visual-qa-patterns.md`. Load that reference when `vision_analyze` flags something but you don't immediately recognize the shape — it's the "if-then-else" expansion of this verification loop.

---

### Converting to Images

Convert presentations to individual slide images for visual inspection:

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

This creates `slide-01.jpg`, `slide-02.jpg`, etc.

To re-render specific slides after fixes:

```bash
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

### When `soffice` / `pdftoppm` are NOT available

Visual QA depends on LibreOffice + Poppler. On bare Windows hosts or minimal Linux containers these may be missing. Detect early and fall back:

1. Probe first: `which soffice && which pdftoppm`. If either is `not found`, skip image conversion.
2. **Content QA alternative** — use python-pptx (already a dependency, no install needed):
   ```python
   from pptx import Presentation
   p = Presentation('output.pptx')
   for i, s in enumerate(p.slides):
       chars = sum(len(r.text or '')
                   for sh in s.shapes if sh.has_text_frame
                   for para in sh.text_frame.paragraphs
                   for r in para.runs)
       print(f'slide {i+1}: {len(s.shapes)} shapes, {chars} text chars')
   ```
   This catches missing content and obvious overflow without rendering images.
3. **Skip markitdown install if it times out** — `pip install markitdown[pptx]` can exceed 120s on slow hosts. python-pptx content extraction (above) is a faster substitute when you only need text + shape counts.

#### Windows fallback: render via PowerPoint COM (no LibreOffice needed)

On Windows machines where Microsoft Office is installed but LibreOffice/pdftoppm are not, you can render PPTX → PNG directly via the `win32com` client (pywin32) talking to PowerPoint. This is the path that actually works on typical Hermes Windows hosts — Office ships by default but LibreOffice rarely does. Visual QA does NOT require telling the user to render locally.

Probe:
```python
import win32com.client as win32  # pywin32 - usually pre-installed on Windows
ppt = win32.Dispatch('PowerPoint.Application')
ppt.Visible = 0
ppt.DisplayAlerts = 0
deck = ppt.Presentations.Open(abs_path, ReadOnly=True, WithWindow=False)
for i, slide in enumerate(deck.Slides, start=1):
    slide.Export(out_png_path, 'PNG', width_px, height_px)
deck.Close()
ppt.Quit()
```

`slide.Export(...)` accepts any reasonable resolution (e.g. 1600×900 or 1920×1080 for 16:9). It correctly handles CJK fonts, smart art, gradients, transparency — anything that renders natively in PowerPoint.

Use the helper: `python scripts/render_via_powerpoint.py <pptx> <out_dir>` (see `scripts/`). Add it to your QA loop and you can find layout issues (text wrap, overlap, overflow) immediately via `vision_analyze` on the PNGs.

If `win32com` import fails, install with `python -m pip install pywin32` (fast — precompiled wheel). Do NOT spend time on `choco install libreoffice` (multi-GB download) when PowerPoint is already there.

4. Tell the user the file is built and ask them to render locally in PowerPoint for full visual QA. Do NOT block delivery waiting for LibreOffice.
5. Optional: install LibreOffice on Windows via `choco install libreoffice` (if choco is present) — slow but one-shot.

---

## Dependencies

- `pip install "markitdown[pptx]"` - text extraction
- `pip install Pillow` - thumbnail grids
- `npm install -g pptxgenjs` - creating from scratch
- LibreOffice (`soffice`) - PDF conversion (auto-configured for sandboxed environments via `scripts/office/soffice.py`)
- Poppler (`pdftoppm`) - PDF to images

## Pitfalls

- **`pip install markitdown[pptx]` can exceed 120s** on slow Windows hosts with cold caches. Set a 60-120s timeout and fall back to `python-pptx` content extraction (see "When `soffice` / `pdftoppm` are NOT available") if install hangs.
- **Don't assume `soffice` exists.** Run `which soffice` before promising visual QA. On user Windows hosts without LibreOffice, you'll get a clean error from the helper script — that's the cue to fall back, not to keep retrying. On Windows, the actual rendering fallback is **PowerPoint COM via `win32com`** (see Windows fallback section above) — Office is almost always installed even when LibreOffice is not.
- **Extending `python-pptx` style helpers is a multi-site edit.** If you add a kwarg like `italic` to a `set_run(...)` helper, every existing call site that uses positional style continues to work, but every call site that uses the new kwarg by name will need the kwarg in the helper signature. With `skill_manage patch` you must patch the helper AND each call site in separate operations; bundle them into one patch when possible.
- **Chinese / CJK text in titles needs explicit East-Asian font hint.** Setting `run.font.name = 'Microsoft YaHei'` is not enough on some renderers — also patch the East-Asian typeface via `lxml.etree.SubElement` on `rPr/eastAsia`. Without this, title blocks fall back to a Western font and look wrong.
- **Long Chinese strings silently wrap to 2 lines inside narrow cards.** A card 4" wide carrying an 18pt headline like "Agent 单次运行时长到了临界点" will wrap mid-phrase, breaking 3-column symmetry that looked perfect in code. Inspect every multi-column row in the rendered PNGs — shorten headlines, drop to 14-16pt, or widen the card before shipping.
- **Bottom callout / footer at `7.20in` clips on a 7.5in slide** in some renderers and word-wraps at the wrong line. Anchor footer at `7.10in` with a thin rect (`Emu(20000)`) and put text top at `7.16in` to leave a 0.4in safe margin. Same rule for any "next steps" callout — give it its own card with at least 0.3in clearance from the footer.
- **Accent/badge rectangles placed near attribution text overlap silently** in the rendered output. Always give decorative overlays ≥0.3in clearance from any textbox above them, especially when the textbox autosizes downward.
- **Speaker notes are NOT visible on the slide itself.** Fill them via `slide.notes_slide.notes_text_frame` (set `font.name = 'Microsoft YaHei'`, 11pt, after `add_slide()`). They appear in PowerPoint's "Notes Page" view and in exported PDF notes pages. Every deck meant to be presented should have them — keep each slide's notes in a dict keyed by slide number.
- **`slide.Export(...)` via win32com renders identically to opening the file in PowerPoint.** Don't bother also rendering with soffice as a "second opinion" — it substitutes fonts and shifts CJK glyphs, so any disagreement means nothing. Trust the COM render for QA.
- **Lingering `POWERPNT.EXE` locks the .pptx file after a COM render crashes or is killed mid-run.** Subsequent saves fail with `PermissionError: [Errno 13]`. The script's `deck.Close()` and `app.Quit()` don't release the file handle when the Python process is interrupted (Ctrl-C, OOM, exception in `Export`). If you try to overwrite and get `[Errno 13] Permission denied`, the COM ghost is still holding it. Kill it before retrying: `taskkill /F /IM POWERPNT.EXE` (Windows) or `pkill -f POWERPNT` (macOS/Linux). After that the next `python build_pptx.py` + render cycle works. Wrap renders in `try/finally` + force `Quit()` if you script long batch jobs.
- **Vision-model QA needs at least two rounds to catch real issues.** The first vision_analyze pass on a deck almost always returns "looks fine" because the prompt is too generic. That is the cue to sharpen the prompt on round two: ask specifically for boxes overlapping text, lines crossing words, accent rectangles colliding with attribution, footers cut off at the slide edge, empty space unbalance between columns. For a 10+ slide deck, budget for 2 fix-and-verify cycles before declaring done. Generic prompts confirm what you expected to see; overlap/clipping prompts reveal what you didn't.
