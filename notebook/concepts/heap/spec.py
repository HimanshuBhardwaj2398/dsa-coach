"""Heap / Priority Queue, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/heap/spec.py"""
import heapq

from build_explainer import V

TITLE = "Heap / Priority Queue, explained"
PITCH = ("When you only ever need the smallest (or largest) item of a changing collection, a heap gives it in O(1) "
         "and takes an insert or removal in O(log n). Keep k items, and the root is the k-th best.")

SPOT = {
    "idea": [
        "A heap is a complete binary tree stored in a list: the children of index k sit at 2k + 1 and 2k + 2, and every "
        "parent is ≤ its children. So the root `heap[0]` is the minimum, and a push or pop repairs one root-to-leaf "
        "path: O(log n).",
        "The pattern is **repeatedly take the best of a changing set**: the k largest of a stream, the next "
        "meeting to end, the next closest node, the smallest head of k sorted lists. Python's `heapq` is a min-heap; "
        "negate keys for a max-heap, and push `(key, tiebreak, item)` tuples when items don't compare.",
    ],
    "questions": [
        ("Do I need the best item repeatedly while items change?", "If you need it only once, a scan or a sort is simpler."),
        ("Do I need all n items, or only the best k?", "A heap of size k: O(n log k) time and O(k) space."),
        ("Smallest or largest?", "`heapq` is a min-heap. To keep the k largest, keep a min-heap of size k: its root is the one to evict."),
        ("Two halves at once?", "A median needs a max-heap of the lower half and a min-heap of the upper half."),
    ],
    "cases": [
        {"text": "The k-th largest element of an unsorted array, n = 10⁵, k = 10.",
         "options": ["A min-heap of size k", "Sort descending", "A max-heap of all n, popped k times"], "answer": 0,
         "why": "All three are correct. The size-k heap is O(n log k) time and O(k) space; sorting is O(n log n)."},
        {"text": "Keep the median of a stream of numbers, queried after every insert.",
         "options": ["Two heaps: lower half max-heap, upper half min-heap", "Sort after every insert", "A hash map"], "answer": 0,
         "why": "The two roots are the middle values; balancing the sizes after each insert is O(log n)."},
        {"text": "Merge k sorted lists into one sorted list.",
         "options": ["A heap of the k current heads", "Concatenate and sort", "Two pointers"], "answer": 0,
         "why": "The next output is the smallest head. A heap of k heads finds it in O(log k): O(N log k) total."},
        {"text": "For each day, how many days until a warmer temperature?",
         "options": ["A heap", "A monotonic stack", "Prefix sums"], "answer": 1,
         "why": "Next greater to the right is a monotonic stack: O(n), no log factor."},
        {"text": "Smash the two heaviest stones together repeatedly until at most one is left.",
         "options": ["A max-heap (negated values)", "Sort once and scan", "A queue"], "answer": 0,
         "why": "The set changes after every smash, and you need the two largest each time: pop twice, push the remainder."},
        {"text": "The k points closest to the origin.",
         "options": ["A max-heap of size k keyed by distance", "A min-heap of all n points", "BFS"], "answer": 0,
         "why": "Keep the k closest so far; the root is the farthest of them, the one to evict. Negate distances with heapq."},
    ],
    "near_misses": [
        ("The k most frequent elements.", "A heap of size k works; bucket sort by frequency is O(n). Either is fine in an interview."),
        ("The minimum of a sliding window.", "A heap needs lazy deletion; a monotonic deque does it in O(n)."),
        ("Sorted output of everything.", "Just sort. A heap pays off when items arrive or change between the times you need the best."),
    ],
}

PARTS = {
    "names": [
        ("heap", "a list with `heap[i] <= heap[2i + 1]` and `heap[i] <= heap[2i + 2]`, so `heap[0]` is the smallest"),
        ("k", "how many of the best items to keep"),
        ("heap[0]", "the root: with the k largest kept, the k-th largest so far"),
    ],
    "plan": [
        ("Start", "an empty heap."),
        ("Each value", "push it; if the heap now holds more than k, pop the smallest."),
        ("Stop", "after the last value, `heap[0]` is the k-th largest."),
        ("Push", "append at the end, then swap with the parent while smaller (sift up)."),
    ],
    "invariant": "After each value, the heap holds exactly the k largest values seen so far (fewer at the start), and its root is the smallest of them.",
    "safe": [
        "A popped value is the smallest of k + 1 candidates: at least k seen values are larger, so it can never be among the k largest. Dropping it is safe.",
        "Sift up only swaps a child with a larger parent, so after the swap the parent is the smaller of the two and the heap property holds above and below.",
        "The tree is complete, so its height is ⌊log₂ n⌋: a sift touches at most that many levels.",
    ],
    "relies_on": "a total order on the keys. With tuples, Python compares the next field on a tie: add a counter before items that don't compare.",
}


def kth_largest(nums, k):
    heap = []
    for i, x in enumerate(nums):
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]


def push(heap, x):
    heap.append(x)
    i = len(heap) - 1
    while i > 0:
        parent = (i - 1) // 2
        if heap[parent] <= heap[i]:
            break
        heap[i], heap[parent] = heap[parent], heap[i]
        i = parent
    return heap


REFERENCE = kth_largest


def heap_tree(heap, cls, name):
    pos, nodes, edges = {}, [], []
    depth = lambda i: (i + 1).bit_length() - 1
    width = 2 ** depth(max(len(heap) - 1, 0))
    for i, x in enumerate(heap):
        d = depth(i)
        slot = i - (2 ** d - 1)
        pos[i] = ((slot + 0.5) * (width / 2 ** d) - 0.5, d)
        nodes.append({"id": i, "label": x, "x": pos[i][0] * 0.9 + 0.5, "y": d, "cls": cls.get(i, ""), "tag": f"[{i}]"})
        if i:
            edges.append({"a": (i - 1) // 2, "b": i})
    return V.graph(name, nodes, edges, w=max(width * 0.9 + 1, 2), h=max(depth(max(len(heap) - 1, 0)) + 1, 1))


def view(S):
    heap = S.v.get("heap", [])
    if S.func == "push":
        i, parent = S.v.get("i"), S.v.get("parent")
        cls = {}
        if parent is not None and parent != i:
            cls[parent] = "front"
        if i is not None:
            cls[i] = "cur"
        return [heap_tree(heap, cls, "the heap as a tree (blue: the new item, amber: its parent)"),
                V.array("the same heap as a list", heap, {"i": i, "parent": parent}, cls),
                V.vars(("x", S.v.get("x")), ("i", i), ("parent", parent))]
    nums, k, i = S.outer["nums"], S.outer["k"], S.v.get("i")
    cls = {0: "ok"} if heap else {}
    return [V.array("nums", nums, {"i": i}, {j: ("cur" if j == i else "done" if i is not None and j < i else "") for j in range(len(nums))}),
            heap_tree(heap, cls, f"min-heap of the {k} largest so far (green: its root)"),
            V.array("heap as a list", heap, labels=[f"[{j}]" for j in range(len(heap))], cls=cls),
            V.vars(("k", k), ("len(heap)", len(heap)))]


def say(S, N):
    if S.text == "heapq.heappush(heap, x)":
        return f"Pushed {S.x}; it sifted up to its place. Root is now {N.v['heap'][0]}."
    if S.text == "heapq.heappop(heap)":
        return f"Popped {S.heap[0]}: it is smaller than {S.k} others kept, so it can't be among the {S.k} largest."
    if S.text == "heap[i], heap[parent] = heap[parent], heap[i]":
        return f"{S.heap[S.i]} < its parent {S.heap[S.parent]}: swapped them."
    if S.text == "if heap[parent] <= heap[i]:" and N.text == "break":
        return f"Parent {S.heap[S.parent]} ≤ {S.heap[S.i]}: the heap property holds, so stop."
    return None


PREDICT = {
    "if len(heap) > k:": {
        "q": lambda S: f"After pushing {S.x}, the heap holds {len(S.heap)} values and k = {S.k}. Which value is popped (or 'none')?",
        "answer": lambda S, N: S.heap[0] if len(S.heap) > S.k else "none",
        "why": lambda S, N: (f"The heap is over k, and the root {S.heap[0]} is the smallest kept." if len(S.heap) > S.k
                             else "The heap isn't over k yet, so nothing is popped."),
        "times": 4,
    },
    "if heap[parent] <= heap[i]:": {
        "q": lambda S: f"The new item {S.heap[S.i]} sits at [{S.i}]; its parent [{S.parent}] holds {S.heap[S.parent]}. Swap or stop?",
        "options": ["swap", "stop"],
        "answer": lambda S, N: "stop" if S.heap[S.parent] <= S.heap[S.i] else "swap",
        "why": "Swap while the parent is larger; stop when the parent is smaller or equal.",
        "times": 3,
    },
}

ROW_COLS = ["x", "heap after push", "popped", "root"]


def row(S, N):
    if S.text == "if len(heap) > k:":
        popped = S.heap[0] if len(S.heap) > S.k else ""
        after = sorted(S.heap)[1:] if popped != "" else sorted(S.heap)
        return [S.x, sorted(S.heap), popped, min(after) if len(after) == S.k else ""]
    if S.text == "heap[i], heap[parent] = heap[parent], heap[i]":
        return [S.heap[S.i], f"swap [{S.i}] and [{S.parent}]", "", list(N.v["heap"])]
    return None


def is_heap(h):
    return all(h[(i - 1) // 2] <= h[i] for i in range(1, len(h)))


def INVARIANT(S):
    heap = S.v.get("heap")
    if heap is None:
        return True
    if S.func == "kth_largest":
        if not is_heap(heap):
            return False
        if S.text == "heapq.heappush(heap, x)":  # before each push: the k largest of what came before
            seen = S.outer["nums"][:S.v["i"]]
            return sorted(heap) == sorted(seen)[-S.outer["k"]:] if seen else heap == []
        return True
    if S.text == "while i > 0:":  # sift up: the heap property holds everywhere except between i and its parent
        i = S.v["i"]
        return all(heap[(j - 1) // 2] <= heap[j] for j in range(1, len(heap)) if j != i)
    return True


TRACES = [
    {"label": "3rd largest of [5, 1, 9, 3, 7, 2, 8]", "args": ([5, 1, 9, 3, 7, 2, 8], 3), "expect": 7,
     "about": "Keep a min-heap of the 3 largest so far. Whenever it grows past 3, its root is the one that can't make the cut.",
     "cols": ["x", "kept (sorted)", "popped", "k-th largest so far"]},
    {"label": "Inside a push: sift 1 up", "fn": push, "args": ([2, 4, 3, 7, 9, 5], 1), "expect": [1, 4, 2, 7, 9, 5, 3],
     "about": "What heappush does: append at the end, then swap upward while the parent is larger.",
     "cols": ["item", "move", "", "heap"]},
]


def inputs(rng):
    cases = [([4], 1), ([1, 1, 1], 2), ([-1, -2], 2), ([3, 2, 1, 5, 6, 4], 2)]
    for _ in range(300):
        n = rng.randint(1, 10)
        cases.append(([rng.randint(-9, 9) for _ in range(n)], rng.randint(1, n)))
    return cases


def push_inputs(rng):
    out = []
    for _ in range(200):
        h = [rng.randint(-9, 9) for _ in range(rng.randint(0, 10))]
        heapq.heapify(h)
        out.append((h, rng.randint(-10, 10)))
    return out


ORACLE = [{"brute": lambda nums, k: sorted(nums)[-k], "inputs": inputs},
          {"fn": push, "brute": lambda h, x: sorted(h + [x]), "inputs": push_inputs,
           "same": lambda got, want: is_heap(got) and sorted(got) == want}]

FAMILY_INTRO = "Each member asks the heap for the best item while the set changes. What differs is what is kept and how keys are built."
FAMILY = [
    {"name": "Keep the best k", "change": "The first trace: a min-heap of size k keeps the k largest. For the k closest, keep a max-heap of size k with `(-distance, point)`.",
     "problems": ["kth-largest-element-in-an-array", "kth-largest-element-in-a-stream", "k-closest-points-to-origin"]},
    {"name": "Take the best, put back the rest", "change": "Pop the best, act, push what remains. Last Stone Weight pops two; Task Scheduler pops the most frequent tasks each cooldown cycle.",
     "problems": ["last-stone-weight", "task-scheduler"]},
    {"name": "Two heaps", "change": "A max-heap for the lower half (negated) and a min-heap for the upper half; keep their sizes within one. The median is a root, or the mean of both roots.",
     "problems": ["find-median-from-data-stream"]},
    {"name": "Merge k sorted streams", "change": "Push `(value, list index, node)` for each head; pop the smallest, push its successor. The index breaks ties, so nodes are never compared.",
     "problems": ["merge-k-sorted-lists", "design-twitter"]},
]

COUNT = {
    "line": "heapq.heappush(heap, x)",
    "input": lambda n: (list(range(n)), 8),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n,
    "bound_text": "n",
    "text": ["The push line runs once per value: n runs. One run is not O(1), though: a push or pop sifts along one "
             "path of a heap that never holds more than k + 1 items, so it costs O(log k). Runs × cost: O(n log k). "
             "With k = n (no evictions) that is O(n log n), no better than sorting."],
    "time": "O(n log k)",
    "space": "O(k): the heap.",
}

TRAPS = [
    ("Forgetting that heapq is a min-heap", "returns the smallest when you wanted the largest. Negate keys for a max-heap."),
    ("Pushing `(priority, item)` when items don't compare", "raises TypeError on a tie. Push `(priority, counter, item)`."),
    ("Keeping all n items when k would do", "costs O(n) space and O(n log n) time instead of O(n log k)."),
    ("Building a heap with n pushes", "is O(n log n); `heapq.heapify(list)` is O(n)."),
]


def popped_values(run):
    return ", ".join(str(s.v["heap"][0]) for s in run["states"] if s.kind == "line" and s.text == "heapq.heappop(heap)")


CHECK = {
    "trace": {"text": "Run kth_largest on nums = [4, 8, 1, 6, 9, 2] with k = 2. Which values are popped, in order, and what does it return?",
              "args": ([4, 8, 1, 6, 9, 2], 2),
              "fields": [("Values popped, in order", popped_values), ("Return value", lambda run: run["result"])]},
    "questions": [
        {"q": "You need the 10 closest of 10⁶ points to the origin. Which heap, and of what size?",
         "options": ["A min-heap of all 10⁶ points by distance", "A max-heap of size 10 by distance: evict the farthest", "A min-heap of size 10 by distance"], "answer": 1,
         "why": "Keep the 10 closest so far; the one to evict is the farthest of them, so it must be at the root: a max-heap (negated distances with heapq)."},
        {"q": "After pushing into a size-k min-heap, why is popping the root safe when the heap holds k + 1 items?",
         "options": ["The root is the newest item", "At least k kept items are larger, so the root can't be among the k largest", "heapq requires it"], "answer": 1,
         "why": "Every other kept item is ≥ the root, and there are k of them."},
    ],
    "own": {"prompt": "When is a heap the right tool, and why does keeping only k items give the k-th largest?",
            "model": "A heap fits when you repeatedly need the smallest or largest item of a set that keeps changing: pushes and pops cost O(log n) and the best item is always at the root. To find the k-th largest, keep a min-heap of at most k items: whenever it grows past k, the root is smaller than k other values and can be dropped. At the end the heap holds the k largest, and its root, the smallest of them, is the k-th largest. That is O(n log k) time and O(k) space."},
}
