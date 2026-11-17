"""1-D Dynamic Programming, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/1d-dp/spec.py"""
from functools import lru_cache
from itertools import combinations

from build_explainer import V

TITLE = "1-D Dynamic Programming, explained"
PITCH = ("Name the subproblem, write how it is built from smaller ones, and fill a table in an order where every "
         "cell it reads is already there. Each subproblem is solved once.")

SPOT = {
    "idea": [
        "Dynamic programming fits when a problem asks for a **best value or a count**, its answer can be built from the "
        "answers to **smaller versions** of itself, and those smaller versions **repeat** (plain recursion would solve "
        "them again and again). Then solve each one once and keep it in a table.",
        "Write it in five lines before coding (SRTBOT, from MIT 6.006): the **S**ubproblem in words ('`dp[i]` = the most "
        "loot from houses 0..i'), the **R**elation between subproblems, a **T**opological order to fill them in, the "
        "**B**ase cases, the **O**riginal problem's cell, and the **T**ime. Most 1-D problems read either the last one "
        "or two cells (take or skip), or every earlier cell (best over all choices).",
    ],
    "questions": [
        ("What is dp[i], in words?", "'The most loot from the first i houses', 'the fewest coins for amount i'."),
        ("What is the last decision?", "Rob house i or not; which coin was used last; where the last word starts."),
        ("Which cells does dp[i] read?", "Only smaller ones, so filling left to right works."),
        ("Count or best?", "Counts add over the choices; best takes max or min."),
    ],
    "cases": [
        {"text": "The most money from houses in a row without robbing two neighbours.",
         "options": ["DP: rob i plus dp[i − 2], or skip and keep dp[i − 1]", "Greedy: take every other house", "Backtracking"], "answer": 0,
         "why": "Two choices per house, each building on a smaller prefix; every-other-house fails on [2, 1, 1, 2]."},
        {"text": "The fewest coins to make an amount, with arbitrary coin values.",
         "options": ["Greedy: largest coin first", "DP over amounts: 1 + min over coins of dp[amount − coin]", "Binary search"], "answer": 1,
         "why": "The last coin is one of the coins; the rest is a smaller amount solved the same way."},
        {"text": "List every way to climb n stairs.",
         "options": ["DP", "Backtracking", "Two pointers"], "answer": 1,
         "why": "Listing them all is exponential output: backtracking. Counting them is DP."},
        {"text": "Can a string be split into dictionary words?",
         "options": ["DP over prefixes: dp[i] true if some word ends at i after a true dp[j]", "A trie only", "A stack"], "answer": 0,
         "why": "The last word ends at i; the prefix before it is a smaller instance of the same question."},
        {"text": "The longest strictly increasing subsequence.",
         "options": ["DP: dp[i] = 1 + max dp[j] over j < i with nums[j] < nums[i]", "Sliding window", "Sort the array"], "answer": 0,
         "why": "Best ending at i reads every earlier cell: O(n²), or O(n log n) with patience sorting."},
        {"text": "The largest product of a contiguous subarray.",
         "options": ["Track both the largest and smallest product ending at i", "Prefix sums", "A heap"], "answer": 0,
         "why": "A negative number swaps them, so keep both: two numbers per step."},
    ],
    "near_misses": [
        ("All combinations or paths themselves.", "Exponential output: backtracking. DP only counts or optimises."),
        ("A greedy choice with an exchange argument.", "Jump Game needs only the farthest reach; DP would work but is slower."),
        ("Two sequences, or a grid.", "Two indices: 2-D DP."),
    ],
}

PARTS = {
    "names": [
        ("dp[i + 2]", "the most loot from houses 0..i (two padding cells at the front stand for 'no houses')"),
        ("dp[i + 1]", "skip house i: the best from houses 0..i − 1"),
        ("dp[i] + money", "rob house i: it adds to the best from houses 0..i − 2"),
    ],
    "plan": [
        ("Subproblem", "`dp[i + 2]` = the most loot from houses 0..i."),
        ("Relation", "`dp[i + 2] = max(dp[i + 1], dp[i] + nums[i])`: skip or rob."),
        ("Order", "left to right: each cell reads the two before it."),
        ("Base, answer", "`dp[0] = dp[1] = 0` (no houses); the answer is `dp[-1]`."),
    ],
    "invariant": "Before house i, every cell dp[0..i + 1] holds the true best for its prefix.",
    "safe": [
        "In any best plan for houses 0..i, house i is robbed or it isn't. Not robbed: the rest is a best plan for 0..i − 1. Robbed: house i − 1 isn't, so the rest is a best plan for 0..i − 2.",
        "Both of those cells were filled earlier, so `max` of the two choices is the best for 0..i.",
        "Each cell is filled once from two lookups: O(n), where plain recursion branches twice per house: O(2ⁿ).",
    ],
    "relies_on": "optimal substructure (a best plan's parts are best plans) and overlapping subproblems. If the choice at i depended on more than the last two houses, the state would need more."
}


def rob(nums):
    dp = [0] * (len(nums) + 2)
    for i, money in enumerate(nums):
        dp[i + 2] = max(dp[i + 1], dp[i] + money)
    return dp[-1]


def coin_change(coins, amount):
    dp = [0] + [amount + 1] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return dp[amount] if dp[amount] <= amount else -1


REFERENCE = rob


def view(S):
    if S.func == "coin_change":
        dp, a, c, amount = S.v.get("dp"), S.v.get("a"), S.v.get("c"), S.outer["amount"]
        if dp is None:
            return [V.vars(("coins", S.outer["coins"]), ("amount", amount))]
        shown = [x if x <= amount else "∞" for x in dp]
        cls = {j: "done" for j in range(len(dp)) if a is not None and j > a}
        if a is not None:
            cls[a] = "cur"
            if c is not None and c <= a and S.text in ("if c <= a:", "dp[a] = min(dp[a], dp[a - c] + 1)"):
                cls[a - c] = "win"
        return [V.array("dp[a]: fewest coins for amount a (∞: not yet possible)", shown, {"a": a, "a − c": a - c if (a is not None and c is not None and c <= a) else None}, cls),
                V.vars(("coins", S.outer["coins"]), ("c", c))]
    nums, dp, i = S.outer["nums"], S.v.get("dp"), S.v.get("i")
    out = [V.array("nums: money in each house", nums, {"i": i}, {j: ("cur" if j == i else "done" if i is not None and j < i else "") for j in range(len(nums))})]
    if dp is not None:
        labels = ["none", "none"] + [f"0..{j}" for j in range(len(nums))]
        cls = {}
        if i is not None:
            cls = {i + 1: "win", i: "win", i + 2: "cur"}
        out.append(V.array("dp: best loot from the houses named above each cell", dp, cls=cls, labels=labels))
    return out


def say(S, N):
    if S.text == "dp[i + 2] = max(dp[i + 1], dp[i] + money)":
        skip, take = S.dp[S.i + 1], S.dp[S.i] + S.money
        return f"Skip house {S.i}: {skip}. Rob it: {S.dp[S.i]} + {S.money} = {take}. Keep {max(skip, take)}."
    if S.text == "dp[a] = min(dp[a], dp[a - c] + 1)":
        before, via = S.dp[S.a], S.dp[S.a - S.c] + 1
        amount = S.outer["amount"]
        fmt = lambda x: "∞" if x > amount else x
        return f"Last coin {S.c}: dp[{S.a - S.c}] + 1 = {fmt(via)}, against {fmt(before)}. dp[{S.a}] = {fmt(N.v['dp'][S.a])}."
    return None


PREDICT = {
    "dp[i + 2] = max(dp[i + 1], dp[i] + money)": {
        "q": lambda S: f"House {S.i} holds {S.money}. Skip: {S.dp[S.i + 1]}. Rob: {S.dp[S.i]} + {S.money}. What is the new cell?",
        "answer": lambda S, N: N.v["dp"][S.i + 2],
        "why": "The larger of the two choices.",
        "times": 3,
    },
    "dp[a] = min(dp[a], dp[a - c] + 1)": {
        "q": lambda S: f"Amount {S.a}, coin {S.c}: dp[{S.a - S.c}] = {S.dp[S.a - S.c] if S.dp[S.a - S.c] <= S.outer['amount'] else '∞'}. Does this coin improve dp[{S.a}] (now {S.dp[S.a] if S.dp[S.a] <= S.outer['amount'] else '∞'})?",
        "options": ["yes", "no"],
        "answer": lambda S, N: "yes" if S.dp[S.a - S.c] + 1 < S.dp[S.a] else "no",
        "why": "It improves when the smaller amount plus this one coin beats the best found so far.",
        "when": lambda S: S.a >= 3,
        "times": 4,
    },
}

ROW_COLS = ["house", "money", "skip", "rob", "best"]


def row(S, N):
    if S.text == "dp[i + 2] = max(dp[i + 1], dp[i] + money)":
        return [S.i, S.money, S.dp[S.i + 1], S.dp[S.i] + S.money, N.v["dp"][S.i + 2]]
    if S.func == "coin_change" and S.text == "for a in range(1, amount + 1):" and "a" in S.v:
        amount = S.outer["amount"]
        return [S.a, S.dp[S.a] if S.dp[S.a] <= amount else "∞"]
    return None


def rob_brute(nums):
    best = 0
    for r in range(len(nums) + 1):
        for pick in combinations(range(len(nums)), r):
            if all(b - a > 1 for a, b in zip(pick, pick[1:])):
                best = max(best, sum(nums[j] for j in pick))
    return best


def coin_brute(coins, amount):
    @lru_cache(None)
    def f(a):
        if a == 0:
            return 0
        options = [f(a - c) + 1 for c in coins if c <= a and f(a - c) >= 0]
        return min(options) if options else -1
    return f(amount)


def INVARIANT(S):
    if S.func == "rob" and S.text == "for i, money in enumerate(nums):" and "i" in S.v:
        nums, dp, i = S.outer["nums"], S.v["dp"], S.v["i"]
        return all(dp[j + 2] == rob_brute(nums[:j + 1]) for j in range(i + 1))
    if S.func == "coin_change" and S.text == "for a in range(1, amount + 1):" and "a" in S.v:
        dp, amount, coins = S.v["dp"], S.outer["amount"], S.outer["coins"]
        return all((dp[b] if dp[b] <= amount else -1) == coin_brute(tuple(coins), b) for b in range(S.v["a"] + 1))
    return True


TRACES = [
    {"label": "Rob [2, 7, 9, 3, 1]", "args": ([2, 7, 9, 3, 1],), "expect": 12,
     "about": "Each cell is filled once from the two cells before it (light). The green answer cell sits at the end."},
    {"label": "Rob [2, 1, 1, 2]: every other house fails", "args": ([2, 1, 1, 2],), "expect": 4,
     "about": "Taking houses 0 and 2, or 1 and 3, gives 3. The best skips two in a row: 2 + 2."},
    {"label": "Coins [1, 3, 4], amount 6", "fn": coin_change, "args": ([1, 3, 4], 6), "expect": 2,
     "cols": ["amount", "fewest coins"],
     "about": "Largest-first would take 4 + 1 + 1. The table tries every last coin and finds 3 + 3."},
]


def rob_inputs(rng):
    return [([],), ([5],), ([1, 2],)] + [([rng.randint(0, 9) for _ in range(rng.randint(0, 9))],) for _ in range(300)]


def coin_inputs(rng):
    out = [([2], 3), ([1], 0), ([5, 7], 1)]
    for _ in range(200):
        coins = sorted(set(rng.randint(1, 9) for _ in range(rng.randint(1, 4))))
        out.append((coins, rng.randint(0, 25)))
    return out


ORACLE = [{"brute": rob_brute, "inputs": rob_inputs},
          {"fn": coin_change, "brute": coin_brute, "inputs": coin_inputs}]

FAMILY_INTRO = "Name the subproblem and the last decision. The members differ in how many earlier cells a cell reads."
FAMILY = [
    {"name": "Take or skip: read the last one or two", "change": "The first traces. Climbing stairs adds the two before (a count). House Robber II runs twice, without the first house and without the last, because they are neighbours.",
     "problems": ["climbing-stairs", "min-cost-climbing-stairs", "house-robber", "house-robber-ii"]},
    {"name": "Best over choices: read one cell per option", "change": "The coin trace. Word Break: dp[i] is true when some word ends at i after a true dp[j]. Decode Ways adds dp[i − 1] (one digit) and dp[i − 2] (two digits) when they are valid. Counting ordered sums (Combination Sum IV) loops amounts outside, choices inside.",
     "problems": ["coin-change", "word-break", "decode-ways", "combination-sum-iv"]},
    {"name": "Best ending here: read every earlier cell", "change": "LIS: `dp[i] = 1 + max(dp[j])` over j < i with smaller values. Maximum product keeps the largest and the smallest product ending at i.",
     "problems": ["longest-increasing-subsequence", "maximum-product-subarray"]},
    {"name": "Reachable sums", "change": "Partition Equal Subset Sum: a set (or boolean row) of sums reachable with the items so far; each item adds itself to every sum already there.",
     "problems": ["partition-equal-subset-sum"]},
    {"name": "Palindromes by centre", "change": "Not a left-to-right table: expand around each of the 2n − 1 centres while the ends match. O(n²) time, O(1) space.",
     "problems": ["longest-palindromic-substring", "palindromic-substrings"]},
]

COUNT = {
    "line": "dp[i + 2] = max(dp[i + 1], dp[i] + money)",
    "input": lambda n: (list(range(n)),),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n,
    "bound_text": "n",
    "text": ["Each cell is written once, from two reads: n runs at O(1). The coin table writes `amount` cells and tries "
             "each coin for each, so its inner line runs amount × coins times: O(amount × coins). Plain recursion "
             "without the table branches at every cell: O(2ⁿ) for the houses."],
    "time": "O(n) for House Robber; O(amount × coins) for Coin Change.",
    "space": "O(n) for the table, O(1) if you keep only the last two cells.",
}

TRAPS = [
    ("No subproblem written in words", "is how wrong relations happen. Write `dp[i] = ...` in a sentence first."),
    ("Reading a cell that isn't filled yet", "means the order is wrong for the relation."),
    ("Base cases that don't mean anything", "like `dp[0] = 1` for coins without saying 'one way to make 0'."),
    ("Loop order for counting", "amounts outside, coins inside counts ordered sequences (Combination Sum IV); coins outside counts combinations (Coin Change II)."),
]


CHECK = {
    "trace": {"text": "Run rob on [4, 1, 2, 7, 5, 3, 1]. Write the dp cells for houses 0..6 (leave out the two padding cells), and the return value.",
              "args": ([4, 1, 2, 7, 5, 3, 1],),
              "fields": [("dp for houses 0..6", lambda run: run["states"][-1].v["dp"][2:]), ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "Climbing stairs with steps of 1, 2 or 3: which cells does dp[i] read?",
         "options": ["dp[i − 1] only", "dp[i − 1], dp[i − 2] and dp[i − 3], added", "Every earlier cell, max"], "answer": 1,
         "why": "The last step was 1, 2 or 3; the count adds the ways for each."},
        {"q": "Coin change says 'fewest coins' but someone writes greedy largest-first. Which input breaks it?",
         "options": ["coins [1, 5, 10], amount 15", "coins [1, 3, 4], amount 6", "coins [2], amount 4"], "answer": 1,
         "why": "Largest-first gives 4 + 1 + 1 = 3 coins; 3 + 3 = 2."},
    ],
    "own": {"prompt": "How do you turn a problem into a DP table, and why is it faster than plain recursion?",
            "model": "Write the subproblem in words (dp[i] = the most loot from houses 0..i), find the last decision (rob house i or not), and turn that into a relation over smaller cells. Fill the table in an order where every cell it reads is already filled, set base cases that mean something, and read the answer from the right cell. Plain recursion solves the same subproblems many times over; the table solves each once, so the time is cells × work per cell."},
}
