"""Built explainers: the recorder counts what really ran, and every spec in the notebook still builds.

Building a spec runs its oracle against brute force, its invariant at every step and its count bound, so a spec that
drifted from its code fails here. The browser side is tests/browser/check_explainers.py.
"""
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "dsa-coach" / "scripts"))
import build_explainer as bx  # noqa: E402

SPECS = sorted((REPO / "notebook" / "concepts").glob("*/spec.py"))


def toy(nums):
    total = 0
    pairs = [[x, x] for x in nums]  # a comprehension: one run of this line, however many items
    for a, b in pairs:
        total += a + b
    return total


class RecorderTest(unittest.TestCase):
    def test_runs_per_line_are_what_executed(self):
        runs, result = bx.record(toy, ([1, 2, 3],), counts_only=True)
        self.assertEqual(result, 12)
        code, _ = bx.source_of(toy)
        by_text = {code[line - 1].strip(): n for line, n in runs.items()}
        self.assertEqual(by_text["pairs = [[x, x] for x in nums]  # a comprehension: one run of this line, however many items"], 1)
        self.assertEqual(by_text["total += a + b"], 3)
        self.assertEqual(by_text["for a, b in pairs:"], 4)  # three passes and the check that ends the loop

    def test_steps_carry_the_frame_locals_and_the_return(self):
        events, _ = bx.record(toy, ([5],))
        self.assertEqual(events[-1]["kind"], "return")
        self.assertEqual(events[-1]["ret"], 10)
        last_line = [e for e in events if e["kind"] == "line"][-1]
        self.assertEqual(last_line["stack"][-1][1]["total"], 10)

    def test_tree_layout_puts_a_parent_over_its_children(self):
        pos = bx.tree_layout("r", {"r": ["a", "b"], "a": ["c", "d"]})
        self.assertEqual(pos["r"][1], 0)
        self.assertEqual(pos["a"][0], (pos["c"][0] + pos["d"][0]) / 2)
        self.assertLess(pos["a"][0], pos["b"][0])


class SpecsBuildTest(unittest.TestCase):
    def test_every_spec_builds_into_a_whole_page(self):
        self.assertTrue(SPECS, "no specs found under notebook/concepts")
        for spec in SPECS:
            with self.subTest(pattern=spec.parent.name):
                page, info = bx.build(spec)
                self.assertTrue(page.startswith("<!doctype html>"))
                self.assertRegex(page, r"<title>[^<]+</title>")
                self.assertGreaterEqual(info["oracle_inputs"], 20)
                data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S)
                                  .group(1).replace("<\\/", "</"))
                self.assertEqual(len(data["spot"]["cases"]), 6)
                for trace in data["traces"]:
                    self.assertTrue(trace["steps"])
                    asks = [s["ask"] for s in trace["steps"] if "ask" in s]
                    for ask in asks:
                        if ask["options"] is not None:
                            self.assertIn(ask["answer"], [str(o) for o in ask["options"]])
                self.assertTrue(any("ask" in s for t in data["traces"] for s in t["steps"]), "no predictions")
                self.assertTrue(all(f["answer"] for f in data["check"]["fields"]))


if __name__ == "__main__":
    unittest.main()
