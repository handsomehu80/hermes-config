# -*- coding: utf-8 -*-
"""
Concatenate all per-entry mixed mp3s into a single 'whole story' mp3 with
brief silence gaps between entries. Useful for "play everything in order" mode.

Usage:
    python concat_story.py
    python concat_story.py --mix-dir audio/mixed --gap 1.5 --out whole_story.mp3
"""
import os, subprocess, glob, argparse, sys

def main(mix_dir, out_path, gap_sec):
    files = sorted(glob.glob(os.path.join(mix_dir, '*.mp3')))
    if not files:
        print(f'ERROR: no mp3 files in {mix_dir}', file=sys.stderr)
        sys.exit(2)
    print(f'Concatenating {len(files)} tracks with {gap_sec}s gaps...')

    parts = []
    for i, f in enumerate(files):
        parts.append(f"[{i}:a]apad=pad_dur={gap_sec}[a{i}]")
    concat = ''.join(f"[a{i}]" for i in range(len(files))) + \
             f"concat=n={len(files)}:v=0:a=1[out]"
    filter_complex = ';'.join(parts) + ';' + concat

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
        print(f'FAIL: {r.stderr[:500]}', file=sys.stderr)
        sys.exit(1)

    sz = os.path.getsize(out_path)
    r2 = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', out_path],
                        capture_output=True, text=True)
    dur = float(r2.stdout.strip() or 0)
    print(f'OK -> {out_path}')
    print(f'    size: {sz:,} bytes ({sz/1024:.0f} KB)')
    print(f'    dur : {dur:.1f}s ({dur/60:.1f} min)')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mix-dir', default=r'audio\mixed')
    ap.add_argument('--out', default=r'audio\whole_story.mp3')
    ap.add_argument('--gap', type=float, default=1.0,
                    help='Silence gap between entries (seconds, default 1.0)')
    args = ap.parse_args()
    main(args.mix_dir, args.out, args.gap)