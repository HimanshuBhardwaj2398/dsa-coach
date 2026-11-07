"""Tests for app/server.py. Run: python3 -m unittest discover -s tests -v"""
import contextlib
import base64
import hashlib
import io
import json
import os
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402

COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"
METHOD = ("    def search(self, nums, target):\n"
          "        lo, hi = 0, len(nums) - 1\n"
          "        while lo <= hi:\n"
          "            mid = (lo + hi) // 2\n"
          "            if nums[mid] == target:\n"
          "                return mid\n"
          "            if nums[mid] > target:\n"
          "                hi = mid - 1\n"
          "            else:\n"
          "                lo = mid + 1\n"
          "        return -1\n")


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dsa-server-test-"))
        self.root = self.tmp / "notebook"
        self.env = dict(os.environ, DSA_TODAY="2026-11-06", HOME=str(self.tmp / "home"))
        self.env.pop("DSA_NOTEBOOK", None)
        subprocess.run([sys.executable, str(COACH), "--root", str(self.root), "init", "--name", "Tester",
                        "--start-date", "2026-11-01", "--days", "90"], check=True, capture_output=True, env=self.env)
        self.server = server.make_server(self.root, port=0, env=self.env)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, method, path, body=None, coach_header=True, host=None, auto_session=True):
        scoped = path.startswith("/api/attempt") or path == "/api/run" or (path.startswith("/api/solve/") and path != "/api/solve/start")
        if scoped and auto_session:
            live_path = self.root / "sessions/current.json"
            identity = server.session_identity(json.loads(live_path.read_text())) if live_path.exists() else "ended-session"
            if method == "GET":
                if "session_id=" not in path:
                    path += ("&" if "?" in path else "?") + "session_id=" + identity
            else:
                body = {"session_id": identity, **(body or {})}
        headers = {"Content-Type": "application/json"}
        if coach_header:
            headers["X-DSA-Coach"] = "1"
        if host:
            headers["Host"] = host
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def start(self):
        return self.call("POST", "/api/solve/start", {"problem": "binary-search", "confidence": 3, "difficulty": "easy"})

    # POST /api/problem/fetch: statement.fetch is replaced, so no test touches the network
    def problem_md(self, slug="koko-eating-bananas"):
        return self.root / "problems" / slug / "problem.md"

    def raw_get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as res:
                return res.status, res.headers, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def fake_claude(self):
        calls = []

        def run(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.server.coach.jobs = server.claude_job.Jobs(run=run)
        return calls

    def wait_job(self, pattern):
        for _ in range(200):
            status, body = self.call("GET", f"/api/explainer?pattern={pattern}")
            if body["state"] != "running":
                return body
            time.sleep(0.01)
        self.fail("job never finished")

    def test_map(self):
        status, body = self.call("GET", "/api/map")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["patterns"]), 22)

    def test_explainer_runs_the_coach_for_one_pattern(self):
        calls = self.fake_claude()
        status, body = self.call("POST", "/api/explainer", {"pattern": "binary-search"})
        self.assertEqual((status, body["state"]), (200, "running"))
        self.assertEqual(self.wait_job("binary-search")["state"], "done")
        argv = calls[0]
        self.assertEqual(argv[:2], ["claude", "-p"])
        self.assertIn("binary-search", argv[2])
        self.assertIn("artifact add --concept binary-search", argv[2])

    def test_explainer_uses_claude_bin_and_rejects_unknown_patterns(self):
        cfg = json.loads((self.root / "config.json").read_text())
        (self.root / "config.json").write_text(json.dumps({**cfg, "claude_bin": "/opt/claude"}))
        calls = self.fake_claude()
        self.call("POST", "/api/explainer", {"pattern": "stack"})
        self.wait_job("stack")
        self.assertEqual(calls[0][0], "/opt/claude")
        self.assertEqual(self.call("POST", "/api/explainer", {"pattern": "nope"})[0], 400)

    def add_explainer(self, key):
        page = self.root / "concepts" / key / f"{key}-explainer.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(f"<p>{key}</p>")
        subprocess.run([sys.executable, str(COACH), "--root", str(self.root), "artifact", "add", "--concept", key,
                        "--title", key, "--file", str(page)], check=True, capture_output=True, env=self.env)
        return page

    def test_explainer_page_is_sandboxed(self):
        self.assertEqual(self.raw_get("/explainer/stack")[0], 404)
        self.add_explainer("stack")
        status, headers, body = self.raw_get("/explainer/stack")
        self.assertEqual((status, body), (200, b"<p>stack</p>"))
        self.assertIn("sandbox", headers["Content-Security-Policy"])

    def test_feedback_revises_the_registered_explainer_in_place(self):
        page = self.add_explainer("stack")
        calls = self.fake_claude()
        feedback = 'The pop step is unclear. Show it with "equal heights".'
        status, body = self.call("POST", "/api/explainer", {"pattern": "stack", "feedback": f"  {feedback}\n"})
        self.assertEqual((status, body["state"]), (200, "running"))
        self.assertEqual(self.wait_job("stack")["state"], "done")
        prompt = calls[0][2]
        self.assertIn(f"Revise the interactive explainer for the pattern Stack (stack) at {page.resolve()},", prompt)
        self.assertIn(json.dumps(feedback), prompt)  # quoted, so his words stay data
        self.assertIn(f"--root {self.root} log question --concept stack --text", prompt)
        self.assertNotIn("artifact add", prompt)  # it is registered already
        self.assertEqual(page.read_text(), "<p>stack</p>")  # the page itself is the coach's to change

    def test_feedback_needs_an_explainer_and_some_words(self):
        calls = self.fake_claude()
        self.assertEqual(self.call("POST", "/api/explainer", {"pattern": "stack", "feedback": "Slower, please"})[0], 404)
        self.add_explainer("stack")
        for feedback in ("", "   ", 3, ["Slower"], "x" * 2001):
            with self.subTest(feedback=feedback):
                status, body = self.call("POST", "/api/explainer", {"pattern": "stack", "feedback": feedback})
                self.assertEqual(status, 400)
                self.assertIn("at most 2000 characters", body["error"])
        self.assertEqual(calls, [])

    def test_stale_actions_cannot_touch_a_replacement_solve(self):
        self.start()
        old = self.call("GET", "/api/attempt")[1]
        self.call("POST", "/api/solve/end", {"outcome": "partial"})
        self.start()
        new = self.call("GET", "/api/attempt")[1]
        paths = [self.root / "sessions/current.json", self.root / new["file"], self.root / "learner/attempts.jsonl"]
        before = [p.read_bytes() for p in paths]
        actions = [("PUT", "/api/attempt", {"text": "old code", "force": True}),
                   ("PUT", "/api/attempt/parts", {"examples": []}),
                   ("POST", "/api/run", {}), ("POST", "/api/solve/stage", {"n": 7}),
                   ("POST", "/api/solve/note", {"stage": 1, "text": "old note"}),
                   ("POST", "/api/solve/break", {}), ("POST", "/api/solve/block", {}),
                   ("POST", "/api/solve/end", {"outcome": "solved"})]
        for method, path, body in actions:
            status, answer = self.call(method, path, {**body, "session_id": old["session_id"]})
            self.assertEqual(status, 409, path)
            self.assertTrue(answer["stale_session"], path)
            self.assertEqual([p.read_bytes() for p in paths], before, path)
        status, _ = self.call("GET", "/api/attempt?session_id=" + old["session_id"])
        self.assertEqual(status, 409)

    def test_browser_session_identity_is_required(self):
        self.start()
        for method, path, body in [("GET", "/api/attempt", None), ("PUT", "/api/attempt", {"text": "x"}),
                                  ("POST", "/api/run", {}), ("POST", "/api/solve/stage", {"n": 2})]:
            self.assertEqual(self.call(method, path, body, auto_session=False)[0], 400)

    def test_content_revision_catches_changes_even_when_mtime_is_preserved(self):
        self.start()
        old = self.call("GET", "/api/attempt")[1]
        path = self.root / old["file"]
        path.write_text("# another editor\n")
        os.utime(path, ns=(old["mtime"], old["mtime"]))
        status, disk = self.call("PUT", "/api/attempt", {"text": "# mine\n", "revision": old["revision"]})
        self.assertEqual(status, 409)
        self.assertEqual(disk["text"], "# another editor\n")
        self.assertNotEqual(disk["revision"], old["revision"])

    def test_read_revision_belongs_to_the_descriptor_not_a_replaced_path(self):
        self.start()
        live = self.call("GET", "/api/state")[1]["live"]
        path = self.root / live["file"]
        original = path.read_bytes()
        real_fstat = os.fstat
        calls = []
        def replace_after_read(fd):
            calls.append(fd)
            if len(calls) == 2:
                server.write_whole(path, "# replacement\n")
            return real_fstat(fd)
        with unittest.mock.patch.object(server.os, "fstat", side_effect=replace_after_read):
            shown = server.read_attempt(path, live)
        self.assertEqual(shown["text"].encode(), original)
        self.assertEqual(shown["revision"], server.hashlib.sha256(original).hexdigest())
        self.assertEqual(path.read_text(), "# replacement\n")

    def test_notebook_identity_is_stable_and_distinct(self):
        first = self.call("GET", "/api/state")[1]["notebook_id"]
        self.assertEqual(first, self.call("GET", "/api/state")[1]["notebook_id"])
        self.assertEqual(first, server.hashlib.sha256(str(self.root.resolve()).encode()).hexdigest())

    def test_fetch_writes_problem_md_and_returns_it(self):
        fake = unittest.mock.Mock(return_value=("Koko Eating Bananas", "<p>Koko loves <code>piles</code>.</p>"))
        with unittest.mock.patch.object(server.statement, "fetch", fake):
            status, body = self.call("POST", "/api/problem/fetch", {"slug": "koko-eating-bananas"})
        self.assertEqual(status, 200)
        fake.assert_called_once_with("koko-eating-bananas")
        self.assertEqual(body["text"], self.problem_md().read_text())
        self.assertTrue(body["text"].startswith("# Koko Eating Bananas\n\nhttps://leetcode.com/problems/koko-eating-bananas/"))
        self.assertIn("Koko loves piles.", body["text"])

    def test_an_existing_statement_is_returned_without_fetching(self):
        self.problem_md().parent.mkdir(parents=True)
        self.problem_md().write_text("pasted earlier\n")
        fake = unittest.mock.Mock()
        with unittest.mock.patch.object(server.statement, "fetch", fake):
            status, body = self.call("POST", "/api/problem/fetch", {"slug": "koko-eating-bananas"})
        self.assertEqual((status, body["text"]), (200, "pasted earlier\n"))
        fake.assert_not_called()

    def test_a_failed_fetch_is_a_502_with_the_reason_and_writes_nothing(self):
        fake = unittest.mock.Mock(side_effect=server.statement.StatementError("it's a premium problem"))
        with unittest.mock.patch.object(server.statement, "fetch", fake):
            status, body = self.call("POST", "/api/problem/fetch", {"slug": "koko-eating-bananas"})
        self.assertEqual(status, 502)
        self.assertIn("it's a premium problem", body["error"])
        self.assertIn("Paste it instead", body["error"])
        self.assertFalse(self.problem_md().parent.exists())

    def test_the_slug_is_checked_before_anything_else(self):
        fake = unittest.mock.Mock()
        with unittest.mock.patch.object(server.statement, "fetch", fake):
            status, _ = self.call("POST", "/api/problem/fetch", {"slug": "../etc"})
            status2, _ = self.call("POST", "/api/problem/fetch", {"slug": "koko"}, coach_header=False)
        self.assertEqual((status, status2), (400, 403))
        fake.assert_not_called()

    def test_binds_to_localhost_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_refuses_requests_without_the_header_or_from_another_host(self):
        self.assertEqual(self.call("GET", "/api/state", coach_header=False)[0], 403)
        self.assertEqual(self.call("GET", "/api/state", host="evil.example:80")[0], 403)

    def test_state_without_a_live_solve(self):
        status, state = self.call("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertIsNone(state["live"])
        self.assertEqual(state["next"]["kind"], "new")
        self.assertEqual(state["due"]["resolves"], [])

    def test_start_then_state_and_attempt(self):
        self.assertEqual(self.start()[0], 200)
        state = self.call("GET", "/api/state")[1]
        self.assertEqual((state["live"]["problem"], state["live"]["stage"], state["live"]["confidence"]),
                         ("binary-search", 1, 3))
        self.assertIsInstance(state["attempt_mtime"], int)
        attempt = self.call("GET", "/api/attempt")[1]
        self.assertIn("class Solution:", attempt["text"])
        self.assertEqual(attempt["plan_card"]["Invariant"], "")
        self.assertEqual(attempt["examples"], [])
        self.assertEqual(attempt["file"], "problems/binary-search/2026-11-06.py")

    def test_a_coach_error_comes_back_as_4xx_with_its_message(self):
        self.start()
        status, body = self.start()
        self.assertEqual(status, 409)
        self.assertIn("already live", body["error"])
        self.call("POST", "/api/solve/end", {"outcome": "solved"})
        status, body = self.call("POST", "/api/solve/start", {"problem": "my-own-puzzle", "confidence": 2})
        self.assertEqual(status, 400)  # coach.py asks for --pattern
        self.assertIn("which pattern", body["error"])
        for key, typed in (("pattern", "already live"), ("mode", "no live solve")):  # coach.py quotes what it refused
            status, body = self.call("POST", "/api/solve/start", {"problem": "two-sum", "confidence": 3, key: typed})
            self.assertEqual(status, 400, typed)
            self.assertIn(f"invalid choice: '{typed}'", body["error"])
        self.assertEqual(self.call("POST", "/api/solve/stage", {})[0], 400)

    def test_ended_session_is_a_distinct_conflict_on_every_scoped_route(self):
        """Identity conflicts carry no disk text and cannot be mistaken for content conflicts."""
        for method, path, body in (("GET", "/api/attempt", None), ("PUT", "/api/attempt", {"text": "x", "mtime": 0}),
                                   ("PUT", "/api/attempt/parts", {"examples": [], "mtime": 0}),
                                   ("POST", "/api/run", {}), ("POST", "/api/solve/stage", {"n": 2}),
                                   ("POST", "/api/solve/note", {"stage": 1, "text": "x"}),
                                   ("POST", "/api/solve/break", {}), ("POST", "/api/solve/block", {}),
                                   ("POST", "/api/solve/end", {"outcome": "solved"})):
            status, answer = self.call(method, path, body)
            self.assertEqual(status, 409, path)
            self.assertTrue(answer["stale_session"], answer)
            self.assertNotIn("text", answer)

    def test_parts_run_and_the_mtime_check(self):
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        stale = attempt["mtime"]
        rows = [{"args": "[-1, 0, 3, 5, 9, 12], 9", "expected": "4", "edge": False},
                {"args": "[5], 5", "expected": "0", "edge": True}]
        status, attempt = self.call("PUT", "/api/attempt/parts",
                                    {"examples": rows, "plan_card": {"Invariant": "target in nums[lo..hi]"},
                                     "mtime": attempt["mtime"]})
        self.assertEqual(status, 200)
        self.assertEqual(attempt["examples"], rows)
        self.assertEqual(attempt["plan_card"]["Invariant"], "target in nums[lo..hi]")
        status, conflict = self.call("PUT", "/api/attempt", {"text": "x", "mtime": stale})
        self.assertEqual(status, 409)
        self.assertIn("EXAMPLES = [", conflict["text"])
        text = attempt["text"].replace("    pass\n", METHOD, 1)
        self.assertEqual(self.call("PUT", "/api/attempt", {"text": text, "mtime": attempt["mtime"]})[0], 200)
        result = self.call("POST", "/api/run", {})[1]
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["rows"]), 2)
        bad = self.call("PUT", "/api/attempt/parts", {"examples": [{"args": "nums", "expected": "1"}],
                                                       "mtime": self.call("GET", "/api/attempt")[1]["mtime"]})
        self.assertEqual(bad[0], 400)

    def test_stage_note_break_block_and_end(self):
        self.start()
        self.assertEqual(self.call("POST", "/api/solve/note", {"stage": 1, "text": "- starts with a dash"})[0], 200)
        self.call("POST", "/api/solve/stage", {"n": 2})
        self.call("POST", "/api/solve/break", {})
        live = self.call("GET", "/api/state")[1]["live"]
        self.assertEqual((live["stage"], live["notes"], live["block"]["open"]), (2, {"1": "- starts with a dash"}, False))
        self.call("POST", "/api/solve/block", {})
        self.assertTrue(self.call("GET", "/api/state")[1]["live"]["block"]["open"])
        status, body = self.call("POST", "/api/solve/end", {"outcome": "partial", "note": "parked: stage 2"})
        self.assertEqual(status, 200)
        self.assertIn("Logged a0001", body["message"])
        self.assertIsNone(self.call("GET", "/api/state")[1]["live"])

    def test_problem_statement_round_trip_and_bad_slugs(self):
        self.assertIsNone(self.call("GET", "/api/problem?slug=binary-search")[1]["text"])
        self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "Given a sorted array..."})
        self.assertEqual(self.call("GET", "/api/problem?slug=binary-search")[1]["text"], "Given a sorted array...")
        self.assertEqual(self.call("GET", "/api/problem?slug=../config")[0], 400)

    def test_static_files_stay_inside_the_static_folder(self):
        self.assertEqual(self.call("GET", "/static/nope.js")[0], 404)
        self.assertEqual(self.call("GET", "/static/../server.py")[0], 404)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)

    def test_the_page_is_served(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/")
        with urllib.request.urlopen(req) as res:
            self.assertIn("text/html", res.headers["Content-Type"])
            page = res.read().decode()
        self.assertIn('id="panel"', page)
        self.assertIn("/static/app.js", page)

    # beyond the plan: input checks, and requests the page would never send ------------------------------------
    def answer(self, method, path, headers, body=None):
        """(status, headers) of the answer to a request with these headers, and the Host urllib adds."""
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, res.headers
        except urllib.error.HTTPError as e:
            e.read()
            return e.code, e.headers

    def files(self) -> dict:
        """Every file and folder in the notebook, with its size and mtime_ns."""
        return {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in self.root.rglob("*")}

    def test_put_parts_checks_its_input_types(self):
        self.start()
        mtime = self.call("GET", "/api/attempt")[1]["mtime"]
        for parts in ({"plan_card": "Invariant: x"}, {"plan_card": None}, {"plan_card": {"Invariant": 5}},
                      {"examples": "[5], 5"}, {"examples": None}, {"examples": ["[5], 5"]},
                      {"examples": [{"args": 5, "expected": "5"}]},
                      {"examples": [{"args": "5", "expected": "5", "edge": "yes"}]}):
            status, body = self.call("PUT", "/api/attempt/parts", dict(parts, mtime=mtime))
            self.assertEqual(status, 400, parts)
            self.assertIn("error", body)
        self.assertEqual(self.call("GET", "/api/attempt")[1]["mtime"], mtime)  # none of them wrote the file

    def test_a_run_whose_output_has_a_lone_surrogate_still_answers_in_json(self):
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        method = "    def f(self, x):\n        print(chr(0xD800))\n        return x\n"
        text = attempt["text"].replace("    pass\n", method, 1)
        text = text.replace("EXAMPLES = [\n]", "EXAMPLES = [\n    ((1,), 1),\n]", 1)
        self.assertEqual(self.call("PUT", "/api/attempt", {"text": text, "mtime": attempt["mtime"]})[0], 200)
        status, result = self.call("POST", "/api/run", {})
        self.assertEqual(status, 200)
        self.assertEqual((result["ok"], result["rows"][0]["stdout"]), (True, "\ud800\n"))

    def test_values_from_the_page_reach_coach_as_values_not_as_options(self):
        for key in ("pattern", "difficulty", "mode"):
            status, body = self.call("POST", "/api/solve/start",
                                     {"problem": "binary-search", "confidence": 3, key: "--unlabeled"})
            self.assertEqual(status, 400, key)
            self.assertIn("invalid choice: '--unlabeled'", body["error"])  # not "expected one argument"
        status, body = self.call("POST", "/api/solve/start", {"problem": "--unlabeled", "confidence": 3})
        self.assertEqual(status, 400)
        self.assertIn("which pattern is unlabeled?", body["error"])
        self.assertIsNone(self.call("GET", "/api/state")[1]["live"])
        self.start()
        status, body = self.call("POST", "/api/solve/end", {"outcome": "--discard"})
        self.assertEqual(status, 400)
        self.assertIn("invalid choice: '--discard'", body["error"])
        self.assertEqual(self.call("GET", "/api/state")[1]["live"]["problem"], "binary-search")  # still live

    def test_the_mtime_check_takes_the_mtime_back_from_a_javascript_number(self):
        self.start()
        path = self.root / self.call("GET", "/api/state")[1]["live"]["file"]
        os.utime(path, ns=(1762412345123456789, 1762412345123456789))
        attempt = self.call("GET", "/api/attempt")[1]
        self.assertEqual(attempt["mtime"], 1762412345123456789)
        as_js = int(Decimal(repr(float(attempt["mtime"]))))  # what JSON.parse, then JSON.stringify, give back
        self.assertEqual(as_js, 1762412345123456800)
        status, saved = self.call("PUT", "/api/attempt", {"text": attempt["text"] + "\n", "mtime": as_js})
        self.assertEqual(status, 200)
        self.assertEqual(self.call("PUT", "/api/attempt", {"text": "x", "mtime": as_js})[0], 409)  # now stale
        for mtime in (None, "1762412345123456789", 10 ** 400, True):
            self.assertEqual(self.call("PUT", "/api/attempt", {"text": "x", "mtime": mtime})[0], 409, mtime)
        self.assertEqual(path.read_text(), saved["text"])

    def test_a_save_after_the_solve_ended_is_a_session_conflict(self):
        """e.g. the chat ended the solve while the page had unsaved edits: there's no disk version to offer."""
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        self.call("POST", "/api/solve/end", {"outcome": "solved"})
        for path, body in (("/api/attempt", {"text": attempt["text"] + "# more\n"}),
                           ("/api/attempt/parts", {"examples": []})):
            answer = self.call("PUT", path, dict(body, mtime=attempt["mtime"]))
            self.assertEqual(answer[0], 409, path)
            self.assertTrue(answer[1]["stale_session"])
            self.assertNotIn("text", answer[1])

    def test_saves_from_the_same_mtime_at_once_go_one_at_a_time(self):
        """Two tabs, or a double click: one save wins, and the others get a conflict carrying the winner's text."""
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        check = server.same_mtime

        def slow_check(sent, actual):  # widens the gap between the mtime check and the write, as a slow disk would
            time.sleep(0.2)
            return check(sent, actual)

        answers = []
        threads = [threading.Thread(target=lambda n=n: answers.append(self.call(
            "PUT", "/api/attempt", {"text": f"# save {n}\n", "mtime": attempt["mtime"]}))) for n in range(4)]
        with unittest.mock.patch.object(server, "same_mtime", slow_check):
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual(sorted(status for status, _ in answers), [200, 409, 409, 409])
        winner = next(body["text"] for status, body in answers if status == 200)
        self.assertEqual({body["text"] for _, body in answers}, {winner})
        self.assertEqual((self.root / attempt["file"]).read_text(), winner)

    def test_a_save_that_changes_nothing_is_not_a_conflict(self):
        """e.g. a double click on Done: the second save carries the mtime that the first one changed."""
        self.start()
        text = self.call("GET", "/api/attempt")[1]["text"] + "# checked\n"
        for path, body in (("/api/attempt", {"text": text}),
                           ("/api/attempt/parts", {"examples": [{"args": "[5], 5", "expected": "0", "edge": True}]})):
            body["mtime"] = self.call("GET", "/api/attempt")[1]["mtime"]
            self.assertEqual(self.call("PUT", path, body)[0], 200, path)
            self.assertEqual(self.call("PUT", path, body)[0], 200, path)  # the same mtime, now stale

    def test_a_save_replaces_the_file_whole(self):
        """As coach.py's write_json does: a reader never sees half a file, a failed save leaves the old file
        and no temp file, and the file keeps its mode."""
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        path, problem = self.root / attempt["file"], self.root / "problems" / "binary-search" / "problem.md"
        self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "Given a sorted array..."})
        path.chmod(0o600)
        problem.chmod(0o600)
        with path.open(encoding="utf-8") as reader:  # opened before the save: it still reads the old file whole
            saved = self.call("PUT", "/api/attempt", {"text": "x = 1\n", "mtime": attempt["mtime"]})[1]
            self.assertEqual(reader.read(), attempt["text"])
        self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "Given an array..."})
        with unittest.mock.patch.object(server.os, "replace", side_effect=OSError("disk full")), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.call("PUT", "/api/attempt", {"text": "y = 2\n", "mtime": saved["mtime"]})[0], 500)
            self.assertEqual(self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "z"})[0], 500)
        self.assertEqual((path.read_text(), problem.read_text()), ("x = 1\n", "Given an array..."))
        self.assertEqual(sorted(os.listdir(path.parent)), sorted([path.name, problem.name]))
        self.assertEqual((path.stat().st_mode & 0o777, problem.stat().st_mode & 0o777), (0o600, 0o600))

    def test_polling_the_state_never_writes(self):
        for live in (False, True):
            if live:
                self.start()
            before = self.files()
            for _ in range(3):
                self.assertEqual(self.call("GET", "/api/state")[0], 200)
            self.assertEqual(self.files(), before, "with a live solve" if live else "without a live solve")

    def test_a_body_that_isnt_a_json_object_is_a_400(self):
        for body in (b"{", b"\xff", b"[1, 2]", b'"text"'):
            self.assertEqual(self.answer("POST", "/api/solve/note", {"X-DSA-Coach": "1"}, body)[0], 400, body)

    def test_text_that_cant_be_saved_or_passed_on_is_a_400_and_changes_nothing(self):
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        before = (self.root / attempt["file"]).read_bytes()
        self.assertEqual(self.call("PUT", "/api/attempt", {"text": "x = '\ud800'", "mtime": attempt["mtime"]})[0], 400)
        self.assertEqual((self.root / attempt["file"]).read_bytes(), before)  # not emptied
        self.assertEqual(self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "\ud800"})[0], 400)
        self.assertFalse((self.root / "problems" / "binary-search" / "problem.md").exists())
        self.assertEqual(self.call("POST", "/api/solve/note", {"stage": 1, "text": "\ud800"})[0], 400)
        self.assertNotIn("notes", self.call("GET", "/api/state")[1]["live"])

    def test_odd_slugs_are_refused(self):
        for slug in ("binary-search\n", "a" * 300, "../config", "Binary-Search", "", 5):
            self.assertEqual(self.call("PUT", "/api/problem", {"slug": slug, "text": "x"})[0], 400, repr(slug))
        self.assertFalse((self.root / "problems" / "binary-search\n").exists())
        self.assertEqual(self.call("PUT", "/api/problem", {"slug": "two-sum", "text": ""})[0], 400)
        self.assertFalse((self.root / "problems" / "two-sum").exists())  # a refused save makes no folder
        self.assertEqual(self.call("GET", "/api/problem?slug=" + "a" * 300)[0], 400)

    def test_a_preflight_or_an_unknown_method_gets_no_cors_headers(self):
        """With no Access-Control-Allow-*, a page on another origin can't send the X-DSA-Coach header."""
        asks = {"Origin": "http://evil.example", "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "x-dsa-coach, content-type"}
        for method, headers in (("OPTIONS", asks), ("DELETE", {"X-DSA-Coach": "1"}), ("BREW", {"X-DSA-Coach": "1"})):
            status, answer = self.answer(method, "/api/attempt", headers)
            self.assertFalse(200 <= status < 300, method)
            self.assertEqual([h for h in answer if h.lower().startswith("access-control-allow-")], [], method)

    def test_a_post_without_the_header_starts_nothing(self):
        """What a form or a no-cors fetch on another site can send with no preflight: text/plain, no custom header."""
        body = json.dumps({"problem": "binary-search", "confidence": 3}).encode()
        headers = {"Content-Type": "text/plain", "Origin": "http://evil.example"}
        self.assertEqual(self.answer("POST", "/api/solve/start", headers, body)[0], 403)
        shown = subprocess.run([sys.executable, str(COACH), "--root", str(self.root), "solve", "show", "--json"],
                               capture_output=True, text=True, env=self.env, check=True)
        self.assertIsNone(json.loads(shown.stdout))

    def test_force_overwrites_a_file_that_changed_on_disk(self):
        """The page's "Keep mine" after a conflict."""
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        path = self.root / attempt["file"]
        path.write_text("changed in another editor\n")
        stale = {"text": "mine\n", "mtime": attempt["mtime"]}
        self.assertEqual(self.call("PUT", "/api/attempt", stale)[0], 409)
        for sent in (stale, {"text": "mine\n"}):  # a stale mtime, and none, as the page sends
            path.write_text("changed in another editor\n")
            status, saved = self.call("PUT", "/api/attempt", dict(sent, force=True))
            self.assertEqual((status, saved["text"], path.read_text()), (200, "mine\n", "mine\n"))

    def test_no_page_can_frame_the_app(self):
        for path in ("/", "/api/state"):
            self.assertEqual(self.answer("GET", path, {"X-DSA-Coach": "1"})[1]["X-Frame-Options"], "DENY", path)

    def test_only_the_companion_route_allows_the_pinned_extension_to_frame_it(self):
        manifest = json.loads((REPO / "extensions/dsa-coach/manifest.json").read_text())
        digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
        identity = "".join(chr(ord("a") + int(c, 16)) for c in digest)
        status, headers = self.answer("GET", "/companion", {})
        self.assertEqual(status, 200)
        self.assertNotIn("X-Frame-Options", headers)
        self.assertEqual(headers["Content-Security-Policy"], f"frame-ancestors chrome-extension://{identity}")
        for path in ("/companion/", "/missing", "/static/index.html"):
            self.assertEqual(self.answer("GET", path, {})[1]["X-Frame-Options"], "DENY")
        self.assertEqual(self.answer("POST", "/companion", {})[1]["X-Frame-Options"], "DENY")

    def test_coaching_is_read_only_and_bound_to_the_current_solve(self):
        self.start()
        live = self.call("GET", "/api/state")[1]["live"]
        request = {"problem": live["problem"], "session_id": live["session_id"], "question": "What next?"}
        with unittest.mock.patch.object(self.server.coach.chat_jobs, "start") as start:
            self.assertEqual(self.call("POST", "/api/coaching", {**request, "session_id": "stale"})[0], 409)
            self.assertEqual(self.call("POST", "/api/coaching", {**request, "problem": "valid-anagram"})[0], 409)
            start.assert_not_called()
            before = self.files()
            status, result = self.call("POST", "/api/coaching", request)
            self.assertEqual(status, 200)
            self.assertEqual(result["state"], "running")
            self.assertEqual(self.files(), before)
            args = start.call_args.args[1]
            self.assertEqual(args[args.index("--tools") + 1], "")
            self.assertTrue(start.call_args.kwargs["collect"])

    def test_a_page_that_went_away_gets_no_500_and_the_terminal_stays_quiet(self):
        """A reload or a closed tab before the answer: writing it raises BrokenPipe or ConnectionReset."""
        handler = self.server.RequestHandlerClass
        with unittest.mock.patch.object(handler, "send", side_effect=BrokenPipeError(32, "Broken pipe")) as send, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            with socket.create_connection(("127.0.0.1", self.port), timeout=30) as page:
                page.sendall(b"GET /api/state HTTP/1.0\r\nHost: 127.0.0.1\r\nX-DSA-Coach: 1\r\n\r\n")
                self.assertEqual(page.recv(100), b"")  # the server hung up without an answer
        self.assertEqual((send.call_count, err.getvalue()), (1, ""))  # no try at a 500, and no traceback

    def test_a_port_another_server_holds_is_skipped(self):
        """127.0.0.1:p still binds while another server listens on *:p (on macOS, with SO_REUSEADDR) or on [::1]:p,
        and then localhost:p could reach either. make_server moves on to the next port instead."""
        for family, host in ((socket.AF_INET, ""), (socket.AF_INET6, "::1")):
            with self.subTest(host=host), socket.socket(family) as other:
                other.bind((host, 0))
                other.listen()
                taken = other.getsockname()[1]
                if taken < 65535:  # 65535 has no port above it to move on to
                    ours = server.make_server(self.root, port=taken, env=self.env)
                    ours.server_close()
                    self.assertNotEqual(ours.server_address[1], taken)

    def test_the_startup_line_reaches_a_pipe_at_once(self):
        """A launcher that reads the server's output gets the URL while the server runs."""
        env = dict(self.env)
        env.pop("PYTHONUNBUFFERED", None)
        proc = subprocess.Popen([sys.executable, str(REPO / "app" / "server.py"), "--root", str(self.root),
                                 "--port", "0", "--no-browser"], stdout=subprocess.PIPE, text=True, env=env)
        try:
            self.assertTrue(select.select([proc.stdout], [], [], 10)[0], "no startup line within 10 s")
            self.assertRegex(proc.stdout.readline(), r"^dsa-coach study app: http://127\.0\.0\.1:\d+/ ")
        finally:
            proc.terminate()
            proc.wait()
            proc.stdout.close()

    def test_a_bug_still_gets_an_answer_the_page_can_show(self):
        with unittest.mock.patch.dict(server.ROUTES, {("GET", "/api/state"): lambda coach, q: {}["boom"]}), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            status, body = self.call("GET", "/api/state")
        self.assertEqual((status, body), (500, {"error": "KeyError: 'boom'"}))
        self.assertIn("Traceback", err.getvalue())  # and the terminal gets the traceback


if __name__ == "__main__":
    unittest.main()
