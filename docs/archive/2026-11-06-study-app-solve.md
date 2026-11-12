> **Archived.** Built in 0.5.0; the Solve tab was removed in 0.9.0. Kept for history: paths inside are as they were when it was written.

# Study App v1 (Solve tab) Implementation Plan

> As built (2026-11-06): code review changed parts of Tasks 2–7; the code and tests on the branch are the reference. See docs/CHANGELOG.md, 0.5.0.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A local web app where Himanshu works a whole solve in one window: a stage panel for the 8-stage protocol, a code editor without autocomplete, and a test runner, while the coach chat (Claude Code or Codex) stays beside it.

**Architecture:** `app/server.py` is a standard-library HTTP server on 127.0.0.1. It never writes the notebook's JSON records itself: every state change is a `coach.py` subprocess call. It reads and writes only the live solve's attempt file (through `app/attempt_file.py`) and `problems/<slug>/problem.md`, and runs the attempt file in a child process through `app/runner.py`. The page (`app/static/`) is plain HTML, CSS and JavaScript with CodeMirror 5 from cdnjs.

**Tech Stack:** Python 3.10+ standard library (`http.server`, `ast`, `subprocess`, `runpy`, `unittest`), vanilla JavaScript, CodeMirror 5.65.16.

**Spec:** `docs/superpowers/specs/2026-11-06-study-app-solve-design.md`. Three decisions this plan adds to it:
1. **CodeMirror 5, not 6.** Version 6 ships as ES modules that need a bundler or careful CDN deduplication. Version 5 is one script tag from cdnjs, has a Python mode and no autocomplete by default.
2. **The server rejects requests without an `X-DSA-Coach: 1` header, and requests whose `Host` isn't `127.0.0.1` or `localhost`.** Without this, any web page he visits could POST code to `/api/attempt` and run it with `/api/run`. Browsers can't add a custom header to a cross-site request without a CORS preflight, which the server never approves. The Host check stops DNS-rebinding.
3. **The examples table takes Python literals only** (lists, numbers, strings, `None`). Problems whose inputs are `ListNode` or `TreeNode` need converters, which are out of scope for v1.

**Working rules for whoever executes this:**
- Work on a branch: `git checkout -b study-app-solve` before Task 1.
- Run tests with `python3 -m unittest discover -s tests -v` from the repo root (`/Users/chetna/Desktop/dsa-coach`).
- Don't touch anything under `notebook/` except through `coach.py`. The tests use temporary notebooks.
- A PreToolUse hook blocks edits to `notebook/problems/<live problem>/*.py` while a solve is live. No step here edits those files.

---

### Task 1: `coach.py due --json`

The server's `/api/state` needs what's due as JSON.

**Files:**
- Modify: `skills/dsa-coach/scripts/coach.py` (`cmd_due`, around line 1073; the `due` parser, around line 1713)
- Test: `tests/test_coach.py`

**Step 1: Write the failing test.** Add this method to `CoachTest` in `tests/test_coach.py`, just above the `# ---- live solve` section:

```python
    def test_due_json(self):
        self.attempt("two-sum", "2026-11-01", pattern="arrays-hashing", hints=3)  # not unaided: due the next day
        d = json.loads(self.run_cli("due", "--json", today="2026-11-02").stdout)
        self.assertEqual([r["problem"] for r in d["resolves"]], ["two-sum"])
        self.assertEqual((d["cards"], d["drafts"], d["inbox"]), ([], 0, []))
```

**Step 2: Run it and see it fail.**

Run: `python3 -m unittest tests.test_coach.CoachTest.test_due_json -v`
Expected: FAIL. `coach due --json failed` with `unrecognized arguments: --json`.

**Step 3: Implement.** In `build_parser`, change the `due` parser to:

```python
    s = sub.add_parser("due", help="list due re-solves and cards")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    s.set_defaults(func=cmd_due)
```

In `cmd_due`, right after `d = j["due"]`, add:

```python
    if args.json:
        print(json.dumps(d, indent=2, ensure_ascii=False))
        return
```

**Step 4: Run it and see it pass.**

Run: `python3 -m unittest tests.test_coach.CoachTest.test_due_json -v`
Expected: PASS.

**Step 5: Commit.**

```bash
git add skills/dsa-coach/scripts/coach.py tests/test_coach.py
git commit -m "coach.py: due --json"
```

---

### Task 2: `coach.py solve note`, and stage notes in the problem's notes

**Files:**
- Modify: `skills/dsa-coach/scripts/coach.py` (`cmd_solve`, `solve_end`, the `solve` parsers)
- Test: `tests/test_coach.py`

**Step 1: Write the failing test.** Add to `CoachTest`, after `test_solve_end_logs_one_attempt_from_blocks_and_rung`:

```python
    def test_solve_note_is_kept_and_written_to_problem_notes(self):
        self.run_cli("solve", "start", "--problem", "two-sum", "--difficulty", "easy", now="10:00")
        self.run_cli("solve", "note", "--stage", "1", "--text", "first draft", now="10:01")
        self.run_cli("solve", "note", "--stage", "1", "--text=- return i != j with nums[i] + nums[j] == target", now="10:02")
        self.run_cli("solve", "note", "--stage", "6", "--text", "seen maps value -> index\nfor every j < i", now="10:03")
        shown = json.loads(self.run_cli("solve", "show", "--json", now="10:04").stdout)
        self.assertEqual(shown["notes"], {"1": "- return i != j with nums[i] + nums[j] == target",
                                          "6": "seen maps value -> index\nfor every j < i"})
        self.run_cli("solve", "end", "--outcome", "solved", now="10:10")
        text = (self.root / "problems" / "two-sum" / "notes.md").read_text()
        self.assertIn("### Stage notes, 2026-11-01 (problems/two-sum/2026-11-01.py)", text)
        self.assertIn("- **1. Unknown, data, condition:** - return i != j", text)
        self.assertIn("- **6. Plan card:** seen maps value -> index\n  for every j < i", text)
        self.assertNotIn("first draft", text)
```

The `--text=-...` form matters: the server passes notes that way so a note starting with `-` isn't read as an option.

**Step 2: Run it and see it fail.**

Run: `python3 -m unittest tests.test_coach.CoachTest.test_solve_note_is_kept_and_written_to_problem_notes -v`
Expected: FAIL. `invalid choice: 'note'`.

**Step 3: Implement.**

In `build_parser`, after the `hint` parser lines, add:

```python
    s = solve.add_parser("note", help="save the learner's note for a stage (replaces that stage's note)")
    s.add_argument("--stage", type=int, required=True, choices=range(1, 9))
    s.add_argument("--text", required=True)
```

In `cmd_solve`, extend the `if action == "stage": ... elif action == "hint": ...` chain with:

```python
    elif action == "note":
        live.setdefault("notes", {})[str(args.stage)] = args.text
```

In `solve_end`, after the `log_and_report(...)` call and before `(root / LIVE).unlink()`, add:

```python
    notes = live.get("notes") or {}
    if notes:
        lines = [f"\n### Stage notes, {today().isoformat()} ({live['file']})\n\n"]
        for n in sorted(notes, key=int):
            text = notes[n].strip().replace("\n", "\n  ")
            lines.append(f"- **{n}. {STAGES[int(n) - 1][0]}:** {text}\n")
        with (root / "problems" / live["problem"] / "notes.md").open("a", encoding="utf-8") as fh:
            fh.writelines(lines)
```

`log_and_report` has already created `notes.md` through `ensure_problem_notes`, so the file exists.

**Step 4: Run it and see it pass, then the whole file.**

Run: `python3 -m unittest tests.test_coach -v`
Expected: all PASS.

**Step 5: Commit.**

```bash
git add skills/dsa-coach/scripts/coach.py tests/test_coach.py
git commit -m "coach.py: solve note, copied into the problem's notes at solve end"
```

---

### Task 3: The attempt-file template becomes LeetCode-shaped

**Files:**
- Modify: `skills/dsa-coach/assets/templates/solve.py` (replace the whole file)
- Test: `tests/test_coach.py`

**Step 1: Write the failing test.** Add to `CoachTest`, after `test_solve_start_scaffolds_the_attempt_file`:

```python
    def test_solve_template_runs_its_examples(self):
        self.run_cli("solve", "start", "--problem", "two-sum", "--difficulty", "easy", now="10:00")
        path = self.root / self.live()["file"]
        text = path.read_text()
        self.assertIn("class Solution:", text)
        self.assertIn("    Hand trace:", text)
        method = ("    def twoSum(self, nums, target):\n"
                  "        seen = {}\n"
                  "        for i, x in enumerate(nums):\n"
                  "            if target - x in seen:\n"
                  "                return [seen[target - x], i]\n"
                  "            seen[x] = i\n")
        text = text.replace("    pass\n", method, 1)
        text = text.replace("EXAMPLES = [\n]", "EXAMPLES = [\n"
                            "    (([2, 7, 11, 15], 9), [0, 1]),\n"
                            "    (([3, 3], 6), [0, 1]),  # edge\n"
                            "    (([1, 2], 3), [1, 0]),\n"
                            "]")
        path.write_text(text)
        out = subprocess.run([sys.executable, str(path)], capture_output=True, text=True).stdout.splitlines()
        self.assertEqual([line[:4] for line in out], ["ok  ", "ok  ", "FAIL"])
```

**Step 2: Run it and see it fail.**

Run: `python3 -m unittest tests.test_coach.CoachTest.test_solve_template_runs_its_examples -v`
Expected: FAIL on `assertIn("class Solution:", ...)`.

**Step 3: Replace `skills/dsa-coach/assets/templates/solve.py` with:**

```python
"""{problem}

{url}
Started {date}.{pattern_line}

Plan card (stage 6):
    State:
    Invariant:
    Relies on:
    Breaks if:
    Termination:
    Complexity:
    Hand trace:
"""


class Solution:
    # Write the method LeetCode gives you here, e.g. def search(self, nums, target):
    # Subgoal comments first (stage 7), then the code under each one.
    pass


# Stage 1: your predicted examples, one per line: ((args, ...), expected). Mark edge cases with "# edge".
EXAMPLES = [
]


if __name__ == "__main__":
    name = next((m for m in vars(Solution) if not m.startswith("_")), None)
    if name is None:
        print("Write the method inside class Solution first.")
    else:
        for args, expected in EXAMPLES:
            got = getattr(Solution(), name)(*args)
            print("ok  " if got == expected else "FAIL", args, "->", got, "expected", expected)
```

`coach.py` fills it with `str.format`, so the template must contain no `{` or `}` other than the four placeholders. The one above has none.

**Step 4: Run the whole coach test file.**

Run: `python3 -m unittest tests.test_coach -v`
Expected: all PASS, including `test_solve_start_scaffolds_the_attempt_file`, which still finds the URL, the pattern name and `Invariant:`.

**Step 5: Commit.**

```bash
git add skills/dsa-coach/assets/templates/solve.py tests/test_coach.py
git commit -m "Attempt template: class Solution, EXAMPLES and a hand-trace field"
```

---

### Task 4: `app/attempt_file.py`: read and write the plan card and EXAMPLES

Pure functions on the file's text. Both have to work while the code under `class Solution` is half-written, so neither parses the whole file.

**Files:**
- Create: `app/attempt_file.py`
- Test: `tests/test_attempt_file.py`

**Step 1: Write the failing tests.** Create `tests/test_attempt_file.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run them and see them fail.**

Run: `python3 -m unittest tests.test_attempt_file -v`
Expected: ERROR. `ModuleNotFoundError: No module named 'attempt_file'`.

**Step 3: Create `app/attempt_file.py`:**

```python
"""The two parts of an attempt file that the Solve tab edits: the plan card in the docstring, and EXAMPLES.

Both work on text and never parse the whole file, so they keep working while the code is half-written.
"""
import ast
import re

PLAN_FIELDS = ["State", "Invariant", "Relies on", "Breaks if", "Termination", "Complexity", "Hand trace"]
FIELD = re.compile(r"^    (" + "|".join(re.escape(f) for f in PLAN_FIELDS) + r"):(.*)$")
MORE = " " * 8  # a continuation line of a multi-line field


def _docstring_end(lines: list) -> int | None:
    """Index of the line that closes the module docstring, if the file starts with one."""
    if not lines or not lines[0].startswith('"""'):
        return None
    return next((i for i in range(1, len(lines)) if '"""' in lines[i]), None)


def read_plan_card(text: str) -> dict:
    lines = text.split("\n")
    end = _docstring_end(lines) or 0
    card, field = {}, None
    for line in lines[1:end]:
        m = FIELD.match(line)
        if m:
            field = m.group(1)
            card[field] = m.group(2).strip()
        elif field and line.startswith(MORE):
            card[field] += "\n" + line[len(MORE):]
        else:
            field = None
    return card


def write_plan_card(text: str, card: dict) -> str:
    """Replace the fields named in card; leave every other line as it is."""
    lines = text.split("\n")
    end = _docstring_end(lines)
    if end is None:
        raise ValueError("the attempt file has no docstring with a plan card")
    out, i = lines[:1], 1
    while i < end:
        line = lines[i]
        i += 1
        m = FIELD.match(line)
        if not m or m.group(1) not in card:
            out.append(line)
            continue
        while i < end and lines[i].startswith(MORE):  # drop the old value's continuation lines
            i += 1
        first, *rest = str(card[m.group(1)]).strip().split("\n")
        out.append(f"    {m.group(1)}: {first}".rstrip())
        out.extend(MORE + r for r in rest)
    return "\n".join(out + lines[end:])


def _examples_span(lines: list) -> tuple | None:
    """(first, last) line indexes of the EXAMPLES = [ ... ] block."""
    for i, line in enumerate(lines):
        if line.startswith("EXAMPLES = ["):
            if line.rstrip().endswith("]"):
                return i, i
            for j in range(i + 1, len(lines)):
                if lines[j].rstrip() == "]":
                    return i, j
            return None
    return None


def read_examples(text: str) -> list:
    """Rows as {"args": source text, "expected": source text, "edge": bool}."""
    lines = text.split("\n")
    span = _examples_span(lines)
    if span is None:
        return []
    block_lines = lines[span[0]:span[1] + 1]
    block = "\n".join(block_lines)
    try:
        node = ast.parse(block).body[0].value
    except SyntaxError as e:
        raise ValueError(f"EXAMPLES has a syntax error: {e.msg}") from None
    rows = []
    for elt in node.elts if isinstance(node, ast.List) else []:
        if not (isinstance(elt, ast.Tuple) and len(elt.elts) == 2 and isinstance(elt.elts[0], ast.Tuple)):
            continue
        args, expected = elt.elts
        rows.append({"args": ", ".join(ast.get_source_segment(block, a) for a in args.elts),
                     "expected": ast.get_source_segment(block, expected),
                     "edge": block_lines[elt.end_lineno - 1].rstrip().endswith("# edge")})
    return rows


def format_row(row: dict) -> str:
    args, expected = str(row.get("args", "")).strip(), str(row.get("expected", "")).strip()
    for source, what in ((f"({args},)", "the inputs"), (expected, "the expected output")):
        try:
            ast.literal_eval(source)
        except (ValueError, SyntaxError):
            raise ValueError(f"{what} must be Python values such as [1, 2], 3 or 'abc': got {source!r}") from None
    return f"    (({args},), {expected}),{'  # edge' if row.get('edge') else ''}"


def write_examples(text: str, rows: list) -> str:
    lines = text.split("\n")
    span = _examples_span(lines)
    if span is None:
        raise ValueError("the attempt file has no EXAMPLES list")
    lines[span[0]:span[1] + 1] = ["EXAMPLES = ["] + [format_row(r) for r in rows] + ["]"]
    return "\n".join(lines)
```

**Step 4: Run them and see them pass.**

Run: `python3 -m unittest tests.test_attempt_file -v`
Expected: all PASS.

**Step 5: Commit.**

```bash
git add app/attempt_file.py tests/test_attempt_file.py
git commit -m "app: read and write the plan card and EXAMPLES in an attempt file"
```

---

### Task 5: `app/runner.py`: run the examples in a sealed child process

**Files:**
- Create: `app/runner.py`
- Test: `tests/test_runner.py`

**Step 1: Write the failing tests.** Create `tests/test_runner.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run them and see them fail.**

Run: `python3 -m unittest tests.test_runner -v`
Expected: ERROR. `ModuleNotFoundError: No module named 'runner'`.

**Step 3: Create `app/runner.py`:**

```python
"""Run an attempt file's EXAMPLES against its class Solution, in a child process with a time limit.

    python3 app/runner.py FILE     prints the result as JSON

The child imports the file under a name other than __main__, so the file's own test loop doesn't run.
"""
import contextlib
import copy
import io
import json
import runpy
import subprocess
import sys
import traceback
from pathlib import Path

TIMEOUT_S = 5


def run(path, timeout: float = TIMEOUT_S) -> dict:
    """{"ok", "method", "rows": [{"ok", "args", "expected", "got", "stdout", "error"}], "error"}"""
    try:
        proc = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--child", str(path)],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "method": None, "rows": [],
                "error": f"timed out after {timeout:g} s: an infinite loop, or too slow for these inputs"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "method": None, "rows": [],
                "error": (proc.stderr or proc.stdout or "the runner stopped without a result").strip()[-3000:]}


def _trace() -> str:
    return traceback.format_exc()[-3000:]


def run_row(solution: type, name: str, row) -> dict:
    try:
        args, expected = row
        args = tuple(args)
    except (TypeError, ValueError):
        return {"ok": False, "args": repr(row), "expected": "", "got": "", "stdout": "",
                "error": "Each example must be ((args, ...), expected)."}
    result = {"ok": False, "args": ", ".join(map(repr, args)), "expected": repr(expected), "got": "",
              "stdout": "", "error": None}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            got = getattr(solution(), name)(*copy.deepcopy(args))
        result.update(ok=bool(got == expected), got=repr(got))
    except Exception:
        result["error"] = _trace()
    result["stdout"] = buf.getvalue()[-2000:]
    return result


def child(path: str) -> dict:
    out = {"ok": False, "method": None, "rows": [], "error": None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns = runpy.run_path(path, run_name="attempt")
    except BaseException:
        out["error"] = "The file didn't load:\n" + _trace()
        return out
    solution = ns.get("Solution")
    if not isinstance(solution, type):
        out["error"] = "There's no class Solution in the file."
        return out
    out["method"] = next((m for m, v in vars(solution).items() if not m.startswith("_") and callable(v)), None)
    if out["method"] is None:
        out["error"] = "Write the method inside class Solution first."
        return out
    examples = ns.get("EXAMPLES")
    if not examples:
        out["error"] = "No examples yet. Add them in stage 1."
        return out
    out["rows"] = [run_row(solution, out["method"], row) for row in examples]
    out["ok"] = all(r["ok"] for r in out["rows"])
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        print(json.dumps(child(sys.argv[2])))
    elif len(sys.argv) == 2:
        print(json.dumps(run(sys.argv[1]), indent=2))
    else:
        sys.exit("usage: python3 app/runner.py FILE")
```

**Step 4: Run them and see them pass.**

Run: `python3 -m unittest tests.test_runner -v`
Expected: all PASS. The timeout test takes about a second.

**Step 5: Commit.**

```bash
git add app/runner.py tests/test_runner.py
git commit -m "app: runner for an attempt file's examples, with a time limit"
```

---

### Task 6: `app/server.py`: the go-between

**Files:**
- Create: `app/server.py`
- Create: `app/static/.gitkeep` (empty, so `STATIC` exists until Task 7)
- Test: `tests/test_server.py`

**Step 1: Write the failing tests.** Create `tests/test_server.py`:

```python
"""Tests for app/server.py. Run: python3 -m unittest discover -s tests -v"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402

COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"
METHOD = ("    def search(self, nums, target):\n"
          "        lo, hi = 0, len(nums) - 1\n"
          "        while lo <= hi:\n"
          "            mid = (lo + hi) // 2\n"
          "            if nums[mid] == target:\n"
          "                return mid\n"
          "            if nums[mid] > target:\n"
          "                hi = mid - 1\n"
          "            else:\n"
          "                lo = mid + 1\n"
          "        return -1\n")


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dsa-server-test-"))
        self.root = self.tmp / "notebook"
        self.env = dict(os.environ, DSA_TODAY="2026-11-06", HOME=str(self.tmp / "home"))
        self.env.pop("DSA_NOTEBOOK", None)
        subprocess.run([sys.executable, str(COACH), "--root", str(self.root), "init", "--name", "Tester",
                        "--start-date", "2026-11-01", "--days", "90"], check=True, capture_output=True, env=self.env)
        self.server = server.make_server(self.root, port=0, env=self.env)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, method, path, body=None, coach_header=True, host=None):
        headers = {"Content-Type": "application/json"}
        if coach_header:
            headers["X-DSA-Coach"] = "1"
        if host:
            headers["Host"] = host
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def start(self):
        return self.call("POST", "/api/solve/start", {"problem": "binary-search", "confidence": 3, "difficulty": "easy"})

    def test_binds_to_localhost_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_refuses_requests_without_the_header_or_from_another_host(self):
        self.assertEqual(self.call("GET", "/api/state", coach_header=False)[0], 403)
        self.assertEqual(self.call("GET", "/api/state", host="evil.example:80")[0], 403)

    def test_state_without_a_live_solve(self):
        status, state = self.call("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertIsNone(state["live"])
        self.assertEqual(state["next"]["kind"], "new")
        self.assertEqual(state["due"]["resolves"], [])

    def test_start_then_state_and_attempt(self):
        self.assertEqual(self.start()[0], 200)
        state = self.call("GET", "/api/state")[1]
        self.assertEqual((state["live"]["problem"], state["live"]["stage"], state["live"]["confidence"]),
                         ("binary-search", 1, 3))
        self.assertIsInstance(state["attempt_mtime"], int)
        attempt = self.call("GET", "/api/attempt")[1]
        self.assertIn("class Solution:", attempt["text"])
        self.assertEqual(attempt["plan_card"]["Invariant"], "")
        self.assertEqual(attempt["examples"], [])
        self.assertEqual(attempt["file"], "problems/binary-search/2026-11-06.py")

    def test_a_coach_error_comes_back_as_4xx_with_its_message(self):
        self.start()
        status, body = self.start()
        self.assertEqual(status, 409)
        self.assertIn("already live", body["error"])
        self.call("POST", "/api/solve/end", {"outcome": "solved"})
        status, body = self.call("POST", "/api/solve/start", {"problem": "my-own-puzzle", "confidence": 2})
        self.assertEqual(status, 400)  # coach.py asks for --pattern; only "already live" is a 409
        self.assertIn("which pattern", body["error"])
        self.assertEqual(self.call("POST", "/api/solve/stage", {})[0], 400)

    def test_no_live_solve_is_a_409(self):
        self.assertEqual(self.call("GET", "/api/attempt")[0], 409)

    def test_parts_run_and_the_mtime_check(self):
        self.start()
        attempt = self.call("GET", "/api/attempt")[1]
        stale = attempt["mtime"]
        rows = [{"args": "[-1, 0, 3, 5, 9, 12], 9", "expected": "4", "edge": False},
                {"args": "[5], 5", "expected": "0", "edge": True}]
        status, attempt = self.call("PUT", "/api/attempt/parts",
                                    {"examples": rows, "plan_card": {"Invariant": "target in nums[lo..hi]"},
                                     "mtime": attempt["mtime"]})
        self.assertEqual(status, 200)
        self.assertEqual(attempt["examples"], rows)
        self.assertEqual(attempt["plan_card"]["Invariant"], "target in nums[lo..hi]")
        status, conflict = self.call("PUT", "/api/attempt", {"text": "x", "mtime": stale})
        self.assertEqual(status, 409)
        self.assertIn("EXAMPLES = [", conflict["text"])
        text = attempt["text"].replace("    pass\n", METHOD, 1)
        self.assertEqual(self.call("PUT", "/api/attempt", {"text": text, "mtime": attempt["mtime"]})[0], 200)
        result = self.call("POST", "/api/run", {})[1]
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["rows"]), 2)
        bad = self.call("PUT", "/api/attempt/parts", {"examples": [{"args": "nums", "expected": "1"}],
                                                       "mtime": self.call("GET", "/api/attempt")[1]["mtime"]})
        self.assertEqual(bad[0], 400)

    def test_stage_note_break_block_and_end(self):
        self.start()
        self.assertEqual(self.call("POST", "/api/solve/note", {"stage": 1, "text": "- starts with a dash"})[0], 200)
        self.call("POST", "/api/solve/stage", {"n": 2})
        self.call("POST", "/api/solve/break", {})
        live = self.call("GET", "/api/state")[1]["live"]
        self.assertEqual((live["stage"], live["notes"], live["block"]["open"]), (2, {"1": "- starts with a dash"}, False))
        self.call("POST", "/api/solve/block", {})
        self.assertTrue(self.call("GET", "/api/state")[1]["live"]["block"]["open"])
        status, body = self.call("POST", "/api/solve/end", {"outcome": "partial", "note": "parked: stage 2"})
        self.assertEqual(status, 200)
        self.assertIn("Logged a0001", body["message"])
        self.assertIsNone(self.call("GET", "/api/state")[1]["live"])

    def test_problem_statement_round_trip_and_bad_slugs(self):
        self.assertIsNone(self.call("GET", "/api/problem?slug=binary-search")[1]["text"])
        self.call("PUT", "/api/problem", {"slug": "binary-search", "text": "Given a sorted array..."})
        self.assertEqual(self.call("GET", "/api/problem?slug=binary-search")[1]["text"], "Given a sorted array...")
        self.assertEqual(self.call("GET", "/api/problem?slug=../config")[0], 400)

    def test_static_files_stay_inside_the_static_folder(self):
        self.assertEqual(self.call("GET", "/static/nope.js")[0], 404)
        self.assertEqual(self.call("GET", "/static/../server.py")[0], 404)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run them and see them fail.**

Run: `python3 -m unittest tests.test_server -v`
Expected: ERROR. `ModuleNotFoundError: No module named 'server'`.

**Step 3: Create `app/static/.gitkeep` (empty) and `app/server.py`:**

```python
"""Local server for the dsa-coach study app (v1: the Solve tab).

    python3 app/server.py [--root NOTEBOOK] [--port 8765] [--no-browser]

It binds to 127.0.0.1 only. Every change to the notebook's records goes through coach.py. The server itself
writes only the live solve's attempt file and problems/<slug>/problem.md.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
import attempt_file  # noqa: E402
import runner  # noqa: E402

REPO = APP.parent
COACH = REPO / "skills" / "dsa-coach" / "scripts" / "coach.py"
STATIC = APP / "static"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HOSTS = {"127.0.0.1", "localhost"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8"}


class ApiError(Exception):
    def __init__(self, status: int, message: str, extra: dict | None = None):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra or {}


class Coach:
    """coach.py against one notebook."""

    def __init__(self, root: Path, env: dict | None = None):
        self.root, self.env = Path(root), env

    def run(self, *args: str) -> str:
        proc = subprocess.run([sys.executable, str(COACH), "--root", str(self.root), *args],
                              capture_output=True, text=True, env=self.env)
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout).strip().removeprefix("error: ")
            raise ApiError(409 if "already live" in message else 400, message)
        return proc.stdout.strip()

    def json(self, *args: str):
        return json.loads(self.run(*args, "--json"))


# helpers ----------------------------------------------------------------------
def need(d: dict, key: str, kind: type, blank_ok: bool = False):
    value = d.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) and kind is int:
        raise ApiError(400, f"missing or wrong {key}")
    if kind is str and not blank_ok and not value.strip():
        raise ApiError(400, f"{key} is empty")
    return value


def check_slug(value) -> str:
    if not isinstance(value, str) or not SLUG.match(value):
        raise ApiError(400, "a problem slug is lowercase letters, digits and dashes")
    return value


def live_solve(coach: Coach) -> dict:
    live = coach.json("solve", "show")
    if live is None:
        raise ApiError(409, "no live solve")
    return live


def read_attempt(path: Path, live: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    out = {"file": live["file"], "path": str(path), "text": text, "mtime": path.stat().st_mtime_ns,
           "plan_card": attempt_file.read_plan_card(text), "examples": [], "examples_error": None}
    try:
        out["examples"] = attempt_file.read_examples(text)
    except ValueError as e:
        out["examples_error"] = str(e)
    return out


def write_checked(path: Path, live: dict, text: str, d: dict) -> dict:
    """Write unless the file changed on disk since the page loaded it (pass force to overwrite anyway)."""
    if not d.get("force") and d.get("mtime") != path.stat().st_mtime_ns:
        raise ApiError(409, "the attempt file changed on disk since you loaded it", read_attempt(path, live))
    path.write_text(text, encoding="utf-8")
    return read_attempt(path, live)


# routes -----------------------------------------------------------------------
def get_state(coach, q):
    live = coach.json("solve", "show")
    state = {"live": live, "next": None, "due": None, "attempt_mtime": None}
    if live:
        path = coach.root / live["file"]
        state["attempt_mtime"] = path.stat().st_mtime_ns if path.exists() else None
    else:
        state["next"], state["due"] = coach.json("next"), coach.json("due")
    return state


def get_attempt(coach, q):
    live = live_solve(coach)
    return read_attempt(coach.root / live["file"], live)


def put_attempt(coach, d):
    live = live_solve(coach)
    return write_checked(coach.root / live["file"], live, need(d, "text", str, blank_ok=True), d)


def put_parts(coach, d):
    live = live_solve(coach)
    path = coach.root / live["file"]
    text = path.read_text(encoding="utf-8")
    try:
        if "plan_card" in d:
            text = attempt_file.write_plan_card(text, d["plan_card"])
        if "examples" in d:
            text = attempt_file.write_examples(text, d["examples"])
    except ValueError as e:
        raise ApiError(400, str(e))
    return write_checked(path, live, text, d)


def post_start(coach, d):
    args = ["solve", "start", "--problem", need(d, "problem", str).strip().lower(),
            "--confidence", str(need(d, "confidence", int))]
    for key in ("pattern", "difficulty", "mode"):
        if d.get(key):
            args += [f"--{key}", str(d[key])]
    if d.get("unlabeled"):
        args.append("--unlabeled")
    return {"message": coach.run(*args)}


def post_stage(coach, d):
    return {"message": coach.run("solve", "stage", str(need(d, "n", int)))}


def post_note(coach, d):
    stage, text = need(d, "stage", int), need(d, "text", str, blank_ok=True)
    return {"message": coach.run("solve", "note", "--stage", str(stage), f"--text={text}")}


def post_break(coach, d):
    return {"message": coach.run("solve", "break")}


def post_block(coach, d):
    return {"message": coach.run("solve", "block")}


def post_end(coach, d):
    args = ["solve", "end", "--outcome", need(d, "outcome", str)]
    if d.get("note"):
        args.append(f"--note={d['note']}")
    return {"message": coach.run(*args)}


def get_problem(coach, q):
    path = coach.root / "problems" / check_slug(q.get("slug")) / "problem.md"
    return {"text": path.read_text(encoding="utf-8") if path.exists() else None}


def put_problem(coach, d):
    path = coach.root / "problems" / check_slug(d.get("slug")) / "problem.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(need(d, "text", str), encoding="utf-8")
    return {"text": path.read_text(encoding="utf-8")}


def post_run(coach, d):
    return runner.run(coach.root / live_solve(coach)["file"])


ROUTES = {
    ("GET", "/api/state"): get_state,
    ("GET", "/api/attempt"): get_attempt,
    ("PUT", "/api/attempt"): put_attempt,
    ("PUT", "/api/attempt/parts"): put_parts,
    ("POST", "/api/solve/start"): post_start,
    ("POST", "/api/solve/stage"): post_stage,
    ("POST", "/api/solve/note"): post_note,
    ("POST", "/api/solve/break"): post_break,
    ("POST", "/api/solve/block"): post_block,
    ("POST", "/api/solve/end"): post_end,
    ("GET", "/api/problem"): get_problem,
    ("PUT", "/api/problem"): put_problem,
    ("POST", "/api/run"): post_run,
}


# HTTP -------------------------------------------------------------------------
def make_handler(coach: Coach):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def send(self, status: int, body, ctype: str = "application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def read_body(self) -> dict:
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            try:
                data = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                raise ApiError(400, "the request body isn't JSON")
            if not isinstance(data, dict):
                raise ApiError(400, "the request body must be a JSON object")
            return data

        def static(self, path: str):
            name = "index.html" if path in ("", "/") else path.removeprefix("/static/")
            target = (STATIC / name).resolve()
            if target.parent != STATIC.resolve() or not target.is_file():
                raise ApiError(404, "not found")
            self.send(200, target.read_bytes(), TYPES.get(target.suffix, "application/octet-stream"))

        def handle_any(self, method: str):
            url = urlparse(self.path)
            try:
                if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in HOSTS:
                    raise ApiError(403, "this server only answers on 127.0.0.1 or localhost")
                if not url.path.startswith("/api/"):
                    if method != "GET":
                        raise ApiError(405, "method not allowed")
                    return self.static(url.path)
                if self.headers.get("X-DSA-Coach") != "1":
                    raise ApiError(403, "missing the X-DSA-Coach header")
                route = ROUTES.get((method, url.path))
                if route is None:
                    raise ApiError(404, f"no route {method} {url.path}")
                data = self.read_body() if method in ("POST", "PUT") else \
                    {k: v[0] for k, v in parse_qs(url.query).items()}
                self.send(200, route(coach, data))
            except ApiError as e:
                self.send(e.status, {"error": e.message, **e.extra})

        def do_GET(self):
            self.handle_any("GET")

        def do_POST(self):
            self.handle_any("POST")

        def do_PUT(self):
            self.handle_any("PUT")

    return Handler


def make_server(root: Path, port: int = 8765, env: dict | None = None, tries: int = 10) -> ThreadingHTTPServer:
    handler = make_handler(Coach(root, env))
    for p in [0] if port == 0 else range(port, port + tries):
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), handler)
        except OSError:
            continue
    raise SystemExit(f"no free port in {port}-{port + tries - 1}; pass --port")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="dsa-coach study app (the Solve tab)")
    p.add_argument("--root", type=Path, help="notebook folder (default: $DSA_NOTEBOOK, else ./notebook in the repo)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)
    root = (a.root or Path(os.environ.get("DSA_NOTEBOOK") or REPO / "notebook")).resolve()
    if not (root / "config.json").exists():
        raise SystemExit(f"{root} isn't a dsa-coach notebook (no config.json). Pass --root.")
    server = make_server(root, a.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"dsa-coach study app: {url}  (notebook: {root})  Ctrl+C stops it")
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
```

**Step 4: Run them and see them pass.**

Run: `python3 -m unittest tests.test_server -v`
Expected: all PASS.

**Step 5: Run the whole suite, then commit.**

Run: `python3 -m unittest discover -s tests -v`
Expected: all PASS.

```bash
git add app/server.py app/static/.gitkeep tests/test_server.py
git commit -m "app: local server for the Solve tab, bound to 127.0.0.1"
```

---

### Task 7: The page (`app/static/`)

No unit tests: the logic that can break silently is in Tasks 4–6. Step 4 is a hand check in the browser.

**Files:**
- Create: `app/static/index.html`, `app/static/app.css`, `app/static/app.js`
- Delete: `app/static/.gitkeep`
- Test: `tests/test_server.py` (one test for `GET /`)

**Step 1: Write the failing test.** Add to `ServerTest`:

```python
    def test_the_page_is_served(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/")
        with urllib.request.urlopen(req) as res:
            self.assertIn("text/html", res.headers["Content-Type"])
            page = res.read().decode()
        self.assertIn('id="panel"', page)
        self.assertIn("/static/app.js", page)
```

Run: `python3 -m unittest tests.test_server.ServerTest.test_the_page_is_served -v`
Expected: FAIL with HTTP 404.

**Step 2: Create `app/static/index.html`:**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DSA Coach · Solve</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
<header id="bar">
  <span id="problem">DSA Coach</span>
  <nav id="stages" aria-label="Solve stages"></nav>
  <span id="rung"></span>
  <span id="timer"></span>
  <button id="block-btn" hidden>Start the next block</button>
</header>
<div id="banner" role="status" hidden></div>

<main id="start" hidden>
  <h1>Start a solve</h1>
  <p id="next-pick"></p>
  <label>Problem (LeetCode slug) <input id="slug" placeholder="koko-eating-bananas" autocomplete="off"></label>
  <label>Pattern (only for problems outside the roadmap) <input id="pattern" placeholder="binary-search" autocomplete="off"></label>
  <label>How sure are you that you'll solve it without help?
    <select id="confidence">
      <option value="">choose 1–5</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option>
    </select>
  </label>
  <button id="start-btn" disabled>Start</button>
  <p id="due-line" class="muted"></p>
</main>

<main id="solve" hidden>
  <section id="panel"></section>
  <section id="work">
    <div class="toolbar">
      <span id="file" class="muted"></span>
      <span id="dirty" class="muted"></span>
      <span class="spacer"></span>
      <button id="save-btn">Save</button>
      <button id="run-btn" class="primary">Run tests</button>
    </div>
    <div id="editor-host"><textarea id="editor-fallback" spellcheck="false"></textarea></div>
    <div id="results"></div>
  </section>
</main>

<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/python/python.min.js"></script>
<script src="/static/app.js"></script>
</body>
</html>
```

**Step 3: Create `app/static/app.css`:**

```css
:root {
  --bg: #fbfaf7; --fg: #1d1d1b; --muted: #6b6a66; --line: #dddad2; --panel: #f3f1ec;
  --accent: #2f5d8a; --ok: #2e7d4f; --fail: #b3412e; --nudge: #8a6d1f;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 15px;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #18181a; --fg: #e8e6e1; --muted: #9b9890; --line: #34333a; --panel: #212125;
          --accent: #7fb0e0; --ok: #6cc28f; --fail: #ef8a76; --nudge: #d9b45a; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); }
a { color: var(--accent); }
button { font: inherit; padding: 4px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--fg); cursor: pointer; }
button:disabled { opacity: .45; cursor: default; }
button.primary { background: var(--accent); color: var(--bg); border-color: var(--accent); }
input, textarea, select { font: inherit; width: 100%; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--fg); }
textarea { resize: vertical; }
label { display: block; margin: 10px 0; color: var(--muted); }
label > input, label > textarea, label > select { margin-top: 4px; color: var(--fg); }
pre { white-space: pre-wrap; margin: 6px 0; font-size: 13px; }
code, pre, .CodeMirror, #editor-fallback { font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.muted { color: var(--muted); }

#bar { display: flex; align-items: center; gap: 14px; padding: 8px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
#problem { font-weight: 600; }
#stages { display: flex; gap: 4px; }
#stages button { width: 30px; padding: 3px 0; }
#stages button.done { color: var(--ok); }
#stages button.current { border-color: var(--accent); color: var(--accent); font-weight: 700; }
#stages button.viewing { background: var(--accent); color: var(--bg); }
#rung, #timer { color: var(--muted); font-variant-numeric: tabular-nums; }

#banner { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; padding: 8px 16px; background: var(--panel); border-bottom: 1px solid var(--line); }
#banner > span { flex: 1 1 300px; }
#banner .close { margin-left: auto; }

#start { max-width: 560px; margin: 32px auto; padding: 0 16px; }
#solve { display: grid; grid-template-columns: minmax(320px, 2fr) 3fr; gap: 0; height: calc(100vh - 50px); }
#panel { overflow: auto; padding: 12px 16px; border-right: 1px solid var(--line); }
#panel h2 { font-size: 18px; margin: 14px 0 4px; }
#panel .question { color: var(--muted); margin-top: 0; }
#panel .actions { display: flex; gap: 8px; margin: 14px 0; flex-wrap: wrap; }
#panel .nudge { color: var(--nudge); }
details.problem { border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; }
details.problem summary { cursor: pointer; color: var(--muted); }
table.examples input[type=checkbox] { width: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }

#work { display: flex; flex-direction: column; min-width: 0; }
.toolbar { display: flex; gap: 8px; align-items: center; padding: 6px 12px; border-bottom: 1px solid var(--line); }
.toolbar .spacer { flex: 1; }
#editor-host { flex: 1; min-height: 0; overflow: hidden; }
#editor-host .CodeMirror { height: 100%; background: var(--bg); color: var(--fg); }
#editor-fallback { width: 100%; height: 100%; border: 0; border-radius: 0; padding: 10px; }
#results { max-height: 35vh; overflow: auto; border-top: 1px solid var(--line); padding: 6px 12px; }
tr.ok td:first-child { color: var(--ok); font-weight: 600; }
tr.fail td:first-child, pre.fail { color: var(--fail); font-weight: 600; }

@media (max-width: 800px) { #solve { grid-template-columns: 1fr; height: auto; } #editor-host { height: 50vh; } }
```

CodeMirror 5's default theme has a white background; the two `#editor-host .CodeMirror` colours above are enough for the dark mode to be readable. Cursor and selection colours in dark mode are a polish item, not a v1 requirement.

**Step 4: Create `app/static/app.js`:**

```js
"use strict";

// Stage names and prompts follow references/protocol.md ("Stage prompts for the solve protocol").
const STAGES = [
  ["Unknown, data, condition", "What is the unknown, what is given, and what must hold? Restate it in one sentence. Predict the output for two or three inputs, at least one of them an edge case (empty, one element, duplicates, negatives)."],
  ["Brute force on the grid", "What is every candidate answer? How would you check one?"],
  ["Count", "How many times does the innermost line run? What does one run cost? Is that fast enough for these constraints?"],
  ["Find the repeated work", "What does the brute force recompute? Which candidates can you prove are useless?"],
  ["Classify and choose the state", "Have you seen a problem with the same unknown? Which pattern, what in the problem made you think of it, and which datum does it rely on? What do add, remove and check cost?"],
  ["Plan card", "Fill in the plan card, including what it relies on and when it breaks, then trace one example by hand."],
  ["Pseudocode, then code", "Write the subgoal comments first, then the code under each one. Does each step keep the invariant?"],
  ["Test and look back", "Trace the edge case as if there's a bug, run the tests, then answer the three questions below."],
];
const PLAN_FIELDS = ["State", "Invariant", "Relies on", "Breaks if", "Termination", "Complexity", "Hand trace"];
const LOOK_BACK = ["Why it works, in one sentence",
  "Time and space complexity, and why",
  "One more question: another approach and its trade-off, a changed constraint and what it breaks, or another problem this method solves"];

const $ = (id) => document.getElementById(id);
let state = null;        // the last /api/state
let attempt = null;      // the last /api/attempt: {file, path, text, mtime, plan_card, examples, examples_error}
let problemText = null;  // problems/<slug>/problem.md, or null before it's pasted
let view = null;         // the stage shown in the panel
let lastStage = null;    // the live stage at the previous poll
let editor = null;       // CodeMirror, or null when the CDN didn't load and the textarea is used
let dirty = false;
let blockBanner = null;  // the block number the "block is over" banner was shown for
let warnedMtime = null;  // the disk mtime we already warned about
let busy = false;

// --- plumbing ----------------------------------------------------------------
async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: {"X-DSA-Coach": "1", "Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    const err = new Error(data.error || res.statusText);
    err.status = res.status; err.data = data;
    throw err;
  }
  return data;
}

const escapeHtml = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

function banner(html, actions = []) {
  const el = $("banner");
  el.innerHTML = "";
  const text = document.createElement("span");
  text.innerHTML = html;
  el.append(text);
  for (const [label, fn] of actions) {
    el.append(button(label, async () => { el.hidden = true; await fn(); }));
  }
  const close = button("×", () => { el.hidden = true; });
  close.className = "close";
  el.append(close);
  el.hidden = false;
}

function fail(e) {
  if (!e.shown) banner(escapeHtml(e.message));
}

function button(label, fn) {
  const b = document.createElement("button");
  b.textContent = label;
  b.onclick = () => Promise.resolve().then(fn).catch(fail);
  return b;
}

function field(parent, label, value, multiline) {
  const l = document.createElement("label");
  l.textContent = label;
  const input = document.createElement(multiline ? "textarea" : "input");
  if (multiline) input.rows = 3;
  input.value = value || "";
  l.append(input);
  parent.append(l);
  return input;
}

async function copyPrompt(text) {
  try {
    await navigator.clipboard.writeText(text);
    banner("Copied. Paste it into the coach chat: <code>" + escapeHtml(text) + "</code>");
  } catch {
    banner("Copy this into the coach chat: <code>" + escapeHtml(text) + "</code>");
  }
}

// --- editor and the attempt file ---------------------------------------------
function setupEditor() {
  if (window.CodeMirror) {
    $("editor-host").innerHTML = "";
    editor = CodeMirror($("editor-host"), {
      mode: "python", lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false,
      extraKeys: {Tab: (cm) => cm.replaceSelection("    "), "Cmd-S": () => save(), "Ctrl-S": () => save()},
    });
    editor.on("change", () => markDirty(true));
  } else {
    const ta = $("editor-fallback");
    ta.addEventListener("input", () => markDirty(true));
    ta.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); }
    });
  }
}
const getCode = () => (editor ? editor.getValue() : $("editor-fallback").value);
function setCode(text) {
  if (editor) editor.setValue(text); else $("editor-fallback").value = text;
  markDirty(false);
}
function markDirty(d) {
  dirty = d;
  $("dirty").textContent = d ? "unsaved" : "saved";
}

function useAttempt(a) {
  attempt = a;
  warnedMtime = null;
  setCode(a.text);
  $("file").textContent = a.file;
}

function conflict(disk) {
  warnedMtime = disk.mtime;
  banner("The attempt file changed on disk (the coach or another editor saved it) while you had unsaved edits.", [
    ["Load the disk version (drops my edits)", async () => { useAttempt(disk); renderPanel(); }],
    ["Keep mine (overwrite the file)", async () => {
      useAttempt(await api("PUT", "/api/attempt", {text: getCode(), force: true}));
    }],
  ]);
}

async function save() {
  if (!attempt) return true;
  try {
    const out = await api("PUT", "/api/attempt", {text: getCode(), mtime: attempt.mtime});
    attempt = out;
    markDirty(false);
    return true;
  } catch (e) {
    if (e.status === 409) conflict(e.data); else fail(e);
    return false;
  }
}

async function saveParts(parts) {
  if (dirty && !(await save())) {
    const e = new Error("not saved"); e.shown = true; throw e;
  }
  try {
    useAttempt(await api("PUT", "/api/attempt/parts", {...parts, mtime: attempt.mtime}));
  } catch (e) {
    if (e.status === 409) { conflict(e.data); e.shown = true; }
    throw e;
  }
}

async function runTests() {
  if (dirty && !(await save())) return;
  $("results").innerHTML = "<p class='muted'>Running…</p>";
  renderResults(await api("POST", "/api/run", {}));
}

function renderResults(r) {
  const out = $("results");
  out.innerHTML = "";
  if (r.error) {
    const pre = document.createElement("pre");
    pre.className = "fail";
    pre.textContent = r.error;
    out.append(pre);
  }
  if (!r.rows.length) return;
  const t = document.createElement("table");
  t.innerHTML = "<tr><th></th><th>input</th><th>expected</th><th>got</th></tr>";
  for (const row of r.rows) {
    const tr = t.insertRow();
    tr.className = row.ok ? "ok" : "fail";
    for (const v of [row.ok ? "ok" : "FAIL", row.args, row.expected, row.error ? "error" : row.got]) {
      tr.insertCell().textContent = v;
    }
    if (row.error || row.stdout) {
      const cell = t.insertRow().insertCell();
      cell.colSpan = 4;
      const pre = document.createElement("pre");
      pre.textContent = (row.stdout || "") + (row.error || "");
      cell.append(pre);
    }
  }
  out.append(t);
}

// --- top bar -----------------------------------------------------------------
function renderBar() {
  const live = state.live;
  const stages = $("stages");
  stages.innerHTML = "";
  $("block-btn").hidden = !live || live.block.open;
  if (!live) {
    $("problem").textContent = "DSA Coach";
    $("rung").textContent = $("timer").textContent = "";
    return;
  }
  $("problem").innerHTML = `<a href="${escapeHtml(live.url)}" target="_blank" rel="noopener">${escapeHtml(live.problem)}</a>` +
    (live.labeled ? ` <span class="muted">${escapeHtml(live.pattern_name)}</span>` : "");
  STAGES.forEach(([name], i) => {
    const n = i + 1;
    const b = button(String(n), () => goTo(n));
    b.title = name;
    b.className = (n === live.stage ? "current" : n < live.stage ? "done" : "") + (n === view ? " viewing" : "");
    stages.append(b);
  });
  $("rung").textContent = `hint rung ${live.rung}/7`;
  const blk = live.block;
  $("timer").textContent = blk.open ? `block ${blk.number}: ${blk.elapsed} of ${blk.length} min`
    : `on a break after block ${blk.number}`;
  if (blk.open && blk.elapsed >= blk.length && blockBanner !== blk.number) {
    blockBanner = blk.number;
    blockOver();
  }
}

function goTo(n) {
  const live = state.live;
  if (n <= live.stage) { view = n; renderPanel(); renderBar(); return; }
  banner(`Which stage are you in? The solve is at stage ${live.stage} (${escapeHtml(STAGES[live.stage - 1][0])}).`, [
    [`Move to stage ${n} anyway`, async () => { await api("POST", "/api/solve/stage", {n}); view = n; await refresh(true); }],
    [`Stay at stage ${live.stage}`, async () => {}],
  ]);
}

function blockOver() {
  const live = state.live;
  banner(`Focus block ${live.block.number} is over. If you're stuck, a five-minute break away from the screen often loosens a first idea that isn't working.`, [
    ["Take a break", async () => { await api("POST", "/api/solve/break", {}); await refresh(); }],
    ["Another block", async () => { await api("POST", "/api/solve/block", {}); await refresh(); }],
    ["Ask for the next rung", () => copyPrompt(`My focus block is over and I'm stuck at stage ${live.stage} of ${live.problem}. Next rung, please.`)],
    ["Park it until tomorrow", () => endSolve("partial", `parked: block ${live.block.number}, stage ${live.stage}`)],
  ]);
}

// --- the stage panel ---------------------------------------------------------
function askPrompt(n) {
  const live = state.live;
  if (n === 7) return `Check my attempt in ${attempt.path}.`;
  return `I'm done with stage ${n} of ${live.problem}. Check it: my notes are in \`coach.py solve show --json\` and my attempt file is ${attempt.path}.`;
}

function problemBlock() {
  const box = document.createElement("details");
  box.className = "problem";
  box.open = !problemText || view === 1;
  const summary = document.createElement("summary");
  summary.textContent = "Problem statement";
  box.append(summary);
  if (problemText) {
    const pre = document.createElement("pre");
    pre.textContent = problemText;
    box.append(pre);
  } else {
    const ta = document.createElement("textarea");
    ta.rows = 8;
    ta.placeholder = "Paste the problem statement from LeetCode. You only do this once per problem.";
    box.append(ta, button("Save statement", async () => {
      problemText = (await api("PUT", "/api/problem", {slug: state.live.problem, text: ta.value})).text;
      renderPanel();
    }));
  }
  return box;
}

function textStage(panel, note, done, n) {
  const ta = field(panel, n === 7 ? "Notes (optional): your subgoals, or what you're unsure about" : "Your answer", note, true);
  ta.rows = 6;
  return async () => ta.value.trim();
}

function stageOne(panel, note, done) {
  const restate = field(panel, "The problem in one sentence", note, true);
  const table = document.createElement("table");
  table.className = "examples";
  table.innerHTML = "<tr><th>inputs, as Python values (e.g. [5], 5)</th><th>your predicted output</th><th>edge?</th><th></th></tr>";
  const rows = () => [...table.rows].slice(1).map((tr) => ({
    args: tr.querySelector(".args").value.trim(),
    expected: tr.querySelector(".expected").value.trim(),
    edge: tr.querySelector(".edge").checked,
  })).filter((r) => r.args || r.expected);
  const gate = () => { done.disabled = !(restate.value.trim() && rows().some((r) => r.edge && r.args && r.expected)); };
  const addRow = (r = {args: "", expected: "", edge: false}) => {
    const tr = table.insertRow();
    tr.innerHTML = '<td><input class="args"></td><td><input class="expected"></td><td><input type="checkbox" class="edge"></td><td></td>';
    tr.querySelector(".args").value = r.args;
    tr.querySelector(".expected").value = r.expected;
    tr.querySelector(".edge").checked = r.edge;
    tr.cells[3].append(button("×", () => { tr.remove(); gate(); }));
    tr.addEventListener("input", gate);
    tr.addEventListener("change", gate);
  };
  (attempt.examples.length ? attempt.examples : [undefined, undefined]).forEach((r) => addRow(r));
  restate.addEventListener("input", gate);
  panel.append(table, button("Add an example", () => addRow()));
  if (attempt.examples_error) {
    const p = document.createElement("p");
    p.className = "nudge";
    p.textContent = attempt.examples_error;
    panel.append(p);
  }
  const hint = document.createElement("p");
  hint.className = "muted";
  hint.textContent = "Done unlocks once you have a one-sentence restatement and at least one edge case.";
  panel.append(hint);
  setTimeout(gate);
  return async () => { await saveParts({examples: rows()}); return restate.value.trim(); };
}

function stageSix(panel) {
  const inputs = PLAN_FIELDS.map((f) => [f, field(panel, f, attempt.plan_card[f] || "", f === "Hand trace")]);
  return async () => {
    await saveParts({plan_card: Object.fromEntries(inputs.map(([f, el]) => [f, el.value]))});
    return null;  // the plan card lives in the attempt file's docstring, not in a stage note
  };
}

function stageEight(panel, note) {
  const parts = note ? note.split("\n\n") : [];
  const boxes = LOOK_BACK.map((q, i) => field(panel, q, (parts[i] || "").replace(/^[^:]*: /, ""), true));
  return async () => boxes.map((b, i) => `${LOOK_BACK[i].split(":")[0]}: ${b.value.trim()}`).join("\n\n");
}

function renderPanel() {
  const live = state.live;
  const n = view;
  const panel = $("panel");
  panel.innerHTML = "";
  const h = document.createElement("h2");
  h.textContent = `${n}. ${STAGES[n - 1][0]}`;
  const q = document.createElement("p");
  q.className = "question";
  q.textContent = STAGES[n - 1][1];
  panel.append(problemBlock(), h, q);

  const note = (live.notes || {})[String(n)] || "";
  let collect;  // saves this stage's parts of the attempt file, and returns the stage note (or null)
  const saveNote = async () => {
    const text = await collect();
    if (text !== null) await api("POST", "/api/solve/note", {stage: n, text});
    await refresh();
  };
  const done = button(n === 8 ? "Done: end the solve" : `Done with stage ${n}`, async () => {
    await saveNote();
    if (n === 8) return endForm(panel);
    if (n >= state.live.stage) await api("POST", "/api/solve/stage", {n: n + 1});
    view = n + 1;
    await refresh(true);
  });
  collect = ({1: stageOne, 6: stageSix, 8: stageEight}[n] || textStage)(panel, note, done, n);

  if (n === 7 && !PLAN_FIELDS.slice(0, 6).some((f) => (attempt.plan_card[f] || "").trim())) {
    const nudge = document.createElement("p");
    nudge.className = "nudge";
    nudge.textContent = "The plan card (stage 6) is empty. Bugs like a missed last candidate show up in the hand trace before they show up in the tests.";
    panel.append(nudge);
  }
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Save", saveNote), done, button("Ask the coach", () => copyPrompt(askPrompt(n))));
  panel.append(actions);
}

function endForm(panel) {
  const box = document.createElement("div");
  box.innerHTML = "<h3>End the solve</h3>";
  const outcome = document.createElement("select");
  for (const o of ["solved", "partial", "failed"]) outcome.add(new Option(o, o));
  const lesson = field(box, "One-line lesson (goes into the problem's notes)", "", false);
  box.append(outcome, button("Log it", () => endSolve(outcome.value, lesson.value.trim())));
  panel.append(box);
}

async function endSolve(outcome, note) {
  const out = await api("POST", "/api/solve/end", {outcome, note});
  attempt = problemText = view = lastStage = blockBanner = null;
  $("results").innerHTML = "";
  banner(escapeHtml(out.message));
  await refresh();
}

// --- start screen ------------------------------------------------------------
function renderStart() {
  const nx = state.next || {};
  const pick = (nx.kind === "new" || nx.kind === "resolve") && nx.problem ? nx.problem : "";
  $("next-pick").innerHTML = pick
    ? `Next pick: <b>${escapeHtml(pick)}</b> (${nx.kind === "resolve" ? "a re-solve from a blank page" : "a new problem"})`
    : "No pick from <code>coach.py next</code> right now. Type a slug.";
  if (pick && !$("slug").value) $("slug").value = pick;
  const due = state.due;
  $("due-line").textContent = due ? `Due: ${due.resolves.length} re-solve(s), ${due.cards.length} card(s), ${due.drafts} draft card(s).` : "";
  gateStart();
}
const gateStart = () => { $("start-btn").disabled = !($("slug").value.trim() && $("confidence").value); };

async function start() {
  const nx = state.next || {};
  const problem = $("slug").value.trim().toLowerCase();
  const body = {problem, confidence: Number($("confidence").value)};
  if ($("pattern").value.trim()) body.pattern = $("pattern").value.trim();
  if (nx.problem === problem && nx.kind === "new") {
    body.pattern = body.pattern || nx.pattern;
    if (nx.block === false) body.unlabeled = true;
  }
  if (nx.problem === problem && nx.kind === "resolve") body.mode = "review";
  await api("POST", "/api/solve/start", body);
  $("slug").value = $("pattern").value = $("confidence").value = "";
  view = 1;
  await refresh(true);
}

// --- the loop ----------------------------------------------------------------
let queued = null;       // a refresh asked for while one was running: null, or whether it wanted a redraw

async function refresh(redraw = false) {
  if (busy) { queued = Boolean(queued) || redraw; return; }
  busy = true;
  try {
    state = await api("GET", "/api/state");
    const live = state.live;
    $("start").hidden = !!live;
    $("solve").hidden = !live;
    if (!live) { renderBar(); renderStart(); return; }
    if (!attempt || attempt.file !== live.file) {
      useAttempt(await api("GET", "/api/attempt"));
      problemText = (await api("GET", "/api/problem?slug=" + encodeURIComponent(live.problem))).text;
      view = view || live.stage;
      redraw = true;
    } else if (state.attempt_mtime !== attempt.mtime && state.attempt_mtime !== warnedMtime) {
      const disk = await api("GET", "/api/attempt");
      if (dirty) conflict(disk); else { useAttempt(disk); redraw = view === 1 || view === 6; }
    }
    if (lastStage !== null && live.stage !== lastStage && view === lastStage) { view = live.stage; redraw = true; }
    lastStage = live.stage;
    if (redraw) renderPanel();
    renderBar();
  } catch (e) {
    fail(e);
  } finally {
    busy = false;
    if (queued !== null) { const r = queued; queued = null; refresh(r); }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setupEditor();
  $("save-btn").onclick = () => save();
  $("run-btn").onclick = () => runTests().catch(fail);
  $("start-btn").onclick = () => start().catch(fail);
  $("slug").oninput = gateStart;
  $("confidence").onchange = gateStart;
  $("block-btn").onclick = () => api("POST", "/api/solve/block", {}).then(() => refresh(), fail);
  refresh();
  setInterval(refresh, 3000);
});
```

Note on `saveNote` inside `renderPanel`: it calls `refresh()` without a redraw, so the text he's typing in the panel isn't wiped by a re-render.

**Step 5: Delete the placeholder and run the server test.**

```bash
git rm -q app/static/.gitkeep
python3 -m unittest tests.test_server -v
```

Expected: all PASS, including `test_the_page_is_served`.

**Step 6: Hand check in the browser.** With no live solve in the real notebook (`python3 skills/dsa-coach/scripts/coach.py solve show` prints "No live solve."), use a throwaway notebook so the real one isn't touched:

```bash
T=$(mktemp -d) && python3 skills/dsa-coach/scripts/coach.py --root "$T/nb" init --name Check --start-date 2026-11-01 --days 90
python3 app/server.py --root "$T/nb"
```

Check, in order:
1. The start screen shows a next pick. **Start** stays disabled until a confidence is chosen.
2. Start `binary-search` with confidence 3. The bar shows `binary-search`, stage 1 highlighted, `hint rung 0/7`, `block 1: 0 of 15 min`.
3. Paste a statement and save it. It shows folded under "Problem statement".
4. Stage 1: type a restatement and one row. **Done** stays disabled until a row is ticked "edge". Add `[5], 5` → `0` as an edge row, press **Done**. The editor's `EXAMPLES` now has both rows.
5. Click stage 4 in the bar. The banner asks "Which stage are you in?". Choose **Stay**.
6. Fill stages 2–5 and **Done** each. Stage 6: fill Invariant and a two-line Hand trace. The docstring in the editor updates.
7. Stage 7: type the buggy `while lo < hi` version, press **Run tests**. The `[5], 5` row is FAIL. Fix it to `<=`, run again: all ok. Put `while True: pass` in the method and run: "timed out".
8. **Ask the coach** copies a prompt that names the attempt file's full path.
9. In a terminal: `python3 skills/dsa-coach/scripts/coach.py --root "$T/nb" solve hint --rung 2`. Within 3 s the bar shows `hint rung 2/7`.
10. In a terminal, append a comment to the attempt file while the editor has unsaved edits. The conflict banner appears once, and both of its buttons work.
11. Stage 8: answer the three boxes, **Done: end the solve**, choose solved, **Log it**. The banner shows "Logged a0001 …", the start screen comes back, and `$T/nb/problems/binary-search/notes.md` has the stage notes.
12. Block the CDN (DevTools → Network → block `cdnjs.cloudflare.com`), reload: the plain textarea editor still saves and runs.

Stop the server with Ctrl+C and `rm -rf "$T"`.

**Step 7: Commit.**

```bash
git add app/static tests/test_server.py
git commit -m "app: the Solve tab page"
```

---

### Task 8: Skill text, docs and the 0.5.0 release

**Files:**
- Modify: `skills/dsa-coach/SKILL.md` (frontmatter `metadata.version`; the "Keep the live solve" list, around line 56)
- Modify: `skills/dsa-coach/scripts/coach.py:22` (`SKILL_VERSION`)
- Modify: `skills/dsa-coach/references/protocol.md` ("Prompts from the coach pane", around line 76)
- Modify: `skills/dsa-coach/references/platforms.md` (Level A section)
- Modify: `ARCHITECTURE.md` (build roadmap table), `docs/CHANGELOG.md`

**Step 1: SKILL.md.** In the "Keep the live solve in `coach.py solve`" list, after the **During** bullet, add:

```markdown
- **In the study app** (`python3 app/server.py`): he writes stage notes, examples and the plan card there. Read them with `solve show --json` (`notes`) and from the attempt file instead of asking him to paste them. The app's prompts arrive through his clipboard and match the pane's below.
```

Change `version: "0.4.1"` to `version: "0.5.0"` in the frontmatter.

**Step 2: coach.py.** Change `SKILL_VERSION = "0.4.1"` to `SKILL_VERSION = "0.5.0"`.

**Step 3: protocol.md.** Under "**Prompts from the coach pane.**", change the first sentence to: "The pane in Claude Code, and the study app's **Ask the coach** button, send these as his own words:"

**Step 4: platforms.md.** At the end of the "Level A" section (before "### Standalone setup"), add:

```markdown
### The study app (Solve tab)

`python3 app/server.py` from the workspace opens a local page with a stage panel, an editor without autocomplete and a test runner. It reads and writes the same notebook through `coach.py`, so the chat in Claude Code or Codex sees every stage, note and test. It listens on 127.0.0.1 only. Pass `--root` for another notebook.
```

**Step 5: ARCHITECTURE.md.** Add a row under "2b. Solve surface" in the build roadmap table:

```markdown
| 2b+. Study app, Solve tab | `app/server.py` (stdlib, 127.0.0.1), `app/runner.py`, `app/attempt_file.py`, `app/static/`; `coach.py solve note`, `due --json`; LeetCode-shaped attempt template | Done (v0.5.0) |
```

**Step 6: CHANGELOG.** Add at the top, under `# Changelog`:

```markdown
## 0.5.0 · 2026-11-06

A study app for long solves: the Solve tab.

- `app/server.py`: a local page with a stage panel for the 8 stages, an editor without autocomplete (CodeMirror 5, with a textarea fallback), and a test runner. Bound to 127.0.0.1; API calls need an `X-DSA-Coach` header so other web pages can't run code through it.
- Stage 1 asks for a one-sentence restatement and predicted examples with at least one edge case; the examples become the tests. Stage 6 writes the plan card into the attempt file. Jumping ahead asks which stage he is in. The plan card before code is a nudge, not a lock.
- The chat stays in Claude Code or Codex. "Ask the coach" copies a prompt; the page re-reads the live solve every 3 seconds, so hints recorded in the chat show up there.
- `coach.py solve note` (stage notes, copied into the problem's notes at `solve end`) and `coach.py due --json`.
- The attempt template is LeetCode-shaped: `class Solution`, `EXAMPLES`, and a hand-trace field.
- Why: in the 2026-11-05 Binary Search solve he went straight to code, and the bug was the one-element case stage 1 predictions catch (protocol.md: predicting outputs before coding raised correct completion from 53% to 76%). Hints stay in the chat, where the ladder asks which question he'd ask himself first: answer-giving help lowered exam scores in the field study behind rule 1.
```

**Step 7: Check for other version strings, then run everything.**

```bash
grep -rn "0\.4\.1" skills tests --include=*.py --include=*.md
python3 -m unittest discover -s tests -v
python3 skills/dsa-coach/scripts/coach.py validate
python3 skills/dsa-coach/scripts/coach.py package
```

Expected: the grep finds nothing (or only CHANGELOG history); all tests PASS; `validate` reports no problems; `package` writes the zip to `dist/`.

**Step 8: Commit.**

```bash
git add skills ARCHITECTURE.md docs/CHANGELOG.md dist
git commit -m "Release 0.5.0: the study app's Solve tab"
```

---

### Task 9: The real check

**Step 1:** Run `python3 app/server.py` against the real notebook. With Claude Code open beside it, Himanshu does one full solve of `koko-eating-bananas` in the app: confidence, statement, all 8 stages, at least one **Ask the coach**, and **End**.

**Step 2:** Afterwards, check `notebook/problems/koko-eating-bananas/notes.md` (stage notes present), `coach.py status` (the attempt is logged), and that the coach never had to ask him to paste anything.

**Step 3:** Write down anything that got in his way. Each item is a candidate for the next spec, not a fix to slip in now.
