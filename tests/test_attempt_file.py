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

    def test_a_one_line_docstring_has_no_plan_card(self):
        # Without a multi-line docstring, a class attribute named like a field is code, not the plan card.
        text = '"""binary-search"""\n\n\nclass Solution:\n    State: str = "x"\n\n    def f(self):\n        """Helper."""\n'
        self.assertEqual(af.read_plan_card(text), {})
        with self.assertRaisesRegex(ValueError, "no docstring"):
            af.write_plan_card(text, {"State": "lo, hi"})

    def test_a_field_with_no_line_in_the_docstring_is_refused(self):
        old = blank().replace("    Hand trace:\n", "")  # a file from the 0.4.0 template
        with self.assertRaisesRegex(ValueError, "Hand trace"):
            af.write_plan_card(old, {"State": "lo, hi", "Hand trace": "[5], 5: found"})
        self.assertEqual(af.read_plan_card(af.write_plan_card(old, {"State": "lo, hi", "Hand trace": ""}))["State"],
                         "lo, hi")

    def test_values_that_would_break_the_docstring_are_refused(self):
        for value in ['say """hi"""', "\\N", "\\x4", "\\u12", "\\U0001"]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Hand trace"):
                af.write_plan_card(blank(), {"Hand trace": value})
        fine = 'lo\\nhi and a "quote"'
        text = af.write_plan_card(blank(), {"Hand trace": fine})
        compile(text, "attempt.py", "exec")
        self.assertEqual(af.read_plan_card(text)["Hand trace"], fine)

    def test_keys_that_arent_plan_fields_are_ignored(self):
        self.assertEqual(af.write_plan_card(blank(), {"State": "lo, hi", "Notes": "x", "state": "y"}),
                         af.write_plan_card(blank(), {"State": "lo, hi"}))


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

    def test_a_row_that_wouldnt_read_back_as_written_is_refused(self):
        for args, expected in [("[2, 7], 9", "0, 1"), ("[2, 7], 9", "4  # note"), ("1,), (2", "0"), ("[1,\n2]", "0")]:
            with self.subTest(args=args, expected=expected), self.assertRaises(ValueError):
                af.write_examples(blank(), [{"args": args, "expected": expected, "edge": False}])
        with self.assertRaises(ValueError) as cm:
            af.format_row({"args": "[2, 7], 9", "expected": "0, 1"})
        self.assertEqual(str(cm.exception), "write the inputs and the output as Python values, "
                                            "such as [1, 2], 3, 'abc', True or None: got '0, 1'")
        with self.assertRaisesRegex(ValueError, r"got 'nums'$"):
            af.format_row({"args": "nums", "expected": "4"})

    def test_a_value_python_cant_build_is_refused(self):
        for row in ({"args": "{[1]: 2}", "expected": "0"}, {"args": "[1]", "expected": "{[1]: 2}"}):  # unhashable key
            with self.subTest(**row), self.assertRaisesRegex(ValueError, r"got '\{\[1\]: 2\}'$"):
                af.format_row(row)

    def test_input_nested_too_deeply_for_the_parser_is_a_value_error(self):
        # Python 3.12 raises RecursionError on the sum and MemoryError on the minus signs; 3.9 reads both.
        for nested in ("1+" * 100000 + "1", "-" * 100000 + "1"):
            with self.subTest(nested[:2]):
                self.assertRaises(ValueError, af.format_row, {"args": nested, "expected": "0"})
                try:
                    rows = af.read_examples(blank().replace("EXAMPLES = [\n]", f"EXAMPLES = [\n    (({nested},), 0),\n]"))
                except ValueError as e:
                    self.assertEqual(str(e), "EXAMPLES is nested too deeply to read")
                else:
                    self.assertEqual(rows[0]["args"], nested)

    def test_one_trailing_comma_in_the_inputs_is_allowed(self):
        # The template teaches (([7, 1, 5],), 4), so he may type that comma himself.
        for typed, plain in (("[5],", "[5]"), ("1, 2,", "1, 2"), ("[5] , ", "[5]")):
            with self.subTest(typed=typed):
                self.assertEqual(af.format_row({"args": typed, "expected": "0"}),
                                 af.format_row({"args": plain, "expected": "0"}))
        with self.assertRaisesRegex(ValueError, r"got '\[5\],,'$"):
            af.format_row({"args": "[5],,", "expected": "0"})

    def test_rows_the_table_cant_show_are_never_dropped(self):
        bad = blank().replace("EXAMPLES = [\n]", "EXAMPLES = [\n    (([1, 2]), 3),\n    (([5],), 0),\n]")
        with self.assertRaisesRegex(ValueError, r"\(\(\[1, 2\]\), 3\)"):
            af.read_examples(bad)
        with self.assertRaises(ValueError):
            af.write_examples(bad, self.rows)

    def test_examples_must_be_one_list_that_parses(self):
        cases = {"runs on": "EXAMPLES = [((1,), 1)]  # one line\n\nMORE = [\n]",
                 "not a list": "EXAMPLES = [((1,), 1)] + [((2,), 2)]",
                 "syntax error": "EXAMPLES = [\n    ((1,), 1\n]"}
        for case, block in cases.items():
            text = blank().replace("EXAMPLES = [\n]", block)
            with self.subTest(case):
                with self.assertRaises(ValueError):
                    af.read_examples(text)
                with self.assertRaises(ValueError):
                    af.write_examples(text, self.rows)
        with self.assertRaisesRegex(ValueError, "EXAMPLES has a syntax error"):
            af.read_examples(blank().replace("EXAMPLES = [\n]", cases["syntax error"]))

    def test_examples_whose_end_cant_be_found_are_refused(self):
        # Not read as no examples, while Run still runs the real ones.
        cases = {"a comment after ]": "EXAMPLES = [\n    ((1,), 1),\n]  # end",
                 "an indented ]": "EXAMPLES = [\n    ((1,), 1),\n    ]",
                 "one line with a comment": "EXAMPLES = [((1,), 1)]  # one"}
        message = r"^put the closing \] of EXAMPLES alone at the start of a line$"
        for case, block in cases.items():
            text = blank().replace("EXAMPLES = [\n]", block)
            with self.subTest(case):
                with self.assertRaisesRegex(ValueError, message):
                    af.read_examples(text)
                with self.assertRaisesRegex(ValueError, message):
                    af.write_examples(text, self.rows)

    def test_the_edge_marker_is_read_loosely(self):
        marks = ["  #edge", "  # Edge", "  # edge case", "  # edge: empty", ""]
        block = "EXAMPLES = [\n" + "".join(f"    (({i},), {i}),{m}\n" for i, m in enumerate(marks))
        block += '    (("# edge",), 5),\n    (("éééééééééé",), 6),  # edge\n]'  # only a comment after the row counts
        rows = af.read_examples(blank().replace("EXAMPLES = [\n]", block))
        self.assertEqual([r["edge"] for r in rows], [True, True, True, True, False, False, True])


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
