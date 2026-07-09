# Web-Viewable Content → Image Capture (Windows Fallback)

When you need to convert an SVG (or HTML page, or any web-renderable file) to a PNG/JPG on a Windows machine where image libraries aren't installed, the browser tool is the fastest fallback.

## When to use

- `cairosvg`, `Pillow`, `svglib`, `wand` all missing on the host.
- Need a raster image (PNG/JPG) from a vector source (SVG) or a rendered web page.
- Don't want to spend 5+ minutes `pip install`ing a 50MB dep chain that may also need native libs (GTK, etc.).

## Procedure

1. **Write the file** at an absolute path, e.g. `C:\Users\Administrator\foo.svg`.
2. **Open it in the browser tool** with a `file:///` URL:
   ```
   browser_navigate(url="file:///C:/Users/Administrator/foo.svg")
   ```
3. **Take a screenshot** — `browser_vision(question="...")` saves to the Hermes screenshot cache:
   ```
   C:\Users\Administrator\AppData\Local\hermes\cache\screenshots\browser_screenshot_<hash>.png
   ```
4. **Copy to a stable path** if you need to keep it (the cache hash is non-deterministic):
   ```bash
   cp "...cache/screenshots/browser_screenshot_<hash>.png" "C:/Users/Administrator/foo.png"
   ```
5. **Send the PNG to WeChat** with `send_message` including `MEDIA:<path>`. WeChat CDN rejects SVG directly — always go SVG → PNG first.

## Why this works

The Hermes browser tool uses Playwright Chromium (already installed for general web work). Chromium renders SVG/HTML/CSS fully — including gradients, filters, transforms, web fonts. A screenshot is a perfect pixel-perfect raster of what the user would see in a browser tab.

## Variants

- **HTML pages with external assets**: `browser_navigate` then `wait_for_load_state("networkidle")` if you do it programmatically. The `browser_vision` tool's question also works as a rendering trigger.
- **PDF / DOCX → image**: same pattern, navigate to `file:///` URL of the document, screenshot.
- **Web app state capture**: navigate to a running app's URL, screenshot.
- **Frame extraction from MP4** (when Manim already rendered): use ffmpeg directly, no browser needed:
  ```bash
  ffmpeg -y -i input.mp4 -vf "fps=1/3" frame_%02d.png
  ```

## Pitfalls

- **Screenshot path is hashed**: don't rely on the cache path being reproducible — copy to a stable location first.
- **WeChat rate limits are aggressive**: multiple `send_message` calls in quick succession get HTTP 500 / "iLink rate limited". Wait 5–10 min between bursts, or probe with text-only first.
- **WeChat CDN rejects SVG**: must convert to PNG/JPG/MP4 before sending as `MEDIA:`.
- **Browser headless mode = no animations during render**: `browser_vision` captures a single static frame. For animated content, render to MP4 (Manim) or GIF, not screenshots.
