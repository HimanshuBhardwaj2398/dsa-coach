# Study app, version 1: the Solve tab

Date: 2026-11-06 · Status: approved; implementation plan in `docs/plans/2026-11-06-study-app-solve.md` (where they differ, the plan's decisions win) · Target release: dsa-coach 0.5.0

## Goal

A local study app where Himanshu solves problems in one window: the problem statement, a stage-by-stage panel for the solve protocol, a code editor and a test runner. The coach (Claude Code or Codex, on his subscriptions) stays in its own chat beside the app. Both read and write the same `notebook/` through `coach.py`.

This is the first piece of a larger app with Learn, Solve, Notes and Due & Journey tabs. Only Solve is in this spec.

## Decisions

| Question | Decision | Why |
|---|---|---|
| First piece to build | Solve tab | Used every day; replaces the attempt file that marimo couldn't open; the live solve data already exists |
| Where code is written | In the app's own editor, autocomplete off | Close to an interview's bare editor; everything on one screen |
| Where the chat lives in v1 | Claude Code or Codex beside the app | Uses his subscriptions, no API keys or backend for a model; v1 ships sooner |
| Technology | Small local web app: stdlib Python server, one HTML page, CodeMirror | Attempt files stay plain `.py`, so `coach.py`, the guard hook, Codex and Claude Code keep working; full layout control; clear path to v2 chat |
| Layout | Follows the stages: a stage panel that changes with the stage, editor and tests always visible | Stages 1 and 6 are the ones not to skip; today's bug (the one-element case) is what stage 1 catches |
| Plan card before code | A nudge, not a lock | Locks get bypassed with junk |
| Problem statement | Pasted once per problem, saved to `problems/<slug>/problem.md` | Always works; no dependency on LeetCode's unofficial endpoint |
| Code shape | LeetCode's `class Solution`; the runner finds the method itself | He can paste the code straight into LeetCode to submit |
| Who logs the attempt | The coach, from stage 8's prompt; parking stays in the app | The record needs technique, mistake codes and the complexity check, which are the coach's judgment |

## Architecture

```
browser (127.0.0.1)              app/server.py (stdlib)                    notebook/
Solve tab                 HTTP   GET  /api/state    coach.py solve show     sessions/current.json
  stage panel            <---->       --json, next --json, due --json       problems/<slug>/problem.md
  editor (CodeMirror)            POST /api/solve/*  coach.py solve ...      problems/<slug>/<date>.py
  tests [Run]                    GET/PUT /api/attempt   the attempt file    problems/<slug>/notes.md
                                 GET/PUT /api/problem   problem.md          learner/attempts.jsonl
                                 POST /api/run      app/runner.py
                                                                                   ^
                                                        Claude Code / Codex chat (unchanged)
```

Units:

- **`coach.py`** is the only owner of state. The server never writes `current.json`, `attempts.jsonl` or the other JSON files directly; it calls `coach.py` as a subprocess and passes `--json` where a command supports it.
- **`app/server.py`**: `http.server` from the standard library, bound to `127.0.0.1` only. `python3 app/server.py [--root NOTEBOOK] [--port 8765]` starts it and opens the browser. It serves `app/static/` and the JSON endpoints above. The only files it reads and writes itself are the attempt file and `problem.md`.
- **`app/runner.py`**: runs one attempt file in a child process with a 5-second timeout. It imports the file, takes the first public method defined on `Solution` (helpers starting with `_` are skipped), calls it with each `EXAMPLES` row and returns JSON: per row the input, expected, got, ok, and an error with traceback if the call raised.
- **`app/static/index.html`, `app.js`, `app.css`**: the page. CodeMirror 5 (5.65.16) from cdnjs, one script tag and no build step; if it doesn't load, the editor falls back to a `<textarea>`.

### The attempt file

Plain Python that still runs with `python3 file.py`:

```python
"""<slug>

https://leetcode.com/problems/<slug>/
Started <date>. Pattern: <name, or omitted when unlabeled>.

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
    # Subgoal comments first (stage 7), then the code under each one.
    pass


# Stage 1: your predicted examples. Each row is (args tuple, expected).
EXAMPLES = [
]


if __name__ == "__main__":
    name = next(m for m in vars(Solution) if not m.startswith("_"))
    for args, expected in EXAMPLES:
        got = getattr(Solution(), name)(*args)
        print("ok  " if got == expected else "FAIL", args, "->", got, "expected", expected)
```

So `python3 file.py` prints ok or FAIL per example without the app, using the same method lookup as the runner. The app writes the plan card into the docstring and the examples into `EXAMPLES`; the editor shows and edits the whole file.

## Changes to existing code (release 0.5.0)

- **`coach.py solve note --stage N --text TEXT`**: stores the note for stage N in the live solve (`current.json`, field `notes`, keyed by stage). Calling it again replaces that stage's note. `solve show --json` includes the notes. `solve end` appends them to `problems/<slug>/notes.md` under a dated heading.
- **`coach.py due --json`**: new flag; prints the due re-solves and cards as JSON for `/api/state`.
- **`coach.py solve start`**: unchanged from the chat. The app always passes `--confidence`, and the start screen requires a choice before **Start** is enabled.
- **`assets/templates/solve.py`**: switches to the shape above (docstring, `class Solution`, `EXAMPLES`).
- **`SKILL.md`, `references/protocol.md`**: one line each: when the app is in use, read stage notes with `solve show --json` and the attempt file from the notebook instead of asking him to paste them. `references/platforms.md`: how to start the app.
- **`.claude/settings.json`**: no change. The guard hook still blocks Claude's edits to attempt files below rung 7; the app's writes are his.
- Release steps from CLAUDE.md: tests, `validate`, version bump in SKILL.md and coach.py, `package`, CHANGELOG entry.

## One solve, start to end

1. **Start screen.** If a solve is live, it opens at its stage. Otherwise it shows `next`'s pick with **Start**, a slug box to start any problem, and a required confidence choice (1–5). **Start** calls `solve start` (with `--unlabeled` when `next` says `block: false`).
2. **Stage 1, Understand.** If `problem.md` doesn't exist, a paste box asks for the statement and saves it. The statement then sits at the top of the stage panel and can be folded. Below it: a one-sentence restatement and an examples table (inputs, predicted output, an edge-case checkbox). At least one row must be marked as an edge case before **Done with stage 1** is enabled. Rows are written into `EXAMPLES`.
3. **Stages 2–5.** One text box per stage, each showing that stage's question from `references/protocol.md`. For unlabeled solves, the stage 5 box doesn't name the pattern.
4. **Stage 6, Plan card.** Fields for state, invariant, relies on, breaks if, termination, complexity and a hand trace, written into the docstring.
5. **Stage 7, Code.** The editor. If the plan card is empty, a nudge says so. **Run** sends the file to `/api/run` and shows ok or FAIL per row, with the traceback for a crash.
6. **Stage 8, Look back.** Three boxes: why it works in one sentence, complexity, and the extra question (rotating between another approach, a changed constraint, another problem the method solves).
7. **End.** Below the look-back boxes he chooses an outcome (solved, partial, failed) and writes a one-line lesson. **Done: ask the coach to log it** saves his code and answers and copies a prompt with both. The coach checks the work and runs `solve end` with the outcome, the lesson as `--note`, the technique, mistake codes and `--complexity-stated`; hints and minutes come from the live solve as today. The page sees the solve end on its next read and goes back to the start screen. Parking is the one end the page makes itself.

Throughout:

- **Done with stage N** saves the stage's note (`solve note`) and calls `solve stage N+1`. Clicking a later stage directly first asks "Which stage are you in?".
- **Ask the coach** on each stage copies a prompt to the clipboard, for example "I'm done with stage 1. Check it in notebook/problems/binary-search/2026-11-06.py and `solve show --json`." He pastes it into the chat. The app never shows hint text or solution code.
- The page re-reads `/api/state` every 3 seconds, so stage and rung changes made from the chat (`solve stage`, `solve hint`) show up on their own.
- **Focus-block timer** from the live solve's blocks. When a block ends, a banner offers: a break (`solve break`), another block (`solve block`), the next rung (copies a prompt for the chat), or park it (`solve end --outcome partial --note "parked: ..."`).

## When things go wrong

| Situation | Behaviour |
|---|---|
| Code loops or is slow | The runner kills the child process after 5 s; the page shows "timed out", names the example it stopped on and keeps the rows that finished |
| Code raises | The failing row shows the exception and traceback; other rows still run |
| `coach.py` returns an error | The server returns its message with HTTP 409 when a solve is already live, 404 when there's no live solve, and 400 otherwise; the page shows it in a banner. No retry, no guessing |
| The attempt file changes on disk while the editor has unsaved edits | The page warns and keeps his edits; he chooses to reload or overwrite |
| Chat and app change state at once | All state goes through `coach.py`; the last write wins and the page catches up on its next read |
| Port in use | The server tries the next ports, skipping any that another server holds, and prints the URL it got |
| CodeMirror CDN unreachable | The editor falls back to a `<textarea>` |

## Testing

`python3 -m unittest discover -s tests`, standard library only:

- **`tests/test_runner.py`**: finds the method on `Solution`; runs examples; reports a timeout, an exception with its traceback, a missing `EXAMPLES`, and a file with no `Solution`.
- **`tests/test_server.py`**: starts the server against a temporary notebook on a free port and exercises each endpoint; checks it binds to `127.0.0.1`; checks a `coach.py` error comes back as a 4xx with the message.
- **`tests/test_coach.py`**: `solve note` stores, replaces and is written to `notes.md` by `solve end`; the new template runs with `python3` and prints a line per example.
- **Hand check before release**: one full solve of Koko Eating Bananas in the app with the chat open beside it.

## Out of scope for v1

- **v2:** the chat inside the app, driving the `claude -p` and `codex exec` command-line tools so it stays on his subscriptions.
- **Later:**
  - The Learn tab (next after Solve), the Notes tab, and the Due & Journey tab.
  - API keys and open-source models.
  - Fetching problem statements automatically.
  - Input converters for `ListNode` and `TreeNode` problems.
  - Phone layout.
  - Accounts and anyone but him.
