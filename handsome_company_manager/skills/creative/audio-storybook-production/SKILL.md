---
name: audio-storybook-production
description: "Generate a multilingual audio storybook — pre-rendered TTS readings + background music per segment, mixed into a flipbook-ready HTML viewer for phone/tablet."
version: 1.0.0
author: Hermes
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [tts, audio, storybook, kids-content, ffmpeg, html-viewer]
    category: creative
---

# Audio Storybook Production

Turn a collection of (image, text) entries — typically a child's daily drawings with descriptions — into a polished audio storybook that opens in any phone or tablet browser. Each entry gets a Chinese (or other-language) TTS reading layered over a mood-matched music bed, then a single self-contained HTML viewer lets you swipe through pages, play/pause audio per page, jump via thumbnail grid, and follows system dark mode.

The class of work this skill covers: **"make these drawings speak / read aloud with music / 配乐朗读 / 有声绘本"** — for any short-form content (kids' daily art, illustrated essays, picture-book drafts).

## When to Use

Trigger this skill when the user says any of:

- "把这本画册配上朗读/音乐" / "make these drawings speak"
- "一日一画 / 一画一文" / daily-art + description workflow
- "翻页绘本 / 有声绘本" / flipbook HTML
- "给每段配朗读和背景音乐" / per-entry narration + background music
- "把这些图文做成能在手机/平板看的" / mobile-friendly viewer

Do NOT use this skill for: pure song generation (use `media/heartmula` or `creative/songwriting-and-ai-music`); podcast-style monologue (no per-entry images); video export (that's a separate mp4 pipeline).

## Architecture

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

Why this shape: keep **TTS, music bed, and mixed as separate folders** so the user can swap any layer (e.g. drop in a real Suno track to replace a procedural bed) and re-run just the mix step. The HTML viewer references `./mixed/` and `../images/` via relative paths so it works under `file://` AND over a local HTTP server.

## Workflow

```
[ ] Step 0: Probe environment
[ ] Step 1: Build manifest.json from text source
[ ] Step 2: Generate TTS per entry (edge-tts)
[ ] Step 3: VERIFY TTS — language + duration sanity
[ ] Step 4: Generate or source background music beds
[ ] Step 5: Mix TTS + bed per entry
[ ] Step 6: Optionally concatenate into single "complete" mp3
[ ] Step 7: Build flipbook.html (use templates/flipbook-viewer.html)
[ ] Step 8: Test in a browser + verify audio playback
[ ] Step 9: Deliver (give user a file:// URL AND a serve.py option for phone)
```

### Step 0 — Probe environment

Before anything else, confirm edge-tts is installed and a target voice works:

```bash
python -c "import edge_tts, asyncio
async def m():
    v = await edge_tts.list_voices()
    zh = [x['ShortName'] for x in v if x['Locale'].startswith('zh-') and 'Xiaoxiao' in x['ShortName']]
    print(zh[:3])
asyncio.run(m())"
```

If it errors with `ModuleNotFoundError`, install: `python -m pip install edge-tts`. Also confirm `ffmpeg` and `ffprobe` are on PATH.

### Step 1 — Build manifest.json

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

`music_prompt` is for documentation/Suno-handoff only — the actual music bed for this skill is procedurally synthesized (Step 4). Keep `tts_text` natural and warm; for kids content, prepend a date announcement ("今天是 2026 年 X 月 X 日") so it sounds like a daily diary.

### Step 2 — Generate TTS

Use `edge-tts` with **explicit voice + rate**. Default voice selection by language:

| Target language | Voice | Notes |
|----------------|-------|-------|
| Chinese (warm female) | `zh-CN-XiaoxiaoNeural` | Most natural storytelling voice |
| Chinese (child-style) | `zh-CN-XiaoyiNeural` | Higher pitch, energetic |
| Chinese (male) | `zh-CN-YunxiNeural` | For heroic / narrator tone |
| English (female) | `en-US-JennyNeural` | |
| Japanese (female) | `ja-JP-NanamiNeural` | |

Rate `-5%` (slightly slower than default) reads more naturally to children. Save one mp3 per entry to `audio/tts/`.

Reference script: `scripts/regen_tts.py` — drop-in for the D:\draw case, easy to adapt (change `MANIFEST` and `OUT_DIR`).

### Step 3 — VERIFY TTS (do not skip)

**This is the single most important step.** edge-tts can silently fall back to English when the package is broken, environment is degraded, or the user's locale conflicts with the voice. When it falls back, the mp3 still gets created — it just contains English-pronounceable fragments (often only the Arabic numerals, e.g. "2026 3 6") rather than the Chinese reading.

**Heuristic check**: a full Chinese reading of a 100-150 character paragraph should be 20-35 seconds long. If a TTS file is **< 8 seconds** and the source text contains CJK characters, it's almost certainly English fallback — **regenerate, do not proceed**.

```bash
# Quick verification of every TTS file
for f in audio/tts/*.mp3; do
  dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
  echo "$f  ${dur}s"
done | sort -t: -k2 -n
```

A reference verifier that does this automatically: `scripts/verify_tts.py`.

### Step 4 — Generate background music beds

Two options:

**(a) Procedural (always works, no API):** use ffmpeg `lavfi` to synthesize 5 mood beds. See `references/mixing-parameters.md` for the canonical chain (`generate_music.py` in the D:\draw reference).

**(b) Suno / external (better quality, manual):** user generates tracks on suno.com using the `music_prompt` from manifest.json, drops mp3s into `audio/music/`, then mix.py picks them up by mood name.

Mood assignment lives in `mix.py`'s MOOD dict — edit there to remap entries to beds.

### Step 5 — Mix TTS + bed

Per entry, build a filter chain:

1. Pad TTS to `tts_dur + tail_extra` seconds (default tail = 1.8s music-only after speech)
2. Loop bed to cover the same duration
3. Apply `afade=t=in:st=0:d=0.4` (gentle bed fade in) and `afade=t=out:st=end-1.8:d=1.8` (smooth out)
4. Reduce bed volume by **-10 dB** (NOT -14 — too quiet for kid content; -10 sits cleanly under speech)
5. `amix=inputs=2:duration=first` to combine
6. `alimiter=limit=0.95` to prevent clipping
7. Encode: 24000 Hz mono, 96 kbps

If you change the bed volume, re-run the entire mix — partial re-mixes leave mismatched loudness across entries.

### Step 6 — Concatenate (optional)

Useful for "play the whole story" mode. Insert a 1.0s silence gap between entries. Final file ≈ `sum(durations) + (N-1) × 1.0` seconds. The D:\draw complete story is ~10 minutes.

### Step 7 — Build flipbook.html

Use `templates/flipbook-viewer.html` as a starting point. The template inlines the manifest as JSON (no CORS, works under `file://`). Key UX requirements:

- **First-run gesture gate** (iOS Safari requires user tap before any audio.play() — even with pre-loaded src)
- **Touch-friendly**: tap left half = prev, right half = next; swipe supported
- **Keyboard**: ←/→ for prev/next, space for play/pause
- **TOC overlay** with thumbnail grid; current page highlighted
- **Auto-play toggle** in the footer (default ON after first gesture)
- **Follow `prefers-color-scheme: dark`** for bedtime reading
- **Mobile-portrait**: stack image+text vertically; **landscape ≥720px**: side-by-side

The template already has all of these wired; only edit the entries-injection point and any color tweaks.

### Step 8 — Test in browser

Open the page, walk through: gate → page 1 plays → next page → TOC jump → last page. For each page, confirm:

- Counter `N / 19` matches
- Date + theme text correct
- Audio duration ≥ 20s for a normal paragraph (catches fallback)
- Progress bar fills as audio plays
- TOC thumbnails are the actual drawing thumbnails (background-image), not placeholders

Use `browser_navigate` + `browser_console` (read `audio.duration` and `audio.currentTime`) for automation.

### Step 9 — Deliver

Always give the user **both** options:

1. **Direct file open**: `file:///D:/draw/audio/flipbook.html` — works without any server, but iOS Safari may have stricter CORS for sibling files
2. **Local server**: `python serve.py` → prints `http://<lan-ip>:8000/audio/flipbook.html` for phone access over WiFi

The serve.py template in `templates/serve.py` handles LAN IP detection and Windows-compatible output.

## Pitfalls

1. **TTS silently falls back to English** — verify file duration in Step 3 BEFORE mixing. A 6-second "Chinese" file with only digits = broken. The lesson learned the hard way: this session's user came back saying "只有数字的英文" because edge-tts had been uninstalled in a previous cleanup, and the old TTS files were never re-verified.

2. **Music bed too quiet** — start at -10 dB bed attenuation, NOT -14. For kids content the music should be clearly audible but not compete with speech. If a parent says "没听到音乐" / "no background music", bump another +3 dB.

3. **iOS Safari audio playback** — `<audio>.play()` will reject with `NotAllowedError` unless called inside a user-gesture handler. The viewer's first-run gate handles this; clicking prev/next doesn't unlock audio in iOS until the FIRST gesture has primed the audio element. Always test on actual phone, not just desktop Chrome.

4. **ffmpeg `aloop` size limit** — when looping a 30s bed to cover a 60s reading, `aloop=loop=-1:size=1e9` works but creates a large intermediate. Use `atrim=0:target_dur` immediately after to drop the extra.

5. **Naming collisions** — mix.py uses `glob(f'{idx:02d}_*.mp3')` to match TTS files. If multiple TTS files match (e.g. you kept old + new), the first one alphabetically wins — which may not be the one you want. Always clean `audio/tts/` before regenerating, or use a distinguishing slug like `{idx:02d}_v2_*.mp3`.

6. **Audio file cache headers** — local HTTP server may serve cached mp3 after re-mix, so the viewer keeps playing old audio. Set `Cache-Control: no-store` in serve.py. Reference: `templates/serve.py` already does this.

7. **Manifest order = playback order** — if user wants the most recent day first, reverse the entries array before inlining into flipbook.html. Don't try to sort at runtime.

8. **Volume clipping** — if you stack too many sine waves in the music bed generation without `alimiter`, the mixed output will distort. The reference `generate_music.py` chains 3-4 sine sources per preset; that's the safe ceiling.

## Verification

Before declaring done, run these four checks:

| Check | Pass criterion |
|-------|----------------|
| TTS file duration per entry | ≥ 15s for typical paragraph, ≥ 5s for short line |
| Mixed file duration | TTS dur + 1.5-2.0s tail |
| Mixed file volume profile | mean_volume > -32 dB, max_volume > -15 dB |
| Browser playback | Page 1 plays, "下一页" advances counter + audio, TOC jumps work |

If any check fails, do not deliver — fix the pipeline and re-run end-to-end.

## Deliverable Checklist

- [ ] `audio/tts/` — N mp3s, each ≥ 15s for Chinese paragraph
- [ ] `audio/music/` — at least one bed per mood used; ≥ 20s
- [ ] `audio/mixed/` — N mp3s, each with both TTS and music audible
- [ ] `audio/manifest.json` — N entries with all required fields
- [ ] `audio/flipbook.html` — opens in browser, plays page 1, navigates
- [ ] `serve.py` — gives the user a phone-accessible URL
- [ ] README in `audio/` — explains how to swap a music bed for real Suno output

## References

| File | Purpose |
|------|---------|
| [references/edge-tts-voices.md](references/edge-tts-voices.md) | Voice catalog by language + tone with notes |
| [references/mixing-parameters.md](references/mixing-parameters.md) | ffmpeg TTS+bed filter chain with tuning notes |
| [references/case-study-draw-storybook.md](references/case-study-draw-storybook.md) | Worked example from D:\draw (the session that produced this skill) |

## Templates & Scripts

| File | Purpose |
|------|---------|
| [scripts/regen_tts.py](scripts/regen_tts.py) | Edge-tts batch generation, voice configurable |
| [scripts/verify_tts.py](scripts/verify_tts.py) | Detect English-fallback TTS via duration heuristic |
| [scripts/mix.py](scripts/mix.py) | TTS + bed mixer (the canonical version) |
| [scripts/generate_music.py](scripts/generate_music.py) | ffmpeg-synthesized mood beds |
| [scripts/concat_story.py](scripts/concat_story.py) | Concatenate mixed mp3s with silence gaps |
| [templates/flipbook-viewer.html](templates/flipbook-viewer.html) | Self-contained HTML viewer, manifest inlined |
| [templates/serve.py](templates/serve.py) | Local HTTP server with LAN IP detection |

## Related skills

- `creative/baoyu-article-illustrator` — generating the drawing images themselves (if user wants new art)
- `creative/songwriting-and-ai-music` — if user wants real Suno music instead of procedural beds
- `media/heartmula` — for song generation (different class: lyrics+music, not TTS narration)