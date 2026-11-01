# /practice Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** One word (`/practice` or "practice") puts the next item in front of the learner, with no status report or decision first.

**Architecture:** A new pick in `coach.py` chooses one item. `pick_new` feeds both `next_steps` in `compute()` and the new `next` subcommand, so `status`, JOURNEY.md and `/practice` agree. A Claude Code command file and a SKILL.md mode tell the coach to act on that item straight away.

**Tech Stack:** Python 3.9+ standard library, `unittest` (tests drive the CLI through `run_cli`), Markdown skill and command files.

**Design:** `docs/plans/2026-11-01-practice-command-design.md`

**Baseline:** `python3 -m unittest discover -s tests` passes 17 tests.

**Branch:** work on `practice-command`. Stage only the paths named in each commit step. `notebook/JOURNEY.md`, `notebook/journey.json` and `notebook/learner/summary.md` have unrelated uncommitted date refreshes, and running the CLI against the real notebook changes them again. Leave them out of these commits.

---

### Task 0: Create the branch

**Step 1: Branch from main**

Run: `git switch -c practice-command`
Expected: `Switched to a new branch 'practice-command'`

---

### Task 1: `pick_new` and the `next` subcommand

**Files:**
- Modify: `skills/dsa-coach/scripts/coach.py` (constants near line 37, new functions before `compute` at line 334, `cmd_next` after `cmd_due` at line 1003, parser after line 1457)
- Test: `tests/test_coach.py`

**Step 1: Write the failing tests**

In `tests/test_coach.py`, add `import importlib.util` to the imports, then add this helper after `attempt`:

```python
    def next_item(self, *args, today=None):
        return json.loads(self.run_cli("next", "--json", *args, today=today).stdout)
```

Add this section before the `# --- status, validate, package, install` banner:

```python
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
```

**Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -5`
Expected: FAILED (failures=3, errors=2 or similar): `next` is an invalid choice, and `coach` has no `pick_new`.

**Step 3: Add the constant and pick functions**

In `coach.py`, after `TIMED_MODES = ("practice", "review", "mock")`, add:

```python
LONG_FORMATS = ("machine-coding", "ai-assisted", "ml-coding")  # started on purpose, never picked by `next`
```

Immediately before `def compute`, add:

```python
def pick_new(rows: list, pattern: str | None = None) -> dict | None:
    """The next new problem: first pattern in plan order under its target, or the named pattern."""
    pool = [r for r in rows if r["key"] == pattern] if pattern else [r for r in rows if r["key"] not in LONG_FORMATS]
    for r in sorted(pool, key=lambda r: (r["week"] or 99, r["tier"] or 9)):
        if pattern or r["attempted"] < r["target"]:
            return {"kind": "new", "pattern": r["key"], "name": r["name"], "problem": r["next_problem"], "first": r["attempted"] == 0}
    return None


def pick_next(j: dict, pattern: str | None = None) -> dict:
    """One item to practise now. A named pattern skips everything due."""
    d = j["due"]
    if not pattern:
        if d["inbox"]:
            return {"kind": "inbox", "files": d["inbox"]}
        if d["resolves"]:
            return dict(d["resolves"][0], kind="resolve")
        if d["cards"]:
            return {"kind": "cards", "count": len(d["cards"])}
    return pick_new(j["patterns"], pattern) or {"kind": "none"}
```

**Step 4: Add the subcommand**

After `cmd_due`, add:

```python
def render_next(item: dict) -> str:
    kind = item["kind"]
    if kind == "inbox":
        return f"Import {len(item['files'])} session delta(s) waiting in inbox/: {', '.join(item['files'])}."
    if kind == "resolve":
        return f"Re-solve {item['problem']} ({item['pattern']}) from a blank page."
    if kind == "cards":
        return f"Quiz: {item['count']} due card(s)."
    if kind == "new" and item["problem"]:
        return f"Solve {item['problem']} ({item['name']})."
    if kind == "new":
        return f"Pick an unattempted problem from the NeetCode {item['name']} section."
    return "Plan finished. Run a mock or an unlabeled mixed set."


def cmd_next(args) -> None:
    root = find_root(args.root)
    pattern = slugify(args.pattern) if args.pattern else None
    if pattern and pattern not in pattern_keys():
        die(f"unknown pattern {pattern}. Choose from: {', '.join(pattern_keys())}")
    item = pick_next(compute(load_state(root), parse_date(args.date)), pattern)
    print(json.dumps(item, indent=2, ensure_ascii=False) if args.json else render_next(item))
```

In `build_parser`, after the `due` parser's `set_defaults` line, add:

```python
    s = sub.add_parser("next", help="the one thing to practise now")
    s.add_argument("--pattern", help="pick a new problem from this pattern, skipping anything due")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    s.set_defaults(func=cmd_next)
```

**Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -4`
Expected: `Ran 22 tests` and `OK`

**Step 6: Commit**

```bash
git add skills/dsa-coach/scripts/coach.py tests/test_coach.py
git commit -m "Add coach.py next to pick one practice item"
```

---

### Task 2: Make `status` agree with `next`

**Files:**
- Modify: `skills/dsa-coach/scripts/coach.py:440-450`
- Test: `tests/test_coach.py`

**Step 1: Write the failing test**

Add to the practice pick section:

```python
    def test_status_steps_match_next_and_put_practice_before_drafts(self):
        self.run_cli("log", "question", "--concept", "sliding-window", "--text", "why?")
        self.run_cli("card", "add", "--concept", "sliding-window", "--type", "trap", "--front", "Q?", "--back", "A.", "--draft")
        steps = self.journey()["next_steps"]
        self.assertTrue(steps[0].startswith("Solve two-sum"), steps)
        self.assertTrue(steps[1].startswith("Approve"), steps)
```

**Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_coach.CoachTest.test_status_steps_match_next_and_put_practice_before_drafts 2>&1 | tail -5`
Expected: FAIL, because `steps[0]` starts with "Approve".

**Step 3: Reorder the steps**

Replace this block in `compute`:

```python
    if drafts:
        steps.append(f"Approve, edit or retire {len(drafts)} draft card(s) (`coach.py card list --drafts`).")
    if due_resolves:
        steps.append("Re-solve from a blank page: " + ", ".join(d["problem"] for d in due_resolves[:3]) + " (a plan-only check is fine for the first).")
    if due_cards:
        steps.append(f"Quiz: {len(due_cards)} due card(s), about {max(2, len(due_cards))} minutes (`coach.py quiz`).")
    if focus and by_key[focus]["status"] in ("exploring", "learning", "not started") and by_key[focus]["next_problem"]:
        steps.append(f"Solve {by_key[focus]['next_problem']} unaided to move {by_key[focus]['name']} forward.")
```

with:

```python
    if due_resolves:
        steps.append("Re-solve from a blank page: " + ", ".join(d["problem"] for d in due_resolves[:3]) + " (a plan-only check is fine for the first).")
    if due_cards:
        steps.append(f"Quiz: {len(due_cards)} due card(s), about {max(2, len(due_cards))} minutes (`coach.py quiz`).")
    new = pick_new(rows)
    if new and new["problem"]:
        steps.append(f"Solve {new['problem']} unaided to move {new['name']} forward.")
    elif new:
        steps.append(f"Pick an unattempted problem from the NeetCode {new['name']} section.")
    if drafts:
        steps.append(f"Approve, edit or retire {len(drafts)} draft card(s) (`coach.py card list --drafts`).")
```

**Step 4: Run all the tests**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -4`
Expected: `Ran 23 tests` and `OK`

**Step 5: Commit**

```bash
git add skills/dsa-coach/scripts/coach.py tests/test_coach.py
git commit -m "Use the practice pick in status and put practice before drafts"
```

---

### Task 3: The practice mode and `/practice` command

**Files:**
- Create: `.claude/commands/practice.md`
- Modify: `skills/dsa-coach/SKILL.md:29` and the modes table at line 43
- Modify: `skills/dsa-coach/references/protocol.md` (new section before `### learn`)
- Modify: `CLAUDE.md`, `AGENTS.md`

**Step 1: Create the command**

`.claude/commands/practice.md`:

```markdown
---
description: Start DSA practice now with one item picked for you
argument-hint: "[pattern or problem]"
---

Use the dsa-coach skill in practice mode (references/protocol.md).

Argument: $ARGUMENTS

1. With no argument, run `python3 skills/dsa-coach/scripts/coach.py next --json`.
2. With an argument, run the same command with `--pattern "<argument>"`. If it fails with "unknown pattern", treat the argument as a problem name and start the solve protocol on it.
3. Act on the result now. Skip the session opening and don't ask what he wants to do.
```

**Step 2: Add the mode to SKILL.md**

Add this row as the first row of the modes table:

```markdown
| "practice", "let's go", `/practice` | practice | `coach.py next --json`, then start on that item at once. Details in references/protocol.md |
```

Add this line after step 3 of "Start of every session":

```markdown
4. **If he asks to practise, skip the opening.** Run `coach.py next --json` and go straight to practice mode.
```

**Step 3: Describe the mode in protocol.md**

Insert before `### learn`:

```markdown
### practice

The fast way in. Don't report status, propose a plan or ask what he wants. `coach.py next --json` returns one item. Write one line saying what it is and why, then the first prompt, in the same message.

| `kind` | First prompt |
|---|---|
| `inbox` | Say what the deltas contain, run `coach.py import`, then run `coach.py next --json` again |
| `resolve` | Review mode, from a blank page |
| `cards` | Quiz mode, one card at a time |
| `new` with `first: true` | Link the problem, then the first-step probe |
| `new` with `first: false` | Link the problem, then stage 1 of the solve protocol |
| `new` with `problem: null` | Pick an unattempted problem from that NeetCode section, then as above |
| `none` | Offer a mock or an unlabeled mixed set |

Problem links are `https://leetcode.com/problems/<slug>/`. After each item, log it and offer the next one in a line. The rules for every mode still apply.

At the end, if draft cards are waiting, ask once: "Keep all N, or go through them?" Keeping all means `card accept` for each. Drafts never hold up practice.
```

**Step 4: Update the workspace instructions**

In `CLAUDE.md`, change the SessionStart line to:

```markdown
- A SessionStart hook prints `coach.py status --brief` at the start of each session. Open from it: where he is, what's due, a proposed plan. If he asks to practise or runs `/practice`, skip the opening and start on the item `coach.py next` picks.
```

In `AGENTS.md`, change the session line to:

```markdown
- At the start of every session run `python3 skills/dsa-coach/scripts/coach.py status --brief` and open from its output: where he is, what's due, a proposed plan. If he asks to practise, skip the opening and start on the item `coach.py next` picks.
```

**Step 5: Check the skill still validates**

Run: `python3 skills/dsa-coach/scripts/coach.py validate`
Expected: output ends in `OK`

**Step 6: Commit**

```bash
git add .claude/commands/practice.md skills/dsa-coach/SKILL.md skills/dsa-coach/references/protocol.md CLAUDE.md AGENTS.md
git commit -m "Add practice mode and /practice command"
```

---

### Task 4: Docs and release 0.2.0

**Files:**
- Modify: `README.md` (session table, commands table)
- Modify: `skills/dsa-coach/SKILL.md` (`metadata.version`)
- Modify: `skills/dsa-coach/scripts/coach.py:22` (`SKILL_VERSION`)
- Modify: `docs/CHANGELOG.md`

**Step 1: Update the README**

In the Claude Code row of "Start a session", change the suggested phrases to begin with `/practice`:

```markdown
| Claude Code | `cd ~/Desktop/dsa-coach && claude`, then `/practice` to start right away, or "where am I?", "teach me two pointers", "review" or "quiz me". The status loads automatically at session start. |
```

Add this row at the top of "Everyday commands", after the `coach.py status` row:

```markdown
| `coach.py next` | The one thing to practise now (`--pattern` to choose one, `--json` for the coach) |
```

**Step 2: Bump the version**

Set `version: "0.2.0"` in SKILL.md and `SKILL_VERSION = "0.2.0"` in `coach.py`.

**Step 3: Record the change**

In `docs/CHANGELOG.md`, add above the 0.1.0 entry:

```markdown
## 0.2.0 · 2026-11-01

One-step practice.

- `/practice` command and practice mode: one item, no opening report. Takes an optional pattern or problem.
- `coach.py next`: picks inbox, due re-solves, due cards, then a new problem in plan order. Long formats are never picked.
- `status` and JOURNEY.md use the same pick, and practice comes before draft approval.
```

**Step 4: Run the full release checks**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -4 && python3 skills/dsa-coach/scripts/coach.py validate && python3 skills/dsa-coach/scripts/coach.py package`
Expected: `Ran 23 tests`, `OK`, validate OK, and the package written to `dist/dsa-coach.zip` (git-ignored).

**Step 5: Commit**

```bash
git add README.md skills/dsa-coach/SKILL.md skills/dsa-coach/scripts/coach.py docs/CHANGELOG.md docs/plans/2026-11-01-practice-command-design.md docs/plans/2026-11-01-practice-command.md
git commit -m "Release 0.2.0: one-step practice"
```

---

### Task 5: Check it in the real notebook

**Step 1: Run the pick against real data**

Run: `python3 skills/dsa-coach/scripts/coach.py next --json`
Expected: `"kind": "new"`, `"pattern": "arrays-hashing"`, `"problem": "two-sum"`, `"first": true`

**Step 2: Check the status agrees**

Run: `python3 skills/dsa-coach/scripts/coach.py status --brief`
Expected: skill 0.2.0, step 1 is "Solve two-sum unaided...", step 2 is the draft approval line.

**Step 3: Check the pattern route**

Run: `python3 skills/dsa-coach/scripts/coach.py next --pattern sliding-window`
Expected: `Solve longest-substring-without-repeating-characters (Sliding Window).`

Slash commands load at session start, so `/practice` needs a new Claude Code session before it can be tried.
