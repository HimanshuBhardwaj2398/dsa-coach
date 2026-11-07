"""The problem catalogue (assets/problems.json). Run: python3 -m unittest discover -s tests -v"""
import importlib.util
import sys
import unittest
from pathlib import Path

COACH = Path(__file__).resolve().parent.parent / "skills" / "dsa-coach" / "scripts" / "coach.py"
sys.path.insert(0, str(COACH.parent))
spec = importlib.util.spec_from_file_location("coach", COACH)
coach = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coach)


class CatalogueTest(unittest.TestCase):
    def test_shipped_catalogue_fits_the_roadmap(self):
        self.assertEqual(coach.catalogue_issues(coach.load_catalogue(), coach.load_roadmap()), [])

    def test_shipped_catalogue_holds_both_lists(self):
        rows = [r for rows in coach.load_catalogue().values() for r in rows]
        self.assertEqual(sum("blind75" in r["lists"] for r in rows), 75)
        self.assertEqual(sum("nc150" in r["lists"] for r in rows), 150)

    def test_reports_what_doesnt_fit(self):
        roadmap = {"patterns": [{"key": "stack", "canonical": ["valid-parentheses"]}]}
        bad = {"stack": [{"slug": "Bad Slug", "title": "", "difficulty": "trivial", "lists": ["top100"]},
                         {"slug": "min-stack", "title": "Min Stack", "difficulty": "medium", "lists": ["nc150"]},
                         {"slug": "min-stack", "title": "Min Stack", "difficulty": "medium", "lists": ["nc150"]}],
               "nope": []}
        issues = "\n".join(coach.catalogue_issues(bad, roadmap))
        for expected in ("nope isn't a roadmap pattern", "lacks its canonical problem valid-parentheses",
                         "bad slug 'Bad Slug'", "min-stack is listed twice", "no title", "difficulty 'trivial'",
                         "lists ['top100']"):
            self.assertIn(expected, issues)
