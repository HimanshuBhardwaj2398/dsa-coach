# Changelog

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
