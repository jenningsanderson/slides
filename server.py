#!/usr/bin/env python3
"""
server.py — Live-reload development server for the slide presentation.

Serves the project from the current directory, watches slides/ and css/
for changes, automatically rebuilds index.html on save, and signals
connected browsers to reload via a polling endpoint — no external
dependencies beyond build.py's requirements.

Usage:
    python3 server.py              # serve on http://localhost:3000
    python3 server.py --port 8080  # custom port
    python3 server.py --no-open    # do not open browser automatically
"""

import argparse
import http.server
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared build state
# ---------------------------------------------------------------------------

_state: dict = {"version": 0, "error": None}
_state_lock = threading.Lock()


def _increment() -> int:
    with _state_lock:
        _state["version"] += 1
        _state["error"] = None
        return _state["version"]


def _set_error(msg: str) -> None:
    with _state_lock:
        _state["error"] = msg


def _get_version() -> int:
    with _state_lock:
        return _state["version"]


# ---------------------------------------------------------------------------
# Build runner (calls build.py as subprocess to keep state isolated)
# ---------------------------------------------------------------------------

def run_build(verbose: bool = True) -> bool:
    """Invoke build.py and return True on success."""
    result = subprocess.run(
        [sys.executable, "build.py", "--no-backup"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        v = _increment()
        if verbose:
            ts = time.strftime("%H:%M:%S")
            out = result.stdout.strip().splitlines()
            summary = out[-1] if out else "done"
            print(f"[{ts}] Rebuilt (v{v}) — {summary}")
        return True
    else:
        err = (result.stderr or result.stdout).strip()
        _set_error(err)
        print(f"  Build failed: {err}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Live-reload script injected into index.html at serve time
# ---------------------------------------------------------------------------

_LIVE_RELOAD_JS = """\
<script>
/* live-reload: injected by server.py */
(function () {
  var v = null;
  function poll() {
    fetch('/__reload__', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (v === null) { v = d.v; }
        else if (d.v !== v) { location.reload(); }
      })
      .catch(function () {})
      .finally(function () { setTimeout(poll, 800); });
  }
  poll();
})();
</script>"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class _Handler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self) -> None:  # type: ignore[override]
        # Reload-check endpoint polled by the injected JS
        if self.path == "/__reload__":
            body = json.dumps({"v": _get_version()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        # Inject live-reload script when serving index.html
        if self.path in ("/", "/index.html"):
            try:
                content = Path("index.html").read_text(encoding="utf-8")
                content = content.replace("</body>", f"{_LIVE_RELOAD_JS}\n</body>", 1)
                body = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)
                return
            except FileNotFoundError:
                pass  # fall through to default handler

        super().do_GET()

    def log_message(self, fmt: str, *args: object) -> None:
        # Suppress noise from asset requests; log only page navigation
        path = str(args[0]).split()[1] if args else ""
        if not any(path.startswith(p) for p in ("/vendor/", "/css/", "/assets/", "/__")):
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] {path}")


# ---------------------------------------------------------------------------
# File watcher thread
# ---------------------------------------------------------------------------

def _watched_files(slides_dir: str = "slides") -> list[Path]:
    md = sorted(Path(slides_dir).glob("*.md")) if Path(slides_dir).is_dir() else []
    html = sorted(Path(slides_dir).glob("*.html")) if Path(slides_dir).is_dir() else []
    css = sorted(Path("css").glob("*.css")) if Path("css").is_dir() else []
    return md + html + css


def _snapshot(files: list[Path]) -> dict[str, float]:
    result: dict[str, float] = {}
    for f in files:
        try:
            result[str(f)] = os.stat(f).st_mtime
        except OSError:
            result[str(f)] = 0.0
    return result


def _watch_loop(slides_dir: str) -> None:
    files = _watched_files(slides_dir)
    prev = _snapshot(files)
    while True:
        time.sleep(0.5)
        files = _watched_files(slides_dir)
        curr = _snapshot(files)
        changed = [f for f in curr if curr[f] != prev.get(f, 0.0)]
        if changed:
            names = ", ".join(Path(f).name for f in changed)
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] Changed: {names}")
            run_build(verbose=True)
        prev = curr


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Live-reload dev server for the slide presentation.",
    )
    p.add_argument(
        "--port", type=int, default=3000,
        help="port to listen on (default: 3000)",
    )
    p.add_argument(
        "--slides-dir", default="slides", metavar="DIR",
        help="slides directory to watch (default: slides)",
    )
    p.add_argument(
        "--no-open", action="store_true",
        help="do not open the browser automatically",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if not Path("build.py").exists():
        sys.exit("Error: build.py not found. Run server.py from the project root.")

    print("Building slides...")
    run_build(verbose=False)
    print(f"  Done. Starting server on http://localhost:{args.port}\n")

    watcher = threading.Thread(
        target=_watch_loop, args=(args.slides_dir,), daemon=True
    )
    watcher.start()

    if not args.no_open:
        threading.Timer(
            0.3, lambda: webbrowser.open(f"http://localhost:{args.port}")
        ).start()

    try:
        httpd = http.server.HTTPServer(("", args.port), _Handler)
        print(f"Serving at http://localhost:{args.port}")
        print(f"Watching {args.slides_dir}/ and css/ for changes.")
        print("Press Ctrl-C to stop.\n")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        sys.exit(f"Error: {e}\nIs port {args.port} already in use? Try --port 8080")


if __name__ == "__main__":
    main()
