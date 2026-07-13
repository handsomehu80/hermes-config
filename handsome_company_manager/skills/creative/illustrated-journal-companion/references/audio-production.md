# Audio Production — TTS + Music + Mixing

Hard-won knowledge from generating narrated mp3s for an illustrated journal
(19 entries, ~85 seconds of mixed audio total). Read this BEFORE running
Step 7 of the workflow.

The pipeline produces three layers:

```
audio/
├── tts/                          # Step 7a: one mp3 per entry, ~2-5s each
│   ├── 01_3月6日_火星.mp3
│   ├── 02_3月9日_课间游戏.mp3
│   └── ...
├── music/                        # Step 7b: 5 mood beds (or per-entry overrides)
│   ├── warm_cosmic.mp3
│   ├── cheerful.mp3
│   ├── heroic.mp3
│   ├── tech_pulse.mp3
│   ├── calm_dream.mp3
│   └── moods.json                # preset → path map
└── mixed/                        # Step 7c: TTS + bed, one per entry
    ├── 01_3月6日_探秘红色火星.mp3
    └── ...

# Plus a complete story version:
audio/一日一画_完整有声版.mp3    # all 19 entries, ~1s gaps, 1.5-2 min total
```

## 1. Edge TTS Chinese voice trigger

The Hermes `text_to_speech` tool defaults to provider=`edge`. With **pure
Chinese text** it returns `No audio was received` — the service has no
language hint to pick the Chinese voice. Reproducible: any of these texts
fail:

```
叮铃铃下课了。
今天天气真好。
下课了。
```

Any text containing an Arabic digit works. The fix is to prepend a natural
date opener that doubles as a picture-book intro:

```python
date_announce = f"今天是 2026 年 {month} 月 {day} 日。"  # month/day from entry['date']
tts_text = date_announce + body_text
```

Why this is good UX too:
- The opener sounds like a natural diary page ("Today is…")
- It works around the TTS quirk without sounding mechanical
- A date that's already in the visible text doesn't feel redundant

**Other TTS gotchas worth knowing:**
- Texts with `"..."` Chinese double quotes work fine once digits are present
- Pure digit `1` is enough; you don't need a year
- The "edge" provider outputs mp3, 24000Hz mono, ~3-5 seconds per 100 chars

## 2. ffmpeg procedural music synthesis

When Suno isn't available (no API, no login, network blocked), ffmpeg can
synthesize ambient beds that work as background music. Five presets cover
the common journal moods:

| Preset | Character | Mood pages |
|---|---|---|
| `warm_cosmic` | low warm pad + slow tremolo + brown noise | Mars, Moon, space, science |
| `cheerful`    | bright C major triad + fast tremolo + pink noise | play, family, friends |
| `heroic`      | midrange pulse + brass-edge bandpass + brown noise | sports, military, door gods |
| `tech_pulse`  | rhythmic 2Hz tremolo + filtered white noise | robots, AI, future |
| `calm_dream`  | very soft F major pad + slow tremolo | tender moments, lullaby |

### The synthesis recipe

Each preset follows the same pattern:

```
sine waves (root + 5th + 3rd/8va)         # consonant frequencies
  → individual volume scaling              # ~0.30 root, ~0.20 5th, ~0.15 color
  → amix to combine harmonics
  → tremolo (frequency in Hz, depth)       # 0.18-2.0 Hz range
  → plus filtered noise (color=...)        # pink / brown / white
  → final lowpass (1500-2200 Hz)           # warmth
  → master volume 1.3-1.5                  # compensate for filter losses
```

Example — the warm_cosmic preset:

```bash
ffmpeg -y -f lavfi -i \
  "sine=frequency=130.81:duration=30[s1];\
   sine=frequency=196.00:duration=30[s2];\
   sine=frequency=261.63:duration=30[s3];\
   [s1]volume=0.30[v1];\
   [s2]volume=0.20[v2];\
   [s3]volume=0.15[v3];\
   [v1][v2][v3]amix=inputs=3:duration=longest[m];\
   [m]tremolo=f=0.25:d=0.4[t];\
   anoisesrc=color=brown:duration=30:amplitude=0.04[n];\
   [n]lowpass=f=400[nb];\
   [t][nb]amix=inputs=2:duration=longest,lowpass=f=1500,volume=1.5" \
  -ar 24000 -ac 1 -b:a 64k warm_cosmic.mp3
```

### Filter chain gotchas

**`highpass` does NOT take a `lowpass` sub-option.** You must chain:

```bash
# WRONG — "Option not found"
[n]highpass=f=400:lowpass=f=2500[nb];

# RIGHT — chain through an intermediate label
[n]highpass=f=400[nb1];
[nb1]lowpass=f=2500[nb];
```

Same with `bandpass` — chain it, don't combine parameters.

### Mood → entry mapping

For a 19-entry child journal the natural mapping is roughly:

```
warm_cosmic → space, planets, science discovery pages
cheerful    → games, family outings, food, daily joy
heroic      → sports heroes, military, door gods, big dreams
tech_pulse  → robots, drones, AI, autonomous vehicles
calm_dream  → moon, sleep, quiet wishes, tender moments
```

Override per entry in the mix script's MOOD dict when one page wants a
different mood than its group default.

## 3. TTS + bed mixing recipe

The mixing pipeline:

```
TTS (raw, 2-5s)                 ┐
                                ├── amix (inputs=2, duration=first) → alimiter → mp3
Bed (looped, faded, -14dB)      ┘
```

### Key parameters

```
target_dur    = tts_duration + 1.5    # 1.5s bed-only tail after TTS ends
bed_volume_db = -14                    # bed is BACKGROUND; -14dB is the sweet spot
bed_fade_in   = 0.4s                   # gentle attack
bed_fade_out  = 1.5s                   # gentle tail at the end
```

### The critical apad trick

**`amix` with `duration=first` cuts the bed short at TTS duration.** To get
the music tail playing AFTER TTS ends, you must pad the TTS stream with
silence up to `target_dur`:

```bash
ffmpeg -i tts.mp3 -i bed.mp3 -filter_complex \
  "[0:a]volume=0dB,apad=whole_dur=6.1[tts]; \
   [1:a]aloop=loop=-1:size=1e9,atrim=0:6.1,\
         afade=t=in:st=0:d=0.4,\
         afade=t=out:st=4.6:d=1.5,\
         volume=-14dB[bed]; \
   [tts][bed]amix=inputs=2:duration=first:dropout_transition=0[mix]; \
   [mix]alimiter=limit=0.95[out]" \
  -map "[out]" -ar 24000 -ac 1 -b:a 96k out.mp3
```

`whole_dur` (note: not `pad_dur`) extends the audio to a target absolute
duration. Without it, the bed gets cut at exactly TTS end.

### Verification recipe

After mixing, sanity-check:

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out.mp3
ffmpeg -i out.mp3 -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
```

Expected:
- duration ≈ tts_dur + 1.5
- mean_volume around -28 to -32 dB
- max_volume around -8 to -12 dB (limited by alimiter)

## 4. Concatenating into one complete-story mp3

Once all entries are mixed, glue them together with brief gaps:

```bash
ffmpeg -i 01.mp3 -i 02.mp3 ... -i 19.mp3 \
  -filter_complex \
    "[0:a]apad=pad_dur=1.0[a0]; \
     [1:a]apad=pad_dur=1.0[a1]; \
     ... \
     [a0][a1]...[a18]concat=n=19:v=0:a=1[out]" \
  -map "[out]" -ar 24000 -ac 1 -b:a 96k complete.mp3
```

For 19 entries with 1s gaps, total is approximately
`(sum of TTS durations) + 19 × 1.0s + 19 × 1.5s tails`
= roughly 1.5-2 minutes for a typical journal.

## 5. Suno-replacement workflow

When the user has real Suno tracks:

1. Generate on suno.com (Custom Mode → paste music prompt → download mp3)
2. Save the file:
   - **By mood** (recommended): `audio/music/warm_cosmic.mp3` overwriting the
     synthesized bed. All entries mapped to that mood now use real Suno music.
   - **By entry** (for fine control): `audio/music/01_mars.mp3`, etc. The mix
     script picks per-entry file when present.
3. Re-run `templates/audio-mix.py` (or `python audio/mix.py`). The output
   regenerated with the real music; nothing else changes.

This means the synthesized beds aren't throwaway — they're a **working
placeholder** the user can later replace without touching code.

## 6. Total time and size budget

For a 19-entry journal:
- TTS: ~1 minute total wall time (calls in batches of 4-5)
- Music beds: ~30 seconds total
- Mixing: ~30 seconds total
- Final mp3 size: ~1.3 MB for complete story, ~50 KB per entry

A whole audiobook (19 narrated entries + background music) weighs about as
much as one photo. Easy to share by email or WeChat.
