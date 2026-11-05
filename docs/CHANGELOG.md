# Changelog

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
