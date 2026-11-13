Triaged through f0000.

# Backlog

What the coach and its tools should change, and when. Raw feedback notes live in `notebook/feedback.jsonl` (`coach.py log feedback`, or `/note` in Claude Code). This file is what they become after triage.

## The test period

A test period is a stretch of real study sessions on one unchanged version. It lasts until at least 10 sessions and 14 days have passed.

**Test period 1** is on 1.0.0. It starts with the first attempt logged under that version (`skill_version` in `attempts.jsonl`).

While it runs, the product is frozen. The one exception is a fix for something that blocks a session or corrupts the record. Everything else becomes a feedback note.

1.0 is proven when the period ends with all of these true:

- Every session started with `/practice` and reached its first prompt with no workaround.
- Every solve that was started was ended, and no live solve is more than a day old.
- At least 5 delayed re-solves in code are logged, so the technique ledger has its first rows.
- At least 10 cards are active, each reviewed at least once.
- `docs/coach-check.md` passes 8 of 8.

## Triage

Triage happens at the end of a test period, in a session that isn't a study session.

1. Read the notes after the id on this file's first line.
2. Read what the notebook shows about the product over the period: sessions a week, solves started against solves ended, minutes to finish a solve, the count of due re-solves over time, the hint rungs used, cards kept against cards reviewed.
3. Group the notes that point at the same thing. Put each group in one of the three lists below, as one line that names the note ids behind it and the evidence.
4. Update the first line to the last id read.

An item goes into Next version only with two notes behind it, or one note and evidence from the notebook. Check each against `docs/research/`, and prefer removing or replacing something to adding to it. Next version holds at most five items. The changelog entry for a release names the note ids it answers.

## Next version

Nothing yet. The first triage fills this.

## Later

Seeded from the critique of 2026-11-13 (0.9.4), before any notes existed. Each waits for evidence from the test period.

- **Explainers built from tested parts.** The trace-first pipeline in `references/explainers.md` is still done by hand, so the four saved pages share no structure and run from 11 KB to 326 KB. Leftovers to clear with it: an empty `concepts/binary-search/trace.json`, a template and `reference.py` in `concepts/arrays-hashing/`, and the heap page's source in an untracked `output/` folder.
- **Predictions on explainer pages reach the notebook.** The learner model lists prediction accuracy as a signal, and nothing records it. No `trace` card exists yet either.
- **An eval harness for the teaching.** `docs/coach-check.md` is run by hand. Automate it once the eight situations have caught something real.
- **Self-reported attempts from before the coach.** a0001 (two-sum) counts as an unaided solve on his word alone. Its due re-solve will replace it with an observed one; decide then whether priors need their own mark.
- **Fewer commands for the coach to remember in a solve.** About a dozen per solve today. Three focus blocks in the first live solve ran to their cap with no `solve break`.
- **A sign that a focus block is over, outside the pane.** Only the pane says so today.
- **`status` as a pure read.** It rewrites four generated files at every session start, so the notebook is changed every day whether or not he studied.
- **The two new thresholds.** Three re-solves a day (`REVIEWS_PER_DAY`) and three minutes of grace on a focus block (`OVERRUN_GRACE`) are design choices, not tested values.
- **FSRS for the card schedule**, in place of the fixed ladder.
- **Feedback notes in session deltas**, so a web chat can send them back.
- **The course layer and testers**: goal intake, a placement diagnostic, a notebook that lives apart from the product's repo, and a skill that doesn't name one learner.
- **Remove the old Solve tab's draft recovery** from the learning app after 2026-12-10, as its changelog entry says.

## Declined

Nothing yet. Each entry here gets its reason, so the same idea isn't argued twice.
