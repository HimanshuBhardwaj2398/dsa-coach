"""Tests for app/server.py, the read-only learning app. Run: python3 -m unittest discover -s tests -v"""
import base64
import contextlib
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
import unittest
import unittest.mock
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402

COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dsa-server-test-"))
        self.root = self.tmp / "notebook"
        self.env = dict(os.environ, DSA_TODAY="2026-11-06", HOME=str(self.tmp / "home"))
        self.env.pop("DSA_NOTEBOOK", None)
        self.coach("init", "--name", "Tester", "--start-date", "2026-11-01", "--days", "90")
        self.server = server.make_server(self.root, port=0, env=self.env)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def coach(self, *args):
        subprocess.run([sys.executable, str(COACH), "--root", str(self.root), *args],
                       check=True, capture_output=True, env=self.env)

    def get(self, path, method="GET", host=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                                     headers={"Host": host} if host else {})
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, res.headers, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_map_carries_progress_due_and_the_live_solve(self):
        status, _, body = self.get("/api/map")
        view = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(len(view["patterns"]), 22)
        self.assertIsNone(view["live"])
        self.coach("solve", "start", "--problem", "binary-search")
        live = json.loads(self.get("/api/map")[2])["live"]
        self.assertEqual((live["problem"], live["stage"]), ("binary-search", 1))

    def test_reading_never_writes_the_notebook(self):
        self.coach("solve", "start", "--problem", "binary-search")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for path in ("/", "/panel", "/api/map", "/static/app.js"):
            self.get(path)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file() and p.name != ".notebook.lock"}
        self.assertEqual(after, {p: b for p, b in before.items() if p.name != ".notebook.lock"})

    def test_every_write_is_refused(self):
        for method in ("POST", "PUT", "DELETE"):
            for path in ("/api/map", "/api/solve/start", "/api/coaching", "/panel"):
                self.assertEqual(self.get(path, method)[0], 405, (method, path))

    def test_retired_routes_are_gone(self):
        for path in ("/api/state", "/api/attempt", "/api/explainer?pattern=stack", "/companion"):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_explainer_page_is_sandboxed_and_only_a_registered_one_is_served(self):
        self.assertEqual(self.get("/explainer/stack")[0], 404)
        page = self.tmp / "stack.html"
        page.write_text("<h1>Stack</h1>")
        self.coach("artifact", "add", "--concept", "stack", "--title", "Stack, explained", "--file", str(page))
        status, headers, body = self.get("/explainer/stack")
        self.assertEqual((status, body), (200, b"<h1>Stack</h1>"))
        self.assertEqual(headers["Content-Security-Policy"], "sandbox allow-scripts allow-popups")
        self.assertEqual(self.get("/explainer/..%2Fconfig.json")[0], 404)

    def test_binds_to_localhost_only_and_refuses_other_hosts(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(self.get("/api/map", host="evil.test")[0], 403)
        self.assertEqual(self.get("/api/map", host=f"localhost:{self.port}")[0], 200)

    def test_static_files_stay_inside_the_static_folder(self):
        self.assertEqual(self.get("/static/app.css")[0], 200)
        for path in ("/static/../server.py", "/static/%2e%2e/server.py", "/missing"):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_no_page_but_the_panel_can_be_framed_and_only_by_the_pinned_extension(self):
        manifest = json.loads((REPO / "extensions/dsa-coach/manifest.json").read_text())
        digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
        identity = "".join(chr(ord("a") + int(c, 16)) for c in digest)
        status, headers, body = self.get("/panel")
        self.assertEqual(status, 200)
        self.assertIn(b'name="dsa-coach-app"', body)
        self.assertNotIn("X-Frame-Options", headers)
        self.assertEqual(headers["Content-Security-Policy"], f"frame-ancestors chrome-extension://{identity}")
        for path in ("/", "/panel/", "/api/map", "/missing", "/static/index.html"):
            self.assertEqual(self.get(path)[1]["X-Frame-Options"], "DENY", path)

    def test_a_page_that_went_away_gets_no_500_and_the_terminal_stays_quiet(self):
        handler = self.server.RequestHandlerClass
        with unittest.mock.patch.object(handler, "send", side_effect=BrokenPipeError(32, "Broken pipe")) as send, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            with socket.create_connection(("127.0.0.1", self.port), timeout=30) as page:
                page.sendall(b"GET /api/map HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
                self.assertEqual(page.recv(100), b"")
        self.assertEqual((send.call_count, err.getvalue()), (1, ""))

    def test_a_bug_still_gets_an_answer_the_page_can_show(self):
        with unittest.mock.patch.object(server, "read_map", side_effect=KeyError("boom")), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            status, _, body = self.get("/api/map")
        self.assertEqual((status, json.loads(body)), (500, {"error": "KeyError: 'boom'"}))
        self.assertIn("Traceback", err.getvalue())

    def test_a_port_another_server_holds_is_skipped(self):
        for family, host in ((socket.AF_INET, ""), (socket.AF_INET6, "::1")):
            with self.subTest(host=host), socket.socket(family) as other:
                other.bind((host, 0))
                other.listen()
                taken = other.getsockname()[1]
                if taken < 65535:
                    ours = server.make_server(self.root, port=taken, env=self.env)
                    ours.server_close()
                    self.assertNotEqual(ours.server_address[1], taken)

    def test_the_startup_line_reaches_a_pipe_at_once(self):
        env = dict(self.env)
        env.pop("PYTHONUNBUFFERED", None)
        proc = subprocess.Popen([sys.executable, str(REPO / "app" / "server.py"), "--root", str(self.root),
                                 "--port", "0", "--no-browser"], stdout=subprocess.PIPE, text=True, env=env)
        try:
            self.assertTrue(select.select([proc.stdout], [], [], 10)[0], "no startup line within 10 s")
            self.assertRegex(proc.stdout.readline(), r"^dsa-coach learning app: http://127\.0\.0\.1:\d+/ ")
        finally:
            proc.terminate()
            proc.wait()
            proc.stdout.close()


if __name__ == "__main__":
    unittest.main()
