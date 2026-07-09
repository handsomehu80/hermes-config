# Chinese Picture Book PDF — Pitfalls & Recipes

Hard-won knowledge from building an A4-landscape picture book PDF (24 pages,
19 entries, ~11 MB output) with ReportLab on Windows. Future agents save hours
by reading this first.

## 1. Chinese fonts on Windows

`C:/Windows/Fonts/` ships three fonts that Just Work for CJK without installing anything:

| File | Registered name | When to use |
|---|---|---|
| `simhei.ttf` | `SimHei` | **Headings, titles, body emphasis** — bold sans-serif, reads well small |
| `simsun.ttc` | `SimSun` | Body text, English — register as `SimSun` (TTC works in ReportLab) |
| `STKAITI.TTF` | `KaiTi` | Decorative body / poetry / quotes — brushstroke feel |

Register once at module load:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/simsun.ttc'))
pdfmetrics.registerFont(TTFont('KaiTi',  'C:/Windows/Fonts/STKAITI.TTF'))
```

## 2. Font glyph coverage — the silent killer

**Not every Unicode symbol renders in every Chinese font.** Verified on
SimHei / SimSun / KaiTi:

| Glyph | SimHei | SimSun | KaiTi | Use case |
|---|---|---|---|---|
| `★` (U+2605) | yes | yes | yes | **Always safe for decoration** |
| `→` (U+2192) | yes | yes | yes | Arrows, instructions |
| `〔 〕` (U+3014/3015) | yes | yes | yes | Quoted labels |
| `·` (U+00B7) | yes | yes | yes | Spacing between phrases |
| `—` (U+2014) | yes | yes | yes | Em-dash |
| `♪` (U+266A) | empty | empty | yes | **DO NOT use for music label** |
| `♫` (U+266B) | empty | empty | yes | Same family — only KaiTi |
| `❤` (U+2764) | empty | empty | empty | All fail |
| `☆` (U+2606) | yes | yes | yes | Outline star — OK |

**Rule of thumb:** if a symbol might be music/emoji/decorative, test it in a
throwaway render before committing. Use `★` for everything decorative — it
works everywhere. If you really need a music note, switch the surrounding
text to KaiTi font (but then it doesn't match the rest).

## 3. CJK text wrapping — ReportLab doesn't do it for you

`canvas.stringWidth` treats Chinese as a single width unit if you don't
manage lines yourself. Greedy char-by-char wrap is the safe default:

```python
def wrap_cjk(c, text, x, y, max_w, font, size, leading, color=None):
    if color is not None:
        c.setFillColor(color)
    c.setFont(font, size)
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        line = ''
        for ch in paragraph:
            test = line + ch
            if c.stringWidth(test, font, size) <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = ch
        if line:
            lines.append(line)
    cur_y = y
    for ln in lines:
        c.drawString(x, cur_y, ln)
        cur_y -= leading
    return cur_y  # y-coordinate of the line BELOW the last drawn line
```

For mixed CJK + English (e.g., a page header like "3月6日 · 晴"), wrap
by word-break for the English portion and character for CJK. Keep a
separate `wrap_en()` helper that splits on whitespace.

**Why not reportlab.platypus?** Platypus has `Paragraph` with CJK
support via `<font>` tags but the setup is heavier than canvas-based
work for a one-shot picture book. Stick with canvas + custom wrap.

## 4. Page layout — landscape A4 for picture books

For entries where the original artwork is landscape (e.g., 2528x1696 px
drawings from a kid's book), landscape A4 (842 x 595 pt) is the right
orientation. Don't fight it with portrait.

Layout pattern that worked:

```
+------------------------------------------------------+
| Date · Weather                          Theme       |  <- 20pt header band
+------------------------------------------------------+
|                              |                       |
|                              |   Polished text       |
|       IMAGE (framed)         |   in KaiTi 13pt       |
|       ~55% of page width     |                       |
|                              |                       |
|                              |                       |
|                              |                       |
|                              | ★ 推荐音乐            |  <- bottom-right
|                              | [Sun prompt text]     |
+------------------------------------------------------+
|                     -- page n --                     |
+------------------------------------------------------+
```

The 55/45 split (image vs text) lets a long paragraph breathe without
forcing the user to squint.

## 5. Decorative bands + page numbers — don't overlap

PDF y-coordinates grow UPWARD from the bottom edge. A common bug:

```python
# BAD — band drawn at y=14-18, page number drawn at y=22
#   baseline at 22 puts the text top at ~22 and bottom at ~14
#   -> text overlaps the band
c.rect(0, 14, PAGE_W, 4, fill=1, stroke=0)
c.drawCentredString(PAGE_W/2, 22, '-- 1 --')
```

**Fix:** put the page number FIRST (lowest y), then bands stacked ABOVE it:

```python
c.drawCentredString(PAGE_W/2, 10, '-- 1 --')   # page number
c.rect(0, 24, PAGE_W, 4, fill=1, stroke=0)     # orange band
c.rect(0, 32, PAGE_W, 2, fill=1, stroke=0)     # blue band
```

Or use a gap of at least 12pt between text baseline and band top.

## 6. Image fitting — preserve aspect, don't crop

Kid drawings have lots of whitespace from the original scan. Don't try
to "fill the frame" by stretching — let the whitespace be the frame.

```python
from PIL import Image as PILImage

def fit_image(c, img_path, x, y, max_w, max_h, frame=True):
    if frame:
        c.setStrokeColor(COL_LIGHT)
        c.setLineWidth(2)
        c.roundRect(x - 4, y - 4, max_w + 8, max_h + 8, 6, stroke=1, fill=0)
    pil = PILImage.open(img_path)
    iw, ih = pil.size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    cx = x + (max_w - w) / 2
    cy = y + (max_h - h) / 2
    c.drawImage(img_path, cx, cy, w, h,
                preserveAspectRatio=True, mask='auto')
```

## 7. Page count budget

For a typical 19-entry journal, the picture-book PDF lands at 24 pages:

- 1 cover
- 1 preface (卷首语)
- 1 table of contents (categorized)
- N entries (1 per entry, landscape)
- 1 farewell (卷尾寄语)
- 1 music index (last page, two-column prompt dump)

That's the minimum useful structure. Adding extra sections (gallery,
timeline, author bio) bloats fast — keep it tight for kids.

## 8. File size

A 24-page landscape A4 with embedded JPGs lands around **10-12 MB**.
That's fine for sharing. If size matters, run embedded images through
PIL with quality=85 before `c.drawImage`:

```python
pil = PILImage.open(src)
if pil.mode != 'RGB': pil = pil.convert('RGB')
pil.save(dst, 'JPEG', quality=85, optimize=True)
```

Don't go below 75 — kid drawings with crayon textures fall apart.
