# -*- coding: utf-8 -*-
"""
Detect silent English-fallback TTS files via a duration heuristic.

When edge-tts is broken / package missing / network blocked, it may produce
English-pronounceable audio with only the Arabic numerals coming through.
A normal Chinese reading of a 100-150 character paragraph takes 20-35 seconds;
a broken one is usually 3-8 seconds.

Usage:
    python verify_tts.py <tts_dir> [--min-duration 15] [--warn-duration 20]

Exit codes:
    0 - all files pass
    1 - one or more files failed the duration threshold
    2 - tts_dir doesn't exist or has no mp3s

This script is the lesson-learned from the D:\\draw case where the user opened
the flipbook on their phone and heard English digits instead of Chinese —
because the TTS package had been silently uninstalled between sessions.
"""
import os, sys, subprocess, json, argparse

def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

def verify(tts_dir: str, min_dur: float, warn_dur: float):
    if not os.path.isdir(tts_dir):
        print(f'ERROR: directory not found: {tts_dir}')
        sys.exit(2)

    files = sorted(f for f in os.listdir(tts_dir) if f.lower().endswith('.mp3'))
    if not files:
        print(f'ERROR: no mp3 files in {tts_dir}')
        sys.exit(2)

    fails, warns, passes = [], [], []
    print(f'{"file":50s} {"dur":>7s}  status')
    print('-' * 75)
    for f in files:
        path = os.path.join(tts_dir, f)
        d = ffprobe_duration(path)
        if d < min_dur:
            status = f'FAIL  (likely English fallback or silent)'
            fails.append((f, d))
        elif d < warn_dur:
            status = 'WARN  (short — check if source text is also short)'
            warns.append((f, d))
        else:
            status = 'OK'
            passes.append((f, d))
        print(f'{f:50s} {d:6.2f}s  {status}')

    print('-' * 75)
    print(f'{len(passes)} OK, {len(warns)} short, {len(fails)} fail')

    if fails:
        print()
        print('Likely English-fallback TTS detected. Probable causes:')
        print('  1. edge-tts package missing: `python -m pip install edge-tts`')
        print('  2. Network blocked — Edge TTS service unreachable')
        print('  3. Wrong voice selected — non-zh voice was used by mistake')
        print('  4. Source text contained no Chinese characters (unlikely)')
        print()
        print('Fix: re-run scripts/regen_tts.py with explicit Chinese voice')
        print('     (default: zh-CN-XiaoxiaoNeural).')
        sys.exit(1)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tts_dir', help='Directory of TTS mp3 files')
    ap.add_argument('--min-duration', type=float, default=15.0,
                    help='Below this duration (sec) is treated as fail (default 15)')
    ap.add_argument('--warn-duration', type=float, default=20.0,
                    help='Below this duration (sec) is treated as warning (default 20)')
    args = ap.parse_args()
    verify(args.tts_dir, args.min_duration, args.warn_duration)