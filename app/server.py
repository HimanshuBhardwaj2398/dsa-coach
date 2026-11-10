"""The local learning app: the map, a pattern's Learn page and its saved explainer, and today's progress.

    python3 app/server.py [--root NOTEBOOK] [--port 8765] [--no-browser]

Read-only: it reads the notebook through `coach.py map --json` and writes nothing. It binds to 127.0.0.1 only.
/panel is the same page for the Chrome side panel (extensions/dsa-coach), the only page another origin may frame.
Solving happens on LeetCode, and coaching and logging happen in the coach chat.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP = Path(__file__).resolve().parent
REPO = APP.parent
COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"
STATIC = APP / "static"
HOSTS = {"127.0.0.1", "localhost"}
# The stable public key in extensions/dsa-coach/manifest.json fixes the unpacked extension's ID.
PANEL_PARENT = "chrome-extension://fiahbfhmngefgmcnlacogkhhhflfomoh"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8"}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def read_map(root: Path, env: dict | None = None) -> dict:
    """Every pattern with its status, explainer and problems, plus what's due and the live solve."""
    proc = subprocess.run([sys.executable, str(COACH), "--root", str(root), "map", "--json"],
                          capture_output=True, text=True, env=env, timeout=30)
    if proc.returncode:
        raise ApiError(500, (proc.stderr or proc.stdout).strip() or "coach.py map failed")
    return json.loads(proc.stdout)


def explainer_file(root: Path, view: dict, key: str) -> Path:
    rel = next((p["explainer"] for p in view["patterns"] if p["key"] == key), None)
    path = (root / (rel or "")).resolve()
    if not rel or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ApiError(404, "no explainer for that pattern yet")
    return path


def make_handler(root: Path, env: dict | None):
    class Handler(BaseHTTPRequestHandler):
        framable = False

        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def end_headers(self):  # every answer, http.server's own error pages too
            if self.framable:
                self.send_header("Content-Security-Policy", f"frame-ancestors {PANEL_PARENT}")
            else:
                self.send_header("X-Frame-Options", "DENY")
            super().end_headers()

        def send(self, status: int, body, ctype: str = "application/json; charset=utf-8", headers: dict | None = None):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def answer(self):
            path = urlparse(self.path).path
            if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in HOSTS:
                raise ApiError(403, "this server only answers on 127.0.0.1 or localhost")
            if path == "/api/map":
                return self.send(200, read_map(root, env))
            if path.startswith("/explainer/"):
                page = explainer_file(root, read_map(root, env), path.removeprefix("/explainer/"))
                # its own origin: the page's scripts run, but can't call this server
                return self.send(200, page.read_bytes(), TYPES[".html"],
                                 {"Content-Security-Policy": "sandbox allow-scripts allow-popups"})
            name = "index.html" if path in ("/", "/panel") else path.removeprefix("/static/")
            target = (STATIC / name).resolve()
            if target.parent != STATIC.resolve() or not target.is_file():
                raise ApiError(404, "not found")
            self.framable = path == "/panel"
            self.send(200, target.read_bytes(), TYPES.get(target.suffix, "application/octet-stream"))

        def do_GET(self):
            try:
                self.answer()
            except ApiError as e:
                self.send(e.status, {"error": e.message})
            except ConnectionError:  # the page went away (a reload, a closed tab): there's no one to answer
                return
            except Exception as e:  # a bug, or a file changed under it: the page still gets an answer to show
                traceback.print_exc()
                self.send(500, {"error": f"{type(e).__name__}: {e}"})

        def do_POST(self):
            self.send(405, {"error": "the learning app is read-only; log work through the coach"})

        do_PUT = do_DELETE = do_POST

    return Handler


def in_use(port: int) -> bool:
    """True if a server already answers on port at 127.0.0.1 or ::1. This server could still bind 127.0.0.1:port,
    on macOS even while that one listens on *:port (SO_REUSEADDR), and then localhost:port could reach either."""
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            pass
    return False


def make_server(root: Path, port: int = 8765, env: dict | None = None, tries: int = 10) -> ThreadingHTTPServer:
    handler = make_handler(Path(root), env)
    for p in [0] if port == 0 else range(port, port + tries):
        if p and in_use(p):
            continue
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), handler)
        except OSError:
            continue
    raise SystemExit(f"no free port in {port}-{port + tries - 1}; pass --port")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="dsa-coach learning app: map, Learn pages and explainers (read-only)")
    p.add_argument("--root", type=Path, help="notebook folder (default: $DSA_NOTEBOOK, else ./notebook in the repo)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)
    root = (a.root or Path(os.environ.get("DSA_NOTEBOOK") or REPO / "notebook")).resolve()
    if not (root / "config.json").exists():
        raise SystemExit(f"{root} isn't a dsa-coach notebook (no config.json). Pass --root.")
    server = make_server(root, a.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"dsa-coach learning app: {url}  (notebook: {root})  Ctrl+C stops it", flush=True)
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
