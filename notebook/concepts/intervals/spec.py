"""Intervals, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/intervals/spec.py"""
import heapq

from build_explainer import V

TITLE = "Intervals, explained"
PITCH = ("Sort the intervals, then sweep once. After sorting by start, an interval can only overlap the ones just "
         "before it, so one comparison with the last kept interval decides each step.")

SPOT = {
    "idea": [
        "Interval problems (meetings, ranges, bookings, balloons) ask how intervals **overlap**. Unsorted, any interval "
        "might overlap any other: n² pairs. **Sorted by start**, an interval that doesn't overlap the last merged one "
        "can't overlap anything earlier either, so one sweep with one comparison per interval is enough.",
        "What you sort by depends on the question. **By start** to merge or insert. **By end** to keep the most "
        "non-overlapping intervals (the one that ends first leaves the most room: a greedy exchange argument). For "
        "**how many at once**, sort the starts and keep a min-heap of end times, or sweep +1/−1 events.",
    ],
    "questions": [
        ("When do two intervals overlap?", "`a.start <= b.end and b.start <= a.end`. Check whether touching ends count."),
        ("What should they be sorted by?", "Start for merging; end for keeping the most; both event lists for counting."),
        ("Whom do I compare with?", "The last kept interval, not the previous one in the input."),
        ("Do I need how many overlap at a moment?", "A heap of end times, or a sweep of +1 at starts and −1 at ends."),
    ],
    "cases": [
        {"text": "Merge all overlapping intervals.",
         "options": ["Sort by start, extend or append against the last merged", "Sort by end, keep the earliest ending", "Union-find"], "answer": 0,
         "why": "Sorted by start, each interval either extends the last merged one or begins a new one."},
        {"text": "Remove the fewest intervals so the rest don't overlap.",
         "options": ["Sort by start and merge", "Sort by end, keep each that starts after the last kept end", "Dynamic programming over subsets"], "answer": 1,
         "why": "Keeping the interval that ends first leaves the most room for the rest (an exchange argument); the removed count is n − kept."},
        {"text": "The fewest meeting rooms for a list of meetings.",
         "options": ["Sort by start; a min-heap of end times", "Merge the intervals", "Binary search"], "answer": 0,
         "why": "The heap holds the rooms in use; if the earliest end is before a new start, that room is reused."},
        {"text": "Can one person attend all these meetings?",
         "options": ["Sort by start and check neighbours", "A heap", "BFS"], "answer": 0,
         "why": "After sorting, a conflict, if any, is between neighbours."},
        {"text": "Insert a new interval into a sorted, non-overlapping list.",
         "options": ["Three phases: before it, overlapping it (merge), after it", "Sort everything again", "A trie"], "answer": 0,
         "why": "The list is already sorted, so one O(n) pass adds the ones before, merges the overlapping ones, adds the rest."},
        {"text": "Sum of nums[l..r] for many (l, r) queries.",
         "options": ["Interval merging", "Prefix sums", "A heap"], "answer": 1,
         "why": "These ranges are queries over an array, not intervals to combine: prefix sums."},
    ],
    "near_misses": [
        ("Range sum queries.", "Ranges over an array: prefix sums, not interval sweeps."),
        ("Activities with weights (maximize total weight).", "Sorting by end isn't enough: weighted interval scheduling is DP with binary search."),
        ("Overlapping windows of a string.", "Sliding window: the window moves over the input, it isn't an input interval."),
    ],
}

PARTS = {
    "names": [
        ("intervals", "sorted by start, so starts never decrease"),
        ("merged", "the answer so far: sorted and non-overlapping"),
        ("merged[-1]", "the last merged interval, the only one a new interval can overlap"),
    ],
    "plan": [
        ("Sort", "by start."),
        ("Each interval", "if it starts at or before `merged[-1]`'s end, extend that end to `max(end, ...)`."),
        ("Otherwise", "it starts after everything kept so far: append it."),
        ("Stop", "after the last interval; `merged` is the answer."),
    ],
    "invariant": "merged is sorted and non-overlapping, and it covers exactly the intervals processed so far.",
    "safe": [
        "Every earlier merged interval ends before `merged[-1]` starts, and the new interval starts at or after `merged[-1]`'s start. So if it doesn't reach `merged[-1]`, it reaches nothing earlier.",
        "When it overlaps, the union is `[merged[-1].start, max(both ends)]`: `max`, because the new interval may end inside the last one.",
        "Sorting first is what makes the previous two bullets true; without it, a later interval could reach back over several merged ones.",
    ],
    "relies_on": "sorting by start. Decide once whether intervals that only touch (end == start) overlap; LeetCode's Merge Intervals says they do.",
}


def merge(intervals):
    intervals = sorted(intervals)
    merged = []
    for i, (start, end) in enumerate(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def min_rooms(meetings):
    ends = []
    for start, end in sorted(meetings):
        if ends and ends[0] <= start:
            heapq.heappop(ends)
        heapq.heappush(ends, end)
    return len(ends)


REFERENCE = merge


def view(S):
    if S.func == "min_rooms":
        meetings = sorted(S.outer["meetings"])
        start, ends = S.v.get("start"), S.v.get("ends", [])
        lo = min([a for a, _ in meetings] + [0])
        hi = max([b for _, b in meetings] + [1])
        spans = [(a, b, f"[{a}, {b})", "cur" if a == start and S.v.get("end") == b else "done" if start is not None and (a, b) < (start, S.v.get("end")) else "")
                 for a, b in meetings]
        return [V.bars("meetings, sorted by start (blue: this one)", spans, lo, hi),
                V.array("ends: min-heap of end times, one per room in use", ends, cls={0: "ok"} if ends else {}),
                V.vars(("start", start), ("rooms in use", len(ends)))]
    intervals, merged, i = S.v.get("intervals", []), S.v.get("merged", []), S.v.get("i")
    lo = min([a for a, _ in intervals] + [0])
    hi = max([b for _, b in intervals] + [1])
    spans = [(a, b, f"[{a}, {b}]", "cur" if j == i else "done" if i is not None and j < i else "") for j, (a, b) in enumerate(intervals)]
    out = [V.bars("intervals, sorted by start (blue: this one)", spans, lo, hi)]
    out.append(V.bars("merged so far (green: the last, the one to compare with)",
                      [(a, b, f"[{a}, {b}]", "ok" if j == len(merged) - 1 else "") for j, (a, b) in enumerate(merged)], lo, hi)
               if merged else V.items("merged so far", []))
    return out


def say(S, N):
    if S.text == "if merged and start <= merged[-1][1]:":
        if not S.merged:
            return f"Nothing merged yet: [{S.start}, {S.end}] starts the list."
        if S.start <= S.merged[-1][1]:
            return f"{S.start} ≤ {S.merged[-1][1]}: [{S.start}, {S.end}] overlaps {S.merged[-1]}."
        return f"{S.start} > {S.merged[-1][1]}: a gap, so [{S.start}, {S.end}] starts a new merged interval."
    if S.text == "merged[-1][1] = max(merged[-1][1], end)":
        return f"Extended the last merged interval to {N.v['merged'][-1]}."
    if S.text == "if ends and ends[0] <= start:":
        if S.ends and S.ends[0] <= S.start:
            return f"The room ending at {S.ends[0]} is free by {S.start}: reuse it."
        return f"No room is free at {S.start}: open another." if S.ends else "The first meeting opens the first room."
    return None


PREDICT = {
    "if merged and start <= merged[-1][1]:": {
        "q": lambda S: f"[{S.start}, {S.end}] against the last merged {S.merged[-1] if S.merged else 'none'}: extend it or start a new one?",
        "options": ["extend the last", "start a new one"],
        "answer": lambda S, N: "extend the last" if S.merged and S.start <= S.merged[-1][1] else "start a new one",
        "why": "Overlap means the new start is at or before the last merged end.",
        "when": lambda S: bool(S.merged),
        "times": 4,
    },
    "if ends and ends[0] <= start:": {
        "q": lambda S: f"A meeting starts at {S.start}; the earliest end in use is {S.ends[0] if S.ends else 'none'}. Reuse that room?",
        "options": ["yes: pop it, then push this end", "no: push this end as a new room"],
        "answer": lambda S, N: "yes: pop it, then push this end" if S.ends and S.ends[0] <= S.start else "no: push this end as a new room",
        "why": "Only the earliest-ending room can be free; if it isn't, none is.",
        "when": lambda S: bool(S.ends),
        "times": 3,
    },
}

ROW_COLS = ["interval", "last merged", "so", "merged after"]


def row(S, N):
    if S.text == "if merged and start <= merged[-1][1]:":
        last = S.merged[-1] if S.merged else "none"
        so = "extend" if S.merged and S.start <= S.merged[-1][1] else "append"
        after = next(t for t in S.trace[S.index + 1:] if t.text in ("for i, (start, end) in enumerate(intervals):",) or t.kind == "return")
        return [[S.start, S.end], last, so, after.v["merged"]]
    if S.text == "heapq.heappush(ends, end)":
        return [[S.start, S.end], sorted(S.ends), "", len(N.v["ends"])]
    return None


def brute_merge(intervals):
    out = [list(x) for x in intervals]
    changed = True
    while changed:
        changed = False
        for a in range(len(out)):
            for b in range(a + 1, len(out)):
                if out[a][0] <= out[b][1] and out[b][0] <= out[a][1]:
                    out[a] = [min(out[a][0], out[b][0]), max(out[a][1], out[b][1])]
                    del out[b]
                    changed = True
                    break
            if changed:
                break
    return sorted(out)


def brute_rooms(meetings):
    return max([sum(1 for a, b in meetings if a <= t < b) for t, _ in meetings] + [0])


def INVARIANT(S):
    if S.func != "merge" or S.text != "for i, (start, end) in enumerate(intervals):":
        return True
    merged = S.v["merged"]
    done = S.v["intervals"][:S.v["i"] + 1] if "i" in S.v else []
    ok = all(merged[j][1] < merged[j + 1][0] for j in range(len(merged) - 1))
    return ok and merged == brute_merge(done)


TRACES = [
    {"label": "Merge [1,3] [8,10] [2,6] [9,12] [15,18]", "args": ([[1, 3], [8, 10], [2, 6], [9, 12], [15, 18]],),
     "expect": [[1, 6], [8, 12], [15, 18]],
     "about": "After sorting by start, each interval is compared with the last merged one only."},
    {"label": "Touching ends, and one inside another", "args": ([[1, 4], [4, 5], [2, 3]],), "expect": [[1, 5]],
     "about": "[1, 4] and [4, 5] touch, which counts as overlap here; [2, 3] sits inside [1, 4], so max() keeps the end at 4."},
    {"label": "Meeting rooms", "fn": min_rooms, "args": ([[0, 30], [5, 10], [15, 20], [10, 15]],), "expect": 2,
     "cols": ["meeting", "ends before", "", "rooms"],
     "about": "A min-heap of end times holds one entry per room in use. The root is the room that frees first."},
]


def interval_inputs(rng):
    out = [([[1, 1]],), ([[1, 2], [3, 4]],), ([[1, 4], [4, 5]],), ([[1, 10], [2, 3], [4, 5]],)]
    for _ in range(300):
        items = []
        for _ in range(rng.randint(1, 7)):
            a = rng.randint(0, 15)
            items.append([a, a + rng.randint(0, 5)])
        out.append((items,))
    return out


def room_inputs(rng):
    out = []
    for _ in range(200):
        items = []
        for _ in range(rng.randint(0, 7)):
            a = rng.randint(0, 15)
            items.append([a, a + rng.randint(1, 6)])
        out.append((items,))
    return out


ORACLE = [{"brute": brute_merge, "inputs": interval_inputs},
          {"fn": min_rooms, "brute": brute_rooms, "inputs": room_inputs}]

FAMILY_INTRO = "Sort, then sweep. The members differ in the sort key and in what the sweep keeps."
FAMILY = [
    {"name": "Merge (sort by start)", "change": "The first traces. Inserting into an already sorted list skips the sort: add the intervals that end before the new one, merge the ones that overlap it, add the rest.",
     "problems": ["merge-intervals", "insert-interval"]},
    {"name": "Keep the most (sort by end)", "change": "Keep an interval when it starts at or after the last kept end; count the others as removed. Ending first never hurts: swap it into any optimal answer.",
     "problems": ["non-overlapping-intervals"]},
    {"name": "Any conflict at all?", "change": "Sort by start; a conflict, if any, is between neighbours.",
     "problems": ["meeting-rooms"]},
    {"name": "How many at once (a heap of ends)", "change": "The third trace. Equivalently, sort all starts and all ends and sweep: +1 at a start, −1 at an end; the peak is the answer.",
     "problems": ["meeting-rooms-ii"]},
    {"name": "Intervals against queries", "change": "Sort both. Sweep queries in order, pushing intervals that have started into a heap keyed by size, and popping the ones that ended before the query.",
     "problems": ["minimum-interval-to-include-each-query"]},
]

COUNT = {
    "line": "if merged and start <= merged[-1][1]:",
    "input": lambda n: ([[3 * i, 3 * i + 1] for i in range(n)][::-1],),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n,
    "bound_text": "n",
    "text": ["The comparison runs once per interval: n runs at O(1). But one line runs once and costs more: "
             "`sorted(intervals)` is O(n log n). The decisive cost is runs × cost of one run, so the sort decides: O(n log n). "
             "The heap version does n pushes and up to n pops at O(log n) each: also O(n log n)."],
    "time": "O(n log n), for the sort.",
    "space": "O(n) for the sorted copy and the output.",
}

TRAPS = [
    ("Comparing with the previous input interval", "instead of the last merged one misses chains like [1, 10], [2, 3], [4, 5]."),
    ("`merged[-1][1] = end` instead of `max(...)`", "shrinks the merged interval when the new one sits inside it."),
    ("Sorting by end to merge", "breaks the proof: an interval can then reach back over several merged ones."),
    ("Mixing `<` and `<=`", "decides whether touching intervals overlap. Read the problem: meetings [1, 5) and [5, 8) don't conflict."),
]


CHECK = {
    "trace": {"text": "Merge [[5, 7], [1, 2], [2, 4], [6, 9], [11, 12]]. What does merge return, and how many times does it extend rather than append?",
              "args": ([[5, 7], [1, 2], [2, 4], [6, 9], [11, 12]],),
              "fields": [("Return value", lambda run: run["result"]),
                         ("Times it extends", lambda run: sum(1 for s in run["states"] if s.kind == "line" and s.text == "merged[-1][1] = max(merged[-1][1], end)"))]},
    "questions": [
        {"q": "Keep the most non-overlapping intervals from [1, 10], [2, 3], [4, 5]. Which sort makes a one-pass greedy correct?",
         "options": ["By start: keep [1, 10] first", "By end: keep [2, 3], then [4, 5]", "By length"], "answer": 1,
         "why": "Taking the interval that ends first leaves the most room; [1, 10] would block both others."},
        {"q": "Meetings [1, 5) and [5, 8): one room or two?",
         "options": ["One: the first ends as the second starts", "Two: they touch"], "answer": 0,
         "why": "Half-open meetings that touch don't overlap, which is why the heap test is `ends[0] <= start`."},
    ],
    "own": {"prompt": "Why does sorting by start let you compare each interval with only the last merged one?",
            "model": "After sorting by start, every earlier merged interval ends before the last merged one begins, and the new interval starts no earlier than the last merged one. So if the new interval doesn't reach the last merged interval, it can't reach any earlier one; if it does, the union just extends the last end to the larger of the two. One comparison per interval, so the sweep is O(n) and the sort dominates at O(n log n)."},
}
