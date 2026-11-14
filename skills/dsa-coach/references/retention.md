# Retention: cards, reviews and quizzes

Understanding a pattern in a session is not the same as producing it in an interview weeks later. Two separate schedules keep it alive: retrieval cards for cues, invariants and complexities, and full re-solves for the procedure itself. Cards don't build procedural fluency, so re-solves keep their own schedule (references/learner-model.md).

## Writing cards in two stages

LLMs left to themselves write shallow term-and-definition cards. Write cards in two stages instead.

**Stage 1, choose targets.** Pick from what actually happened in the session:

- the cue that should trigger the pattern
- the invariant or state definition
- what the solution relies on, and what to use when that's missing (the plan card's Relies on and Breaks if lines)
- a changed constraint from the look-back step, and what it changes
- an edge case he missed
- the reason behind a complexity
- a bug from his own attempt (mistake code)
- a Python trap
- a link to his own work (where would this appear in an LLM serving stack or a RAG pipeline?)

**Stage 2, write each prompt** so it is:

- **focused**: one idea per card
- **precise**: one acceptable answer, not "tell me about sliding windows"
- **consistent**: the same answer every time he reviews it
- **tractable**: answerable in under a minute from memory
- **effortful**: requires recalling, not recognizing

## Card types (the `--type` value)

| Type | Example front | Example back |
|---|---|---|
| trigger | "Shortest substring that contains every char of t, with duplicates. Pattern, and why does it apply?" | "Variable sliding window, shortest-valid template: a window that contains t still contains t when it grows, so the valid region is a staircase." |
| invariant | "In Minimum Window Substring, what does `have` count, and exactly when does it change?" | "Distinct letters c with window[c] ≥ need[c]. +1 when a count reaches need exactly on add; −1 when it drops below need on remove." |
| trap | "`while lo <= hi` vs `while lo < hi` in binary search: when is each correct?" | "`<=` with `hi = n - 1` and `hi = mid - 1`; `<` with `hi = n` and `hi = mid`. Mixing them loops forever or skips an index." |
| complexity | "Why is the sliding window O(n) with a while loop inside a for loop?" | "l and r only move forward, each at most n times, so the while body runs at most n times in total." |
| bug | A snippet from his own attempt: "What's wrong?" | The fix and the mistake code |
| pytrap | "What does `[[0] * 3] * 2` share?" | "Both rows are the same list object; use `[[0] * 3 for _ in range(2)]`." |
| trace | "Sliding window on s = ADOBECODEBANC, t = ABC: what are l and r after the first shrink?" | Values from the executed trace |
| salience | "Where would a monotonic deque show up in an LLM serving stack?" | "Sliding-window maximum over latency samples for autoscaling or rate limits." |

Show him each card when you write it. He says keep, edit or drop, and the ones he keeps are added active, first due the next day. Cards he wrote or edited himself matter more to him, and he decides what's worth remembering. A card that waits as a draft is never reviewed, so `--draft` is only for cards that arrive from a web chat, where he can't decide yet.

```bash
coach.py card add --concept sliding-window --type invariant --front "..." --back "..."
coach.py card edit --id c0004 --back "..."
coach.py card retire --id c0005
coach.py card list --drafts          # from web chats: then card accept --id c0006, or card retire
```

## Card schedule

Accepted cards are first due the next day. After each review the gap grows through 1, 3, 7, 14, 30 and 60 days on a pass and goes back to 1 day on a fail, never exceeding 30% of the days left before the target date. Spacing at all matters more than the exact intervals (expanding and uniform schedules did about equally well in a meta-analysis). A future version can switch to FSRS, which predicts recall better than Anki's older SM-2 for nearly all users.

A card that survives a gap of 5 days or more is very likely to be remembered later (about 95% at the median in Quantum Country's data), so the snapshot reports cards "held at 5+ days".

## Quiz session

1. `coach.py quiz --n 10` shows due card fronts; `--json` adds the answers for grading.
2. Ask one card at a time and wait for his answer before revealing. For trace cards, he writes the state before seeing it.
3. Grade strictly: pass means correct and complete without hints.
4. Record each result with `card review --id ID --grade pass|fail`.
5. Keep it under 20 minutes. If more is due, quiz the oldest due cards first.

## Re-solves vs cards

| | Cards | Re-solves |
|---|---|---|
| Trains | Cues, invariants, complexities, traps | Producing working code under time pressure |
| Takes | Under a minute each | 5 minutes (plan-only) to 25+ minutes (full code) |
| Schedule | 1, 3, 7, 14, 30, 60 days | 1, 3, 7, 14, 30 days |
| Counts toward | Recall stats in the snapshot | Problem and pattern status (re-solves in code only; a plan-only check just keeps the schedule moving) |

## Later (build step 2)

Quiz and test pages will be generated from `cards.json` and published as interactive pages that store his answers. New problems already mix: `coach.py next` interleaves patterns after each pattern's first three problems. Timed "retention tests" will add unlabeled sets of problems he has seen, drawn from several patterns (interleaving helps most when similar patterns sit side by side).
