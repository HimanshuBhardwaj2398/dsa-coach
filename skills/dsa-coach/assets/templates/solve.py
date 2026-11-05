"""{problem}

{url}
Started {date}.{pattern_line}

Plan card (stage 6):
    State:
    Invariant:
    Relies on:
    Breaks if:
    Termination:
    Complexity:
    Hand trace:
"""


class Solution:
    # Write the method LeetCode gives you here, e.g. def search(self, nums, target):
    # Subgoal comments first (stage 7), then the code under each one.
    pass


# Stage 1: your predicted examples, one per line: ((args, ...), expected). Mark edge cases with "# edge".
EXAMPLES = [
]


if __name__ == "__main__":
    name = next((m for m in vars(Solution) if not m.startswith("_")), None)
    if name is None:
        print("Write the method inside class Solution first.")
    else:
        for args, expected in EXAMPLES:
            got = getattr(Solution(), name)(*args)
            print("ok  " if got == expected else "FAIL", args, "->", got, "expected", expected)
