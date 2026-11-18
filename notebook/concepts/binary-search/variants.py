"""Loop-lab data for "Binary Search, explained" (v3).

Every binary-search loop is five choices: the loop guard, where hi starts, how mid
rounds, and the two updates (plus the comparison, and for some tasks what to return).
For each task this script writes every combination as real Python, runs it on every
small input under sys.settrace, and records whether it is correct. When it is not,
it records the first failing input and the trace of that run: the loop going round
on the same lo and hi, a wrong answer, or an IndexError.

    python3 variants.py                      # print the JSON
    python3 variants.py --page PAGE.html     # also write it into the page's variant-data tag
"""
import bisect
import itertools
import json
import re
import sys

COMMON = [
    ("guard", "Loop guard", ["<", "<="]),
    ("start", "hi starts at", None),  # filled per task
    ("mid", "mid", ["(lo + hi) // 2", "(lo + hi + 1) // 2"]),
    ("lo", "lo update", ["mid + 1", "mid"]),
    ("hi", "hi update", ["mid", "mid - 1"]),
]

TASKS = [
    {
        "id": "exact",
        "title": "Find the target (Binary Search, LC 704)",
        "goal": "Return the index of target in sorted, distinct nums, or -1.",
        "template": """def search(nums, target):
    lo, hi = 0, {start}
    while lo {guard} hi:
        mid = {mid}
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = {lo}
        else:
            hi = {hi}
    return -1""",
        "start": ["len(nums) - 1", "len(nums)"],
        "extra": [],
        "initial": {"guard": "<=", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid - 1"},
    },
    {
        "id": "lower",
        "title": "First index with nums[i] >= target (Search Insert Position, LC 35)",
        "goal": "Return the first index whose value is at least target; len(nums) if there is none. Duplicates allowed.",
        "template": """def first_at_least(nums, target):
    lo, hi = 0, {start}
    while lo {guard} hi:
        mid = {mid}
        if {cmp}:
            lo = {lo}
        else:
            hi = {hi}
    return lo""",
        "start": ["len(nums)", "len(nums) - 1"],
        "extra": [("cmp", "Go right when", ["nums[mid] < target", "nums[mid] <= target"])],
        "initial": {"guard": "<", "start": "len(nums)", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid", "cmp": "nums[mid] < target"},
    },
    {
        "id": "sqrt",
        "title": "Last true: integer square root (Sqrt(x), LC 69)",
        "goal": "Return the largest k with k * k <= x, for x >= 0.",
        "template": """def my_sqrt(x):
    lo, hi = 0, {start}
    while lo {guard} hi:
        mid = {mid}
        if {cmp}:
            lo = {lo}
        else:
            hi = {hi}
    return {ret}""",
        "start": ["x", "x + 1"],
        "extra": [
            ("cmp", "Go right when", ["mid * mid <= x", "mid * mid < x"]),
            ("ret", "Return", ["lo", "lo - 1", "hi"]),
        ],
        "initial": {"guard": "<", "start": "x", "mid": "(lo + hi + 1) // 2", "lo": "mid", "hi": "mid - 1", "cmp": "mid * mid <= x", "ret": "lo"},
    },
    {
        "id": "minrot",
        "title": "Minimum of a rotated sorted array (LC 153)",
        "goal": "Return the smallest value of a sorted, distinct array rotated 1 to n times.",
        "spoiler": "find-minimum-in-rotated-sorted-array",
        "template": """def find_min(nums):
    lo, hi = 0, {start}
    while lo {guard} hi:
        mid = {mid}
        if {cmp}:
            lo = {lo}
        else:
            hi = {hi}
    return nums[lo]""",
        "start": ["len(nums) - 1", "len(nums)"],
        "extra": [("cmp", "Go right when", ["nums[mid] > nums[lo]", "nums[mid] > nums[hi]", "nums[mid] >= nums[hi]"])],
        # starts broken on purpose: the exact-match loop, comparing with lo
        "initial": {"guard": "<=", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid - 1", "cmp": "nums[mid] > nums[lo]"},
    },
    {
        "id": "rotsearch",
        "title": "Target in a rotated sorted array (LC 33)",
        "goal": "Return the index of target in a sorted, distinct array rotated 1 to n times, or -1.",
        "template": """def search(nums, target):
    lo, hi = 0, {start}
    while lo {guard} hi:
        mid = {mid}
        if nums[mid] == target:
            return mid
        if {cmp}:  # left half sorted
            if nums[lo] <= target < nums[mid]:
                hi = {hi}
            else:
                lo = {lo}
        else:  # right half sorted
            if nums[mid] < target <= nums[hi]:
                lo = {lo}
            else:
                hi = {hi}
    return -1""",
        "start": ["len(nums) - 1", "len(nums)"],
        "extra": [("cmp", "Left half sorted when", ["nums[lo] <= nums[mid]", "nums[lo] < nums[mid]", "nums[mid] > nums[hi]"])],
        "initial": {"guard": "<=", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid - 1", "cmp": "nums[lo] <= nums[mid]"},
    },
]

# The versions the page teaches. The build fails if any of them is not correct.
CANONICAL = {
    "exact": [
        {"guard": "<=", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid - 1"},
        {"guard": "<", "start": "len(nums)", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid"},
    ],
    "lower": [{"guard": "<", "start": "len(nums)", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid", "cmp": "nums[mid] < target"}],
    "sqrt": [
        {"guard": "<", "start": "x", "mid": "(lo + hi + 1) // 2", "lo": "mid", "hi": "mid - 1", "cmp": "mid * mid <= x", "ret": "lo"},
        {"guard": "<", "start": "x + 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid", "cmp": "mid * mid <= x", "ret": "lo - 1"},
    ],
    "minrot": [{"guard": "<", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid", "cmp": "nums[mid] > nums[hi]"}],
    "rotsearch": [
        {"guard": "<=", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid - 1", "cmp": "nums[lo] <= nums[mid]"},
        {"guard": "<=", "start": "len(nums) - 1", "mid": "(lo + hi) // 2", "lo": "mid + 1", "hi": "mid - 1", "cmp": "nums[mid] > nums[hi]"},
    ],
}

ODD = lambda n: list(range(1, 2 * n, 2))  # [1, 3, 5, ...]: every miss is an even target


def rotations(values):
    return [values[k:] + values[:k] for k in range(len(values))]


def inputs(task_id):
    """(args, expected) for every small input, smallest first."""
    if task_id == "exact":
        for n in range(0, 7):
            nums = ODD(n)
            for t in range(0, 2 * n + 1):
                yield (nums, t), (nums.index(t) if t in nums else -1)
    elif task_id == "lower":
        for n in range(0, 6):
            for nums in itertools.combinations_with_replacement([1, 2, 3], n):
                for t in range(0, 5):
                    yield (list(nums), t), bisect.bisect_left(nums, t)
    elif task_id == "sqrt":
        for x in range(0, 41):
            yield (x,), int(x ** 0.5)
    elif task_id == "minrot":
        for n in range(1, 8):
            for nums in rotations(ODD(n)):
                yield (nums,), min(nums)
    elif task_id == "rotsearch":
        for n in range(1, 7):
            for nums in rotations(ODD(n)):
                for t in range(0, 2 * n + 1):
                    yield (nums, t), (nums.index(t) if t in nums else -1)


DEMO = {
    "exact": ([1, 3, 5, 7, 9, 11, 13], 9),
    "lower": ([1, 2, 2, 2, 3], 2),
    "sqrt": (20,),
    "minrot": ([9, 11, 13, 1, 3, 5, 7],),
    "rotsearch": ([7, 9, 11, 1, 3, 5], 3),
}


def slots(task):
    out = []
    for key, label, options in COMMON:
        out.append({"key": key, "label": label, "options": task["start"] if key == "start" else options})
    for key, label, options in task["extra"]:
        out.append({"key": key, "label": label, "options": options})
    return out


def source(task, choice):
    return task["template"].format(**choice)


class Stuck(Exception):
    pass


def compile_fn(src):
    space = {}
    exec(compile(src, "<variant>", "exec"), space)
    return next(v for v in space.values() if callable(v))


def run(src, args):
    """Run one variant under sys.settrace. Returns kind, result, rows, end state, error."""
    fn = compile_fn(src)
    lines = src.splitlines()
    while_line = next(i for i, l in enumerate(lines, 1) if l.strip().startswith("while "))
    mid_line = next(i for i, l in enumerate(lines, 1) if l.strip().startswith("mid = "))
    code = fn.__code__
    rows, seen, last = [], set(), [None]

    def tracer(frame, event, arg):
        if frame.f_code is not code:
            return None
        if event == "line":
            n = frame.f_lineno - code.co_firstlineno + 1
            loc = frame.f_locals
            if n == while_line:
                state = (loc["lo"], loc["hi"])
                last[0] = list(state)
                if state in seen:
                    raise Stuck(state)
                seen.add(state)
            elif n == mid_line + 1:
                rows.append([loc["lo"], loc["hi"], loc["mid"]])
        return tracer

    sys.settrace(tracer)
    try:
        result = fn(*args)
        kind, err = "ok", None
    except Stuck:
        kind, result, err = "stuck", None, None
    except IndexError as e:
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        kind, result = "crash", None
        line = lines[tb.tb_lineno - 1].strip()
        loc = tb.tb_frame.f_locals
        where = ", ".join(f"{k} = {loc[k]}" for k in ("lo", "hi", "mid") if k in loc)
        err = f"IndexError on `{line}` ({where}, len(nums) = {len(args[0])})"
        if not lines[tb.tb_lineno - 1].startswith(" " * 8):
            err += " after the loop"
    finally:
        sys.settrace(None)
    return kind, result, rows, last[0], err


def show(args, task_id):
    if task_id == "sqrt":
        return f"x = {args[0]}"
    if task_id == "minrot":
        return f"nums = {args[0]}"
    return f"nums = {args[0]}, target = {args[1]}"


def evaluate(task, choice):
    src = source(task, choice)
    counts = {"stuck": 0, "wrong": 0, "crash": 0}
    first, upper_ok = None, task["id"] == "lower"
    for args, expected in inputs(task["id"]):
        kind, result, rows, end, err = run(src, args)
        if kind == "ok" and result != expected:
            kind = "wrong"
        if upper_ok and result != bisect.bisect_right(args[0], args[1]):
            upper_ok = False  # stuck or crashed runs return None, so they end this too
        if kind != "ok":
            counts[kind] += 1
            if first is None:
                first = {"v": kind, "in": show(args, task["id"]), "exp": expected, "got": result,
                         "rows": rows, "end": end, "err": err}
    if first is None:
        args = DEMO[task["id"]]
        kind, result, rows, end, err = run(src, args)
        assert kind == "ok", (task["id"], choice, kind)
        return {"v": "ok", "in": show(args, task["id"]), "got": result, "rows": rows, "end": end}
    first["k"] = counts
    if upper_ok:
        first["alt"] = "It does find something: the first index with nums[i] > target (the upper bound)."
    return first


# The three templates the page shows. They are checked here and the page prints them from the data.
TEMPLATES = {
    "spot": """def find(nums, target):
    lo, hi = 0, len(nums) - 1   # target, if present, is in [lo, hi]
    while lo <= hi:             # one unchecked element still counts
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid          # confirmed on the spot
        if nums[mid] < target:
            lo = mid + 1        # mid and its left: too small
        else:
            hi = mid - 1        # mid and its right: too big
    return -1                   # lo == hi + 1: nothing left""",
    "first": """def first_true(lo, hi, passes):
    # passes: False ... False True ... True on [lo, hi)
    while lo < hi:              # stop at one candidate
        mid = (lo + hi) // 2
        if passes(mid):
            hi = mid            # mid may be the first: keep it
        else:
            lo = mid + 1        # mid fails: drop it
    return lo                   # first True, or hi if none""",
    "last": """def last_true(lo, hi, passes):
    # passes: True ... True False ... False on [lo, hi]
    # and passes(lo) is True
    while lo < hi:
        mid = (lo + hi + 1) // 2  # round up so lo = mid moves
        if passes(mid):
            lo = mid            # mid may be the last: keep it
        else:
            hi = mid - 1        # mid fails: drop it
    return lo""",
}


def check_templates():
    find = compile_fn(TEMPLATES["spot"])
    for args, expected in inputs("exact"):
        assert find(*args) == expected, args
    first, last = compile_fn(TEMPLATES["first"]), compile_fn(TEMPLATES["last"])
    for lo in range(0, 4):
        for hi in range(lo, lo + 9):
            for flip in range(lo, hi + 1):  # first True at flip; flip == hi means none
                assert first(lo, hi, lambda k: k >= flip) == flip, (lo, hi, flip)
            for t in range(lo, hi + 1):  # last True at t
                assert last(lo, hi, lambda k: k <= t) == t, (lo, hi, t)


def check_claims():
    """Sentences on the page that quote a run."""
    find = compile_fn(TEMPLATES["spot"])
    assert find([1, 2, 2, 2, 3], 2) == 2  # an exact-match loop does not find the first occurrence (1)
    minrot = next(t for t in TASKS if t["id"] == "minrot")
    by_lo = dict(CANONICAL["minrot"][0], cmp="nums[mid] > nums[lo]")
    assert run(source(minrot, by_lo), ([1, 3, 5],))[1] == 5  # comparing with lo: unrotated input, wrong side


def build():
    check_templates()
    check_claims()
    out = []
    for task in TASKS:
        sl = slots(task)
        results = {}
        for picks in itertools.product(*[range(len(s["options"])) for s in sl]):
            choice = {s["key"]: s["options"][i] for s, i in zip(sl, picks)}
            results[".".join(map(str, picks))] = evaluate(task, choice)
        index = lambda choice: ".".join(str(s["options"].index(choice[s["key"]])) for s in sl)
        for choice in CANONICAL[task["id"]]:
            assert results[index(choice)]["v"] == "ok", (task["id"], choice, results[index(choice)])
        ok = sum(r["v"] == "ok" for r in results.values())
        out.append({
            "id": task["id"], "title": task["title"], "goal": task["goal"], "spoiler": task.get("spoiler"),
            "template": task["template"], "slots": sl, "initial": index(task["initial"]),
            "canonical": [index(c) for c in CANONICAL[task["id"]]], "okCount": ok,
            "inputs": sum(1 for _ in inputs(task["id"])), "results": results,
        })
        print(f"{task['id']}: {ok} of {len(results)} combinations correct on {out[-1]['inputs']} inputs", file=sys.stderr)
    return {"tasks": out, "templates": TEMPLATES}


def main():
    data = build()
    text = json.dumps(data, separators=(",", ":"))
    if "--page" in sys.argv:
        path = sys.argv[sys.argv.index("--page") + 1]
        page = open(path, encoding="utf-8").read()
        tag = re.compile(r'(<script id="variant-data" type="application/json">)(.*?)(</script>)', re.S)
        assert tag.search(page), "the page has no variant-data tag"
        page = tag.sub(lambda m: m.group(1) + text.replace("</", "<\\/") + m.group(3), page)
        open(path, "w", encoding="utf-8").write(page)
        print(f"wrote {len(text):,} bytes into {path}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
