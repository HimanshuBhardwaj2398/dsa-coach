"""Two Pointers, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/two-pointers/spec.py"""
from build_explainer import V

TITLE = "Two Pointers, explained"
PITCH = ("Two indices close in from both ends. Each comparison proves that every pair using one of them is finished, "
         "so the n² pairs take at most n − 1 steps.")

SPOT = {
    "idea": [
        "Reach for two pointers when the candidates are **pairs** and one comparison can rule out every pair that uses "
        "one element. Sorted order gives that proof for sums, mirror symmetry gives it for palindromes, and the "
        "shorter wall gives it for container area.",
        "Draw the candidates as the upper triangle of an n × n grid: cell (i, j) is the pair i < j. Brute force reads "
        "every cell. Two pointers stand on one cell and, with one comparison, grey out a whole row or column.",
    ],
    "questions": [
        ("What are the candidates?", "Pairs (i, j) with i < j, or a pair inside a triple once one index is fixed."),
        ("What does one comparison prove?", "If the sum is too small, the left element with any partner up to `r` is smaller still."),
        ("Which element is finished?", "Move that pointer, and only that one."),
        ("What must I keep?", "Usually just `l`, `r` and the best so far: O(1) extra space."),
    ],
    "cases": [
        {"text": "A sorted array; return the indices of two numbers that add up to a target, using O(1) extra space.",
         "options": ["Two pointers from both ends", "A hash map of values seen", "A sliding window"], "answer": 0,
         "why": "Sorted, a pair, a target: a sum that is too small finishes the left element. A hash map also works, but takes O(n) space."},
        {"text": "An unsorted array; return the original indices of two numbers that add up to a target.",
         "options": ["Two pointers from both ends", "A hash map of values seen", "Binary search"], "answer": 1,
         "why": "Without order, a comparison rules nothing out, and sorting would scramble the indices. Remember what you have seen instead."},
        {"text": "The longest substring without a repeated character.",
         "options": ["Two pointers from both ends", "A window whose two ends both move right", "Binary search"], "answer": 1,
         "why": "The candidates are contiguous ranges and the test is about what is inside one: a sliding window."},
        {"text": "Heights of vertical lines; pick two that, with the x-axis, hold the most water.",
         "options": ["Two pointers from both ends", "A monotonic stack", "Dynamic programming"], "answer": 0,
         "why": "Area is capped by the shorter wall. Pairing it with anything closer is narrower and no taller, so the shorter wall is finished."},
        {"text": "Is this string a palindrome once non-letters are ignored?",
         "options": ["Two pointers from both ends", "A hash map of counts", "A stack"], "answer": 0,
         "why": "Mirror positions are compared pairwise; once a pair matches, neither character is needed again."},
        {"text": "Remove duplicates from a sorted array in place and return the new length.",
         "options": ["Two pointers from both ends", "A read pointer and a write pointer, both moving right", "A hash set"], "answer": 1,
         "why": "One pointer reads every item; the other marks where the next kept item goes. Same direction, different speeds."},
    ],
    "near_misses": [
        ("Pair sum on an unsorted array.", "No order, so no proof: use a hash map, or sort first when the indices don't matter (n log n)."),
        ("Subarray sum equals k, with negative numbers.", "Contiguous ranges and negatives: neither end can be ruled out. Prefix sums with a hash map."),
        ("Count the pairs with sum below a target.", "Still two pointers, but when `nums[l] + nums[r] < target` all r − l pairs (l, l+1..r) count at once."),
    ],
}

PARTS = {
    "names": [
        ("l", "the smallest index still in play"),
        ("r", "the largest index still in play"),
        ("s", "`nums[l] + nums[r]`, the one pair being checked"),
    ],
    "plan": [
        ("Start", "`l = 0`, `r = n - 1`: every pair is in play."),
        ("Continue", "while `l < r`: at least one pair is left."),
        ("Move", "`s < target`: `l += 1`. `s > target`: `r -= 1`. Equal: return the pair."),
        ("Stop", "`l` meets `r`: no pair is left, so there is none."),
    ],
    "invariant": "Any pair that sums to the target lies inside [l..r]. Every pair with an index outside has been ruled out.",
    "safe": [
        "If `s < target`: for every j ≤ r, `nums[l] + nums[j] ≤ nums[l] + nums[r] < target`, so no answer uses index l. Drop it: `l += 1`.",
        "If `s > target`: for every i ≥ l, `nums[i] + nums[r] ≥ s > target`, so no answer uses index r. Drop it: `r -= 1`.",
        "Progress: `r - l` shrinks by one every turn, so the loop ends.",
    ],
    "relies_on": "ascending order. On an unsorted array the first bullet is false: one small sum proves nothing about other pairs.",
}


def pair_with_sum(nums, target):
    l, r = 0, len(nums) - 1
    while l < r:
        s = nums[l] + nums[r]
        if s == target:
            return [l, r]
        if s < target:
            l += 1
        else:
            r -= 1
    return []


REFERENCE = pair_with_sum


def view(S):
    nums, l, r = S.v.get("nums") or S.outer["nums"], S.v.get("l"), S.v.get("r")
    if l is None:
        return [V.array("nums", nums), V.vars(("target", S.outer["target"]))]
    n = len(nums)
    out = {i: "done" for i in range(n) if i < l or i > r}
    out.update({l: "cur", r: "cur"} if l < r else {})
    pairs = [[(nums[i] + nums[j] if i < j else None) for j in range(n)] for i in range(n)]
    cls = {(i, j): ("cur" if (i, j) == (l, r) else "done" if i < l or j > r else "")
           for i in range(n) for j in range(n) if i < j}
    return [V.array("nums", nums, {"l": l, "r": r}, out),
            V.vars(("target", S.v["target"]), ("s", S.v.get("s"))),
            V.grid("every pair (i, j): its sum; grey = ruled out", pairs, list(range(n)), list(range(n)), cls)]


def verdict(S):
    s, t = S.v["s"], S.v["target"]
    return "return the pair" if s == t else "l moves right" if s < t else "r moves left"


PREDICT = {
    "if s == target:": {
        "q": lambda S: f"s = {S.s}, target = {S.target}. What happens next?",
        "options": ["return the pair", "l moves right", "r moves left"],
        "answer": lambda S, N: verdict(S),
        "why": lambda S, N: (f"{S.s} < {S.target}: every pair using index {S.l} is at most {S.s}, so index {S.l} is finished."
                             if S.s < S.target else
                             f"{S.s} > {S.target}: every pair using index {S.r} is at least {S.s}, so index {S.r} is finished."
                             if S.s > S.target else "Found it."),
        "times": 4,
    },
    "s = nums[l] + nums[r]": {
        "q": lambda S: f"l = {S.l}, r = {S.r}. What is s?",
        "answer": lambda S, N: N.v["s"],
        "when": lambda S: S.l > 0 or S.r < len(S.nums) - 1,
        "times": 2,
    },
}

ROW_COLS = ["l", "r", "nums[l] + nums[r]", "so"]


def row(S, N):
    if S.text == "if s == target:":
        return [S.l, S.r, f"{S.nums[S.l]} + {S.nums[S.r]} = {S.s}",
                {"return the pair": "found", "l moves right": "too small: l += 1", "r moves left": "too big: r -= 1"}[verdict(S)]]
    return None


def INVARIANT(S):
    nums, t, l, r = S.outer["nums"], S.outer["target"], S.v.get("l"), S.v.get("r")
    if l is None:
        return True
    return not any(nums[i] + nums[j] == t for i in range(len(nums)) for j in range(i + 1, len(nums)) if i < l or j > r)


TRACES = [
    {"label": "[1, 3, 4, 6, 8, 11], target 10", "args": ([1, 3, 4, 6, 8, 11], 10), "expect": [2, 3],
     "about": "Six sorted numbers and a target of 10. Watch which row or column each comparison greys out."},
    {"label": "No pair: [2, 5, 9], target 4", "args": ([2, 5, 9], 4), "expect": [],
     "about": "Every sum is too big, so r walks left until no pair is left."},
]


def brute(nums, target):
    return {(i, j) for i in range(len(nums)) for j in range(i + 1, len(nums)) if nums[i] + nums[j] == target}


def inputs(rng):
    cases = [([], 3), ([5], 5), ([2, 2], 4), ([1, 2], 4), ([-3, -1, 0, 2], -1)]
    for _ in range(400):
        nums = sorted(rng.randint(-6, 12) for _ in range(rng.randint(0, 9)))
        cases.append((nums, rng.randint(-8, 20)))
    return cases


ORACLE = {"brute": brute, "inputs": inputs, "same": lambda got, want: (tuple(got) in want) if want else got == []}

FAMILY_INTRO = "Opposite-end pointers are one member of a family. Every member makes the same move: one comparison proves an element is finished."
FAMILY = [
    {"name": "Pair with a target, sorted input", "change": "The trace above. LeetCode wants 1-based indices: return `[l + 1, r + 1]`.",
     "problems": ["two-sum-ii-input-array-is-sorted"]},
    {"name": "Fix one, pair the rest", "change": [
        "Sort, fix `nums[i]`, then run the pair search on the part to its right for `-nums[i]`. Skip a fixed value equal to the one before it, and after a find move both pointers past equal values, so no triple repeats.",
        "n fixed values × at most n pair steps: O(n²), which beats the n³ of all triples."],
     "problems": ["3sum"]},
    {"name": "Move the limiting side", "change": [
        "Area is `min(h[l], h[r]) * (r - l)`. The shorter wall caps every pair it makes with anything inside, and those pairs are narrower, so the shorter wall is finished: move it.",
        "Trapping Rain Water uses the same idea on running maxima: the side with the lower maximum already knows its water level."],
     "problems": ["container-with-most-water", "trapping-rain-water"]},
    {"name": "Mirror check", "change": "Compare `s[l]` and `s[r]` and move both inward; skip characters the problem ignores before comparing.",
     "problems": ["valid-palindrome"]},
]

COUNT = {
    "line": "s = nums[l] + nums[r]",
    "input": lambda n: (list(range(n)), -1),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n - 1,
    "bound_text": "n − 1",
    "text": ["Each turn drops one index from [l..r], which starts with n indices, so the sum line runs at most n − 1 times. "
             "The worst input never finds a pair. Doubling n doubles the count: linear."],
    "time": "O(n)",
    "space": "O(1): two indices and a sum.",
}

TRAPS = [
    ("`while l <= r`", "lets l equal r, pairing an element with itself."),
    ("Moving both pointers after a miss", "skips pairs nothing has ruled out. Only the finished side moves."),
    ("Running it on unsorted input", "breaks the proof. Sort first and lose the original indices, or use a hash map."),
    ("3Sum without skipping equal values", "returns the same triple more than once."),
]


def checked_pairs(run):
    return ", ".join(f"({s.v['l']}, {s.v['r']})" for s in run["states"] if s.text == "s = nums[l] + nums[r]" and s.kind == "line")


CHECK = {
    "trace": {"text": "Run the same loop on nums = [2, 4, 5, 7, 9, 12] with target = 13. Write the pairs (l, r) it checks, in order, and what it returns.",
              "args": ([2, 4, 5, 7, 9, 12], 13),
              "fields": [("Pairs (l, r) checked, in order", checked_pairs), ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "An unsorted list of 10⁵ numbers; you need any two values that sum to k (the values, not their indices). What keeps two pointers correct?",
         "options": ["Run the loop as it is", "Sort first (n log n), then run the loop", "Move both pointers every turn"], "answer": 1,
         "why": "The safe-move proof needs order, and sorting buys it for n log n. When the original indices matter, a hash map is O(n)."},
        {"q": "Container With Most Water: heights[l] = 3 and heights[r] = 8. Which pointer moves?",
         "options": ["r, because 8 is bigger", "l: every pair of the 3 with anything inside is narrower and no taller", "Both"], "answer": 1,
         "why": "The 3 caps the height of every pair it is in, and moving r inward only narrows them. The 3 is finished."},
    ],
    "own": {"prompt": "When does one comparison let you discard a whole row of pairs, and what does that rely on?",
            "model": "Two pointers fit when the candidates are pairs and one comparison proves an element is finished. With sorted values, a sum that is too small means the left element pairs with nothing bigger than nums[r], so every pair using it is too small too: drop it. That needs order (or symmetry, or a limiting side). Each move drops one index, so the n² pairs take at most n − 1 steps."},
}
