# -*- coding: utf-8 -*-
"""
Generate 5 mood-matched ambient music beds using ffmpeg `lavfi` synthesis.
No external service or API required — produces acceptable background pads.

Each bed is exactly 30 seconds (24000 Hz mono, 64 kbps mp3) and designed
to loop seamlessly when the mix script extends it to match TTS duration.

Mood assignments are conventional; remap in mix.py's MOOD dict if needed.

Usage:
    python generate_music.py
    python generate_music.py --out-dir audio/music
"""
import os, subprocess, json, argparse, sys

PRESETS = {
    'warm_cosmic': {
        'desc': 'Low warm pad with slow pulse — Mars, Moon, space, science wonder.',
        'chain': (
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
    },
    'cheerful': {
        'desc': 'Brighter major-key pad with light pulse — play, fun, family.',
        'chain': (
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
    },
    'heroic': {
        'desc': 'Midrange pulse with brass-like edge — door gods, Olympics, military.',
        'chain': (
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
    },
    'tech_pulse': {
        'desc': 'Mid-tempo pulse with rhythmic pulse — robots, AI, drones.',
        'chain': (
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
    },
    'calm_dream': {
        'desc': 'Very soft dreamy pad — tender moments, gentle wishes, lullaby feel.',
        'chain': (
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
    },
}

def gen(preset_name: str, preset: dict, out_dir: str):
    out = os.path.join(out_dir, f'{preset_name}.mp3')
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-f', 'lavfi', '-i', preset['chain'],
        '-ar', '24000', '-ac', '1',
        '-b:a', '64k',
        out
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f'FAIL {preset_name}: {r.stderr}', file=sys.stderr)
        return None
    sz = os.path.getsize(out)
    print(f'OK  {preset_name}.mp3  {sz:,} bytes  ({preset["desc"]})')
    return out

def main(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    print(f'Generating {len(PRESETS)} mood beds -> {out_dir}\n')
    paths = {}
    for name, p in PRESETS.items():
        paths[name] = gen(name, p, out_dir)
    with open(os.path.join(out_dir, 'moods.json'), 'w', encoding='utf-8') as f:
        json.dump(paths, f, indent=2, ensure_ascii=False)
    print(f'\nDone. {len([p for p in paths.values() if p])}/{len(PRESETS)} beds -> {out_dir}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out-dir', default=r'audio\music',
                    help='Output directory for mood bed mp3s')
    args = ap.parse_args()
    main(args.out_dir)