"""Tests for app/server.py. Run: python3 -m unittest discover -s tests -v"""
import contextlib
import io
import json
import os
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

    def call(self, method, path, body=None, coach_header=True, host=None):
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

    def test_no_live_solve_is_a_404_on_every_route_that_needs_one(self):
        """Not a 409: the page takes a 409 from a save for a file conflict, and shows the disk version it carries."""
        for method, path, body in (("GET", "/api/attempt", None), ("PUT", "/api/attempt", {"text": "x", "mtime": 0}),
                                   ("PUT", "/api/attempt/parts", {"examples": [], "mtime": 0}),
                                   ("POST", "/api/run", {}), ("POST", "/api/solve/stage", {"n": 2}),
                                   ("POST", "/api/solve/note", {"stage": 1, "text": "x"}),
                                   ("POST", "/api/solve/break", {}), ("POST", "/api/solve/block", {}),
                                   ("POST", "/api/solve/end", {"outcome": "solved"})):
            status, answer = self.call(method, path, body)
            self.assertEqual(status, 404, path)
            self.assertTrue(answer["error"].startswith("no live solve"), answer)

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

    # beyond the plan: input checks, and requests the page would never send ------------------------------------
    def raw(self, request: bytes) -> int:
        """Send these bytes as the whole request; the status code of the answer."""
        with socket.create_connection(("127.0.0.1", self.port), timeout=30) as s:
            s.sendall(request)
            s.shutdown(socket.SHUT_WR)
            with s.makefile("rb") as answer:
                return int(answer.readline().split()[1])

    def post_raw(self, body: bytes = b"", length=None) -> int:
        return self.raw(b"POST /api/solve/note HTTP/1.0\r\nHost: 127.0.0.1\r\nX-DSA-Coach: 1\r\nContent-Length: "
                        + str(len(body) if length is None else length).encode() + b"\r\n\r\n" + body)

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

    def test_a_save_after_the_solve_ended_is_a_404_not_a_conflict(self):
        """e.g. the chat ended the solve while the page had unsaved edits: there's no disk version to offer."""
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        self.call("POST", "/api/solve/end", {"outcome": "solved"})
        for path, body in (("/api/attempt", {"text": attempt["text"] + "# more\n"}),
                           ("/api/attempt/parts", {"examples": []})):
            answer = self.call("PUT", path, dict(body, mtime=attempt["mtime"]))
            self.assertEqual(answer, (404, {"error": "no live solve"}), path)

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
        for body in (b"{", b"\xff", b"[" * 100000, b"[1, 2]", b'"text"'):
            self.assertEqual(self.post_raw(body), 400, body[:10])
        for length in ("abc", "-1", "100000000000"):
            self.assertEqual(self.post_raw(length=length), 400, length)

    def test_text_that_cant_be_saved_or_passed_on_is_a_400_and_changes_nothing(self):
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        before = (self.root / attempt["file"]).read_bytes()
        self.assertEqual(self.call("PUT", "/api/attempt", {"text": "x = '\ud800'", "mtime": attempt["mtime"]})[0], 400)
        self.assertEqual((self.root / attempt["file"]).read_bytes(), before)  # not emptied
        self.assertEqual(self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "\ud800"})[0], 400)
        self.assertFalse((self.root / "problems" / "binary-search" / "problem.md").exists())
        for text in ("\ud800", "a\x00b", "x" * 2_000_000):  # the last is too long for a command line
            self.assertEqual(self.call("POST", "/api/solve/note", {"stage": 1, "text": text})[0], 400, text[:5])
        self.assertNotIn("notes", self.call("GET", "/api/state")[1]["live"])

    def test_odd_slugs_and_static_names_are_refused(self):
        for slug in ("binary-search\n", "a" * 300, "../config", "Binary-Search", "", 5):
            self.assertEqual(self.call("PUT", "/api/problem", {"slug": slug, "text": "x"})[0], 400, repr(slug))
        self.assertFalse((self.root / "problems" / "binary-search\n").exists())
        self.assertEqual(self.call("PUT", "/api/problem", {"slug": "two-sum", "text": ""})[0], 400)
        self.assertFalse((self.root / "problems" / "two-sum").exists())  # a refused save makes no folder
        self.assertEqual(self.call("GET", "/api/problem?slug=" + "a" * 300)[0], 400)
        self.assertEqual(self.call("GET", "/static/" + "a" * 300)[0], 404)
        self.assertEqual(self.raw(b"GET /static/a\x00b HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"), 404)

    def test_a_bug_still_gets_an_answer_the_page_can_show(self):
        with unittest.mock.patch.dict(server.ROUTES, {("GET", "/api/state"): lambda coach, q: {}["boom"]}), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            status, body = self.call("GET", "/api/state")
        self.assertEqual((status, body), (500, {"error": "KeyError: 'boom'"}))
        self.assertIn("Traceback", err.getvalue())  # and the terminal gets the traceback


if __name__ == "__main__":
    unittest.main()
