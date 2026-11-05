"""Tests for app/runner.py. Run: python3 -m unittest discover -s tests -v"""
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import attempt_file  # noqa: E402
import runner  # noqa: E402

TEMPLATE = (REPO / "skills" / "dsa-coach" / "assets" / "templates" / "solve.py").read_text()

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

    def test_a_timeout_names_the_example_it_stopped(self):
        r = self.run_text('''
            class Solution:
                def search(self, nums, target):
                    lo, hi = 0, len(nums) - 1
                    while lo <= hi:
                        mid = (lo + hi) // 2
                        if nums[mid] == target:
                            return mid
                        if nums[mid] < target:
                            lo = mid  # the bug: lo never gets past mid
                        else:
                            hi = mid - 1
                    return -1
            EXAMPLES = [(([1, 3, 5], 3), 1), (([1, 3, 5], 5), 2)]
        ''', timeout=2)
        self.assertEqual(set(r), {"ok", "method", "rows", "error"})
        self.assertFalse(r["ok"])
        self.assertTrue(r["rows"][0]["ok"])
        self.assertEqual(r["rows"][1], {"ok": False, "args": "[1, 3, 5], 5", "expected": "2", "got": None,
                                        "stdout": "", "error": "timed out on this example"})
        self.assertEqual(r["error"], "timed out after 2 s on the example ([1, 3, 5], 5) -> 2: "
                                     "an infinite loop, or too slow for these inputs")
        r = self.run_text("while True:\n    pass\n", timeout=1)  # stuck before any example starts
        self.assertEqual((r["rows"], r["error"]), ([], "timed out after 1 s: an infinite loop, or too slow for these inputs"))

    def test_input_fails_fast_instead_of_waiting_for_the_time_limit(self):
        read_end, write_end = os.pipe()  # a stdin nobody types into, like a terminal left alone
        saved = os.dup(0)
        os.dup2(read_end, 0)
        try:
            r = self.run_text('''
                class Solution:
                    def f(self, x):
                        return int(input())
                EXAMPLES = [((1,), 1)]
            ''', timeout=2)
        finally:
            os.dup2(saved, 0)
            for fd in (saved, read_end, write_end):
                os.close(fd)
        self.assertIsNone(r["error"])
        self.assertIn("EOFError", r["rows"][0]["error"])

    def test_exit_in_the_method_stays_on_its_row(self):
        r = self.run_text('''
            import sys
            class Solution:
                def f(self, x):
                    if x == 0:
                        sys.exit("stop")
                    if x == 1:
                        exit()
                    return x
            EXAMPLES = [((0,), 0), ((1,), 1), ((5,), 5)]
        ''')
        self.assertIn("SystemExit: stop", r["rows"][0]["error"])
        self.assertIn("SystemExit", r["rows"][1]["error"])
        self.assertTrue(r["rows"][2]["ok"])

    def test_the_real_template_end_to_end(self):
        text = TEMPLATE.format(problem="remove-element", url="https://leetcode.com/problems/remove-element/",
                               date="2026-11-06", pattern_line=" Pattern: Two Pointers.")
        # removeElement works in place. If the file's own __main__ loop ran first, it would rewrite EXAMPLES'
        # lists, and the runner's calls on them would return a different k: rows ok means the loop was skipped.
        text = text.replace("    pass\n", textwrap.indent(textwrap.dedent('''
            def removeElement(self, nums: List[int], val: int) -> int:
                k = 0
                for x in nums:
                    if x != val:
                        nums[k] = x
                        k += 1
                return k
        ''').lstrip("\n"), "    "), 1)
        text = attempt_file.write_examples(text, [{"args": "[3, 2, 2, 3], 3", "expected": "2", "edge": False},
                                                  {"args": "[0, 1, 2, 2, 3, 0, 4, 2], 2", "expected": "5", "edge": True}])
        path = self.tmp / "remove-element.py"
        path.write_text(text)
        r = runner.run(path)
        self.assertEqual((r["error"], r["method"]), (None, "removeElement"))
        self.assertEqual([row["ok"] for row in r["rows"]], [True, True])
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    unittest.main()
