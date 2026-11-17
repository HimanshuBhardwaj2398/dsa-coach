"""Advanced Graphs, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/advanced-graphs/spec.py"""
import heapq
from itertools import combinations

from build_explainer import V

TITLE = "Advanced Graphs, explained"
PITCH = ("BFS with a heap instead of a queue. Always expand the cheapest frontier entry next; with non-negative "
         "weights, the first time a node comes off the heap its cost is final.")

SPOT = {
    "idea": [
        "When edges have **costs**, BFS's 'fewest edges' is the wrong measure. **Dijkstra** keeps a min-heap of "
        "(cost so far, node) and always expands the cheapest. Because no edge is negative, nothing found later can "
        "beat a node's cost once it is popped: it is **settled**. Entries that were pushed before a cheaper route "
        "turned up stay in the heap as **stale** entries and are skipped when popped.",
        "The same loop with a different key builds a **minimum spanning tree** (Prim: key = the edge's own cost, not "
        "the path's). Other members change what a state is: (node, stops used) for 'at most k stops', where "
        "Bellman-Ford's k rounds of relaxing every edge fit better; letters as nodes for an alien alphabet (topological "
        "order); each edge used once for an itinerary (Hierholzer).",
    ],
    "questions": [
        ("Are there weights, and can they be negative?", "Non-negative: Dijkstra. Negative: Bellman-Ford."),
        ("Shortest path, or cheapest way to connect everything?", "Path: Dijkstra. Connect all: a minimum spanning tree (Prim or Kruskal)."),
        ("Is there an extra limit (stops, fuel, time)?", "Make it part of the state, or run Bellman-Ford for exactly k rounds."),
        ("What is the cost of a path: a sum or a maximum?", "Swim in Rising Water: the max along the path; the heap still works."),
    ],
    "cases": [
        {"text": "How long until a signal sent from node k reaches every node, with travel times on the edges?",
         "options": ["Dijkstra from k; the answer is the largest distance", "BFS from k", "Union-find"], "answer": 0,
         "why": "Weighted shortest paths from one source: Dijkstra; every node has heard once the farthest has."},
        {"text": "Cheapest flight from A to B with at most k stops.",
         "options": ["Plain Dijkstra on cost", "Bellman-Ford for k + 1 rounds (or Dijkstra on (node, stops))", "DFS of every route"], "answer": 1,
         "why": "Plain Dijkstra may settle a node by a cheap route with too many stops and discard the route that fits."},
        {"text": "Connect all points with the least total wire.",
         "options": ["A minimum spanning tree (Prim or Kruskal)", "Dijkstra from one point", "Sort the points"], "answer": 0,
         "why": "Connecting everything cheaply is an MST, not a shortest path from one point."},
        {"text": "Given words sorted in an unknown alphabet, recover the letter order.",
         "options": ["A topological sort of letter constraints", "Dijkstra", "A trie alone"], "answer": 0,
         "why": "Each pair of adjacent words gives one 'letter x before letter y' edge; a cycle means no valid order."},
        {"text": "Fewest moves for a knight between two squares.",
         "options": ["Dijkstra", "BFS", "MST"], "answer": 1,
         "why": "Every move costs the same, so BFS is enough and simpler."},
        {"text": "The time when you can swim from the top-left to the bottom-right as water rises.",
         "options": ["A heap keyed by the highest elevation on the path", "Plain BFS", "Union-find only"], "answer": 0,
         "why": "Dijkstra's loop with 'cost = max so far' instead of a sum. (Binary search plus BFS, or union-find by elevation, also work.)"},
    ],
    "near_misses": [
        ("Equal weights everywhere.", "Plain BFS: same answer, no log factor."),
        ("Negative edge weights.", "A settled node could still be improved: Bellman-Ford."),
        ("Shortest paths between every pair, n ≤ 100.", "Floyd–Warshall's triple loop is simpler than n runs of Dijkstra."),
    ],
}

PARTS = {
    "names": [
        ("heap", "(cost so far, node) entries, cheapest first; it may hold old, stale entries"),
        ("dist", "the best cost found so far for each reached node"),
        ("done", "settled nodes: popped once, cost final"),
    ],
    "plan": [
        ("Start", "`dist = {start: 0}`, `heap = [(0, start)]`."),
        ("Pop", "the cheapest entry; if its node is already settled, it is stale: skip it."),
        ("Settle and relax", "mark the node done; for each edge, if `d + w` beats `dist[nxt]`, record it and push it."),
        ("Stop", "the heap is empty: dist holds the cost of every reachable node."),
    ],
    "invariant": "Every settled node's dist is its true cheapest cost, and every heap entry is a real path's cost.",
    "safe": [
        "When the cheapest entry (d, node) is popped, every other route to node goes through some entry still in the heap, which costs at least d; edges add ≥ 0, so no route beats d. Settle it.",
        "A node can be pushed several times as cheaper routes appear. Only its cheapest entry is popped first; later ones are stale and skipped.",
        "Each edge is relaxed once, when its tail is settled, so the heap gets at most E pushes.",
    ],
    "relies_on": "non-negative edge weights. One negative edge can make a settled cost wrong.",
}

EDGES = [("A", "B", 4), ("A", "C", 1), ("C", "B", 2), ("B", "D", 1), ("C", "D", 5), ("D", "E", 3), ("C", "E", 8)]
POS = {"A": (0, 1), "B": (2, 0), "C": (1, 2), "D": (3, 1), "E": (4, 2)}
DIRECTED = {v: [] for v in POS}
UNDIRECTED = {v: [] for v in POS}
for _a, _b, _w in EDGES:
    DIRECTED[_a].append((_b, _w))
    UNDIRECTED[_a].append((_b, _w))
    UNDIRECTED[_b].append((_a, _w))


def dijkstra(graph, start):
    dist = {start: 0}
    heap = [(0, start)]
    done = set()
    while heap:
        d, node = heapq.heappop(heap)
        if node in done:
            continue
        done.add(node)
        for nxt, w in graph[node]:
            if d + w < dist.get(nxt, float("inf")):
                dist[nxt] = d + w
                heapq.heappush(heap, (d + w, nxt))
    return dist


def prim(graph, start):
    total, done = 0, set()
    heap = [(0, start)]
    while heap:
        w, node = heapq.heappop(heap)
        if node in done:
            continue
        done.add(node)
        total += w
        for nxt, cost in graph[node]:
            if nxt not in done:
                heapq.heappush(heap, (cost, nxt))
    return total


REFERENCE = dijkstra


def view(S):
    is_prim = S.func == "prim"
    graph = S.outer["graph"]
    done, heap = S.v.get("done", set()), S.v.get("heap", [])
    dist = S.v.get("dist", {})
    node, nxt = S.v.get("node"), S.v.get("nxt")
    queued = {v for _, v in heap if v not in done}
    cls = {v: "ok" for v in done}
    cls.update({v: "front" for v in queued})
    if node is not None and S.text not in ("while heap:",):
        cls[node] = "cur"
    nodes = [{"id": v, "label": v, "x": x, "y": y, "cls": cls.get(v, ""),
              "tag": "" if is_prim else (f"{dist[v]}" if v in dist else "∞")} for v, (x, y) in POS.items()]
    looking = S.text.startswith("if d + w") or S.text.startswith("dist[nxt]") or S.text.startswith("if nxt not in done") or S.text.startswith("heapq.heappush")
    edges = [{"a": a, "b": b, "label": w, "cls": "cur" if looking and (a, b) in ((node, nxt), (nxt, node) if is_prim else (node, nxt)) else ""} for a, b, w in EDGES]
    ordered = sorted(heap)
    stale = {j: "done" for j, (d, v) in enumerate(ordered) if v in done or (not is_prim and d > dist.get(v, d))}
    out = [V.graph(("Prim: green = in the tree, amber = touching it" if is_prim else
                    "Dijkstra: green = settled, amber = in the heap; tags: best cost so far"), nodes, edges,
                   directed=not is_prim, w=5, h=3),
           V.items("heap, cheapest first (struck out: stale)", [f"({d}, {v})" for d, v in ordered], stale)]
    out.append(V.vars(("total", S.v.get("total"))) if is_prim else V.mapping("dist", dist, nxt if looking else None))
    return out


def say(S, N):
    if S.text in ("d, node = heapq.heappop(heap)", "w, node = heapq.heappop(heap)"):
        return f"Popped the cheapest entry: ({N.v.get('d', N.v.get('w'))}, {N.v['node']})."
    if S.text == "if node in done:":
        return f"{S.node} is settled already: a stale entry, skip it." if N.text == "continue" else f"{S.node} isn't settled: settle it now."
    if S.text == "if d + w < dist.get(nxt, float(\"inf\")):":
        best = S.dist.get(S.nxt)
        if S.d + S.w < (best if best is not None else float("inf")):
            return f"{S.node} → {S.nxt}: {S.d} + {S.w} = {S.d + S.w} beats {best if best is not None else '∞'}: record it and push it."
        return f"{S.node} → {S.nxt}: {S.d} + {S.w} = {S.d + S.w} doesn't beat {best}."
    if S.text == "dist[nxt] = d + w":
        return f"dist[{S.nxt}] = {S.d} + {S.w} = {S.d + S.w}."
    if S.text == "heapq.heappush(heap, (d + w, nxt))":
        return f"Pushed ({S.d + S.w}, {S.nxt}). Any older entry for {S.nxt} is now stale."
    if S.text == "heapq.heappush(heap, (cost, nxt))":
        return f"Pushed ({S.cost}, {S.nxt}): the edge {S.node}–{S.nxt} could bring {S.nxt} into the tree."
    if S.text == "total += w":
        return f"Added the edge of cost {S.w} that brought {S.node} into the tree: total {N.v['total']}."
    return None


PREDICT = {
    "d, node = heapq.heappop(heap)": {
        "q": "Which entry comes off the heap next? Write it as (cost, node).",
        "answer": lambda S, N: f"({N.v['d']}, {N.v['node']})",
        "why": "The heap always gives the cheapest entry, stale or not.",
        "times": 3,
    },
    "if d + w < dist.get(nxt, float(\"inf\")):": {
        "q": lambda S: f"Settled {S.node} at {S.d}. Edge to {S.nxt} costs {S.w}; {S.nxt}'s best so far is {S.dist.get(S.nxt, '∞')}. Improve it?",
        "options": ["yes", "no"],
        "answer": lambda S, N: "yes" if S.d + S.w < S.dist.get(S.nxt, float("inf")) else "no",
        "why": lambda S, N: f"{S.d} + {S.w} = {S.d + S.w}, against {S.dist.get(S.nxt, '∞')}.",
        "times": 4,
    },
    "if node in done:": {
        "q": lambda S: f"Popped ({S.v.get('d', S.v.get('w'))}, {S.node}). Is it stale?",
        "options": ["yes: skip it", "no: settle it"],
        "answer": lambda S, N: "yes: skip it" if S.node in S.done else "no: settle it",
        "why": "An entry is stale when its node was settled by a cheaper entry earlier.",
        "when": lambda S: S.node in S.done,
        "times": 2,
    },
}

ROW_COLS = ["popped", "so", "dist after"]


def row(S, N):
    if S.text == "if node in done:":
        cost = S.v.get("d", S.v.get("w"))
        nxt = next((t for t in S.trace[S.index + 1:] if t.text == "while heap:"), None)
        after = (nxt.v.get("dist") if nxt and S.func == "dijkstra" else nxt.v.get("total") if nxt else "")
        return [f"({cost}, {S.node})", "stale: skip" if S.node in S.done else "settle", after]
    return None


def bellman_ford(graph, start):
    dist = {start: 0}
    for _ in range(len(graph)):
        for a in graph:
            for b, w in graph[a]:
                if a in dist and dist[a] + w < dist.get(b, float("inf")):
                    dist[b] = dist[a] + w
    return dist


def INVARIANT(S):
    if S.func != "dijkstra" or S.text != "while heap:":
        return True
    true = bellman_ford(S.outer["graph"], S.outer["start"])
    return all(S.v["dist"][v] == true[v] for v in S.v["done"])


TRACES = [
    {"label": "Dijkstra from A", "args": (DIRECTED, "A"), "expect": {"A": 0, "B": 3, "C": 1, "D": 4, "E": 7},
     "about": "A → B costs 4, but A → C → B costs 3: B is pushed twice, and the (4, B) entry goes stale."},
    {"label": "Prim on the same graph (undirected)", "fn": prim, "args": (UNDIRECTED, "A"), "expect": 7,
     "cols": ["popped", "so", "tree cost after"],
     "about": "The same loop, keyed by one edge's cost instead of a path's: it grows the cheapest tree that touches every node."},
]


def random_graph(rng, directed=True):
    n = rng.randint(1, 6)
    names = [chr(65 + i) for i in range(n)]
    g = {v: [] for v in names}
    for a in names:
        for b in names:
            if a != b and rng.random() < 0.35 and (directed or a < b):
                w = rng.randint(0, 9)
                g[a].append((b, w))
                if not directed:
                    g[b].append((a, w))
    return g, names[0]


def mst_brute(graph, start):
    """Kruskal over the component of start: sort edges, keep each that joins two trees."""
    reach, stack = {start}, [start]
    while stack:
        for b, _ in graph[stack.pop()]:
            if b not in reach:
                reach.add(b)
                stack.append(b)
    parent = {v: v for v in reach}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    total = 0
    for w, a, b in sorted((w, a, b) for a in reach for b, w in graph[a] if a < b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            total += w
    return total


ORACLE = [{"brute": bellman_ford, "inputs": lambda rng: [random_graph(rng) for _ in range(250)]},
          {"fn": prim, "brute": mst_brute, "inputs": lambda rng: [random_graph(rng, directed=False) for _ in range(250)]}]

FAMILY_INTRO = "Keep the heap loop; change the key, the state or the order."
FAMILY = [
    {"name": "Dijkstra (sum of costs)", "change": "The first trace. Network Delay Time is the largest settled cost. Swim in Rising Water keys the heap by the highest cell on the path instead of a sum.",
     "problems": ["network-delay-time", "swim-in-rising-water"]},
    {"name": "A limit on stops", "change": "Bellman-Ford for k + 1 rounds, each relaxing every edge from a copy of the previous round's costs, so a round adds at most one flight.",
     "problems": ["cheapest-flights-within-k-stops"],
     "code": "cost = {src: 0}\nfor _ in range(k + 1):\n    nxt = dict(cost)                 # relax from last round's costs only\n    for a, b, price in flights:\n        if a in cost and cost[a] + price < nxt.get(b, float(\"inf\")):\n            nxt[b] = cost[a] + price\n    cost = nxt\nreturn cost.get(dst, -1)"},
    {"name": "Minimum spanning tree", "change": "The second trace (Prim). Kruskal sorts all edges and keeps each that joins two different union-find trees.",
     "problems": ["min-cost-to-connect-all-points"]},
    {"name": "Order from constraints", "change": "Alien Dictionary: compare adjacent words, add an edge at their first differing letter, then Kahn's topological sort (see Graphs). A longer word before its own prefix is invalid.",
     "problems": ["alien-dictionary"]},
    {"name": "Every edge once", "change": "Reconstruct Itinerary: Hierholzer's algorithm. DFS taking the smallest unused ticket, appending an airport after its edges are used up, then reversing.",
     "problems": ["reconstruct-itinerary"]},
]


def dense(n):
    g = {i: [((i + s) % n, (i * 7 + s) % 10) for s in (1, 2, 3)] for i in range(n)}
    return g, 0


COUNT = {
    "line": "if d + w < dist.get(nxt, float(\"inf\")):",
    "input": dense,
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: 3 * n,
    "bound_text": "E (here 3n: three edges out of each node)",
    "n_name": "nodes (3 edges out of each)",
    "text": ["Each node is settled once, and settling it relaxes each of its outgoing edges once, so the relax check "
             "runs at most E times. Each run may push onto the heap, which costs O(log E), and every pushed entry is "
             "popped once, also O(log E). Runs × cost: O(E log E), usually written O(E log V)."],
    "time": "O(E log V)",
    "space": "O(V + E): dist, done, and up to E heap entries.",
}

TRAPS = [
    ("Marking a node done when it is pushed", "settles it before a cheaper route is found. Settle on pop."),
    ("No stale check", "re-expands a node from an old, larger cost: still correct, but slower; with the check, each node is expanded once."),
    ("Negative weights", "break the settle-on-pop proof. Use Bellman-Ford."),
    ("Dijkstra for 'at most k stops'", "prunes a costlier route that would have fitted the stop limit. Put stops in the state, or use k + 1 Bellman-Ford rounds."),
]


CHECK = {
    "trace": {"text": "Run dijkstra on the same graph from C. In what order are nodes settled, and what is the cost of E?",
              "args": (DIRECTED, "C"),
              "fields": [("Order nodes are settled", lambda run: ", ".join(s.v["node"] for s in run["states"] if s.kind == "line" and s.text == "done.add(node)")),
                         ("Cost of E", lambda run: run["result"]["E"])]},
    "questions": [
        {"q": "One edge in the graph has weight −3. Can Dijkstra's settled costs be trusted?",
         "options": ["Yes", "No: a later, cheaper route through the negative edge can beat a settled cost", "Only for the start node"], "answer": 1,
         "why": "The proof needs every edge ≥ 0. Use Bellman-Ford."},
        {"q": "Prim and Dijkstra run the same loop. What is the heap's key in each?",
         "options": ["Both: the path cost from the start", "Dijkstra: the path cost from the start; Prim: the cost of the one edge joining the tree", "Both: the edge cost"], "answer": 1,
         "why": "That one change turns 'cheapest route to each node' into 'cheapest set of edges connecting all nodes'."},
    ],
    "own": {"prompt": "Why is a node's cost final when it comes off the heap, and what is a stale entry?",
            "model": "The heap always hands out the cheapest entry. Any other route to that node would have to leave the settled region through an entry still in the heap, which costs at least as much, and with non-negative edges it can only grow from there; so the popped cost can't be beaten and the node is settled. A node may have been pushed earlier with a larger cost before a cheaper route turned up; that old entry is stale, and when it is popped later the node is already settled, so it is skipped."},
}
