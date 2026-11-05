"""Tests for app/attempt_file.py. Run: python3 -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import attempt_file as af  # noqa: E402

TEMPLATE = (REPO / "skills" / "dsa-coach" / "assets" / "templates" / "solve.py").read_text()


def blank():
    return TEMPLATE.format(problem="binary-search", url="https://leetcode.com/problems/binary-search/",
                           date="2026-11-06", pattern_line=" Pattern: Binary Search.")


class PlanCardTest(unittest.TestCase):
    def test_blank_template_has_every_field_empty(self):
        self.assertEqual(af.read_plan_card(blank()), {f: "" for f in af.PLAN_FIELDS})

    def test_write_then_read_round_trips_and_keeps_the_rest(self):
        card = {"State": "lo, hi", "Invariant": "target, if present, is in nums[lo..hi]",
                "Hand trace": "[5], 5: lo=0 hi=0 mid=0 -> found\n[-1,0,3], 3: lo=0 hi=2 mid=1 -> lo=2"}
        text = af.write_plan_card(blank(), card)
        self.assertIn("    Invariant: target, if present, is in nums[lo..hi]\n", text)
        self.assertIn("    Hand trace: [5], 5: lo=0 hi=0 mid=0 -> found\n        [-1,0,3], 3:", text)
        back = af.read_plan_card(text)
        self.assertEqual({k: back[k] for k in card}, card)
        self.assertEqual(back["Complexity"], "")
        self.assertIn("class Solution:", text)
        again = af.write_plan_card(text, {"Hand trace": "short"})
        self.assertEqual(af.read_plan_card(again)["Hand trace"], "short")
        self.assertNotIn("[-1,0,3]", again)

    def test_a_file_without_a_docstring(self):
        self.assertEqual(af.read_plan_card("class Solution:\n    pass\n"), {})
        with self.assertRaises(ValueError):
            af.write_plan_card("class Solution:\n    pass\n", {"State": "x"})


class ExamplesTest(unittest.TestCase):
    rows = [{"args": "[-1, 0, 3, 5, 9, 12], 9", "expected": "4", "edge": False},
            {"args": "[5]", "expected": "0", "edge": True}]

    def test_write_then_read_round_trips(self):
        text = af.write_examples(blank(), self.rows)
        self.assertIn("EXAMPLES = [\n    (([-1, 0, 3, 5, 9, 12], 9,), 4),\n    (([5],), 0),  # edge\n]", text)
        self.assertEqual(af.read_examples(text), self.rows)
        self.assertEqual(af.read_examples(af.write_examples(text, [])), [])

    def test_blank_template_has_no_examples(self):
        self.assertEqual(af.read_examples(blank()), [])

    def test_bad_literals_are_refused(self):
        with self.assertRaises(ValueError):
            af.write_examples(blank(), [{"args": "nums", "expected": "4", "edge": False}])
        with self.assertRaises(ValueError):
            af.write_examples(blank(), [{"args": "[1]", "expected": "", "edge": False}])

    def test_half_written_code_elsewhere_doesnt_matter(self):
        text = af.write_examples(blank(), self.rows).replace("    pass\n", "    def search(self, nums, target:\n", 1)
        self.assertEqual(af.read_examples(text), self.rows)
        self.assertEqual(af.read_examples(af.write_examples(text, self.rows[:1])), self.rows[:1])

    def test_no_examples_list(self):
        self.assertEqual(af.read_examples("x = 1\n"), [])
        with self.assertRaises(ValueError):
            af.write_examples("x = 1\n", self.rows)


class TemplateTest(unittest.TestCase):
    def test_the_real_template_filled_in_parses(self):
        text = TEMPLATE.format(problem="best-time-to-buy-and-sell-stock",
                               url="https://leetcode.com/problems/best-time-to-buy-and-sell-stock/",
                               date="2026-11-06", pattern_line="")
        self.assertIn('"""\nfrom __future__ import annotations\n', text)
        self.assertEqual(af.read_plan_card(text), {f: "" for f in af.PLAN_FIELDS})
        self.assertEqual(af.read_examples(text), [])


if __name__ == "__main__":
    unittest.main()
