# Learner model: the notebook

Everything the coach knows about his progress lives in plain files in the notebook folder, so he can read, edit and version it, and any agent on any platform can use it. Claude's or ChatGPT's own memory should hold only a few stable facts (goal, level, format defaults): opaque memory profiles have been shown to make assistants agree with users more.

## Layout

```text
notebook/
├── config.json            goals, start and target dates, weekly hours, time caps
├── JOURNEY.md             generated snapshot: where he is (never hand-edit)
├── journey.json           the same data for dashboards and other tools (generated)
├── learner/
│   ├── summary.md         ≤60-line plain-text context for any session (generated)
│   ├── attempts.jsonl     one JSON object per attempt
│   ├── questions.jsonl    one JSON object per follow-up question
│   ├── cards.json         retrieval cards with their schedule
│   ├── techniques.json    technique ledger (generated)
│   └── preferences.md     stated preferences: formatting defaults only
├── concepts/<slug>/       notes.md (core idea, plan card, FAQ, changelog) and explainer files
├── problems/<slug>/
│   ├── notes.md           plan card, lesson lines, and the ## Stage notes section that `solve end` writes
│   └── YYYY-MM-DD.py      attempt files from before 0.9.0, when he coded in the study app (kept as history)
├── sessions/YYYY-MM-DD.md session logs
├── sessions/current.json  the live solve, if any (`coach.py solve`; deleted by `solve end`)
├── artifacts/registry.json saved explainers and published pages
├── inbox/                 session deltas from web chats, waiting for `coach.py import`
├── exports/               context packs for web chats (`coach.py export`)
└── feedback.jsonl         his notes about the coach and its tools (`coach.py log feedback`)
```

Write through `scripts/coach.py` so IDs, dates and schedules stay consistent. Hand edits to notes are fine; hand edits to the JSON files should keep the fields below.

## Attempts (`learner/attempts.jsonl`)

| Field | Values | Meaning |
|---|---|---|
| id | a0001… | Assigned by the CLI |
| date | YYYY-MM-DD | Day of the attempt |
| problem | slug | e.g. `minimum-window-substring` (LeetCode slug when there is one) |
| pattern | key | A key from `assets/roadmap.json`, e.g. `sliding-window` |
| difficulty | easy, medium, hard | Sets the time cap for "ready" |
| mode | learn, practice, review, mock, ai, machine | How the attempt was run |
| outcome | solved, partial, failed | Solved means all tests pass (for a plan-only check: the plan was right and complete) |
| minutes | integer | Time he worked: the focus blocks, each counted up to its length, or his own figure when a block ran well past it |
| hints | 0–7 | Highest hint-ladder rung used |
| assisted | true, false | Saw a solution, used rung 5 or higher, or AI mode |
| confidence | 1–5 or null | His confidence **before** starting |
| technique | name or null | How the pattern was taught in this session (list below) |
| mistakes | list of codes | Mistake codes (list below) |
| complexity_stated | true, false | Stated time and space complexity correctly |
| plan_only | true, false | A re-solve checked as a plan, with no code written |
| note | text | One-line lesson |
| skill_version | text | Version of this skill when logged |

An attempt is **unaided** when it is solved, not assisted, and used hint rung 0 or 1. Rung 1 is a general question he could have asked himself.

A **plan-only check** that passes keeps the review schedule moving like any unaided attempt. It earns no status and credits no technique: those take an unaided solve in code.

A **parked** attempt is one he stepped away from after a focused block (see the hint ladder in SKILL.md). Log it as `partial`, with the rung reached so far and a note starting `parked:`. The schedule brings it back the next day as a due re-solve, and a later unaided solve counts as usual.

## Statuses

Problem status:

| Status | Rule |
|---|---|
| learning | Attempted, no unaided solve in code yet |
| practicing | At least one unaided solve in code |
| retained | An unaided solve in code at least 3 days after the first attempt |
| ready | A delayed unaided solve in code (3+ days after the first attempt) that was also within the time cap (easy 15, medium 25, hard 40 minutes), with complexity stated, in practice, review or mock mode |

Pattern status: `not started` (nothing logged), `exploring` (concepts, questions or explainers but no attempts), `learning`, `practicing` (at least one problem practicing), `retained` (at least two problems retained), `ready` (at least three problems ready, or all of them if the NeetCode section has fewer). "Interview-ready" for a pattern should also be confirmed on unseen problems in mocks.

## Review schedule for problems

After each attempt the next re-solve is due after 1, 3, 7, 14 or 30 days, by the number of consecutive unaided solves (0 → 1 day, 1 → 3, 2 → 7, 3 → 14, 4+ → 30). Any attempt that isn't unaided resets it to 1 day. No gap is longer than 30% of the days left before the target date.

Each due re-solve carries a `check`. It is `code` until the problem is retained, and after any attempt that wasn't an unaided solve in code; otherwise it is `plan`. So once a problem is retained, full re-solves and plan-only checks alternate. `coach.py next` serves at most three re-solves a day, then moves on to cards and new problems.

## Mistake codes

| Code | Meaning |
|---|---|
| comp | Misread the problem or the constraints |
| pattern | Picked the wrong pattern or missed the cue |
| invariant | Wrong or vague state definition or invariant |
| boundary | Off-by-one, loop bounds, empty ranges |
| edge | Missed an edge case (empty, duplicates, negatives, large input) |
| pytrap | Python pitfall: `[[0]*n]*m` aliasing, mutable default arguments, `heapq` being a min-heap, recursion limit, `//` with negatives |
| complexity | Wrong or missing complexity analysis |
| impl | Implementation slip not covered above |
| process | Skipped a stage: coded before planning, no tests |
| comm | Didn't explain the approach clearly (mocks) |

Every logged mistake should change practice: a trap card, a confusable-pair problem, or an earlier re-solve.

## Technique names

`explainer-predict` (interactive explainer with predictions), `worked-example`, `faded-example`, `hint-ladder`, `plan-card`, `contrast-pair`, `lead-reveal` (guided questioning), `analogy` (to ML or production systems), `reading` (an external resource), `none`.

## Evidence rules

1. **A technique earns credit only from delayed outcomes.** When he re-solves a problem at least 3 days after an attempt where a technique was used, that technique gets one success if the re-solve was unaided and one failure otherwise. AI drills never count. The ledger keeps successes and trials per technique and pattern, with a Beta(1, 1) estimate.
2. **Small numbers are provisional.** Treat any technique with fewer than 3 delayed checks as provisional. Change a default only when a challenger clearly wins over about three delayed comparisons, and keep trying other techniques about a fifth of the time.
3. **Preferences are not evidence.** Stated preferences live in `preferences.md` and set formatting defaults only. A preference becomes a teaching default only if it is not worse on delayed outcomes.
4. **Counts, dates and IDs, never adjectives.** Write "3 of 4 delayed re-solves passed (a0012, a0019, a0023)", never "great at graphs".
5. **Confidence is for calibration.** Compare confidence before an attempt with the outcome. High-confidence failures are the most valuable to revisit, because errors made with high confidence are especially likely to be corrected after feedback.

## Signals, strongest first

| Signal | What it predicts | How it's used |
|---|---|---|
| Unaided re-solve after 3+ days, within the time cap, complexity stated | Durable skill | Promotes status; the only way a technique earns credit |
| Delayed card recall | Recall of cues, invariants, complexities | Card schedule |
| First unaided attempt, hint rung used | Current skill (inflated by recency) | Scaffolding for the next problem only |
| Prediction accuracy in explainers | Accuracy of his mental model | Finds misconceptions, creates trap cards |
| Confidence vs outcome | Calibration | Weekly report; high-confidence errors queued |
| "Didn't land" flags, clarity ratings | How an explanation felt | Triggers a rewrite and an eval case, never a reward |
| Stated format preference | Nothing about learning | Formatting defaults only |

## Feedback notes (`feedback.jsonl`)

What he, or the coach, noticed about the coach and its tools. A note is about the product, not about his learning, and nothing in the journey reads it. Each row has an id (`f0001`…), the date, who raised it (`learner` or `coach`), an optional area, the text, the skill version, and `during` (problem, stage and rung) when a solve was live. Notes wait there until the next triage between versions.
