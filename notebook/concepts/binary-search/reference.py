"""Trace source for "Binary Search, explained".

Runs the real algorithms under sys.settrace, records one step per executed
line, checks the invariant at every step, checks the answers against linear
scans, measures loop runs at n = 8, 16, 32, 64, 1024, and prints everything
as JSON for the page.

    python3 reference.py > trace.json
"""
import json
import math
import random
import sys

SEARCH = '''def search(nums, target):
    lo, hi = 0, len(nums)          # first i with nums[i] >= target is in [lo, hi]
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    if lo < len(nums) and nums[lo] == target:
        return lo
    return -1
'''

SQRT = '''def my_sqrt(x):
    lo, hi = 0, x + 1              # first k with k * k > x is in [lo, hi]
    while lo < hi:
        mid = (lo + hi) // 2
        if mid * mid <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1
'''

LINEAR = '''def linear(nums, target):
    for i in range(len(nums)):
        if nums[i] == target:
            return i
    return -1
'''

LO_EQUALS_MID = '''def search_lo_mid(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid
        else:
            hi = mid
    if lo < len(nums) and nums[lo] == target:
        return lo
    return -1
'''

CLOSED = '''def search_closed(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
'''

NO_GUARD = '''def search_no_guard(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    if nums[lo] == target:
        return lo
    return -1
'''


def load(src, name):
    env = {}
    exec(compile(src, "<%s>" % name, "exec"), env)
    return env[name]


search = load(SEARCH, "search")
my_sqrt = load(SQRT, "my_sqrt")
linear = load(LINEAR, "linear")
search_lo_mid = load(LO_EQUALS_MID, "search_lo_mid")
search_closed = load(CLOSED, "search_closed")
search_no_guard = load(NO_GUARD, "search_no_guard")


def run_traced(fn, *args, cap=None):
    """Return (result, events). One event per line about to run, plus the return.
    With cap, stop after that many line events and return ("stuck", events)."""
    events = []

    class Stuck(Exception):
        pass

    def tracer(frame, event, arg):
        if frame.f_code.co_name != fn.__name__:
            return None
        if event in ("line", "return"):
            snap = {k: json.loads(json.dumps(v)) for k, v in frame.f_locals.items()}
            events.append({"event": event, "line": frame.f_lineno, "locals": snap,
                           "ret": arg if event == "return" else None})
            if cap and len(events) > cap:
                raise Stuck()
        return tracer

    sys.settrace(tracer)
    try:
        result = fn(*args)
    except Stuck:
        result = "stuck"
    finally:
        sys.settrace(None)
    return result, events


def line_runs(fn, *args):
    _, events = run_traced(fn, *args)
    runs = {}
    for e in events:
        if e["event"] == "line":
            runs[e["line"]] = runs.get(e["line"], 0) + 1
    return runs


# ---------- step records for the page ----------
# Both functions have the same shape: line 3 loop test, 4 mid, 5 test, 6 lo = mid + 1, 8 hi = mid.
# pred(k) is the monotone question: search asks nums[k] >= target, my_sqrt asks k * k > x.

def build_steps(kind, args, predictions, fades):
    fn = search if kind == "search" else my_sqrt
    result, events = run_traced(fn, *args)
    if kind == "search":
        nums, target = args
        pred = lambda k: nums[k] >= target
        value = lambda k: nums[k]
        size = len(nums)
    else:
        (x,) = args
        pred = lambda k: k * k > x
        value = lambda k: k * k
        size = x + 2                   # the number line 0 .. x + 1
    steps, it = [], 0
    for idx, e in enumerate(events):
        loc = events[idx + 1]["locals"] if idx + 1 < len(events) else e["locals"]
        lo, hi, mid, line = loc.get("lo"), loc.get("hi"), loc.get("mid"), e["line"]
        if lo is not None:
            # Invariant: everything left of lo fails pred, everything from hi on passes it.
            assert all(not pred(k) for k in range(lo)), (kind, args, lo)
            assert all(pred(k) for k in range(hi, size)), (kind, args, hi)
        if e["event"] == "return":
            continue
        if (kind == "search" and line in (10, 11)) or (kind == "sqrt" and line == 9):
            r = result
            if kind == "search":
                say = ("Return %d: nums[%d] = %d is the target." % (r, r, args[1]) if r != -1 else
                       "Return −1: the first place target could sit holds something else, so it isn't in nums.")
            else:
                say = "Return %d − 1 = %d: the largest k with k * k <= %d." % (lo, r, args[0])
            step = {"line": line, "op": "return", "ret": r, "say": say}
        elif line == 2:
            step = {"line": line, "op": "init",
                    "say": ("lo, hi = 0, %d. Nothing is known yet: the unknown part is all of [0, %d)." % (hi, hi) if kind == "search" else
                            "lo, hi = 0, %d. k = %d surely has k * k > x, so the first such k is in [0, %d]." % (hi, hi, hi))}
        elif line == 3:
            if lo < hi:
                it += 1
                step = {"line": line, "op": "advance", "it": it,
                        "say": "lo = %d < hi = %d: %d candidate(s) still unknown, so keep going." % (lo, hi, hi - lo)}
            else:
                step = {"line": line, "op": "end",
                        "say": "lo = hi = %d: nothing is unknown. lo is the first position where the question flips to yes." % lo}
        elif line == 4:
            step = {"line": line, "op": "mid", "say": "mid = (%d + %d) // 2 = %d, the middle of the unknown part." % (lo, hi, mid)}
        elif line == 5:
            yes = pred(mid)
            if kind == "search":
                say = ("nums[%d] = %d < %d? %s." % (mid, value(mid), args[1], "No" if yes else "Yes"))
            else:
                say = ("%d * %d = %d <= %d? %s." % (mid, mid, value(mid), args[0], "No" if yes else "Yes"))
            step = {"line": line, "op": "test", "yes": yes, "say": say}
        elif line == 6:
            step = {"line": line, "op": "move", "side": "lo",
                    "say": ("lo = %d. mid and everything left of it fail the test, so they are ruled out. Unknown: [%d, %d)." % (lo, lo, hi))}
        elif line == 8:
            step = {"line": line, "op": "move", "side": "hi",
                    "say": ("hi = %d. mid passes the test and so does everything right of it; mid itself may be the answer, so it stays as hi. Unknown: [%d, %d)." % (hi, lo, hi))}
        elif line == 9 and kind == "search":
            nums = args[0]
            inside = lo < len(nums)
            step = {"line": line, "op": "final", "hit": inside and nums[lo] == args[1],
                    "say": ("lo = %d. Is nums[%d] = %d the target?" % (lo, lo, nums[lo]) if inside else
                            "lo = %d = len(nums): every value is smaller than target. The lo < len(nums) guard stops an IndexError." % lo)}
        else:
            continue
        step.update({"lo": lo, "hi": hi, "mid": mid if step["op"] in ("mid", "test", "move") else None})
        key = (step["op"], 0 if step["op"] in ("final", "return", "end") else it)
        if key in predictions:
            step["predict"] = predictions[key]
        if key in fades:
            step["fade"] = fades[key]
        steps.append(step)
    check_counts(steps, line_runs(fn, *args))
    return result, steps


def check_counts(steps, runs):
    """The page's live per-line counts must equal the tracer's counts."""
    counted = {}
    for st in steps:
        counted[st["line"]] = counted.get(st["line"], 0) + 1
    assert counted == runs, (counted, runs)


def race(nums, target):
    """Section 2: one compare per press, linear scan against binary search, same input."""
    _, events = run_traced(search, nums, target)
    bin_rows = []
    for idx, e in enumerate(events):
        if e["event"] == "line" and e["line"] == 5:
            loc = e["locals"]
            after = events[idx + 1]["locals"]
            nxt = events[idx + 2]["locals"]     # after lo or hi moved
            bin_rows.append({"lo": loc["lo"], "hi": loc["hi"], "mid": loc["mid"],
                             "new_lo": nxt["lo"], "new_hi": nxt["hi"]})
    lin = linear(nums, target)
    lin_compares = line_runs(linear, nums, target)[3]
    assert lin_compares == lin + 1
    return {"nums": nums, "target": target, "binary": bin_rows, "linear_compares": lin_compares,
            "found": search(nums, target)}


# ---------- checks ----------

def oracle_checks():
    rng = random.Random(11)
    cases = [([], 3), ([5], 5), ([5], 1), ([5], 9), ([2, 2, 2], 2), ([1, 3], 2), ([-7, -3, 0], -3)]
    for _ in range(4000):
        n = rng.randint(0, 12)
        nums = sorted(rng.randint(-8, 8) for _ in range(n))
        cases.append((nums, rng.randint(-10, 10)))
    for nums, t in cases:
        got = search(nums, t)
        want = nums.index(t) if t in nums else -1   # first occurrence
        assert got == want, (nums, t, got, want)
    for x in range(0, 3000):
        assert my_sqrt(x) == math.isqrt(x), x
    return len(cases) + 3000


def iterations(fn, *args):
    return line_runs(fn, *args).get(4, 0)


def doubling():
    rows = []
    for n in (8, 16, 32, 64, 1024):
        nums = list(range(0, 2 * n, 2))
        targets = range(-1, 2 * n + 1)        # every value, present or missing
        worst = max(iterations(search, nums, t) for t in targets)
        lin = max(line_runs(linear, nums, t).get(3, 0) for t in (nums[-1], -1))
        assert worst == math.floor(math.log2(n)) + 1 and lin == n
        rows.append({"n": n, "linear": lin, "binary": worst})
    return rows


def checks():
    fresh, ft = [3, 9, 14, 20, 27, 31, 40], 30
    _, ev = run_traced(search, fresh, ft)
    mids = [e["locals"]["mid"] for e in ev if e["event"] == "line" and e["line"] == 5]
    end = [e["locals"] for e in ev if e["event"] == "line" and e["line"] == 9][0]
    stuck, sev = run_traced(search_lo_mid, [1, 3], 3, cap=200)
    last = sev[-1]["locals"]
    try:
        no_guard = search_no_guard([1, 3, 5], 9)
    except IndexError as err:
        no_guard = "IndexError: %s" % err
    unsorted = [7, 1, 9, 3, 5]
    n_million = 10 ** 6
    return {
        "fresh": {"nums": fresh, "target": ft, "mids": mids, "lo": end["lo"], "ret": search(fresh, ft)},
        "dups": {"nums": [1, 2, 2, 2, 3, 5], "target": 2, "ret": search([1, 2, 2, 2, 3, 5], 2)},
        "beyond": {"nums": [1, 3, 5], "target": 9, "lo": len([1, 3, 5]), "ret": search([1, 3, 5], 9)},
        "million": {"n": n_million, "iters": math.floor(math.log2(n_million)) + 1,
                    "measured": iterations(search, list(range(n_million)), n_million - 1)},
        "lo_mid": {"call": "search_lo_mid([1, 3], 3)", "result": stuck, "lo": last["lo"], "hi": last["hi"]},
        "sqrt": {"x": 50, "ret": my_sqrt(50)},
        "closed_dups": search_closed([1, 2, 2, 2, 3, 5], 2),
        "no_guard": no_guard,
        "unsorted": {"nums": unsorted, "target": 7, "ret": search(unsorted, 7)},
    }


def main():
    main_nums, main_t = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91], 23
    _, main_steps = build_steps(
        "search", (main_nums, main_t),
        predictions={
            ("move", 1): {"q": "nums[5] = 23 is the target already. What does the loop do?",
                          "choices": ["return 5 now", "hi = 5 and keep going", "lo = 6 and keep going"],
                          "a": "hi = 5 and keep going",
                          "why": "This loop only ever asks 'is nums[mid] < target?'. A no means mid could be the first match, so it becomes hi; the loop stops when lo meets it."},
            ("move", 2): {"q": "nums[2] = 8 < 23. Which part stays unknown?",
                          "choices": ["[0, 2)", "[2, 5)", "[3, 5)"], "a": "[3, 5)",
                          "why": "8 and everything left of it is smaller than 23, so lo jumps past mid: lo = mid + 1 = 3."},
        },
        fades={("advance", 3): {"q": "Fill lo and hi before stepping on (as lo, hi):", "a": "3, 5"}})
    _, miss_steps = build_steps(
        "search", (main_nums, 13),
        predictions={("final", 0): {"q": "Loop over with lo = 4. What does search return?",
                                    "choices": ["4", "3", "−1"], "a": "−1",
                                    "why": "lo = 4 is where 13 would go (nums[4] = 16). It isn't 13, so the target is absent."}},
        fades={})
    _, dup_steps = build_steps(
        "search", ([1, 2, 2, 2, 3, 5], 2),
        predictions={("final", 0): {"q": "Three 2s, at indices 1, 2 and 3. Which index does lo land on?",
                                    "choices": ["1", "2", "3"], "a": "1",
                                    "why": "lo is the first index where nums[i] >= 2 is true: the leftmost 2."}},
        fades={})
    _, beyond_steps = build_steps("search", ([1, 3, 5], 9), predictions={}, fades={})
    _, sqrt_steps = build_steps(
        "sqrt", (20,),
        predictions={
            ("move", 1): {"q": "10 * 10 = 100 > 20. Which part stays unknown?",
                          "choices": ["[0, 10)", "[11, 21)", "[0, 9)"], "a": "[0, 10)",
                          "why": "10 already answers yes (k * k > x), so every k above it does too. 10 itself might be the first yes, so hi = 10."},
            ("move", 3): {"q": "2 * 2 = 4 <= 20. New lo?",
                          "choices": ["2", "3", "5"], "a": "3"},
        },
        fades={})
    out = {
        "code": {"search": SEARCH.rstrip("\n").split("\n"), "sqrt": SQRT.rstrip("\n").split("\n"),
                 "linear": LINEAR.rstrip("\n").split("\n"), "lo_mid": LO_EQUALS_MID.rstrip("\n").split("\n")},
        "presets": [
            {"id": "main", "label": "search([2, 5, 8, 12, 16, 23, 38, 56, 72, 91], 23)", "code": "search",
             "tape": main_nums, "target": main_t, "steps": main_steps},
            {"id": "miss", "label": "Missing: search(same nums, 13)", "code": "search", "tape": main_nums, "target": 13, "steps": miss_steps},
            {"id": "dups", "label": "Duplicates: search([1, 2, 2, 2, 3, 5], 2)", "code": "search", "tape": [1, 2, 2, 2, 3, 5], "target": 2, "steps": dup_steps},
            {"id": "beyond", "label": "Edge: search([1, 3, 5], 9)", "code": "search", "tape": [1, 3, 5], "target": 9, "steps": beyond_steps},
            {"id": "sqrt", "label": "On the answer: my_sqrt(20)", "code": "sqrt", "tape": list(range(22)), "x": 20, "steps": sqrt_steps},
        ],
        "race": race(list(range(3, 99, 6)), 87),
        "doubling": doubling(),
        "oracle_cases": oracle_checks(),
        "checks": checks(),
    }
    json.dump(out, sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
