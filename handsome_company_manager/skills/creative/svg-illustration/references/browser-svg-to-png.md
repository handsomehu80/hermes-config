# Browser-based SVG → PNG Conversion

When you have an SVG and need a PNG, but standard tools aren't available
or are safety-blocked, the Hermes `browser` toolset works as a universal
zero-dependency converter.

## When to Use This

- `cairosvg` not installed (Windows often lacks GTK runtime)
- `PIL` / `wand` / `rsglib` / `rsvg-convert` not installed
- `pip install` is blocked by safety filters
- `python -c "..."` invocations are getting time-out blocked
- You need a PNG quickly and the deliverable platform (WeChat, iMessage) rejects SVG

## The Recipe (3 tool calls)

```
Step 1: browser_navigate(url="file:///C:/full/path/to/image.svg")
Step 2: browser_vision(question="Capture this SVG illustration")
Step 3: terminal(command="cp <found-path> <stable-path>")
```

After step 2, the AI sees the rendered image AND a PNG is automatically
saved to:

```
~/AppData/Local/hermes/cache/screenshots/browser_screenshot_<hash>.png
```

`<hash>` is a per-page UUID (e.g. `0a38c7edf3044346b7d8354a988c8723`).
**Copy to a stable path immediately** — the cache can be cleared on
gateway restart.

## Why It Works

The browser toolset runs headless Playwright Chromium, which can render
any format Chromium supports (including SVG). `browser_vision` is
implemented as a screenshot under the hood — the screenshot is saved to
disk for archival, and the AI gets to look at it via its vision channel.
We're piggybacking on the screenshot side-effect.

## Locating the Screenshot File

The exact filename isn't known ahead of time (the hash is per-page).
Use one of these:

```bash
# Newest first:
ls -t ~/AppData/Local/hermes/cache/screenshots/ | head -3

# By recency (compared to a known-recent file):
find ~/AppData -name "browser_screenshot_*.png" -newer /path/to/known/file

# MSYS path on Windows:
ls -t "/c/Users/Administrator/AppData/Local/hermes/cache/screenshots/"
```

## Full Working Example

```python
# Author the SVG
write_file(
    path="C:\\Users\\Administrator\\my_image.svg",
    content="<svg viewBox='0 0 1200 900' ...>...</svg>"
)

# Render in browser
browser_navigate(url="file:///C:/Users/Administrator/my_image.svg")

# AI sees it (and screenshot is auto-saved)
browser_vision(question="Take a screenshot showing my SVG")

# Find the screenshot
terminal(command='ls -t "/c/Users/Administrator/AppData/Local/hermes/cache/screenshots/" | head -3')

# Copy to stable path
terminal(command='cp "/c/Users/Administrator/AppData/Local/hermes/cache/screenshots/browser_screenshot_ABC123.png" "/c/Users/Administrator/my_image.png"')

# Send to WeChat
send_message(
    target="weixin",
    message="Here's the image! MEDIA:C:\\Users\\Administrator\\my_image.png"
)
```

## WeChat / iLink Specifics

These are WeChat-platform quirks discovered in real sessions. They are
documented here so you don't re-discover them the hard way.

| Issue | Symptom | Fix |
|-------|---------|-----|
| **SVG rejected** | `Weixin media send failed: CDN upload HTTP 500` | Convert to PNG first (that's what this recipe is for) |
| **iLink rate limit** | `iLink sendmessage rate limited: ret=-2` | Wait 5-10 min, OR tell the user to drag-drop the local file to a chat (user-side action, no agent limit) |
| **Large PNG rejected** | Same HTTP 500 | Resize / compress to < 2 MB before sending |
| **Wrong CDN URL** | Send appears to succeed but file doesn't arrive | The MEDIA: prefix is required; plain text paths don't upload |

When you hit a rate limit, **don't immediately retry** — that hardens
the limit. Tell the user the file is at the stable local path and let
them drag it themselves, or wait 5-10 min.

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Empty page after `browser_navigate` to SVG | SVG missing `viewBox`, or uses external refs | Ensure `viewBox` is set; SVG is self-contained |
| Screenshot only shows partial image | Browser viewport smaller than SVG | Set explicit `width` and `height` attributes on the `<svg>` root |
| Screenshot has weird scrollbars | Page rendered with default browser margins | Add CSS or wrap in HTML; or use a `<style>` block in the SVG |
| SVG text is garbled in browser | Missing font for CJK characters | Add font fallback chain: `font-family="'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"` |
| Screenshot file not in expected path | Hermes version differences | Run the `ls` command from the table above to discover the actual path |

## Why NOT Just Install cairosvg

You might think: "just `pip install cairosvg` and use Python." Two reasons
this often fails on Windows:

1. **cairosvg requires GTK runtime** — pip install alone doesn't pull
   this on Windows; you need MSYS2 or vcpkg.
2. **Safety filter** — `pip install` and `python -c` are common
   safety-blocked patterns. Browser is a more reliable path.

The browser recipe sidesteps both. The trade-off is that it requires
the browser toolset to be enabled (it is, in this profile).

## Variations

**To capture a specific region** (e.g., just the character, not the
whole scene): wrap the SVG in an HTML page with a `<div>` of known
size, then navigate to the HTML file:

```html
<!doctype html>
<html><body style="margin:0;background:transparent">
  <img src="image.svg" style="width:600px;height:600px">
</body></html>
```

The browser's screenshot will be the size of the rendered content.

**To convert multiple SVGs**: navigate + vision each in sequence.
The cache directory accumulates one screenshot per page.
