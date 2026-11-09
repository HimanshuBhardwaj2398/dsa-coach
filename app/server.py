"""Local server for the dsa-coach study app (v1: the Solve tab).

    python3 app/server.py [--root NOTEBOOK] [--port 8765] [--no-browser]

It binds to 127.0.0.1 only. Every change to the notebook's records goes through coach.py. The server itself
writes only the live solve's attempt file and problems/<slug>/problem.md, each one whole. A missing
problem.md can be fetched from LeetCode (app/statement.py), one problem at a time.
"""
from __future__ import annotations

import argparse
import hashlib
from contextlib import contextmanager
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import tempfile
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
import attempt_file  # noqa: E402
import claude_job  # noqa: E402
import companion  # noqa: E402
import completion  # noqa: E402
import runner  # noqa: E402
import statement  # noqa: E402

REPO = APP.parent
COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"
STATIC = APP / "static"
sys.path.insert(0, str(COACH.parent))
from session_lock import session_lock, session_identity  # noqa: E402
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,254}")  # used with fullmatch; 255 is the longest name a folder can have
HOSTS = {"127.0.0.1", "localhost"}
# Stable public key in extensions/dsa-coach/manifest.json fixes this unpacked extension's ID.
COMPANION_ORIGIN = "chrome-extension://fiahbfhmngefgmcnlacogkhhhflfomoh"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8"}
ROADMAP = json.loads((COACH.parent.parent / "assets" / "roadmap.json").read_text(encoding="utf-8"))
EXPLAINER_TIMEOUT = 300  # seconds: the coach traces real Python before it draws
FEEDBACK_LIMIT = 2000  # characters: what should change in an explainer
WRITE = threading.Lock()  # saves go one at a time, so two can't both pass the mtime check


class ApiError(Exception):
    def __init__(self, status: int, message: str, extra: dict | None = None):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra or {}


class Coach:
    """coach.py against one notebook."""

    def __init__(self, root: Path, env: dict | None = None):
        self.root, self.env = Path(root), env
        self.jobs = claude_job.Jobs()
        self.chat_jobs = claude_job.Jobs()
        self.chat_sessions = {}  # coaching request id -> the solve it was asked in, to record the rung it gave
        self.finish_jobs = {}  # finish review id -> (solve, the inputs it assesses)
        self.finish_done = {}  # finish review id -> its answer, so a second poll gets the same one
        self.reviews = {}  # solve -> {"fingerprint", "review"}: the latest review that can be saved. Memory only.
        # An empty cwd avoids loading project instructions or local notebook hooks in the read-only chat.
        self.chat_directory = tempfile.TemporaryDirectory(prefix="dsa-coach-chat-")

    def run(self, *args: str) -> str:
        proc = subprocess.run([sys.executable, str(COACH), "--root", str(self.root), *args],
                              capture_output=True, text=True, env=self.env)
        if proc.returncode != 0:  # the status goes by how coach.py's message starts, not by a value it quotes
            message = (proc.stderr or proc.stdout).strip().removeprefix("error: ")
            status = 409 if message.startswith(("a solve is already live", "the solve changed", "the solve is busy")) else \
                404 if message.startswith("no live solve") else 400
            raise ApiError(status, message)
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
        raise ApiError(404, "no live solve")
    return live


@contextmanager
def checked_solve(coach, data):
    expected = need(data, "session_id", str)
    try:
        with session_lock(coach.root):
            path = coach.root / "sessions" / "current.json"
            live = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            if live is None or session_identity(live) != expected:
                raise ApiError(409, "the solve changed; refresh before trying again", {"stale_session": True})
            yield live
    except TimeoutError as exc:
        raise ApiError(409, str(exc)) from None


def read_attempt(path: Path, live: dict) -> dict:
    # Read text and metadata from one descriptor. Atomic path replacement cannot pair old bytes with a new mtime.
    for _ in range(3):
        with path.open("rb") as fh:
            before = os.fstat(fh.fileno())
            raw = fh.read()
            after = os.fstat(fh.fileno())
        if (before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size):
            break
    else:
        raise ApiError(409, "the attempt is changing on disk; try again")
    text = raw.decode("utf-8")
    out = {"file": live["file"], "path": str(path), "text": text, "mtime": after.st_mtime_ns,
           "revision": hashlib.sha256(raw).hexdigest(), "session_id": session_identity(live),
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


def write_whole(path: Path, text: str) -> None:
    """Write a temp file beside path, then rename it over path, as coach.py's write_json does: a reader never
    sees half a file, and a failed write leaves the old one. A symlink stays a link; the file keeps its mode."""
    path = path.resolve()
    tmp = path.with_name(f".{path.name}.{os.urandom(6).hex()}.tmp")
    try:
        with open(tmp, "x", encoding="utf-8") as fh:  # a new file gets the umask's mode, as write_text gave it
            fh.write(text)
        if path.exists():
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write_checked(path: Path, live: dict, text: str, d: dict) -> dict:
    """Write unless the file changed on disk since the page loaded it (pass force to overwrite anyway).
    A save that leaves the file as it is isn't a conflict."""
    with WRITE:
        disk = read_attempt(path, live)
        matches = d["revision"] == disk["revision"] if "revision" in d else same_mtime(d.get("mtime"), disk["mtime"])
        if not d.get("force") and not matches and disk["text"] != text:
            raise ApiError(409, "the attempt file changed on disk since you loaded it", disk)
        write_whole(path, text)
        return read_attempt(path, live)


# routes -----------------------------------------------------------------------
def get_state(coach, q):
    live = coach.json("solve", "show")
    state = {"notebook_id": hashlib.sha256(str(coach.root.resolve()).encode()).hexdigest(), "live": live, "next": None, "due": None, "attempt_mtime": None}
    if live:
        path = coach.root / live["file"]
        state["attempt_mtime"] = path.stat().st_mtime_ns if path.exists() else None
    else:
        state["next"], state["due"] = coach.json("next"), coach.json("due")
    return state


def get_attempt(coach, q):
    with checked_solve(coach, q) as live:
        return read_attempt(coach.root / live["file"], live)


def put_attempt(coach, d):
    with checked_solve(coach, d) as live:
        return write_checked(coach.root / live["file"], live, need(d, "text", str, blank_ok=True), d)


def put_parts(coach, d):
    with checked_solve(coach, d) as live:
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
    return {"message": coach.run("solve", "stage", str(need(d, "n", int)), "--expected-session", need(d, "session_id", str))}


def post_note(coach, d):
    stage, text = need(d, "stage", int), need(d, "text", str, blank_ok=True)
    return {"message": coach.run("solve", "note", "--stage", str(stage), f"--text={text}", "--expected-session", need(d, "session_id", str))}


def post_break(coach, d):
    return {"message": coach.run("solve", "break", "--expected-session", need(d, "session_id", str))}


def post_block(coach, d):
    return {"message": coach.run("solve", "block", "--expected-session", need(d, "session_id", str))}


def post_touch(coach, d):  # activity: typing, running code or working on LeetCode keeps the block's clock going
    coach.run("solve", "touch", "--quiet", "--expected-session", need(d, "session_id", str))
    return {}


def post_end(coach, d):
    args = ["solve", "end", f"--outcome={need(d, 'outcome', str)}", "--expected-session", need(d, "session_id", str)]
    if d.get("note"):
        args.append(f"--note={d['note']}")
    return {"message": coach.run(*args)}


def get_problem(coach, q):
    path = coach.root / "problems" / check_slug(q.get("slug")) / "problem.md"
    return {"text": path.read_text(encoding="utf-8") if path.exists() else None}


def put_problem(coach, d):
    path, text = coach.root / "problems" / check_slug(d.get("slug")) / "problem.md", need(d, "text", str)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_whole(path, text)
    return {"text": path.read_text(encoding="utf-8")}


def post_problem_fetch(coach, d):
    """The statement from LeetCode, saved as problem.md, unless one is already there (pasted or fetched)."""
    slug = check_slug(d.get("slug"))
    path = coach.root / "problems" / slug / "problem.md"
    if not path.exists():
        try:
            title, html = statement.fetch(slug)
        except statement.StatementError as e:
            raise ApiError(502, f"Couldn't fetch the statement: {e}. Paste it instead.")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(path, statement.document(slug, title, html))
    return {"text": path.read_text(encoding="utf-8")}


def post_run(coach, d):
    with checked_solve(coach, d) as live:
        path, identity = coach.root / live["file"], session_identity(live)
    return {**runner.run(path), "session_id": identity}


def check_pattern(value) -> dict:
    p = next((p for p in ROADMAP["patterns"] if p["key"] == value), None)
    if p is None:
        raise ApiError(400, f"unknown pattern {value!r}")
    return p


def get_map(coach, q):
    return coach.json("map")


def explainer_prompt(p: dict, root: Path) -> str:
    path = root / f"concepts/{p['key']}/{p['key']}-explainer.html"  # absolute: artifact add reads --file from the cwd
    return (f"Use the dsa-coach skill. Write the interactive explainer for the pattern {p['name']} ({p['key']}), "
            f"following references/explainers.md. Save it as one self-contained HTML file at {path}. "
            f"Don't publish it. Then register it: python3 skills/dsa-coach/scripts/coach.py --root {root} "
            f"artifact add --concept {p['key']} --title \"{p['name']}, explained\" --file {path}")


def revise_prompt(p: dict, path: Path, feedback: str, root: Path) -> str:
    """He read the explainer and says what should change. explainers.md asks the coach to offer a problem first; the
    page has shown him that advice, so the coach builds what he still asks for."""
    return (f"Use the dsa-coach skill. Revise the interactive explainer for the pattern {p['name']} ({p['key']}) at "
            f"{path}, following references/explainers.md. His feedback, quoted: {json.dumps(feedback)}. "
            f"He was told that attempting one problem often shows what a page is really missing, and still wants this "
            f"change. Log his feedback with python3 skills/dsa-coach/scripts/coach.py --root {root} log question "
            f"--concept {p['key']} --text and his words. Change what the feedback needs and keep what works; every "
            f"frame still comes from a real Python trace. Save over the same file; it is already registered. "
            f"Don't publish it.")


def claude_argv(coach, prompt: str) -> list:
    cfg = json.loads((coach.root / "config.json").read_text(encoding="utf-8"))
    return [cfg.get("claude_bin", "claude"), "-p", prompt, "--permission-mode", "acceptEdits",
            "--allowedTools", "Bash(python3:*),Read,Write,Edit,Glob,Grep"]


def post_explainer(coach, d):
    """Writes the pattern's explainer, or with feedback revises the one it has."""
    p = check_pattern(d.get("pattern"))
    feedback = d.get("feedback")
    if feedback is None:
        prompt = explainer_prompt(p, coach.root)
    elif not isinstance(feedback, str) or not feedback.strip() or len(feedback) > FEEDBACK_LIMIT:
        raise ApiError(400, f"say what should change, in at most {FEEDBACK_LIMIT} characters")
    else:
        prompt = revise_prompt(p, explainer_file(coach, p["key"]), feedback.strip(), coach.root)
    key = "explainer:" + p["key"]
    try:
        coach.jobs.start(key, claude_argv(coach, prompt), REPO, EXPLAINER_TIMEOUT)
    except claude_job.Busy as e:
        raise ApiError(409, str(e))
    return {"state": "running", "error": None}  # not status(): a fast job may already be done, and the page polls


def get_explainer(coach, q):
    return coach.jobs.status("explainer:" + check_pattern(q.get("pattern"))["key"])


def post_coaching(coach, d):
    problem = check_slug(d.get("problem"))
    live = coach.json("solve", "show")
    if d.get("session_id") != (live.get("session_id") if live else None) or (live and live["problem"] != problem):
        raise ApiError(409, "the solve changed; refresh before asking the coach", {"stale_session": True})
    context = live
    if live:
        with checked_solve(coach, d):
            saved = read_attempt(coach.root / live["file"], live)
            context = {**live, "plan_card": saved["plan_card"], "examples": saved["examples"]}
    protocol = (COACH.parent.parent / "references/protocol.md").read_text(encoding="utf-8")
    # The eight-stage teaching table is enough; platform and command instructions are not needed.
    protocol = protocol.split("## Stage prompts for the solve protocol", 1)[1].split("## Modes in detail", 1)[0]
    try:
        system, stream = companion.request(d, context, protocol)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from None
    config = json.loads((coach.root / "config.json").read_text(encoding="utf-8"))
    key = os.urandom(16).hex()
    try:
        coach.chat_jobs.start(key, companion.argv(config.get("claude_bin", "claude"), system),
                              coach.chat_directory.name, 180, input_text=stream, collect=True)
    except claude_job.Busy as exc:
        raise ApiError(409, str(exc)) from None
    if live:
        coach.chat_sessions[key] = live["session_id"]
    return {"id": key, "state": "running"}


def get_coaching(coach, q):
    key = need(q, "id", str)
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ApiError(400, "invalid coaching request")
    status = coach.chat_jobs.status(key)
    if status["state"] == "idle":
        raise ApiError(404, "coaching request expired; ask again")
    output = status.pop("output", None)
    if status["state"] == "done":
        try:
            status.update(companion.response(output or ""))
        except ValueError as exc:
            return {"state": "error", "error": str(exc)}
        session = coach.chat_sessions.pop(key, None)  # pop: the page polls again, the rung is recorded once
        if session and status["rung"]:
            status["recorded_rung"] = record_rung(coach, session, status["rung"])
    return status


def record_rung(coach, session, rung):
    """Record the rung the panel's coach gave on the hint ladder, which only goes up. None if nothing changed."""
    try:
        before = coach.json("solve", "show")
        if not before or before["session_id"] != session or rung <= before["rung"]:
            return None
        coach.run("solve", "hint", "--rung", str(rung), "--expected-session", session)
        return rung
    except ApiError:
        return None


# Finishing in the panel: the coach reviews the evidence, then he saves (completion.py) -------------------------
def finish_inputs(coach, d) -> tuple:
    """What a finish review assesses: his saved work from the notebook, and his finish answers and LeetCode code."""
    live = live_solve(coach)
    if live["session_id"] != need(d, "session_id", str):
        raise ApiError(409, "the solve changed; refresh before trying again", {"stale_session": True})
    if d.get("problem") != live["problem"]:
        raise ApiError(409, f"LeetCode shows a different problem from your solve ({live['problem']}).")
    if d.get("outcome") not in completion.OUTCOMES:
        raise ApiError(400, "choose solved, partial or failed")
    if not isinstance(d.get("outside_help"), bool):
        raise ApiError(400, "say whether you used outside help or saw a solution")
    try:
        lesson, code = companion.limited_text(d, "lesson", 500), companion.limited_text(d, "code", 24000)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from None
    with checked_solve(coach, d):
        saved = read_attempt(coach.root / live["file"], live)
    return live, {"problem": live["problem"], "stage_notes": live.get("notes") or {}, "plan_card": saved["plan_card"],
                  "examples": saved["examples"], "rung": live["rung"], "outcome": d["outcome"],
                  "lesson": lesson.strip(), "outside_help": d["outside_help"], "code": code}


def post_finish_review(coach, d):
    live, inputs = finish_inputs(coach, d)
    try:
        system, stream = completion.request(inputs, companion.limited_text(d, "page_text", 24000))
    except ValueError as exc:
        raise ApiError(400, str(exc)) from None
    config = json.loads((coach.root / "config.json").read_text(encoding="utf-8"))
    key = os.urandom(16).hex()
    try:
        coach.chat_jobs.start(key, companion.argv(config.get("claude_bin", "claude"), system),
                              coach.chat_directory.name, 180, input_text=stream, collect=True)
    except claude_job.Busy as exc:
        raise ApiError(409, str(exc)) from None
    coach.finish_jobs[key] = (live["session_id"], inputs)
    return {"id": key, "state": "running"}


def get_finish_review(coach, q):
    key = need(q, "id", str)
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ApiError(400, "invalid review request")
    if key in coach.finish_done:
        return coach.finish_done[key]
    status = coach.chat_jobs.status(key)
    if status["state"] == "idle" or key not in coach.finish_jobs:
        raise ApiError(404, "review request expired; ask again")
    output = status.pop("output", None)
    if status["state"] != "done":
        return status
    session, inputs = coach.finish_jobs.pop(key)
    try:
        review = completion.parse(output or "", inputs["outcome"])
    except ValueError as exc:
        result = {"state": "error", "error": str(exc)}
    else:
        recorded = record_rung(coach, session, review["rung"]) if review["rung"] else None
        if recorded:
            inputs = {**inputs, "rung": recorded}
        coach.reviews[session] = {"fingerprint": completion.fingerprint(inputs), "review": review}
        result = {"state": "done", "review": review, "recorded_rung": recorded}
    if len(coach.finish_done) >= 24:
        coach.finish_done.pop(next(iter(coach.finish_done)))
    coach.finish_done[key] = result
    return result


def post_finish_save(coach, d):
    """Logs the attempt the latest review proposed, if nothing it assessed has changed. A repeat returns the receipt."""
    session = need(d, "session_id", str)
    live = coach.json("solve", "show")
    if not live or live["session_id"] != session:  # ended already, or replaced: coach.py tells which
        return {"receipt": json.loads(coach.run("solve", "end", "--json", "--expected-session", session))}
    held = coach.reviews.get(session)
    if not held:
        raise ApiError(409, "Ask for a review first: the coach checks the evidence before the attempt is logged.")
    review = held["review"]
    if not review["recordable"]:
        raise ApiError(409, "The review still needs: " + "; ".join(review["missing"]))
    _, inputs = finish_inputs(coach, d)
    if completion.fingerprint(inputs) != held["fingerprint"]:
        raise ApiError(409, "Your answers, code or hints changed since the review. Ask for a fresh review.",
                       {"review_stale": True})
    note = "; ".join(filter(None, [inputs["lesson"], f"evidence: {review['evidence']}"]))
    args = ["solve", "end", "--json", f"--outcome={review['outcome']}", "--expected-session", session, f"--note={note}"]
    if inputs["outside_help"]:
        args.append("--assisted")
    if review["technique"]:
        args.append(f"--technique={review['technique']}")
    if review["mistakes"]:
        args.append("--mistakes=" + ",".join(review["mistakes"]))
    if review["complexity_stated"]:
        args.append("--complexity-stated")
    receipt = json.loads(coach.run(*args))
    coach.reviews.pop(session, None)
    return {"receipt": receipt}


def explainer_file(coach, key: str) -> Path:
    check_pattern(key)
    rel = next(p["explainer"] for p in coach.json("map")["patterns"] if p["key"] == key)
    path = (coach.root / (rel or "")).resolve()
    if not rel or not path.is_relative_to(coach.root.resolve()) or not path.is_file():
        raise ApiError(404, "no explainer for that pattern yet")
    return path


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
    ("POST", "/api/solve/touch"): post_touch,
    ("POST", "/api/solve/end"): post_end,
    ("GET", "/api/problem"): get_problem,
    ("POST", "/api/problem/fetch"): post_problem_fetch,
    ("PUT", "/api/problem"): put_problem,
    ("POST", "/api/run"): post_run,
    ("GET", "/api/map"): get_map,
    ("POST", "/api/explainer"): post_explainer,
    ("GET", "/api/explainer"): get_explainer,
    ("POST", "/api/coaching"): post_coaching,
    ("GET", "/api/coaching"): get_coaching,
    ("POST", "/api/finish/review"): post_finish_review,
    ("GET", "/api/finish/review"): get_finish_review,
    ("POST", "/api/finish/save"): post_finish_save,
}


# HTTP -------------------------------------------------------------------------
def make_handler(coach: Coach):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def end_headers(self):  # every answer, http.server's own error pages too
            if getattr(self, "companion_response", False):
                self.send_header("Content-Security-Policy", f"frame-ancestors {COMPANION_ORIGIN}")
            else:
                self.send_header("X-Frame-Options", "DENY")
            super().end_headers()

        def send(self, status: int, body, ctype: str = "application/json; charset=utf-8", headers: dict | None = None):
            # ASCII JSON: a run's stdout can hold a lone surrogate (print(chr(0xD800))), which UTF-8 can't encode
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def read_body(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise ApiError(400, "invalid Content-Length") from None
            if not 0 <= length <= 8_000_000:
                raise ApiError(413, "request too large")
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw or b"{}")
                json.dumps(data, ensure_ascii=False).encode()  # JSON can carry a lone surrogate; files can't
            except ValueError:  # not JSON, or not UTF-8 text
                raise ApiError(400, "the request body isn't JSON in UTF-8")
            if not isinstance(data, dict):
                raise ApiError(400, "the request body must be a JSON object")
            return data

        def static(self, path: str):
            name = "index.html" if path in ("", "/", "/companion") else path.removeprefix("/static/")
            target = (STATIC / name).resolve()
            if target.parent != STATIC.resolve() or not target.is_file():
                raise ApiError(404, "not found")
            self.companion_response = path == "/companion"
            self.send(200, target.read_bytes(), TYPES.get(target.suffix, "application/octet-stream"))

        def handle_any(self, method: str):
            self.companion_response = False
            url = urlparse(self.path)
            try:
                if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in HOSTS:
                    raise ApiError(403, "this server only answers on 127.0.0.1 or localhost")
                if not url.path.startswith("/api/"):
                    if method != "GET":
                        raise ApiError(405, "method not allowed")
                    if url.path.startswith("/explainer/"):
                        path = explainer_file(coach, url.path.removeprefix("/explainer/"))
                        # its own origin: the page's scripts run, but can't call this server's API
                        return self.send(200, path.read_bytes(), TYPES[".html"],
                                         {"Content-Security-Policy": "sandbox allow-scripts allow-popups"})
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
                self.send(e.status, {"error": e.message, "stale_session": e.message.startswith("the solve changed"), **e.extra})
            except ConnectionError:  # the page went away (a reload, a closed tab): there's no one to answer
                return
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


class StudyServer(ThreadingHTTPServer):
    def server_close(self):
        super().server_close()
        if hasattr(self, "coach"):
            self.coach.chat_directory.cleanup()


def make_server(root: Path, port: int = 8765, env: dict | None = None, tries: int = 10) -> ThreadingHTTPServer:
    coach = Coach(root, env)
    handler = make_handler(coach)
    for p in [0] if port == 0 else range(port, port + tries):
        if p and in_use(p):
            continue
        try:
            srv = StudyServer(("127.0.0.1", p), handler)
            srv.coach = coach  # tests swap its jobs
            return srv
        except OSError:
            continue
    coach.chat_directory.cleanup()
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
    print(f"dsa-coach study app: {url}  (notebook: {root})  Ctrl+C stops it", flush=True)
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
