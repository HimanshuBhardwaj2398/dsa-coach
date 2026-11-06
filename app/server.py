"""Local server for the dsa-coach study app (v1: the Solve tab).

    python3 app/server.py [--root NOTEBOOK] [--port 8765] [--no-browser]

It binds to 127.0.0.1 only. Every change to the notebook's records goes through coach.py. The server itself
writes only the live solve's attempt file and problems/<slug>/problem.md.
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import subprocess
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
import attempt_file  # noqa: E402
import runner  # noqa: E402

REPO = APP.parent
COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"
STATIC = APP / "static"
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,254}")  # used with fullmatch; 255 is the longest name a folder can have
HOSTS = {"127.0.0.1", "localhost"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8"}
MAX_BODY = 10_000_000  # bytes in a request body


class ApiError(Exception):
    def __init__(self, status: int, message: str, extra: dict | None = None):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra or {}


class Coach:
    """coach.py against one notebook."""

    def __init__(self, root: Path, env: dict | None = None):
        self.root, self.env = Path(root), env

    def run(self, *args: str) -> str:
        try:
            proc = subprocess.run([sys.executable, str(COACH), "--root", str(self.root), *args],
                                  capture_output=True, text=True, env=self.env)
        except ValueError:  # a NUL character can't go on a command line
            raise ApiError(400, "the text has a NUL character; take it out and try again") from None
        except OSError as e:
            if e.errno != errno.E2BIG:
                raise
            raise ApiError(400, "the text is too long to pass to coach.py; shorten it and try again") from None
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout).strip().removeprefix("error: ")
            raise ApiError(409 if "already live" in message else 400, message)
        return proc.stdout.strip()

    def json(self, *args: str):
        return json.loads(self.run(*args, "--json"))


# helpers ----------------------------------------------------------------------
def need(d: dict, key: str, kind: type, blank_ok: bool = False):
    value = d.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) and kind is int:
        raise ApiError(400, f"missing or wrong {key}")
    if kind is str and not blank_ok and not value.strip():
        raise ApiError(400, f"{key} is empty")
    return value


def check_slug(value) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise ApiError(400, "a problem slug is lowercase letters, digits and dashes, 255 at most")
    return value


def live_solve(coach: Coach) -> dict:
    live = coach.json("solve", "show")
    if live is None:
        raise ApiError(409, "no live solve")
    return live


def read_attempt(path: Path, live: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    out = {"file": live["file"], "path": str(path), "text": text, "mtime": path.stat().st_mtime_ns,
           "plan_card": attempt_file.read_plan_card(text), "examples": [], "examples_error": None}
    try:
        out["examples"] = attempt_file.read_examples(text)
    except ValueError as e:
        out["examples_error"] = str(e)
    return out


def same_mtime(sent, actual: int) -> bool:
    """True if sent is the file's mtime_ns as the page holds it: a JavaScript number keeps 53 bits of it."""
    try:
        return isinstance(sent, (int, float)) and float(sent) == float(actual)
    except OverflowError:  # an int too big for a float
        return False


def write_checked(path: Path, live: dict, text: str, d: dict) -> dict:
    """Write unless the file changed on disk since the page loaded it (pass force to overwrite anyway)."""
    if not d.get("force") and not same_mtime(d.get("mtime"), path.stat().st_mtime_ns):
        raise ApiError(409, "the attempt file changed on disk since you loaded it", read_attempt(path, live))
    path.write_text(text, encoding="utf-8")
    return read_attempt(path, live)


# routes -----------------------------------------------------------------------
def get_state(coach, q):
    live = coach.json("solve", "show")
    state = {"live": live, "next": None, "due": None, "attempt_mtime": None}
    if live:
        path = coach.root / live["file"]
        state["attempt_mtime"] = path.stat().st_mtime_ns if path.exists() else None
    else:
        state["next"], state["due"] = coach.json("next"), coach.json("due")
    return state


def get_attempt(coach, q):
    live = live_solve(coach)
    return read_attempt(coach.root / live["file"], live)


def put_attempt(coach, d):
    live = live_solve(coach)
    return write_checked(coach.root / live["file"], live, need(d, "text", str, blank_ok=True), d)


def put_parts(coach, d):
    live = live_solve(coach)
    card, rows = d.get("plan_card", {}), d.get("examples", [])
    if not isinstance(card, dict) or not all(isinstance(v, str) for v in card.values()):
        raise ApiError(400, "plan_card must be an object whose values are text")
    if not isinstance(rows, list) or not all(
            isinstance(r, dict) and isinstance(r.get("args"), str) and isinstance(r.get("expected"), str)
            and isinstance(r.get("edge", False), bool) for r in rows):
        raise ApiError(400, "each example must be an object with args and expected as text, and edge true or false")
    path = coach.root / live["file"]
    text = path.read_text(encoding="utf-8")
    try:
        if "plan_card" in d:
            text = attempt_file.write_plan_card(text, card)
        if "examples" in d:
            text = attempt_file.write_examples(text, rows)
    except ValueError as e:
        raise ApiError(400, str(e))
    return write_checked(path, live, text, d)


def post_start(coach, d):  # --name=value, so a value such as "--unlabeled" can't be read as an option
    args = ["solve", "start", f"--problem={need(d, 'problem', str).strip().lower()}",
            "--confidence", str(need(d, "confidence", int))]
    for key in ("pattern", "difficulty", "mode"):
        if d.get(key):
            args.append(f"--{key}={d[key]}")
    if d.get("unlabeled"):
        args.append("--unlabeled")
    return {"message": coach.run(*args)}


def post_stage(coach, d):
    return {"message": coach.run("solve", "stage", str(need(d, "n", int)))}


def post_note(coach, d):
    stage, text = need(d, "stage", int), need(d, "text", str, blank_ok=True)
    return {"message": coach.run("solve", "note", "--stage", str(stage), f"--text={text}")}


def post_break(coach, d):
    return {"message": coach.run("solve", "break")}


def post_block(coach, d):
    return {"message": coach.run("solve", "block")}


def post_end(coach, d):
    args = ["solve", "end", f"--outcome={need(d, 'outcome', str)}"]
    if d.get("note"):
        args.append(f"--note={d['note']}")
    return {"message": coach.run(*args)}


def get_problem(coach, q):
    path = coach.root / "problems" / check_slug(q.get("slug")) / "problem.md"
    return {"text": path.read_text(encoding="utf-8") if path.exists() else None}


def put_problem(coach, d):
    path, text = coach.root / "problems" / check_slug(d.get("slug")) / "problem.md", need(d, "text", str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"text": path.read_text(encoding="utf-8")}


def post_run(coach, d):
    return runner.run(coach.root / live_solve(coach)["file"])


ROUTES = {
    ("GET", "/api/state"): get_state,
    ("GET", "/api/attempt"): get_attempt,
    ("PUT", "/api/attempt"): put_attempt,
    ("PUT", "/api/attempt/parts"): put_parts,
    ("POST", "/api/solve/start"): post_start,
    ("POST", "/api/solve/stage"): post_stage,
    ("POST", "/api/solve/note"): post_note,
    ("POST", "/api/solve/break"): post_break,
    ("POST", "/api/solve/block"): post_block,
    ("POST", "/api/solve/end"): post_end,
    ("GET", "/api/problem"): get_problem,
    ("PUT", "/api/problem"): put_problem,
    ("POST", "/api/run"): post_run,
}


# HTTP -------------------------------------------------------------------------
def make_handler(coach: Coach):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def send(self, status: int, body, ctype: str = "application/json; charset=utf-8"):
            # ASCII JSON: a run's stdout can hold a lone surrogate (print(chr(0xD800))), which UTF-8 can't encode
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def read_body(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 <= length <= MAX_BODY:
                raise ApiError(400, f"a request body needs a Content-Length from 0 to {MAX_BODY} bytes")
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw or b"{}")
                json.dumps(data, ensure_ascii=False).encode()  # JSON can carry a lone surrogate; files can't
            except (ValueError, RecursionError):  # not JSON, not UTF-8 text, or nested too deeply
                raise ApiError(400, "the request body isn't JSON in UTF-8")
            if not isinstance(data, dict):
                raise ApiError(400, "the request body must be a JSON object")
            return data

        def static(self, path: str):
            name = "index.html" if path in ("", "/") else path.removeprefix("/static/")
            try:
                target = (STATIC / name).resolve()
                found = target.parent == STATIC.resolve() and target.is_file()
            except (OSError, ValueError):  # a name too long for the file system, or a NUL character
                found = False
            if not found:
                raise ApiError(404, "not found")
            self.send(200, target.read_bytes(), TYPES.get(target.suffix, "application/octet-stream"))

        def handle_any(self, method: str):
            url = urlparse(self.path)
            try:
                if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in HOSTS:
                    raise ApiError(403, "this server only answers on 127.0.0.1 or localhost")
                if not url.path.startswith("/api/"):
                    if method != "GET":
                        raise ApiError(405, "method not allowed")
                    return self.static(url.path)
                if self.headers.get("X-DSA-Coach") != "1":
                    raise ApiError(403, "missing the X-DSA-Coach header")
                route = ROUTES.get((method, url.path))
                if route is None:
                    raise ApiError(404, f"no route {method} {url.path}")
                data = self.read_body() if method in ("POST", "PUT") else \
                    {k: v[0] for k, v in parse_qs(url.query).items()}
                self.send(200, route(coach, data))
            except ApiError as e:
                self.send(e.status, {"error": e.message, **e.extra})
            except Exception as e:  # a bug, or a file changed under it: the page still gets an answer to show
                traceback.print_exc()
                self.send(500, {"error": f"{type(e).__name__}: {e}"})

        def do_GET(self):
            self.handle_any("GET")

        def do_POST(self):
            self.handle_any("POST")

        def do_PUT(self):
            self.handle_any("PUT")

    return Handler


def make_server(root: Path, port: int = 8765, env: dict | None = None, tries: int = 10) -> ThreadingHTTPServer:
    handler = make_handler(Coach(root, env))
    for p in [0] if port == 0 else range(port, port + tries):
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), handler)
        except OSError:
            continue
    raise SystemExit(f"no free port in {port}-{port + tries - 1}; pass --port")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="dsa-coach study app (the Solve tab)")
    p.add_argument("--root", type=Path, help="notebook folder (default: $DSA_NOTEBOOK, else ./notebook in the repo)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)
    root = (a.root or Path(os.environ.get("DSA_NOTEBOOK") or REPO / "notebook")).resolve()
    if not (root / "config.json").exists():
        raise SystemExit(f"{root} isn't a dsa-coach notebook (no config.json). Pass --root.")
    server = make_server(root, a.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"dsa-coach study app: {url}  (notebook: {root})  Ctrl+C stops it")
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
