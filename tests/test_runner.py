"""Tests for app/runner.py. Run: python3 -m unittest discover -s tests -v"""
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import runner  # noqa: E402

GOOD = '''
class Solution:
    def _mid(self, lo, hi):
        return (lo + hi) // 2

    def search(self, nums, target):
        lo, hi = 0, len(nums) - 1
        while lo < hi:  # the bug from 2026-11-05: misses the last candidate
            mid = self._mid(lo, hi)
            if nums[mid] == target:
                return mid
            if nums[mid] > target:
                hi = mid - 1
            else:
                lo = mid + 1
        return -1

EXAMPLES = [
    (([-1, 0, 3, 5, 9, 12], 9), 4),
    (([5], 5), 0),  # edge
]
'''


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dsa-runner-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_text(self, text, timeout=5):
        path = self.tmp / "attempt.py"
        path.write_text(textwrap.dedent(text))
        return runner.run(path, timeout=timeout)

    def test_ok_and_fail_rows_and_the_method_skips_helpers(self):
        r = self.run_text(GOOD)
        self.assertEqual(r["method"], "search")
        self.assertEqual([row["ok"] for row in r["rows"]], [True, False])
        self.assertEqual(r["rows"][1]["args"], "[5], 5")
        self.assertEqual((r["rows"][1]["expected"], r["rows"][1]["got"]), ("0", "-1"))
        self.assertFalse(r["ok"])
        self.assertIsNone(r["error"])

    def test_an_exception_shows_its_traceback_and_other_rows_still_run(self):
        r = self.run_text('''
            class Solution:
                def f(self, x):
                    return 10 // x
            EXAMPLES = [((0,), 0), ((5,), 2)]
        ''')
        self.assertIn("ZeroDivisionError", r["rows"][0]["error"])
        self.assertTrue(r["rows"][1]["ok"])

    def test_prints_are_kept_per_row(self):
        r = self.run_text('''
            print("loading")
            class Solution:
                def f(self, x):
                    print("x is", x)
                    return x
            EXAMPLES = [((1,), 1)]
        ''')
        self.assertEqual(r["rows"][0]["stdout"], "x is 1\n")
        self.assertTrue(r["ok"])

    def test_an_infinite_loop_times_out(self):
        r = self.run_text('''
            class Solution:
                def f(self, x):
                    while True:
                        pass
            EXAMPLES = [((1,), 1)]
        ''', timeout=1)
        self.assertIn("timed out", r["error"])
        self.assertFalse(r["ok"])

    def test_missing_pieces_are_explained(self):
        self.assertIn("No examples yet", self.run_text("class Solution:\n    def f(self, x):\n        return x\n")["error"])
        self.assertIn("no class Solution", self.run_text("EXAMPLES = [((1,), 1)]\n")["error"])
        self.assertIn("Write the method", self.run_text("class Solution:\n    pass\nEXAMPLES = [((1,), 1)]\n")["error"])
        self.assertIn("didn't load", self.run_text("class Solution:\n    def f(self, x:\n")["error"])
        self.assertIn("must be ((args", self.run_text(
            "class Solution:\n    def f(self, x):\n        return x\nEXAMPLES = [1]\n")["rows"][0]["error"])

    def test_leetcode_type_hints_load_without_a_typing_import(self):
        r = self.run_text('''
            """two-sum"""
            from __future__ import annotations


            class Solution:
                def total(self, nums: List[int]) -> int:
                    return sum(nums)


            EXAMPLES = [(([1, 2, 3],), 6)]
        ''')
        self.assertIsNone(r["error"])
        self.assertEqual(r["method"], "total")
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    unittest.main()
