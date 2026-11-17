"""Graphs, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/graphs/spec.py"""
from collections import deque

from build_explainer import V

TITLE = "Graphs, explained"
PITCH = ("Nodes and the links between them, with cycles allowed. Every graph algorithm here is a walk that never "
         "re-enters a node: BFS for fewest steps, DFS for reaching everything, Kahn's order for prerequisites.")

SPOT = {
    "idea": [
        "A graph problem is often in disguise: grid cells linked to their four neighbours, words one letter apart, "
        "courses and their prerequisites, accounts sharing an email. Name the **nodes** and the **edges** first; the "
        "algorithm usually follows.",
        "Then choose the walk. **BFS** (a queue) reaches nodes in order of distance, so the first time it reaches a node "
        "is by the fewest edges. **DFS** (recursion or a stack) is enough when you only need to reach everything: flood "
        "fill, components, cycles. **Topological order** (Kahn: repeatedly take a node with no unmet prerequisites) "
        "orders a directed graph, and fails exactly when there is a cycle. **Union-find** merges components as edges arrive.",
    ],
    "questions": [
        ("What are the nodes and the edges?", "Cells and their neighbours; words and one-letter changes; courses and prerequisites."),
        ("Fewest steps, or just reachable?", "Fewest steps on unweighted edges: BFS. Reachable or count of components: DFS or union-find."),
        ("Directed with dependencies?", "Topological order. Fewer nodes come out than went in: there is a cycle."),
        ("When is a node marked visited?", "When it is added to the queue, not when it is taken off, so it is queued once."),
    ],
    "cases": [
        {"text": "Count the islands of 1s in a grid of 0s and 1s.",
         "options": ["Flood fill (DFS or BFS) from each unvisited 1", "Dynamic programming", "Two pointers"], "answer": 0,
         "why": "Each flood fill marks one whole island; the number of fills started is the answer."},
        {"text": "Minutes until every orange rots, when rot spreads to neighbours each minute.",
         "options": ["Multi-source BFS from every rotten orange", "DFS from one orange", "Sorting"], "answer": 0,
         "why": "All sources start at minute 0 in one queue; BFS rounds are minutes."},
        {"text": "Can you finish all courses, given prerequisite pairs?",
         "options": ["Topological sort: is there a cycle?", "BFS shortest path", "A heap"], "answer": 0,
         "why": "Kahn's algorithm takes every course whose prerequisites are met; if some never become free, they sit on a cycle."},
        {"text": "Fewest one-letter changes to turn one word into another, through a word list.",
         "options": ["BFS over words", "DFS over words", "Backtracking over letters"], "answer": 0,
         "why": "Words are nodes, one-letter changes are unweighted edges, and fewest changes is BFS distance."},
        {"text": "Edges arrive one at a time; report the first edge that creates a cycle.",
         "options": ["Union-find", "BFS after each edge", "Topological sort"], "answer": 0,
         "why": "An edge whose two ends already share a root closes a cycle; union-find answers that in near O(1)."},
        {"text": "Cheapest route when each flight has a price.",
         "options": ["Plain BFS", "Dijkstra (weighted shortest path)", "Union-find"], "answer": 1,
         "why": "BFS counts edges, not costs. With non-negative weights, Dijkstra: see Advanced Graphs."},
    ],
    "near_misses": [
        ("A tree.", "A graph with no cycles and one path between nodes: plain recursion works, no visited set needed."),
        ("Shortest path with weights.", "BFS is only for unweighted (or equal-weight) edges. Use Dijkstra."),
        ("A grid DP like unique paths.", "Moves only right and down, so no cycles: the order is fixed and DP fills it."),
    ],
}

PARTS = {
    "names": [
        ("queue", "nodes reached but not yet expanded, in the order they were reached"),
        ("dist", "the nodes reached so far, each with its number of edges from the start; it is also the visited set"),
        ("node, nxt", "the node being expanded, and the neighbour being looked at"),
    ],
    "plan": [
        ("Start", "`dist = {start: 0}`, `queue = [start]`."),
        ("Expand", "take the node at the front of the queue."),
        ("Each neighbour", "not in dist yet: `dist[nxt] = dist[node] + 1`, and queue it."),
        ("Stop", "the queue is empty: every reachable node has its distance."),
    ],
    "invariant": "The queue holds nodes in order of distance, and its first and last differ by at most 1. So when a node is first reached, it is by the fewest edges.",
    "safe": [
        "Nodes leave the queue in order of distance d, d, ..., d + 1, d + 1. A neighbour first reached from a node at distance d can't be reached in fewer than d + 1 edges, or it would have been reached from an earlier node.",
        "Marking a node when it is queued (adding it to dist) stops it from being queued twice, so each node is expanded once and each edge looked at once per direction.",
        "The queue only grows with nodes not in dist, so the loop ends.",
    ],
    "relies_on": "unweighted edges: one edge, one step. With weights, a path of more edges can be cheaper, and BFS order breaks.",
}

POS = {"A": (0, 1), "B": (1, 0), "C": (1, 2), "D": (2, 0), "E": (2, 2), "F": (3, 1), "G": (4, 1)}
GRAPH = {"A": ["B", "C"], "B": ["A", "D"], "C": ["A", "D", "E"], "D": ["B", "C", "F"], "E": ["C", "F"],
         "F": ["D", "E", "G"], "G": ["F"]}
COURSE_POS = {0: (0, 1), 1: (1, 0), 2: (1, 2), 3: (2, 1), 4: (3, 1), 5: (2, 2.4)}


def bfs_distances(graph, start):
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in graph[node]:
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return dist


def course_order(n, prereqs):
    indegree = [0] * n
    unlocks = [[] for _ in range(n)]
    for before, after in prereqs:
        unlocks[before].append(after)
        indegree[after] += 1
    ready = deque(c for c in range(n) if indegree[c] == 0)
    order = []
    while ready:
        course = ready.popleft()
        order.append(course)
        for nxt in unlocks[course]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    return order if len(order) == n else []


REFERENCE = bfs_distances


def view(S):
    if S.func == "course_order":
        n, prereqs = S.outer["n"], S.outer["prereqs"]
        order, ready = S.v.get("order", []), list(S.v.get("ready", []))
        indegree, course = S.v.get("indegree"), S.v.get("course")
        cls = {c: "ok" for c in order}
        cls.update({c: "front" for c in ready})
        if course is not None and S.text not in ("while ready:",):
            cls[course] = "cur"
        nodes = [{"id": c, "label": c, "x": COURSE_POS[c][0], "y": COURSE_POS[c][1], "cls": cls.get(c, ""),
                  "tag": "" if indegree is None else f"in {indegree[c]}"} for c in range(n)]
        nxt = S.v.get("nxt")
        edges = [{"a": a, "b": b, "cls": "cur" if (a, b) == (course, nxt) else "done" if a in order else ""} for a, b in prereqs]
        return [V.graph("courses (tag: prerequisites not yet met; green: taken; amber: ready)", nodes, edges, directed=True, w=4, h=3.4),
                V.items("ready (front on the left)", ready), V.items("order", order)]
    graph, dist = S.outer["graph"], S.v.get("dist", {})
    queue, node, nxt = list(S.v.get("queue", [])), S.v.get("node"), S.v.get("nxt")
    cls = {v: "ok" for v in dist}
    cls.update({v: "front" for v in queue})
    if node is not None and S.text != "while queue:":
        cls[node] = "cur"
    nodes = [{"id": v, "label": v, "x": x, "y": y, "cls": cls.get(v, ""), "tag": f"d={dist[v]}" if v in dist else ""} for v, (x, y) in POS.items()]
    looking = S.text in ("if nxt not in dist:", "dist[nxt] = dist[node] + 1", "queue.append(nxt)")
    edges = [{"a": a, "b": b, "cls": "cur" if looking and {a, b} == {node, nxt} else ""} for a in graph for b in graph[a] if a < b]
    return [V.graph("graph (green: reached, amber: in the queue, blue: being expanded; d = distance)", nodes, edges, w=5, h=3),
            V.items("queue (front on the left)", queue), V.mapping("dist", dist, nxt if looking else None)]


def say(S, N):
    if S.text == "node = queue.popleft()":
        return f"Took {N.v['node']} off the front: expand it."
    if S.text == "if nxt not in dist:":
        return f"{S.nxt} is new: reach it now." if N.text != "for nxt in graph[node]:" else f"{S.nxt} was reached already: skip it."
    if S.text == "dist[nxt] = dist[node] + 1":
        return f"dist[{S.nxt}] = {S.dist[S.node]} + 1 = {S.dist[S.node] + 1}."
    if S.text == "unlocks[before].append(after)":
        return f"{S.before} → {S.after}: course {S.after} waits for course {S.before}."
    if S.text == "ready = deque(c for c in range(n) if indegree[c] == 0)":
        return f"Courses with nothing to wait for start the ready queue: {list(N.v['ready'])}."
    if S.text == "course = ready.popleft()":
        return f"Course {N.v['course']} has no unmet prerequisites: take it."
    if S.text == "indegree[nxt] -= 1":
        return f"Course {S.nxt} has one fewer unmet prerequisite: {S.indegree[S.nxt] - 1} left."
    if S.text == "if indegree[nxt] == 0:" and N.text == "ready.append(nxt)":
        return f"Course {S.nxt} is free: it joins the ready queue."
    return None


PREDICT = {
    "if nxt not in dist:": {
        "q": lambda S: f"Expanding {S.node} (d = {S.dist[S.node]}). Its neighbour {S.nxt}: reach it now or skip it?",
        "options": ["reach it now", "skip it: already reached"],
        "answer": lambda S, N: "skip it: already reached" if S.nxt in S.dist else "reach it now",
        "why": lambda S, N: (f"{S.nxt} is in dist already (d = {S.dist[S.nxt]}): a later path can't be shorter." if S.nxt in S.dist
                             else f"{S.nxt} isn't in dist: its distance is {S.dist[S.node]} + 1."),
        "times": 5,
    },
    "node = queue.popleft()": {
        "q": "Which node is expanded next?",
        "answer": lambda S, N: N.v["node"],
        "why": "The front of the queue: nodes leave in the order they were reached, which is order of distance.",
        "times": 3,
    },
    "if indegree[nxt] == 0:": {
        "q": lambda S: f"Course {S.nxt} now has {S.indegree[S.nxt]} unmet prerequisite(s). Is it ready?",
        "options": ["yes", "no"],
        "answer": lambda S, N: "yes" if S.indegree[S.nxt] == 0 else "no",
        "why": "A course is ready exactly when its count of unmet prerequisites reaches 0.",
        "times": 3,
    },
}

ROW_COLS = ["expanded", "distance", "queue after"]


def row(S, N):
    if S.func == "bfs_distances" and S.text == "for nxt in graph[node]:" and N.text == "while queue:":
        return [S.node, S.dist[S.node], list(N.v["queue"])]
    if S.text == "order.append(course)":
        return [S.course, list(N.v["order"]), list(S.ready)]
    return None


def bfs_brute(graph, start):
    dist = {start: 0}
    for _ in range(len(graph)):  # relax every edge n times: Bellman-Ford with weight 1
        for a in graph:
            for b in graph[a]:
                if a in dist and dist[a] + 1 < dist.get(b, float("inf")):
                    dist[b] = dist[a] + 1
    return dist


def INVARIANT(S):
    if S.func != "bfs_distances" or S.text != "while queue:":
        return True
    d = [S.v["dist"][v] for v in S.v["queue"]]
    true = bfs_brute(S.outer["graph"], S.outer["start"])
    return d == sorted(d) and (not d or d[-1] - d[0] <= 1) and all(true[v] == x for v, x in S.v["dist"].items())


TRACES = [
    {"label": "BFS from A", "args": (GRAPH, "A"), "expect": {"A": 0, "B": 1, "C": 1, "D": 2, "E": 2, "F": 3, "G": 4},
     "about": "Seven nodes, start at A. The queue always holds one or two distances, smaller first."},
    {"label": "Course order (Kahn)", "fn": course_order, "args": (6, [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (5, 4)]),
     "expect": [0, 5, 1, 2, 3, 4], "cols": ["took", "order", "ready before"],
     "about": "An arrow a → b means a comes before b. A course is ready when all its prerequisites are taken."},
    {"label": "Courses with a cycle", "fn": course_order, "args": (3, [(0, 1), (1, 2), (2, 1)]), "expect": [],
     "cols": ["took", "order", "ready before"],
     "about": "1 and 2 each wait for the other. They never become ready, so fewer courses come out than went in."},
]


def random_graph(rng):
    n = rng.randint(1, 8)
    names = [chr(65 + i) for i in range(n)]
    g = {v: [] for v in names}
    for a in names:
        for b in names:
            if a < b and rng.random() < 0.35:
                g[a].append(b)
                g[b].append(a)
    return g, names[0]


def course_valid(n, prereqs):
    return n, prereqs


def topo_ok(got, want):
    n, prereqs = want
    indeg = [0] * n
    for _, b in prereqs:
        indeg[b] += 1
    # brute: a cycle exists iff repeatedly deleting nodes with indegree 0 leaves some behind
    left, edges = set(range(n)), list(prereqs)
    while True:
        free = [c for c in left if all(b != c for a, b in edges if a in left)]
        if not free:
            break
        left -= set(free)
    if left:
        return got == []
    where = {c: i for i, c in enumerate(got)}
    return sorted(got) == list(range(n)) and all(where[a] < where[b] for a, b in prereqs)


def course_inputs(rng):
    out = [(1, []), (2, [(0, 1), (1, 0)]), (3, [])]
    for _ in range(200):
        n = rng.randint(1, 7)
        out.append((n, [(a, b) for a in range(n) for b in range(n) if a != b and rng.random() < 0.2]))
    return out


ORACLE = [{"brute": bfs_brute, "inputs": lambda rng: [random_graph(rng) for _ in range(200)]},
          {"fn": course_order, "brute": course_valid, "inputs": course_inputs, "same": topo_ok}]

FAMILY_INTRO = "Most graph problems are one of these walks, once the nodes and edges are named."
FAMILY = [
    {"name": "Flood fill on a grid", "change": "Cells are nodes, the four neighbours are edges. Start a DFS or BFS from every unvisited land cell; mark cells as you reach them. Border-first fills solve Surrounded Regions and Pacific Atlantic.",
     "problems": ["number-of-islands", "max-area-of-island", "surrounded-regions", "pacific-atlantic-water-flow"]},
    {"name": "BFS from many sources", "change": "Put every source in the queue at distance 0; each BFS round is one minute or one step.",
     "problems": ["rotting-oranges", "walls-and-gates"]},
    {"name": "Fewest steps", "change": "BFS distance on an implicit graph: words one letter apart, states of a puzzle.",
     "problems": ["word-ladder"]},
    {"name": "Topological order", "change": "The second trace. A course schedule exists exactly when Kahn's algorithm outputs every node.",
     "problems": ["course-schedule", "course-schedule-ii"]},
    {"name": "Components and cycles with union-find", "change": "`find` with path compression and `union` by size; an edge whose ends share a root closes a cycle. A tree is n − 1 edges and no cycle.",
     "problems": ["number-of-connected-components-in-an-undirected-graph", "graph-valid-tree", "redundant-connection"],
     "code": "parent = list(range(n))\n\ndef find(x):\n    while parent[x] != x:\n        parent[x] = parent[parent[x]]  # path halving\n        x = parent[x]\n    return x\n\ndef union(a, b):\n    ra, rb = find(a), find(b)\n    if ra == rb:\n        return False                   # already connected: this edge closes a cycle\n    parent[ra] = rb\n    return True"},
    {"name": "Copy a graph", "change": "DFS with a map from each original node to its copy; the map doubles as the visited set.",
     "problems": ["clone-graph"]},
]


def ring(n):
    names = list(range(n))
    g = {v: [] for v in names}
    for v in names:
        for step in (1, 2):
            w = (v + step) % n
            g[v].append(w)
            g[w].append(v)
    return g, 0


COUNT = {
    "line": "if nxt not in dist:",
    "input": ring,
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: 4 * n,
    "bound_text": "4n (the sum of degrees: 2E with E = 2n)",
    "n_name": "nodes (2 edges each way)",
    "text": ["Each node is expanded once, and expanding it looks at each of its edges once, so the neighbour check runs "
             "once per edge end: the sum of the degrees, 2E for an undirected graph. Here E = 2n, so 4n. The pop line "
             "runs n times. Together: O(V + E)."],
    "time": "O(V + E)",
    "space": "O(V) for dist and the queue.",
}

TRAPS = [
    ("Marking visited when a node leaves the queue", "lets it be queued many times; on a dense graph that is far more work. Mark when queuing."),
    ("Recursive DFS on a 10⁶-cell grid", "can pass Python's recursion limit. Use BFS or an explicit stack."),
    ("Starting from one node only", "misses the other components. Loop over every node and start from each unvisited one."),
    ("BFS on weighted edges", "returns the fewest edges, not the cheapest path."),
]


CHECK = {
    "trace": {"text": "Run bfs_distances on the same graph starting from G. In what order are nodes expanded, and what is dist['A']?",
              "args": (GRAPH, "G"),
              "fields": [("Order of expansion", lambda run: ", ".join(run["result"])),  # dist is filled in queue order
                         ("dist['A']", lambda run: run["result"]["A"])]},
    "questions": [
        {"q": "Kahn's algorithm outputs 4 of 6 courses. What does that tell you?",
         "options": ["The two others are unreachable from course 0", "The two others sit on (or behind) a cycle", "The input is sorted wrongly"], "answer": 1,
         "why": "A course never becomes ready only if some prerequisite chain never frees it: a cycle, or a course waiting on one."},
        {"q": "A grid where moving onto mud costs 5 and onto grass costs 1. Fewest-cost path?",
         "options": ["BFS", "Dijkstra", "DFS"], "answer": 1,
         "why": "Weighted edges: BFS would count moves, not cost. (With only costs 0 and 1, a deque-based 0-1 BFS works.)"},
    ],
    "own": {"prompt": "Why does BFS reach each node by the fewest edges, and why mark a node when you queue it?",
            "model": "BFS takes nodes off the queue in order of distance, and every node it queues is one edge farther than the node being expanded, so the queue only ever holds two neighbouring distances, smaller first. The first time a node is reached, every node closer to the start has already been expanded, so no shorter route was missed. Marking it as soon as it is queued means it is queued once, so each node is expanded once and each edge looked at a constant number of times: O(V + E)."},
}
