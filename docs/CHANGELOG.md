# Changelog

## 0.5.1 · 2026-11-07

The Solve tab fetches the problem statement.

- **Statement:** when a solve opens without a statement, the app asks LeetCode for that one problem (the GraphQL endpoint its own site uses) and saves it as plain text in `problems/<slug>/problem.md`: the title, the link, then the statement with its examples and constraints. One request per problem, never on a poll and never in bulk.
- **Fallback:** if the fetch fails (offline, the endpoint changed, a premium problem), the paste box appears with the reason and a **Fetch from LeetCode** retry button.
- **Git:** `notebook/problems/*/problem.md` is ignored, fetched or pasted. Statements are LeetCode's text, and the repo is public.
- **Why:** pasting each statement was a chore on every new problem, and the app should stay out of the way of the solve itself.

## 0.5.0 · 2026-11-06

A study app for long solves: the Solve tab.

- **Study app:** `python3 app/server.py` opens a local page with a stage panel for the 8 stages, an editor without autocomplete (CodeMirror 5, with a textarea fallback) and a test runner. It is bound to 127.0.0.1, checks the Host, needs an `X-DSA-Coach: 1` header on API calls and can't be framed, so other web pages can't run code through it.
- **Stages:** stage 1 asks for a one-sentence restatement and predicted examples with at least one edge case; the examples become the tests. Stage 6 writes the plan card into the attempt file. Jumping ahead asks which stage he is in. The plan card before code is a nudge, not a lock.
  - The examples table never drops a row it can't read back, and a row or plan-card value that would break the file is refused.
- **Runner:** the examples run in a separate child process (`python -I`, no stdin) with a 5 s limit. A timeout or crash keeps the finished rows and names the example it stopped on.
- **Chat:** it stays in Claude Code or Codex. "Ask the coach" copies a prompt; the page re-reads the live solve every 3 seconds, so hints recorded in the chat show up there. Stage 8's Done copies a prompt with his outcome and lesson, and the coach logs the attempt with technique, mistake codes and the complexity check; parking ends a solve in the app. If the solve ends from the chat while he has unsaved code or stage text, a banner offers to copy it.
- **`coach.py`:**
  - `solve note --stage N --text T` keeps one note per stage; a blank text clears it. At `solve end` the notes go into the problem's `notes.md`, in a `## Stage notes` section just above `## Lessons`, one `### <date> (<file>)` block per solve.
  - `due --json`, which the app's start screen reads.
  - JSON files are written to a temp file and renamed into place, so a reader never sees half a file.
- **Attempt template:** LeetCode-shaped: the plan card with a hand-trace field, `class Solution` under `from __future__ import annotations` (so LeetCode's `List[int]` hints load), and `EXAMPLES` rows with `# edge` marks. `python3 file.py` prints ok or FAIL per example and stops at the first error with its traceback.
- **Limits:** examples are Python values (lists, numbers, strings, True/False/None), so linked-list and tree problems (`ListNode`, `TreeNode`) don't run in the app yet.
- **Python 3.9:** the app and its tests run on 3.9 and later, like `coach.py`.
- **Skill text:** in the app, the coach reads his notes and the attempt file instead of asking him to paste them, and ends the solve from stage 8's prompt with the full fields (SKILL.md, protocol.md); platforms.md says how to start it.
- **Why:** in the 2026-11-05 Binary Search solve he went straight to code, and the bug was the one-element case stage 1 predictions catch (protocol.md: predicting outputs before coding raised correct completion from 53% to 76% in a CS1 study). Hints stay in the chat, where the ladder asks which question he'd ask himself first: answer-giving help lowered exam scores in the field study behind rule 1.

## 0.4.1 · 2026-11-05

Package the existing DSA coach for reuse outside this workspace.

- Move runtime requirements from `compatibility` frontmatter into the skill body so both the notebook and skill-creator validators accept the package.
- Include `$dsa-coach` in the Codex default prompt.
- Document explicit notebook selection and initialization for an extracted skill, and distinguish the optional project hook from the skill's teaching instructions.
- Preserve the teaching protocol and separate notebook data, as described in `docs/research/`; no changes to learning schedules or scoring.

## 0.4.0 · 2026-11-05

Long solves, in an editor file and a pane beside the chat.

- **`coach.py solve`:** start, stage, hint, break, block, show and end keep the live solve in `notebook/sessions/current.json`.
  - `start` creates a blank attempt file, `problems/<slug>/<date>.py`, with the link, a short plan card and an examples block. A re-solve always gets a new file.
  - `end` logs the attempt. Minutes come from the focus blocks and hints from the highest rung.
  - `--unlabeled` keeps the pattern out of the file, `solve show` and the status.
- **Status:** `status` prints the live solve, so the SessionStart hook brings it back after a compaction or in a new session.
- **Guard:** `coach.py guard`, a PreToolUse hook that `install` adds, blocks Claude's Write and Edit on the live problem's `.py` files until hint rung 7. Rule 1 is now enforced, not only asked.
- **Coach pane:** `plugins/dsa-coach-pane`, a Claude Code plugin, shows the problem, the stage, the focus-block timer and the hint rung beside the chat. Its buttons send prompts to the coach: check my code, stage done, next hint, block over.
  - It names the pattern only for labeled problems.
  - It announces a finished block once.
  - It installs from the workspace's own marketplace (`.claude-plugin/marketplace.json`).
- **Skill text:** SKILL.md, the practice mode, `/practice` and platforms.md run every solve through `coach.py solve`.

## 0.3.0 · 2026-11-05

Principles from *Learning How to Learn*, *How to Solve It* and "Programming as Theory Building" (docs/research/learning-principles.md).

- **Solve protocol:** the eight stages sit under Polya's four phases. Stage 8 is now "test and look back": why the solution works in one sentence, plus one rotating question (another approach, a changed constraint, or another problem).
- **Hint ladder:**
  - It starts with "which question would you ask yourself?"
  - Rung 1 is a general Polya question (table in references/protocol.md).
  - A leading question counts as the rung it gives away.
- **Attempts:**
  - A genuine attempt is one focused block of about 25 minutes.
  - When a block ends unsolved: a short break, then another block, the next rung, or park it until tomorrow (`partial` with a `parked:` note).
- **Reviews and mocks:** both add a changed-constraint question. Mock mode gets an OA variant (2–3 problems, hard start, jump to easy).
- **Plan card:** new Relies on and Breaks if lines, and the invariants table says what each pattern relies on.
- **Keep it simple:**
  - New rule 8.
  - AI drills can plant needless complexity, and the learner turns down suggestions that don't fit the plan card.
  - Machine coding abstracts only around likely changes.
- **`coach.py next` interleaves:**
  - A pattern's first three problems stay together.
  - After that, new problems rotate across started patterns, least recently practised first, with `block: false` so the coach presents them unlabeled.
  - A new pattern starts when its week arrives.
- **Retrieval:**
  - After an explainer, the core idea goes into the concept notes in the learner's own words.
  - After a linked resource, recall comes before discussion.
  - An attempt is offered before more examples or animation.
- **Sessions:** planned in 25-minute blocks, and each ends by agreeing when the next block happens.

## 0.2.0 · 2026-11-01

One-step practice.

- `/practice` command and practice mode: one item, no opening report. Takes an optional pattern or problem.
- `coach.py next`: picks inbox, due re-solves, due cards, then a new problem in plan order. Long formats are never picked.
- `status` and JOURNEY.md use the same pick, and practice comes before draft approval.

## 0.1.0 · 2026-10-30

First version (build step 1: core).

- Skill: rules for every mode, session start and end, eight modes, the eight-stage solve protocol, the hint ladder, adaptation by measured mastery.
- References: protocol and rubrics, plan card and fading ladder, explainer rules and the trace-first pipeline, learner model and evidence rules, retention (cards, schedule, quizzes), 12-week roadmap, resources, platforms and the session delta format.
- coach.py: init, status, log (attempt, question, session), concept, card (add, accept, edit, retire, review, list), quiz, due, artifact, snapshot (JOURNEY.md, journey.json, summary.md, technique ledger), export, import, package, install (links and Claude Code hook), validate.
- Notebook seeded with the sliding-window explainer, the questions asked so far and six draft cards.
