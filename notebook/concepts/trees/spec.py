"""Trees, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/trees/spec.py"""
from collections import deque

from build_explainer import V, tree_layout

TITLE = "Trees, explained"
PITCH = ("Ask each subtree one question and combine the two answers. A call returns the answer for its own subtree, "
         "so the root's call returns the whole answer.")

SPOT = {
    "idea": [
        "Most tree problems are one recursive function that **returns the answer for the subtree it was given**. Trust "
        "the two recursive calls, combine their answers at the node, and handle `None`. That is depth, size, "
        "sameness, inversion and balance.",
        "Two variations cover most of the rest. Some answers need information **from above** (the bounds a BST node must "
        "fit, the largest value on the path), so pass it down as an argument. Some need to **record something "
        "different from what they return** (the diameter through a node), so return a height and update a best. "
        "When the question is about levels or the nearest node, go breadth-first with a queue.",
    ],
    "questions": [
        ("What does a call return for its subtree?", "Name it in one phrase: its height, whether it is balanced, its largest path down."),
        ("What does a node do with its children's answers?", "`1 + max(left, right)`, `left and right and ...`, a sum."),
        ("Does a node need something from above?", "Then it is an argument: bounds, a running maximum, the depth."),
        ("Is it about levels or nearness?", "Breadth-first: a queue, one level per round."),
    ],
    "cases": [
        {"text": "Maximum depth of a binary tree.",
         "options": ["DFS that returns a value up", "BFS by levels only", "Backtracking"], "answer": 0,
         "why": "Depth of a node = 1 + the larger depth of its children. (Counting levels with BFS works too.)"},
        {"text": "Is this binary tree a valid binary search tree?",
         "options": ["Compare each node with its two children", "Pass the allowed (low, high) range down", "BFS by levels"], "answer": 1,
         "why": "A node deep in the left subtree must also be below the root. Only bounds passed down catch that."},
        {"text": "The values you see from the right side, top to bottom.",
         "options": ["BFS level by level, last node of each level", "In-order traversal", "A heap"], "answer": 0,
         "why": "One value per level: the last one dequeued in each round. (DFS visiting right first also works.)"},
        {"text": "The longest path between any two nodes (the diameter).",
         "options": ["Return the height, record left + right at each node", "BFS from the root", "Sort the values"], "answer": 0,
         "why": "The best path through a node is left height + right height, but the parent can only extend one side: return one thing, record another."},
        {"text": "The k-th smallest value in a binary search tree.",
         "options": ["In-order traversal, stop at the k-th", "BFS", "Pass bounds down"], "answer": 0,
         "why": "In-order visits a BST's values in sorted order."},
        {"text": "The fewest moves for a knight between two squares.",
         "options": ["Tree recursion", "BFS on a graph", "In-order traversal"], "answer": 1,
         "why": "Squares link in cycles, so it is a graph: BFS with a visited set, not tree recursion."},
    ],
    "near_misses": [
        ("A graph with cycles.", "Tree recursion assumes each node is reached once. With cycles you need a visited set: graphs."),
        ("A heap.", "Stored as a tree, but you never recurse on it: you sift along one path."),
        ("All paths from root to leaf with a property.", "Still a tree, but you build each path: that is backtracking on a tree."),
    ],
}

PARTS = {
    "names": [
        ("node", "the root of the subtree this call is about; None for an empty subtree"),
        ("left, right", "what the recursive calls returned: the depths of the two subtrees"),
        ("call stack", "the calls waiting for a child's answer, root at the bottom"),
    ],
    "plan": [
        ("Base case", "`node is None`: an empty subtree has depth 0."),
        ("Recurse", "ask the left subtree, then the right subtree."),
        ("Combine", "`1 + max(left, right)`: this node plus its deeper side."),
        ("Answer", "the root's call returns the depth of the whole tree."),
    ],
    "invariant": "Every call returns the depth of its own subtree, and nothing else.",
    "safe": [
        "The base case is right by definition: no nodes, depth 0.",
        "If the calls on the children return their subtrees' depths, `1 + max(left, right)` is this subtree's depth. That is the whole proof (induction on height).",
        "Each call is on a smaller subtree, so the recursion reaches `None` and stops.",
    ],
    "relies_on": "subtrees not sharing nodes, which is what makes it a tree. Recursion depth equals the tree's height: a skewed tree of 10⁴ nodes needs an explicit stack or a higher recursion limit.",
}


class TreeNode:
    def __init__(self, val, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def tree(values):
    """A tree from LeetCode's level-order list, None for a missing child."""
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        for side in ("left", "right"):
            if i < len(values) and values[i] is not None:
                setattr(node, side, TreeNode(values[i]))
                queue.append(getattr(node, side))
            i += 1
    return root


def max_depth(node):
    if node is None:
        return 0
    left = max_depth(node.left)
    right = max_depth(node.right)
    return 1 + max(left, right)


def level_order(root):
    levels = []
    queue = deque([root] if root else [])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        levels.append(level)
    return levels


REFERENCE = max_depth


def height(node):
    return 0 if node is None else 1 + max(height(node.left), height(node.right))


def tree_view(root, cls, tags, name):
    children, labels, stack = {}, {}, [root] if root else []
    while stack:
        n = stack.pop()
        labels[n.val] = n.val
        children[n.val] = [c.val for c in (n.left, n.right) if c]
        stack += [c for c in (n.right, n.left) if c]
    pos = tree_layout(root.val if root else None, children)
    nodes = [{"id": v, "label": v, "x": x, "y": y, "cls": cls.get(v, ""), "tag": tags.get(v, "")} for v, (x, y) in pos.items()]
    edges = [{"a": a, "b": b} for a, kids in children.items() for b in kids]
    return V.graph(name, nodes, edges)


def view(S):
    if S.func == "level_order" or "root" in S.outer:
        root = S.outer["root"]
        queue = [n.val for n in S.v.get("queue", [])]
        done = {v for level in S.v.get("levels", []) for v in level} | set(S.v.get("level", []))
        node = S.v.get("node")
        cls = {v: "ok" for v in done}
        cls.update({v: "front" for v in queue})
        if node is not None and S.text not in ("while queue:",):
            cls[node.val] = "cur"
        return [tree_view(root, cls, {}, "tree (amber: queued, green: visited)"),
                V.items("queue (front on the left)", queue), V.items("this level", S.v.get("level", [])),
                V.items("levels", S.v.get("levels", []))]
    root = S.outer["node"]
    returned = {s.v["node"].val: s.ret for s in S.trace[:S.index] if s.kind == "return" and s.v.get("node") is not None}
    on_stack = [f[1]["node"].val for f in S.stack if f[1].get("node") is not None]
    cls = {v: "ok" for v in returned}
    cls.update({v: "win" for v in on_stack})
    if S.v.get("node") is not None:
        cls[S.v["node"].val] = "cur"
    tags = {v: f"depth {d}" for v, d in returned.items()}
    calls = [f"max_depth({f[1]['node'].val if f[1].get('node') is not None else 'None'})" for f in S.stack]
    out = [tree_view(root, cls, tags, "tree (blue: this call, light: waiting, green: returned)"), V.items("call stack (bottom first)", calls)]
    if "left" in S.v or "right" in S.v:
        out.append(V.vars(("left", S.v.get("left")), ("right", S.v.get("right"))))
    return out


def say(S, N):
    if S.func == "level_order":
        if S.text == "node = queue.popleft()":
            return f"Took node {N.v['node'].val} off the front of the queue."
        if S.text.startswith("queue.append(node."):
            side = "left" if "left" in S.text else "right"
            return f"Queued node {getattr(S.node, side).val}, the {side} child of {S.node.val}."
        if S.text == "levels.append(level)":
            return f"Level {len(N.v['levels'])} is done: {S.level}."
        if S.text == "for _ in range(len(queue)):" and N.text == "node = queue.popleft()" and S.v.get("level") == []:
            return f"This level has {len(S.queue)} node(s): exactly what is in the queue now."
        return None
    if S.kind == "return":
        node = S.v.get("node")
        return f"max_depth({'None' if node is None else node.val}) returned {S.ret}."
    if N.depth > S.depth:
        node = N.v.get("node")
        return f"Called max_depth({'None' if node is None else node.val})." if N.func == "max_depth" else None
    return None


PREDICT = {
    "return 1 + max(left, right)": {
        "q": lambda S: f"At node {S.node.val}: left = {S.left}, right = {S.right}. What does this call return?",
        "answer": lambda S, N: 1 + max(S.left, S.right),
        "why": lambda S, N: f"This node plus its deeper side: 1 + {max(S.left, S.right)}.",
        "times": 3,
    },
    "node = queue.popleft()": {
        "q": "Which node comes off the queue next?",
        "answer": lambda S, N: N.v["node"].val,
        "why": "The queue is first in, first out: nodes leave in the order they were added, level by level.",
        "times": 3,
    },
}

ROW_COLS = ["call returns", "left", "right", "depth"]


def row(S, N):
    if S.kind == "return" and S.func == "max_depth" and S.v.get("node") is not None:
        return [f"max_depth({S.v['node'].val})", S.v["left"], S.v["right"], S.ret]
    if S.text == "levels.append(level)":
        return [len(S.v["levels"]) + 1, S.v["level"], [n.val for n in S.v["queue"]]]
    return None


def INVARIANT(S):
    if S.kind == "return" and S.func == "max_depth":
        return S.ret == height(S.v["node"])
    return True


TRACES = [
    {"label": "Depth: [3, 9, 20, null, null, 15, 7]", "args": (tree([3, 9, 20, None, None, 15, 7]),), "expect": 3,
     "about": "Depth-first. A call waits (light blue) until both children have answered, then returns its own depth."},
    {"label": "Levels: the same tree, breadth-first", "fn": level_order, "args": (tree([3, 9, 20, None, None, 15, 7]),),
     "cols": ["level", "values", "queue after it"],
     "expect": [[3], [9, 20], [15, 7]],
     "about": "Breadth-first with a queue. Each round of the outer loop takes exactly one level off the queue."},
]


def random_tree(rng):
    n = rng.randint(0, 9)
    values = [rng.randint(1, 50) if rng.random() < 0.8 or i == 0 else None for i in range(n)]
    return tree(values)


def levels_brute(root):
    out = {}

    def walk(node, d):
        if node:
            out.setdefault(d, []).append(node.val)
            walk(node.left, d + 1)
            walk(node.right, d + 1)
    walk(root, 0)
    return [out[d] for d in sorted(out)]


def inputs(rng):
    return [(None,), (TreeNode(1),)] + [(random_tree(rng),) for _ in range(300)]


ORACLE = [{"brute": height, "inputs": inputs},
          {"fn": level_order, "brute": levels_brute, "inputs": inputs}]

FAMILY_INTRO = "Name what a call returns, and what (if anything) it needs from above. That picks the member."
FAMILY = [
    {"name": "Return a value up", "change": "The depth trace above. Invert: swap the children, return the node. Same tree: both None, or equal values and both subtrees the same.",
     "problems": ["maximum-depth-of-binary-tree", "invert-binary-tree", "same-tree", "subtree-of-another-tree"]},
    {"name": "Return one thing, record another", "change": "Return the height; at each node record `left + right` (diameter) or `node.val + max(0, left) + max(0, right)` (max path sum). Balanced: return the height, or -1 once a subtree is unbalanced.",
     "problems": ["diameter-of-binary-tree", "balanced-binary-tree", "binary-tree-maximum-path-sum"]},
    {"name": "Pass information down", "change": "Validate a BST with `(low, high)` bounds; count good nodes with the largest value on the path so far.",
     "problems": ["validate-binary-search-tree", "count-good-nodes-in-binary-tree"]},
    {"name": "Use the BST order", "change": "In-order yields sorted values (k-th smallest). For the lowest common ancestor in a BST, walk down until p and q fall on different sides.",
     "problems": ["kth-smallest-element-in-a-bst", "lowest-common-ancestor-of-a-binary-search-tree"]},
    {"name": "Level by level", "change": "The second trace: `for _ in range(len(queue))` takes exactly one level per round. Right side view = the last value of each level.",
     "problems": ["binary-tree-level-order-traversal", "binary-tree-right-side-view"]},
    {"name": "Build and serialize", "change": "Preorder's first value is the root; its position in inorder splits the left and right subtrees. Serialize with a preorder that writes `None` markers.",
     "problems": ["construct-binary-tree-from-preorder-and-inorder-traversal", "serialize-and-deserialize-binary-tree"]},
]

COUNT = {
    "line": "if node is None:",
    "input": lambda n: (tree(list(range(1, n + 1))),),
    "sizes": [15, 31, 63, 127],
    "bound": lambda n: 2 * n + 1,
    "bound_text": "2n + 1",
    "text": ["There is one call per node and one per empty child. A tree of n nodes has n + 1 empty child slots, so the "
             "base-case check runs exactly 2n + 1 times, each O(1). Doubling n doubles it. BFS is the same: each node is "
             "queued once and dequeued once."],
    "time": "O(n)",
    "space": "O(h) for the call stack, h the height: O(log n) when balanced, O(n) when skewed. BFS keeps up to one level, O(n) at worst.",
}

TRAPS = [
    ("Checking a BST against its children only", "misses a value deep in the left subtree that is larger than the root. Pass bounds down."),
    ("No `None` case", "crashes at the first leaf's child, or counts leaves wrong."),
    ("Returning the path through both children to the parent", "in max path sum: a parent can extend only one side."),
    ("Deep recursion on a skewed tree", "hits Python's recursion limit (about 1000). Use an explicit stack for very deep trees."),
]


CHECK = {
    "trace": {"text": "Run max_depth on the tree [1, 2, 3, 4, null, null, 5, 6] (6 hangs left of 4). What does the call on node 2 return, and what does the root's call return?",
              "args": (tree([1, 2, 3, 4, None, None, 5, 6]),),
              "fields": [("max_depth(node 2) returns", lambda run: next(s.ret for s in run["states"] if s.kind == "return" and s.v.get("node") is not None and s.v["node"].val == 2)),
                         ("max_depth(root) returns", lambda run: run["result"])]},
    "questions": [
        {"q": "To check a BST, a coworker compares each node only with its two children. Which tree passes their check but isn't a BST?",
         "options": ["5 with children 3 and 8, and 6 as the left child of 3", "5 with children 3 and 8", "A single node"], "answer": 0,
         "why": "6 > 3 is fine locally, but 6 sits in 5's left subtree and is larger than 5. Bounds passed down catch it."},
        {"q": "The minimum depth (root to the nearest leaf) of a tree with 10⁵ nodes, mostly in one long branch. Which order finds it with the least work?",
         "options": ["DFS: depth of every subtree", "BFS: stop at the first leaf dequeued", "In-order"], "answer": 1,
         "why": "BFS reaches nodes in order of depth, so the first leaf it meets is the nearest; it never walks the long branch."},
    ],
    "own": {"prompt": "What does each call of a tree recursion promise, and why does that give the answer for the whole tree?",
            "model": "Each call promises the answer for the subtree it was given: for depth, 0 for None, otherwise 1 + the larger of its children's depths. If the two calls on the children keep that promise, combining them keeps it for the node, so by induction the root's call returns the whole tree's answer. When a node needs information from above, pass it down as an argument; when the answer differs from what a parent can use, return one thing and record the other."},
}
