> **Archived.** Built in 0.2.0 (`/practice`). Kept for history: paths inside are as they were when it was written.

# /practice command design

Date: 2026-11-01. Status: approved. Target version: 0.2.0.

## Problem

Getting from "I feel like practising" to a problem on screen takes too many steps. The notebook has 0 logged attempts on day 3 of the plan. Each session opens with a status report and a proposed plan, the top next step is card admin, and `status` suggests a week 2 sliding-window problem while also listing week 1 patterns.

## Goal

One word starts practice, at any point in a session, with no decision needed from the learner. Everything else the coach does stays the same.

## Experience

`/practice` or saying "practice" prints one line saying what and why, then the first prompt in the same message:

- A problem in a pattern with no attempts opens with the first-step probe (references/protocol.md).
- Any other new problem opens at stage 1 of the solve protocol.
- A due re-solve opens from a blank page, per review mode.
- Due cards open as a quiz, one card at a time.

The normal session opening is skipped. `/practice <pattern>` limits the pick to that pattern. `/practice <problem-slug>` goes straight to that problem. "Where am I?" still gives the full picture.

## Selection

`coach.py next` returns one item, taking the first that applies:

1. Inbox deltas. The coach says what they contain and imports them, as CLAUDE.md requires, then continues with the next item.
2. Due re-solves, oldest first.
3. Due cards.
4. A new problem: order patterns by week, then tier, then roadmap order, and take the first pattern with fewer attempted problems than its `target`. Use its first canonical problem not yet attempted.

If that pattern has no canonical problem left, return the pattern with `problem: null`. The coach then picks an unattempted problem from that NeetCode section, as learn mode already does.

`machine-coding`, `ai-assisted` and `ml-coding` are excluded from the new-problem step. They are long formats started on purpose through their own modes.

With `--pattern KEY`, only step 4 applies, limited to that pattern. An unknown key exits with an error listing the valid keys.

`--json` prints the item as `{"kind": "inbox" | "resolve" | "cards" | "new", ...}`. Plain output is one line.

## Related changes

- A single pick function in `coach.py` feeds `next`, the `status` next steps and JOURNEY.md, so they can't disagree.
- `next_steps` puts practice before draft approval. Inbox import stays first.
- At the end of a practice session, the coach offers to keep all draft cards or go through them. Drafts never block practice.
- SKILL.md gets a `practice` row in the modes table, and an exception to the session opening when practice is requested. CLAUDE.md gets the same exception.
- `.claude/commands/practice.md` runs `coach.py next --json`, passing `$ARGUMENTS`.

## Unchanged

Attempt before answers, predict before reveal, the hint ladder, logging, evidence rules and all notebook file formats.

## Out of scope

Time-boxed sessions, solution file scaffolding, a terminal launcher, and filling in the roadmap's missing problems. Only "getting started" was picked as the blocker.

## Testing

Unit tests in `tests/test_coach.py`, written first:

- Priority order across inbox, re-solves, cards and new problems.
- Plan order: a fresh notebook picks `two-sum`, even with recent sliding-window activity.
- A pattern with no canonical problem left returns `problem: null`.
- `--pattern` limits the pick, and an unknown key errors.
- Excluded patterns are never picked.
- `status` next steps agree with `next`, and practice comes before drafts.

## Release

Per CLAUDE.md: run the tests and `coach.py validate`, bump `metadata.version` and `SKILL_VERSION` to 0.2.0, run `coach.py package`, and record the change in `docs/CHANGELOG.md`.
