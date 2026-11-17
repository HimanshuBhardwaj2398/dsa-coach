"""2-D Dynamic Programming, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/2d-dp/spec.py"""
from functools import lru_cache

from build_explainer import V

TITLE = "2-D Dynamic Programming, explained"
PITCH = ("Two indices, one table. Each cell answers the question for two prefixes (or a cell of a grid), reads its "
         "neighbours above and to the left, and the bottom-right cell is the answer.")

SPOT = {
    "idea": [
        "When a subproblem needs **two numbers** to name it (a prefix of each of two strings, a cell of a grid, an item "
        "and a capacity, a day and a state), the table is 2-D. The method doesn't change: say what `dp[i][j]` means in "
        "words, find the last decision, and fill in an order where every cell it reads is already filled.",
        "For two strings, the last decision is about their **last characters**: if they match, they can pair up "
        "(diagonal + 1); if not, one of them is dropped (the cell above or to the left). That one idea gives longest "
        "common subsequence, edit distance (with a third neighbour for replace) and distinct subsequences.",
    ],
    "questions": [
        ("What two things name a subproblem?", "Prefix lengths i and j; a grid cell; items so far and remaining capacity."),
        ("What does dp[i][j] mean, in words?", "'The LCS of a[:i] and b[:j]', 'the ways to reach cell (i, j)'."),
        ("Which neighbours does a cell read?", "Diagonal, up, left: fill row by row, left to right."),
        ("Do I need the whole table?", "If a row reads only the row above, keep two rows: O(n) space."),
    ],
    "cases": [
        {"text": "The length of the longest common subsequence of two strings.",
         "options": ["2-D DP over prefixes", "Two pointers", "A hash set of characters"], "answer": 0,
         "why": "The last characters either match (diagonal + 1) or one is dropped (max of up and left)."},
        {"text": "The fewest insertions, deletions and replacements to turn one word into another.",
         "options": ["2-D DP: edit distance", "Greedy from the left", "BFS over strings"], "answer": 0,
         "why": "Same table as LCS, reading three neighbours: delete (up), insert (left), replace (diagonal)."},
        {"text": "Paths from the top-left to the bottom-right of a grid, moving right or down.",
         "options": ["DP: dp[r][c] = dp[r − 1][c] + dp[r][c − 1]", "BFS", "Backtracking listing every path"], "answer": 0,
         "why": "Every path into a cell comes from above or from the left; count, don't list."},
        {"text": "The number of ways to make an amount from coins, each usable any number of times (order doesn't matter).",
         "options": ["DP over (coins so far, amount)", "Greedy", "Backtracking"], "answer": 0,
         "why": "Unbounded knapsack: rolled to one row, loop coins outside and amounts inside."},
        {"text": "The longest increasing subsequence of one array.",
         "options": ["2-D DP", "1-D DP", "A heap"], "answer": 1,
         "why": "One sequence, one index: dp[i] = the longest ending at i."},
        {"text": "Best stock profit when you must wait a day after selling.",
         "options": ["DP over (day, state: holding, sold, resting)", "Greedy: buy every dip", "Two pointers"], "answer": 0,
         "why": "The second dimension is a small state machine; each day's states read yesterday's."},
    ],
    "near_misses": [
        ("One sequence.", "One index: 1-D DP."),
        ("A grid where you can move in all four directions.", "Cycles: the fill order breaks. That is BFS, or memoised DFS when values strictly increase."),
        ("Listing every path.", "Exponential output: backtracking."),
    ],
}

PARTS = {
    "names": [
        ("dp[i][j]", "the length of the longest common subsequence of `a[:i]` and `b[:j]`"),
        ("row 0, column 0", "an empty prefix: the LCS is 0"),
        ("a[i − 1], b[j − 1]", "the last characters of the two prefixes (the table is shifted by one)"),
    ],
    "plan": [
        ("Match", "`a[i − 1] == b[j − 1]`: pair them, `dp[i][j] = dp[i − 1][j − 1] + 1`."),
        ("No match", "drop one: `dp[i][j] = max(dp[i − 1][j], dp[i][j − 1])`."),
        ("Order", "row by row, left to right: diagonal, up and left are filled first."),
        ("Answer", "`dp[len(a)][len(b)]`, the bottom-right cell."),
    ],
    "invariant": "Every filled cell dp[i][j] equals the LCS length of a[:i] and b[:j].",
    "safe": [
        "If the last characters match, some longest common subsequence uses them as its last pair; the rest is an LCS of the shorter prefixes: diagonal + 1.",
        "If they differ, they can't both be the last pair, so one of them is unused: the answer is the better of dropping a's last character (up) or b's (left).",
        "Row-major order fills (i − 1, j − 1), (i − 1, j) and (i, j − 1) before (i, j).",
    ],
    "relies_on": "the answer for two prefixes depending only on shorter prefixes. With a third string, the table becomes 3-D.",
}


def lcs(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


REFERENCE = lcs


def view(S):
    a, b = S.outer["a"], S.outer["b"]
    dp, i, j = S.v.get("dp"), S.v.get("i"), S.v.get("j")
    if dp is None:
        return [V.vars(("a", a), ("b", b))]
    written = {(t.v["i"], t.v["j"]) for t in S.trace[:S.index] if t.kind == "line" and t.text.startswith("dp[i][j] =")}
    filled = lambda r, c: r == 0 or c == 0 or (r, c) in written
    writing = S.text.startswith("dp[i][j] =") or S.text.startswith("if a[i - 1]")
    cells = [[dp[r][c] if filled(r, c) else None for c in range(len(b) + 1)] for r in range(len(a) + 1)]
    cls = {}
    if i is not None and j is not None and writing:
        cls[(i, j)] = "cur"
        if a[i - 1] == b[j - 1]:
            cls[(i - 1, j - 1)] = "ok"
        else:
            cls[(i - 1, j)] = "win"
            cls[(i, j - 1)] = "win"
    return [V.grid("dp: LCS of a[:i] (rows) and b[:j] (columns)", cells, ["∅"] + list(a), ["∅"] + list(b), cls),
            V.vars(("i", i), ("j", j), ("a[i − 1]", a[i - 1] if i else None), ("b[j − 1]", b[j - 1] if j else None))]


def say(S, N):
    if S.text == "if a[i - 1] == b[j - 1]:":
        x, y = S.outer["a"][S.i - 1], S.outer["b"][S.j - 1]
        return f"'{x}' = '{y}': they pair up." if x == y else f"'{x}' ≠ '{y}': drop one of them."
    if S.text == "dp[i][j] = dp[i - 1][j - 1] + 1":
        return f"dp[{S.i}][{S.j}] = diagonal {S.dp[S.i - 1][S.j - 1]} + 1 = {N.v['dp'][S.i][S.j]}."
    if S.text == "dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])":
        return f"dp[{S.i}][{S.j}] = max(up {S.dp[S.i - 1][S.j]}, left {S.dp[S.i][S.j - 1]}) = {N.v['dp'][S.i][S.j]}."
    return None


PREDICT = {
    "if a[i - 1] == b[j - 1]:": {
        "q": lambda S: f"Cell ({S.i}, {S.j}): '{S.outer['a'][S.i - 1]}' vs '{S.outer['b'][S.j - 1]}'. Which cells does it read?",
        "options": ["the diagonal, + 1", "the max of up and left"],
        "answer": lambda S, N: "the diagonal, + 1" if S.outer["a"][S.i - 1] == S.outer["b"][S.j - 1] else "the max of up and left",
        "why": "Matching last characters pair up; otherwise one of them is dropped.",
        "times": 4,
    },
    "dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])": {
        "q": lambda S: f"up = {S.dp[S.i - 1][S.j]}, left = {S.dp[S.i][S.j - 1]}. Value of dp[{S.i}][{S.j}]?",
        "answer": lambda S, N: N.v["dp"][S.i][S.j],
        "when": lambda S: S.i >= 2,
        "times": 2,
    },
}

ROW_COLS = ["row", "a[i − 1]", "row of dp"]


def row(S, N):
    if S.text == "for j in range(1, len(b) + 1):" and N.text == "for i in range(1, len(a) + 1):":
        return [S.i, S.outer["a"][S.i - 1], S.dp[S.i]]
    if S.text == "for j in range(1, len(b) + 1):" and N.kind == "line" and N.text == "return dp[-1][-1]":
        return [S.i, S.outer["a"][S.i - 1], S.dp[S.i]]
    return None


def lcs_brute(a, b):
    @lru_cache(None)
    def f(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))
    return f(0, 0)


def INVARIANT(S):
    if S.text != "if a[i - 1] == b[j - 1]:":
        return True
    a, b, dp, i, j = S.outer["a"], S.outer["b"], S.v["dp"], S.v["i"], S.v["j"]
    return all(dp[r][c] == lcs_brute(a[:r], b[:c]) for r in range(i) for c in range(len(b) + 1)) and \
        all(dp[i][c] == lcs_brute(a[:i], b[:c]) for c in range(j))


TRACES = [
    {"label": "LCS('abcde', 'ace')", "args": ("abcde", "ace"), "expect": 3,
     "about": "Rows are prefixes of 'abcde', columns prefixes of 'ace'. Green: the diagonal a match reads; light: up and left for a mismatch."},
    {"label": "No common letter: 'abc', 'def'", "args": ("abc", "def"), "expect": 0,
     "about": "Every cell takes max(up, left) of zeros. The table still costs m × n."},
]


def inputs(rng):
    out = [("", ""), ("a", ""), ("", "b"), ("aaa", "aa")]
    for _ in range(300):
        out.append(("".join(rng.choice("abc") for _ in range(rng.randint(0, 7))),
                    "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))))
    return out


ORACLE = {"brute": lcs_brute, "inputs": inputs}

FAMILY_INTRO = "Name the two indices and the last decision; the rest is the same table."
FAMILY = [
    {"name": "Two strings, three neighbours", "change": "LCS above. Edit distance: `1 + min(up, left, diagonal)` on a mismatch, the diagonal on a match. Distinct Subsequences counts: diagonal + up on a match. Interleaving String and regex matching use the same grid of prefixes.",
     "problems": ["longest-common-subsequence", "edit-distance", "distinct-subsequences", "interleaving-string", "regular-expression-matching"]},
    {"name": "Paths in a grid", "change": "`dp[r][c] = dp[r − 1][c] + dp[r][c − 1]`, with obstacles set to 0. When moves go in all four directions but values strictly increase (Longest Increasing Path), memoised DFS gives the order instead.",
     "problems": ["unique-paths", "longest-increasing-path-in-a-matrix"]},
    {"name": "Items × capacity (knapsack)", "change": "`dp[k][x]` = ways or best using the first k items for total x. Rolled to one row: unbounded items loop x upward; 0/1 items loop x downward so an item isn't reused. Target Sum is subset sum after algebra.",
     "problems": ["coin-change-ii", "target-sum"]},
    {"name": "Day × state", "change": "Stock with cooldown: three states per day (holding, just sold, resting), each read from yesterday's.",
     "problems": ["best-time-to-buy-and-sell-stock-with-cooldown"]},
    {"name": "Intervals of the input", "change": "`dp[l][r]` for a range, filled by increasing length; Burst Balloons picks the last balloon to burst in the range.",
     "problems": ["burst-balloons"]},
]

COUNT = {
    "line": "if a[i - 1] == b[j - 1]:",
    "input": lambda n: ("ab" * (n // 2), "ba" * (n // 2)),
    "sizes": [8, 16, 32, 64],
    "bound": lambda n: n * n,
    "bound_text": "m · n (here n · n)",
    "n_name": "n (both lengths)",
    "text": ["The comparison runs once per cell: m · n times, each O(1). Doubling both lengths quadruples it: "
             "the 'vs the row above' column reads about ×4. Each row reads only the row above, so two rows of "
             "length n + 1 are enough when only the length is needed."],
    "time": "O(m · n)",
    "space": "O(m · n); O(min(m, n)) with two rolling rows.",
}

TRAPS = [
    ("Mixing string and table indices", "`a[i]` vs `a[i − 1]`: the table has an extra row and column for the empty prefix."),
    ("Filling in an order that reads unfilled cells", "gives zeros where answers should be. Row by row, left to right."),
    ("0/1 knapsack rolled to one row, looping capacity upward", "reuses an item. Loop downward."),
    ("Keeping the whole table when one row would do", "uses m · n memory for nothing; reconstructing the subsequence does need it."),
]


CHECK = {
    "trace": {"text": "Run lcs('abcb', 'bdcab'). What is dp[2][3] (LCS of 'ab' and 'bdc'), and what does it return?",
              "args": ("abcb", "bdcab"),
              "fields": [("dp[2][3]", lambda run: run["states"][-1].v["dp"][2][3]), ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "Edit distance at a mismatch: which three cells, and what does each mean?",
         "options": ["up = delete from a, left = insert into a, diagonal = replace; 1 + the minimum", "Only the diagonal", "up + left"], "answer": 0,
         "why": "Each neighbour is the cost after one operation on the last character."},
        {"q": "You only need the LCS length of two strings of length 10⁵. Memory?",
         "options": ["The full 10¹⁰-cell table", "Two rows of 10⁵ + 1 cells", "One cell"], "answer": 1,
         "why": "Each row reads only the row above. (Time is still 10¹⁰ steps: too slow for that size in Python anyway.)"},
    ],
    "own": {"prompt": "What decides which neighbours a cell of a two-string table reads?",
            "model": "dp[i][j] answers the question for the prefixes a[:i] and b[:j], so the cell looks at the last characters. If they match, they can be paired, and the rest is the diagonal cell; if not, one of them goes unused, so the answer is the better of dropping a's last character (the cell above) or b's (the cell to the left). Filling row by row, left to right, guarantees those cells are ready, and the bottom-right cell answers the full strings in m × n steps."},
}
