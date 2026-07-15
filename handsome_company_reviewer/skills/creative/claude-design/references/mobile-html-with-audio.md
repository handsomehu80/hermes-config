# Mobile HTML artifacts with audio + cross-device serving

When a one-off HTML artifact needs to:
- play audio (TTS, music, narration)
- be viewed on a phone/tablet over WiFi (not just the laptop)

Use the patterns below. They cover the footguns that mobile Safari / Chrome-on-Android introduce on top of a normal self-contained HTML deliverable.

## 1. iOS audio gesture gate (mandatory)

Mobile Safari (and Android Chrome in some states) **silently refuses `audio.play()` until a user gesture occurs in the current page**. This breaks naive auto-play on page load and also breaks `play()` triggered from a `setTimeout` / `fetch` callback.

**Pattern: gate overlay that hides on first tap, then primes the audio element.**

```html
<div class="gate" id="gate">
  <h1>标题</h1>
  <p>手机浏览器要先点一下才能播放声音。</p>
  <button class="big" id="gateBtn">▶ 开始</button>
</div>

<audio id="audio" preload="auto"></audio>

<script>
let unlocked = false;
const audio = document.getElementById('audio');
const gate  = document.getElementById('gate');

gateBtn.addEventListener('click', () => {
  unlocked = true;
  gate.classList.add('hidden');
  audio.src = FIRST_SRC;
  audio.load();
  audio.play();   // user gesture → allowed
});

function play(){ if(!unlocked) return; audio.play().catch(()=>{}); }
</script>

<style>
.gate{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center}
.gate.hidden{display:none}
</style>
```

**After unlock**, `play()` works from any handler — including setTimeout, async fetches, click handlers on other buttons, swipe handlers, keyboard handlers. The `unlocked` flag is just a safety net to re-show the gate if the user reloads.

**Pitfall:** If you `<audio autoplay>` on a single-audio page without the gate, you'll hear audio on desktop but get a silent failure on phone. Test on a real phone, not just desktop Chrome.

## 2. Single `<audio>` element, swap `src` on page change

For a paginated reader (page 1 of 19, page 2 of 19, ...), use **one** `<audio>` element and change its `src`. Don't create a new audio per page — iOS will hit a per-element gesture limit.

```js
function goto(i){
  audio.src = entries[i].audio;
  audio.load();
  // do NOT auto-call play() here unless the caller is itself a user gesture
}

nextBtn.addEventListener('click', ()=>{
  goto(++cur);
  play();          // OK: prev/next button click counts as a gesture
});
```

**Why not just `<audio src="...">` per page?** Same-origin src swap works on desktop, but iOS Safari has stricter rules — keep one element to be safe.

## 3. Mobile viewport meta

```html
<meta name="viewport"
      content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#1A1B2E">
```

- `viewport-fit=cover` lets you draw under the iPhone notch.
- `maximum-scale=1.0` + `user-scalable=no` is fine for kid/reader apps where pinch-zoom isn't wanted.

## 4. iPhone notch / home indicator CSS

```css
:root {
  --safe-t: env(safe-area-inset-top, 0px);
  --safe-b: env(safe-area-inset-bottom, 0px);
}
.app { padding: calc(var(--safe-t) + 10px) 12px calc(var(--safe-b) + 10px); }
```

Without this, the bottom controls sit under the home indicator on notched iPhones.

## 5. Auto dark-mode (kids read in bed)

```css
:root { --bg:#FFF8F0; --ink:#2C2C2C; --accent:#FF8B6A; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#1A1B2E; --ink:#F5F5F7; --accent:#FFD56B; }
}
```

No JS toggle needed. `theme-color` meta + this CSS gives a system-matching experience.

## 6. Touch gestures (swipe + tap zones)

Two approaches that compose well:

**Tap zones** — invisible left/right halves of the screen:
```html
<div class="tapzone l" id="tzL"></div>
<div class="tapzone r" id="tzR"></div>
<style>.tapzone{position:absolute;top:0;bottom:0;width:30%;z-index:5}
.tapzone.l{left:0}.tapzone.r{right:0}</style>
```

**Swipe** — record start, compare end:
```js
let tx=0;
document.addEventListener('touchstart', e=>{ tx=e.touches[0].clientX; }, {passive:true});
document.addEventListener('touchend',   e=>{
  const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) > 50) (dx<0 ? nextBtn : prevBtn).click();
}, {passive:true});
```

Threshold ~50px feels right for kids (smaller for adults). Require `|dx| > |dy|*1.5` to avoid hijacking vertical scroll.

## 7. Serving the artifact to a phone on the same WiFi

The deliverable lives on the laptop. The user wants to view it on their phone without uploading anywhere. Drop a tiny `serve.py` next to the artifact folder and run it.

```python
# serve.py — bind 0.0.0.0, auto-detect LAN IP, serve a folder
import http.server, socketserver, sys, socket
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))   # just for routing — no packets sent
        ip = s.getsockname()[0]
        s.close(); return ip
    except Exception:
        return "127.0.0.1"

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=".", **kw)
    def end_headers(self):
        self.send_header("Cache-Control","no-store")
        super().end_headers()

with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), H) as httpd:
    httpd.allow_reuse_address = True
    print(f"http://localhost:{PORT}/  (手机 http://{lan_ip()}:{PORT}/)")
    httpd.serve_forever()
```

**Pitfalls:**
- Windows Firewall will pop a one-time prompt the first time. Tell the user it's expected.
- The phone must be on the **same WiFi** (not a guest network, not cellular).
- Some routers do AP isolation by default. If the phone can't reach the laptop IP, that's why.

## 8. File layout for relative-path portability

Put the HTML at `D:\some\project\output\reader.html` with assets at `D:\some\project\images\` and `D:\some\project\audio\`. Then in HTML use `../images/foo.jpeg` and `../audio/bar.mp3`. This works via `file://` (drag HTML into browser) AND over `http://` from the serve.py script — same paths in both modes.

If you instead inline assets as base64 the file becomes large and you lose cacheability across pages. Only inline tiny things (icons, fonts).

## 9. TOC / chapter grid pattern

For 19+ entries, render thumbnails via `background-image` on a `<div>` rather than `<img>` tags — much faster first paint, no per-image reflow:

```html
<div class="ti" style="background-image:url('../images/p04.jpeg')"></div>
<style>.ti{width:100%;aspect-ratio:4/3;background:center/cover no-repeat}</style>
```

Highlight current page with an `outline` (not border, to avoid layout shift):
```css
.toc-item.cur { outline: 3px solid var(--accent); outline-offset: -3px; }
```

## 10. Verification recipe

After writing the HTML, verify in this order:
1. `terminal(background=true)` to start `serve.py` on an unused port (8765 is usually free).
2. `curl http://localhost:8765/path` — confirm 200 + reasonable byte count.
3. `browser_navigate` to that URL — confirm DOM loads.
4. `browser_click` the start button — confirm gate hides.
5. `browser_click` next page — confirm counter increments via `browser_console` JS read.
6. `browser_vision` a screenshot — confirm visual layout matches intent.
7. Kill the background server with `process(action='kill', session_id=...)`.

Do **not** skip the real-device test if mobile fidelity matters. Desktop Chrome in mobile-emulation mode lies about: audio gesture enforcement, `safe-area-inset` behavior, iOS-specific CSS quirks.

## 11. Things that look fine on desktop but break on phone

- `audio.play()` with no prior gesture (silent fail)
- `100vh` in CSS (covers under URL bar; use `100dvh` or fixed-position with `inset:0`)
- Fixed bottom bars without `safe-area-inset-bottom` (sits under home indicator)
- `tap-highlight-color` not set to `transparent` (annoying blue flash on tap)
- Touch events without `{passive:true}` (causes scroll jank warnings)
- `<input>` inside a scroll container (zoom-on-focus jumps layout)