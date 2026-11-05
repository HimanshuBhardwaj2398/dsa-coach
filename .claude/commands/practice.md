---
description: Start DSA practice now with one item picked for you
argument-hint: "[pattern or problem]"
---

Use the dsa-coach skill in practice mode (references/protocol.md).

Argument: $ARGUMENTS

1. If `coach.py solve show` reports a live solve, resume it instead.
2. With no argument, run `python3 skills/dsa-coach/scripts/coach.py next --json`.
3. With an argument, run the same command with `--pattern "<argument>"`. If it fails with "unknown pattern", treat the argument as a problem name.
4. For a problem, run `coach.py solve start --problem <slug>` (add `--unlabeled` when `block` is false) and point him to the attempt file.
5. Act on the result now. Skip the session opening and don't ask what he wants to do.
