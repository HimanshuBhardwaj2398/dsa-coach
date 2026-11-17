Triaged through f0018.

# Backlog

What the coach and its tools should change, and when. Raw feedback notes live in `notebook/feedback.jsonl` (`coach.py log feedback`, or `/note` in Claude Code). This file is what they become after triage.

## The test period

A test period is a stretch of real study sessions on one unchanged version. It lasts until at least 10 sessions and 14 days have passed.

**Test period 1** ran on 1.0.1. It began with the first attempt under that version (2026-11-17) and ended the same day, after one session: he chose to build every open note (f0010–f0018) at once, without a triage. That built 1.1.0.

**Test period 2** is on 1.1.0. It starts with the first attempt logged under that version (`skill_version` in `attempts.jsonl`).

While it runs, the product is frozen. The one exception is a fix for something that blocks a session or corrupts the record. Everything else becomes a feedback note.

The version is proven when the period ends with all of these true:

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

Seeded from the critique of 2026-11-13 (0.9.4), before any notes existed, and from the browser test of 2026-11-16. Each waits for evidence from the test period.

- **What 1.1.0 took out of a solve (f0015–f0018).** Stage 1 (restate, predict outputs) is gone and the coach now gives the look-back answers in the last stage. The research behind both (predicting outputs: 53% → 76% correct completion; Polya's look back; generation over reading) is in `docs/research/`, and the one solve under 1.0.1 had its restatement catch a misread goal. At the next triage, read the record for misreads that cost a block and for lessons that didn't survive to the re-solve.
- **The four hand-built explainers on the spec pipeline.** Arrays & Hashing, Sliding Window, Stack and Binary Search predate `build_explainer.py` and share none of its structure. Leftovers: an empty `concepts/binary-search/trace.json`, a template and `reference.py` in `concepts/arrays-hashing/`, and the old heap page (`heap-explorer.html`, `reference.py`, `trace.json` in `concepts/heap/`), which the built heap page replaced as the pattern's explainer.
- **Explainers for the three formats** (machine coding, AI-assisted coding, ML coding). f0013 asked for every pattern; these are timed rounds practised in chat, and the app shows no explainer for them. A page on how to run each round would be a different kind of page.
- **An MCP server for the coach (f0011, f0012).** Discussed 2026-11-17: the panel stays; a local server adds nothing where `coach.py` runs. Revisit as skill + MCP together (ARCHITECTURE.md step 5) once the technique ledger has rows that aren't provisional and he studies in the Claude app.
- **Predictions on explainer pages reach the notebook.** The learner model lists prediction accuracy as a signal, and nothing records it. No `trace` card exists yet either. The "core idea" box on the Arrays & Hashing page is not remembered through the app, because the sandbox has no storage.
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
- **A tab title for each view.** It is "DSA Coach" everywhere (f0009).
- **What "Blind 75 1/8" counts.** It is problems solved unaided, shown beside rows that say "last: solved" (f0009). A wording decision.
- **`check_app.py` failed once** with a Playwright error, on its first run after the 1.0.1 scroll change. The next 15 runs passed and the error text wasn't kept. If it fails again, keep the whole output.

## Declined

Nothing yet. Each entry here gets its reason, so the same idea isn't argued twice.
