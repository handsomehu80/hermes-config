# -*- coding: utf-8 -*-
"""
Regenerate Chinese (or other-language) TTS readings for all entries in a manifest
using Microsoft Edge TTS via the edge-tts package.

Configuration is at the top — change MANIFEST, OUT_DIR, VOICE for your project.

Default voice: zh-CN-XiaoxiaoNeural (warm female Chinese, best for kids storybook)

Usage:
    python regen_tts.py
    python regen_tts.py --manifest /path/to/manifest.json --voice zh-CN-XiaoyiNeural
"""
import asyncio, os, json, argparse, sys, edge_tts, time

DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural'
RATE = '-5%'    # slightly slower than default — better for kids storytelling
PITCH = '+0Hz'  # neutral pitch

async def synth_one(text: str, out_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH)
    await communicate.save(out_path)

async def run(manifest_path: str, out_dir: str, voice: str, force: bool):
    if not os.path.isfile(manifest_path):
        print(f'ERROR: manifest not found: {manifest_path}', file=sys.stderr)
        sys.exit(2)
    with open(manifest_path, encoding='utf-8') as f:
        entries = json.load(f)

    os.makedirs(out_dir, exist_ok=True)

    print(f'Voice: {voice}  rate={RATE}  pitch={PITCH}')
    print(f'Manifest: {manifest_path}  ({len(entries)} entries)')
    print(f'Output  : {out_dir}\n')

    t0 = time.time()
    ok, fail = 0, 0
    for e in entries:
        idx = e['idx']
        date = e.get('date', f'idx{idx}')
        theme = e.get('theme', f'entry{idx}')
        # Short ascii slug from theme (avoid non-ascii in filenames)
        slug = ''.join(c if c.isascii() and c.isalnum() else '' for c in theme)[:20] or f'page{idx}'
        out_name = f'{idx:02d}_{date}_{slug}.mp3'
        out_path = os.path.join(out_dir, out_name)

        if not force and os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print(f'  [{idx:2d}/{len(entries)}] SKIP {out_name}  (exists, {os.path.getsize(out_path):,}b)')
            ok += 1
            continue

        try:
            await synth_one(e['tts_text'], out_path, voice)
            sz = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            print(f'  [{idx:2d}/{len(entries)}] OK   {out_name}  ({sz:,}b)  '
                  f'{e["tts_text"][:40].strip()}…')
            ok += 1
        except Exception as ex:
            print(f'  [{idx:2d}/{len(entries)}] FAIL {out_name}  {ex}', file=sys.stderr)
            fail += 1

    dt = time.time() - t0
    print(f'\nDone. {ok}/{len(entries)} ok, {fail} fail, {dt:.1f}s elapsed')

    if fail:
        print('Some entries failed. Common causes:', file=sys.stderr)
        print('  - Network blocked (Edge TTS service unreachable)', file=sys.stderr)
        print('  - Wrong voice name (try zh-CN-XiaoxiaoNeural explicitly)', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', default=r'audio\manifest.json',
                    help='Path to manifest.json with [{idx, tts_text, ...}]')
    ap.add_argument('--out-dir', default=r'audio\tts',
                    help='Output directory for TTS mp3s')
    ap.add_argument('--voice', default=DEFAULT_VOICE,
                    help=f'Edge TTS voice name (default: {DEFAULT_VOICE})')
    ap.add_argument('--force', action='store_true',
                    help='Regenerate even if file exists')
    args = ap.parse_args()
    asyncio.run(run(args.manifest, args.out_dir, args.voice, args.force))