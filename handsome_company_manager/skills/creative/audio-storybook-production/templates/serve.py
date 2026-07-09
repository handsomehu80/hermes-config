"""
Tiny local HTTP server for testing the audio storybook on a phone or tablet
over WiFi.

Usage:
    python serve.py            # default 8000, serves the project root
    python serve.py 9000       # custom port
    python serve.py 9000 C:\\my\\project   # custom root directory

Then:
    - Open http://localhost:PORT/audio/flipbook.html on the laptop
    - On a phone/tablet on the SAME WiFi, open http://<lan-ip>:PORT/audio/flipbook.html
      (the script prints the LAN URL when it starts)
    - Press Ctrl+C to stop

Includes `Cache-Control: no-store` so re-mixed audio files are picked up
immediately (without this, browsers may serve stale mp3s after re-mix).
"""
import http.server, socketserver, sys, os, socket

def get_lan_ip() -> str:
    """Best-effort LAN IP discovery. Falls back to 127.0.0.1."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))  # Alibaba DNS — no packets actually sent
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # Disable caching during development so re-mixed audio / re-edited html
        # are picked up on browser refresh.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        # If you need to embed the page in an iframe, uncomment the next line:
        # self.send_header("X-Frame-Options", "ALLOWALL")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ROOT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))

    os.chdir(ROOT)
    ip = get_lan_ip()
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print("=" * 60)
        print(f"📖  Audio Storybook · Local server")
        print(f"    Root : {ROOT}")
        print(f"    Local:   http://localhost:{PORT}/audio/flipbook.html")
        print(f"    LAN  :   http://{ip}:{PORT}/audio/flipbook.html")
        print(f"    (phone/tablet must be on the same WiFi)")
        print(f"    Ctrl+C to stop")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Stopped")