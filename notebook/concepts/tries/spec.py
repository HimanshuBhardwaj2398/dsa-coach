"""Tries, explained. Build: python3 skills/dsa-coach/scripts/build_explainer.py notebook/concepts/tries/spec.py"""
from build_explainer import V, tree_layout

TITLE = "Tries, explained"
PITCH = ("A tree of characters where every node is a prefix. Words that share a beginning share a path, so a prefix "
         "lookup costs the length of the prefix, however many words are stored.")

SPOT = {
    "idea": [
        "A trie (prefix tree) stores words letter by letter: the root is the empty prefix, each edge adds one character, "
        "and a marker says where a whole word ends. Looking up a word or a prefix walks one edge per character: O(L), "
        "independent of how many words there are.",
        "Reach for it when the questions are about **prefixes** (autocomplete, \"does any word start with...\"), when a "
        "**wildcard** must try several letters, or when **many words** are searched at once, as on a letter grid, so "
        "a dead prefix stops every word that shares it. For plain membership, a hash set is simpler.",
    ],
    "questions": [
        ("Are the questions about prefixes?", "Starts-with, autocomplete, the shortest root of a word."),
        ("Do many words share work?", "Searching all of them on one grid: walk the trie and the grid together."),
        ("Is there a wildcard?", "At a `.`, try every child: DFS through the trie."),
        ("What marks a whole word?", "An end flag, so that 'car' isn't found just because 'cart' is stored."),
    ],
    "cases": [
        {"text": "Implement insert, search and startsWith for a dictionary.",
         "options": ["A trie", "A hash set only", "A sorted list"], "answer": 0,
         "why": "startsWith on a hash set means checking every word. A trie answers it by walking the prefix."},
        {"text": "Find every dictionary word that appears on a grid of letters.",
         "options": ["A trie of the words plus backtracking on the grid", "Backtracking per word", "BFS from every cell"], "answer": 0,
         "why": "One walk of the grid follows the trie; a prefix that isn't in the trie stops all words with it at once."},
        {"text": "Is this word in the list? (One query type: exact membership.)",
         "options": ["A trie", "A hash set", "Binary search on unsorted words"], "answer": 1,
         "why": "Exact membership is what a hash set does in O(L), with far less code and memory."},
        {"text": "Search words where '.' matches any letter.",
         "options": ["A trie, branching at each '.'", "A regular expression over every word", "A heap"], "answer": 0,
         "why": "Letters follow one edge; a '.' tries each child. Prefixes shared by many words are explored once."},
        {"text": "Top 3 search suggestions as each letter is typed.",
         "options": ["A trie (or a sorted list with binary search)", "A hash map of full words", "Union-find"], "answer": 0,
         "why": "Each typed letter moves one node deeper; the suggestions are the words under that node."},
        {"text": "The longest common prefix of a list of words.",
         "options": ["A trie, or compare the words column by column", "A heap", "BFS"], "answer": 0,
         "why": "Walk down while exactly one child exists and no word ends. Comparing column by column does the same with no extra structure."},
    ],
    "near_misses": [
        ("Exact membership only.", "A hash set: same O(L) per lookup, far less memory."),
        ("Substring search in one long text.", "A trie of prefixes doesn't help; KMP, rolling hashes or a suffix structure do."),
        ("Anagram groups.", "Order of letters doesn't matter: hash the sorted word or the letter counts."),
    ],
}

PARTS = {
    "names": [
        ("root", "the empty prefix: a dict from a first letter to a child node"),
        ("node", "the prefix read so far; its keys are the letters that can come next"),
        ('"$"', "the end marker: a whole word ends at this node"),
    ],
    "plan": [
        ("Insert", "from the root, follow each letter, creating a node when it's missing; mark the last node with `$`."),
        ("Search", "follow each letter; a missing letter means no such word or prefix."),
        ("Word or prefix?", "at the end, a word needs `$`; a prefix needs only to have got there."),
        ("Cost", "one step per character: O(L) for a word of length L."),
    ],
    "invariant": "Every node stands for the prefix spelled on the path from the root to it, and it carries `$` exactly when that prefix is an inserted word.",
    "safe": [
        "Two words share the nodes of their common prefix and no more, so inserting one never changes another's path.",
        "`setdefault(ch, {})` reuses an existing child, so the same prefix is never stored twice.",
        "A search that falls off the trie at letter i proves no stored word starts with those i + 1 letters.",
    ],
    "relies_on": "a small alphabet per node and shared prefixes. With few shared prefixes, a trie is mostly overhead compared with a hash set.",
}


def build_trie(words):
    root = {}
    for word in words:
        node = root
        for ch in word:
            node = node.setdefault(ch, {})
        node["$"] = True
    return root


def search(root, word):
    node = root
    for ch in word:
        if ch not in node:
            return False
        node = node[ch]
    return "$" in node


REFERENCE = build_trie
WORDS = ["car", "cart", "cat", "dog", "do"]


def prefixes(root):
    """Every node by its prefix, with its children's prefixes."""
    nodes, children, stack = {"": root}, {}, [""]
    while stack:
        p = stack.pop()
        kids = sorted(k for k in nodes[p] if k != "$")
        children[p] = [p + k for k in kids]
        for k in kids:
            nodes[p + k] = nodes[p][k]
            stack.append(p + k)
    return nodes, children


def where(nodes, target):
    return next((p for p, n in nodes.items() if n is target), None)


def view(S):
    root = S.outer.get("root")
    if root is None:
        return [V.items("words", S.outer["words"])]
    nodes, children = prefixes(root)
    here = where(nodes, S.v.get("node")) if "node" in S.v else None
    pos = tree_layout("", children)
    trail = {here[:i] for i in range(len(here) + 1)} if here is not None else set()
    g = [{"id": p or "root", "label": p[-1] if p else "·", "x": x, "y": y,
          "cls": "cur" if p == here else "win" if p in trail else "ok" if "$" in nodes[p] else "",
          "tag": "end" if "$" in nodes[p] else ""} for p, (x, y) in pos.items()]
    edges = [{"a": a or "root", "b": b, "cls": "cur" if b in trail else ""} for a, kids in children.items() for b in kids]
    out = [V.graph("trie (blue: current node, light: the path to it, green: a word ends here)", g, edges,
                   w=max([x for x, _ in pos.values()] + [0]) + 1, h=max([y for _, y in pos.values()] + [0]) + 1)]
    if S.func == "build_trie":
        word = S.v.get("word")
        out.append(V.vars(("word", word), ("ch", S.v.get("ch")), ("prefix so far", here)))
    else:
        out.append(V.vars(("word", S.outer["word"]), ("ch", S.v.get("ch")), ("prefix so far", here)))
    return out


def say(S, N):
    if S.text == "node = node.setdefault(ch, {})":
        nodes, _ = prefixes(S.outer["root"])
        here = where(nodes, S.v["node"])
        made = (here + S.ch) not in nodes
        return f"'{S.ch}' after '{here}': {'created a new node' if made else 'the node exists already: shared with an earlier word'}."
    if S.text == 'node["$"] = True':
        return f"Marked the end of '{S.word}'."
    if S.text == "if ch not in node:":
        return f"'{S.ch}' is a child here: follow it." if N.text != "return False" else f"No '{S.ch}' here: the word isn't stored."
    if S.text == 'return "$" in node':
        return None
    return None


PREDICT = {
    "node = node.setdefault(ch, {})": {
        "q": lambda S: f"Inserting '{S.word}': does the prefix '{where(prefixes(S.outer['root'])[0], S.v['node'])}{S.ch}' already have a node?",
        "options": ["yes: reuse it", "no: create it"],
        "answer": lambda S, N: "yes: reuse it" if S.ch in S.v["node"] else "no: create it",
        "why": "Words share the nodes of their common prefix.",
        "when": lambda S: S.word != "car",
        "times": 4,
    },
    'return "$" in node': {
        "q": lambda S: f"Every letter of '{S.outer['word']}' was found. Is it a stored word?",
        "options": ["yes", "no: only a prefix"],
        "answer": lambda S, N: "yes" if "$" in S.v["node"] else "no: only a prefix",
        "why": "Reaching the node proves the prefix exists; the end marker decides whether a word ends there.",
        "times": 1,
    },
}

ROW_COLS = ["word", "new nodes", "nodes in all"]


def count_nodes(root):
    return len(prefixes(root)[0])


def row(S, N):
    if S.text == 'node["$"] = True':
        before = next((t for t in reversed(S.trace[:S.index]) if t.text == "node = root"), None)
        had = count_nodes(before.outer["root"]) if before else 1
        now = count_nodes(S.outer["root"])
        return [S.word, now - had, now]
    if S.text == "if ch not in node:":
        nodes, _ = prefixes(S.outer["root"])
        return [S.ch, "found" if S.ch in S.v["node"] else "missing", where(nodes, S.v["node"]) + (S.ch if S.ch in S.v["node"] else "")]
    return None


def INVARIANT(S):
    if S.kind == "return" and S.func == "build_trie":
        return all(search(S.ret, w) for w in S.outer["words"]) and count_nodes(S.ret) == 1 + len({w[:i] for w in S.outer["words"] for i in range(1, len(w) + 1)})
    return True


TRACES = [
    {"label": "Insert car, cart, cat, dog, do", "args": (WORDS,),
     "about": "Watch 'cart' reuse all of 'car', and 'do' add no node at all: only an end marker.", "cols": ROW_COLS},
    {"label": "Search 'ca' (a prefix, not a word)", "fn": search, "args": (build_trie(WORDS), "ca"), "expect": False,
     "about": "Both letters are found, but no word ends at 'ca'.", "cols": ["letter", "here?", "prefix reached"]},
    {"label": "Search 'cab' (falls off)", "fn": search, "args": (build_trie(WORDS), "cab"), "expect": False,
     "about": "'ca' exists, but no word continues with 'b'.", "cols": ["letter", "here?", "prefix reached"]},
]


def word_inputs(rng):
    out = []
    for _ in range(200):
        words = ["".join(rng.choice("abc") for _ in range(rng.randint(0, 4))) for _ in range(rng.randint(0, 6))]
        probe = "".join(rng.choice("abc") for _ in range(rng.randint(0, 4)))
        out.append((words, probe))
    return out


ORACLE = [{"fn": lambda words, probe: search(build_trie(words), probe), "brute": lambda words, probe: probe in words,
           "inputs": word_inputs},
          {"fn": lambda words, probe: count_nodes(build_trie(words)),
           "brute": lambda words, probe: 1 + len({w[:i] for w in words for i in range(1, len(w) + 1)}),
           "inputs": word_inputs}]

FAMILY_INTRO = "The trie is the same in every member; what changes is how it is walked."
FAMILY = [
    {"name": "Insert, search, starts-with", "change": "The traces above. `startsWith` is search without the end-marker check.",
     "problems": ["implement-trie-prefix-tree"]},
    {"name": "Wildcards: branch at '.'", "change": "A DFS over (node, index): a letter follows one child, a '.' tries every child. Shared prefixes are explored once.",
     "problems": ["design-add-and-search-words-data-structure"],
     "code": "def match(node, word, i):\n    if i == len(word):\n        return \"$\" in node\n    if word[i] == \".\":\n        return any(match(child, word, i + 1) for ch, child in node.items() if ch != \"$\")\n    return word[i] in node and match(node[word[i]], word, i + 1)"},
    {"name": "Many words at once on a grid", "change": "Backtrack on the grid while walking the trie: a cell whose letter isn't a child prunes every word with that prefix. Remove a word's end marker once found, so it is reported once.",
     "problems": ["word-search-ii"]},
]


def word_list(n):
    words, alphabet = [], "abcdefghijklmnopqrstuvwxyz"
    for i in range(n):
        w, x = "", i
        for _ in range(5):
            w += alphabet[x % 26]
            x //= 26
        words.append(w)
    return (words,)


COUNT = {
    "line": "node = node.setdefault(ch, {})",
    "input": word_list,
    "sizes": [16, 32, 64, 128],
    "bound": lambda n: 5 * n,
    "bound_text": "5n (n words of 5 letters: their total length)",
    "n_name": "words of 5 letters",
    "text": ["The inner line runs once per character inserted, so its runs are the total length of the words, and each "
             "run is one dict operation. A search runs it at most once per character of the query: O(L), whether the "
             "trie holds ten words or a million."],
    "time": "O(total length) to build; O(L) per query.",
    "space": "O(total length) at most, less when words share prefixes.",
}

TRAPS = [
    ("No end marker", "reports 'car' as stored when only 'cart' is."),
    ("A mutable default for children (`children={}`)", "makes every node share one dict."),
    ("Word Search II without pruning found words", "reports a word once per path and keeps searching dead branches."),
    ("A trie for exact membership only", "costs memory and code for what a set does."),
]


CHECK = {
    "trace": {"text": "Insert ['to', 'tea', 'ten', 'i'] with build_trie. How many nodes does the trie have, counting the root, and how many new nodes does 'ten' add?",
              "args": (["to", "tea", "ten", "i"],),
              "fields": [("Nodes in all, with the root", lambda run: count_nodes(run["result"])),
                         ("New nodes added by 'ten'", lambda run: count_nodes(build_trie(["to", "tea", "ten"])) - count_nodes(build_trie(["to", "tea"])))]},
    "questions": [
        {"q": "You only ever ask whether a whole word is in a list of 10⁵ words. Trie or set?",
         "options": ["A trie: it's O(L)", "A set: also O(L) per lookup, far less memory and code", "A sorted list"], "answer": 1,
         "why": "A trie earns its memory only when prefixes matter."},
        {"q": "Word Search II with 10⁴ words on a 12 × 12 grid. Why build a trie of the words first?",
         "options": ["To sort the words", "One grid walk serves every word, and a dead prefix stops all words with it", "Tries use less memory"], "answer": 1,
         "why": "Searching each word separately repeats the same grid walks for shared prefixes."},
    ],
    "own": {"prompt": "What does each node of a trie stand for, and when is a trie worth it over a hash set?",
            "model": "Each node stands for the prefix spelled from the root to it; words that share a beginning share those nodes, and an end marker says where a whole word stops. Any lookup walks one edge per character, O(L), no matter how many words are stored. That pays off when the questions are about prefixes, wildcards, or many words searched together; for plain membership a hash set does the same job more simply."},
}
