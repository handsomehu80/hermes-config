# Case Study — D:\draw (一日一画)

The session that produced this skill. A parent's 8-year-old son's daily drawings from March–June 2026, originally captured as scanned pages with handwritten descriptions in a single PDF (`D:\draw\一天一画.pdf`). Goal: turn the collection into an audio storybook the kid can flip through on a phone or iPad.

## What was built

```
D:\draw\
├── images/          # 23 source drawings (page01..page23), mostly JPEG
├── 一日一画_优化版.md   # Polished per-entry text (Chinese, kid-friendly tone)
├── 一天一画.pdf      # Original scanned PDF (NOT used directly — text was re-extracted)
├── 一日一画_有声画册.pdf # Earlier PDF build, kept for reference
├── audio_meta.py    # Extracts entries → audio/manifest.json
├── serve.py         # Local HTTP server for phone WiFi access
└── audio/
    ├── tts/         # 19 mp3s, ~30s each, zh-CN-XiaoxiaoNeural
    ├── music/       # 5 procedural mood beds (ffmpeg-synthesized)
    ├── mixed/       # 19 mp3s, ~30s each, TTS + bed at -10dB
    ├── manifest.json # 19 entries with idx/date/theme/tts_text/music_prompt/image
    ├── 一日一画_完整有声版.mp3 # 10.1 min concatenation of all 19 mixed mp3s
    ├── README.md    # Documents Suno-swap workflow
    └── flipbook.html # Self-contained viewer (26KB, data inlined)
```

## Key decisions and what worked

1. **Source of truth: the polished `.md` text**, not the PDF. The PDF had OCR'd handwritten Chinese that was hard to re-extract cleanly. The user had already hand-polished each entry into `一日一画_优化版.md` — using that was both faster and produced better TTS output.

2. **`audio_meta.py` reuses `build_pdf.py` entries** via `importlib`. Avoids two sources of truth. Single Python file owns the entry list.

3. **Prepending "今天是 2026 年 X 月 X 日"** before each entry. Without it, edge-tts had trouble staying in Chinese voice (the first sentence was pure numbers/dates). The date announcement gives the voice a "warm diary opening" anchor. Discovered this empirically in the first session.

4. **Procedural music beds, NOT real Suno tracks.** User had no Suno API key, suno.com was unreachable from the environment. ffmpeg `lavfi` synthesis produces acceptable ambient pads for 5 mood categories. Documented the swap path in `audio/README.md` so the user can drop in real Suno tracks later.

5. **`rate=-5%` on edge-tts.** Default rate sounds rushed for kids content. -5% gives a natural storyteller pace.

6. **Bed volume -10 dB, not -14.** The first mix used -14 dB and the user reported "没听到音乐" / "no background music". Bumped to -10 dB and verified audible but not competing.

## What failed and why this skill exists

The first session produced 19 mixed mp3s that LOOKED fine in the viewer. But when the user opened the flipbook on their phone, the audio was **English, not Chinese — and only the digits were intelligible** ("2026 3 6"). What happened:

- `edge-tts` was installed in the first session
- It generated TTS, mixed everything, shipped the deliverable
- Between sessions, the venv was reset (or packages cleaned) — `edge-tts` was uninstalled
- The mixed mp3s still existed on disk, still played, still had "TTS + music" structure
- But the TTS portion was **English-fallback garbage** because the package wasn't actually there during regeneration (it wasn't regenerated — the old files just sat there)
- The user had no reason to suspect the audio was wrong until they actually listened

The fix: `scripts/verify_tts.py` checks each TTS file's duration against a Chinese-paragraph heuristic. A real Chinese reading of a 100-150 character paragraph is 20-35s. The broken files were 6s each (just the digits).

## What the user asked for, in order

1. Optimize the original text + try to pair music → first session, produced PDF + audio
2. "C" → build an HTML flipbook for phone/iPad → second session, produced `flipbook.html`
3. "网页打开" → user opened it and noticed audio was English + no music → third session (this one), diagnosed, regenerated with `zh-CN-XiaoxiaoNeural` + bumped bed volume

## Files referenced in this case study

- Working scripts in this skill: `scripts/regen_tts.py`, `scripts/mix.py`, `scripts/generate_music.py`, `scripts/concat_story.py`, `scripts/verify_tts.py`
- HTML viewer: `templates/flipbook-viewer.html`
- Local server: `templates/serve.py`

## Lessons that propagated into the umbrella skill

1. **Verify TTS file duration before declaring done** — codified in Step 3 of SKILL.md and automated in `scripts/verify_tts.py`.
2. **Bed volume at -10 dB**, not -14 — codified in `references/mixing-parameters.md`.
3. **iOS Safari audio gesture** — handled by the gate overlay in `templates/flipbook-viewer.html`.
4. **Self-contained viewer** — manifest inlined as JSON, no CORS, works under `file://`.
5. **Always deliver both file:// AND serve.py options** — user can preview locally, then test on phone.