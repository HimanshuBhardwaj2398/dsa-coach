"""Trace source for "Arrays & Hashing, explained".

Runs the real algorithms under sys.settrace, records one step per executed
line (with a copy of the locals), checks the invariant at every step, checks
the answers against brute force, measures line runs at n = 8, 16, 32, 64,
and prints everything as JSON for the page.

    python3 reference.py > trace.json
"""
import json
import random
import sys

TWO_SUM = '''def two_sum(nums, target):
    seen = {}                      # value -> index, for nums[:j]
    for j, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], j]
        seen[x] = j
'''

BRUTE = '''def two_sum_brute(nums, target):
    n = len(nums)
    for j in range(n):
        for i in range(j):
            if nums[i] + nums[j] == target:
                return [i, j]
'''

GROUP = '''def group_anagrams(strs):
    groups = {}                    # sorted letters -> words
    for s in strs:
        key = "".join(sorted(s))
        if key not in groups:
            groups[key] = []
        groups[key].append(s)
    return list(groups.values())
'''


def load(src, name):
    env = {}
    exec(compile(src, "<%s>" % name, "exec"), env)
    return env[name]


two_sum = load(TWO_SUM, "two_sum")
two_sum_brute = load(BRUTE, "two_sum_brute")
group_anagrams = load(GROUP, "group_anagrams")


def run_traced(fn, *args):
    """Return (result, events). One event per line about to run, plus the return."""
    events = []
    name = "<%s>" % fn.__name__

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != name:
            return None
        if event in ("line", "return"):
            snap = {}
            for k, v in frame.f_locals.items():
                snap[k] = json.loads(json.dumps(v))
            events.append({"event": event, "line": frame.f_lineno, "locals": snap,
                           "ret": json.loads(json.dumps(arg)) if event == "return" else None})
        return tracer

    sys.settrace(tracer)
    try:
        result = fn(*args)
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

def after_states(events):
    """Pair each event with the locals after its line ran (the next event's locals)."""
    out = []
    for idx, e in enumerate(events):
        after = events[idx + 1]["locals"] if idx + 1 < len(events) else e["locals"]
        loop_ended = e["line"] == 3 and e["event"] == "line" and events[idx + 1]["line"] != 4
        out.append((e, after, loop_ended))
    return out


def two_sum_steps(nums, target, predictions, fades):
    result, events = run_traced(two_sum, nums, target)
    steps = []
    for e, loc, loop_ended in after_states(events):
        seen = {int(k): v for k, v in loc.get("seen", {}).items()}
        j, x, need, line = loc.get("j"), loc.get("x"), loc.get("need"), e["line"]
        if line in (4, 5):
            # Invariant: while column j is examined, the map holds exactly the values of nums[:j].
            assert set(seen) == set(nums[:j]), (nums, j, seen)
        if e["event"] == "return":
            text = ("Returned %s: nums[%d] + nums[%d] = %d." % (e["ret"], e["ret"][0], e["ret"][1], target)
                    if e["ret"] else "No pair found: returns None.")
            step = {"line": line, "op": "return", "say": text}
        elif line == 2:
            step = {"line": line, "op": "init", "say": "Start with an empty map. It will hold every value to the left of j."}
        elif loop_ended:
            step = {"line": line, "op": "end", "say": "No values left: the loop ends."}
        elif line == 3:
            step = {"line": line, "op": "advance",
                    "say": "j = %d, x = %d. The map holds nums[:%d]: every value to the left of j." % (j, x, j)}
        elif line == 4:
            step = {"line": line, "op": "need",
                    "say": "need = %d − %d = %d. A partner for x must have this value." % (target, x, need)}
        elif line == 5:
            hit = need in seen
            step = {"line": line, "op": "lookup", "hit": hit,
                    "say": ("%d is in the map at index %d. One lookup answered all of column %d." % (need, seen[need], j)
                            if hit else
                            "%d is not in the map, so no i < %d pairs with x. One lookup ruled out all of column %d." % (need, j, j))}
        elif line == 6:
            step = {"line": line, "op": "found", "changed": need,
                    "say": "Return [seen[%d], j] = [%d, %d]." % (need, seen[need], j)}
        elif line == 7:
            step = {"line": line, "op": "insert", "changed": x,
                    "say": "Store %d → %d. The map now holds nums[:%d], ready for j = %d." % (x, j, j + 1, j + 1)}
        else:
            continue
        step.update({"j": j, "x": x, "need": need, "map": [[k, v] for k, v in seen.items()]})
        key = (step["op"], j)
        if key in predictions:
            step["predict"] = predictions[key]
        if key in fades:
            step["fade"] = fades[key]
        steps.append(step)
    check_counts(steps, line_runs(two_sum, nums, target))
    return result, steps


def group_steps(strs, predictions):
    result, events = run_traced(group_anagrams, strs)
    steps = []
    done = 0
    for e, loc, loop_ended in after_states(events):
        groups = loc.get("groups", {})
        s, key, line = loc.get("s"), loc.get("key"), e["line"]
        if e["event"] == "return":
            continue
        elif line == 8:
            step = {"line": line, "op": "result", "say": "Return the %d groups as a list of lists." % len(groups)}
        elif line == 2:
            step = {"line": line, "op": "init", "say": "Empty map. Each key will be a word's letters in sorted order."}
        elif loop_ended:
            step = {"line": line, "op": "end", "say": "No words left: the loop ends."}
        elif line == 3:
            step = {"line": line, "op": "advance", "say": 'Next word: "%s".' % s}
            key = None
        elif line == 4:
            step = {"line": line, "op": "key", "say": 'Sort the letters of "%s": key = "%s".' % (s, key)}
        elif line == 5:
            new = key not in groups
            step = {"line": line, "op": "lookup", "hit": not new,
                    "say": ('"%s" is not in the map yet: a new group.' % key if new
                            else '"%s" is already in the map: "%s" joins that group without being compared with any word.' % (key, s))}
        elif line == 6:
            step = {"line": line, "op": "newgroup", "changed": key, "say": 'Open an empty group under "%s".' % key}
        elif line == 7:
            done += 1
            # Invariant: after each append, the groups hold exactly the words seen so far.
            assert sorted(w for v in groups.values() for w in v) == sorted(strs[:done])
            step = {"line": line, "op": "append", "changed": key, "say": 'Append "%s" to group "%s".' % (s, key)}
        else:
            continue
        step.update({"s": s, "key": key, "map": [[k, list(v)] for k, v in groups.items()]})
        if (step["op"], s) in predictions:
            step["predict"] = predictions[(step["op"], s)]
        steps.append(step)
    check_counts(steps, line_runs(group_anagrams, strs))
    return result, steps


def check_counts(steps, runs):
    """The page's live per-line counts must equal the tracer's counts."""
    counted = {}
    for st in steps:
        if st["op"] != "return":
            counted[st["line"]] = counted.get(st["line"], 0) + 1
    # The tracer also sees the final failing `for` check; the page counts it too.
    assert counted == runs, (counted, runs)


def grid_columns(nums, target):
    """For each column j: cells brute force checks, and lookups hashing does."""
    cols = []
    brute_total = 0
    for j in range(len(nums)):
        checked = []
        for i in range(j):
            checked.append(i)
            if nums[i] + nums[j] == target:
                break
        brute_total += len(checked)
        hit = [i for i in checked if nums[i] + nums[j] == target]
        cols.append({"j": j, "checked": checked, "hit": hit[0] if hit else None,
                     "brute_total": brute_total, "hash_total": j + 1})
        if hit:
            break
    return cols


# ---------- checks ----------

def oracle_checks():
    rng = random.Random(7)
    cases = [([], 5), ([4], 8), ([3, 3], 6), ([-2, 7, -5], -7), ([1, 2, 3], 100)]
    for _ in range(3000):
        n = rng.randint(0, 9)
        cases.append(([rng.randint(-6, 6) for _ in range(n)], rng.randint(-8, 8)))
    for nums, t in cases:
        a, b = two_sum(nums, t), two_sum_brute(nums, t)
        assert (a is None) == (b is None), (nums, t, a, b)
        if a:
            i, j = a
            assert i < j and nums[i] + nums[j] == t
            assert j == b[1], "both stop at the first column that has a partner"
    words = ["eat", "tea", "tan", "ate", "nat", "bat", "", "a", "ab", "ba", "abc"]
    for _ in range(2000):
        strs = [rng.choice(words) for _ in range(rng.randint(0, 7))]
        got = sorted(sorted(g) for g in group_anagrams(strs))
        brute = []
        for w in strs:  # O(n^2) grouping by comparing with each group's first word
            for g in brute:
                if sorted(g[0]) == sorted(w):
                    g.append(w)
                    break
            else:
                brute.append([w])
        assert got == sorted(sorted(g) for g in brute), strs
    return len(cases)


def doubling():
    rows = []
    for n in (8, 16, 32, 64):
        nums = list(range(n))          # no pair sums to -1: the worst case, every column runs
        b = line_runs(two_sum_brute, nums, -1)
        h = line_runs(two_sum, nums, -1)
        rows.append({"n": n, "brute_compare": b[5], "hash_lookup": h[5],
                     "brute_formula": n * (n - 1) // 2, "hash_formula": n})
        assert b[5] == n * (n - 1) // 2 and h[5] == n
    return rows


INSERT_FIRST = '''def two_sum_insert_first(nums, target):
    seen = {}
    for j, x in enumerate(nums):
        seen[x] = j
        need = target - x
        if need in seen:
            return [seen[need], j]
'''


def checks():
    """Answers for the visual-hidden check, all computed by running code."""
    fresh, ft = [4, 6, 2, 5, 1], 7
    got, events = run_traced(two_sum, fresh, ft)
    final_map = events[-1]["locals"]["seen"]
    n = 100
    runs_b = line_runs(two_sum_brute, list(range(n)), -1)[5]
    runs_h = line_runs(two_sum, list(range(n)), -1)[5]
    buggy = load(INSERT_FIRST, "two_sum_insert_first")
    return {
        "fresh": {"nums": fresh, "target": ft, "ret": got,
                  "map": ", ".join("%s:%s" % (k, v) for k, v in final_map.items())},
        "n100": {"brute": runs_b, "hash": runs_h},
        "insert_first": {"call": "[3], 6", "ret": buggy([3], 6)},
        "groups": {"strs": ["ab", "ba", "b", "a"], "count": len(group_anagrams(["ab", "ba", "b", "a"]))},
    }


def main():
    main_nums, main_t = [5, 8, 1, 9, 4, 3], 7
    _, main_steps = two_sum_steps(
        main_nums, main_t,
        predictions={
            ("lookup", 1): {"q": "need = −1. Is −1 in the map?", "choices": ["yes", "no"], "a": "no"},
            ("lookup", 4): {"q": "need = 3, and 3 is in nums. Is 3 in the map right now?", "choices": ["yes", "no"], "a": "no",
                            "why": "3 sits at index 5, to the right of j = 4. The map only holds nums[:4]. The pair is found when j reaches 3's index instead."},
            ("lookup", 5): {"q": "need = 4. Is 4 in the map, and at which index?", "choices": ["no", "yes, index 4", "yes, index 0"], "a": "yes, index 4"},
        },
        fades={("advance", 4): {"q": "Fill the map before stepping on: type it as value:index pairs, e.g. 5:0, 8:1",
                                "a": "5:0, 8:1, 1:2, 9:3"}})
    _, edge_steps = two_sum_steps(
        [3, 3], 6,
        predictions={("lookup", 0): {"q": "j = 0, need = 3, and x itself is 3. Is 3 in the map?", "choices": ["yes", "no"], "a": "no",
                                     "why": "The check runs before the insert, so x can't pair with itself. Swap lines 5–6 and line 7 and [3] with target 6 would wrongly return [0, 0]."}},
        fades={})
    _, none_steps = two_sum_steps([2, 5, 9], 6, predictions={}, fades={})
    strs = ["eat", "tea", "tan", "ate", "nat", "bat"]
    _, group = group_steps(
        strs,
        predictions={("lookup", "ate"): {"q": 'key for "ate" is "aet". Is it already in the map?', "choices": ["yes", "no"], "a": "yes"},
                     ("lookup", "bat"): {"q": 'key for "bat" is "abt". Is it already in the map?', "choices": ["yes", "no"], "a": "no"}})
    out = {
        "code": {"two_sum": TWO_SUM.rstrip("\n").split("\n"), "brute": BRUTE.rstrip("\n").split("\n"),
                 "group": GROUP.rstrip("\n").split("\n")},
        "presets": [
            {"id": "main", "label": "two_sum([5, 8, 1, 9, 4, 3], 7)", "code": "two_sum", "tape": main_nums, "target": main_t, "steps": main_steps},
            {"id": "edge", "label": "Edge: two_sum([3, 3], 6)", "code": "two_sum", "tape": [3, 3], "target": 6, "steps": edge_steps},
            {"id": "none", "label": "No answer: two_sum([2, 5, 9], 6)", "code": "two_sum", "tape": [2, 5, 9], "target": 6, "steps": none_steps},
            {"id": "group", "label": "group_anagrams([eat, tea, tan, ate, nat, bat])", "code": "group", "tape": strs, "steps": group},
        ],
        "grid": {"nums": main_nums, "target": main_t, "cols": grid_columns(main_nums, main_t)},
        "doubling": doubling(),
        "oracle_cases": oracle_checks(),
        "checks": checks(),
    }
    json.dump(out, sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
