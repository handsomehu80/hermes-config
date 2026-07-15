# Mixing TTS + Background Music with ffmpeg

The canonical filter chain for mixing a TTS reading (one mp3 per entry) with a mood-matched background music bed (one mp3 per mood) into a single per-entry mp3.

## Reference filter graph

```
[tts.mp3] ──► [volume=0dB][apad=whole_dur=TARGET][tts]
[bed.mp3] ──► [aloop=loop=-1:size=1e9][atrim=0:TARGET]
              [afade=t=in:st=0:d=0.4]
              [afade=t=out:st=TARGET-1.8:d=1.8]
              [volume=-10dB][bed]
[tts][bed] ──► [amix=inputs=2:duration=first:dropout_transition=0][mix]
[mix] ──► [alimiter=limit=0.95][out]
```

Where `TARGET = tts_duration + tail_extra` (default `tail_extra = 1.8s` so the music continues 1.8s after speech ends, then fades).

## Tuning parameters

| Parameter | Default | Range | What it does |
|-----------|---------|-------|--------------|
| `bed_volume_db` | `-10` | `-14` to `-6` | Bed loudness relative to speech. `-10` is the sweet spot for kids. `-14` is too quiet — user complaints of "no music". `-6` competes with speech. |
| `bed_fade_in` | `0.4` | `0.2` to `1.0` | How long the bed takes to fade in at the start. Shorter = more abrupt, longer = more cinematic. |
| `bed_fade_out` | `1.8` | `1.0` to `3.0` | How long the bed fades out at the end. Longer tail = "music lingers" feel. |
| `tail_extra` | `1.8` | `0.0` to `3.0` | Music-only seconds AFTER speech ends. 0 = abrupt cut. 1.8 = graceful wind-down. |
| `alimiter.limit` | `0.95` | `0.85` to `0.98` | Clipping prevention. <0.90 starts sounding compressed; >0.98 risks digital clipping. |
| Output bitrate | `96k` | `64k` to `128k` | Per-entry mp3 quality. 96k mono is plenty for narration. |

## Working ffmpeg command

```bash
ffmpeg -y -hide_banner -loglevel error \
  -i tts.mp3 \
  -i warm_cosmic.mp3 \
  -filter_complex "
    [0:a]volume=0dB,apad=whole_dur=${TARGET}[tts];
    [1:a]aloop=loop=-1:size=1e9,atrim=0:${TARGET},afade=t=in:st=0:d=0.4,afade=t=out:st=${TARGET_FADE_START}:d=1.8,volume=-10dB[bed];
    [tts][bed]amix=inputs=2:duration=first:dropout_transition=0[mix];
    [mix]alimiter=limit=0.95[out]
  " \
  -map '[out]' \
  -ar 24000 -ac 1 -b:a 96k \
  mixed/01_xxx.mp3
```

Where:
- `TARGET = $(ffprobe -show_entries format=duration ... tts.mp3) + 1.8`
- `TARGET_FADE_START = TARGET - 1.8`

## Why these specific values

**`aloop=loop=-1:size=1e9`** — the `size=1e9` allocates a 1-billion-sample internal buffer for seamless looping. ffmpeg needs an explicit finite loop size; without it, `aloop` errors out. 1e9 samples @ 24000Hz ≈ 11.6 hours, so it never actually limits us in practice.

**`duration=first`** in `amix` — use the TTS stream length as the output length. Without `duration=first`, `amix` would extend to whichever stream is longer, and the bed fade-out gets cut off.

**`dropout_transition=0`** — when one stream ends (the bed fades out), don't add crossfade artifacts. We control fades ourselves.

**`atrim=0:${TARGET}`** after `aloop` — drops anything beyond the target duration. Without this, the bed filter chain stays "alive" past the end and `amix` extends the output.

**`whole_dur=${TARGET}` in `apad`** — pads the TTS with silence to TARGET length so both streams end at the same point. If the bed is exactly TARGET long but TTS is shorter, the bed continues alone past TTS end (which is the goal — music tail).

## Procedural music beds (ffmpeg lavfi)

For 5 mood presets without any external service, the working chains are in `scripts/generate_music.py`. Quick patterns:

```
warm_cosmic   : 3 sine waves (130.81/196.00/261.63 Hz) + brown noise + tremolo f=0.25
cheerful      : 4 sine waves (C/E/G/C high) + pink noise + tremolo f=1.5
heroic        : 4 sine waves (A/C#/E/A) + brown noise + tremolo f=0.6
tech_pulse    : 3 sine waves (F/C/F#) + white noise + tremolo f=2.0
calm_dream    : 3 sine waves (G/B/D) + brown noise + tremolo f=0.18
```

Each bed is exactly 30 seconds, generated at 24000 Hz mono, 64 kbps. The mix step loops them to match TTS duration.

## Mood-to-entry mapping

Keep this in `mix.py`'s `MOOD` dict. When the user wants to swap a real Suno track in, they just override the mood filename in the dict (or drop the new mp3 with the same name).

```python
MOOD = {
    1:  'warm_cosmic',   # 火星 — wonder, science
    2:  'cheerful',      # 课间游戏 — playful
    3:  'heroic',        # 门神 — ancient guardian
    # ... etc
}
```

## Verification

After mixing, run:

```bash
for f in mixed/*.mp3; do
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f"
  ffmpeg -i "$f" -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
done
```

Healthy mixed output:
- duration ≈ TTS duration + 1.8s
- `mean_volume` between -32 dB and -22 dB
- `max_volume` > -15 dB

If `mean_volume` < -32 dB, the bed is too quiet — bump `bed_volume_db` from -10 to -8 and re-mix.

If `max_volume` is hitting 0 dB or above, clipping is happening — lower bed by another 3 dB.