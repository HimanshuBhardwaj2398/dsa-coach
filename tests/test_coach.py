"""Tests for skills/dsa-coach/scripts/coach.py. Run: python3 -m unittest discover -s tests -v"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COACH = HERE.parent / "skills" / "dsa-coach" / "scripts" / "coach.py"


class CoachTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dsa-coach-test-"))
        self.root = self.tmp / "notebook"
        self.env = dict(os.environ, DSA_TODAY="2026-11-01", HOME=str(self.tmp / "home"))
        self.env.pop("DSA_NOTEBOOK", None)
        self.run_cli("init", "--name", "Tester", "--start-date", "2026-11-01", "--days", "90")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, today=None, ok=True):
        env = dict(self.env)
        if today:
            env["DSA_TODAY"] = today
        proc = subprocess.run([sys.executable, str(COACH), "--root", str(self.root), *args],
                              capture_output=True, text=True, env=env, cwd=self.tmp)
        if ok and proc.returncode != 0:
            self.fail(f"coach {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}")
        return proc

    def journey(self):
        return json.loads((self.root / "journey.json").read_text())

    def attempt(self, problem, date, outcome="solved", hints=0, **kw):
        args = ["log", "attempt", "--problem", problem, "--pattern", kw.get("pattern", "sliding-window"),
                "--outcome", outcome, "--hints", str(hints), "--date", date,
                "--minutes", str(kw.get("minutes", 20)), "--mode", kw.get("mode", "practice")]
        if kw.get("technique"):
            args += ["--technique", kw["technique"]]
        if kw.get("confidence"):
            args += ["--confidence", str(kw["confidence"])]
        if kw.get("mistakes"):
            args += ["--mistakes", kw["mistakes"]]
        if kw.get("complexity", True):
            args.append("--complexity-stated")
        return self.run_cli(*args, today=date)

    def next_item(self, *args, today=None):
        return json.loads(self.run_cli("next", "--json", *args, today=today).stdout)

    # ------------------------------------------------------------------ init
    def test_init_creates_layout_and_snapshot(self):
        for rel in ["config.json", "JOURNEY.md", "journey.json", "learner/summary.md", "learner/cards.json",
                    "learner/attempts.jsonl", "artifacts/registry.json", "inbox/imported", "exports", "README.md"]:
            self.assertTrue((self.root / rel).exists(), rel)
        cfg = json.loads((self.root / "config.json").read_text())
        self.assertEqual(cfg["target_date"], "2027-01-30")
        j = self.journey()
        self.assertEqual(j["plan"]["day"], 1)
        self.assertEqual(j["plan"]["phase"], "Foundations")
        self.assertEqual(j["focus"], "arrays-hashing")  # nothing logged: first planned pattern
        self.assertTrue(any(s.startswith("This week's plan") for s in j["next_steps"]))
        self.assertEqual(j["behind"], [])
        self.assertLessEqual(len((self.root / "learner/summary.md").read_text().splitlines()), 60)

    def test_behind_plan_and_session_digest(self):
        self.run_cli("log", "session", "--summary", "Did a thing.\nSecond line.", "--minutes", "30")
        j = json.loads(self.run_cli("snapshot", "--date", "2026-11-20").stdout and (self.root / "journey.json").read_text())
        self.assertEqual(j["plan"]["week"], 3)
        self.assertIn("arrays-hashing", j["behind"])
        self.assertEqual(j["sessions"][-1], {"date": "2026-11-01", "summary": "Did a thing."})
        self.assertIn("Last session: 2026-11-01: Did a thing.", (self.root / "learner/summary.md").read_text())

    def test_init_is_idempotent(self):
        (self.root / "learner/attempts.jsonl").write_text('{"id": "a0001"}\n')
        out = self.run_cli("init")
        self.assertIn("already initialized", out.stdout)
        self.assertIn("a0001", (self.root / "learner/attempts.jsonl").read_text())

    # ------------------------------------------------------------------ schedule and statuses
    def test_resolve_ladder_and_statuses(self):
        self.attempt("minimum-window-substring", "2026-11-01", hints=3, technique="explainer-predict")
        j = self.journey()
        p = j["problems"]["minimum-window-substring"]
        self.assertEqual((p["status"], p["next_due"]), ("learning", "2026-11-02"))
        self.attempt("minimum-window-substring", "2026-11-02")  # unaided, but only 1 day later
        p = self.journey()["problems"]["minimum-window-substring"]
        self.assertEqual((p["status"], p["next_due"]), ("practicing", "2026-11-05"))
        self.attempt("minimum-window-substring", "2026-11-05", minutes=22)  # 4 days after first, within cap
        p = self.journey()["problems"]["minimum-window-substring"]
        self.assertEqual((p["status"], p["next_due"]), ("ready", "2026-11-12"))
        self.attempt("minimum-window-substring", "2026-11-12", outcome="failed")
        p = self.journey()["problems"]["minimum-window-substring"]
        self.assertEqual(p["next_due"], "2026-11-13")  # reset to 1 day

    def test_hard_time_cap_and_hints_block_ready(self):
        self.attempt("p1", "2026-11-01")
        self.attempt("p1", "2026-11-05", minutes=60)  # over the 25-minute medium cap
        self.assertEqual(self.journey()["problems"]["p1"]["status"], "retained")
        self.attempt("p2", "2026-11-01")
        self.attempt("p2", "2026-11-05", hints=2)  # rung 2 is not unaided
        self.assertEqual(self.journey()["problems"]["p2"]["status"], "practicing")

    def test_review_gap_is_capped_by_target_date(self):
        self.run_cli("init")  # no-op
        cfg = json.loads((self.root / "config.json").read_text())
        cfg["target_date"] = "2026-11-21"
        (self.root / "config.json").write_text(json.dumps(cfg))
        for d in ["2026-11-01", "2026-11-02", "2026-11-05", "2026-11-12"]:
            self.attempt("p", d)
        # streak 4 would give 30 days; 9 days left * 0.3 -> cap 2
        self.assertEqual(self.journey()["problems"]["p"]["next_due"], "2026-11-14")

    def test_pattern_status_and_focus(self):
        self.attempt("a", "2026-11-01", pattern="two-pointers")
        self.run_cli("log", "question", "--concept", "sliding-window", "--text", "why?", "--date", "2026-11-02", today="2026-11-02")
        j = self.journey()
        rows = {r["key"]: r for r in j["patterns"]}
        self.assertEqual(rows["two-pointers"]["status"], "practicing")
        self.assertEqual(rows["sliding-window"]["status"], "exploring")
        self.assertEqual(j["focus"], "sliding-window")  # most recent activity

    # ------------------------------------------------------------------ technique ledger
    def test_technique_credit_only_after_delay(self):
        self.attempt("x", "2026-11-01", hints=4, technique="worked-example")
        self.attempt("x", "2026-11-02")  # too soon: no credit
        self.assertEqual(self.journey()["techniques"], [])
        self.attempt("x", "2026-11-04")  # 3 days after exposure: credit
        t = self.journey()["techniques"]
        self.assertEqual(len(t), 1)
        self.assertEqual((t[0]["technique"], t[0]["trials"], t[0]["successes"], t[0]["provisional"]), ("worked-example", 1, 1, True))
        self.attempt("y", "2026-11-01", technique="worked-example")
        self.attempt("y", "2026-11-06", outcome="failed")
        t = self.journey()["techniques"][0]
        self.assertEqual((t["trials"], t["successes"], t["estimate"]), (2, 1, 0.5))

    def test_ai_mode_is_assisted_and_never_credits(self):
        self.attempt("z", "2026-11-01", technique="hint-ladder")
        self.attempt("z", "2026-11-05", mode="ai")
        rows = [json.loads(l) for l in (self.root / "learner/attempts.jsonl").read_text().splitlines()]
        self.assertTrue(rows[-1]["assisted"])
        self.assertEqual(self.journey()["techniques"], [])

    # ------------------------------------------------------------------ cards
    def test_card_lifecycle(self):
        out = self.run_cli("card", "add", "--concept", "sliding-window", "--type", "invariant", "--front", "Q?", "--back", "A.", "--draft")
        self.assertIn("c0001", out.stdout)
        self.assertEqual(self.journey()["due"]["drafts"], 1)
        bad = self.run_cli("card", "review", "--id", "c0001", "--grade", "pass", ok=False)
        self.assertNotEqual(bad.returncode, 0)
        self.run_cli("card", "accept", "--id", "c0001")
        cards = json.loads((self.root / "learner/cards.json").read_text())
        self.assertEqual((cards[0]["status"], cards[0]["due"]), ("active", "2026-11-02"))
        quiz = self.run_cli("quiz", today="2026-11-02")
        self.assertIn("Q?", quiz.stdout)
        self.assertNotIn("A.", quiz.stdout)
        self.run_cli("card", "review", "--id", "c0001", "--grade", "pass", "--date", "2026-11-02", today="2026-11-02")
        self.run_cli("card", "review", "--id", "c0001", "--grade", "pass", "--date", "2026-11-05", today="2026-11-05")
        cards = json.loads((self.root / "learner/cards.json").read_text())
        self.assertEqual(cards[0]["due"], "2026-11-12")  # 1 -> 3 -> 7 days
        self.run_cli("card", "review", "--id", "c0001", "--grade", "pass", "--date", "2026-11-12", today="2026-11-12")
        self.assertEqual(self.journey()["totals"]["cards_held"], 1)  # passed after a 7-day gap
        self.run_cli("card", "review", "--id", "c0001", "--grade", "fail", "--date", "2026-11-26", today="2026-11-26")
        cards = json.loads((self.root / "learner/cards.json").read_text())
        self.assertEqual(cards[0]["due"], "2026-11-27")

    # ------------------------------------------------------------------ artifacts, questions, concepts
    def test_artifact_copy_and_version(self):
        page = self.tmp / "page.html"
        page.write_text("<h1>x</h1>")
        self.run_cli("concept", "add", "--slug", "sliding-window", "--title", "Sliding Window", "--pattern", "sliding-window")
        self.run_cli("artifact", "add", "--concept", "sliding-window", "--title", "Page", "--file", str(page), "--url", "https://example.org/a")
        self.assertTrue((self.root / "concepts/sliding-window/page.html").exists())
        self.run_cli("artifact", "add", "--concept", "sliding-window", "--title", "Page", "--url", "https://example.org/b")
        reg = json.loads((self.root / "artifacts/registry.json").read_text())
        self.assertEqual((len(reg), reg[0]["version"], reg[0]["url"]), (1, 2, "https://example.org/b"))
        self.run_cli("log", "question", "--concept", "sliding-window", "--text", "First?")
        self.run_cli("log", "question", "--concept", "sliding-window", "--text", "Second?")
        notes = (self.root / "concepts/sliding-window/notes.md").read_text()
        self.assertLess(notes.index("Second?"), notes.index("First?"))
        self.assertIn("\n\n## Changelog", notes)

    # ------------------------------------------------------------------ delta import / export
    def test_import_valid_and_invalid_delta(self):
        example = json.loads((COACH.parent.parent / "assets" / "delta-example.json").read_text())
        (self.root / "inbox" / "good.json").write_text(json.dumps(example))
        broken = dict(example, attempts=[dict(example["attempts"][0], pattern="nope", hints=9)])
        (self.root / "inbox" / "bad.json").write_text(json.dumps(broken))
        out = self.run_cli("import")
        self.assertIn("Imported good.json", out.stdout)
        self.assertIn("skip bad.json", out.stdout)
        self.assertIn("hints must be 0-7", out.stdout)
        self.assertTrue((self.root / "inbox/imported/good.json").exists())
        self.assertTrue((self.root / "inbox/bad.json").exists())
        j = self.journey()
        self.assertEqual(j["totals"]["attempts"], 2)
        self.assertEqual(j["due"]["drafts"], 1)
        self.assertEqual(len(j["artifacts"]), 1)
        session = (self.root / "sessions/2026-11-02.md").read_text()
        self.assertIn("claude-web", session)

    def test_export_pack(self):
        self.run_cli("export")
        pack = (self.root / "exports/pack-2026-11-01.md").read_text()
        self.assertIn("Learner summary", pack)
        self.assertIn("dsa-coach-delta/1", pack)
        self.assertIn("Rules for every mode", pack)

    # ------------------------------------------------------------------ practice pick
    def test_next_follows_the_plan_over_recent_activity(self):
        self.run_cli("log", "question", "--concept", "sliding-window", "--text", "why?")
        item = self.next_item()
        self.assertEqual((item["kind"], item["pattern"], item["problem"], item["first"]),
                         ("new", "arrays-hashing", "two-sum", True))

    def test_next_priority_order(self):
        self.attempt("two-sum", "2026-11-01", pattern="arrays-hashing", hints=3)  # re-solve due 11-02
        self.run_cli("card", "add", "--concept", "arrays-hashing", "--type", "trigger", "--front", "Q?", "--back", "A.", "--draft")
        self.run_cli("card", "accept", "--id", "c0001")  # due 11-02
        (self.root / "inbox" / "d.json").write_text("{}")
        self.assertEqual(self.next_item(today="2026-11-02")["kind"], "inbox")
        (self.root / "inbox" / "d.json").unlink()
        item = self.next_item(today="2026-11-02")
        self.assertEqual((item["kind"], item["problem"]), ("resolve", "two-sum"))
        self.attempt("two-sum", "2026-11-02", pattern="arrays-hashing")
        item = self.next_item(today="2026-11-02")
        self.assertEqual((item["kind"], item["count"]), ("cards", 1))
        self.run_cli("card", "review", "--id", "c0001", "--grade", "pass", "--date", "2026-11-02", today="2026-11-02")
        item = self.next_item(today="2026-11-02")
        self.assertEqual((item["kind"], item["problem"], item["first"]), ("new", "group-anagrams", False))

    def test_next_leaves_the_choice_to_the_coach_after_named_problems(self):
        for slug in ("two-sum", "group-anagrams", "longest-consecutive-sequence"):
            self.attempt(slug, "2026-11-01", pattern="arrays-hashing")
        item = self.next_item()
        self.assertEqual((item["kind"], item["pattern"], item["problem"]), ("new", "arrays-hashing", None))
        self.assertIn("NeetCode", self.run_cli("next").stdout)

    def test_next_pattern_filter(self):
        self.attempt("two-sum", "2026-11-01", pattern="arrays-hashing", hints=3)
        item = self.next_item("--pattern", "Sliding Window", today="2026-11-02")  # skips the due re-solve
        self.assertEqual((item["kind"], item["problem"]), ("new", "longest-substring-without-repeating-characters"))
        bad = self.run_cli("next", "--pattern", "nope", ok=False)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("arrays-hashing", bad.stderr)

    def test_pick_new_skips_long_formats_and_finished_patterns(self):
        spec = importlib.util.spec_from_file_location("coach", COACH)
        coach = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coach)
        rows = [
            {"key": "stack", "name": "Stack", "week": 2, "tier": 1, "target": 1, "attempted": 1, "next_problem": None},
            {"key": "machine-coding", "name": "Machine Coding", "week": 3, "tier": 3, "target": 4, "attempted": 0, "next_problem": "lru-cache"},
            {"key": "trees", "name": "Trees", "week": 4, "tier": 1, "target": 15, "attempted": 0, "next_problem": "maximum-depth-of-binary-tree"},
        ]
        self.assertEqual(coach.pick_new(rows)["pattern"], "trees")
        self.assertIsNone(coach.pick_new(rows[:2]))

    def test_status_steps_match_next_and_put_practice_before_drafts(self):
        self.run_cli("log", "question", "--concept", "sliding-window", "--text", "why?")
        self.run_cli("card", "add", "--concept", "sliding-window", "--type", "trap", "--front", "Q?", "--back", "A.", "--draft")
        steps = self.journey()["next_steps"]
        self.assertTrue(steps[0].startswith("Solve two-sum"), steps)
        self.assertTrue(steps[1].startswith("Approve"), steps)

    # ------------------------------------------------------------------ status, validate, package, install
    def test_status_and_validate(self):
        out = self.run_cli("status", "--brief")
        self.assertIn("day 1/90", out.stdout)
        self.assertLessEqual(len(out.stdout.splitlines()), 10)
        out = self.run_cli("validate")
        self.assertIn("OK", out.stdout)

    def test_validate_flags_bad_attempt(self):
        with (self.root / "learner/attempts.jsonl").open("a") as fh:
            fh.write(json.dumps({"id": "a0009", "date": "2026-11-01", "problem": "p", "pattern": "nope", "outcome": "solved"}) + "\n")
        out = self.run_cli("validate", ok=False)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("a0009", out.stdout)

    def test_package_zip(self):
        dest = self.tmp / "dist" / "dsa-coach.zip"
        self.run_cli("package", "--out", str(dest))
        names = zipfile.ZipFile(dest).namelist()
        self.assertIn("dsa-coach/SKILL.md", names)
        self.assertIn("dsa-coach/scripts/coach.py", names)
        self.assertFalse(any("__pycache__" in n for n in names))

    def test_install_into_a_copy_of_the_workspace(self):
        ws = self.tmp / "ws"
        shutil.copytree(COACH.parent.parent, ws / "skills" / "dsa-coach")
        coach = ws / "skills" / "dsa-coach" / "scripts" / "coach.py"
        proc = subprocess.run([sys.executable, str(coach), "install"], capture_output=True, text=True, env=self.env, cwd=ws)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((ws / ".claude/skills/dsa-coach/SKILL.md").exists())
        self.assertTrue((ws / ".agents/skills/dsa-coach/SKILL.md").exists())
        self.assertTrue((ws / ".claude/skills/dsa-coach").is_symlink())
        settings = json.loads((ws / ".claude/settings.json").read_text())
        self.assertIn("status --brief", json.dumps(settings))
        again = subprocess.run([sys.executable, str(coach), "install"], capture_output=True, text=True, env=self.env, cwd=ws)
        self.assertIn("already linked", again.stdout)
        self.assertIn("already present", again.stdout)


if __name__ == "__main__":
    unittest.main()
