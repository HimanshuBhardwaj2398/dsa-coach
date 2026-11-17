"""Linked List, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/linked-list/spec.py"""
from build_explainer import V

TITLE = "Linked List, explained"
PITCH = ("A list you can only walk forward. Every technique comes down to rewiring `next` pointers in a safe order, "
         "and to walking with more than one pointer.")

SPOT = {
    "idea": [
        "A linked list gives O(1) splicing at a node you already hold, and no random access: reaching index i costs i steps. "
        "So the problems are about **pointer order**: which `next` you must save before you overwrite it, and which node "
        "you must keep a handle on so nothing becomes unreachable.",
        "Three moves cover most of them: **rewire** with `prev` and `curr` (reverse, reorder), **walk with two speeds or a gap** "
        "(middle, cycle, n-th from the end), and **build behind a dummy head** (merge, remove), so the first node is not a special case.",
    ],
    "questions": [
        ("What must stay reachable?", "Before `curr.next = ...`, save `curr.next` if you still need the rest."),
        ("Do I need a node before the head?", "If the head can change or be removed, start from a dummy node."),
        ("Would two pointers at different speeds find it?", "Middle: slow 1, fast 2. Cycle: they meet. n-th from the end: a gap of n."),
        ("In what order do the pointer writes happen?", "Write them down first; most bugs are two lines swapped."),
    ],
    "cases": [
        {"text": "Reverse a singly linked list in place.",
         "options": ["Rewire with prev and curr", "Copy the values into an array, reverse, write back", "Recursion is the only way"], "answer": 0,
         "why": "Three pointers, O(1) extra space: save next, point curr back at prev, step both forward."},
        {"text": "Does the list have a cycle? Use O(1) extra space.",
         "options": ["A set of visited nodes", "Slow and fast pointers", "Count the nodes"], "answer": 1,
         "why": "A set works in O(n) space. With fast moving 2 and slow 1, fast gains one node per step, so inside a cycle it catches slow."},
        {"text": "Remove the n-th node from the end, in one pass.",
         "options": ["Two pointers n apart", "Reverse the list first", "A hash map from index to node"], "answer": 0,
         "why": "Move the lead n steps ahead, then move both: when the lead reaches the end, the trailer is just before the node to remove."},
        {"text": "Merge two sorted lists into one sorted list.",
         "options": ["A dummy head and a tail pointer", "Collect the values and sort them", "Fast and slow pointers"], "answer": 0,
         "why": "Append the smaller head to `tail` each step; the dummy means the first append isn't a special case."},
        {"text": "Design a cache that evicts the least recently used key, with O(1) get and put.",
         "options": ["A hash map plus a doubly linked list", "A heap of timestamps", "A sorted list"], "answer": 0,
         "why": "The map finds a node in O(1); the doubly linked list moves it to the front or drops the tail in O(1)."},
        {"text": "Return the k-th element of an array.",
         "options": ["Walk a linked list k steps", "Index the array directly", "Fast and slow pointers"], "answer": 1,
         "why": "Arrays give O(1) random access. A linked list only pays off when you splice at nodes you already hold."},
    ],
    "near_misses": [
        ("Find the duplicate number in an array of n + 1 values in 1..n.", "No list in sight, but `i → nums[i]` is one: Floyd's cycle finding on indices."),
        ("Reverse an array.", "Two pointers swapping from both ends; there are no `next` pointers to rewire."),
        ("Merge k sorted lists.", "The splice is a linked list move, but choosing the smallest head each time is a heap."),
    ],
}

PARTS = {
    "names": [
        ("prev", "the head of the part already reversed (None at first)"),
        ("curr", "the first node not yet reversed"),
        ("nxt", "a saved handle on `curr.next`, taken before that pointer is overwritten"),
    ],
    "plan": [
        ("Start", "`prev = None`, `curr = head`."),
        ("Continue", "while `curr`: nodes are left to reverse."),
        ("Move", "save `nxt = curr.next`; point `curr.next = prev`; step `prev, curr = curr, nxt`."),
        ("Stop", "`curr` is None; `prev` is the new head."),
    ],
    "invariant": "`prev` heads the reversed part and `curr` heads the rest. Together they hold every node, and nothing is unreachable.",
    "safe": [
        "`nxt = curr.next` comes first: once `curr.next = prev` runs, it is the only handle on the rest of the list.",
        "`curr.next = prev` adds one node to the front of the reversed part; the rest is still reachable through `nxt`.",
        "`prev, curr = curr, nxt` restores the invariant for one more reversed node, so the loop ends after n turns.",
    ],
    "relies_on": "the order of the three writes. Swap any two and a node becomes unreachable or the list loops.",
}


class ListNode:
    def __init__(self, val, next=None):
        self.val, self.next = val, next


def build(values):
    head = None
    for v in reversed(values):
        head = ListNode(v, head)
    return head


def to_list(node):
    out = []
    while node:
        out.append(node.val)
        node = node.next
    return out


def reverse_list(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev, curr = curr, nxt
    return prev


REFERENCE = reverse_list


def nodes_of(S):
    """Every node a local can reach, without repeats (the snapshot keeps shared nodes shared)."""
    seen, out = set(), []
    for name in ("head", "prev", "curr", "nxt"):
        node = S.v.get(name)
        while node is not None and id(node) not in seen:
            seen.add(id(node))
            out.append(node)
            node = node.next
    return out


def view(S):
    nodes = nodes_of(S)
    last = max([n.val for n in nodes] + [0])
    walk = lambda n: [x.val for x in iter_nodes(n)]
    reversed_part, rest = set(walk(S.v.get("prev"))), set(walk(S.v.get("curr")))
    tags = {}
    for name in ("prev", "curr", "nxt"):
        if name in S.v:
            node = S.v[name]
            key = "none-left" if node is None and name == "prev" else "none-right" if node is None else node.val
            tags.setdefault(key, []).append(name)
    g_nodes = [{"id": "none-left", "label": "∅", "x": 0, "y": 0, "cls": "done", "tag": " ".join(tags.get("none-left", []))},
               {"id": "none-right", "label": "∅", "x": last + 1, "y": 0, "cls": "done", "tag": " ".join(tags.get("none-right", []))}]
    edges = []
    for n in nodes:
        cls = "cur" if S.v.get("curr") is n else "ok" if n.val in reversed_part else ""
        g_nodes.append({"id": n.val, "label": n.val, "x": n.val, "y": 0, "cls": cls, "tag": " ".join(tags.get(n.val, []))})
        target = n.next.val if n.next else ("none-right" if n.val == last and n.val not in reversed_part else "none-left")
        edges.append({"a": n.val, "b": target, "cls": "ok" if n.val in reversed_part else ""})
    return [V.graph("nodes and their next pointers (green: reversed part)", g_nodes, edges, directed=True, w=last + 2, h=1),
            V.items("reachable from prev", walk(S.v.get("prev")), note="" if "prev" in S.v else "not started"),
            V.items("reachable from curr", walk(S.v.get("curr")))]


def name(node):
    return "None" if node is None else f"node {node.val}"


def say(S, N):
    """What the line S.text just did, in words: the nodes are objects, so the automatic narration skips them."""
    if S.text == "prev, curr = None, head":
        return f"prev = None, curr = {name(N.v['curr'])}."
    if S.text == "nxt = curr.next":
        return f"Saved nxt = {name(N.v['nxt'])}: the only handle on the rest once node {S.curr.val} is rewired."
    if S.text == "curr.next = prev":
        return f"Node {S.curr.val} now points to {name(S.prev)}. The reversed part grew by one."
    if S.text == "prev, curr = curr, nxt":
        return f"Stepped forward: prev = {name(N.v['prev'])}, curr = {name(N.v['curr'])}."
    if S.text == "while curr:":
        return "curr is a node, so another turn." if N.text != "return prev" else "curr is None: every node is reversed."
    return None


def iter_nodes(node):
    seen = set()
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        yield node
        node = node.next


PREDICT = {
    "curr.next = prev": {
        "q": lambda S: f"curr is node {S.curr.val} and prev is {'None' if S.prev is None else 'node ' + str(S.prev.val)}. "
                       f"After this line, what does node {S.curr.val} point to?",
        "answer": lambda S, N: "None" if N.v["curr"].next is None else N.v["curr"].next.val,
        "why": lambda S, N: f"It joins the front of the reversed part. The rest stays reachable only through nxt (node {S.nxt.val if S.nxt else 'None'}).",
        "times": 3,
    },
    "nxt = curr.next": {
        "q": "Why must this line run before `curr.next = prev`?",
        "options": ["It is faster", "After the rewire, curr.next no longer leads to the rest", "Python requires it"],
        "answer": lambda S, N: "After the rewire, curr.next no longer leads to the rest",
        "why": "Without nxt, the rest of the list would be unreachable after one rewire.",
        "times": 1,
    },
}

ROW_COLS = ["turn", "prev heads", "curr heads"]


def row(S, N):
    if S.text == "prev, curr = curr, nxt":
        turns = sum(1 for s in S.trace[:S.index + 1] if s.text == "prev, curr = curr, nxt")
        return [turns, " → ".join(map(str, to_list(N.v["prev"]))), " → ".join(map(str, to_list(N.v["curr"]))) or "None"]
    return None


def INVARIANT(S):
    if S.text != "while curr:":
        return True
    a = [n.val for n in iter_nodes(S.v.get("prev"))]
    b = [n.val for n in iter_nodes(S.v.get("curr"))]
    everything = sorted(a + b)
    return not (set(a) & set(b)) and everything == list(range(1, len(everything) + 1))


TRACES = [
    {"label": "1 → 2 → 3 → 4", "args": (build([1, 2, 3, 4]),),
     "about": "Four nodes. The green part grows from the left while the arrows flip, one node per turn."},
    {"label": "One node", "args": (build([1]),),
     "about": "The edge case: one turn, and the single node points at None."},
]


def inputs(rng):
    cases = [([],), ([1],), ([1, 2],)]
    for _ in range(200):
        cases.append(([rng.randint(-5, 9) for _ in range(rng.randint(0, 8))],))
    return [(build(vals),) for (vals,) in cases]


ORACLE = {"brute": lambda head: list(reversed(to_list(head))), "inputs": inputs,
          "same": lambda got, want: to_list(got) == want}

FAMILY_INTRO = "Linked list problems share a short list of moves. Name the move before you write a line."
FAMILY = [
    {"name": "Rewire with prev and curr", "change": "The trace above. Reverse in groups of k by reversing k nodes, then reconnecting the group's old head to what follows.",
     "problems": ["reverse-linked-list", "reverse-nodes-in-k-group"]},
    {"name": "Build behind a dummy head", "change": "`dummy = tail = ListNode(0)`; append to `tail`; return `dummy.next`. For k lists, keep their heads in a heap.",
     "problems": ["merge-two-sorted-lists", "add-two-numbers", "merge-k-sorted-lists"]},
    {"name": "Two speeds", "change": "`slow` moves 1, `fast` moves 2. They meet inside a cycle; when fast reaches the end, slow is in the middle. Reorder List = find the middle, reverse the second half, weave.",
     "problems": ["linked-list-cycle", "find-the-duplicate-number", "reorder-list"]},
    {"name": "A gap of n", "change": "Start the lead n steps ahead of the trailer; move both until the lead ends. Begin at a dummy head so removing the first node works too.",
     "problems": ["remove-nth-node-from-end-of-list"]},
    {"name": "A map from node to node", "change": "Copy with random pointers: map each old node to its copy in one pass, wire `next` and `random` in a second. LRU: a map to doubly linked nodes.",
     "problems": ["copy-list-with-random-pointer", "lru-cache"]},
]

COUNT = {
    "line": "nxt = curr.next",
    "input": lambda n: (build(list(range(1, n + 1))),),
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: n,
    "bound_text": "n",
    "text": ["Each turn moves one node from the rest to the reversed part, so the loop body runs exactly n times, "
             "each line O(1). Doubling n doubles the count."],
    "time": "O(n)",
    "space": "O(1): three pointers. (A recursive reverse uses O(n) stack.)",
}

TRAPS = [
    ("`curr.next = prev` before saving `curr.next`", "loses the rest of the list."),
    ("Returning `head`", "returns the old first node, now the last. The new head is `prev`."),
    ("`fast.next.next` without checking `fast.next`", "crashes on an even-length list. Loop `while fast and fast.next`."),
    ("No dummy head", "makes removing or replacing the first node a special case."),
]


CHECK = {
    "trace": {"text": "Reverse 5 → 6 → 7 with the same loop. Write the value prev points to after each turn, and the list it returns.",
              "args": (build([5, 6, 7]),),
              "fields": [("prev after each turn", lambda run: ", ".join(str(s.v["prev"].val) for s in run["states"]
                                                                    if s.kind == "line" and s.text == "while curr:" and s.v.get("prev"))),
                         ("Returned list", lambda run: to_list(run["result"]))]},
    "questions": [
        {"q": "Find the middle node in one pass. Where is slow when fast can't take two more steps?",
         "options": ["At the start", "In the middle: fast covered twice slow's distance", "At the end"], "answer": 1,
         "why": "fast moves 2 for slow's 1, so when fast reaches the end, slow has covered half."},
        {"q": "Remove the n-th node from the end. Why start both pointers at a dummy node before the head?",
         "options": ["So removing the first node needs no special case", "To save memory", "To detect cycles"], "answer": 0,
         "why": "The trailer must stop before the node it removes; when that node is the head, only a dummy comes before it."},
    ],
    "own": {"prompt": "What has to be true of prev and curr after every turn, and why does the order of the three lines matter?",
            "model": "prev heads the reversed part and curr heads the rest, and together they hold every node. Saving curr.next first keeps the rest reachable; pointing curr.next at prev moves one node into the reversed part; stepping both forward restores the invariant. Swap the first two lines and the rest of the list is lost."},
}
