"""
Picture Book PDF — Starter Template (Chinese)
=============================================

Builds a landscape-A4 picture book with: cover, preface, table of contents,
N entries (image-left + text-right + music reference), farewell, music index.

Based on the working build_pdf.py used to produce
'胡轩瑞的时光小册 . 优化有声版' (24 pages, ~11 MB).

Usage:
    1. Copy this file to your working directory.
    2. Replace ENTRIES with your own data: date, weather, theme, image
       filename, polished Chinese text, Suno music prompt.
    3. Drop matching images into ./images/ (or update DRAW_DIR).
    4. Run: python build_pdf.py
    5. Output: in the same directory.

Tested on Windows with ReportLab 4.x. Should work on macOS / Linux with the
same ReportLab install; only the font paths change.
"""

from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from PIL import Image as PILImage
import os

# ------------------------------------------------------------------
# Fonts — Windows paths; change to /System/Library/Fonts/ on macOS,
# /usr/share/fonts/ on Linux for these CJK families.
# ------------------------------------------------------------------
CHINESE_FONTS = {
    'SimHei': 'C:/Windows/Fonts/simhei.ttf',      # sans-serif, headings
    'SimSun': 'C:/Windows/Fonts/simsun.ttc',      # serif body / English
    'KaiTi':  'C:/Windows/Fonts/STKAITI.TTF',     # brushstroke / poetry
}
for name, path in CHINESE_FONTS.items():
    pdfmetrics.registerFont(TTFont(name, path))

# ------------------------------------------------------------------
# Page geometry
# ------------------------------------------------------------------
PAGE_W, PAGE_H = landscape(A4)        # 842 x 595 pt
MARGIN = 14 * mm

# ------------------------------------------------------------------
# Palette — warm cream + accents; tweak to taste
# ------------------------------------------------------------------
COL_BG     = HexColor('#FAF6EC')
COL_DARK   = HexColor('#2C3E50')
COL_ACCENT = HexColor('#E67E22')     # orange — primary accent
COL_BLUE   = HexColor('#3A7BC8')
COL_GREEN  = HexColor('#5DA271')
COL_PINK   = HexColor('#E96A8C')
COL_LIGHT  = HexColor('#EAE2D0')     # subtle frame border
COL_GREY   = HexColor('#7F8C8D')

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
DRAW_DIR = './images'                # one image per entry
OUT_PDF  = './picture_book.pdf'

# ------------------------------------------------------------------
# ENTRIES — replace with your own. Each entry is one picture-book page.
# Polish the text lightly: keep the original voice, add rhythm and
# sensory texture, do NOT replace child words with adult equivalents.
# Suno style prompts go in 'music'. See references/chinese-pdf-pitfalls.md
# for why we use '*' (not music note) as a decorative marker.
# ------------------------------------------------------------------
ENTRIES = [
    {
        'date': '3月6日', 'weather': '晴', 'theme': '探秘红色火星',
        'theme_group': '星际科技',
        'image': 'mars.jpg',
        'text': (
            '2012年，"好奇号"火星车飞过长长的星河，\n'
            '在火星上安家啦！\n'
            '它正在一寸一寸地探索红色星球的小秘密——\n'
            '咦？为什么火星红红的？\n'
            '原来，它的土里藏着一种叫"氧化铁"的小东西，\n'
            '我们平时看到的铁锈，也是这个颜色呢！\n'
            '火星呀火星，你到底还藏了多少有趣的小秘密？'
        ),
        'music': (
            "Children's storybook adventure, wonder and discovery, "
            "warm piano and glockenspiel, soft strings, 90 BPM, "
            "magical realism, Pixar-style innocence"
        ),
    },
    # ... add more entries
]


# ------------------------------------------------------------------
# Drawing helpers
# ------------------------------------------------------------------
def fill_bg(c):
    c.setFillColor(COL_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def draw_corner_stars(c):
    """Subtle decorative stars in corners (star works in all CJK fonts)."""
    c.setFillColor(COL_ACCENT)
    c.setFont('SimHei', 14)
    c.drawString(MARGIN, PAGE_H - MARGIN + 4, '*')
    c.drawString(MARGIN + 18, PAGE_H - MARGIN - 4, '.')
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 4, '*')
    c.drawRightString(PAGE_W - MARGIN - 18, PAGE_H - MARGIN - 4, '.')


def fit_image(c, img_path, x, y, max_w, max_h, frame=True):
    """Aspect-preserving image fit inside (x, y, max_w, max_h), optional frame."""
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


def wrap_cjk(c, text, x, y, max_w, font, size, leading, color=None):
    """Char-by-char greedy CJK wrap. Returns y below the last drawn line."""
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
    return cur_y


def wrap_en(c, text, x, y, max_w, font, size, leading, color=None):
    """Word-break wrap for English (used for Suno style prompts)."""
    if color is not None:
        c.setFillColor(color)
    c.setFont(font, size)
    words = text.split(' ')
    lines, line = [], ''
    for w in words:
        test = (line + ' ' + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    cur_y = y
    for ln in lines:
        c.drawString(x, cur_y, ln)
        cur_y -= leading
    return cur_y


# ------------------------------------------------------------------
# Page builders
# ------------------------------------------------------------------
def page_cover(c):
    fill_bg(c)
    # Top decorative band
    c.setFillColor(COL_ACCENT); c.rect(0, PAGE_H - 18, PAGE_W, 4, fill=1, stroke=0)
    c.setFillColor(COL_BLUE);   c.rect(0, PAGE_H - 26, PAGE_W, 2, fill=1, stroke=0)

    c.setFillColor(COL_ACCENT)
    c.setFont('SimHei', 44)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 70, '时光小册')  # <- title
    c.setFillColor(COL_DARK)
    c.setFont('KaiTi', 26)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 110, '. 优 化 版 .')
    c.setFillColor(COL_GREY)
    c.setFont('SimHei', 14)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 150, '2026.3 -- 2026.6')

    # Hero image — pick one of your entries as the cover visual
    hero = os.path.join(DRAW_DIR, ENTRIES[0]['image']) if ENTRIES else None
    if hero and os.path.exists(hero):
        fit_image(c, hero, MARGIN + 30, 70,
                  PAGE_W - 2 * MARGIN - 60, PAGE_H - 260, frame=True)

    # Bottom band + page number — page number BELOW bands to avoid overlap
    c.setFillColor(COL_BLUE);   c.rect(0, 32, PAGE_W, 2, fill=1, stroke=0)
    c.setFillColor(COL_ACCENT); c.rect(0, 24, PAGE_W, 4, fill=1, stroke=0)
    c.setFillColor(COL_GREY)
    c.setFont('SimHei', 10)
    c.drawCentredString(PAGE_W / 2, 10, '-- 1 --')


def page_preface(c, n):
    fill_bg(c); draw_corner_stars(c)
    c.setFillColor(COL_ACCENT); c.setFont('SimHei', 28)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 60, '卷 首 语')
    c.setFillColor(COL_DARK); c.setFont('KaiTi', 18)
    preface = [
        '童年是什么？',
        '童年是一幅画，画里有我们五彩的生活；',
        '童年是一首歌，歌里有我们的幸福和快乐。',
        '',
        '童年是快乐的，童年是无忧无虑的，童年是多姿多彩的。',
        '我们在这里，记录童年的精彩，留住美好的回忆。',
    ]
    y = PAGE_H - 130
    for ln in preface:
        c.drawCentredString(PAGE_W / 2, y, ln); y -= 36
    c.setFillColor(COL_GREY); c.setFont('SimHei', 10)
    c.drawCentredString(PAGE_W / 2, 20, f'-- {n} --')


def page_toc(c, n):
    """Groups entries by their 'theme_group' key into 2-column TOC."""
    fill_bg(c); draw_corner_stars(c)
    c.setFillColor(COL_ACCENT); c.setFont('SimHei', 28)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 60, '目  录')

    groups = {}
    for e in ENTRIES:
        g = e.get('theme_group', '日记')
        groups.setdefault(g, []).append((e['date'], e['theme']))

    col_w = (PAGE_W - 2 * MARGIN) / 2 - 10
    left_x = MARGIN + 10
    right_x = MARGIN + col_w + 30
    y = PAGE_H - 120
    for i, (title, items) in enumerate(groups.items()):
        col_x = left_x if i % 2 == 0 else right_x
        cur_y = y
        c.setFillColor(COL_ACCENT); c.setFont('SimHei', 16)
        c.drawString(col_x, cur_y, f'# {title}')
        cur_y -= 24
        c.setFillColor(COL_DARK); c.setFont('SimHei', 12)
        for date, theme in items:
            c.drawString(col_x + 20, cur_y, f'{date}  {theme}')
            cur_y -= 20
        y -= len(items) * 20 + 50

    c.setFillColor(COL_GREY); c.setFont('SimHei', 10)
    c.drawCentredString(PAGE_W / 2, 20, f'-- {n} --')


def page_entry(c, idx, entry, n):
    fill_bg(c); draw_corner_stars(c)

    # Header
    c.setFillColor(COL_ACCENT); c.setFont('SimHei', 16)
    c.drawString(MARGIN, PAGE_H - MARGIN - 4, f'{entry["date"]}  .  {entry["weather"]}')
    c.setFillColor(COL_DARK); c.setFont('KaiTi', 18)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 4, entry['theme'])

    c.setStrokeColor(COL_LIGHT); c.setLineWidth(1.5)
    c.line(MARGIN, PAGE_H - MARGIN - 18, PAGE_W - MARGIN, PAGE_H - MARGIN - 18)

    # Image (left ~55%)
    img_x = MARGIN
    img_y = 90
    img_w = PAGE_W * 0.55 - MARGIN
    img_h = PAGE_H - MARGIN - 40 - img_y
    img_path = os.path.join(DRAW_DIR, entry['image'])
    if os.path.exists(img_path):
        fit_image(c, img_path, img_x, img_y, img_w, img_h)

    # Text (right ~45%)
    text_x = PAGE_W * 0.55 + 10
    text_w = PAGE_W - MARGIN - text_x
    text_top = PAGE_H - MARGIN - 50
    wrap_cjk(c, entry['text'], text_x, text_top, text_w,
             'KaiTi', 13, 22)

    # Music reference (bottom-right) — use star not music note (see reference)
    music_y = 80
    c.setFillColor(COL_ACCENT); c.setFont('SimHei', 11)
    c.drawString(text_x, music_y, '*  推荐音乐')
    c.setStrokeColor(COL_ACCENT); c.setLineWidth(0.5)
    c.line(text_x + 86, music_y - 3, text_x + 156, music_y - 3)
    wrap_en(c, entry['music'], text_x, music_y - 18,
            text_w, 'SimSun', 8.5, 11, color=COL_GREY)

    c.setFillColor(COL_GREY); c.setFont('SimHei', 10)
    c.drawCentredString(PAGE_W / 2, 20, f'-- {n} --')


def page_farewell(c, n):
    fill_bg(c); draw_corner_stars(c)
    c.setFillColor(COL_ACCENT); c.setFont('SimHei', 28)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 60, '老师卷尾寄语')
    c.setFillColor(COL_DARK); c.setFont('KaiTi', 16)
    lines = [
        '每一幅画，都是一段小小世界。',
        '都被一个热爱生活的小小作者收进了笔尖。',
        '',
        '愿这本时光小书，陪他走过很长很长的路；',
        '愿每一笔、每一句、每一段旋律，',
        '都成为童年最亮的那颗星。',
    ]
    y = PAGE_H - 140
    for ln in lines:
        c.drawCentredString(PAGE_W / 2, y, ln); y -= 32
    c.setFillColor(COL_GREY); c.setFont('SimHei', 10)
    c.drawCentredString(PAGE_W / 2, 20, f'-- {n} --')


def page_music_index(c, n):
    """All Suno prompts in a compact 2-column reference on the last page."""
    fill_bg(c); draw_corner_stars(c)
    c.setFillColor(COL_ACCENT); c.setFont('SimHei', 24)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 50, '*   音 乐 索 引   *')
    c.setFillColor(COL_GREY); c.setFont('SimHei', 11)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 75,
                        '-- 复制任意一段到 suno.com -> Custom Mode -> Style of Music，即可生成 --')

    col_w = (PAGE_W - 2 * MARGIN - 20) / 2
    col1_x = MARGIN
    col2_x = MARGIN + col_w + 20
    block_h = 70
    c.setFont('SimSun', 8)

    for i, entry in enumerate(ENTRIES):
        col_x = col1_x if i % 2 == 0 else col2_x
        cur_y = PAGE_H - 110 - (i // 2) * block_h

        c.setFillColor(COL_ACCENT); c.setFont('SimHei', 11)
        c.drawString(col_x, cur_y, f'{entry["date"]}  {entry["theme"]}')
        cur_y -= 16

        c.setFillColor(COL_DARK); c.setFont('SimSun', 8)
        words = entry['music'].split(' ')
        line = ''
        for w in words:
            test = (line + ' ' + w).strip()
            if c.stringWidth(test, 'SimSun', 8) <= col_w - 4:
                line = test
            else:
                c.drawString(col_x, cur_y, line); cur_y -= 11
                line = w
        if line:
            c.drawString(col_x, cur_y, line)

    c.setFillColor(COL_GREY); c.setFont('SimHei', 10)
    c.drawCentredString(PAGE_W / 2, 20, f'-- {n} --')


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------
def build():
    c = canvas.Canvas(OUT_PDF, pagesize=landscape(A4))
    c.setTitle('Picture Book')
    c.setAuthor('Optimized Layout')

    n = 1
    page_cover(c);     c.showPage(); n += 1
    page_preface(c, n); c.showPage(); n += 1
    page_toc(c, n);    c.showPage(); n += 1
    for i, entry in enumerate(ENTRIES, start=1):
        page_entry(c, i, entry, n); c.showPage(); n += 1
    page_farewell(c, n);    c.showPage(); n += 1
    page_music_index(c, n); c.showPage(); n += 1

    c.save()
    size = os.path.getsize(OUT_PDF)
    print(f'OK -> {OUT_PDF}')
    print(f'    pages: {n - 1}')
    print(f'    size : {size:,} bytes  ({size/1024/1024:.1f} MB)')


if __name__ == '__main__':
    build()
