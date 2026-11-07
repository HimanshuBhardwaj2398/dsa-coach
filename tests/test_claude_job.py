"""Tests for app/claude_job.py. Run: python3 -m unittest discover -s tests -v"""
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import claude_job  # noqa: E402


def settle(jobs, key):
    for _ in range(200):
        s = jobs.status(key)
        if s["state"] != "running":
            return s
        time.sleep(0.01)
    raise AssertionError("the job never finished")


def done(code=0, out="", err=""):
    return lambda argv, **kw: subprocess.CompletedProcess(argv, code, out, err)


class JobsTest(unittest.TestCase):
    def test_idle_before_any_job(self):
        self.assertEqual(claude_job.Jobs().status("x"), {"state": "idle", "error": None})

    def test_success(self):
        jobs = claude_job.Jobs(run=done())
        jobs.start("x", ["claude", "-p", "hi"], cwd=".", timeout=5)
        self.assertEqual(settle(jobs, "x"), {"state": "done", "error": None})

    def test_failure_keeps_the_end_of_stderr(self):
        jobs = claude_job.Jobs(run=done(1, err="boom"))
        jobs.start("x", ["claude"], cwd=".", timeout=5)
        self.assertEqual(settle(jobs, "x"), {"state": "error", "error": "boom"})

    def test_missing_binary_and_timeout(self):
        def missing(argv, **kw):
            raise FileNotFoundError(argv[0])

        def slow(argv, **kw):
            raise subprocess.TimeoutExpired(argv, kw["timeout"])

        for run, text in ((missing, "can't find claude"), (slow, "longer than 5 s")):
            jobs = claude_job.Jobs(run=run)
            jobs.start("x", ["claude"], cwd=".", timeout=5)
            self.assertIn(text, settle(jobs, "x")["error"])

    def test_one_job_at_a_time(self):
        gate = threading.Event()

        def blocked(argv, **kw):
            gate.wait(5)
            return subprocess.CompletedProcess(argv, 0, "", "")

        jobs = claude_job.Jobs(run=blocked)
        jobs.start("a", ["claude"], cwd=".", timeout=5)
        with self.assertRaises(claude_job.Busy):
            jobs.start("b", ["claude"], cwd=".", timeout=5)
        gate.set()
        settle(jobs, "a")
        jobs.start("b", ["claude"], cwd=".", timeout=5)  # free again
        self.assertEqual(settle(jobs, "b")["state"], "done")
