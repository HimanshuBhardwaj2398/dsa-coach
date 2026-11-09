"""The four stage names are written out in coach.py, the study app, the panel and the pane: they must agree."""
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "dsa-coach" / "scripts"))
import coach  # noqa: E402


class StageNamesTest(unittest.TestCase):
    def test_every_consumer_lists_the_same_four_stages(self):
        names = [name for name, _ in coach.STAGES]
        self.assertEqual(names, ["Understand", "Find an approach", "Build it", "Check and finish"])
        app = (REPO / "app/static/app.js").read_text(encoding="utf-8")
        table = app.split("const STAGES = [", 1)[1].split("];", 1)[0]
        self.assertEqual(re.findall(r'^\s*\["([^"]+)"', table, re.M), names)
        panel = (REPO / "app/static/companion.js").read_text(encoding="utf-8")
        self.assertEqual(json.loads(re.search(r"COMPANION_STAGE_NAMES = (\[[^\]]*\])", panel).group(1)), names)
        pane = (REPO / "plugins/dsa-coach-pane/hooks/register.tsx").read_text(encoding="utf-8")
        table = pane.split("const STAGES", 1)[1].split("]\n", 1)[0]
        self.assertEqual(re.findall(r"\['([^']+)', '", table), names)
        self.assertEqual(re.findall(r"\['[^']+', '([^']+)'\]", table), [phase for _, phase in coach.STAGES])


if __name__ == "__main__":
    unittest.main()
