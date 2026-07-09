---
name: svg-illustration
description: "Hand-craft illustrated images in pure SVG (二次元 / anime / cartoon / cute mascots / festival cards) and convert them to PNG via the browser tool when Python image libraries aren't available or are safety-blocked. Use when the user wants a 二次元/anime/卡通/cute character scene, OR when you have an SVG but need a PNG (e.g., for WeChat CDN which rejects SVG with HTTP 500). Covers both authoring and zero-dependency conversion."
version: 1.0.0
author: MiniMax-M3
license: MIT
metadata:
  hermes:
    tags:
      - svg
      - illustration
      - anime
      - 二次元
      - image-generation
      - fallback
      - creative
      - no-deps
    category: creative
---

# SVG Illustration

Hand-craft illustrated images in pure SVG markup, plus a zero-dependency way
to convert them to PNG when standard image libraries aren't available or are
blocked by safety filters.

## When to Use

- User wants a 二次元 / anime / cute character / mascot / festival-card style image
- You have an SVG (this skill's output, an exported design, etc.) but need a PNG
- The deliverable platform (WeChat, iMessage, Discord) rejects SVG
- `cairosvg` / `PIL` / `wand` / `rsvg-convert` are not installed AND `pip install` is blocked
- A quick illustration is needed and the user can't wait for ComfyUI to install a 7 GB model

## When NOT to Use

- User wants photorealistic AI output → use the `comfyui` skill
- User wants true anime model output (Anything V5, Counterfeit, AOM3, etc.) → use `comfyui`
- Vector logo / icon work → use design tools directly
- High-fidelity art with complex lighting / anatomy / perspective → AI gen wins

## Quick Start

1. **Author SVG** with `write_file` directly. Templates in this skill:
   - `templates/anime-festival-scene.svg` — full 二次元 scene with character + traditional Chinese festival background
   - (more templates can be added under `templates/`)

2. **Verify visually** by sending to the AI vision via `browser_navigate` + `browser_vision`. The AI sees the rendered output and you can iterate.

3. **Convert to PNG** when the destination needs it (full recipe in `references/browser-svg-to-png.md`):
   - `browser_navigate(url="file:///C:/path/to/image.svg")`
   - `browser_vision(question="Capture this image")` → saves to `~/AppData/Local/hermes/cache/screenshots/browser_screenshot_<hash>.png`
   - Copy to a stable path immediately (cache can be cleared).

## Style Anatomy (二次元 / Anime)

Key visual signatures that make a flat SVG read as anime:

- **Big eyes** with layered iris (gradient color + dark pupil) + 2 white sparkles (large upper-left + small lower-right)
- **Small nose** (tiny curve) **+ simple mouth** (just a smile arc, optional tiny fill)
- **Blush cheeks** as soft pink radial gradients
- **Egg-shaped face** with hair covering ears or pulled into twin tails / ponytail
- **Hair with bangs** as a separate path layer over the face (front bangs + side strands)
- **Hanfu / sailor / lolita** clothing with gold trim and traditional cloud patterns
- **Decoration** — ribbons, sparkles, sakura petals, hearts, kawaii stickers
- **Background** — gradient sky (pink/blue) + simple mountain silhouettes + water lines

A successful 二次元 feel: eye height ≥ 25% of face height, no harsh shadows, color palette dominated by 2-3 hues.

## Technical Tips

- viewBox `1200×900` (4:3) is a good default for WeChat delivery
- Use `<defs>` + `<linearGradient>` / `<radialGradient>` for cel-shaded depth without raster effects
- Sparkle path (4-point star, centered at `cx,cy` with radius `r`):
  ```
  M cx,cy-r L cx+r/4,cy-r/4 L cx+r,cy L cx+r/4,cy+r/4 L cx,cy+r L cx-r/4,cy+r/4 L cx-r,cy L cx-r/4,cy-r/4 Z
  ```
- Eye sparkle pattern: large upper-left ellipse (~30% of iris) + small lower-right ellipse (~10%)
- Keep stroke widths consistent (1-3) for a cel-shaded look
- Avoid heavy Gaussian blurs — flat colors read as anime better
- Build characters on a `<g transform="translate(x,y)">` so you can move the whole group

## Pitfalls

1. **Don't over-detail** — anime aesthetic favors flat, simple shapes. Too much shading / gradients looks like a 3D render, not 二次元.
2. **Eyes must dominate face** — for 二次元 feel, eye height ≥ 25% of face height. Shrink face / enlarge eyes if needed.
3. **Save before complex renders** — SVG editing gets unwieldy past 500 lines. Save incremental checkpoints with versioned names.
4. **CDN-rejected formats** — WeChat CDN rejects SVG with HTTP 500. Always convert to PNG before `send_message` to WeChat.
5. **Browser screenshot cache is fragile** — screenshot files are at `~/AppData/Local/hermes/cache/screenshots/browser_screenshot_<hash>.png`. The hash is per-page; **copy to a stable path immediately** after capture.
6. **WeChat iLink rate limit** — file sends can hit `ret=-2`. Wait 5-10 min, OR tell the user to drag-drop the local file to a chat themselves (user-side action bypasses agent limit).
7. **Single-quoted SVG attributes can break some renderers** — use double-quoted attributes everywhere.
8. **Hero/center character needs breathing room** — leave 5-10% margin on all sides; otherwise the SVG feels cramped on smaller devices.
9. **Text needs a font fallback chain** — `font-family="'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"` covers Windows + macOS + Linux.

## Verification

After authoring:
- [ ] Open in browser — check that text renders, gradients are smooth, no missing paths
- [ ] Use `browser_vision` to capture and look at the result yourself
- [ ] Test on the deliverable platform — actually try sending to WeChat / Discord / etc. before declaring done
- [ ] If sending to a rate-limited platform, send ONCE, then wait if you get a rate-limit error (don't retry immediately)

## Reference

- `references/browser-svg-to-png.md` — full recipe for converting SVG to PNG using only the browser tool, including WeChat delivery specifics
- `templates/anime-festival-scene.svg` — 二次元 character + 端午 festival background starter
