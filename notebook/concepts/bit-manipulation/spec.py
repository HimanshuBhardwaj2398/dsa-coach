"""Bit Manipulation, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/bit-manipulation/spec.py"""
from collections import Counter
from functools import reduce

from build_explainer import V

TITLE = "Bit Manipulation, explained"
PITCH = ("Treat an integer as a row of bits. A few identities do the work: x ^ x = 0 cancels pairs, and "
         "x & (x − 1) clears the lowest set bit.")

SPOT = {
    "idea": [
        "Bit problems look like tricks, but each rests on one identity you can check on paper. **XOR** is addition "
        "without carries: `x ^ x = 0` and `x ^ 0 = x`, in any order, so XOR-ing a list cancels every value that "
        "appears twice. **`x & (x − 1)`** turns off the lowest 1 bit (subtracting 1 flips that bit and every 0 below "
        "it), so a loop of it runs once per set bit. `x & 1` reads the lowest bit; `x >> 1` drops it.",
        "Reach for bits when a problem says 'appears twice except one', 'missing number', 'count the 1s', 'without + or −', "
        "or 'all subsets of n ≤ 20' (each subset is an n-bit mask). Python's integers never overflow, so 32-bit "
        "behaviour (negative numbers, the sign bit) needs an explicit mask: `& 0xFFFFFFFF`.",
    ],
    "questions": [
        ("Do equal values need to cancel?", "XOR them all: pairs vanish, the odd one out remains."),
        ("Do I need the set bits one at a time?", "`n & (n − 1)` drops the lowest; `n & -n` isolates it."),
        ("Is a subset small enough to be a mask?", "n ≤ 20: loop masks 0..2ⁿ − 1, bit i means item i is in."),
        ("Does 32-bit overflow matter?", "Mask with `0xFFFFFFFF`, and convert values ≥ 2³¹ back to negative."),
    ],
    "cases": [
        {"text": "Every value appears twice except one. Find it with O(1) extra space.",
         "options": ["XOR all values", "A hash map of counts", "Sort and scan"], "answer": 0,
         "why": "Pairs cancel (x ^ x = 0) in any order; what remains is the single value. O(n) time, O(1) space."},
        {"text": "The numbers 0..n with one missing. Find it.",
         "options": ["XOR the indices with the values (or subtract the sum from n(n + 1)/2)", "Binary search", "A heap"], "answer": 0,
         "why": "Every present number cancels its index; the missing one is left."},
        {"text": "Count the 1 bits of an integer.",
         "options": ["Repeat n &= n − 1, counting", "Convert to a string of 0s and 1s and loop", "Sort the bits"], "answer": 0,
         "why": "One turn per set bit. (bin(n).count('1') is fine in practice; the interview wants the reason.)"},
        {"text": "Is n a power of two?",
         "options": ["n > 0 and n & (n − 1) == 0", "n % 2 == 0", "Loop dividing by 2"], "answer": 0,
         "why": "A power of two has exactly one set bit; clearing it leaves 0."},
        {"text": "Add two integers without using + or −.",
         "options": ["XOR for the sum without carries, AND shifted left for the carries, repeat", "Repeated increment", "Logarithms"], "answer": 0,
         "why": "a ^ b adds without carrying; (a & b) << 1 is the carries. In Python, mask to 32 bits so it ends."},
        {"text": "The element that appears more than n/2 times.",
         "options": ["XOR all values", "Boyer-Moore voting or a hash map", "n & (n − 1)"], "answer": 1,
         "why": "XOR only cancels pairs; a majority isn't a pairing problem. (Counting each bit position also works.)"},
    ],
    "near_misses": [
        ("Every value appears three times except one.", "XOR alone fails; count each bit position mod 3."),
        ("Two values appear once.", "XOR everything, then split the values by any set bit of the result and XOR each group."),
        ("Large numbers as strings.", "That's digit arithmetic, not bits."),
    ],
}

PARTS = {
    "names": [
        ("acc", "the XOR of every value seen so far"),
        ("x ^ x = 0", "a value cancels itself"),
        ("x ^ 0 = x", "zero changes nothing, so acc starts at 0"),
    ],
    "plan": [
        ("Start", "`acc = 0`."),
        ("Each value", "`acc ^= x`."),
        ("Order", "doesn't matter: XOR is commutative and associative."),
        ("Stop", "every pair has cancelled; acc is the single value."),
    ],
    "invariant": "acc is the XOR of the values processed so far, which equals the XOR of those that have appeared an odd number of times.",
    "safe": [
        "XOR works bit by bit: each output bit is 1 when an odd number of inputs have a 1 there.",
        "A value seen twice contributes its 1s twice to every bit, an even count, so it vanishes from acc.",
        "Only the single value has an odd count, so acc ends equal to it.",
    ],
    "relies_on": "every other value appearing an even number of times. With triples, XOR leaves the wrong answer.",
}


def single_number(nums):
    acc = 0
    for i, x in enumerate(nums):
        acc ^= x
    return acc


def count_ones(n):
    count = 0
    while n:
        n &= n - 1
        count += 1
    return count


REFERENCE = single_number
WIDTH = 4


def bits(value, width=WIDTH):
    return list(format(value, f"0{width}b"))


def view(S):
    if S.func == "count_ones":
        n = S.v["n"]
        width = max(4, S.outer["n"].bit_length() if "n" in S.outer else 4)
        b = bits(n, width)
        low = next((j for j in range(len(b) - 1, -1, -1) if b[j] == "1"), None)
        return [V.array("n in binary (blue: the lowest 1, which n & (n − 1) clears)", b, cls={low: "cur"} if low is not None else {},
                        labels=[str(2 ** (width - 1 - j)) for j in range(width)]),
                V.vars(("n", n), ("count", S.v.get("count")))]
    nums, i, acc = S.outer["nums"], S.v.get("i"), S.v.get("acc")
    out = [V.array("nums", nums, {"i": i}, {j: ("cur" if j == i else "done" if i is not None and j < i else "") for j in range(len(nums))})]
    if acc is not None:
        rows = [bits(acc)]
        heads = ["acc"]
        if i is not None and S.text == "acc ^= x":
            rows = [bits(acc), bits(S.v["x"])]
            heads = ["acc", f"x = {S.v['x']}"]
        cls = {}
        if len(rows) == 2:
            cls = {(1, j): "cur" for j in range(WIDTH) if rows[1][j] == "1"}
        out.append(V.grid("bits (8 4 2 1)", rows, heads, [8, 4, 2, 1], cls))
        out.append(V.vars(("acc", acc), ("acc in binary", format(acc, f"0{WIDTH}b"))))
    return out


def say(S, N):
    if S.text == "acc ^= x":
        return f"{format(S.acc, '04b')} ^ {format(S.x, '04b')} = {format(N.v['acc'], '04b')}: acc = {N.v['acc']}."
    if S.text == "n &= n - 1":
        return f"{format(S.n, 'b')} & {format(S.n - 1, 'b')} = {format(N.v['n'], 'b') if N.v['n'] else '0'}: the lowest 1 is gone."
    return None


PREDICT = {
    "acc ^= x": {
        "q": lambda S: f"acc = {format(S.acc, '04b')}, x = {format(S.x, '04b')}. acc ^ x in binary?",
        "answer": lambda S, N: format(N.v["acc"], "04b"),
        "why": "Each bit is 1 where exactly one of the two has a 1.",
        "when": lambda S: S.i >= 1,
        "times": 3,
    },
    "n &= n - 1": {
        "q": lambda S: f"n = {format(S.n, 'b')}. What is n after n &= n − 1, in binary?",
        "answer": lambda S, N: format(N.v["n"], "b") if N.v["n"] else "0",
        "why": "n − 1 flips the lowest 1 and every 0 below it; AND keeps only what both share.",
        "times": 2,
    },
}

ROW_COLS = ["i", "x", "acc after", "binary"]


def row(S, N):
    if S.text == "acc ^= x":
        return [S.i, S.x, N.v["acc"], format(N.v["acc"], "04b")]
    if S.text == "n &= n - 1":
        return [format(S.n, "b"), format(N.v["n"], "b") if N.v["n"] else "0", "", ""]
    return None


def INVARIANT(S):
    if S.func == "single_number" and S.text == "for i, x in enumerate(nums):" and "i" in S.v:
        done = S.outer["nums"][:S.v["i"] + 1]
        odd = [x for x, c in Counter(done).items() if c % 2]
        return S.v["acc"] == reduce(lambda a, b: a ^ b, done, 0) == reduce(lambda a, b: a ^ b, odd, 0)
    return True


TRACES = [
    {"label": "[4, 1, 2, 1, 2]", "args": ([4, 1, 2, 1, 2],), "expect": 4,
     "about": "Watch the 1s and the 2s each switch their bits on and then off again."},
    {"label": "Count the 1s in 11 (1011)", "fn": count_ones, "args": (11,), "expect": 3,
     "cols": ["n before", "n after", "", ""],
     "about": "Three set bits, three turns: each n &= n − 1 removes the lowest one."},
]


def pairs_plus_one(rng):
    out = [([7],), ([0, 3, 3],)]
    for _ in range(200):
        vals = rng.sample(range(0, 50), rng.randint(1, 6))
        nums = vals[1:] * 2 + [vals[0]]
        rng.shuffle(nums)
        out.append((nums,))
    return out


ORACLE = [{"brute": lambda nums: next(x for x, c in Counter(nums).items() if c == 1), "inputs": pairs_plus_one},
          {"fn": count_ones, "brute": lambda n: bin(n).count("1"),
           "inputs": lambda rng: [(rng.randint(0, 2 ** 20),) for _ in range(200)] + [(0,), (1,), (2 ** 31 - 1,)]}]

FAMILY_INTRO = "Each member is one identity, used on purpose. Say the identity, then write the loop."
FAMILY = [
    {"name": "Cancel pairs with XOR", "change": "The first trace. Missing Number XORs every index 0..n with every value: present numbers cancel their index.",
     "problems": ["single-number", "missing-number"]},
    {"name": "Clear the lowest set bit", "change": "The second trace. Counting Bits for 0..n: `bits[i] = bits[i & (i - 1)] + 1`, or `bits[i >> 1] + (i & 1)`: DP over bits.",
     "problems": ["number-of-1-bits", "counting-bits"]},
    {"name": "Shift and mask", "change": "Reverse Bits: 32 times, shift the result left and add `n & 1`, then shift n right.",
     "problems": ["reverse-bits"]},
    {"name": "Add without +", "change": "Repeat `a, b = (a ^ b) & MASK, ((a & b) << 1) & MASK` until b is 0; a value above 2³¹ − 1 is negative in 32 bits: `~(a ^ MASK)`.",
     "problems": ["sum-of-two-integers"]},
    {"name": "Overflow by hand", "change": "Reverse Integer: build the reversed digits and return 0 if the result leaves [−2³¹, 2³¹ − 1].",
     "problems": ["reverse-integer"]},
]

COUNT = {
    "fn": count_ones,
    "line": "n &= n - 1",
    "input": lambda n: (n,),
    "sizes": [2 ** 8 - 1, 2 ** 16 - 1, 2 ** 32 - 1, 2 ** 64 - 1],
    "bound": lambda n: bin(n).count("1"),
    "bound_text": "the number of 1 bits in n",
    "n_name": "n (all bits 1)",
    "text": ["The loop runs once per set bit, never more than the number of bits. These inputs are all 1s, the worst "
             "case: 8, 16, 32, 64 turns. A loop that shifts one bit at a time always runs once per bit, even for a "
             "number with a single 1. Single Number is one XOR per value: O(n)."],
    "time": "O(set bits) for counting; O(n) for Single Number.",
    "space": "O(1)",
}

TRAPS = [
    ("`x & 1 == 0`", "parses as `x & (1 == 0)`. Write `(x & 1) == 0`."),
    ("`~x` expecting a 32-bit flip", "in Python, `~x` is `-x - 1`. Mask with `0xFFFFFFFF`."),
    ("Negative numbers with `>>`", "Python's shift keeps the sign and never stops for -1. Mask first."),
    ("XOR when values appear three times", "leaves garbage. Count each bit position mod 3."),
]


CHECK = {
    "trace": {"text": "Run single_number on [6, 3, 5, 3, 6]. Write acc after each value, and the return value.",
              "args": ([6, 3, 5, 3, 6],),
              "fields": [("acc after each value", lambda run: ", ".join(str(s.v["acc"]) for s in run["states"][1:] if s.trace[s.index - 1].text == "acc ^= x")),
                         ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "n = 40 (101000 in binary). What is n & (n − 1)?",
         "options": ["32 (100000)", "39 (100111)", "8 (001000)"], "answer": 0,
         "why": "40 − 1 = 39 = 100111; AND with 101000 keeps 100000: the lowest 1 is cleared."},
        {"q": "Why is `n > 0 and n & (n - 1) == 0` a power-of-two test?",
         "options": ["Powers of two are even", "A power of two has one set bit, and clearing it leaves 0", "It isn't"], "answer": 1,
         "why": "n & (n − 1) clears the lowest 1; zero left means there was exactly one. n > 0 excludes 0."},
    ],
    "own": {"prompt": "Why does XOR-ing a list find the value that appears once, and when does it fail?",
            "model": "XOR acts on each bit separately: a bit of the result is 1 when an odd number of the inputs have a 1 there. Every value that appears twice puts its 1s in twice, an even count, so it disappears whatever the order; only the single value's bits survive. It fails when values repeat an odd number of times (three each), because then they don't cancel; count each bit position modulo 3 instead."},
}
