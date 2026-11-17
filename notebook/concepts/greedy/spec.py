"""Greedy, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/greedy/spec.py"""
from build_explainer import V

TITLE = "Greedy, explained"
PITCH = ("Make the choice that looks best now, never revisit it, and prove that choice can always be swapped into "
         "some optimal answer. The proof is the whole pattern; the code is usually one loop.")

SPOT = {
    "idea": [
        "A greedy algorithm commits to one local choice per step: the farthest reach, the interval that ends first, "
        "dropping a running sum once it turns negative. It is fast and short, and **wrong unless you can say why**. "
        "The usual proof is an **exchange argument**: take any optimal answer, swap in the greedy choice, and show it "
        "is no worse.",
        "So reach for greedy when one quantity summarises everything the future needs (a farthest index, a running "
        "sum, the earliest end), and test it on a small counterexample before trusting it. Coins of 1, 3 and 4 for "
        "amount 6 is the classic warning: largest-first takes 4 + 1 + 1, but 3 + 3 is better. That is DP.",
    ],
    "questions": [
        ("What one number summarises the past?", "The farthest reachable index; the best sum ending here; the fuel left."),
        ("What is the greedy choice?", "Extend the reach; restart the sum; take the interval that ends first."),
        ("Why can it always be swapped into an optimal answer?", "Say the exchange argument in one sentence, or don't use greedy."),
        ("Is there a small counterexample?", "Try 3–4 elements by hand; if the greedy choice loses, it is DP."),
    ],
    "cases": [
        {"text": "Can you reach the last index, where nums[i] is the longest jump from i?",
         "options": ["Greedy: track the farthest reachable index", "BFS over every jump", "Backtracking"], "answer": 0,
         "why": "Any index up to the farthest reach is reachable, so one number decides everything: O(n)."},
        {"text": "The largest sum of a contiguous subarray.",
         "options": ["Kadane: extend the run or restart at x", "Sort and take the largest", "Backtracking"], "answer": 0,
         "why": "A run with a negative sum only hurts whatever follows, so drop it and restart."},
        {"text": "Fewest coins for an amount with coins [1, 3, 4].",
         "options": ["Greedy: largest coin first", "Dynamic programming", "Two pointers"], "answer": 1,
         "why": "Largest-first gives 4 + 1 + 1 = 3 coins for 6, but 3 + 3 = 2 coins. No exchange argument: DP."},
        {"text": "Gas stations in a circle: from which one can you drive all the way round?",
         "options": ["Greedy: restart after the tank goes negative", "Try every start in full", "Binary search"], "answer": 0,
         "why": "If you run dry between a and b, no station between them can start either; and a full loop exists iff total gas ≥ total cost."},
        {"text": "Split a string into as many parts as possible so each letter appears in one part.",
         "options": ["Greedy with each letter's last index", "DP over cut positions", "A heap"], "answer": 0,
         "why": "Extend the current part to the farthest last occurrence of any letter in it; cut when you reach it."},
        {"text": "Fewest jumps to reach the last index.",
         "options": ["Greedy levels: the farthest reach within the current jump", "Backtracking", "Sorting"], "answer": 0,
         "why": "It is BFS by levels without a queue: each jump's range is [start, farthest], and the next range is what it can reach."},
    ],
    "near_misses": [
        ("Coin change with arbitrary coins.", "Largest-first fails on [1, 3, 4] for 6: DP."),
        ("0/1 knapsack.", "Best value per weight first fails; fractional knapsack is the greedy one."),
        ("Weighted intervals.", "Earliest end works only without weights; with weights it is DP."),
    ],
}

PARTS = {
    "names": [
        ("reach", "the farthest index reachable using indexes 0..i"),
        ("i", "the index being considered"),
        ("i + step", "how far a jump from i can go"),
    ],
    "plan": [
        ("Start", "`reach = 0`: only index 0 is reachable."),
        ("Each index", "if `i > reach`, it can't be reached, and nothing after it can: return False."),
        ("Otherwise", "`reach = max(reach, i + step)`."),
        ("Stop", "every index was reachable: True."),
    ],
    "invariant": "Before index i is checked, every index ≤ reach is reachable, and no index > reach is reachable using jumps from 0..i − 1.",
    "safe": [
        "Reachable indexes form a prefix: if j is reachable, so is every index before j (jump shorter). So one number, the farthest reach, describes them all.",
        "If `i > reach`, no jump from any earlier index lands on i or beyond: the end is unreachable.",
        "Taking the max keeps the reach true after index i: a jump from i adds exactly [i, i + step].",
    ],
    "relies_on": "the reachable set being a prefix. If some jumps were forbidden landing squares, it wouldn't be, and greedy would break.",
}


def can_jump(nums):
    reach = 0
    for i, step in enumerate(nums):
        if i > reach:
            return False
        reach = max(reach, i + step)
    return True


def max_subarray(nums):
    best = cur = nums[0]
    for i in range(1, len(nums)):
        cur = max(nums[i], cur + nums[i])
        best = max(best, cur)
    return best


REFERENCE = can_jump


def view(S):
    nums = S.outer["nums"]
    i = S.v.get("i")
    if S.func == "max_subarray":
        start = i
        if i is not None and "cur" in S.v:  # the run that ends at i: walk back while the sums still match
            total, start = 0, i
            for j in range(i, -1, -1):
                total += nums[j]
                if total == S.v["cur"] and S.text != "cur = max(nums[i], cur + nums[i])":
                    start = j
        cls = {j: "win" for j in range(start, i + 1)} if i is not None and S.text != "cur = max(nums[i], cur + nums[i])" else {}
        if i is not None:
            cls[i] = "cur"
        return [V.array("nums (light: the run ending at i)", nums, {"i": i}, cls),
                V.vars(("cur: best sum ending at i", S.v.get("cur")), ("best: best sum so far", S.v.get("best")))]
    reach = S.v.get("reach", 0)
    cls = {j: "win" for j in range(len(nums)) if j <= reach}
    if i is not None:
        cls[i] = "cur"
    labels = [f"{j}" for j in range(len(nums))]
    return [V.array("nums: jump lengths (light: reachable so far)", nums, {"i": i, "reach": min(reach, len(nums))}, cls, labels),
            V.vars(("reach", reach), ("i + step", None if i is None else i + S.v.get("step", 0)))]


def say(S, N):
    if S.text == "if i > reach:":
        return f"{S.i} ≤ {S.reach}: index {S.i} is reachable." if N.text != "return False" else f"{S.i} > {S.reach}: index {S.i} can't be reached."
    if S.text == "reach = max(reach, i + step)":
        return f"From {S.i} a jump reaches {S.i + S.step}; reach is now {N.v['reach']}."
    if S.text == "cur = max(nums[i], cur + nums[i])":
        x = S.outer["nums"][S.i]
        return (f"Restart at {x}: the run so far ({S.cur}) is negative, so it only drags {x} down." if x > S.cur + x
                else f"Extend: {S.cur} + {x} = {S.cur + x}.")
    return None


PREDICT = {
    "if i > reach:": {
        "q": lambda S: f"reach = {S.reach}. Is index {S.i} reachable?",
        "options": ["yes", "no"],
        "answer": lambda S, N: "no" if S.i > S.reach else "yes",
        "why": "Reachable indexes are exactly 0..reach.",
        "when": lambda S: S.i > 0,
        "times": 3,
    },
    "reach = max(reach, i + step)": {
        "q": lambda S: f"reach = {S.reach}, i = {S.i}, nums[i] = {S.step}. New reach?",
        "answer": lambda S, N: N.v["reach"],
        "times": 2,
    },
    "cur = max(nums[i], cur + nums[i])": {
        "q": lambda S: f"cur = {S.cur}, nums[i] = {S.outer['nums'][S.i]}. Extend the run or restart at nums[i]?",
        "options": ["extend", "restart"],
        "answer": lambda S, N: "restart" if S.outer["nums"][S.i] > S.cur + S.outer["nums"][S.i] else "extend",
        "why": "Restart exactly when the run so far is negative: adding it would only lower the sum.",
        "times": 4,
    },
}

ROW_COLS = ["i", "nums[i]", "i + nums[i]", "reach after"]


def row(S, N):
    if S.text == "reach = max(reach, i + step)":
        return [S.i, S.step, S.i + S.step, N.v["reach"]]
    if S.text == "best = max(best, cur)":
        return [S.i, S.outer["nums"][S.i], S.cur, N.v["best"]]
    return None


def reachable(nums):
    seen, stack = {0}, [0]
    while stack:
        i = stack.pop()
        for j in range(i + 1, min(len(nums), i + nums[i] + 1)):
            if j not in seen:
                seen.add(j)
                stack.append(j)
    return seen


def INVARIANT(S):
    if S.func == "can_jump" and S.text == "if i > reach:":
        nums, i, reach = S.outer["nums"], S.v["i"], S.v["reach"]
        sub = reachable(nums[:i] + [0])  # jumps from 0..i-1 only
        return all((j in sub) == (j <= reach) for j in range(i + 1))
    if S.func == "max_subarray" and S.text == "best = max(best, cur)":
        nums, i = S.outer["nums"], S.v["i"]
        return S.v["cur"] == max(sum(nums[j:i + 1]) for j in range(i + 1))
    return True


TRACES = [
    {"label": "Jump: [2, 3, 1, 1, 4]", "args": ([2, 3, 1, 1, 4],), "expect": True,
     "about": "The light cells are everything reachable so far. One number, reach, is the whole state."},
    {"label": "Jump: [3, 2, 1, 0, 4]", "args": ([3, 2, 1, 0, 4],), "expect": False,
     "about": "Every path lands on the 0 at index 3, and reach stops growing there."},
    {"label": "Kadane: [-2, 1, -3, 4, -1, 2, 1, -5, 4]", "fn": max_subarray, "args": ([-2, 1, -3, 4, -1, 2, 1, -5, 4],), "expect": 6,
     "cols": ["i", "nums[i]", "cur", "best"],
     "about": "cur is the best sum of a run ending at i. It restarts whenever the run before it is negative."},
]


def jump_inputs(rng):
    return [([0],), ([1, 0],), ([0, 1],)] + [([rng.randint(0, 3) for _ in range(rng.randint(1, 9))],) for _ in range(300)]


def sub_inputs(rng):
    return [([-3],), ([-1, -2],), ([5, -9, 6],)] + [([rng.randint(-6, 6) for _ in range(rng.randint(1, 9))],) for _ in range(300)]


ORACLE = [{"brute": lambda nums: len(nums) - 1 in reachable(nums), "inputs": jump_inputs},
          {"fn": max_subarray, "brute": lambda nums: max(sum(nums[a:b + 1]) for a in range(len(nums)) for b in range(a, len(nums))),
           "inputs": sub_inputs}]

FAMILY_INTRO = "Each member keeps one summary number and has one sentence of proof. Learn the sentence with the code."
FAMILY = [
    {"name": "Farthest reach", "change": "The first traces. For the fewest jumps, count levels: when i reaches the end of the current jump's range, jump again and extend the range to the farthest reach.",
     "problems": ["jump-game", "jump-game-ii"]},
    {"name": "Drop a bad prefix", "change": "Kadane restarts the run when it goes negative. Gas Station restarts the start after the tank goes negative, and checks total gas ≥ total cost once.",
     "problems": ["maximum-subarray", "gas-station"]},
    {"name": "Extend to the last occurrence", "change": "Record each letter's last index; grow the current part to the largest last index seen; cut when i reaches it.",
     "problems": ["partition-labels"]},
    {"name": "Smallest first", "change": "Hand of Straights: sort and start each group at the smallest card left. Merge Triplets: keep only triplets that don't exceed the target anywhere, then check each target value is hit.",
     "problems": ["hand-of-straights", "merge-triplets-to-form-target-triplet"]},
    {"name": "A range of possibilities", "change": "Valid Parenthesis String keeps the lowest and highest number of open brackets possible; `*` widens the range. Fail if the high goes negative; succeed if the low can reach 0.",
     "problems": ["valid-parenthesis-string"]},
]

COUNT = {
    "line": "if i > reach:",
    "input": lambda n: ([1] * n,),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n,
    "bound_text": "n",
    "text": ["One pass: the check runs at most once per index, each O(1). Doubling n doubles it. A BFS over every jump "
             "would look at up to n jumps from each index, O(n²); the farthest reach makes those redundant."],
    "time": "O(n)",
    "space": "O(1)",
}

TRAPS = [
    ("Greedy without a proof", "passes the examples and fails the hidden tests. Try a 3–4 element counterexample first."),
    ("Kadane starting from `best = 0`", "returns 0 for an all-negative array. Start from `nums[0]`."),
    ("Gas Station without the total check", "returns a start even when no full loop exists."),
    ("Jump Game II counting every reach update as a jump", "overcounts; count only when the current range ends."),
]


CHECK = {
    "trace": {"text": "Run can_jump on [2, 0, 1, 0, 4]. Write reach after each index it processes, and what it returns.",
              "args": ([2, 0, 1, 0, 4],),
              "fields": [("reach after each index", lambda run: ", ".join(str(s.v["reach"]) for s in run["states"][1:] if s.kind == "line" and s.text == "for i, step in enumerate(nums):" and "i" in s.v)),
                         ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "Coins [1, 5, 10, 25] (US coins) vs [1, 3, 4]: why does largest-first work for one and not the other?",
         "options": ["It works for both", "US coins have an exchange property (any optimal answer can take the largest coin); [1, 3, 4] doesn't: 6 = 3 + 3",
                     "Largest-first always fails"], "answer": 1,
         "why": "Greedy is only as good as its exchange argument. For arbitrary coins, use DP."},
        {"q": "Kadane at i: cur = −2, nums[i] = 5. What is the new cur?",
         "options": ["3", "5", "−2"], "answer": 1,
         "why": "max(5, −2 + 5) = 5: the negative run is dropped."},
    ],
    "own": {"prompt": "What makes a greedy choice safe, and how do you check before trusting it?",
            "model": "A greedy choice is safe when an exchange argument shows it can be swapped into some optimal answer without making it worse: the reachable indexes are always a prefix, so the farthest reach is all that matters; a negative running sum only lowers whatever follows, so restarting never hurts. Before trusting a greedy idea, try a three- or four-element counterexample by hand; if the local choice loses (coins 1, 3, 4 for 6), the problem needs DP."},
}
