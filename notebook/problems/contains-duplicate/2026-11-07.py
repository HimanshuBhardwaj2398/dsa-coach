"""contains-duplicate

https://leetcode.com/problems/contains-duplicate/
Started 2026-11-07. Pattern: Arrays & Hashing.

Plan card (stage 6):
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
    def containsDuplicate(self, nums: list[int]) -> bool:
        # 1. Track values we've already passed
        seen: set[int] = set()
        # 2. Scan once; a value already in seen is a duplicate
        for x in nums:
            if x in seen:
                return True
            seen.add(x)
        # 3. Finished the scan without a repeat, so all values are distinct
        return False


# Stage 1: your predicted examples, one per line: ((args, ...), expected). Mark edge cases with "# edge".
# One input needs a trailing comma: (([7, 1, 5, 3, 6, 4],), 5).
EXAMPLES = [
    (([1,2,3,4],), False),  # edge
    (([1,1,2,2,3,4,5,6],), True),
    (([4],), False),  # edge
]


if __name__ == "__main__":
    name = next((m for m, v in vars(Solution).items() if not m.startswith("_") and callable(v)), None)
    if name is None:
        print("Write the method inside class Solution first.")
    else:
        for args, expected in EXAMPLES:
            got = getattr(Solution(), name)(*args)
            print("ok  " if got == expected else "FAIL", args, "->", got, "expected", expected)
