"""Prefix Sums, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/prefix-sums/spec.py"""
from itertools import accumulate

from build_explainer import V

TITLE = "Prefix Sums, explained"
PITCH = ("Any range sum is a difference of two running totals. Store the totals you have passed, and a question about "
         "every subarray ending here becomes one lookup.")

SPOT = {
    "idea": [
        "A **prefix sum** `P[i]` is the sum of the first i values, with `P[0] = 0`. The sum of `nums[l..r]` is "
        "`P[r + 1] - P[l]`: two running totals, one subtraction.",
        "That turns \"which subarrays sum to k?\" into \"which earlier totals equal `total - k`?\". A hash map from "
        "total to how often it appeared answers that for every subarray ending at the current index, in one lookup. "
        "Unlike a sliding window, it doesn't care whether values are negative.",
    ],
    "questions": [
        ("Is the question about contiguous ranges?", "Sums, counts or remainders of `nums[l..r]`."),
        ("Can the range be written as a difference?", "`sum(l..r) = P[r + 1] - P[l]`, so fix the end and look up the start."),
        ("What do I look up?", "The earlier total that would make the difference right: `total - k`, or the same remainder mod k."),
        ("Count, earliest index, or just existence?", "That decides what the map stores: counts, first index, or a set."),
    ],
    "cases": [
        {"text": "Answer 10⁴ queries for the sum of nums[l..r] on a fixed array.",
         "options": ["Prefix sums", "Sliding window", "Sum the range on each query"], "answer": 0,
         "why": "Build P once in O(n); each query is `P[r + 1] - P[l]`, O(1)."},
        {"text": "Count the subarrays whose sum is k; values can be negative.",
         "options": ["Sliding window", "Prefix sums with a map of counts", "Sort, then two pointers"], "answer": 1,
         "why": "Negatives break the window's rule for which end to move. Totals don't care: count earlier totals equal to `total - k`."},
        {"text": "All values are positive. Find the shortest subarray with sum at least k.",
         "options": ["A sliding window", "Prefix sums with a map", "Binary search on the answer only"], "answer": 0,
         "why": "With positive values, growing the window raises the sum and shrinking lowers it, so a window works in O(1) space."},
        {"text": "Does any subarray of length at least 2 sum to a multiple of k?",
         "options": ["Prefix remainders, with the first index of each", "A hash set of values", "A heap"], "answer": 0,
         "why": "Two totals with the same remainder mod k differ by a multiple of k. Keep the first index of each remainder to check the length."},
        {"text": "Product of the array except self, without division.",
         "options": ["Prefix and suffix products", "A hash map of counts", "Two pointers from both ends"], "answer": 0,
         "why": "The product of everything except i is (product left of i) × (product right of i): two running products."},
        {"text": "Sum of a sub-rectangle of a matrix, for many queries.",
         "options": ["2-D prefix sums", "BFS from the corner", "A sliding window per row only"], "answer": 0,
         "why": "`P[r][c]` holds the sum above and left of (r, c); a rectangle is four lookups with inclusion–exclusion."},
    ],
    "near_misses": [
        ("Maximum subarray sum.", "Prefix sums work (subtract the smallest total so far), but Kadane's running sum is the same idea with less to keep."),
        ("Positive values and a target sum.", "A sliding window answers it in O(1) extra space; save the map for when values can be negative."),
        ("A sum over a non-contiguous choice.", "Subsets aren't ranges: that is DP or backtracking."),
    ],
}

PARTS = {
    "names": [
        ("total", "the prefix sum through the current index: `P[i + 1]`"),
        ("seen", "how many times each earlier total has appeared, starting with `{0: 1}` for the empty prefix"),
        ("total - k", "the earlier total a subarray ending here would need to start after"),
    ],
    "plan": [
        ("Start", "`seen = {0: 1}`, `total = count = 0`."),
        ("Each value", "add it to `total`; add `seen[total - k]` to `count`; then record `total` in `seen`."),
        ("Order", "count before recording, so a subarray is never empty."),
        ("Stop", "after the last value: `count` holds every subarray."),
    ],
    "invariant": "Before the lookup at index i, `seen` holds the totals P[0..i], and `count` holds the subarrays inside nums[:i] that sum to k.",
    "safe": [
        "A subarray `nums[j..i]` sums to k exactly when `P[i + 1] - P[j] = k`, that is when `P[j] = total - k`. So `seen[total - k]` is the number of subarrays ending at i.",
        "`seen` starts with `{0: 1}` because `P[0] = 0`: a subarray that starts at index 0 needs it.",
        "Recording `total` after the lookup keeps j ≤ i: the current total can only start later subarrays.",
    ],
    "relies_on": "addition being undone by subtraction. It works for any integers, negative ones included. For products, zeros break the division; use prefix and suffix products instead.",
}


def count_subarrays(nums, k):
    seen = {0: 1}
    total = count = 0
    for i, x in enumerate(nums):
        total += x
        count += seen.get(total - k, 0)
        seen[total] = seen.get(total, 0) + 1
    return count


REFERENCE = count_subarrays


def view(S):
    nums, k = S.outer["nums"], S.outer["k"]
    i = S.v.get("i")
    cls = {} if i is None else {j: ("cur" if j == i else "done" if j < i else "") for j in range(len(nums))}
    out = [V.array("nums", nums, {"i": i}, cls)]
    upto = 0 if i is None else i + (1 if "total" in S.v and S.text != "total += x" else 0)
    prefixes = [0] + list(accumulate(nums))[:upto]
    out.append(V.array("prefix totals P passed so far", prefixes, labels=[f"P{j}" for j in range(len(prefixes))]))
    if "seen" in S.v:
        need = S.v["total"] - k if "total" in S.v else None
        out.append(V.mapping("seen: total → times", S.v["seen"], need))
        out.append(V.vars(("k", k), ("total", S.v.get("total")), ("total - k", need), ("count", S.v.get("count"))))
    return out


PREDICT = {
    "count += seen.get(total - k, 0)": {
        "q": lambda S: f"total = {S.total}, so total − k = {S.total - S.k}. How many subarrays end at index {S.i}?",
        "answer": lambda S, N: S.seen.get(S.total - S.k, 0),
        "why": lambda S, N: f"seen holds {S.total - S.k} {S.seen.get(S.total - S.k, 0)} time(s): each is a start after which the sum is exactly {S.k}.",
        "times": 4,
    },
}

ROW_COLS = ["i", "x", "total", "total − k", "found here", "count"]


def row(S, N):
    if S.text == "count += seen.get(total - k, 0)":
        return [S.i, S.x, S.total, S.total - S.k, S.seen.get(S.total - S.k, 0), N.v["count"]]
    return None


def brute(nums, k):
    return sum(1 for l in range(len(nums)) for r in range(l, len(nums)) if sum(nums[l:r + 1]) == k)


def INVARIANT(S):
    if S.text != "count += seen.get(total - k, 0)":
        return True
    nums, k, i = S.outer["nums"], S.outer["k"], S.v["i"]
    prefixes = [0] + list(accumulate(nums))[:i]
    want = {}
    for p in prefixes:
        want[p] = want.get(p, 0) + 1
    return S.v["seen"] == want and S.v["count"] == brute(nums[:i], k)


TRACES = [
    {"label": "[1, 2, 1, -1, 2, 1], k = 3", "args": ([1, 2, 1, -1, 2, 1], 3),
     "about": "Count the subarrays that sum to 3. A negative value is in the middle, so a sliding window would get lost."},
    {"label": "[0, 0, 0], k = 0", "args": ([0, 0, 0], 0), "expect": 6,
     "about": "Every subarray sums to 0. Watch one total appear several times, and count each earlier appearance."},
]


def inputs(rng):
    cases = [([], 0), ([5], 5), ([5], 0), ([0, 0], 0), ([-1, 1], 0), ([1, -1, 1, -1], 0)]
    for _ in range(400):
        cases.append(([rng.randint(-4, 5) for _ in range(rng.randint(0, 9))], rng.randint(-4, 8)))
    return cases


ORACLE = {"brute": brute, "inputs": inputs}

FAMILY_INTRO = "Every member writes a range as a difference of two running values, then looks the other one up."
FAMILY = [
    {"name": "Range queries on a fixed array", "change": "Build `P` once; a query is `P[r + 1] - P[l]`. No map needed.",
     "problems": ["range-sum-query-immutable"]},
    {"name": "Count ranges with a target sum", "change": "The trace above: a map from total to count, looked up at `total - k`.",
     "problems": ["subarray-sum-equals-k"]},
    {"name": "Same remainder, earliest index", "change": "Store `total % k → first index`. A repeat remainder at least two indices later means a subarray summing to a multiple of k. Start with `{0: -1}`.",
     "problems": ["continuous-subarray-sum"]},
    {"name": "Products from both sides", "change": "`answer[i]` = product of everything left of i × product of everything right of i: one pass left to right, one right to left.",
     "problems": ["product-of-array-except-self"]},
]

COUNT = {
    "line": "total += x",
    "input": lambda n: ([1] * n, 2),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n,
    "bound_text": "n",
    "text": ["The loop body runs once per value, and each line in it costs O(1) on average (a dict lookup or store). "
             "So the sum line runs n times and decides the Big-O: doubling n doubles it. Brute force sums every one of "
             "the n(n + 1)/2 ranges."],
    "time": "O(n) on average (dict operations are O(1) on average).",
    "space": "O(n): up to n + 1 different totals in the map.",
}

TRAPS = [
    ("Starting with an empty map", "misses every subarray that starts at index 0. `seen = {0: 1}`."),
    ("Recording before looking up", "counts the empty subarray when k = 0."),
    ("A sliding window with negative values", "has no rule for which end to move; totals do."),
    ("`P[r] - P[l]` for nums[l..r]", "drops the last value. With `P[0] = 0` it is `P[r + 1] - P[l]`."),
]


def counts_after(run):
    return ", ".join(str(s.v["count"]) for s in run["states"] if s.kind == "line" and s.text == "seen[total] = seen.get(total, 0) + 1")


CHECK = {
    "trace": {"text": "Run the loop on nums = [2, -1, 1, 2] with k = 2. Write count after each value, in order, and the return value.",
              "args": ([2, -1, 1, 2], 2),
              "fields": [("count after each value", counts_after), ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "All values are positive and you want the longest subarray with sum ≤ k. Which is the better tool?",
         "options": ["Prefix sums with a map", "A sliding window", "Sorting first"], "answer": 1,
         "why": "Positive values make the window's moves safe, and it needs O(1) space. The map is for when values can be negative."},
        {"q": "Why does `seen` start as `{0: 1}`?",
         "options": ["To avoid a KeyError", "So a subarray starting at index 0 is counted", "Because k is never 0"], "answer": 1,
         "why": "A subarray `nums[0..i]` needs `P[0] = 0` as its earlier total."},
    ],
    "own": {"prompt": "Why does looking up total − k count the subarrays that end at the current index?",
            "model": "A subarray nums[j..i] sums to k exactly when the running total at i minus the running total before j equals k, so the earlier total must be total − k. The map counts how often each earlier total appeared, so one lookup counts every start that works. Counting before recording keeps the subarray non-empty, and {0: 1} stands for the empty prefix, so subarrays from index 0 are counted."},
}
