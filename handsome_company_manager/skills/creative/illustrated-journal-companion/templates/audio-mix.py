"""
Audio Narration — Starter Template (Step 7 of illustrated-journal-companion)
==============================================================================

Produces narrated mp3s for an illustrated journal:
  audio/tts/      TTS readings, one mp3 per entry
  audio/music/    Background music beds (synthesized OR user-supplied)
  audio/mixed/    Final mixed mp3s, one per entry
  audio/<name>_完整有声版.mp3   All entries concatenated

The script does three things:
  1. generate_music_beds()  — synthesize 5 mood beds via ffmpeg lavfi
  2. mix_one()              — loop bed to TTS length, fade, lower, mix
  3. concat_story()         — concatenate all mixed mp3s with gaps

Usage:
  1. Replace ENTRIES with your own (date, theme, polished_text, mood).
  2. Use the Hermes text_to_speech tool to generate one mp3 per entry
     into audio/tts/<idx:02d>_<date>_<theme>.mp3.
     The text_to_speech tool requires Arabic digits in Chinese input — see
     references/audio-production.md §1.
  3. Run: python audio-mix.py generate_beds
  4. Run: python audio-mix.py mix
  5. (Optional) Run: python audio-mix.py concat

Tested on Windows with Python 3.11 and ffmpeg 8.x. Should work on macOS/Linux
with the same ffmpeg install.
"""

import os, sys, subprocess, json, glob, shutil

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR  = os.path.join(ROOT, 'audio')
TTS_DIR    = os.path.join(AUDIO_DIR, 'tts')
MUSIC_DIR  = os.path.join(AUDIO_DIR, 'music')
MIX_DIR    = os.path.join(AUDIO_DIR, 'mixed')
for d in (TTS_DIR, MUSIC_DIR, MIX_DIR):
    os.makedirs(d, exist_ok=True)

# ------------------------------------------------------------------
# Mood → bed mapping. Tweak per entry to taste.
# Common mapping for child journal:
#   warm_cosmic → space / planets / science discovery
#   cheerful    → play / family / food / daily joy
#   heroic      → sports heroes / military / door gods / big dreams
#   tech_pulse  → robots / drones / AI / autonomous vehicles
#   calm_dream  → moon / sleep / tender moments
# ------------------------------------------------------------------
MOOD = {
    # idx (1-based) : mood name
    1:  'warm_cosmic',
    2:  'cheerful',
    3:  'heroic',
    4:  'warm_cosmic',
    5:  'calm_dream',
    6:  'heroic',
    7:  'tech_pulse',
    8:  'heroic',
    9:  'tech_pulse',
    10: 'cheerful',
    11: 'cheerful',
    12: 'tech_pulse',
    13: 'cheerful',
    14: 'tech_pulse',
    15: 'cheerful',
    16: 'tech_pulse',
    17: 'cheerful',
    18: 'heroic',
    19: 'heroic',
}

# ------------------------------------------------------------------
# ENTRIES — same shape as picture-book-pdf.py template
# ------------------------------------------------------------------
ENTRIES = [
    # {
    #     'idx': 1,
    #     'date': '3月6日',
    #     'theme': '探秘红色火星',
    #     'text': '...'  # polished text (without pinyin)
    # },
    # ... add all entries
]


# ------------------------------------------------------------------
# Mood bed presets (ffmpeg lavfi chains)
# Each chain is one input. They all produce ~30 seconds of ambient music.
# ------------------------------------------------------------------
PRESETS = {
    'warm_cosmic': (
        "sine=frequency=130.81:duration=30[s1];"
        "sine=frequency=196.00:duration=30[s2];"
        "sine=frequency=261.63:duration=30[s3];"
        "[s1]volume=0.30[v1];"
        "[s2]volume=0.20[v2];"
        "[s3]volume=0.15[v3];"
        "[v1][v2][v3]amix=inputs=3:duration=longest[m];"
        "[m]tremolo=f=0.25:d=0.4[t];"
        "anoisesrc=color=brown:duration=30:amplitude=0.04[n];"
        "[n]lowpass=f=400[nb];"
        "[t][nb]amix=inputs=2:duration=longest,lowpass=f=1500,volume=1.5"
    ),
    'cheerful': (
        "sine=frequency=261.63:duration=30[s1];"
        "sine=frequency=329.63:duration=30[s2];"
        "sine=frequency=392.00:duration=30[s3];"
        "sine=frequency=523.25:duration=30[s4];"
        "[s1]volume=0.20[v1];"
        "[s2]volume=0.18[v2];"
        "[s3]volume=0.15[v3];"
        "[s4]volume=0.08[v4];"
        "[v1][v2][v3][v4]amix=inputs=4:duration=longest[m];"
        "[m]tremolo=f=1.5:d=0.3[t];"
        "anoisesrc=color=pink:duration=30:amplitude=0.03[n];"
        "[n]highpass=f=200[nb];"
        "[t][nb]amix=inputs=2:duration=longest,lowpass=f=2200,volume=1.4"
    ),
    'heroic': (
        "sine=frequency=220.00:duration=30[s1];"
        "sine=frequency=277.18:duration=30[s2];"
        "sine=frequency=329.63:duration=30[s3];"
        "sine=frequency=440.00:duration=30[s4];"
        "[s1]volume=0.25[v1];"
        "[s2]volume=0.22[v2];"
        "[s3]volume=0.18[v3];"
        "[s4]volume=0.12[v4];"
        "[v1][v2][v3][v4]amix=inputs=4:duration=longest[m];"
        "[m]tremolo=f=0.6:d=0.35[t];"
        "anoisesrc=color=brown:duration=30:amplitude=0.05[n];"
        "[n]bandpass=f=800:width_type=h:w=600[nb];"
        "[t][nb]amix=inputs=2:duration=longest,lowpass=f=1800,volume=1.5"
    ),
    'tech_pulse': (
        "sine=frequency=174.61:duration=30[s1];"
        "sine=frequency=261.63:duration=30[s2];"
        "sine=frequency=349.23:duration=30[s3];"
        "[s1]volume=0.30[v1];"
        "[s2]volume=0.22[v2];"
        "[s3]volume=0.15[v3];"
        "[v1][v2][v3]amix=inputs=3:duration=longest[m];"
        "[m]tremolo=f=2.0:d=0.7[t];"
        "anoisesrc=color=white:duration=30:amplitude=0.04[n];"
        "[n]highpass=f=400[nb1];"
        "[nb1]lowpass=f=2500[nb];"
        "[t][nb]amix=inputs=2:duration=longest,volume=1.4"
    ),
    'calm_dream': (
        "sine=frequency=196.00:duration=30[s1];"
        "sine=frequency=246.94:duration=30[s2];"
        "sine=frequency=293.66:duration=30[s3];"
        "[s1]volume=0.28[v1];"
        "[s2]volume=0.20[v2];"
        "[s3]volume=0.15[v3];"
        "[v1][v2][v3]amix=inputs=3:duration=longest[m];"
        "[m]tremolo=f=0.18:d=0.5[t];"
        "anoisesrc=color=brown:duration=30:amplitude=0.03[n];"
        "[n]lowpass=f=350[nb];"
        "[t][nb]amix=inputs=2:duration=longest,lowpass=f=1200,volume=1.3"
    ),
}


# ==================================================================
# generate_music_beds — synthesize 5 mood beds via ffmpeg
# ==================================================================
def generate_music_beds():
    print('Synthesizing mood beds via ffmpeg...')
    for name, chain in PRESETS.items():
        out_path = os.path.join(MUSIC_DIR, f'{name}.mp3')
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-f', 'lavfi', '-i', chain,
            '-ar', '24000', '-ac', '1', '-b:a', '64k',
            out_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f'  FAIL {name}: {r.stderr.strip()[:200]}')
        else:
            sz = os.path.getsize(out_path)
            print(f'  OK  {name}.mp3  ({sz:,} bytes)')


# ==================================================================
# mix_one — TTS + bed with tail
# ==================================================================
def _ffprobe_duration(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def mix_one(tts_path, bed_path, out_path,
            bed_volume_db=-14,
            bed_fade_in=0.4,
            bed_fade_out=1.5,
            tail_extra=1.5):
    """
    Layout per entry:
      [bed_fade_in | TTS+bed overlap | TTS+bed overlap | bed fade out tail]
      ^0s          ... TTS playing ...                 | tts_dur -> tts_dur+tail_extra
    """
    tts_dur = _ffprobe_duration(tts_path)
    target_dur = tts_dur + tail_extra

    bed_filters = (
        f"aloop=loop=-1:size=1e9,"
        f"atrim=0:{target_dur},"
        f"afade=t=in:st=0:d={bed_fade_in},"
        f"afade=t=out:st={target_dur - bed_fade_out}:d={bed_fade_out},"
        f"volume={bed_volume_db}dB"
    )

    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-i', tts_path,
        '-i', bed_path,
        '-filter_complex',
            f"[0:a]volume=0dB,apad=whole_dur={target_dur}[tts];"
            f"[1:a]{bed_filters}[bed];"
            f"[tts][bed]amix=inputs=2:duration=first:dropout_transition=0[mix];"
            f"[mix]alimiter=limit=0.95[out]",
        '-map', '[out]',
        '-ar', '24000', '-ac', '1', '-b:a', '96k',
        out_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def mix_all_entries():
    if not ENTRIES:
        print('No ENTRIES defined. Edit audio-mix.py first.')
        return

    print(f'Mixing {len(ENTRIES)} tracks...')
    ok = 0
    for e in ENTRIES:
        idx = e['idx']
        # Look for TTS file: prefer per-entry exact match, fall back to prefix
        tts_pattern = os.path.join(TTS_DIR, f'{idx:02d}_*.mp3')
        candidates = sorted(glob.glob(tts_pattern))
        if not candidates:
            print(f'  idx {idx:2d}: TTS missing (run text_to_speech first)')
            continue
        tts_path = candidates[0]

        mood = MOOD.get(idx, 'warm_cosmic')
        bed_path = os.path.join(MUSIC_DIR, f'{mood}.mp3')
        if not os.path.exists(bed_path):
            print(f'  idx {idx:2d}: bed missing ({mood})')
            continue

        out_name = f'{idx:02d}_{e["date"]}_{e["theme"]}.mp3'
        out_path = os.path.join(MIX_DIR, out_name)

        ok_flag = mix_one(tts_path, bed_path, out_path)
        if ok_flag:
            d = _ffprobe_duration(out_path)
            print(f'  {idx:2d}. {e["theme"][:14]:14s}  bed={mood:12s}  -> {d:4.1f}s')
            ok += 1
        else:
            print(f'  idx {idx:2d}: MIX FAILED')

    print(f'\nDone. {ok}/{len(ENTRIES)} mixed -> {MIX_DIR}')


# ==================================================================
# concat_story — glue all mixed mp3s into one complete-story mp3
# ==================================================================
def concat_story(out_name='完整有声版.mp3', gap_sec=1.0):
    files = sorted(glob.glob(os.path.join(MIX_DIR, '*.mp3')))
    if not files:
        print('No mixed mp3s in', MIX_DIR)
        return
    out_path = os.path.join(AUDIO_DIR, out_name)

    parts = ''.join(
        f"[{i}:a]apad=pad_dur={gap_sec}[a{i}];"
        for i in range(len(files))
    )
    concat = ''.join(f'[a{i}]' for i in range(len(files))) + \
             f'concat=n={len(files)}:v=0:a=1[out]'
    filter_complex = parts + concat

    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']
    for f in files:
        cmd += ['-i', f]
    cmd += [
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-ar', '24000', '-ac', '1', '-b:a', '96k',
        out_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('CONCAT FAIL:', r.stderr[:300])
        return
    dur = _ffprobe_duration(out_path)
    sz = os.path.getsize(out_path)
    print(f'OK -> {out_path}')
    print(f'    size : {sz:,} bytes  ({sz/1024:.0f} KB)')
    print(f'    dur  : {dur:.1f}s  ({dur/60:.1f} min)')


# ==================================================================
# CLI
# ==================================================================
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'mix'
    if cmd == 'generate_beds':
        generate_music_beds()
    elif cmd == 'mix':
        if not os.path.exists(os.path.join(MUSIC_DIR, 'warm_cosmic.mp3')):
            print('No music beds found. Run: python audio-mix.py generate_beds')
            sys.exit(1)
        mix_all_entries()
    elif cmd == 'concat':
        concat_story()
    elif cmd == 'all':
        generate_music_beds()
        mix_all_entries()
        concat_story()
    else:
        print('Usage: python audio-mix.py [generate_beds|mix|concat|all]')
