---
name: illustrated-journal-companion
description: "Process existing illustrated journals, diaries, or sketchbooks (PDF or image set) and produce (1) lightly polished text that preserves the original voice, (2) multimedia companions such as Suno music prompts per page, and (3) optional narrated mp3s (TTS reading + background music + mixed output). Use when the input is real artwork + handwritten or typed notes, not when generating new illustrations."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [journal, illustrated-diary, child-art, music-companion, suno, multimedia, tts, audiobook, ffmpeg]
    related_skills: [ocr-and-documents, songwriting-and-ai-music, baoyu-comic, baoyu-article-illustrator]
triggers:
  - child illustrated diary
  - sketchbook with notes
  - journal or portfolio enhancement
  - add music to drawings
  - 一日一画
  - 画册配乐
  - 把日记做成有声绘本
  - 有声画册
  - mp3 narration
  - audiobook from PDF
---

# Illustrated Journal Companion

For when someone hands you an **existing** illustrated document — a child's
"一日一画" booklet, a family travel journal with photos, a student science
portfolio — and asks you to enhance it (polish text, add music, make it
shareable). The output is a polished companion, NOT new artwork.

## When to use

Trigger on requests like:
- "我孩子有一本画册日记，能帮我润色+配音乐吗"
- "Add music to my daughter's sketchbook"
- "把这本日记做成有声绘本"
- "Optimize this daily-drawing PDF and match music to each page"

**Do NOT use** when:
- The user wants NEW illustrations for an article → use `baoyu-article-illustrator`
- The user wants a NEW knowledge comic generated → use `baoyu-comic`
- The user wants to extract text from a scanned document → use `ocr-and-documents` directly

## Core principles

1. **Preserve voice above all.** The child's / author's authentic language
   is the value. Polish is rhythm and sensory texture — NOT vocabulary
   upgrade or "improvement." If a sentence would lose its charm with an
   adult word, leave the kid word in.
2. **Visual-first.** The IMAGE carries the emotional weight. Always analyze
   the visual before/aside from the text. A "Mars with rover" page's
   pinyin text alone won't tell you it's a red planet drawing.
3. **Per-page is the unit.** Each page is one entry: image + text + mood +
   one music prompt. Don't merge entries.
4. **Reproducible output.** Suno prompts should be paste-ready, not
   paraphrased. Users want to copy-paste, not re-engineer.

## Workflow

### Step 1: Extract

PDF path:
```python
import pymupdf
doc = pymupdf.open("journal.pdf")
# text layer
for i, page in enumerate(doc):
    print(page.get_text())
# images
import os; os.makedirs("pages", exist_ok=True)
for i, page in enumerate(doc):
    for j, img in enumerate(page.get_images(full=True)):
        base = doc.extract_image(img[0])
        with open(f"pages/p{i+1:02d}_{j+1}.{base['ext']}", "wb") as f:
            f.write(base["image"])
```

Image-set path: just `ls` the directory; sort by name or mtime.

### Step 2: Two-channel per page

For each page, get BOTH:
- text (pinyin + Chinese characters in many cases)
- vision_analyze on the image — ask specifically: "Describe the drawing's
  content, colors, mood, and any text/labels in it. It's by an [N]-year-old."

Cross-reference: text tells you what the kid WROTE, vision tells you what
they DREW. Often they diverge — that's interesting material for the
companion.

### Step 3: Light polish

For each entry, write a 3-6 sentence "润色版" that:
- opens with a hook (small wonder, question, scene-setter)
- keeps ALL of the original's concrete details (names, dates, colors)
- adds sensory texture (sound, motion, taste) but in the kid's register
- closes with the child's own emotional beat (delight, curiosity, pride)
- does NOT replace kid words with adult equivalents
- does NOT add lessons or morals the kid didn't write

Preserve pinyin-annotated text by stripping pinyin for the polished version
(it's a reading aid for the original; the polished version reads natively).

### Step 4: Suno music prompt per page

One Suno Style prompt per entry. Template:

```
[Mood adjective] [genre], [emotion keywords], [BPM suggestion],
[2-4 instrument cues], [vocal persona if any], [production feel],
[dynamic arc — describe the journey, not just genre]
```

Concrete patterns that work (proven):
- Wonder/discovery: `"curious and bright, soft piano, glockenspiel, building strings, 88 BPM"`
- Action/play: `"playful and bouncy, ukulele, hand claps, tambourine, 110 BPM"`
- Heroic/ambition: `"heroic but childlike, brass swells, steady drums, soaring melody, 95 BPM"`
- Tender/lullaby: `"gentle piano lullaby, ambient pads, soft bells, 75 BPM"`
- Tech/future: `"playful synth-pop, bouncy arpeggios, retro 80s warmth, 105 BPM"`
- Epic/mythic: `"cinematic folk, bamboo flute, percussion, ancient and grand, 88 BPM"`

**Pitfall**: Don't list 12 instruments. Pick 3-5. Don't write "sad song" —
write the dynamic arc: "starts quiet, builds to hopeful major key." Suno
responds better to journey than to label.

### Step 5: Bundle

Default output: one markdown file with
- preface (卷首语)
- table of contents grouped by theme
- one section per entry: 润色版 + music prompt
- closing note (卷尾寄语)

Optional extensions (offer as A/B/C/D/E/F):
- A. Markdown only (default — done)
- B. Separate music-prompt file for easy copy-paste
- C. Print-ready PDF bundling images + polished text → **see Step 6**
- D. Lyric version — compress polished text into 4-8 line verses per entry
- E. Specific-genre remixes (e.g., all-Chinese-instrument versions)
- F. **Audio narration — narrated mp3 per page + complete story mp3** → **see Step 7**

## Step 6: PDF bundling (extension C)

When the user picks option C, build a landscape A4 picture book PDF with
ReportLab + Chinese fonts. Concrete working example: 19 entries + 5 wrap
pages = 24 pages, ~11 MB output.

**Layout pattern:**

```
+------------------------------------------------------+
| Date · Weather                          Theme       |
+------------------------------------------------------+
|                              |                       |
|       IMAGE (framed)         |   Polished text       |
|       ~55% page width        |   in KaiTi 13pt       |
|                              |                       |
|                              | *  推荐音乐           |  <- bottom-right
|                              | [Sun prompt text]     |
+------------------------------------------------------+
|                     -- page n --                     |
+------------------------------------------------------+
```

**Page sequence:**
1. cover (title + hero image + decorative bands)
2. preface (卷首语)
3. table of contents (2-column, grouped by theme)
4. one landscape page per entry (image-left, text-right, music reference)
5. farewell (卷尾寄语)
6. music index (all 19 Suno prompts in 2-column reference)

**Recipe:**

The full working starter is in `templates/picture-book-pdf.py` — copy it,
swap in your `ENTRIES`, drop images into `./images/`, run. Reads top to
bottom without surprises.

**Pitfalls (READ FIRST — see `references/chinese-pdf-pitfalls.md` for detail):**

- **Use ★, NOT music notes, for decorative markers.** SimHei and SimSun
  both render `♪` (U+266A) and `♫` (U+266B) as empty boxes. Only KaiTi has
  them. If you want a music note in front of "推荐音乐", either use the
  star OR set the surrounding label in KaiTi. ★ is the path of least
  resistance — works in all three CJK fonts.
- **No CJK wrap built into ReportLab.** `canvas.stringWidth` doesn't break
  on Chinese. Write a 15-line char-by-char greedy wrapper
  (`wrap_cjk` in the template) before drawing long body text.
- **Decorative bands overlap page numbers** if both share the same y-zone.
  Page number goes at the LOWEST y; bands stack ABOVE it with at least
  12pt of gap. Bug got me once: page number baseline at y=22 behind a band
  at y=14-18 = invisible text.
- **A4 landscape, not portrait.** If the source drawings are landscape
  (they almost always are, from scanned book pages), landscape A4 with
  image-on-left / text-on-right beats portrait every time.
- **Preserve image whitespace.** Kid drawings have natural margins. Don't
  stretch to fill the frame — the whitespace is part of the look. Use
  aspect-preserving fit with `preserveAspectRatio=True`.

## Step 7: Audio narration (extension F)

When the user wants a **real** audio version (TTS reading + background music
+ mixed mp3), build it as a separate pass that takes the polished text from
Step 3 + the music assignments from Step 4. Three sub-steps; full recipes in
`references/audio-production.md`.

### 7a. Generate TTS readings

Use the Hermes `text_to_speech` tool, one call per entry.

**CRITICAL pitfall — edge TTS rejects pure Chinese.** With "edge" provider,
text containing ONLY Chinese characters returns `No audio was received`. The
trigger is missing language hint. **Fix:** include at least one ASCII digit
anywhere in the text. Prepending a natural date opener like
"今天是 2026 年 3 月 6 日。" both fixes the trigger AND sounds great as a
picture-book opener:

```text
今天是 2026 年 3 月 6 日。2012年，"好奇号"火星车飞过长长的星河……
```

Save to `audio/tts/<idx:02d>_<date>_<theme>.mp3`. Each TTS clip lands ~2-5s
depending on text length.

### 7b. Background music

Two paths, in order of preference:

1. **Suno-generated (real music).** User goes to suno.com, pastes the
   `music` prompt from Step 4 into Custom Mode → Style of Music, downloads
   the mp3, saves as `audio/music/<mood>.mp3`. This is what the user
   actually asked for; treat it as the default expectation.

2. **Procedural synthesis fallback (when Suno isn't available).**
   ffmpeg can synthesize ambient beds that are serviceable as
   background music. Five mood presets (warm_cosmic / cheerful / heroic /
   tech_pulse / calm_dream) using sine wave harmonics + tremolo + filtered
   noise. The recipes and ffmpeg chains are in
   `references/audio-production.md` §2.

   Generate via `templates/audio-mix.py` (the `generate_music_beds` step).

Map each entry to a mood (the entry's natural mood from Step 4). Common
mapping for a 19-entry child journal:
- Wonder/discovery pages → warm_cosmic
- Play/family/daily life → cheerful
- Sports/heroes/military → heroic
- Robots/future/AI → tech_pulse
- Tender/lullaby moments → calm_dream

### 7c. Mix TTS + music per page

Recipe (full code in `templates/audio-mix.py`):

```
target_dur = tts_duration + 1.5s_tail      # bed plays alone for the tail

TTS:    apad=whole_dur=target_dur            # silence-pad so amix doesn't cut
Bed:    aloop + atrim + afade_in + afade_out + volume=-14dB
Mix:    amix inputs=2 duration=first dropout_transition=0
Master: alimiter=limit=0.95                   # prevent clipping
```

Output: `audio/mixed/<idx:02d>_<date>_<theme>.mp3`. The user can play
each entry individually, or run `concat_story.py` to glue all 19 with
~1s gaps into a single complete-story mp3.

### 7d. Replace synthesized beds with real Suno (later)

When the user generates real Suno music, they save it as
`audio/music/<mood>.mp3` (overwriting the synthesized bed) OR as
`audio/music/<idx:02d>_<theme>.mp3` (per-entry override). Re-running
`audio-mix.py` produces a fresh mixed output with real music — no
script changes needed.

## Pitfalls

- **Don't over-pilot** — "润色" means polish. If the polished version reads
  like an adult wrote it, you've gone too far. Show side-by-side comparison
  if unsure.
- **Don't merge entries** — each page is sacred. The dates and small details
  are what make journals personal.
- **Don't translate pinyin away silently** — preserve pinyin in the original
  text dump but not in the polished version. Note this when handing back.
- **Music prompts aren't lyrics** — Suno Style prompts describe sound, not
  words. Don't put Chinese sentences in the style field; that belongs in
  Lyrics field.
- **Vision_analyze is per-image, not per-PDF** — call once per extracted
  image, not once per PDF.
- **Decorative symbols in PDF: use `★`, not `♪`.** SimHei and SimSun (the
  two CJK fonts that handle English + Chinese reliably on Windows) both
  render U+266A / U+266B as empty boxes. Only KaiTi has music-note glyphs.
  If you label something "♪ 推荐音乐" in SimHei, the music note becomes
  a tofu box and the page looks broken. Default to `★` for any decorative
  marker — it renders in all three CJK fonts. (See
  `references/chinese-pdf-pitfalls.md` §2 for the full coverage table.)
- **Edge TTS rejects pure Chinese.** The Hermes `text_to_speech` tool with
  provider=`edge` returns `No audio was received` for text containing only
  Chinese characters — there's no language hint to pick the Chinese voice.
  Fix: prepend a date opener with Arabic digits, e.g.
  `"今天是 2026 年 3 月 6 日。……"`. Doubles as a natural diary-page opening.
  Full detail in `references/audio-production.md` §1.
- **ffmpeg `highpass` doesn't accept `lowpass` as a sub-option.**
  `highpass=f=400:lowpass=f=2500` errors with "Option not found." Chain
  through an intermediate label: `[n]highpass=f=400[nb1];[nb1]lowpass=f=2500[nb]`.
- **`amix` with `duration=first` cuts the bed short at TTS duration.** To
  get the music tail playing AFTER TTS ends, pad the TTS stream with silence
  using `apad=whole_dur=target_dur` (NOT `pad_dur`, which is sample-count).
  Without `whole_dur`, the bed disappears the moment TTS ends.
- **Sunlight check before promising "real Suno music".** Suno.com is
  unreachable from some networks (and has no public API key in many
  Hermes installs). When you can't reach Suno, say so upfront and offer
  the ffmpeg-synthesized beds as a working placeholder — the user can
  replace them later without touching code.

## References

- `references/suno-style-patterns.md` — extended mood-to-style cheat sheet
  with 15+ tested patterns
- `references/chinese-pdf-pitfalls.md` — ReportLab + Chinese fonts recipe;
  font glyph coverage table, CJK wrap helper, landscape A4 layout, page
  number / decorative band pitfall. Read this BEFORE doing PDF bundling.
- `references/audio-production.md` — edge TTS Chinese voice trigger + ffmpeg
  procedural music synthesis + TTS/music mixing recipe. Read this BEFORE
  doing the audio narration extension (Step 7).
- `templates/journal-companion.md` — markdown template for output
- `templates/picture-book-pdf.py` — working ReportLab starter for the
  PDF bundling extension; copy, swap in your entries + images, run.
- `templates/audio-mix.py` — working starter for Step 7: TTS prep + music
  bed generation + per-entry mix + complete-story concat. Copy, swap in
  your entries, run.
