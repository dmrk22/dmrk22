#!/usr/bin/env python3
"""Local server for the plate maker.

Serves this repo at http://127.0.0.1:<port>/ so tools/build.html can load its fonts,
and accepts POST /save/<name>.svg so the page can write finished plates into assets/.
Nothing outside assets/ is writable, and only .svg files.

    python3 tools/serve.py [port]      # default 8765, then open /tools/build.html
"""
import http.server
import os
import pathlib
import signal
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MAX_BYTES = 2_000_000  # a plate is 5-60 KB; anything near this size is a bug


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        name = self.path.removeprefix("/save/")
        target = (ASSETS / name).resolve()
        size = int(self.headers.get("Content-Length") or 0)
        if (not self.path.startswith("/save/") or target.parent != ASSETS
                or target.suffix != ".svg" or not 0 < size <= MAX_BYTES):
            self.send_error(403, "only POST /save/<name>.svg, into assets/")
            return
        body = self.rfile.read(size)
        if len(body) != size:  # client went away mid-upload: keep the old plate
            self.send_error(400, "short body")
            return
        # Write beside the target, then swap, so a crash never leaves half a plate.
        fd, tmp = tempfile.mkstemp(dir=ASSETS, suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(body)
        os.replace(tmp, target)
        self.send_response(204)
        self.end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ASSETS.mkdir(exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    # SIGTERM (a closed preview pane, kill) exits as cleanly as Ctrl-C does.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print(f"plate maker: http://127.0.0.1:{port}/tools/build.html", flush=True)
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
