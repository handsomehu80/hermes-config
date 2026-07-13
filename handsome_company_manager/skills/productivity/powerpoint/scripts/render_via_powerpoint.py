#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Render a .pptx to per-slide PNGs via Microsoft PowerPoint COM automation.

Why this exists:
  Most Hermes Windows hosts ship with Microsoft Office but NOT LibreOffice
  or Poppler. The standard `soffice + pdftoppm` QA path in this skill
  silently fails there. PowerPoint COM via pywin32 ships with the OS Python
  install on Windows and renders any .pptx faithfully — including CJK
  fonts, gradients, transparency, smart art.

Usage:
    python scripts/render_via_powerpoint.py <path/to/deck.pptx> <out_dir>
    python scripts/render_via_powerpoint.py <path/to/deck.pptx> <out_dir> --width 1920 --height 1080

Outputs one PNG per slide named slide-01.png, slide-02.png, ...

Dependencies:
    pip install pywin32   (usually pre-installed on Windows hosts with Office)
"""

import argparse
import os
import sys


def probe_com():
    """Return a PowerPoint.Application instance, or raise a clear error."""
    try:
        import win32com.client as win32
    except ImportError as e:
        raise SystemExit(
            'pywin32 is not installed. Run: python -m pip install pywin32'
        ) from e

    ppt = win32.Dispatch('PowerPoint.Application')
    # Run hidden so it doesn't pop a window.
    try:
        ppt.Visible = 0
    except Exception:
        pass
    try:
        ppt.DisplayAlerts = 0
    except Exception:
        pass
    return ppt


def render(pptx_path, out_dir, width, height):
    ppt = probe_com()

    pptx_abs = os.path.abspath(pptx_path)
    if not os.path.exists(pptx_abs):
        raise SystemExit(f'pptx not found: {pptx_abs}')

    out_abs = os.path.abspath(out_dir)
    os.makedirs(out_abs, exist_ok=True)

    # ReadOnly, no window, not added to recent files.
    deck = ppt.Presentations.Open(
        pptx_abs, ReadOnly=True, Untitled=False, WithWindow=False
    )
    n = len(deck.Slides)
    print(f'Deck has {n} slides')
    print(f'Output dir: {out_abs}')
    print(f'Resolution: {width}x{height}')

    try:
        for i in range(1, n + 1):
            slide = deck.Slides(i)
            out_name = f'slide-{i:02d}.png'
            out_path = os.path.join(out_abs, out_name)
            slide.Export(out_path, 'PNG', width, height)
            sz = os.path.getsize(out_path)
            print(f'  Slide {i:02d}: saved {out_name}  ({sz:,} bytes)')
    finally:
        # Always close — leaked PowerPoint processes are sticky on Windows.
        deck.Close()
        ppt.Quit()

    print('Done.')


def main():
    p = argparse.ArgumentParser(
        description='Render PPTX -> PNG via PowerPoint COM (Windows).'
    )
    p.add_argument('pptx', help='Path to the .pptx file')
    p.add_argument('out_dir', help='Directory to write slide-NN.png files')
    p.add_argument('--width', type=int, default=1600,
                   help='Output width in pixels (default: 1600)')
    p.add_argument('--height', type=int, default=900,
                   help='Output height in pixels (default: 900)')
    args = p.parse_args()

    # Sanity check we're on Windows; this script doesn't work elsewhere.
    if sys.platform != 'win32':
        raise SystemExit(
            'This script requires Windows + Microsoft Office. '
            'On Linux/macOS, use the soffice + pdftoppm path instead.'
        )

    render(args.pptx, args.out_dir, args.width, args.height)


if __name__ == '__main__':
    main()
