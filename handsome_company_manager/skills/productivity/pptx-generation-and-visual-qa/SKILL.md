---
name: pptx-generation-and-visual-qa
description: Generate a PPTX from scratch with python-pptx AND verify it visually by rendering to PNG. Covers Windows rendering via PowerPoint COM, file-lock pitfalls, and a self-check checklist for box/line overlap defects.
---

# PPTX Generation + Visual QA

End-to-end workflow for building a `.pptx` from scratch using `python-pptx`, then **proving it actually renders correctly** by rasterising to PNG and inspecting every slide. Covers the Windows path when LibreOffice is not available.

Use this skill whenever you need to:
- Build a presentation deck programmatically (not by hand-editing PowerPoint)
- Catch layout bugs (overlap, text overflow, hidden elements) before declaring done
- Render PPT → PNG for embedding in chat / markdown / reports

---

## When NOT to use this

- Reading or lightly editing an existing PPT — use the built-in `powerpoint` skill instead.
- Need pixel-perfect template work — use the `powerpoint` skill's template editing flow.
- The deliverable is a Google Slides or Keynote file — different toolchain entirely.

---

## Two-phase workflow

### Phase 1 — Build with python-pptx

1. **Pick a colour palette upfront.** Edit the four constants near the top of the build script (primary / secondary / accent / bg). Do not hard-code hex inside helper functions. Theme: dark navy / teal / gold accents on light bg, dark navy on cover/conclusion.
2. **Standardise geometry.** Fix slide size (16:9 = 13.333 × 7.5 in) and stick to a small number of standard boxes:
   - top bar: 0–0.5 in
   - title block: 0.8–1.7 in (left=0.5, width=12.5)
   - thin gold accent rect under title: top=1.72, height=35000 EMU
   - body region: 2.0–6.5 in
   - footer bar: 7.10–7.30 in
3. **Use the helper primitives** — `add_filled_rect`, `add_rounded_rect`, `add_textbox`, `add_page_footer`, `set_notes`. Don't drop raw `shapes.add_shape()` calls into body builders; route through helpers so coordinate maths stay consistent.
4. **Speaker notes** — for every content slide, fill `set_notes(slide, [...])` with 4–7 lines of 60–90s talk script. PowerPoint reads these from `slide.notes_slide.notes_text_frame`.
5. **Save → render → inspect → fix → re-save.** Don't try to QA by reading python-pptx object model; rendering reveals overlaps the AST cannot.

### Phase 2 — Render & Visual QA

#### A. Pick a renderer

| Env | Renderer |
|---|---|
| Linux/macOS server, no GUI | `soffice --headless --convert-to pdf` then `pdftoppm -jpeg -r 150` |
| Windows with Office installed | **win32com + PowerPoint** — pattern below |
| Neither | install `libreoffice` via `choco` on Windows or apt-get on Linux |

**On Windows use win32com** (PowerPoint COM automation). LibreOffice not required. See the `render_windows.py` pattern in the codebase (e.g. `D:\explore\loop engineer\render_slides.py`).

```python
import os, win32com.client as win32

ppt_app = win32.Dispatch('PowerPoint.Application')
ppt_app.Visible = 0          # hide window
ppt_app.DisplayAlerts = 0
deck = ppt_app.Presentations.Open(ppt_abs, ReadOnly=True, WithWindow=False)
for i in range(1, len(deck.Slides) + 1):
    deck.Slides(i).Export(out_path, 'PNG', 1600, 900)
deck.Close(); ppt_app.Quit()
```

#### B. PowerPoint file-lock pitfall (CRITICAL)

**win32com leaves the .pptx file locked if you don't clean up.** If a subsequent build fails with `PermissionError: [Errno 13]`, the previous COM session is still holding the file.

```bash
taskkill /F /IM POWERPNT.EXE   # Windows
sleep 2                        # give the OS time to release the lock
```

Always run this between regenerations if `python build_pptx.py` fails with permission error.

#### C. The Visual-QA checklist — search actively, don't confirm passively

For each slide image, ask in this order:

| # | Check | What it catches |
|---|---|---|
| 1 | **Title vs accent decoration collision** | Big quote marks / oversized glyphs overlapping title text |
| 2 | **Callout vs outer-frame border** | Caveat / tagline text rendered ON TOP of a rounded-rect border line |
| 3 | **Card-grid bottom edge vs callout bar** | 6 / 3 / 2 cards stacked, then a dark callout bar placed at the exact same y as the bottom row |
| 4 | **Two cards' heights vs anchor text** | Bottom anchor text rendering overlapping or touching the cards' rounded bottom corners |
| 5 | **Footer bar vs any element** | A horizontal element positioned in the 7.10–7.30 in band where the navy footer lives |
| 6 | **Bullet dot circles clipped** | `shape.add_shape(OVAL, …)` placed with some x offset that bleeds outside a card |
| 7 | **Slide-number "11/11" at very bottom** | Footer bar placed too low, causing the slide number text to be cropped |
| 8 | **Two-line wrapping of single-line labels** | E.g. Q2 question "?" on its own line, or driver headline wrapping while siblings fit |
| 9 | **Stacked rounded-rect accent rectangle** | A small accent rect overlapping a longer anchor / attribution line above it |
| 10 | **Big white-space gap** | Card height >> content height → unbalanced, fix by reducing cell_h |

**Drill-down catalog** for any "yes" answer above: see `references/visual-qa-patterns.md` for 13 patterns with **failure signature → root cause → fix recipe**, including non-PPT corollaries (gitignore comment syntax, Windows `ln -sf` failure, Python path handling on Windows). Use it as the "if-then-else" expansion of this 10-item list.

**Critical meta-rule:** After EVERY fix, **re-render and re-inspect the affected slide**. One fix often creates another overlap (Pattern 13 in the reference: "fix and pray is the failure mode that brings the user back saying 再仔细核对一下排版"). Minimum verification cadence:
- 1-3 fixes: re-render all slides in the affected section
- 4-6 fixes: re-render the entire deck
- 7+ fixes: re-render and consider the layout was fundamentally off — start over

---

## python-pptx pitfalls (gotchas actually hit)

- **East Asian font needs explicit hinting.** Microsoft YaHei won't render correctly if you only set `run.font.name`. Add an additional XML hint:
  ```python
  from pptx.oxml.ns import qn
  rPr = run._r.get_or_add_rPr()
  elem = etree.SubElement(rPr, qn('a:eastAsia'))
  elem.set('typeface', 'Microsoft YaHei')
  ```
- **Notes live at `slide.notes_slide.notes_text_frame`** — not on the slide itself. Add them after creating the slide.
- **EMU vs Inches.** `add_shape(..., left=Inches(0.5), width=Emu(20000))` is fine but inconsistent. Pick one and document it. 35000 EMU ≈ 0.038 in (a typical underline).
- **Z-order is add-order.** Last added shape is on top. If you want a callout *behind* a card, add it first.
- **`MSO_SHAPE.RECTANGLE` has a default 0.75pt black border.** For cards/strips, always do `shape.line.fill.background()` to hide it. Same for ROUNDED_RECTANGLE.
- **`MSO_SHAPE.ROUNDED_RECTANGLE`** has a generous default corner radius. Shrink with `shape.adjustments[0] = 0.10`.
- **`shape.shadow.inherit = False`** matters — by default, python-pptx adds drop shadows that ruin flat-design decks.

---

## Concrete shape recipes

### Title slide (dark)

```python
# left accent stripe
add_filled_rect(slide, left=Inches(0),    top=Inches(0),     width=Inches(0.45), height=SLIDE_H, fill_color=NAVY)
add_filled_rect(slide, left=Inches(0.45), top=Inches(0),     width=Inches(0.10), height=SLIDE_H, fill_color=GOLD)
# kicker (yellow caps, 14pt)
# title (white, 58pt bold)
# subtitle (ice blue, 22pt)
# gold underline + footer text
```

### Content slide (light)

```python
# top navy bar (0–0.5 in)
# section label (white, top-bar) + slide-number (ice, right-justified top-bar)
# title (midnight, 34pt bold)
# gold accent rect (left-of-title, 35000 EMU tall)
# ... body content from 2.0–6.5 ...
# navy footer bar (7.10–7.30) + label/slide-number in footer
```

### Two-column comparison

```python
# two cards: left=0.5 right=6.8, width=6.1 each, height=4.7, top=2.0
# top stripe (header background) at top=2.0 height=0.9
# header title (white 22pt bold) at left=card.left+0.2, top=2.05
# sub-header ("agent 的行为" line) below
# bullets: y starts at 3.05, step 0.85 each
# oval bullet dot at left=card.left+0.3, top=y+0.15, size 0.18 in
# text column at left=card.left+0.7, anchor='t'
```

### 6-card grid (2 rows × 3 cols)

```python
# card_w = 3.9, card_h = 2.0 (NOT 2.1 — see overlap pitfall #3)
# gap_x = 0.2, gap_y = 0.20
# number circle: oval at left+0.3 top+0.3, size 0.6
# title text: 17pt bold, anchored middle
# desc text: 12pt, anchored top, multi-line
```

### Timeline (vertical)

```python
# vertical thin line (20000 EMU wide) at left=1.7 from top=2.1 height=4.7
# oval dots at left=1.6 top=y+0.05, size 0.3 (so the line passes through the dot's middle)
# date column: left=0.5 right-aligned
# who+what+why text: left=2.1 width=10.7
```

---

## Verification (mandatory)

Before declaring done:

1. ✓ python-pptx lint passes (no syntax errors)
2. ✓ build script saves the .pptx successfully
3. ✓ render script produces one PNG per slide, all named `slide-NN.png`
4. ✓ Vision model inspects EVERY slide (don't skip even the cover) and reports `0` overlaps
5. ✓ `python -m markitdown deck.pptx` shows the expected titles / counts (sanity check content survived)
6. ✓ Last write: kill any zombie POWERPNT.EXE and re-render once to confirm idempotency

---

## Anti-patterns to avoid

- ❌ Inspecting the python-pptx tree in memory and concluding "looks fine" without rendering. The model shows what you expect, not what's there.
- ❌ Positioning an element at `top=Inches(x)` where `x` is the same as another element's bottom — they'll touch.
- ❌ Putting two text boxes on top of each other to "let them wrap nicely" — they collide.
- ❌ Using `MSO_SHAPE.RECTANGLE` for cards and forgetting to set `line.fill.background()` so the default 0.75pt black border shows up.
- ❌ Leaving `shape.shadow.inherit = True` and getting a drop shadow you didn't design.
- ❌ Saving without verifying the file lock state on Windows.
- ❌ Trusting one round of vision QA — one fix often creates another overlap; loop until clean.
- ❌ Treating "user said re-check the layout" as one-time feedback instead of encoding the deeper rule (always re-render after every fix; the first round of fixes is never the last).
