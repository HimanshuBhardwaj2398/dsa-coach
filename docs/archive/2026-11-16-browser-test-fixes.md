> **Archived.** Finished by release 1.0.1. Kept for history: paths inside are as they were when it was written.

# Browser Test Fixes (1.0.1) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix what the browser test of 2026-11-16 found in the learning app and the saved explainers (feedback notes f0001 to f0009), and release it as 1.0.1.

**Architecture:** No new parts. `coach.py map --json` gains three fields (a title for each problem, how many due re-solves are today's, how many days a live solve has been left), and the page in `app/static/` uses them. Two saved explainer pages are repaired, and a new hand-run browser check opens every saved explainer the way the app serves it, so a broken page is caught before he opens it.

**Tech Stack:** Python 3 standard library (`coach.py`, `app/server.py`), plain JavaScript and CSS with no build step (`app/static/`), `unittest`, `node --test`, Playwright for Python (already installed, used by `tests/browser/`).

---

## Read this first

### Where this comes from

On 2026-11-16 the learning app was driven in Chrome and in Playwright against a copy of the notebook. Nine things were logged as feedback notes, f0001 to f0009, in `notebook/feedback.jsonl`. One was fixed that day because it blocked a Learn page (commit `78b3214`: the Arrays & Hashing explainer threw on `localStorage` inside the app's sandbox, so its stepper was dead).

Every change below was first made in a throwaway clone and run there: 83 Python tests, 9 frontend tests, `check_app.py` and the new `check_explainers.py` all passed. The code blocks in this plan are that code. The release steps in Task 11 (version, changelog, backlog, package) were not run.

### The freeze, and when to build this

`plans/backlog.md` says test period 1 "starts with the first attempt logged under that version". On 2026-11-16 all 17 rows of `notebook/learner/attempts.jsonl` carry `skill_version` 0.4.1, so the period has not started. Two choices, and it is Himanshu's call:

- **Build it before the first study session (recommended).** Release 1.0.1 and let test period 1 run on 1.0.1. Task 11 changes the one line in `plans/backlog.md` that names the version.
- **Keep 1.0.0 frozen.** Then this plan waits for the triage at the end of the period.

Do not start Task 0 until he has chosen. If an attempt has been logged under 1.0.0 by the time you read this, the period is running: stop and ask.

By the letter of the triage rule (two notes, or one note and evidence from the notebook), f0006 and f0007 qualify on the notebook's evidence (a live solve six days old, 17 due re-solves). The others are reproduced defects seen once. He has been told this.

### The five changes

| # | Change | Notes | Tasks |
|---|---|---|---|
| A | Saved explainers open correctly from the app, and a check proves it | f0001, f0002, f0003 | 2, 3, 4, 5 |
| B | Today says what to do: the stale solve, today's re-solves, titles | f0006, f0007 | 6, 7 |
| C | Feedback typed into "Improve it" survives, and the prompt panel stays where it was made | f0004, f0005 | 8 |
| D | Views open at the top, the map reopens where he left it, and the offline notice is always in view | f0008 | 9 |
| E | Two small things: the panel shows "Next re-solve", feedback appears in the prompt as typed | f0009 (part) | 10 |

Task 1 fixes the existing browser check itself, which fails whenever his own app is running on port 8765.

### Left out, on purpose

These go to **Later** in `plans/backlog.md` in Task 11. Do not build them here.

- The tab title is "DSA Coach" on every view (f0009).
- Cmd+Enter does not submit the feedback form (f0009).
- The map says "Blind 75 1/8" beside eight rows marked "last: solved" (f0009). The count is of problems solved unaided. This is a wording question for him, not a defect.
- Through the app, the "core idea, in your own words" box on the Arrays & Hashing page is not remembered after a reload, because the sandbox blocks storage. It belongs with the existing Later item "Predictions on explainer pages reach the notebook".
- On the heap page, the index label under node 3 touches the "Array · labels below = indices" caption. It is the fragment's own layout.
- `output/heap-lab/` stays untracked. The existing Later item "Explainers built from tested parts" already lists it.

### Rules of this repo that apply

- Read `CLAUDE.md` first. Keep the code very simple: standard library, no framework, no build step, small pure functions, nothing built for a need that has not shown up.
- Never hand-edit `notebook/JOURNEY.md`, `notebook/journey.json`, `notebook/learner/summary.md` or `notebook/learner/techniques.json`. They are generated. They already show as modified; leave them out of every commit in this plan.
- Codex also edits this repo, sometimes mid-session. Run `git status --short` before each task and stop if a file you are about to edit has changed under you.
- Commit when a task says to. Push only when he asks.
- `docs/research/` was checked: nothing in it speaks to page layout. Change B shows the cap that 1.0.0 already set (`REVIEWS_PER_DAY`) and the question the coach already asks at session start; it adds no rule.

### Commands used throughout

Run all of these from the repo root, `/Users/chetna/Desktop/dsa-coach`.

```bash
python3 -m unittest discover -s tests            # Python tests: 81 before this plan, 83 after Task 6
node --test tests/frontend/*.test.cjs            # frontend tests: 6 before, 9 after Task 10
python3 tests/browser/check_app.py               # browser check of the app and the side panel; prints "OK. Screenshots in ..."
python3 tests/browser/check_explainers.py        # new in Task 2
python3 skills/dsa-coach/scripts/coach.py validate   # prints OK on its last line
```

---

### Task 0: Branch and baseline

**Files:** none.

**Step 1: Check the working tree**

Run: `git status --short`

Expected: the generated notebook files, `notebook/artifacts/registry.json`, `notebook/learner/questions.jsonl` and `plans/README.md` as modified, and `notebook/concepts/heap/`, `notebook/concepts/binary-search/binary-search-explainer.html`, `notebook/feedback.jsonl`, `output/` and this plan as untracked. Nothing under `app/`, `tests/` or `skills/`. If there is, stop and ask.

The Binary Search explainer and its registry entry appeared at 11:52 on 2026-11-16, from another session, while this plan was being written. It is not part of this plan. Ask him whether it is finished. If it is, commit it first, on its own, so that Task 4's commit holds only the heap page:

```bash
git add notebook/concepts/binary-search/binary-search-explainer.html
```

and stage only its entry of `notebook/artifacts/registry.json` (the pending diff holds two entries, heap x0004 and binary-search). If he says it is not finished, leave both files alone and, in Task 4, do not commit `registry.json`: tell him it still waits.

**Step 2: Branch**

```bash
git checkout -b fixes-1.0.1
```

**Step 3: Run the baseline**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3
node --test tests/frontend/*.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"
```

Expected: `Ran 81 tests` and `OK`; `ℹ pass 6`, `ℹ fail 0`.

Do not run `check_app.py` yet. It fails if his app is running on port 8765, and Task 1 fixes that.

---

### Task 1: The browser check stops depending on port 8765

The side panel's default address is `http://127.0.0.1:8765`. The check opens the panel, which connects to that default at once, and only then stores the test server's address. If his real app is running on 8765, the panel's own save of the default address can land after the test's, and the panel then shows his real notebook. Seen on 2026-11-16: the check failed with `unexpected value "Solving contains-duplicate · Arrays & Hashing"`.

**Files:**
- Modify: `tests/browser/check_app.py` (the five lines that open the panel)

**Step 1: Store the address before the panel opens**

Replace:

```python
                panel = context.new_page()
                panel.set_viewport_size({"width": 390, "height": 844})
                panel.goto(server.PANEL_PARENT + "/sidepanel.html")
                panel.evaluate(f"chrome.storage.local.set({{server: {origin!r}}})")
                panel.reload()
```

with:

```python
                # Set the address before the panel opens, so it never tries the default port, where his own app may be running.
                worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
                worker.evaluate(f"chrome.storage.local.set({{server: {origin!r}}})")
                panel = context.new_page()
                panel.set_viewport_size({"width": 390, "height": 844})
                panel.goto(server.PANEL_PARENT + "/sidepanel.html")
```

**Step 2: Run it, with something listening on 8765**

In a second terminal: `python3 app/server.py --no-browser` (it prints the address; it must say 8765). If it says 8766, his own app is already on 8765, which serves the same purpose: stop the one you started. Then:

Run: `python3 tests/browser/check_app.py`

Expected: `OK. Screenshots in ...`. Run it twice. Stop the second terminal's server with Ctrl+C.

**Step 3: Commit**

```bash
git add tests/browser/check_app.py
git commit -m "Browser check: set the panel's address before it opens"
```

---

### Task 2: A browser check for the saved explainers

`check_app.py` registers a one-line placeholder as its explainer, so it cannot see a real page break. This check opens every registered explainer through the app's `/explainer/<key>` route, which serves it with `Content-Security-Policy: sandbox allow-scripts allow-popups`.

**Files:**
- Create: `tests/browser/check_explainers.py`

**Step 1: Write the check**

```python
"""Browser check for the saved explainers. Run by hand: python3 tests/browser/check_explainers.py [--root NOTEBOOK]

Serves the notebook the way the learning app does and opens every registered explainer in Chromium with Playwright.
Each page must be a whole document (a doctype and a title), run without script errors inside the app's sandbox,
and open at its top.
"""
import argparse
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402


def faults(page, url: str) -> list:
    """What is wrong with the explainer at url, in words. Empty when it is fine."""
    found = []
    page.on("pageerror", lambda error: found.append(f"script error: {error}"))
    page.goto(url)
    page.wait_for_timeout(800)  # scripts that run on load have finished
    facts = page.evaluate("({doctype: !!document.doctype, title: document.title.trim(), y: Math.round(scrollY)})")
    if not facts["doctype"] or not facts["title"]:
        found.append("not a whole page: it needs <!doctype html> and a <title>")
    if facts["y"]:
        found.append(f"opens {facts['y']}px down the page: something takes focus or scrolls on load")
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="open every saved explainer the way the learning app serves it")
    parser.add_argument("--root", type=Path, default=REPO / "notebook", help="notebook folder (default: ./notebook in the repo)")
    root = parser.parse_args().root.resolve()
    keys = [p["key"] for p in server.read_map(root)["patterns"] if p["explainer"]]
    srv = server.make_server(root, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bad = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chromium", headless=True)
            for key in keys:
                page = browser.new_page(viewport={"width": 1280, "height": 860})
                found = faults(page, f"http://127.0.0.1:{srv.server_address[1]}/explainer/{key}")
                page.close()
                bad += bool(found)
                print(f"{key}: " + ("ok" if not found else "; ".join(found)))
            browser.close()
    finally:
        srv.shutdown()
        srv.server_close()
    if bad:
        raise SystemExit(f"{bad} of {len(keys)} explainers need fixing")
    print(f"OK. {len(keys)} explainers open cleanly.")


if __name__ == "__main__":
    main()
```

The app is read-only (`tests/test_server.py` has `test_reading_never_writes_the_notebook`), so running this against the real notebook changes nothing.

**Step 2: Run it and watch it fail**

Run: `python3 tests/browser/check_explainers.py; echo "exit $?"`

Expected, exactly these two faults:

```
arrays-hashing: opens 1804px down the page: something takes focus or scrolls on load
sliding-window: ok
stack: ok
binary-search: ok
heap: not a whole page: it needs <!doctype html> and a <title>
2 of 5 explainers need fixing
exit 1
```

(The pixel count may differ a little.) Tasks 3 and 4 turn these two green.

**Step 3: Commit**

```bash
git add tests/browser/check_explainers.py
git commit -m "Browser check: open every saved explainer the way the app serves it"
```

---

### Task 3: The Arrays & Hashing explainer opens at its top (f0002)

`askChoice` draws a prediction gate and focuses its first button. One gate (the doubling question in section 3) is drawn as the page loads, so the browser scrolls to it. Gates drawn while he steps must keep taking focus.

**Files (the same three edits in both):**
- Modify: `notebook/concepts/arrays-hashing/arrays-hashing-explainer.html` (lines 389, 400 and 415)
- Modify: `notebook/concepts/arrays-hashing/explainer.template.html` (the same lines)

**Step 1: Give `askChoice` a `focus` argument**

Replace `function askChoice(box, q, choices, answer, why, done) {` with:

```js
function askChoice(box, q, choices, answer, why, done, focus = true) {
```

Replace the function's last statement, `  box.querySelector("button").focus();`, with:

```js
  if (focus) box.querySelector("button").focus();  // not for a gate drawn as the page loads: that would open the page here
```

**Step 2: Turn it off for the gate drawn on load**

The call that starts `askChoice($("dblGate"), "n doubles from 32 to 64.` ends with `  () => renderDbl(true));`. Replace that last line with:

```js
  () => renderDbl(true), false);
```

Each of the three old strings appears exactly once in each file. Check with `grep -c` before and after.

**Step 3: Run the check**

Run: `python3 tests/browser/check_explainers.py`

Expected: `arrays-hashing: ok`. Heap still fails.

**Step 4: Check by hand that stepping still moves focus**

Run `python3 app/server.py`, open Map → Arrays & Hashing → Read the explainer. The page opens at its title. In section 2, press "Next column →" six times: a "Predict:" question appears and its first button has the focus ring. Stop the server.

**Step 5: Commit**

```bash
git add notebook/concepts/arrays-hashing/arrays-hashing-explainer.html notebook/concepts/arrays-hashing/explainer.template.html
git commit -m "Arrays & Hashing explainer: open at the top"
```

---

### Task 4: The heap explainer becomes a whole page (f0001)

`notebook/concepts/heap/heap-explorer.html` is a widget fragment written for a chat host. It starts at `<div id="heap-explorer">`, has no doctype or title, and takes its colours from variables the host defines (`--foreground`, `--muted` and five more). Opened alone, every fill falls back to black, so the numbers cannot be seen. The fix is a head that defines those seven names and the nine classes the fragment uses. The fragment's own markup and script are not changed.

**Files:**
- Modify: `notebook/concepts/heap/heap-explorer.html` (untracked today; this task commits it)
- Commit with it: `notebook/artifacts/registry.json`, for the heap page's entry, x0004 (see Task 0 about the binary-search entry beside it)

**Step 1: Put this above the file's first line**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Min-heap: predict the next move</title>
<style>
  /* The explorer below was written for a host page that supplies these names and classes. This page supplies its own. */
  :root {
    color-scheme: light dark;
    --background: light-dark(#fbfbfa, #1c1d1f);
    --foreground: light-dark(#1f2328, #e6e6e3);
    --muted: light-dark(#e4e6e9, #34373b);
    --muted-foreground: light-dark(#5b6168, #a3a8ae);
    --border: light-dark(#c9cdd2, #4a4e53);
    --viz-series-1: light-dark(#2f6fd0, #7fb0ff);
    --font-size-base: 15px;
  }
  body { margin: 0 auto; max-width: 760px; padding: 24px 16px; background: var(--background); color: var(--foreground);
    font: var(--font-size-base)/1.5 system-ui, sans-serif; }
  .btn, .form-select, .form-control { font: inherit; padding: 5px 12px; border: 1px solid var(--border); border-radius: 6px;
    background: var(--background); color: var(--foreground); }
  .btn { cursor: pointer; }
  .btn:disabled { opacity: .5; cursor: default; }
  .btn-primary { background: var(--foreground); color: var(--background); }
  .viz-controls, .viz-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; }
  .text-small { font-size: 13px; color: var(--muted-foreground); }
  .tabular-nums { font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
```

**Step 2: Put this after the file's last line** (the last line is `</div>`)

```html
</body>
</html>
```

**Step 3: Run the check**

Run: `python3 tests/browser/check_explainers.py`

Expected:

```
arrays-hashing: ok
sliding-window: ok
stack: ok
binary-search: ok
heap: ok
OK. 5 explainers open cleanly.
```

**Step 4: Look at it**

Run `python3 app/server.py`, open Map → Heap / Priority Queue → Read the explainer. The tree shows 3 at the root, 8 and 5 below, then 12, 10, 7, in grey circles with dark numbers, and the array row shows 3 8 5 12 10 7. Switch the system to dark mode and reload: light numbers on dark circles. Stop the server.

**Step 5: Commit**

```bash
git add notebook/concepts/heap/heap-explorer.html notebook/artifacts/registry.json
git commit -m "Heap explainer: a whole page with its own colours"
```

---

### Task 5: The guide says what a saved page must be (f0003)

**Files:**
- Modify: `skills/dsa-coach/references/explainers.md` (the "Output and saving" list, and step 6 of the pipeline)
- Modify: `README.md` (step 2 of "Changing the skill")

**Step 1: Replace one bullet in `explainers.md`**

Under `## Output and saving`, replace the bullet

```markdown
- Elsewhere (ChatGPT, Codex), write a single self-contained HTML file he can open in a browser.
```

with

```markdown
- Elsewhere (ChatGPT, Codex), write a single HTML file he can open in a browser.
- The saved file is a whole page that needs nothing from its host: `<!doctype html>`, a `<title>`, inline CSS and JS, and its own colours for light and dark. A widget written for a chat host is a fragment: wrap it in a page before saving. The learning app serves the file sandboxed, where `localStorage` and cookies throw, so keep state in memory or put storage inside `try`/`catch`. Nothing takes focus or scrolls while the page loads.
```

**Step 2: Extend step 6 of the pipeline in `explainers.md`**

Replace

```markdown
6. **Page check.** If a browser is available, step through the built page and compare the displayed state with the trace, then look at it once at phone width.
```

with

```markdown
6. **Page check.** If a browser is available, step through the built page and compare the displayed state with the trace, then look at it once at phone width. In the dsa-coach repo, `python3 tests/browser/check_explainers.py` opens every saved page the way the learning app serves it.
```

**Step 3: Name the check in `README.md`**

In "Changing the skill", step 2, replace

```markdown
After changing the app or extension, also `python3 tests/browser/check_app.py`.
```

with

```markdown
After changing the app or extension, also `python3 tests/browser/check_app.py`. After saving or changing an explainer, also `python3 tests/browser/check_explainers.py`.
```

**Step 4: Validate and commit**

Run: `python3 skills/dsa-coach/scripts/coach.py validate | tail -1`

Expected: `OK`

```bash
git add skills/dsa-coach/references/explainers.md README.md
git commit -m "Explainer guide: a saved page is a whole page, and the sandbox has no storage"
```

---

### Task 6: `map --json` names the problems, counts today's re-solves and dates a left solve

**Files:**
- Modify: `skills/dsa-coach/scripts/coach.py` (`cmd_map` near line 1462, `live_view` near line 1516, `cmd_status` near line 1730)
- Test: `tests/test_coach.py` (beside `test_map_json_carries_due_and_the_live_solve`, near line 718)

**Step 1: Write the failing tests**

In `tests/test_coach.py`, inside `test_map_json_carries_due_and_the_live_solve`, replace

```python
        self.assertEqual(set(view["due"]), {"resolves", "cards", "drafts", "inbox"})
```

with

```python
        self.assertEqual(set(view["due"]), {"resolves", "today", "cards", "drafts", "inbox"})
```

Then add these two tests directly after that test method:

```python
    def test_map_names_the_due_resolves_and_says_how_many_are_todays(self):
        for slug in ("two-sum", "valid-anagram", "contains-duplicate", "group-anagrams"):
            self.attempt(slug, "2026-11-01", pattern="arrays-hashing")
        due = json.loads(self.run_cli("map", "--json", today="2026-11-20").stdout)["due"]
        self.assertEqual((len(due["resolves"]), due["today"]), (4, 3))  # REVIEWS_PER_DAY: the first three are today's
        self.assertEqual(sorted(r["title"] for r in due["resolves"]),
                         ["Contains Duplicate", "Group Anagrams", "Two Sum", "Valid Anagram"])

    def test_map_says_how_long_a_live_solve_was_left(self):
        self.run_cli("solve", "start", "--problem", "two-sum", now="22:00")
        live = json.loads(self.run_cli("map", "--json", now="23:30").stdout)["live"]
        self.assertEqual((live["title"], live["idle_days"]), ("Two Sum", 0))
        self.env["DSA_NOW"] = "2026-11-03T09:00:00+05:30"
        self.assertEqual(json.loads(self.run_cli("map", "--json").stdout)["live"]["idle_days"], 2)
```

(`run_cli(now="22:00")` sets the clock to that time on 2026-11-01, the test's own day.)

**Step 2: Run them and watch them fail**

Run: `python3 -m unittest tests.test_coach -k test_map 2>&1 | tail -4`

Expected: `FAILED (failures=1, errors=2)`, with `KeyError: 'today'` and `KeyError: 'title'`.

**Step 3: Change `cmd_map`**

Replace

```python
    journey, roadmap = compute(state, parse_date(args.date)), state["roadmap"]
    live = load_live(root, required=False)
    due = dict(journey["due"], resolves=[dict(r, url=problem_url(roadmap, r["problem"])) for r in journey["due"]["resolves"]])
    view = dict(map_view(journey, roadmap, load_catalogue()), due=due, live=live_view(live) if live else None)
```

with

```python
    journey, roadmap, catalogue = compute(state, parse_date(args.date)), state["roadmap"], load_catalogue()
    titles = {c["slug"]: c["title"] for rows in catalogue.values() for c in rows}
    title = lambda slug: titles.get(slug, slug)  # a problem outside the catalogue keeps its slug
    live = load_live(root, required=False)
    # `today`: how many of the due re-solves, from the top of the list, are still today's (REVIEWS_PER_DAY)
    due = dict(journey["due"], today=len(resolves_left(journey)),
               resolves=[dict(r, title=title(r["problem"]), url=problem_url(roadmap, r["problem"]))
                         for r in journey["due"]["resolves"]])
    view = dict(map_view(journey, roadmap, catalogue), due=due,
                live=dict(live_view(live), title=title(live["problem"])) if live else None)
```

`resolves_left` already exists (near line 563) and is what `next` and `status` use, so the page and the coach agree on which re-solves are today's.

**Step 4: Change `live_view`, and let `cmd_status` read it**

In `live_view`, replace the docstring

```python
    """The live solve plus what follows from it: stage and rung names, minutes so far, the current block, and
    `line`, the state in words (never the pattern: the app shows it as it is)."""
```

with

```python
    """The live solve plus what follows from it: stage and rung names, minutes so far, the current block,
    `idle_days` (whole days since its last block started) and `line`, the state in words (never the pattern:
    the app shows it as it is)."""
```

and in its `return dict(live, ...)`, add one line after the line that ends `minutes=minutes,`:

```python
                idle_days=(at.date() - datetime.fromisoformat(blocks[-1]["start"]).date()).days,
```

In `cmd_status`, replace

```python
        line = describe_live(live_view(live))
        days = (now().date() - datetime.fromisoformat(live["blocks"][-1]["start"]).date()).days
```

with

```python
        view = live_view(live)
        line, days = describe_live(view), view["idle_days"]
```

**Step 5: Run the whole Python suite**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`

Expected: `Ran 83 tests` and `OK`. `test_status_asks_about_a_live_solve_left_from_an_earlier_day` still passes: it covers the `cmd_status` change.

**Step 6: Commit**

```bash
git add skills/dsa-coach/scripts/coach.py tests/test_coach.py
git commit -m "map --json: problem titles, today's re-solves, days a live solve was left"
```

---

### Task 7: Today says what to do (f0006, f0007)

Before: a heading "Solving contains-duplicate", the line "block 10: 15 of 15 min" for a solve left six days ago, and 17 due re-solves in one flat list of slugs that starts with the problem already being solved. After: titles, a line that says the solve was left and what to tell the coach, today's re-solves on show and the rest folded under "14 more waiting".

**Files:**
- Modify: `app/static/app.js` (the pure helpers near line 94, `renderToday` near line 138)
- Modify: `app/static/app.css` (after the `.today li` rule, near line 97)
- Test: `tests/frontend/app.test.cjs`, `tests/browser/check_app.py`

**Step 1: Write the failing frontend tests**

Append to `tests/frontend/app.test.cjs`:

```js

test("due re-solves split into today's and the ones waiting, without the live solve", () => {
  const run = load();
  const split = (today, live) => JSON.parse(run(
    `JSON.stringify(splitDue({today: ${today}, resolves: [{problem: 'a'}, {problem: 'b'}, {problem: 'c'}]}, ${live}))`));
  assert.deepEqual(split(2, 'null'), {today: [{problem: 'a'}, {problem: 'b'}], later: [{problem: 'c'}]});
  assert.deepEqual(split(2, `'a'`), {today: [{problem: 'b'}], later: [{problem: 'c'}]});  // the live solve is shown above the list
  assert.deepEqual(split(0, 'null').today, []);  // today's are done: the rest wait
});

test('a live solve left from an earlier day asks him to decide', () => {
  const run = load();
  assert.match(run(`liveNote({idle_days: 0})`), /^Ask for checks and hints/);
  assert.match(run(`liveNote({idle_days: 6})`), /^Untouched for 6 days\. .*resume it, park it or drop it/);
});
```

Run: `node --test tests/frontend/app.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"`

Expected: `ℹ pass 4`, `ℹ fail 2` (`splitDue is not defined`, `liveNote is not defined`).

**Step 2: Add the two helpers to `app.js`**

Directly above `function byWeek(patterns) {`:

```js
function splitDue(due, liveProblem) {  // today's re-solves and the ones waiting; the live solve has its own place above them
  const listed = (r) => r.problem !== liveProblem;
  return {today: due.resolves.slice(0, due.today).filter(listed), later: due.resolves.slice(due.today).filter(listed)};
}
function liveNote(live) {  // a solve left from an earlier day is his to decide on (the coach asks the same at session start)
  return live.idle_days
    ? `Untouched for ${plural(live.idle_days, "day")}. Tell the coach in chat: resume it, park it or drop it.`
    : "Ask for checks and hints in your coach chat.";
}
```

Run the frontend tests again. Expected: `ℹ pass 6`, `ℹ fail 0`.

**Step 3: Make the browser check expect the new Today**

In `tests/browser/check_app.py`:

Replace the `coach` helper

```python
        def coach(*args, today=None):
            subprocess.run([sys.executable, str(server.COACH), "--root", str(root), *args], check=True,
                           capture_output=True, env=dict(env, DSA_TODAY=today) if today else env)
```

with

```python
        def coach(*args, today=None, now=None):
            dated = {name: value for name, value in (("DSA_TODAY", today), ("DSA_NOW", now)) if value}
            subprocess.run([sys.executable, str(server.COACH), "--root", str(root), *args], check=True,
                           capture_output=True, env=dict(env, **dated))
```

Replace

```python
        coach("solve", "start", "--problem", "two-sum", "--unlabeled")
```

with

```python
        coach("solve", "start", "--problem", "two-sum", "--unlabeled", now="2026-01-02T10:00:00+05:30")  # left open
```

Replace

```python
                expect(page.locator("h1")).to_have_text("Solving two-sum")
                assert "Arrays" not in page.locator("#content").inner_text()  # unlabeled: no pattern name
                expect(page.locator("a", has_text="valid-anagram")).to_have_attribute(
                    "href", "https://leetcode.com/problems/valid-anagram/")
```

with

```python
                expect(page.locator("h1")).to_have_text("Solving Two Sum")
                assert "Arrays" not in page.locator("#content").inner_text()  # unlabeled: no pattern name
                expect(page.locator(".today .nudge")).to_contain_text("Untouched for")  # a solve from an earlier day
                expect(page.locator("a", has_text="Valid Anagram")).to_have_attribute(
                    "href", "https://leetcode.com/problems/valid-anagram/")
```

In the panel part, replace `expect(frame.locator("h1")).to_have_text("Solving two-sum")` with `expect(frame.locator("h1")).to_have_text("Solving Two Sum")`.

Run: `python3 tests/browser/check_app.py 2>&1 | tail -4`

Expected: FAIL, `Locator expected to have text 'Solving Two Sum'`, actual `Solving two-sum`.

**Step 4: Change `renderToday`**

Replace

```js
    const title = elem("h1", `Solving ${live.problem}`);
```

with

```js
    const title = elem("h1", `Solving ${live.title}`);
```

Replace

```js
      elem("p", "Ask for checks and hints in your coach chat.", "hint")));
```

with

```js
      elem("p", liveNote(live), live.idle_days ? "nudge" : "hint")));
```

Replace the block that builds the due box

```js
  const dueBox = section(elem("h2", "Due"));
  if (due.resolves.length) {
    dueBox.append(list(due.resolves.map((r) => {
      const item = elem("span");
      item.append(link(r.problem, r.url, true),
        elem("span", r.overdue_days ? ` · ${plural(r.overdue_days, "day")} overdue` : " · due today", "muted"));
      return item;
    })));
  }
  if (counts.length) dueBox.append(elem("p", counts.join(" · ") + ". Ask the coach in chat."));
  if (!due.resolves.length && !counts.length) dueBox.append(elem("p", "Nothing due.", "muted"));
```

with

```js
  const {today, later} = splitDue(due, live?.problem);
  const dueItem = (r) => {
    const item = elem("span");
    item.append(link(r.title, r.url, true),
      elem("span", r.overdue_days ? ` · ${plural(r.overdue_days, "day")} overdue` : " · due today", "muted"));
    return item;
  };
  const dueBox = section(elem("h2", "Due today"));
  if (today.length) dueBox.append(list(today.map(dueItem)));
  else if (later.length && !due.today) dueBox.append(elem("p", "Today's re-solves are done.", "muted"));
  if (later.length) {  // the coach serves a few re-solves a day; the rest stay folded away
    const more = elem("details");
    more.append(elem("summary", `${later.length} more waiting`), list(later.map(dueItem)));
    dueBox.append(more);
  }
  if (counts.length) dueBox.append(elem("p", counts.join(" · ") + ". Ask the coach in chat."));
  if (!today.length && !later.length && !counts.length) dueBox.append(elem("p", live ? "Nothing else due." : "Nothing due.", "muted"));
```

**Step 5: Add two CSS rules**

In `app/static/app.css`, directly after `.today li { margin: 4px 0; }`:

```css
.today summary { cursor: pointer; color: var(--muted); }
.nudge { color: var(--nudge); font-weight: 600; }
```

**Step 6: Run the checks**

Run: `python3 tests/browser/check_app.py 2>&1 | tail -2`

Expected: `OK. Screenshots in ...`

Run: `node --test tests/frontend/*.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"`

Expected: `ℹ pass 8`, `ℹ fail 0`.

**Step 7: Look at it with the real notebook**

Run `python3 app/server.py`. Today reads "Solving Contains Duplicate · Arrays & Hashing", then in amber "Untouched for N days. Tell the coach in chat: resume it, park it or drop it.", then "Due today" with Valid Anagram and Group Anagrams, then a closed "14 more waiting" that opens on a click. Stop the server.

**Step 8: Commit**

```bash
git add app/static/app.js app/static/app.css tests/frontend/app.test.cjs tests/browser/check_app.py
git commit -m "Today: a left solve asks for a decision; today's re-solves first, by title"
```

---

### Task 8: Typed feedback survives, and the prompt panel stays where it was made (f0004, f0005)

Two facts about the page today. Coming back to the tab redraws the page (so it shows what the coach just saved), and that wipes text typed into "What should change?". The "Ask your coach" panel sits outside the redrawn part, stays open when he goes to another view, and while it is open the page does not redraw on return.

The change: redraw on return unless the feedback form is open; close the form once its text has become the prompt; close the panel when the view changes.

**Files:**
- Modify: `app/static/app.js` (`improveForm` near line 265, the two listeners near line 275)
- Modify: `app/static/index.html` (the hint inside `#handoff`)
- Test: `tests/browser/check_app.py`

**Step 1: Make the browser check expect it**

In `tests/browser/check_app.py`, replace

```python
                page.fill(".improve textarea", "show two equal heights")
                page.click("text=Make the prompt")
                prompt = page.locator("#handoff-prompt").input_value()
                assert "Revise" in prompt and "show two equal heights" in prompt, prompt
                page.screenshot(path=out / "learn-handoff.png", full_page=True)
```

with

```python
                page.fill(".improve textarea", "show two equal heights")
                page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")  # as if he came back to the tab
                page.wait_for_timeout(500)
                expect(page.locator(".improve textarea")).to_have_value("show two equal heights")
                page.click("text=Make the prompt")
                prompt = page.locator("#handoff-prompt").input_value()
                assert "Revise" in prompt and "show two equal heights" in prompt, prompt
                expect(page.locator(".improve")).to_have_count(0)  # the feedback now lives in the prompt
                page.screenshot(path=out / "learn-handoff.png", full_page=True)
                page.click("[data-nav=today]")
                expect(page.locator("#handoff")).to_be_hidden()  # the prompt doesn't follow him to another view
```

Run: `python3 tests/browser/check_app.py 2>&1 | tail -6`

Expected: FAIL at the `.improve textarea` line: the form is gone after the redraw.

**Step 2: Change the two listeners in `app.js`**

Replace

```js
window.addEventListener("hashchange", () => show(false));
// The coach updates the notebook from the chat: coming back to this page or tab reads it again.
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && $("handoff").hidden) show(); });
```

with

```js
window.addEventListener("hashchange", () => {
  $("handoff").hidden = true;  // its prompt belongs to the page he just left
  show(false);
});
// The coach updates the notebook from the chat: coming back to this page or tab reads it again,
// unless he is part-way through typing feedback, which a redraw would wipe.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && !document.querySelector("form.improve")) show();
});
```

**Step 3: Close the form when its text becomes the prompt**

In `improveForm`, replace

```js
  form.onsubmit = (e) => { e.preventDefault(); openHandoff(explainerPrompt(p, text.value.trim())); };
```

with

```js
  form.onsubmit = (e) => {  // the feedback now lives in the prompt, where he can still edit it
    e.preventDefault();
    openHandoff(explainerPrompt(p, text.value.trim()));
    box.replaceWith(explainerBlock(p));
  };
```

**Step 4: Correct the hint in `index.html`**

The page now reads the notebook again by itself when he comes back. Replace

```html
  <p class="hint">Paste this into your coach chat. When the coach has saved the explainer, choose Refresh.</p>
```

with

```html
  <p class="hint">Paste this into your coach chat. This page reads the notebook again when you come back to it.</p>
```

**Step 5: Run the checks**

Run: `python3 tests/browser/check_app.py 2>&1 | tail -2`

Expected: `OK. Screenshots in ...`

**Step 6: Commit**

```bash
git add app/static/app.js app/static/index.html tests/browser/check_app.py
git commit -m "Learn page: typed feedback survives a tab switch; the prompt panel closes with its view"
```

---

### Task 9: Views open at the top, the map reopens where he left it, the offline notice is always in view (f0008)

The page swaps its content on a hash change and never touches the scroll position. At the side panel's width the map is one long column, so a pattern opened from low on the map shows its Learn page with the title above the viewport, and "← Map" lands at the top of the map. The error notice sits above the content, out of view once he has scrolled.

**Files:**
- Modify: `app/static/app.js` (the `hashchange` listener from Task 8, and `show` near line 127)
- Modify: `app/static/index.html` (move `#notice` into the header)
- Modify: `app/static/app.css` (the `#notice` rules near line 85, and the narrow-width rule near line 129)
- Test: `tests/browser/check_app.py`

**Step 1: Make the browser check expect it**

In `tests/browser/check_app.py`, directly above the comment line `# Set the address before the panel opens` (added in Task 1), insert:

```python
                page.set_viewport_size({"width": 390, "height": 600})  # the side panel's width: the map is one long column
                page.goto(origin + "/#/map")
                page.locator('a.node[href="#/learn/bit-manipulation"]').click()  # low on the map: clicking scrolls down to it
                expect(page.locator(".learn h1")).to_be_in_viewport()  # a Learn page, long enough to scroll, opens at its top
                page.click("text=← Map")
                expect(page.locator('a.node[href="#/learn/bit-manipulation"]')).to_be_in_viewport()  # the map, where he left it

```

And near the end, replace

```python
                panel.reload()
                expect(panel.locator("#status")).to_contain_text("offline")
```

with

```python
                panel.reload()
                expect(panel.locator("#status")).to_contain_text("offline")
                page.click("#refresh")  # still scrolled down the map
                expect(page.locator("#notice")).to_be_in_viewport()
```

Run: `python3 tests/browser/check_app.py 2>&1 | tail -6`

Expected: FAIL at `.learn h1` `to_be_in_viewport`. (The pattern must have a Learn page long enough to scroll. The plan first named ML Coding, whose page is too short: that line passed on the old code.)

**Step 2: Set the scroll position on a view change**

In `app.js`, replace the `hashchange` listener written in Task 8

```js
window.addEventListener("hashchange", () => {
  $("handoff").hidden = true;  // its prompt belongs to the page he just left
  show(false);
});
```

with

```js
let mapScroll = 0;  // where the map was left, so "← Map" comes back to the pattern he opened
window.addEventListener("hashchange", (e) => {
  if (route(new URL(e.oldURL).hash).view === "map") mapScroll = scrollY;
  $("handoff").hidden = true;  // its prompt belongs to the page he just left
  show(false);  // draws at once: the data is already here
  scrollTo(0, route(location.hash).view === "map" ? mapScroll : 0);
});
```

`show(false)` has no `await` on its path once the data is loaded, so the new view is in the page before `scrollTo` runs.

**Step 3: Move the notice into the sticky header**

In `index.html`, replace

```html
  <button id="refresh" type="button" class="ghost">Refresh</button>
</header>
<div id="notice" role="status" hidden></div>
```

with

```html
  <button id="refresh" type="button" class="ghost">Refresh</button>
  <div id="notice" role="status" hidden></div>
</header>
```

In `app.css`, replace

```css
#notice, #recovery { margin: 12px 24px 0; padding: 10px 14px; border-radius: 8px; }
#notice { background: var(--fail-soft); }
#recovery { background: var(--nudge-soft); }
```

with

```css
#notice, #recovery { padding: 10px 14px; border-radius: 8px; }
#notice { flex-basis: 100%; background: var(--fail-soft); }  /* inside the sticky header: seen wherever he has scrolled to */
#recovery { margin: 12px 24px 0; background: var(--nudge-soft); }
```

and in the `@media (max-width: 560px)` block replace

```css
  #notice, #recovery, #handoff { margin-inline: 12px; }
```

with

```css
  #recovery, #handoff { margin-inline: 12px; }
```

**Step 4: End "busy" on a failed load too**

`#content` keeps `aria-busy="true"` forever after a failed load. In `show`, replace

```js
    try { data = await getMap(); } catch (e) { if (mine === loads) fail(e); return; }
    if (mine !== loads) return;
    mapData = data;
    $("notice").hidden = true;
    $("content").setAttribute("aria-busy", "false");
```

with

```js
    try { data = await getMap(); } catch (e) { if (mine === loads) fail(e); return; }
    finally { if (mine === loads) $("content").setAttribute("aria-busy", "false"); }
    if (mine !== loads) return;
    mapData = data;
    $("notice").hidden = true;
```

**Step 5: Run the checks**

Run: `python3 tests/browser/check_app.py 2>&1 | tail -2`

Expected: `OK. Screenshots in ...`

Run: `node --test tests/frontend/*.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"`

Expected: `ℹ pass 8`, `ℹ fail 0`.

**Step 6: Commit**

```bash
git add app/static/app.js app/static/index.html app/static/app.css tests/browser/check_app.py
git commit -m "App: views open at the top, the map reopens where it was left, the notice stays in view"
```

---

### Task 10: Two small fixes (f0009, in part)

**Files:**
- Modify: `app/static/app.css` (the last rule of the narrow-width block)
- Modify: `app/static/app.js` (`explainerPrompt` near line 241)
- Test: `tests/frontend/app.test.cjs`

**Step 1: The side panel shows "Next re-solve" and drops "Difficulty"**

At 390 px there is room for three columns. "due now" tells him what to do next; the difficulty does not. In `app.css` replace

```css
  table.problems th:nth-child(4), table.problems td:nth-child(4) { display: none; }
```

with

```css
  table.problems th:nth-child(2), table.problems td:nth-child(2) { display: none; }  /* difficulty: "due now" matters more here */
```

**Step 2: Write the failing test for the prompt**

Append to `tests/frontend/app.test.cjs`:

```js

test('feedback goes into the prompt as he typed it', () => {
  const run = load();
  const p = `({key: 'stack', name: 'Stack', explainer: 'concepts/stack/stack-derived.html'})`;
  assert.match(run(`explainerPrompt(${p}, 'show "two equal" heights')`), /My feedback: "show "two equal" heights"\. Log it/);
});
```

Run: `node --test tests/frontend/app.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"`

Expected: `ℹ fail 1` (the prompt has `\"two equal\"`).

**Step 3: Put the feedback in as typed**

In `explainerPrompt`, replace

```js
    `following references/explainers.md. My feedback: ${JSON.stringify(feedback)}. Log it with coach.py log question ` +
```

with

```js
    `following references/explainers.md. My feedback: "${feedback}". Log it with coach.py log question ` +
```

**Step 4: Run everything**

```bash
node --test tests/frontend/*.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"   # ℹ pass 9, ℹ fail 0
python3 tests/browser/check_app.py 2>&1 | tail -1                       # OK. Screenshots in ...
```

**Step 5: Commit**

```bash
git add app/static/app.css app/static/app.js tests/frontend/app.test.cjs
git commit -m "App: the panel shows the next re-solve; feedback enters the prompt as typed"
```

---

### Task 11: Release 1.0.1

**Files:**
- Modify: `skills/dsa-coach/SKILL.md` (line 6), `skills/dsa-coach/scripts/coach.py` (line 26)
- Modify: `docs/CHANGELOG.md` (new entry at the top, under `# Changelog`)
- Modify: `plans/backlog.md` (first line, the test period's version, the Later list)
- Modify: `plans/README.md`; move this plan to `docs/archive/`

**Step 1: Bump the version in both places**

- `skills/dsa-coach/SKILL.md`: `  version: "1.0.0"` → `  version: "1.0.1"`
- `skills/dsa-coach/scripts/coach.py`: `SKILL_VERSION = "1.0.0"` → `SKILL_VERSION = "1.0.1"`

Run: `grep -rn '"1\.0\.0"' tests/ | head`

If a test names the old version, update it to 1.0.1.

**Step 2: Add the changelog entry**

Directly under `# Changelog` in `docs/CHANGELOG.md` (put the real release date in the heading):

```markdown
## 1.0.1 · 2026-11-XX · What the first browser test found

The learning app was driven in a real browser for the first time against the real notebook, on 2026-11-16. It answers feedback notes f0001 to f0009. No attempt had been logged under 1.0.0, so test period 1 runs on this version.

**Explainers** (f0001, f0002, f0003)
- **The Arrays & Hashing stepper works from the app.** The app serves explainers sandboxed, where `localStorage` throws, and an unguarded read stopped the page's script before the stepper was set up (fixed on the day, `78b3214`). The page also opens at its top now: a prediction drawn on load no longer takes focus.
- **The heap page can be read.** It was a widget fragment that took its colours from a chat host, so alone it drew black on black. It is a whole page with its own light and dark colours.
- **`tests/browser/check_explainers.py`** opens every saved explainer the way the app serves it and fails on a script error, a missing doctype or title, or a page that opens part-way down. `references/explainers.md` says what a saved page must be.

**Today** (f0006, f0007)
- **A live solve left from an earlier day says so,** and says what to tell the coach: resume it, park it or drop it. `status` has asked this since 1.0.0; the page showed the solve as if it were running.
- **Today's re-solves come first, by title.** The rest fold under "N more waiting". The live solve is not listed again below itself. `map --json` carries `due.today`, a `title` on each due re-solve and on the live solve, and `live.idle_days`.

**The Learn page and getting around** (f0004, f0005, f0008, f0009)
- Feedback typed into "Improve it" is no longer wiped by a visit to another tab. The form closes once its text has become the prompt.
- The "Ask your coach" panel closes when he goes to another view, and no longer stops the page from reading the notebook again.
- A view opens at its top, and "← Map" returns to where the map was left. The "app isn't answering" notice sits in the header, in view wherever he has scrolled to.
- At the side panel's width the problems table shows "Next re-solve" and drops "Difficulty". Feedback enters the prompt as typed, without escaped quotes.

**The browser check** sets the side panel's address before the panel opens. It used to fail whenever his own app was running on port 8765.

Tests: `test_map_names_the_due_resolves_and_says_how_many_are_todays`, `test_map_says_how_long_a_live_solve_was_left`, three frontend tests (`splitDue`, `liveNote`, the prompt). 83 Python tests, 9 frontend tests.

Coach check: not needed for this release, which changes nothing about how the coach teaches. The run that 1.0.0 still owes comes before the test period's first study session.
```

**Step 3: Update `plans/backlog.md`**

- First line: `Triaged through f0000.` → `Triaged through f0009.`
- `**Test period 1** is on 1.0.0.` → `**Test period 1** is on 1.0.1.`
- Add to the end of the **Later** list:

```markdown
- **A tab title for each view.** It is "DSA Coach" everywhere (f0009).
- **Cmd+Enter submits the Improve-it form** (f0009).
- **What "Blind 75 1/8" counts.** It is problems solved unaided, shown beside rows that say "last: solved" (f0009). A wording decision.
- **The heap page's layout:** the index under node 3 touches the array caption.
```

- In the existing Later item "Predictions on explainer pages reach the notebook", add one sentence at its end: `The "core idea" box on the Arrays & Hashing page is not remembered through the app, because the sandbox has no storage.`

**Step 4: Run everything, then package**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3                    # Ran 83 tests, OK
node --test tests/frontend/*.test.cjs 2>&1 | grep -E "^ℹ (pass|fail)"   # ℹ pass 9, ℹ fail 0
python3 tests/browser/check_app.py 2>&1 | tail -1                       # OK. Screenshots in ...
python3 tests/browser/check_explainers.py | tail -1                     # OK. 5 explainers open cleanly.
python3 skills/dsa-coach/scripts/coach.py validate | tail -1            # OK
python3 skills/dsa-coach/scripts/coach.py package                       # writes dist/dsa-coach.zip (dist/ is git-ignored)
```

Every line must match before you go on. If one does not, stop and fix it; do not release.

**Step 5: Archive this plan**

```bash
git mv plans/2026-11-16-browser-test-fixes.md docs/archive/2026-11-16-browser-test-fixes.md
```

Add as the archived file's first line: `Finished by release 1.0.1.` In `plans/README.md`, remove this plan's line and restore `No other plans are open.`

**Step 6: Commit, and ask before merging**

```bash
git add skills/dsa-coach/SKILL.md skills/dsa-coach/scripts/coach.py docs/CHANGELOG.md plans/ docs/archive/
git commit -m "Release 1.0.1: what the first browser test found"
```

Then stop. Tell Himanshu the branch `fixes-1.0.1` is ready, what each check printed, and that `dist/dsa-coach.zip` needs re-uploading wherever he uploaded the skill (Claude web, Cowork). Merge and push only when he says so. The notebook's pending session files (`JOURNEY.md`, `journey.json`, `learner/summary.md`, `learner/questions.jsonl`, `feedback.jsonl`) are his to commit as a session commit; they are not part of this release.
