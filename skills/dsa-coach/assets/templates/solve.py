"""{problem}

{url}
Started {date}.{pattern_line}

Plan card (stage 2):
    State:
    Invariant:
    Relies on:
    Breaks if:
    Termination:
    Complexity:
    Hand trace:
"""
from __future__ import annotations


class Solution:
    # Write the method LeetCode gives you here, e.g. def search(self, nums, target):
    # Build it (stage 3): one step of your plan at a time. Subgoal comments help when you're unsure.
    # The first method is the one the examples call: name helpers _like_this or put them below it.
    pass


# Stage 1: your predicted examples, one per line: ((args, ...), expected). Mark edge cases with "# edge".
# One input needs a trailing comma: (([7, 1, 5, 3, 6, 4],), 5).
EXAMPLES = [
]


if __name__ == "__main__":
    name = next((m for m, v in vars(Solution).items() if not m.startswith("_") and callable(v)), None)
    if name is None:
        print("Write the method inside class Solution first.")
    else:
        for args, expected in EXAMPLES:
            got = getattr(Solution(), name)(*args)
            print("ok  " if got == expected else "FAIL", args, "->", got, "expected", expected)
