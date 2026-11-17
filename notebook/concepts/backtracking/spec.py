"""Backtracking, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/backtracking/spec.py"""
from itertools import combinations

from build_explainer import V, tree_layout

TITLE = "Backtracking, explained"
PITCH = ("Build every answer one choice at a time: choose, recurse, undo. The calls trace a decision tree, and pruning "
         "cuts off whole branches that can't lead to an answer.")

SPOT = {
    "idea": [
        "Backtracking is depth-first search over **partial solutions**. Each call makes one decision (take this item "
        "or not, which letter goes here, where the next queen goes), recurses, then **undoes** it so the next option starts "
        "from the same state. The calls form a decision tree; the answers are its leaves.",
        "Reach for it when the problem asks for **all** the combinations, subsets, permutations or placements, or when "
        "the input is small (n ≤ 20 or so) and the space is exponential anyway. If it only asks *how many* or *the best*, "
        "check whether the subproblems overlap: then it is dynamic programming.",
    ],
    "questions": [
        ("What is one decision?", "Take or skip `nums[i]`; which unused value goes next; which column for this row's queen."),
        ("What is a partial solution, and when is it complete?", "The path so far; complete at depth n, or when the target is met."),
        ("What must be undone after recursing?", "Pop the path, unmark the cell, remove from the used set."),
        ("What can be pruned?", "A sum already past the target, a letter that doesn't match, a queen under attack."),
    ],
    "cases": [
        {"text": "Return all subsets of a list of distinct numbers.",
         "options": ["Backtracking: take or skip each item", "Dynamic programming", "A heap"], "answer": 0,
         "why": "All 2ⁿ subsets are wanted, so the work is exponential anyway; take or skip is one decision per item."},
        {"text": "Return all permutations of distinct numbers.",
         "options": ["Backtracking with a used set", "Sort once", "Two pointers"], "answer": 0,
         "why": "Each level picks one unused value; undo by removing it from the path and the used set."},
        {"text": "How many ways can you climb n stairs taking 1 or 2 steps?",
         "options": ["Backtracking over every path", "Dynamic programming", "Greedy"], "answer": 1,
         "why": "It asks only for a count, and ways(n) = ways(n-1) + ways(n-2) repeats subproblems: DP in O(n)."},
        {"text": "Does a word appear in a grid of letters along adjacent cells, each used once?",
         "options": ["Backtracking from each cell, marking visited cells", "BFS for the shortest path", "A trie alone"], "answer": 0,
         "why": "Extend the path letter by letter, mark the cell, recurse, unmark. A mismatched letter prunes at once."},
        {"text": "Place n queens on an n × n board so none attack each other; list every board.",
         "options": ["Backtracking row by row with attacked columns and diagonals", "Greedy placement", "Union-find"], "answer": 0,
         "why": "One queen per row is one decision per level; sets of used columns and diagonals prune in O(1)."},
        {"text": "All combinations of candidates summing to a target, each candidate reusable.",
         "options": ["Backtracking that may stay on the same index", "A sliding window", "Prefix sums"], "answer": 0,
         "why": "Recurse with the same index to reuse a value, move on to skip it; prune when the sum passes the target."},
    ],
    "near_misses": [
        ("Count the subsets with a given sum.", "A count, with overlapping subproblems (index, remaining sum): DP, unless n is tiny."),
        ("Shortest path in a grid.", "Backtracking finds every path; BFS finds the shortest one directly."),
        ("Next permutation.", "One step of rearranging, not all permutations: a scan from the right."),
    ],
}

PARTS = {
    "names": [
        ("path", "the partial solution: the values chosen so far"),
        ("i", "the next index to decide about"),
        ("res", "complete solutions, each a copy of path at a leaf"),
    ],
    "plan": [
        ("Leaf", "`i == len(nums)`: every item is decided, so record `path[:]`."),
        ("Choose", "take `nums[i]`: append it and recurse on `i + 1`."),
        ("Undo", "pop it, so the path is exactly as it was before the choice."),
        ("Other branch", "skip `nums[i]`: recurse on `i + 1` with the path unchanged."),
    ],
    "invariant": "On entry to a call, path holds one choice for each of nums[:i], in order, and nothing else.",
    "safe": [
        "Every subset is a sequence of take-or-skip decisions, one per index, so each leaf is one subset and each subset is one leaf.",
        "Popping after the first recursive call restores the invariant for the second, so the skip branch starts from the same path.",
        "Recording `path[:]` stores a copy; `path` itself keeps changing, and storing it would leave every entry equal to the final, empty path.",
    ],
    "relies_on": "undoing exactly what was done, in reverse order. The work is exponential by design: prune early to cut whole subtrees.",
}


def subsets(nums):
    res, path = [], []

    def build(i):
        if i == len(nums):
            res.append(path[:])
            return
        path.append(nums[i])
        build(i + 1)
        path.pop()
        build(i + 1)

    build(0)
    return res


REFERENCE = subsets
CACHE = {}


def calls(S):
    """The decision tree of the whole run: each call of build is a node, numbered as it starts."""
    key = id(S.trace)
    if key not in CACHE:
        info = {"label": {}, "paths": {}, "parent": {}, "edge": {}, "born": {}, "active": [], "ended": [], "leaf": {}}
        stack, ended, count = [], set(), 0
        for k, st in enumerate(S.trace):
            if st.kind == "line" and st.func == "build" and st.text == "if i == len(nums):":
                me, path = count, list(st.outer["path"])
                count += 1
                info["label"][me] = ",".join(map(str, path)) or "∅"
                info["born"][me] = k
                info["paths"][me] = path
                if stack:
                    parent = stack[-1]
                    info["parent"][me] = parent
                    took = len(path) > len(info["paths"][parent])
                    info["edge"][me] = f"+{path[-1]}" if took else "skip"
                if st.v["i"] == len(st.outer["nums"]):
                    info["leaf"][me] = True
                stack.append(me)
            info["active"].append(list(stack))
            info["ended"].append(set(ended))
            if st.kind == "return" and st.func == "build":
                ended.add(stack.pop())
        children = {}
        for c, p in info["parent"].items():
            children.setdefault(p, []).append(c)
        info["pos"] = tree_layout(0, children)
        CACHE[key] = info
    return CACHE[key]


def view(S):
    out = []
    if S.func == "build" or any(f[0] == "build" for f in S.stack) or S.index > 2:
        c = calls(S)
        active, ended = c["active"][S.index], c["ended"][S.index]
        nodes, edges = [], []
        for me, born in c["born"].items():
            if born > S.index:
                continue
            x, y = c["pos"][me]
            cls = "cur" if active and me == active[-1] else "win" if me in active else ("ok" if me in c["leaf"] else "done") if me in ended else ""
            nodes.append({"id": me, "label": c["label"][me], "x": x, "y": y, "cls": cls})
            if me in c["parent"]:
                edges.append({"a": c["parent"][me], "b": me, "label": c["edge"][me], "cls": "cur" if me in active else ""})
        out.append(V.graph("decision tree so far (blue: this call, light: waiting, green: a recorded leaf)", nodes, edges,
                           w=max(x for x, _ in c["pos"].values()) + 1, h=max(y for _, y in c["pos"].values()) + 1))
    out += [V.array("nums", S.outer["nums"], {"i": S.v.get("i")} if S.func == "build" else {}),
            V.items("path", S.outer.get("path", [])), V.items("res", S.outer.get("res", []))]
    return out


def say(S, N):
    if S.text == "path.append(nums[i])":
        return f"Chose to take {S.outer['nums'][S.v['i']]}: path is {N.outer['path']}."
    if S.text == "path.pop()":
        return f"Undid the choice: {S.outer['path'][-1]} left the path, which is {N.outer['path']} again."
    if S.text == "res.append(path[:])":
        return f"Every item decided: recorded a copy of {S.outer['path']}."
    if S.kind == "return" and S.func == "build":
        return f"build({S.v['i']}) is done; back to its caller."
    if N.func == "build" and N.depth > S.depth:
        return f"Called build({N.v['i']})."
    return None


PREDICT = {
    "res.append(path[:])": {
        "q": "Every item is decided. Which subset gets recorded? (Write it like 1, 3, or 'empty'.)",
        "answer": lambda S, N: ", ".join(map(str, S.outer["path"])) or "empty",
        "why": "The path holds exactly the items taken on the way down to this leaf.",
        "times": 3,
    },
    "path.pop()": {
        "q": "Which value leaves the path?",
        "answer": lambda S, N: S.outer["path"][-1],
        "why": "The last value appended: undo happens in reverse order of the choices.",
        "times": 2,
    },
}

ROW_COLS = ["leaf", "recorded"]


def row(S, N):
    if S.text == "res.append(path[:])":
        return [len(S.outer["res"]) + 1, S.outer["path"]]
    return None


def INVARIANT(S):
    if S.func != "build" or S.text != "if i == len(nums):":
        return True
    nums, path, i = S.outer["nums"], S.outer["path"], S.v["i"]
    it = iter(nums[:i])
    return all(any(x == y for y in it) for x in path)  # path is a subsequence of nums[:i]


TRACES = [
    {"label": "All subsets of [1, 2, 3]", "args": ([1, 2, 3],),
     "expect": [[1, 2, 3], [1, 2], [1, 3], [1], [2, 3], [2], [3], []],
     "about": "Take or skip each value. Each call is a node of the decision tree; each leaf is one subset."},
    {"label": "Edge: []", "args": ([],), "expect": [[]],
     "about": "No items: the first call is already a leaf, and the empty subset is the one answer."},
]


def brute(nums):
    return sorted(sorted(c) for r in range(len(nums) + 1) for c in combinations(nums, r))


def inputs(rng):
    out = [([],), ([5],), ([1, 2],)]
    for _ in range(100):
        out.append((rng.sample(range(-5, 10), rng.randint(0, 6)),))
    return out


ORACLE = {"brute": brute, "inputs": inputs, "same": lambda got, want: sorted(sorted(x) for x in got) == want}

FAMILY_INTRO = "The members differ in what one decision is, what is undone, and what is pruned."
FAMILY = [
    {"name": "Take or skip", "change": "The trace above. With duplicates, sort first and skip a value equal to the previous one when that previous one was skipped at this level.",
     "problems": ["subsets", "subsets-ii"]},
    {"name": "Choose from a start index", "change": "`for j in range(start, n)`: append, recurse with `j` to allow reuse (or `j + 1` to forbid it), pop. Prune once the running sum passes the target.",
     "problems": ["combination-sum", "combination-sum-ii", "letter-combinations-of-a-phone-number"],
     "code": "def pick(start, remaining):\n    if remaining == 0:\n        res.append(path[:])\n        return\n    for j in range(start, len(cands)):\n        if cands[j] > remaining:\n            break                # sorted: every later candidate is too big too\n        path.append(cands[j])\n        pick(j, remaining - cands[j])\n        path.pop()"},
    {"name": "Order matters: a used set", "change": "Each level picks any unused value; mark it used, recurse, unmark.",
     "problems": ["permutations"]},
    {"name": "Place under constraints", "change": "One row per level for queens, with sets for used columns and both diagonals (`r - c`, `r + c`). Palindrome partitioning cuts the string at each position whose prefix is a palindrome.",
     "problems": ["n-queens", "palindrome-partitioning"]},
    {"name": "Paths in a grid", "change": "From each cell, match the next letter, mark the cell, try the four neighbours, unmark. A mismatch prunes the branch at once.",
     "problems": ["word-search"]},
]

COUNT = {
    "line": "if i == len(nums):",
    "input": lambda n: (list(range(n)),),
    "sizes": [4, 6, 8, 10],
    "bound": lambda n: 2 ** (n + 1) - 1,
    "bound_text": "2ⁿ⁺¹ − 1",
    "n_name": "n (items)",
    "text": ["Every call starts with the leaf check, and the decision tree has 2ⁿ leaves and 2ⁿ − 1 inner calls: "
             "2ⁿ⁺¹ − 1 runs in all. Each leaf also copies a path of up to n items. So two more items quadruple the "
             "count: exponential, as any algorithm that lists all 2ⁿ subsets must be."],
    "time": "O(n · 2ⁿ): 2ⁿ leaves, each copying up to n items.",
    "space": "O(n) for the path and the call stack, plus the output itself.",
}

TRAPS = [
    ("`res.append(path)` without copying", "stores the same list every time; at the end every entry is the final, empty path."),
    ("Forgetting to undo", "leaks a choice into the sibling branch: the skip branch still holds the taken value."),
    ("Duplicates without sorting and skipping", "lists the same subset or combination more than once."),
    ("Pruning after recursing", "explores the doomed subtree anyway. Check the bound before the call."),
]


CHECK = {
    "trace": {"text": "Run subsets on nums = [4, 5]. Write the subsets in the order they are recorded, and how many times build is called.",
              "args": ([4, 5],),
              "fields": [("Subsets in the order recorded", lambda run: run["result"]),
                         ("Calls to build", lambda run: sum(1 for s in run["states"] if s.kind == "line" and s.text == "if i == len(nums):"))]},
    "questions": [
        {"q": "You need the number of subsets of a 40-item list whose sum is at most 1000. Backtracking or DP?",
         "options": ["Backtracking: 2⁴⁰ leaves is fine", "DP over (index, sum): about 40 × 1000 states", "A heap"], "answer": 1,
         "why": "A count with overlapping subproblems: (index, remaining sum) repeats across branches. 2⁴⁰ is about 10¹²."},
        {"q": "Permutations of [1, 2, 3]: what replaces 'the next index i' as the decision?",
         "options": ["Which unused value goes in the next position", "Whether to take nums[i]", "Where to split the list"], "answer": 0,
         "why": "Order matters, so each level chooses among all values not used yet: a used set, marked and unmarked."},
    ],
    "own": {"prompt": "What does undo protect, and how do you tell backtracking from DP?",
            "model": "Each call makes one choice, recurses, then undoes it, so the next option starts from exactly the state the call received; the path is always a valid partial solution and every leaf is one complete answer. Backtracking lists or searches all the answers, so exponential work is expected and pruning saves it. When the question asks only for a count or a best value and the same subproblem (index, remaining) comes up in many branches, it is DP instead."},
}
