"""Math & Geometry, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/math-geometry/spec.py"""
from build_explainer import V

TITLE = "Math & Geometry, explained"
PITCH = ("No data structure to discover: the work is exact index arithmetic. Keep boundaries that shrink after "
         "each use, and when a number is huge, halve it instead of counting it down.")

SPOT = {
    "idea": [
        "These problems test **careful bookkeeping** more than a clever idea: walk a matrix in a spiral, rotate it in "
        "place, add digits with a carry, raise x to the 2³¹-th power. Most bugs are off-by-one errors, so make the "
        "bookkeeping explicit: name the boundaries (`top`, `bottom`, `left`, `right`) and say when each moves.",
        "Two tools recur. **Shrinking boundaries**: after a row or column is used, move that boundary inward, and check "
        "the boundaries still cross before the next side, so a single row or column isn't walked twice. "
        "**Halving**: `xⁿ = (x²)^(n/2)`, so look at n's bits and square at each step: log n multiplications instead of n.",
    ],
    "questions": [
        ("What are the boundaries, and when does each move?", "Top after the top row, right after the right column, and so on."),
        ("Can a step run on an empty range?", "Re-check `top <= bottom` / `left <= right` before the bottom row and left column."),
        ("Is the number too big to count down?", "Halve it: exponentiation by squaring, O(log n)."),
        ("Can it be done in place?", "Rotate = transpose + reverse each row; mark rows and columns in the first row and column."),
    ],
    "cases": [
        {"text": "Return the elements of an m × n matrix in spiral order.",
         "options": ["Four shrinking boundaries", "BFS from the corner", "Sort the elements"], "answer": 0,
         "why": "Walk top, right, bottom, left; move each boundary in after using it; stop when they cross."},
        {"text": "Rotate an n × n image by 90° clockwise, in place.",
         "options": ["Transpose, then reverse each row", "Copy into a new matrix", "Spiral order"], "answer": 0,
         "why": "Transposing swaps (r, c) and (c, r); reversing rows then puts each column in its rotated place. O(1) extra space."},
        {"text": "Compute x to the power n for n up to 2³¹ − 1.",
         "options": ["Multiply x by itself n times", "Exponentiation by squaring", "A lookup table"], "answer": 1,
         "why": "n multiplications is about 2 × 10⁹; squaring needs about 31."},
        {"text": "Multiply two numbers given as strings of up to 200 digits, without converting them.",
         "options": ["Grade-school multiplication into a digit array", "Repeated addition", "Binary search"], "answer": 0,
         "why": "Digit i times digit j lands at position i + j (+1); carry at the end. O(m · n)."},
        {"text": "Is a number 'happy' (repeatedly summing squares of digits reaches 1)?",
         "options": ["Detect a cycle (a set, or slow and fast pointers)", "DP", "Sorting"], "answer": 0,
         "why": "The sequence either reaches 1 or loops; spotting the loop is cycle detection."},
        {"text": "Set a cell's whole row and column to 0 when it is 0, with O(1) extra space.",
         "options": ["Use the first row and column as markers", "A set of rows and a set of columns", "BFS"], "answer": 0,
         "why": "The sets work in O(m + n) space; the first row and column can hold the same marks, with one extra flag."},
    ],
    "near_misses": [
        ("Shortest path in a grid.", "That is a graph: BFS."),
        ("Counting paths in a grid.", "That is 2-D DP."),
        ("Big integers in Python.", "Python ints don't overflow; interviewers may still ask you to treat them as 32-bit."),
    ],
}

PARTS = {
    "names": [
        ("top, bottom", "the first and last rows not yet walked"),
        ("left, right", "the first and last columns not yet walked"),
        ("out", "the elements in spiral order so far"),
    ],
    "plan": [
        ("Start", "the boundaries are the matrix's edges."),
        ("One lap", "top row left to right, then `top += 1`; right column down, then `right -= 1`."),
        ("Re-check", "if a row is left, bottom row right to left, `bottom -= 1`; if a column is left, left column up, `left += 1`."),
        ("Stop", "the boundaries cross: every cell is in out."),
    ],
    "invariant": "The unvisited cells are exactly the rectangle rows top..bottom, columns left..right.",
    "safe": [
        "Each side walked is one edge of that rectangle; moving its boundary in removes exactly those cells.",
        "After the top row and right column, the rectangle may be empty (a single row or column was left). The two checks stop the bottom and left walks from visiting cells twice.",
        "Every lap removes at least one row or column, so the loop ends after at most m + n laps.",
    ],
    "relies_on": "updating each boundary right after its side is walked, and re-checking before the third and fourth sides.",
}


def spiral(matrix):
    out = []
    top, bottom, left, right = 0, len(matrix) - 1, 0, len(matrix[0]) - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            out.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):
            out.append(matrix[r][right])
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                out.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                out.append(matrix[r][left])
            left += 1
    return out


def power(x, n):
    result = 1
    while n > 0:
        if n % 2 == 1:
            result *= x
        x *= x
        n //= 2
    return result


REFERENCE = spiral


def view(S):
    if S.func == "power":
        n = S.v["n"]
        bits = list(bin(n)[2:]) if n else ["0"]
        return [V.array("n in binary (the last bit decides whether x is multiplied in)", bits, cls={len(bits) - 1: "cur"},
                        labels=[f"2^{len(bits) - 1 - j}" for j in range(len(bits))]),
                V.vars(("x", S.v["x"]), ("n", n), ("result", S.v.get("result")))]
    m = S.outer["matrix"]
    out = S.v.get("out", [])
    seen = set(out)
    t, b, l, r = (S.v.get(k) for k in ("top", "bottom", "left", "right"))
    cls = {}
    for i, row_ in enumerate(m):
        for j, x in enumerate(row_):
            if x in seen:
                cls[(i, j)] = "done"
            elif t is not None and t <= i <= b and l <= j <= r:
                cls[(i, j)] = "win"
    if out:
        last = out[-1]
        for i, row_ in enumerate(m):
            for j, x in enumerate(row_):
                if x == last:
                    cls[(i, j)] = "cur"
    return [V.grid("matrix (light: still unvisited; blue: just added)", m, list(range(len(m))), list(range(len(m[0]))), cls),
            V.vars(("top", t), ("bottom", b), ("left", l), ("right", r)), V.items("out", out)]


def say(S, N):
    if S.text in ("top += 1", "right -= 1", "bottom -= 1", "left += 1"):
        name = S.text.split()[0]
        return f"That side is done: {name} moves in to {N.v[name]}."
    if S.text == "if top <= bottom:" and N.text != "for c in range(right, left - 1, -1):":
        return f"top {S.top} > bottom {S.bottom}: no row is left, so skip the bottom row."
    if S.text == "if left <= right:" and N.text != "for r in range(bottom, top - 1, -1):":
        return f"left {S.left} > right {S.right}: no column is left, so skip the left column."
    if S.text == "if n % 2 == 1:":
        return f"n = {S.n} is odd: multiply x = {S.x} into result." if S.n % 2 else f"n = {S.n} is even: result stays {S.result}."
    if S.text == "x *= x":
        return f"Square x: {S.x} → {S.x * S.x}. It now stands for the next power of two."
    return None


PREDICT = {
    "if top <= bottom:": {
        "q": lambda S: f"top = {S.top}, bottom = {S.bottom}. Is there a bottom row left to walk?",
        "options": ["yes", "no"],
        "answer": lambda S, N: "yes" if S.top <= S.bottom else "no",
        "why": "After the top row moved down, the rows left are top..bottom; none if top > bottom.",
        "times": 3,
    },
    "top += 1": {
        "q": "Which values did that top row add? (Write them in order.)",
        "answer": lambda S, N: ", ".join(map(str, S.outer["matrix"][S.top][S.left:S.right + 1])),
        "why": "Row top, from column left to right.",
        "when": lambda S: S.top > 0,
        "times": 1,
    },
    "if n % 2 == 1:": {
        "q": lambda S: f"n = {S.n}. Does x = {S.x} get multiplied into result?",
        "options": ["yes", "no"],
        "answer": lambda S, N: "yes" if S.n % 2 == 1 else "no",
        "why": "Only when n's lowest bit is 1.",
        "times": 3,
    },
}

ROW_COLS = ["lap", "top, bottom, left, right after", "out so far"]


def row(S, N):
    if S.text == "while top <= bottom and left <= right:" and S.v.get("out"):
        laps = sum(1 for t in S.trace[:S.index] if t.text == "while top <= bottom and left <= right:")
        return [laps, f"{S.top}, {S.bottom}, {S.left}, {S.right}", S.out]
    if S.text == "n //= 2":
        return [S.n, S.x, N.v["result"]]
    return None


def spiral_brute(matrix):
    m, n = len(matrix), len(matrix[0])
    seen, out, r, c, d = set(), [], 0, 0, 0
    moves = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    for _ in range(m * n):
        out.append(matrix[r][c])
        seen.add((r, c))
        dr, dc = moves[d]
        if not (0 <= r + dr < m and 0 <= c + dc < n) or (r + dr, c + dc) in seen:
            d = (d + 1) % 4
            dr, dc = moves[d]
        r, c = r + dr, c + dc
    return out


def INVARIANT(S):
    if S.func != "spiral" or S.text != "while top <= bottom and left <= right:":
        return True
    m = S.outer["matrix"]
    rect = {m[i][j] for i in range(S.v["top"], S.v["bottom"] + 1) for j in range(S.v["left"], S.v["right"] + 1)}
    return rect == {x for row_ in m for x in row_} - set(S.v["out"])


TRACES = [
    {"label": "Spiral of a 3 × 4 matrix", "args": ([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],),
     "expect": [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7],
     "about": "The light rectangle is what is left. On the second lap only one row remains, and the checks stop the walk from going back over it."},
    {"label": "One column", "args": ([[1], [2], [3]],), "expect": [1, 2, 3],
     "about": "After the top cell and the right column, left > right: the left-column walk must be skipped."},
    {"label": "3¹³ by squaring", "fn": power, "args": (3, 13), "expect": 1594323, "cols": ["n", "x after squaring", "result"],
     "about": "13 is 1101 in binary. Each loop handles one bit: multiply when it is 1, square x, shift n right."},
]


def mats(rng):
    out = [([[7]],), ([[1, 2]],), ([[1], [2]],)]
    for _ in range(200):
        m, n = rng.randint(1, 5), rng.randint(1, 5)
        vals = rng.sample(range(100), m * n)
        out.append(([vals[i * n:(i + 1) * n] for i in range(m)],))
    return out


ORACLE = [{"brute": spiral_brute, "inputs": mats},
          {"fn": power, "brute": lambda x, n: x ** n,
           "inputs": lambda rng: [(rng.randint(-5, 5), rng.randint(0, 40)) for _ in range(200)] + [(2, 0), (0, 0), (1, 10 ** 6)]}]

FAMILY_INTRO = "Name the bookkeeping out loud; most of these are an exact index rule plus one edge case."
FAMILY = [
    {"name": "Shrinking boundaries", "change": "The spiral traces. Rotate Image goes layer by layer with the same boundaries, or transposes and reverses each row.",
     "problems": ["spiral-matrix", "rotate-image"],
     "code": "for r in range(n):                 # transpose: swap across the diagonal\n    for c in range(r + 1, n):\n        m[r][c], m[c][r] = m[c][r], m[r][c]\nfor row in m:                      # then reverse each row: 90° clockwise\n    row.reverse()"},
    {"name": "Markers in place", "change": "Set Matrix Zeroes: record zero rows and columns in row 0 and column 0, with one extra flag for row 0 itself; clear from the bottom-right so the markers are read before they are overwritten.",
     "problems": ["set-matrix-zeroes"]},
    {"name": "Digit arithmetic", "change": "Plus One: carry from the last digit. Multiply Strings: `res[i + j + 1] += a[i] * b[j]`, then carry right to left.",
     "problems": ["plus-one", "multiply-strings"]},
    {"name": "Exponentiation by squaring", "change": "The third trace. For negative n, compute with −n and take the reciprocal.",
     "problems": ["powx-n"]},
    {"name": "Cycles and counting", "change": "Happy Number: a set of seen values, or slow and fast pointers. Detect Squares: count points in a hash map, and for each diagonal partner look up the other two corners.",
     "problems": ["happy-number", "detect-squares"]},
]

COUNT = {
    "fn": power,
    "line": "if n % 2 == 1:",
    "input": lambda n: (1, n),  # x = 1 keeps the numbers small; the loop count depends only on n
    "sizes": [2 ** 8 - 1, 2 ** 16 - 1, 2 ** 32 - 1, 2 ** 64 - 1],
    "bound": lambda n: n.bit_length(),
    "bound_text": "the number of bits of n",
    "n_name": "n (exponent)",
    "text": ["Each turn halves n, so the loop runs once per bit of n: about log₂ n turns. Squaring n (from 2⁸ to 2¹⁶, 2³², 2⁶⁴) "
             "only doubles the count. Multiplying x by itself n times would need n − 1 multiplications. (In Python, "
             "the numbers themselves grow, so each multiplication gets slower; with a modulus they stay small. The "
             "table is measured with x = 1 for that reason: the count of turns doesn't depend on x.) "
             "The spiral visits each of the m · n cells once: O(m · n)."],
    "time": "O(log n) multiplications for power; O(m · n) for the spiral.",
    "space": "O(1) beyond the output.",
}

TRAPS = [
    ("No re-check before the bottom row or left column", "walks a single remaining row or column twice."),
    ("Rotating with a copy", "when the problem says in place. Transpose, then reverse each row."),
    ("Negative exponents", "need the reciprocal: `power(1 / x, -n)`."),
    ("Carries processed left to right", "in digit arithmetic. Work from the least significant digit."),
]


CHECK = {
    "trace": {"text": "Run spiral on [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]. What does it return, and what is top after the first lap?",
              "args": ([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]],),
              "fields": [("Return value", lambda run: run["result"]),
                         ("top after the first lap", lambda run: [s.v["top"] for s in run["states"] if s.kind == "line" and s.text == "while top <= bottom and left <= right:"][1])]},
    "questions": [
        {"q": "How many multiplications (squarings plus multiplies into result) does power(x, 1024) need, roughly?",
         "options": ["About 1024", "About 11: 1024 has 11 bits", "About 32"], "answer": 1,
         "why": "One loop turn per bit; each turn squares once and multiplies at most once."},
        {"q": "Rotate an n × n matrix 90° counter-clockwise in place. Which steps?",
         "options": ["Transpose, then reverse each column (or reverse each row first, then transpose)", "Transpose only", "Spiral order"], "answer": 0,
         "why": "Clockwise is transpose + reverse rows; the mirror-image recipe turns the other way."},
    ],
    "own": {"prompt": "What keeps the spiral from visiting a cell twice, and why is squaring fast?",
            "model": "The unvisited cells are always the rectangle between top, bottom, left and right; each side walked is one edge of it, and its boundary moves in right after. When only one row or column is left, the first two sides use it up, so the checks top <= bottom and left <= right stop the last two sides. Squaring is fast because each loop turn handles one bit of n: x is squared so it stands for the next power of two, and multiplied into the result when that bit is 1. That is about log₂ n turns instead of n."},
}
