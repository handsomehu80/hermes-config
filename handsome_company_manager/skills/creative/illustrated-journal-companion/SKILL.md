---
name: illustrated-journal-companion
description: "Class-level umbrella for illustrated-content production on Hermes. Three modes under one skill: (1) Polish existing illustrated journals/diaries (PDF or image set) — light text polish + per-page multimedia companions (Suno prompts, optional narrated mp3s). (2) Direct audio-only storybook mode — pre-rendered TTS readings + background music per segment + mixed mp3s + flipbook HTML viewer (no polish step). (3) PDF bundling — landscape A4 picture-book with images + polished text + music references. Use when the input is real artwork + handwritten/typed notes (modes 1 & 3), OR when the user wants the audio-only flipbook experience with existing (image, text) pairs (mode 2)."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [journal, illustrated-diary, child-art, music-companion, suno, multimedia, tts, audiobook, ffmpeg, audio-storybook, flipbook, picture-book]
    related_skills: [ocr-and-documents, songwriting-and-ai-music, baoyu-comic, baoyu-article-illustrator]
    absorbed_from: [audio-storybook-production]
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
  - audio storybook
  - 翻页绘本
  - make these drawings speak
  - flipbook HTML
  - per-entry narration + background music
  - mobile-friendly viewer
---

# Illustrated Journal Companion

Class-level umbrella for **illustrated-content production on Hermes**. Three modes under one skill — pick the one that matches the user's actual ask:

| Mode | Input | Output | When |
|---|---|---|---|
| **§ Polish Journal** (Steps 1-6) | Existing illustrated journal (PDF or image set) | Polished markdown companion (text + Suno prompts) + optional PDF bundle + optional audio | User says "润色+配音乐", "optimize this daily-drawing PDF", "把这本日记做成有声绘本" |
| **§ Audio Storybook Mode** (this section) | Existing (image, text) pairs that DON'T need polishing | TTS mp3 per entry + mixed mp3 per entry + flipbook HTML viewer + serve.py for phone access | User says "把这些图文做成能在手机/平板看的", "翻页绘本 / 有声绘本", "make these drawings speak" — and the texts are already polished |
| **§ PDF Bundling** (Step 6) | Polished entries + images | Landscape A4 picture-book PDF | User wants a printable book |

The modes are independent — pick one and skip the rest. The audio + viewer stack that powers Mode 2 is the same machinery used by Mode 1's audio extension (Step 7). The scripts/ folder holds the battle-tested Python tools for both paths.

> **Background:** This umbrella absorbed the now-archived `audio-storybook-production` skill. The complete audio production toolchain (`scripts/mix.py`, `scripts/regen_tts.py`, `scripts/verify_tts.py`, `scripts/generate_music.py`, `scripts/concat_story.py`) and the flipbook viewer (`templates/flipbook-viewer.html`, `templates/serve.py`) live here under the umbrella — see § Audio Storybook Mode below for direct usage without a polish step.

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

## Mode 2: Audio Storybook (Direct, No Polish Step)

When the user already has the (image, text) pairs they want — and just wants
TTS + music + a flipbook viewer — skip Steps 1-6 entirely and use this mode.
This is the path that used to live in the now-archived `audio-storybook-production`
skill; the toolchain is identical to Step 7's audio stack but with its own
scaffolding (manifest schema, flipbook viewer, serve.py for phone access).

### When to use this mode

Trigger phrases that should route here (and NOT to Mode 1):
- "把这本画册配上朗读/音乐" / "make these drawings speak" — and the texts are already polished
- "翻页绘本 / 有声绘本" / flipbook HTML — user wants a swipable viewer
- "给每段配朗读和背景音乐" / per-entry narration + background music
- "把这些图文做成能在手机/平板看的" / mobile-friendly viewer
- "一日一画 / 一画一文" — when the daily-art already has accompanying text

Do NOT use this mode for: pure song generation (use `media/heartmula` or
`creative/songwriting-and-ai-music`); podcast-style monologue (no per-entry
images); video export (separate mp4 pipeline).

### Architecture (direct audio mode)

```
{project}/
├── images/         # source drawings (page01_img1.jpeg ... pageNN_img1.jpeg)
├── text source     # polished entry texts, one per drawing
├── audio/
│   ├── tts/        # one mp3 per entry (TTS only)
│   ├── music/      # mood beds, one per mood (procedural or sourced)
│   ├── mixed/      # TTS + bed, one per entry — what the viewer actually plays
│   ├── manifest.json   # [{idx, date, theme, tts_text, music_prompt, image, audio}]
│   ├── flipbook.html   # self-contained viewer (data inlined)
│   └── README.md
└── serve.py        # tiny local HTTP server for phone access over WiFi
```

Why this shape: keep **TTS, music bed, and mixed as separate folders** so the
user can swap any layer (e.g. drop in a real Suno track to replace a
procedural bed) and re-run just the mix step. The HTML viewer references
`./mixed/` and `../images/` via relative paths so it works under `file://`
AND over a local HTTP server.

### Workflow (9 steps)

```text
[ ] Step 0: Probe environment (edge-tts + ffmpeg on PATH)
[ ] Step 1: Build manifest.json from text source
[ ] Step 2: Generate TTS per entry (scripts/regen_tts.py)
[ ] Step 3: VERIFY TTS — language + duration sanity (scripts/verify_tts.py)
[ ] Step 4: Generate or source background music beds (scripts/generate_music.py)
[ ] Step 5: Mix TTS + bed per entry (scripts/mix.py)
[ ] Step 6: Optionally concatenate into single "complete" mp3 (scripts/concat_story.py)
[ ] Step 7: Build flipbook.html (templates/flipbook-viewer.html)
[ ] Step 8: Test in a browser + verify audio playback
[ ] Step 9: Deliver (file:// URL AND serve.py for phone access)
```

#### Step 0 — Probe environment

Before anything else, confirm edge-tts is installed and a target voice works:

```bash
python -c "import edge_tts, asyncio
async def m():
    v = await edge_tts.list_voices()
    zh = [x['ShortName'] for x in v if x['Locale'].startswith('zh-') and 'Xiaoxiao' in x['ShortName']]
    print(zh[:3])
asyncio.run(m())"
```

If it errors with `ModuleNotFoundError`, install: `python -m pip install edge-tts`.
Also confirm `ffmpeg` and `ffprobe` are on PATH.

#### Step 1 — Build manifest.json

For N entries, produce a JSON array where each item has at minimum:

```json
{
  "idx": 1,
  "date": "3月6日",
  "theme": "探秘红色火星",
  "tts_text": "今天是 2026 年 3 月 6 日。2012年，\"好奇号\"火星车飞过长长的星河……",
  "music_prompt": "Children's storybook adventure, wonder, warm piano, 90 BPM",
  "image": "page04_img1.jpeg"
}
```

`music_prompt` is for documentation/Suno-handoff only — the actual music bed
for this mode is procedurally synthesized (Step 4). Keep `tts_text` natural
and warm; for kids content, prepend a date announcement
("今天是 2026 年 X 月 X 日") so it sounds like a daily diary.

#### Step 2 — Generate TTS

Use `edge-tts` with **explicit voice + rate**. Default voice selection by language:

| Target language | Voice | Notes |
|----------------|-------|-------|
| Chinese (warm female) | `zh-CN-XiaoxiaoNeural` | Most natural storytelling voice |
| Chinese (child-style) | `zh-CN-XiaoyiNeural` | Higher pitch, energetic |
| Chinese (male) | `zh-CN-YunxiNeural` | For heroic / narrator tone |
| English (female) | `en-US-JennyNeural` | |
| Japanese (female) | `ja-JP-NanamiNeural` | |

Rate `-5%` (slightly slower than default) reads more naturally to children.
Save one mp3 per entry to `audio/tts/`. Use `scripts/regen_tts.py`.

#### Step 3 — VERIFY TTS (do not skip)

**This is the single most important step.** edge-tts can silently fall back to
English when the package is broken, environment is degraded, or the user's
locale conflicts with the voice. When it falls back, the mp3 still gets
created — it just contains English-pronounceable fragments (often only the
Arabic numerals, e.g. "2026 3 6") rather than the Chinese reading.

**Heuristic check**: a full Chinese reading of a 100-150 character paragraph
should be 20-35 seconds long. If a TTS file is **< 8 seconds** and the source
text contains CJK characters, it's almost certainly English fallback —
**regenerate, do not proceed**. Use `scripts/verify_tts.py` to scan all TTS
files and flag anything suspect.

#### Step 4 — Generate background music beds

Two options:

**(a) Procedural (always works, no API):** use `scripts/generate_music.py` to
synthesize 5 mood beds via ffmpeg `lavfi`. See `references/mixing-parameters.md`
for the canonical chain.

**(b) Suno / external (better quality, manual):** user generates tracks on
suno.com using the `music_prompt` from manifest.json, drops mp3s into
`audio/music/`, then mix.py picks them up by mood name.

Mood assignment lives in `scripts/mix.py`'s MOOD dict — edit there to remap
entries to beds.

#### Step 5 — Mix TTS + bed

Per entry, build a filter chain:

1. Pad TTS to `tts_dur + tail_extra` seconds (default tail = 1.8s music-only after speech)
2. Loop bed to cover the same duration
3. Apply `afade=t=in:st=0:d=0.4` (gentle bed fade in) and
   `afade=t=out:st=end-1.8:d=1.8` (smooth out)
4. Reduce bed volume by **-10 dB** (NOT -14 — too quiet for kid content; -10 sits cleanly under speech)
5. `amix=inputs=2:duration=first` to combine
6. `alimiter=limit=0.95` to prevent clipping
7. Encode: 24000 Hz mono, 96 kbps

If you change the bed volume, re-run the entire mix — partial re-mixes leave
mismatched loudness across entries. Use `scripts/mix.py`.

#### Step 6 — Concatenate (optional)

Useful for "play the whole story" mode. Insert a 1.0s silence gap between
entries. Final file ≈ `sum(durations) + (N-1) × 1.0` seconds. A typical
19-entry child journal produces ~10 minutes. Use `scripts/concat_story.py`.

#### Step 7 — Build flipbook.html

Use `templates/flipbook-viewer.html` as a starting point. The template inlines
the manifest as JSON (no CORS, works under `file://`). Key UX requirements:

- **First-run gesture gate** (iOS Safari requires user tap before any `audio.play()` — even with pre-loaded src)
- **Touch-friendly**: tap left half = prev, right half = next; swipe supported
- **Keyboard**: ←/→ for prev/next, space for play/pause
- **TOC overlay** with thumbnail grid; current page highlighted
- **Auto-play toggle** in the footer (default ON after first gesture)
- **Follow `prefers-color-scheme: dark`** for bedtime reading
- **Mobile-portrait**: stack image+text vertically; **landscape ≥720px**: side-by-side

The template already has all of these wired; only edit the
entries-injection point and any color tweaks.

#### Step 8 — Test in browser

Open the page, walk through: gate → page 1 plays → next page → TOC jump →
last page. For each page, confirm:

- Counter `N / 19` matches
- Date + theme text correct
- Audio duration ≥ 20s for a normal paragraph (catches fallback)
- Progress bar fills as audio plays
- TOC thumbnails are the actual drawing thumbnails (`background-image`), not placeholders

Use `browser_navigate` + `browser_console` (read `audio.duration` and
`audio.currentTime`) for automation.

#### Step 9 — Deliver

Always give the user **both** options:

1. **Direct file open**: `file:///D:/draw/audio/flipbook.html` — works
   without any server, but iOS Safari may have stricter CORS for sibling files
2. **Local server**: `python serve.py` → prints `http://<lan-ip>:8000/audio/flipbook.html`
   for phone access over WiFi

The `templates/serve.py` template handles LAN IP detection and
Windows-compatible output. Set `Cache-Control: no-store` so re-mixed audio
doesn't serve stale mp3s.

### Verification checklist for Mode 2

| Check | Pass criterion |
|-------|----------------|
| TTS file duration per entry | ≥ 15s for typical paragraph, ≥ 5s for short line |
| Mixed file duration | TTS dur + 1.5-2.0s tail |
| Mixed file volume profile | mean_volume > -32 dB, max_volume > -15 dB |
| Browser playback | Page 1 plays, "下一页" advances counter + audio, TOC jumps work |

If any check fails, do not deliver — fix the pipeline and re-run end-to-end.

## References

| File | Purpose |
|------|---------|
| `references/suno-style-patterns.md` | Extended mood-to-style cheat sheet with 15+ tested patterns |
| `references/chinese-pdf-pitfalls.md` | ReportLab + Chinese fonts recipe; font glyph coverage table, CJK wrap helper, landscape A4 layout, page number / decorative band pitfall. Read this BEFORE doing PDF bundling. |
| `references/audio-production.md` | Edge TTS Chinese voice trigger + ffmpeg procedural music synthesis + TTS/music mixing recipe. Read this BEFORE doing the audio narration extension (Step 7) or Mode 2. |
| `references/edge-tts-voices.md` | Voice catalog by language + tone with notes (folded in from `audio-storybook-production`) |
| `references/mixing-parameters.md` | ffmpeg TTS+bed filter chain with tuning notes (folded in from `audio-storybook-production`) |
| `references/case-study-draw-storybook.md` | Worked example from `D:\draw` — the session that originally produced the audio-storybook-production skill (folded in from `audio-storybook-production`) |

## Templates & Scripts

| File | Purpose | Mode |
|------|---------|------|
| `templates/journal-companion.md` | Markdown template for the polished output | Mode 1 |
| `templates/picture-book-pdf.py` | Working ReportLab starter for the PDF bundling extension; copy, swap in your entries + images, run | Mode 1 (Step 6) |
| `templates/audio-mix.py` | Working starter for Step 7: TTS prep + music bed generation + per-entry mix + complete-story concat. All-in-one for Mode 1's audio extension | Mode 1 (Step 7) |
| `templates/flipbook-viewer.html` | Self-contained HTML viewer with manifest inlined; mobile-portrait + landscape responsive | **Mode 2 (Step 7)** |
| `templates/serve.py` | Local HTTP server with LAN IP detection and `Cache-Control: no-store`; for phone access over WiFi | **Mode 2 (Step 9)** |
| `scripts/regen_tts.py` | Edge-tts batch generation, voice configurable | **Mode 2 (Step 2)** |
| `scripts/verify_tts.py` | Detect English-fallback TTS via duration heuristic (the single most important step) | **Mode 2 (Step 3)** |
| `scripts/generate_music.py` | ffmpeg-synthesized mood beds (5 presets) | **Mode 2 (Step 4)** |
| `scripts/mix.py` | TTS + bed mixer (the canonical version with manifest.json + tunable bed_volume_db) | **Mode 2 (Step 5)** |
| `scripts/concat_story.py` | Concatenate mixed mp3s with silence gaps for "complete story" mode | **Mode 2 (Step 6)** |
