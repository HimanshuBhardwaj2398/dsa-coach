"""Tests for skills/dsa-coach/scripts/coach.py. Run: python3 -m unittest discover -s tests -v"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COACH = HERE.parent / "skills" / "dsa-coach" / "scripts" / "coach.py"
sys.path.insert(0, str(COACH.parent))
from coach import notebook_lock


class CoachTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dsa-coach-test-"))
        self.root = self.tmp / "notebook"
        self.env = dict(os.environ, DSA_TODAY="2026-11-01", HOME=str(self.tmp / "home"))
        self.env.pop("DSA_NOTEBOOK", None)
        self.run_cli("init", "--name", "Tester", "--start-date", "2026-11-01", "--days", "90")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, today=None, ok=True, now=None, stdin=None):
        env = dict(self.env)
        if today:
            env["DSA_TODAY"] = today
        if now:
            env["DSA_NOW"] = f"2026-11-01T{now}:00+05:30"
        proc = subprocess.run([sys.executable, str(COACH), "--root", str(self.root), *args],
                              capture_output=True, text=True, env=env, cwd=self.tmp, input=stdin)
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
    def test_map_joins_catalogue_and_progress(self):
        self.attempt("best-time-to-buy-and-sell-stock", "2026-11-01", pattern="sliding-window")
        view = json.loads(self.run_cli("map", "--json", today="2026-11-01").stdout)
        sw = next(p for p in view["patterns"] if p["key"] == "sliding-window")
        self.assertEqual(sw["lists"], {"blind75": {"done": 1, "total": 4}, "nc150": {"done": 1, "total": 6}})
        row = sw["problems"][0]  # Blind 75 first
        self.assertEqual((row["slug"], row["status"], row["due"]), ("best-time-to-buy-and-sell-stock", "practicing", False))
        self.assertEqual(row["url"], "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/")
        self.assertEqual([("blind75" in x["lists"]) for x in sw["problems"]], [True] * 4 + [False] * 2)
        ml = next(p for p in view["patterns"] if p["key"] == "ml-coding")
        self.assertTrue(ml["format"])
        self.assertEqual(ml["problems"], [])
        self.assertIn("next_text", view)

    def test_map_names_the_latest_explainer(self):
        folder = self.root / "concepts" / "stack"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "stack-explainer.html").write_text("<p>stack</p>")
        self.run_cli("artifact", "add", "--concept", "stack", "--title", "Stack", "--file", str(folder / "stack-explainer.html"))
        view = json.loads(self.run_cli("map", "--json").stdout)
        stack = next(p for p in view["patterns"] if p["key"] == "stack")
        self.assertEqual(stack["explainer"], "concepts/stack/stack-explainer.html")

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

    def test_import_writes_nothing_when_any_part_is_invalid(self):
        self.run_cli("card", "add", "--concept", "two-pointers", "--front", "f", "--back", "b", "--draft")
        example = json.loads((COACH.parent.parent / "assets" / "delta-example.json").read_text())
        for broken in [dict(example, card_reviews=[{"id": "c0001", "grade": "pass"}]),  # a draft can't be reviewed
                       dict(example, session={"date": "02/11/2026"}),
                       dict(example, artifacts=[{"concept": "x", "title": "t", "file": "/no/such/page.html"}]),
                       dict(example, attempts="not a list"), ["not", "an", "object"]]:
            (self.root / "inbox" / "bad.json").write_text(json.dumps(broken))
            out = self.run_cli("import").stdout
            self.assertIn("skip bad.json: nothing imported", out)
            self.assertFalse((self.root / "learner/attempts.jsonl").read_text().strip())

    def test_importing_the_same_delta_twice_logs_it_once(self):
        example = (COACH.parent.parent / "assets" / "delta-example.json").read_text()
        delta = self.tmp / "web.json"
        delta.write_text(example)
        self.assertIn("Imported web.json", self.run_cli("import", str(delta)).stdout)
        self.assertIn("already imported", self.run_cli("import", str(delta)).stdout)
        self.assertEqual(len(self.attempts()), 2)

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
        item = self.next_item("--pattern", "arrays-hashing")
        self.assertEqual((item["kind"], item["pattern"], item["problem"]), ("new", "arrays-hashing", None))
        self.assertIn("NeetCode", self.run_cli("next", "--pattern", "arrays-hashing").stdout)

    def test_next_keeps_a_block_of_three_then_starts_the_next_pattern(self):
        item = self.next_item()
        self.assertEqual((item["pattern"], item["problem"], item["first"], item.get("block")),
                         ("arrays-hashing", "two-sum", True, True))
        for slug in ("two-sum", "group-anagrams", "longest-consecutive-sequence"):
            self.attempt(slug, "2026-11-01", pattern="arrays-hashing")
        item = self.next_item()  # block done; Two Pointers is also planned for week 1
        self.assertEqual((item["kind"], item["pattern"], item["problem"], item["first"], item.get("block")),
                         ("new", "two-pointers", "two-sum-ii-input-array-is-sorted", True, True))

    def test_next_mixes_started_patterns_until_the_next_week(self):
        for slug in ("two-sum", "group-anagrams", "longest-consecutive-sequence"):
            self.attempt(slug, "2026-11-06", pattern="arrays-hashing")
        for slug in ("two-sum-ii-input-array-is-sorted", "3sum", "container-with-most-water"):
            self.attempt(slug, "2026-11-07", pattern="two-pointers")
        item = self.next_item(today="2026-11-07")  # still week 1: the least recently practised pattern
        self.assertEqual((item["kind"], item["pattern"], item["first"], item.get("block")),
                         ("new", "arrays-hashing", False, False))
        step = self.journey()["next_steps"][0]
        self.assertIn("pattern unlabeled", step)
        self.assertNotIn("Arrays", step)
        item = self.next_item(today="2026-11-08")  # week 2: Sliding Window starts its own block
        self.assertEqual((item["kind"], item["pattern"], item["first"], item.get("block")),
                         ("new", "sliding-window", True, True))

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

    def test_due_json(self):
        self.attempt("two-sum", "2026-11-01", pattern="arrays-hashing", hints=3)  # not unaided: due the next day
        d = json.loads(self.run_cli("due", "--json", today="2026-11-02").stdout)
        self.assertEqual([r["problem"] for r in d["resolves"]], ["two-sum"])
        self.assertEqual((d["cards"], d["drafts"], d["inbox"]), ([], 0, []))

    # ------------------------------------------------------------------ live solve
    def live(self):
        path = self.root / "sessions" / "current.json"
        return json.loads(path.read_text()) if path.exists() else None

    def attempts(self):
        text = (self.root / "learner" / "attempts.jsonl").read_text()
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_writers_wait_for_the_notebook_lock_and_readers_do_not(self):
        script = ("import sys; sys.path.insert(0, sys.argv[1]); import coach; "
                  "print('ready', flush=True); coach.main(sys.argv[2:])")
        writers = [("log", "attempt", "--problem", "two-sum", "--pattern", "arrays-hashing", "--outcome", "solved"),
                   ("card", "add", "--concept", "arrays-hashing", "--front", "f", "--back", "b"),
                   ("card", "add", "--concept", "arrays-hashing", "--front", "g", "--back", "c")]
        children = []
        with notebook_lock(self.root):
            self.run_cli("solve", "show")  # a reader doesn't wait
            for args in writers:
                proc = subprocess.Popen([sys.executable, "-c", script, str(COACH.parent), "--root", str(self.root), *args],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
                children.append(proc)
                self.assertEqual(proc.stdout.readline().strip(), "ready")
                self.assertIsNone(proc.poll())
        for proc in children:
            _, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, err)
        self.assertEqual(len(self.attempts()), 1)
        cards = json.loads((self.root / "learner/cards.json").read_text())
        self.assertEqual(sorted(c["id"] for c in cards), ["c0001", "c0002"])

    def test_a_writer_gives_up_when_the_lock_is_held_too_long(self):
        script = ("import sys; sys.path.insert(0, sys.argv[1]); from pathlib import Path; import coach\n"
                  "with coach.notebook_lock(Path(sys.argv[2]), timeout=0.05): pass\n")
        with notebook_lock(self.root):
            result = subprocess.run([sys.executable, "-c", script, str(COACH.parent), str(self.root)],
                                    capture_output=True, text=True, timeout=5)
        self.assertIn("the notebook is busy", result.stderr)

    def test_solve_start_creates_no_file_and_uses_the_problem_list(self):
        out = self.run_cli("solve", "start", "--problem", "two-sum", "--confidence", "3", now="10:00").stdout
        self.assertIn("On LeetCode: https://leetcode.com/problems/two-sum/", out)
        live = self.live()
        self.assertEqual((live["pattern"], live["difficulty"], live["block_minutes"], live["stage"], live["rung"]),
                         ("arrays-hashing", "easy", 15, 1, 0))
        self.assertNotIn("file", live)
        self.assertFalse((self.root / "problems" / "two-sum").exists())
        self.run_cli("solve", "end", "--discard")
        self.run_cli("solve", "start", "--problem", "product-of-array-except-self")  # listed, not canonical
        self.assertEqual((self.live()["pattern"], self.live()["difficulty"]), ("arrays-hashing", "medium"))
        again = self.run_cli("solve", "start", "--problem", "valid-anagram", ok=False)
        self.assertIn("already live", again.stderr)

    def test_solve_needs_a_pattern_for_unknown_problems(self):
        proc = self.run_cli("solve", "start", "--problem", "my-own-puzzle", ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--pattern", proc.stderr)

    def test_solve_refuses_a_problem_with_no_letters_or_digits(self):
        proc = self.run_cli("solve", "start", "--problem", "!!!", "--pattern", "arrays-hashing", ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no letters or digits", proc.stderr)
        self.assertIsNone(self.live())

    def test_solve_end_logs_one_attempt_from_blocks_and_rung(self):
        self.run_cli("solve", "start", "--problem", "two-sum", "--confidence", "3", now="10:00")
        self.run_cli("solve", "stage", "3", now="10:05")
        self.run_cli("solve", "hint", now="10:10")
        self.run_cli("solve", "hint", "--rung", "3", now="10:12")
        self.run_cli("solve", "hint", "--rung", "2", now="10:13")  # the highest rung stays
        self.assertEqual((self.live()["stage"], self.live()["rung"]), (3, 3))
        self.run_cli("solve", "break", now="10:20")  # 20 minutes, counted as the 15-minute block it is
        self.run_cli("solve", "block", now="10:30")
        self.run_cli("solve", "end", "--outcome", "solved", "--note", "complement lookup", now="10:42")
        self.assertIsNone(self.live())
        [a] = self.attempts()
        self.assertEqual((a["problem"], a["pattern"], a["difficulty"]), ("two-sum", "arrays-hashing", "easy"))
        self.assertEqual((a["minutes"], a["hints"], a["confidence"], a["outcome"]), (27, 3, 3, "solved"))

    def view(self, now):
        return json.loads(self.run_cli("solve", "show", "--json", now=now).stdout)

    def test_an_open_block_counts_at_most_its_length(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        self.assertEqual(self.view("10:04")["block"]["elapsed"], 4)
        v = self.view("22:00")  # left open overnight
        self.assertEqual((v["block"]["number"], v["block"]["elapsed"], v["minutes"]), (1, 15, 15))
        self.run_cli("solve", "block", now="22:01")
        self.assertEqual(self.view("22:06")["minutes"], 20)

    def test_idle_time_an_older_solve_paused_out_still_counts_as_paused(self):
        self.run_cli("solve", "start", "--problem", "valid-anagram", "--difficulty", "medium", now="10:00")
        live = self.live()
        live["blocks"] = [{"start": "2026-11-01T10:00:00+05:30", "end": "2026-11-01T10:30:00+05:30", "paused": 600}]
        live["last_active"] = "2026-11-01T10:30:00+05:30"
        (self.root / "sessions/current.json").write_text(json.dumps(live))
        self.assertEqual(self.view("11:00")["minutes"], 20)

    def test_solve_note_is_kept_and_written_to_problem_notes(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        first = self.live()["session_id"]
        self.run_cli("solve", "note", "--stage", "1", "--text", "first draft", now="10:01")
        self.run_cli("solve", "note", "--stage", "1", "--text=- return i != j with nums[i] + nums[j] == target", now="10:02")
        self.run_cli("solve", "note", "--stage", "2", "--text", "seen maps value -> index\nfor every j < i", now="10:03")
        shown = self.view("10:04")
        self.assertEqual(shown["notes"], {"1": "- return i != j with nums[i] + nums[j] == target",
                                          "2": "seen maps value -> index\nfor every j < i"})
        self.run_cli("solve", "end", "--outcome", "solved", now="10:10")
        self.run_cli("log", "attempt", "--problem", "two-sum", "--pattern", "arrays-hashing", "--outcome", "solved",
                     "--note", "complement lookup")  # a lesson line, appended under ## Lessons
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:20")
        second = self.live()["session_id"]
        self.run_cli("solve", "note", "--stage", "3", "--text", "all pairs, O(n^2)", now="10:21")
        self.run_cli("solve", "end", "--outcome", "solved", now="10:30")
        text = (self.root / "problems" / "two-sum" / "notes.md").read_text()
        self.assertIn(f"## Stage notes\n\n### 2026-11-01 ({first})\n\n- **1. Understand:** - return i != j", text)
        self.assertIn(f"- **2. Find an approach:** seen maps value -> index\n  for every j < i\n\n"
                      f"### 2026-11-01 ({second})\n\n- **3. Build it:** all pairs, O(n^2)\n\n## Lessons\n", text)
        self.assertNotIn("first draft", text)
        self.assertEqual(text.count("## Stage notes"), 1)
        self.assertGreater(text.index("complement lookup"), text.index("## Lessons\n"))

    def test_solve_has_four_stages(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        self.assertIn("stage 1/4 Understand", self.run_cli("solve", "show", now="10:01").stdout)
        self.run_cli("solve", "stage", "4", now="10:02")
        self.assertNotEqual(self.run_cli("solve", "stage", "5", ok=False).returncode, 0)
        self.assertNotEqual(self.run_cli("solve", "note", "--stage", "5", "--text", "x", ok=False).returncode, 0)

    def test_solve_end_records_its_session_and_a_retry_logs_once(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        live_path = self.root / "sessions/current.json"
        self.run_cli("solve", "note", "--stage", "1", "--text", "pairs", now="10:01")
        saved, session = live_path.read_bytes(), self.live()["session_id"]
        first = json.loads(self.run_cli("solve", "end", "--outcome", "solved", "--json", now="10:10").stdout)
        self.assertEqual((first["problem"], first["outcome"], first["id"]), ("two-sum", "solved", "a0001"))
        self.assertEqual(self.attempts()[0]["session"], session)
        live_path.write_bytes(saved)  # as if it stopped before removing the live solve
        again = json.loads(self.run_cli("solve", "end", "--outcome", "solved", "--json", now="10:11").stdout)
        self.assertEqual(again, first)
        self.assertIsNone(self.live())
        self.assertEqual(len(self.attempts()), 1)
        notes = (self.root / "problems/two-sum/notes.md").read_text()
        self.assertEqual(notes.count("- **1. Understand:** pairs"), 1)

    def test_solve_blank_note_clears_the_stage_and_writes_nothing(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        self.run_cli("solve", "note", "--stage", "1", "--text", "a draft", now="10:01")
        self.run_cli("solve", "note", "--stage", "3", "--text", "n^2 pairs", now="10:01")
        self.run_cli("solve", "note", "--stage", "1", "--text=", now="10:02")
        self.assertEqual(self.live()["notes"], {"3": "n^2 pairs"})
        self.run_cli("solve", "note", "--stage", "3", "--text", " \n ", now="10:03")
        self.run_cli("solve", "end", "--outcome", "solved", now="10:10")
        self.assertNotIn("## Stage notes", (self.root / "problems" / "two-sum" / "notes.md").read_text())

    def test_stage_notes_split_only_at_the_lessons_heading(self):
        sessions = []
        for note, at in [("line a\n## Lessons\nline b", "10:00"), ("all pairs", "10:20")]:
            self.run_cli("solve", "start", "--problem", "two-sum", now=at)
            sessions.append(self.live()["session_id"])
            self.run_cli("solve", "note", "--stage", "2", "--text", note, now=at)
            self.run_cli("solve", "end", "--outcome", "solved", now=at)
        text = (self.root / "problems" / "two-sum" / "notes.md").read_text()
        self.assertEqual(text.count("\n## Lessons\n"), 1)
        lessons = text.index("\n## Lessons\n")
        for session in sessions:
            self.assertLess(text.index(f"### 2026-11-01 ({session})"), lessons)

    def test_solve_unlabeled_keeps_the_pattern_out_of_view(self):
        self.run_cli("solve", "start", "--problem", "valid-anagram", "--difficulty", "medium", "--unlabeled", now="10:00")
        shown = self.run_cli("solve", "show", now="10:07").stdout
        status = [line for line in self.run_cli("status", "--brief", now="10:07").stdout.splitlines()
                  if line.startswith("Live solve")][0]
        for out in (shown, status):
            self.assertNotIn("Arrays & Hashing", out)
            self.assertNotIn("arrays-hashing", out)
        self.assertIn("Live solve: valid-anagram", status)
        self.assertIn("block 1: 7 of 25 min", status)
        self.assertEqual(self.view("10:08")["pattern"], "arrays-hashing")

    def test_discard_logs_nothing(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        self.assertIn("nothing logged", self.run_cli("solve", "end", "--discard", now="10:01").stdout)
        self.assertEqual(self.attempts(), [])
        self.assertIn("No live solve", self.run_cli("solve", "show").stdout)
        self.assertNotEqual(self.run_cli("solve", "end", "--discard", ok=False).returncode, 0)

    def test_map_json_carries_due_and_the_live_solve(self):
        view = json.loads(self.run_cli("map", "--json").stdout)
        self.assertIsNone(view["live"])
        self.assertEqual(set(view["due"]), {"resolves", "cards", "drafts", "inbox"})
        self.run_cli("solve", "start", "--problem", "two-sum", now="10:00")
        live = json.loads(self.run_cli("map", "--json", now="10:05").stdout)["live"]
        self.assertEqual((live["problem"], live["stage_name"], live["block"]["elapsed"]), ("two-sum", "Understand", 5))

    def test_write_json_replaces_the_file_whole(self):
        """The page polls `solve show --json` while the chat and the app write current.json."""
        spec = importlib.util.spec_from_file_location("coach", COACH)
        coach = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coach)
        path = self.tmp / "sessions" / "current.json"
        coach.write_json(path, {"stage": 1})
        with path.open(encoding="utf-8") as reader:  # opened before the next write: it never sees a cut-off file
            coach.write_json(path, {"note": "seen → index"})
            self.assertEqual(reader.read(), '{\n  "stage": 1\n}\n')
        self.assertEqual(path.read_bytes(), '{\n  "note": "seen → index"\n}\n'.encode("utf-8"))
        plain = path.with_name("plain.json")
        plain.write_text("{}\n")  # the permissions the old in-place write gave
        self.assertEqual(path.stat().st_mode, plain.stat().st_mode)
        plain.unlink()
        with unittest.mock.patch.object(coach.os, "replace", side_effect=OSError("disk full")):
            self.assertRaises(OSError, coach.write_json, path, {"stage": 2})
        self.assertEqual(os.listdir(path.parent), ["current.json"])  # no temp files left behind
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"note": "seen → index"})

    def test_write_json_writes_through_a_symlink_and_keeps_the_mode(self):
        """e.g. .claude/settings.json linked from a dotfiles repo."""
        spec = importlib.util.spec_from_file_location("coach", COACH)
        coach = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coach)
        target = self.tmp / "dotfiles" / "settings.json"
        target.parent.mkdir()
        target.write_text("{}\n")
        target.chmod(0o600)
        link = self.tmp / "settings.json"
        link.symlink_to(target)
        coach.write_json(link, {"hooks": 1})
        self.assertTrue(link.is_symlink())
        self.assertEqual(json.loads(target.read_text()), {"hooks": 1})
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

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
        self.assertEqual(list(settings["hooks"]), ["SessionStart"])
        again = subprocess.run([sys.executable, str(coach), "install"], capture_output=True, text=True, env=self.env, cwd=ws)
        self.assertIn("already linked", again.stdout)
        self.assertIn("already present", again.stdout)


if __name__ == "__main__":
    unittest.main()
