# -*- coding: utf-8 -*-
"""
Mix TTS readings + background music beds into final per-entry mp3s.

Inputs:
  - {tts_dir}/*.mp3    (TTS readings, one per entry)
  - {beds_dir}/*.mp3   (background beds, one per mood name)
  - manifest.json      ([{idx, date, theme, ...}])

Outputs:
  - {mix_dir}/{idx:02d}_{date}_{theme}.mp3

Mix parameters:
  - bed_volume_db = -10 (loud enough to be clearly audible for kids content;
                          previously -14 was too quiet)
  - bed_fade_in   = 0.4s
  - bed_fade_out  = 1.8s
  - tail_extra    = 1.8s of music-only after TTS ends
  - alimiter      = 0.95 (clipping prevention)

To swap a procedural bed for a real Suno track, drop a mp3 into {beds_dir}
with the matching mood name (e.g. warm_cosmic.mp3), or override MOOD below
to point to your new filename.

Usage:
    python mix.py
    python mix.py --manifest audio/manifest.json --tts-dir audio/tts --beds-dir audio/music
"""
import os, subprocess, json, glob, sys, argparse

def ffprobe_duration(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

# Default mood assignment. Override per-project if needed.
DEFAULT_MOOD = {
    1:  'warm_cosmic', 2:  'cheerful',    3:  'heroic',
    4:  'warm_cosmic', 5:  'calm_dream',  6:  'heroic',
    7:  'tech_pulse',  8:  'heroic',      9:  'tech_pulse',
    10: 'cheerful',    11: 'cheerful',    12: 'tech_pulse',
    13: 'cheerful',    14: 'tech_pulse',  15: 'cheerful',
    16: 'tech_pulse',  17: 'cheerful',    18: 'heroic',
    19: 'heroic',
}

def mix_one(tts_path, bed_path, out_path,
            bed_volume_db=-10, bed_fade_in=0.4, bed_fade_out=1.8, tail_extra=1.8):
    tts_dur = ffprobe_duration(tts_path)
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
    if r.returncode != 0:
        print(f'  FAIL: {r.stderr[:300]}')
        return None
    return out_path

def main(manifest, tts_dir, beds_dir, mix_dir, bed_db):
    os.makedirs(mix_dir, exist_ok=True)
    with open(manifest, encoding='utf-8') as f:
        entries = json.load(f)

    print(f'Mixing {len(entries)} tracks...')
    print(f'  TTS : {tts_dir}')
    print(f'  Beds: {beds_dir}')
    print(f'  Out : {mix_dir}')
    print(f'  Bed volume: {bed_db} dB\n')

    ok, missing_tts, missing_bed = 0, 0, 0
    for e in entries:
        idx = e['idx']
        tts_pattern = os.path.join(tts_dir, f'{idx:02d}_*.mp3')
        tts_files = glob.glob(tts_pattern)
        if not tts_files:
            print(f'  idx {idx:2d}: TTS missing ({tts_pattern})')
            missing_tts += 1
            continue
        tts_path = sorted(tts_files)[0]

        mood = DEFAULT_MOOD.get(idx, 'warm_cosmic')
        bed_path = os.path.join(beds_dir, f'{mood}.mp3')
        if not os.path.exists(bed_path):
            print(f'  idx {idx:2d}: bed missing ({mood})')
            missing_bed += 1
            continue

        date_safe = e.get('date', '').replace('/', '-')
        theme_safe = e.get('theme', '').replace('/', '-')
        out_name = f'{idx:02d}_{date_safe}_{theme_safe}.mp3'
        out_path = os.path.join(mix_dir, out_name)

        tts_dur = ffprobe_duration(tts_path)
        result = mix_one(tts_path, bed_path, out_path, bed_volume_db=bed_db)
        if result:
            out_dur = ffprobe_duration(result)
            print(f'  {idx:2d}. {e.get("theme","?")[:14]:14s}  '
                  f'tts={tts_dur:4.1f}s  bed={mood:12s}  '
                  f'-> {out_dur:4.1f}s  ({os.path.getsize(result):,}b)')
            ok += 1

    print(f'\nDone. {ok}/{len(entries)} mixed, {missing_tts} TTS missing, {missing_bed} bed missing.')
    print(f'Output -> {mix_dir}')
    if missing_tts or missing_bed:
        sys.exit(1)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', default=r'audio\manifest.json')
    ap.add_argument('--tts-dir', default=r'audio\tts')
    ap.add_argument('--beds-dir', default=r'audio\music')
    ap.add_argument('--mix-dir', default=r'audio\mixed')
    ap.add_argument('--bed-db', type=float, default=-10.0,
                    help='Bed volume in dB (negative = quieter than speech). Default -10.')
    args = ap.parse_args()
    main(args.manifest, args.tts_dir, args.beds_dir, args.mix_dir, args.bed_db)