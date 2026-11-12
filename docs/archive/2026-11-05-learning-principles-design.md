> **Archived.** Built in 0.3.0. Kept for history: paths inside are as they were when it was written.

# Learning-principles upgrade design

Date: 2026-11-05. Status: approved. Target version: 0.3.0.

## Problem

Three sources were reviewed against the skill:
- *Learning How to Learn* (Oakley and Sejnowski).
- *How to Solve It* (Polya).
- "Programming as Theory Building" (Naur), read through Vecino's "Why LLMs can't make your code simpler".

Most of their advice was already in place. Five gaps remained:

1. `roadmap.md` promises interleaving, but `coach.py next` served a pattern's whole target (9 Arrays & Hashing problems) before starting the next pattern, and every pick named its pattern.
2. Polya's look-back phase was thin. The research brief's "one alternative" never reached stage 8.
3. Nothing tested the theory behind a solution, so a re-solve from memorised code passed.
4. When stuck, the only path was the hint ladder. There was no switch from focused work to a break.
5. The coach is an LLM, and nothing held its own code to the plan card.

The notebook made the behavioural principles the most urgent. On day 7 there were no logged attempts, two explainers had been studied, both concept notes still had an empty Core idea section, and the latest question asked for more examples and animations.

## Goal

Apply the principles with the smallest change that does it: text edits that replace rather than add, plus one tested change to `coach.py next`. The principles and their sources are in `docs/research/learning-principles.md`.

## Changes

**SKILL.md**
- A genuine attempt is one focused block of about 25 minutes (15 for an easy).
- Rule 6 adds recall after a resource.
- New rule 8, keep it simple.
- Sessions are planned in 25-minute blocks, and each ends by agreeing when the next block happens.
- The 8 solve stages are grouped under Polya's four phases:
  - Stage 1 adds the unknown, the data and the condition.
  - Stage 5 adds the datum the solution relies on.
  - Stage 6 adds Relies on / Breaks if.
  - Stage 7 adds a check of each step against the invariant.
  - Stage 8 becomes "test and look back".
- Hint ladder:
  - It starts with "which question would you ask yourself?"
  - Rung 1 is a general Polya question; rung 2 is a nudge specific to the problem.
  - A leading question counts as the rung it gives away.
  - When a block ends unsolved: a break, then another block, the next rung, or park the problem.

**references/protocol.md**
- Polya's question table.
- Stage prompts updated to match.
- Practice mode presents a pattern's problems unlabeled once `block` is false.
- Learn mode saves the core idea in the learner's own words.
- Reviews and mocks add a changed-constraint question.
- Mock mode gets an OA variant: hard start, jump to easy.
- AI drills can plant complexity flaws, and the learner turns down suggestions that don't fit the plan card.
- Machine coding abstracts only around likely changes.
- The rubric is updated, and debugging adds a break after a whole stuck block.

**Plan card** (reference and template)
- New Relies on and Breaks if lines.
- The invariants table gains a "Relies on (otherwise use)" column.

**Other references**
- `explainers.md`: offer an attempt before more examples; the core idea goes into the concept notes.
- `retention.md`: new card targets.
- `roadmap.md`: interleaving as implemented, and spreading the hours over the week.
- `learner-model.md`: the parked-attempt convention.

**coach.py**
- New constant `BLOCK = 3`.
- `pick_new(rows, pattern, week)`:
  1. Finish a started pattern's block first.
  2. Then start the next pattern once its week has come.
  3. Otherwise pick the started pattern practised least recently.
- Picks carry `block`, and pattern rows carry `last_attempt`.
- Status steps for mixed picks don't name the pattern.

**CLAUDE.md, AGENTS.md**: check skill changes against `docs/research/`, and prefer replacing or simplifying rules.

## Unchanged

- Notebook file formats and the session delta format. A parked attempt is an ordinary `partial` attempt with a `parked:` note.
- Evidence rules, schedules, and hint-rung numbering (0–7, unaided at rung 1 or below).
- `next --pattern`.

## Out of scope

The "Not adopted" list in `docs/research/learning-principles.md`:
- memory palaces;
- code metrics;
- Polya's full dictionary;
- a minutes-against-plan metric;
- enforced breaks.

## Testing

Unit tests in `tests/test_coach.py`, written first:
- After a three-problem Arrays & Hashing block, the pick is Two Pointers with `first` and `block` true.
- With both week-1 blocks done, the pick is the pattern practised least recently, with `block` false, and the status step doesn't name it.
- In week 2, Sliding Window starts while Arrays & Hashing is still under target.
- The existing `problem: null` test now uses `--pattern arrays-hashing`.

## Release

Per CLAUDE.md:
- Run the tests and `coach.py validate`.
- Bump `metadata.version` and `SKILL_VERSION` to 0.3.0.
- Run `coach.py package`.
- Record the change in `docs/CHANGELOG.md`.
