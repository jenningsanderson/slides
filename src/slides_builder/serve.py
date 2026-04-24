"""
Live-reload development server for slides-builder.

Serves the project from the current directory, watches slides/ and css/ for
changes, rebuilds index.html on save, and signals connected browsers to reload
via a polling endpoint — no external dependencies beyond build.py's requirements.
"""

import http.server
import json
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from slides_builder import build as build_mod

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
# Build runner
# ---------------------------------------------------------------------------

def _rebuild(
    slides_dir: str,
    output: str,
    project_root: str,
    title: str = "Slides",
    base_url: str = "",
    verbose: bool = True,
) -> bool:
    """Trigger a build and update the reload version counter. Returns True on success."""
    try:
        build_mod.run_build(
            slides_dir=slides_dir,
            output=output,
            project_root=project_root,
            no_backup=True,
            title=title,
            base_url=base_url,
            verbose=verbose,
        )
        v = _increment()
        if verbose:
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] Rebuilt (v{v})")
        return True
    except Exception as exc:
        _set_error(str(exc))
        print(f"  Build failed: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Live-reload script injected into index.html at serve time
# ---------------------------------------------------------------------------

_LIVE_RELOAD_JS = """\
<script>
/* live-reload: injected by server */
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
                pass

        super().do_GET()

    def log_message(self, fmt: str, *args: object) -> None:
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


def _watch_loop(
    slides_dir: str,
    output: str,
    project_root: str,
    title: str,
    base_url: str,
) -> None:
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
            _rebuild(slides_dir, output, project_root, title=title, base_url=base_url)
        prev = curr


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_server(
    slides_dir: str = "slides",
    output: str = "index.html",
    port: int = 3000,
    no_open: bool = False,
    title: str = "Slides",
    base_url: str = "",
) -> None:
    project_root = os.getcwd()

    print("Building slides...")
    _rebuild(slides_dir, output, project_root, title=title, base_url=base_url, verbose=False)
    print(f"  Done. Starting server on http://localhost:{port}\n")

    watcher = threading.Thread(
        target=_watch_loop,
        args=(slides_dir, output, project_root, title, base_url),
        daemon=True,
    )
    watcher.start()

    if not no_open:
        threading.Timer(0.3, lambda: webbrowser.open(f"http://localhost:{port}")).start()

    try:
        httpd = http.server.HTTPServer(("", port), _Handler)
        print(f"Serving at http://localhost:{port}")
        print(f"Watching {slides_dir}/ and css/ for changes.")
        print("Press Ctrl-C to stop.\n")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        sys.exit(f"Error: {e}\nIs port {port} already in use? Try --port 8080")
