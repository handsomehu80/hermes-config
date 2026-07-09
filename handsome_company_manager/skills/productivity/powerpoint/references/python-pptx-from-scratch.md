# Creating a deck from scratch with python-pptx

> Why this guide exists: the canonical "create from scratch" path in this
> skill is pptxgenjs (a Node tool). On hosts without Node.js, or when you
> want to stay inside one Python script you can version-control,
> python-pptx is a strong second option. It's already installed via
> `pip install python-pptx` (lighter than the markitdown stack) on most
> Hermes hosts and produces identical .pptx files.

## When to choose python-pptx over pptxgenjs

Pick python-pptx when:

- The host has Python but no Node.
- You want the deck builder script to live next to its content as a single
  `.py` file you can re-run and diff.
- The deck is content-heavy (dense text, comparison tables, structured cards)
  rather than chart-heavy or template-heavy.

Reach for pptxgenjs (see `pptxgenjs.md`) when:

- You need theme / master slides.
- The deck leans on native PowerPoint charts.
- A template is already in place and you're swapping content.

## Minimum skeleton

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

# 16:9
prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)

# blank layout = index 6 in default template
slide = prs.slides.add_slide(prs.slide_layouts[6])

# 1. background fill
bg = slide.background.fill
bg.solid()
bg.fore_color.rgb = RGBColor(0x0B, 0x1B, 0x33)

# 2. a helper that handles CJK font hint correctly
def set_run(run, *, text, size=18, bold=False, color):
    run.text = text
    run.font.name = 'Microsoft YaHei'
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    # critical for CJK: also set East-Asian typeface on rPr
    rPr = run._r.get_or_add_rPr()
    for tag in ('eastAsia', 'cs', 'ascii', 'hAnsi'):
        existing = rPr.find(qn(f'a:{tag}'))
        if existing is not None:
            rPr.remove(existing)
        etree.SubElement(rPr, qn(f'a:{tag}')).set('typeface', 'Microsoft YaHei')

# 3. add a title
tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.6),
                              Inches(12.3), Inches(1.0))
tf = tb.text_frame
tf.margin_left = Inches(0)
tf.margin_right = Inches(0)
p = tf.paragraphs[0]
set_run(p.add_run(), text='Hello World',
        size=40, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

prs.save('output.pptx')
```

## Patterns that pay off

### Sandwich structure (dark title / light content / dark conclusion)

Mix dark backgrounds on slide 1 and the final slide only. Mid-deck slides
use a near-white background (`F7F9FC`). This single design choice reads as
"premium deck" without any fancy graphics.

### One dominant color, one accent

Define your palette as 4-5 module-level constants at the top of the script:

```python
PRIMARY   = RGBColor(0x06, 0x5A, 0x82)  # 60% of shapes
SECONDARY = RGBColor(0x1C, 0x72, 0x93)  # 25%
ACCENT    = RGBColor(0xF7, 0xB7, 0x3C)  # <10%, for highlights
BG_DARK   = RGBColor(0x0B, 0x1B, 0x33)
BG_LIGHT  = RGBColor(0xF7, 0xF9, 0xFC)
TEXT_MUTE = RGBColor(0x4A, 0x55, 0x68)
```

Then every helper takes these. Re-skinning the deck becomes changing 6 lines.

### Reusable content-slide builder

```python
def build_content_slide(prs, *, slide_num, total, section, title, render):
    """render(slide) does the layout. Section bar + title are boilerplate."""
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG_LIGHT

    # top accent bar with section name (white text)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                             Inches(0), Inches(0),
                             Inches(13.333), Inches(0.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = PRIMARY
    bar.line.fill.background()
    # textbox overlay...
    render(s)
```

### Common shape recipes

| What you want              | How                                                                 |
|----------------------------|---------------------------------------------------------------------|
| Card with rounded corners  | `MSO_SHAPE.ROUNDED_RECTANGLE`, set `adjustments[0] = 0.10`          |
| Top stripe (color header)  | `MSO_SHAPE.RECTANGLE` strip + textbox overlay                        |
| Numbered bullet circle     | `MSO_SHAPE.OVAL` filled + centered textbox                           |
| Flow connector arrow       | `MSO_SHAPE.RIGHT_ARROW` filled with no line                          |
| Grid of equal-sized cards  | loop with `cell_w`, `cell_h`, `gap_x`, `gap_y` computed from slide W  |

### QA after build (when soffice is missing)

```python
from pptx import Presentation
p = Presentation('output.pptx')
print(f'slides: {len(p.slides)}')
for i, s in enumerate(p.slides):
    chars = sum(len(r.text or '')
                for sh in s.shapes if sh.has_text_frame
                for para in sh.text_frame.paragraphs
                for r in para.runs)
    print(f'  slide {i+1}: {len(s.shapes):3d} shapes, {chars:4d} text chars')
```

This catches truncation, blank slides, and gross overflow without rendering.
Real visual QA still needs the user to open the file in PowerPoint on hosts
where soffice is absent.

## Known sharp edges

- **Chinese / CJK titles fall back to a Western font** unless you also
  patch the East-Asian typeface via `lxml` (see skeleton above). This is
  the single most common bug — set it once in your helper.
- **`MSO_SHAPE.OVAL`** and other shapes inherit a default shadow; turn it
  off with `shp.shadow.inherit = False` to avoid dark halos.
- **`text_frame.paragraphs[0]`** is auto-created but its `runs` collection
  is empty — always `add_run()` rather than mutate it.
- **python-pptx has no "save & render" path, but on Windows you can fall back
  to PowerPoint COM via `win32com` without installing LibreOffice.** See the
  "Windows fallback" section in SKILL.md and the helper at
  `scripts/render_via_powerpoint.py`. It renders PNGs in seconds and handles
  CJK fonts correctly. Reserve `soffice + pdftoppm` for Linux/macOS hosts.

## Reference

Source script that exercises every pattern above:
`D:\explore\loop engineer\build_pptx.py` (11-slide Chinese AI/dev deck,
Ocean Gradient palette, sandwich structure).
