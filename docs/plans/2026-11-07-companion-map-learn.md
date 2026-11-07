# Companion, milestone A: Map and Learn Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the study app's home a map of the roadmap's patterns. Each pattern opens a Learn page with its cues, invariant, template, a coach-written explainer, resources and its Blind 75 / NeetCode 150 problems, which link to LeetCode.

**Architecture:**
- `coach.py` gets a problem catalogue (`assets/problems.json`), per-pattern resources (in `roadmap.json`) and a `map` command. The command joins the catalogue with progress `compute()` already works out.
- `app/server.py` serves that map, and runs the coach headless (`claude -p`) through a new `app/claude_job.py` to write explainers.
- The page gains `nav.js` (hash routes `#/map`, `#/learn/<key>`, `#/solve`). It reuses `app.js`'s helpers, and `app.js` (the Solve view) is untouched.

**Tech stack:** Python 3 stdlib, plain JS with no framework or build step, `unittest`, `node --test`, Playwright for the browser check. Spec: `docs/plans/2026-11-07-companion-map-learn-design.md`.

**Rules for the executor:**
- Keep it simple: small functions, data shaping in pure functions, no speculative options.
- Never hand-edit `notebook/`'s generated files.
- Run the full suites at the end of every task:

```bash
python3 -m unittest discover -s tests
node --test tests/frontend/
```

---

### Task 0: Clean start

The working tree holds uncommitted work: the calm Solve layout and plan 001's reliability changes, plus learner files in `notebook/`.

**Step 1:** Ask Himanshu how to commit the existing work: two commits (layout, plan 001) or one. Never include `notebook/` in implementation commits.

**Step 2:**

```bash
git checkout -b companion-map-learn
```

**Step 3:** Run both suites. Expected: all pass (127 Python, 21 node at the time of writing).

---

### Task 1: The problem catalogue

**Files:**
- Create: `skills/dsa-coach/assets/problems.json`
- Modify: `skills/dsa-coach/scripts/coach.py` (constants near `LONG_FORMATS`, a loader next to `load_roadmap`, and `cmd_validate`)
- Create: `tests/test_catalogue.py`

**Step 1: Write the failing tests** (`tests/test_catalogue.py`)

```python
"""The problem catalogue (assets/problems.json). Run: python3 -m unittest discover -s tests -v"""
import importlib.util
import unittest
from pathlib import Path

COACH = Path(__file__).resolve().parent.parent / "skills" / "dsa-coach" / "scripts" / "coach.py"
spec = importlib.util.spec_from_file_location("coach", COACH)
coach = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coach)


class CatalogueTest(unittest.TestCase):
    def test_shipped_catalogue_fits_the_roadmap(self):
        self.assertEqual(coach.catalogue_issues(coach.load_catalogue(), coach.load_roadmap()), [])

    def test_shipped_catalogue_holds_both_lists(self):
        rows = [r for rows in coach.load_catalogue().values() for r in rows]
        self.assertEqual(sum("blind75" in r["lists"] for r in rows), 75)
        self.assertEqual(sum("nc150" in r["lists"] for r in rows), 150)

    def test_reports_what_doesnt_fit(self):
        roadmap = {"patterns": [{"key": "stack", "canonical": ["valid-parentheses"]}]}
        bad = {"stack": [{"slug": "Bad Slug", "title": "", "difficulty": "trivial", "lists": ["top100"]},
                         {"slug": "min-stack", "title": "Min Stack", "difficulty": "medium", "lists": ["nc150"]},
                         {"slug": "min-stack", "title": "Min Stack", "difficulty": "medium", "lists": ["nc150"]}],
               "nope": []}
        issues = "\n".join(coach.catalogue_issues(bad, roadmap))
        for expected in ("nope isn't a roadmap pattern", "lacks its canonical problem valid-parentheses",
                         "bad slug 'Bad Slug'", "min-stack is listed twice", "no title", "difficulty 'trivial'",
                         "lists ['top100']"):
            self.assertIn(expected, issues)
```

**Step 2: Run them and check they fail.**

```bash
python3 -m unittest tests.test_catalogue -v
```

Expected: ERROR, `module 'coach' has no attribute 'catalogue_issues'`.

**Step 3: Create `skills/dsa-coach/assets/problems.json`**

- **Format:** one key per roadmap pattern; each holds an ordered list of `{slug, title, difficulty, lists}`.
- **`lists` values:**
  - `blind75` and `nc150` mark the two lists;
  - `roadmap` marks a canonical problem that's in neither list (prefix sums).
- **Left out:** the three non-LeetCode formats (`machine-coding`, `ai-assisted`, `ml-coding`).
- **Generating it:** write the file with this script, run once from the repo root, then deleted. It is the reviewed catalogue: NeetCode 150, plus Combination Sum IV (Blind 75's one problem outside NeetCode 150), plus the prefix-sums canonical problems.

```python
import json
D = {"E": "easy", "M": "medium", "H": "hard"}
F = {"B": "blind75", "N": "nc150", "R": "roadmap"}
DATA = """
arrays-hashing
contains-duplicate|Contains Duplicate|E|BN
valid-anagram|Valid Anagram|E|BN
two-sum|Two Sum|E|BN
group-anagrams|Group Anagrams|M|BN
top-k-frequent-elements|Top K Frequent Elements|M|BN
encode-and-decode-strings|Encode and Decode Strings|M|BN
product-of-array-except-self|Product of Array Except Self|M|BN
valid-sudoku|Valid Sudoku|M|N
longest-consecutive-sequence|Longest Consecutive Sequence|M|BN
two-pointers
valid-palindrome|Valid Palindrome|E|BN
two-sum-ii-input-array-is-sorted|Two Sum II - Input Array Is Sorted|M|N
3sum|3Sum|M|BN
container-with-most-water|Container With Most Water|M|BN
trapping-rain-water|Trapping Rain Water|H|N
sliding-window
best-time-to-buy-and-sell-stock|Best Time to Buy and Sell Stock|E|BN
longest-substring-without-repeating-characters|Longest Substring Without Repeating Characters|M|BN
longest-repeating-character-replacement|Longest Repeating Character Replacement|M|BN
permutation-in-string|Permutation in String|M|N
minimum-window-substring|Minimum Window Substring|H|BN
sliding-window-maximum|Sliding Window Maximum|H|N
prefix-sums
range-sum-query-immutable|Range Sum Query - Immutable|E|R
subarray-sum-equals-k|Subarray Sum Equals K|M|R
continuous-subarray-sum|Continuous Subarray Sum|M|R
stack
valid-parentheses|Valid Parentheses|E|BN
min-stack|Min Stack|M|N
evaluate-reverse-polish-notation|Evaluate Reverse Polish Notation|M|N
generate-parentheses|Generate Parentheses|M|N
daily-temperatures|Daily Temperatures|M|N
car-fleet|Car Fleet|M|N
largest-rectangle-in-histogram|Largest Rectangle in Histogram|H|N
binary-search
binary-search|Binary Search|E|N
search-a-2d-matrix|Search a 2D Matrix|M|N
koko-eating-bananas|Koko Eating Bananas|M|N
find-minimum-in-rotated-sorted-array|Find Minimum in Rotated Sorted Array|M|BN
search-in-rotated-sorted-array|Search in Rotated Sorted Array|M|BN
time-based-key-value-store|Time Based Key-Value Store|M|N
median-of-two-sorted-arrays|Median of Two Sorted Arrays|H|N
linked-list
reverse-linked-list|Reverse Linked List|E|BN
merge-two-sorted-lists|Merge Two Sorted Lists|E|BN
linked-list-cycle|Linked List Cycle|E|BN
reorder-list|Reorder List|M|BN
remove-nth-node-from-end-of-list|Remove Nth Node From End of List|M|BN
copy-list-with-random-pointer|Copy List with Random Pointer|M|N
add-two-numbers|Add Two Numbers|M|N
find-the-duplicate-number|Find the Duplicate Number|M|N
lru-cache|LRU Cache|M|N
merge-k-sorted-lists|Merge k Sorted Lists|H|BN
reverse-nodes-in-k-group|Reverse Nodes in k-Group|H|N
trees
invert-binary-tree|Invert Binary Tree|E|BN
maximum-depth-of-binary-tree|Maximum Depth of Binary Tree|E|BN
diameter-of-binary-tree|Diameter of Binary Tree|E|N
balanced-binary-tree|Balanced Binary Tree|E|N
same-tree|Same Tree|E|BN
subtree-of-another-tree|Subtree of Another Tree|E|BN
lowest-common-ancestor-of-a-binary-search-tree|Lowest Common Ancestor of a Binary Search Tree|M|BN
binary-tree-level-order-traversal|Binary Tree Level Order Traversal|M|BN
binary-tree-right-side-view|Binary Tree Right Side View|M|N
count-good-nodes-in-binary-tree|Count Good Nodes in Binary Tree|M|N
validate-binary-search-tree|Validate Binary Search Tree|M|BN
kth-smallest-element-in-a-bst|Kth Smallest Element in a BST|M|BN
construct-binary-tree-from-preorder-and-inorder-traversal|Construct Binary Tree from Preorder and Inorder Traversal|M|BN
binary-tree-maximum-path-sum|Binary Tree Maximum Path Sum|H|BN
serialize-and-deserialize-binary-tree|Serialize and Deserialize Binary Tree|H|BN
heap
kth-largest-element-in-a-stream|Kth Largest Element in a Stream|E|N
last-stone-weight|Last Stone Weight|E|N
k-closest-points-to-origin|K Closest Points to Origin|M|N
kth-largest-element-in-an-array|Kth Largest Element in an Array|M|N
task-scheduler|Task Scheduler|M|N
design-twitter|Design Twitter|M|N
find-median-from-data-stream|Find Median from Data Stream|H|BN
backtracking
subsets|Subsets|M|N
combination-sum|Combination Sum|M|N
combination-sum-ii|Combination Sum II|M|N
permutations|Permutations|M|N
subsets-ii|Subsets II|M|N
word-search|Word Search|M|BN
palindrome-partitioning|Palindrome Partitioning|M|N
letter-combinations-of-a-phone-number|Letter Combinations of a Phone Number|M|N
n-queens|N-Queens|H|N
graphs
number-of-islands|Number of Islands|M|BN
max-area-of-island|Max Area of Island|M|N
clone-graph|Clone Graph|M|BN
walls-and-gates|Walls and Gates|M|N
rotting-oranges|Rotting Oranges|M|N
pacific-atlantic-water-flow|Pacific Atlantic Water Flow|M|BN
surrounded-regions|Surrounded Regions|M|N
course-schedule|Course Schedule|M|BN
course-schedule-ii|Course Schedule II|M|N
graph-valid-tree|Graph Valid Tree|M|BN
number-of-connected-components-in-an-undirected-graph|Number of Connected Components in an Undirected Graph|M|BN
redundant-connection|Redundant Connection|M|N
word-ladder|Word Ladder|H|N
tries
implement-trie-prefix-tree|Implement Trie (Prefix Tree)|M|BN
design-add-and-search-words-data-structure|Design Add and Search Words Data Structure|M|BN
word-search-ii|Word Search II|H|BN
intervals
insert-interval|Insert Interval|M|BN
merge-intervals|Merge Intervals|M|BN
non-overlapping-intervals|Non-overlapping Intervals|M|BN
meeting-rooms|Meeting Rooms|E|BN
meeting-rooms-ii|Meeting Rooms II|M|BN
minimum-interval-to-include-each-query|Minimum Interval to Include Each Query|H|N
greedy
maximum-subarray|Maximum Subarray|M|BN
jump-game|Jump Game|M|BN
jump-game-ii|Jump Game II|M|N
gas-station|Gas Station|M|N
hand-of-straights|Hand of Straights|M|N
merge-triplets-to-form-target-triplet|Merge Triplets to Form Target Triplet|M|N
partition-labels|Partition Labels|M|N
valid-parenthesis-string|Valid Parenthesis String|M|N
1d-dp
climbing-stairs|Climbing Stairs|E|BN
min-cost-climbing-stairs|Min Cost Climbing Stairs|E|N
house-robber|House Robber|M|BN
house-robber-ii|House Robber II|M|BN
longest-palindromic-substring|Longest Palindromic Substring|M|BN
palindromic-substrings|Palindromic Substrings|M|BN
decode-ways|Decode Ways|M|BN
coin-change|Coin Change|M|BN
maximum-product-subarray|Maximum Product Subarray|M|BN
word-break|Word Break|M|BN
longest-increasing-subsequence|Longest Increasing Subsequence|M|BN
partition-equal-subset-sum|Partition Equal Subset Sum|M|N
combination-sum-iv|Combination Sum IV|M|B
2d-dp
unique-paths|Unique Paths|M|BN
longest-common-subsequence|Longest Common Subsequence|M|BN
best-time-to-buy-and-sell-stock-with-cooldown|Best Time to Buy and Sell Stock with Cooldown|M|N
coin-change-ii|Coin Change II|M|N
target-sum|Target Sum|M|N
interleaving-string|Interleaving String|M|N
longest-increasing-path-in-a-matrix|Longest Increasing Path in a Matrix|H|N
distinct-subsequences|Distinct Subsequences|H|N
edit-distance|Edit Distance|M|N
burst-balloons|Burst Balloons|H|N
regular-expression-matching|Regular Expression Matching|H|N
advanced-graphs
reconstruct-itinerary|Reconstruct Itinerary|H|N
min-cost-to-connect-all-points|Min Cost to Connect All Points|M|N
network-delay-time|Network Delay Time|M|N
swim-in-rising-water|Swim in Rising Water|H|N
alien-dictionary|Alien Dictionary|H|BN
cheapest-flights-within-k-stops|Cheapest Flights Within K Stops|M|N
math-geometry
rotate-image|Rotate Image|M|BN
spiral-matrix|Spiral Matrix|M|BN
set-matrix-zeroes|Set Matrix Zeroes|M|BN
happy-number|Happy Number|E|N
plus-one|Plus One|E|N
powx-n|Pow(x, n)|M|N
multiply-strings|Multiply Strings|M|N
detect-squares|Detect Squares|M|N
bit-manipulation
single-number|Single Number|E|N
number-of-1-bits|Number of 1 Bits|E|BN
counting-bits|Counting Bits|E|BN
reverse-bits|Reverse Bits|E|BN
missing-number|Missing Number|E|BN
sum-of-two-integers|Sum of Two Integers|M|BN
reverse-integer|Reverse Integer|M|N
"""
out, key = {}, None
for line in DATA.strip().splitlines():
    if "|" not in line:
        key = line
        out[key] = []
        continue
    slug, title, d, flags = line.split("|")
    out[key].append({"slug": slug, "title": title, "difficulty": D[d], "lists": [F[c] for c in flags]})
with open("skills/dsa-coach/assets/problems.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
    f.write("\n")
```

**Step 4: Add the loader and the check to `coach.py`**

Next to `LONG_FORMATS`:

```python
LISTS = ("blind75", "nc150", "roadmap")  # problems.json: the two lists, or a canonical problem outside both
```

Below `load_roadmap()`:

```python
def load_catalogue() -> dict:
    data = read_json(ASSETS / "problems.json", None)
    if data is None:
        die(f"missing {ASSETS / 'problems.json'}")
    return data


def catalogue_issues(catalogue: dict, roadmap: dict) -> list:
    """What in problems.json doesn't fit the roadmap or the format: for validate."""
    issues, seen = [], set()
    patterns = {p["key"]: p for p in roadmap["patterns"]}
    issues += [f"problems.json: {key} isn't a roadmap pattern" for key in catalogue if key not in patterns]
    for key, p in patterns.items():
        listed = {r.get("slug") for r in catalogue.get(key, [])}
        if key not in LONG_FORMATS:
            issues += [f"problems.json: {key} lacks its canonical problem {s}"
                       for s in p.get("canonical", []) if s not in listed]
    for key, rows in catalogue.items():
        for r in rows:
            slug = r.get("slug", "")
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
                issues.append(f"problems.json: bad slug {slug!r} in {key}")
            elif slug in seen:
                issues.append(f"problems.json: {slug} is listed twice")
            seen.add(slug)
            if not r.get("title"):
                issues.append(f"problems.json: {slug} has no title")
            if r.get("difficulty") not in DIFFICULTIES:
                issues.append(f"problems.json: {slug} has difficulty {r.get('difficulty')!r}")
            if not r.get("lists") or set(r["lists"]) - set(LISTS):
                issues.append(f"problems.json: {slug} has lists {r.get('lists')}")
    return issues
```

In `cmd_validate`, right after the duplicate-pattern-key check:

```python
    issues += catalogue_issues(load_catalogue(), roadmap)
```

**Step 5: Run the tests and `validate`.**

```bash
python3 -m unittest tests.test_catalogue -v
python3 skills/dsa-coach/scripts/coach.py validate
```

Expected: 3 tests pass; validate prints `OK`.

**Step 6: Commit**

```bash
git add skills/dsa-coach/assets/problems.json skills/dsa-coach/scripts/coach.py tests/test_catalogue.py
git commit -m "Catalogue: NeetCode 150 and Blind 75 by roadmap pattern"
```

---

### Task 2: Resources per pattern

The Learn page lists two or three resources. They live with the pattern in `roadmap.json`, and every URL must already be in `references/resources.md`, so there is one vetted source.

**Files:**
- Modify: `skills/dsa-coach/assets/roadmap.json` (add `"resources"` to patterns)
- Modify: `tests/test_catalogue.py`

**Step 1: Write the failing test** (append to `CatalogueTest`)

```python
    def test_resources_come_from_the_vetted_list(self):
        vetted = (COACH.parent.parent / "references" / "resources.md").read_text(encoding="utf-8")
        for p in coach.load_roadmap()["patterns"]:
            for r in p.get("resources", []):
                self.assertTrue(r["title"], p["key"])
                self.assertIn(r["url"], vetted, f"{p['key']}: {r['url']} isn't in references/resources.md")
        with_resources = [p["key"] for p in coach.load_roadmap()["patterns"] if p.get("resources")]
        self.assertGreaterEqual(len(with_resources), 18)
```

**Step 2: Run it.** Expected: FAIL, `0 not greater than or equal to 18`.

**Step 3: Add the resources.**

Add `"resources": [...]` to each pattern below in `roadmap.json`, as `{"title": ..., "url": ...}` objects. Edit with a short Python script that loads the JSON, sets the field and dumps it with the file's existing indent, so the formatting stays the same.

```python
R = {
 "arrays-hashing": [("Time complexity of Python's built-in types", "https://docs.python.org/3/builtins/time-complexity.html"),
                    ("collections: Counter, defaultdict, deque", "https://docs.python.org/3/library/collections.html")],
 "two-pointers": [("Competitive Programmer's Handbook, ch. 8", "https://cses.fi/book/book.pdf"),
                  ("Python Tutor", "https://pythontutor.com/visualize.html")],
 "sliding-window": [("Hello Interview: sliding window", "https://www.hellointerview.com/learn/code/sliding-window/fixed-length"),
                    ("Python Tutor", "https://pythontutor.com/visualize.html")],
 "prefix-sums": [("USACO Guide: prefix sums", "https://usaco.guide/silver/prefix-sums")],
 "stack": [("Competitive Programmer's Handbook, ch. 8 (monotonic stack)", "https://cses.fi/book/book.pdf")],
 "binary-search": [("TopCoder: binary search", "https://www.topcoder.com/thrive/articles/Binary%20Search"),
                   ("bisect", "https://docs.python.org/3/library/bisect.html")],
 "linked-list": [("Tech Interview Handbook cheatsheets", "https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/")],
 "trees": [("MIT 6.006 lecture notes 6–7", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/"),
           ("VisuAlgo: BST", "https://visualgo.net/en/bst")],
 "heap": [("heapq, with its implementation notes", "https://docs.python.org/3/library/heapq.html"),
          ("VisuAlgo: heap", "https://visualgo.net/en/heap")],
 "backtracking": [("Erickson, Algorithms, ch. 2", "https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf"),
                  ("Recursion Tree Visualizer", "https://recursion.vercel.app/")],
 "graphs": [("WilliamFiset: graph theory", "https://www.youtube.com/playlist?list=PLDV1Zeh2NRsDGO4--qE8yH72HFL1Km93P"),
            ("VisuAlgo", "https://visualgo.net/en")],
 "tries": [("Tech Interview Handbook cheatsheets", "https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/")],
 "intervals": [("Tech Interview Handbook cheatsheets", "https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/")],
 "greedy": [("Competitive Programmer's Handbook, ch. 6", "https://cses.fi/book/book.pdf")],
 "1d-dp": [("MIT 6.006 lectures 15–16 (SRTBOT)", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/"),
           ("Competitive Programmer's Handbook, ch. 7", "https://cses.fi/book/book.pdf")],
 "2d-dp": [("MIT 6.006 lectures 15–16 (SRTBOT)", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/"),
           ("VisuAlgo: recursion tree vs DAG", "https://visualgo.net/en/recursion")],
 "advanced-graphs": [("CP-Algorithms", "https://cp-algorithms.com/"),
                     ("Red Blob Games: pathfinding", "https://redblobgames.com/pathfinding/a-star/introduction.html")],
 "math-geometry": [("Tech Interview Handbook cheatsheets", "https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/")],
 "bit-manipulation": [("Competitive Programmer's Handbook, ch. 10", "https://cses.fi/book/book.pdf")],
 "ml-coding": [("Karpathy: Neural Networks, Zero to Hero", "https://karpathy.ai/zero-to-hero.html"),
               ("Deep-ML", "https://www.deep-ml.com/")],
}
```

Before running: check the chapter numbers against the book's contents page: greedy is CPH ch. 6, bit manipulation ch. 10. Fix the titles if they differ.

**Step 4: Run the tests and `validate`.** Expected: PASS, `OK`.

**Step 5: Commit**

```bash
git add skills/dsa-coach/assets/roadmap.json tests/test_catalogue.py
git commit -m "Roadmap: two or three vetted resources per pattern"
```

---

### Task 3: `coach.py map`

**Files:**
- Modify: `skills/dsa-coach/scripts/coach.py` (add `map_view`, `render_map`, `cmd_map` after `cmd_next`; a parser entry after `next`'s)
- Modify: `tests/test_coach.py` (add to `CoachTest`)

**Step 1: Write the failing tests**

```python
    def test_map_joins_catalogue_and_progress(self):
        self.attempt("best-time-to-buy-and-sell-stock", "2026-11-01", pattern="sliding-window")
        view = json.loads(self.run_cli("map", "--json", today="2026-11-01").stdout)
        sw = next(p for p in view["patterns"] if p["key"] == "sliding-window")
        self.assertEqual(sw["lists"], {"blind75": {"done": 1, "total": 4}, "nc150": {"done": 1, "total": 6}})
        row = sw["problems"][0]  # Blind 75 first
        self.assertEqual((row["slug"], row["status"], row["due"]), ("best-time-to-buy-and-sell-stock", "practicing", False))
        self.assertEqual(row["url"], "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/")
        self.assertEqual([("blind75" in x["lists"]) for x in sw["problems"]], [True] * 4 + [False] * 2)
        ml = next(p for p in view["patterns"] if p["key"] == "ml-coding")
        self.assertTrue(ml["format"])
        self.assertEqual(ml["problems"], [])
        self.assertIn("next_text", view)

    def test_map_names_the_latest_explainer(self):
        folder = self.root / "concepts" / "stack"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "stack-explainer.html").write_text("<p>stack</p>")
        self.run_cli("artifact", "add", "--concept", "stack", "--title", "Stack", "--file", "concepts/stack/stack-explainer.html")
        view = json.loads(self.run_cli("map", "--json").stdout)
        stack = next(p for p in view["patterns"] if p["key"] == "stack")
        self.assertEqual(stack["explainer"], "concepts/stack/stack-explainer.html")
```

**Step 2: Run them.**

```bash
python3 -m unittest tests.test_coach -k map -v
```

Expected: FAIL; `coach map` exits with "invalid choice: 'map'".

**Step 3: Implement**

```python
SOLVED = ("practicing", "retained", "ready")  # a problem solved unaided at least once


def list_progress(problems: list, name: str) -> dict:
    on = [x for x in problems if name in x["lists"]]
    return {"done": sum(x["status"] in SOLVED for x in on), "total": len(on)}


def map_view(j: dict, roadmap: dict, catalogue: dict) -> dict:
    """The study app's map: every pattern with its status, explainer and problems (Blind 75 first)."""
    explainers = {a["concept"]: a["file"] for a in j["artifacts"] if (a.get("file") or "").endswith(".html")}
    due = {d["problem"] for d in j["due"]["resolves"]}
    status = {r["key"]: r["status"] for r in j["patterns"]}
    patterns = []
    for p in roadmap["patterns"]:
        problems = []
        for c in sorted(catalogue.get(p["key"], []), key=lambda c: "blind75" not in c["lists"]):
            seen = j["problems"].get(c["slug"]) or {}
            problems.append({**c, "url": roadmap["problem_url"].format(slug=c["slug"]),
                             "status": seen.get("status", "not started"), "last_outcome": seen.get("last_outcome"),
                             "next_due": seen.get("next_due"), "due": c["slug"] in due})
        patterns.append({
            "key": p["key"], "name": p["name"], "week": p.get("week"), "tier": p.get("tier"),
            "cues": p.get("cues", []), "invariant": p.get("invariant", ""), "template": p.get("template", ""),
            "resources": p.get("resources", []), "status": status[p["key"]], "format": p["key"] in LONG_FORMATS,
            "explainer": explainers.get(p["key"]), "due": sum(x["due"] for x in problems),
            "lists": {name: list_progress(problems, name) for name in ("blind75", "nc150")},
            "problems": problems,
        })
    nxt = pick_next(j)
    return {"plan": j["plan"], "next": nxt, "next_text": render_next(nxt),
            "next_url": roadmap["problem_url"].format(slug=nxt["problem"]) if nxt.get("problem") else None,
            "patterns": patterns}


def render_map(view: dict) -> str:
    lines = []
    for p in view["patterns"]:
        b, n = p["lists"]["blind75"], p["lists"]["nc150"]
        lists = f" · Blind 75 {b['done']}/{b['total']} · NeetCode 150 {n['done']}/{n['total']}" if b["total"] or n["total"] else ""
        lines.append(f"{p['name']}: {p['status']}{lists}")
    return "\n".join(lines)


def cmd_map(args) -> None:
    root = find_root(args.root)
    view = map_view(compute(load_state(root), parse_date(args.date)), load_roadmap(), load_catalogue())
    print(json.dumps(view, indent=2, ensure_ascii=False) if args.json else render_map(view))
```

Parser, after the `next` subparser:

```python
    s = sub.add_parser("map", help="every pattern with its status, explainer and problems (the study app's map)")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date", help="as of this date (YYYY-MM-DD)")
    s.set_defaults(func=cmd_map)
```

(Copy `--date`'s help text from the `next` subparser if it differs.)

**Step 4: Run the tests.** Expected: both pass. Then `python3 skills/dsa-coach/scripts/coach.py map` prints 22 lines from the real notebook.

**Step 5: Commit**

```bash
git add skills/dsa-coach/scripts/coach.py tests/test_coach.py
git commit -m "coach.py map: patterns with status, explainer and catalogue problems"
```

---

### Task 4: `app/claude_job.py`

**Files:**
- Create: `app/claude_job.py`
- Create: `tests/test_claude_job.py`

**Step 1: Write the failing tests**

```python
"""Tests for app/claude_job.py. Run: python3 -m unittest discover -s tests -v"""
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import claude_job  # noqa: E402


def settle(jobs, key):
    for _ in range(200):
        s = jobs.status(key)
        if s["state"] != "running":
            return s
        time.sleep(0.01)
    raise AssertionError("the job never finished")


def done(code=0, out="", err=""):
    return lambda argv, **kw: subprocess.CompletedProcess(argv, code, out, err)


class JobsTest(unittest.TestCase):
    def test_idle_before_any_job(self):
        self.assertEqual(claude_job.Jobs().status("x"), {"state": "idle", "error": None})

    def test_success(self):
        jobs = claude_job.Jobs(run=done())
        jobs.start("x", ["claude", "-p", "hi"], cwd=".", timeout=5)
        self.assertEqual(settle(jobs, "x"), {"state": "done", "error": None})

    def test_failure_keeps_the_end_of_stderr(self):
        jobs = claude_job.Jobs(run=done(1, err="boom"))
        jobs.start("x", ["claude"], cwd=".", timeout=5)
        self.assertEqual(settle(jobs, "x"), {"state": "error", "error": "boom"})

    def test_missing_binary_and_timeout(self):
        def missing(argv, **kw):
            raise FileNotFoundError(argv[0])

        def slow(argv, **kw):
            raise subprocess.TimeoutExpired(argv, kw["timeout"])

        for run, text in ((missing, "can't find claude"), (slow, "longer than 5 s")):
            jobs = claude_job.Jobs(run=run)
            jobs.start("x", ["claude"], cwd=".", timeout=5)
            self.assertIn(text, settle(jobs, "x")["error"])

    def test_one_job_at_a_time(self):
        gate = threading.Event()

        def blocked(argv, **kw):
            gate.wait(5)
            return subprocess.CompletedProcess(argv, 0, "", "")

        jobs = claude_job.Jobs(run=blocked)
        jobs.start("a", ["claude"], cwd=".", timeout=5)
        with self.assertRaises(claude_job.Busy):
            jobs.start("b", ["claude"], cwd=".", timeout=5)
        gate.set()
        settle(jobs, "a")
        jobs.start("b", ["claude"], cwd=".", timeout=5)  # free again
        self.assertEqual(settle(jobs, "b")["state"], "done")
```

**Step 2: Run them.** `python3 -m unittest tests.test_claude_job -v`. Expected: ERROR, `No module named 'claude_job'`.

**Step 3: Implement `app/claude_job.py`**

```python
"""Runs the coach headless (`claude -p ...`), one job at a time, so a page can start one and check on it."""
from __future__ import annotations

import subprocess
import threading


class Busy(Exception):
    pass


class Jobs:
    def __init__(self, run=subprocess.run):
        self._run = run  # injectable, for tests
        self._lock = threading.Lock()
        self._jobs: dict = {}
        self._running: str | None = None

    def start(self, key: str, argv: list, cwd, timeout: float) -> None:
        with self._lock:
            if self._running:
                raise Busy(f"the coach is busy with {self._running}; try again when it's done")
            self._running = key
            self._jobs[key] = {"state": "running", "error": None}
        threading.Thread(target=self._work, args=(key, argv, cwd, timeout), daemon=True).start()

    def status(self, key: str) -> dict:
        with self._lock:
            return dict(self._jobs.get(key, {"state": "idle", "error": None}))

    def _work(self, key: str, argv: list, cwd, timeout: float) -> None:
        try:
            proc = self._run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            error = None if proc.returncode == 0 else \
                ((proc.stderr or proc.stdout or "").strip()[-500:] or f"{argv[0]} exited with {proc.returncode}")
        except FileNotFoundError:
            error = f"can't find {argv[0]}: set claude_bin in notebook/config.json"
        except subprocess.TimeoutExpired:
            error = f"the coach took longer than {int(timeout)} s and was stopped"
        with self._lock:
            self._jobs[key] = {"state": "error" if error else "done", "error": error}
            self._running = None
```

**Step 4: Run the tests.** Expected: 5 pass.

**Step 5: Commit**

```bash
git add app/claude_job.py tests/test_claude_job.py
git commit -m "claude_job: run the coach headless, one job at a time"
```

---

### Task 5: Server routes for the map and explainers

**Files:**
- Modify: `app/server.py`
- Modify: `tests/test_server.py`

**Step 1: Write the failing tests** (in `ServerTest`; `self.call` already exists)

Check how `self.call` returns status and body before writing these, and adapt the unpacking if it differs.

```python
    def fake_claude(self):
        calls = []

        def run(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.server.coach.jobs = server.claude_job.Jobs(run=run)
        return calls

    def wait_job(self, pattern):
        for _ in range(200):
            status, body = self.call("GET", f"/api/explainer?pattern={pattern}")
            if body["state"] != "running":
                return body
            time.sleep(0.01)
        self.fail("job never finished")

    def test_map(self):
        status, body = self.call("GET", "/api/map")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["patterns"]), 22)

    def test_explainer_runs_the_coach_for_one_pattern(self):
        calls = self.fake_claude()
        status, body = self.call("POST", "/api/explainer", {"pattern": "binary-search"})
        self.assertEqual((status, body["state"]), (200, "running"))
        self.assertEqual(self.wait_job("binary-search")["state"], "done")
        argv = calls[0]
        self.assertEqual(argv[:2], ["claude", "-p"])
        self.assertIn("binary-search", argv[2])
        self.assertIn("artifact add --concept binary-search", argv[2])

    def test_explainer_uses_claude_bin_and_rejects_unknown_patterns(self):
        cfg = json.loads((self.root / "config.json").read_text())
        (self.root / "config.json").write_text(json.dumps({**cfg, "claude_bin": "/opt/claude"}))
        calls = self.fake_claude()
        self.call("POST", "/api/explainer", {"pattern": "stack"})
        self.wait_job("stack")
        self.assertEqual(calls[0][0], "/opt/claude")
        self.assertEqual(self.call("POST", "/api/explainer", {"pattern": "nope"})[0], 400)

    def test_explainer_page_is_sandboxed(self):
        self.assertEqual(self.raw_get("/explainer/stack")[0], 404)
        folder = self.root / "concepts" / "stack"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "stack-explainer.html").write_text("<p>stack</p>")
        subprocess.run([sys.executable, str(COACH), "--root", str(self.root), "artifact", "add", "--concept", "stack",
                        "--title", "Stack", "--file", "concepts/stack/stack-explainer.html"],
                       check=True, capture_output=True, env=self.env)
        status, headers, body = self.raw_get("/explainer/stack")
        self.assertEqual((status, body), (200, b"<p>stack</p>"))
        self.assertIn("sandbox", headers["Content-Security-Policy"])
```

Add a small `raw_get(path)` helper to the test class: a `urllib.request` GET to `http://127.0.0.1:{self.port}{path}` that returns `(status, headers, body)` and catches `HTTPError` for the 404. Don't send the `X-DSA-Coach` header; static pages don't need it.

**Step 2: Run them.** Expected: FAIL (`no route GET /api/map`, no `coach` attribute on the server).

**Step 3: Implement in `app/server.py`**

- `import claude_job` next to `import runner`.
- After `TYPES`:

```python
ROADMAP = json.loads((COACH.parent.parent / "assets" / "roadmap.json").read_text(encoding="utf-8"))
EXPLAINER_TIMEOUT = 300  # seconds: the coach traces real Python before it draws
```

- In `Coach.__init__`: `self.jobs = claude_job.Jobs()`.
- Routes, after `post_run`:

```python
def check_pattern(value) -> dict:
    p = next((p for p in ROADMAP["patterns"] if p["key"] == value), None)
    if p is None:
        raise ApiError(400, f"unknown pattern {value!r}")
    return p


def get_map(coach, q):
    return coach.json("map")


def explainer_prompt(p: dict, root: Path) -> str:
    rel = f"concepts/{p['key']}/{p['key']}-explainer.html"
    return (f"Use the dsa-coach skill. Write the interactive explainer for the pattern {p['name']} ({p['key']}), "
            f"following references/explainers.md. Save it as one self-contained HTML file at {root / rel}. "
            f"Don't publish it. Then register it: python3 skills/dsa-coach/scripts/coach.py --root {root} "
            f"artifact add --concept {p['key']} --title \"{p['name']}, explained\" --file {rel}")


def claude_argv(coach, prompt: str) -> list:
    cfg = json.loads((coach.root / "config.json").read_text(encoding="utf-8"))
    return [cfg.get("claude_bin", "claude"), "-p", prompt, "--permission-mode", "acceptEdits",
            "--allowedTools", "Bash(python3:*),Read,Write,Edit,Glob,Grep"]


def post_explainer(coach, d):
    p = check_pattern(d.get("pattern"))
    key = "explainer:" + p["key"]
    try:
        coach.jobs.start(key, claude_argv(coach, explainer_prompt(p, coach.root)), REPO, EXPLAINER_TIMEOUT)
    except claude_job.Busy as e:
        raise ApiError(409, str(e))
    return coach.jobs.status(key)


def get_explainer(coach, q):
    return coach.jobs.status("explainer:" + check_pattern(q.get("pattern"))["key"])


def explainer_file(coach, key: str) -> Path:
    check_pattern(key)
    rel = next(p["explainer"] for p in coach.json("map")["patterns"] if p["key"] == key)
    path = (coach.root / (rel or "")).resolve()
    if not rel or not path.is_relative_to(coach.root.resolve()) or not path.is_file():
        raise ApiError(404, "no explainer for that pattern yet")
    return path
```

- Add to `ROUTES`: `("GET", "/api/map"): get_map`, `("POST", "/api/explainer"): post_explainer`, `("GET", "/api/explainer"): get_explainer`.
- In the handler, give `send` an optional `headers: dict | None = None` argument and send each one before `end_headers()`. In `handle_any`, before `return self.static(url.path)`:

```python
                    if url.path.startswith("/explainer/"):
                        path = explainer_file(coach, url.path.removeprefix("/explainer/"))
                        # its own origin: the page's scripts run, but can't call this server's API
                        return self.send(200, path.read_bytes(), TYPES[".html"],
                                         {"Content-Security-Policy": "sandbox allow-scripts allow-popups"})
```

- In `make_server`, keep the coach on the server so tests can swap its jobs:

```python
    coach = Coach(root, env)
    handler = make_handler(coach)
    ...
            srv = ThreadingHTTPServer(("127.0.0.1", p), handler)
            srv.coach = coach
            return srv
```

**Step 4: Run all the server tests.** Expected: the new tests and every existing one pass.

**Step 5: Commit**

```bash
git add app/server.py tests/test_server.py
git commit -m "Server: the map, and explainers written by the coach headless"
```

---

### Task 6: The Map and Learn views

**Files:**
- Create: `app/static/nav.js`
- Modify: `app/static/index.html`, `app/static/app.css`
- Create: `tests/frontend/nav.test.cjs`

**Step 1: Write the failing tests** (`tests/frontend/nav.test.cjs`)

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function load() {
  const c = vm.createContext({document: {addEventListener() {}}, window: {addEventListener() {}}, location: {hash: ''}});
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../app/static/nav.js'), 'utf8'), c);
  return (code) => vm.runInContext(code, c);
}

test('routes default to the map', () => {
  const run = load();
  assert.deepEqual({...run(`route('')`)}, {view: 'map', key: ''});
  assert.deepEqual({...run(`route('#/learn/stack')`)}, {view: 'learn', key: 'stack'});
  assert.deepEqual({...run(`route('#/solve')`)}, {view: 'solve', key: ''});
  assert.deepEqual({...run(`route('#/nowhere')`)}, {view: 'map', key: ''});
});

test('weeks come in order and keep roadmap order inside a week', () => {
  const run = load();
  const weeks = run(`byWeek([{key:'a',week:2},{key:'b',week:1},{key:'c',week:2}])`);
  assert.deepEqual(JSON.parse(JSON.stringify(weeks)), [[1, [{key: 'b', week: 1}]], [2, [{key: 'a', week: 2}, {key: 'c', week: 2}]]]);
});

test('list progress reads as done/total, and nothing for an empty list', () => {
  const run = load();
  assert.equal(run(`listsText({blind75:{done:1,total:4}, nc150:{done:2,total:6}})`), 'Blind 75 1/4 · NeetCode 150 2/6');
  assert.equal(run(`listsText({blind75:{done:0,total:0}, nc150:{done:0,total:3}})`), 'NeetCode 150 0/3');
  assert.equal(run(`statusLabel('practicing')`), 'Practising');
});
```

**Step 2: Run them.** `node --test tests/frontend/nav.test.cjs`. Expected: FAIL, `ENOENT` on nav.js.

**Step 3: Write `app/static/nav.js`**

```js
"use strict";
// The Map and Learn views. Loaded after app.js; uses its $, elem, button, api, fail, state and editor.

const STATUS_LABEL = {"not started": "Not started", exploring: "Exploring", learning: "Learning",
  practicing: "Practising", retained: "Retained", ready: "Ready"};
const FOUNDATIONS = ["Python for interviews", "Complexity", "How to approach a problem"];  // written for testers
const POLL_MS = 3000;
let mapData = null;
let pollTimer = null;

// --- pure helpers -------------------------------------------------------------
function route(hash) {  // "#/map" (the default), "#/learn/<key>" or "#/solve"
  const [, view = "map", key = ""] = String(hash || "").split("/");
  return ["map", "learn", "solve"].includes(view) ? {view, key} : {view: "map", key: ""};
}
const statusLabel = (s) => STATUS_LABEL[s] || s;
function listsText(lists) {
  return [["Blind 75", lists.blind75], ["NeetCode 150", lists.nc150]]
    .filter(([, l]) => l.total).map(([name, l]) => `${name} ${l.done}/${l.total}`).join(" · ");
}
function byWeek(patterns) {
  const weeks = new Map();
  for (const p of patterns) {
    if (!weeks.has(p.week)) weeks.set(p.week, []);
    weeks.get(p.week).push(p);
  }
  return [...weeks.entries()].sort((a, b) => a[0] - b[0]);
}

// --- small DOM helpers ----------------------------------------------------------
const withClass = (el, className) => Object.assign(el, {className});
function link(text, href, newTab = false) {
  const a = Object.assign(elem("a", text), {href});
  if (newTab) Object.assign(a, {target: "_blank", rel: "noopener"});
  return a;
}
function list(items) {
  const ul = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    li.append(item);
    ul.append(li);
  }
  return ul;
}

// --- routing --------------------------------------------------------------------
async function show() {
  const {view, key} = route(location.hash);
  document.body.dataset.view = view;
  clearTimeout(pollTimer);
  if (view === "solve") {
    if (editor) editor.refresh();  // CodeMirror measures wrong while hidden
    return;
  }
  try {
    mapData = await api("GET", "/api/map");
  } catch (e) {
    return fail(e);
  }
  if (view === "map") renderMap(); else renderLearn(key);
}

// --- the map ----------------------------------------------------------------------
function renderMap() {
  const strip = withClass(document.createElement("section"), "next-strip");
  strip.append(withClass(elem("p", "Next up"), "eyebrow"), elem("p", mapData.next_text));
  if (mapData.next_url) strip.append(link("Open on LeetCode", mapData.next_url, true));
  if (state?.live) strip.append(link(`Resume ${state.live.problem}`, "#/solve"));
  const weeks = withClass(document.createElement("div"), "weeks");
  weeks.append(week("Foundations", FOUNDATIONS.map(stub)));
  for (const [n, patterns] of byWeek(mapData.patterns)) weeks.append(week(`Week ${n}`, patterns.map(node)));
  $("map").replaceChildren(strip, weeks);
}
function week(title, nodes) {
  const col = withClass(document.createElement("section"), "week");
  col.append(withClass(elem("h2", title), "eyebrow"), ...nodes);
  return col;
}
function stub(name) {
  const d = withClass(document.createElement("div"), "node stub");
  d.append(elem("b", name), withClass(elem("span", "coming later"), "meta"));
  return d;
}
function node(p) {
  const a = withClass(link("", `#/learn/${p.key}`), `node s-${p.status.replace(" ", "-")}`);
  a.append(elem("b", p.name), withClass(elem("span", statusLabel(p.status)), "status"),
    withClass(elem("span", p.format ? "practised with the coach in chat" : listsText(p.lists)), "meta"));
  if (p.due) a.append(withClass(elem("span", `${p.due} due`), "due"));
  return a;
}

// --- a pattern's Learn page ---------------------------------------------------------
function renderLearn(key) {
  const p = mapData.patterns.find((x) => x.key === key);
  if (!p) { location.hash = "#/map"; return; }
  const page = withClass(document.createElement("article"), "learn");
  page.append(link("← Map", "#/map"), withClass(elem("p", `Week ${p.week} · ${statusLabel(p.status)}`), "eyebrow"),
    elem("h1", p.name), elem("h2", "Cues"), list(p.cues), elem("h2", "Invariant"), elem("p", p.invariant),
    elem("h2", "Template"), elem("pre", p.template), explainerBlock(p));
  if (p.resources.length) page.append(elem("h2", "Read"), list(p.resources.map((r) => link(r.title, r.url, true))));
  if (p.problems.length) page.append(elem("h2", "Problems"), problemTable(p.problems));
  $("learn").replaceChildren(page);
}

function problemTable(problems) {
  const t = withClass(document.createElement("table"), "problems");
  t.innerHTML = "<tr><th>Problem</th><th>Difficulty</th><th>Status</th><th>Next re-solve</th></tr>";
  for (const x of problems) {
    const tr = t.insertRow();
    const name = tr.insertCell();
    name.append(link(x.title, x.url, true));
    if (x.lists.includes("blind75")) name.append(withClass(elem("span", "Blind 75"), "tag"));
    tr.insertCell().textContent = x.difficulty;
    tr.insertCell().textContent = statusLabel(x.status) + (x.last_outcome ? ` (last: ${x.last_outcome})` : "");
    tr.insertCell().textContent = x.due ? "due now" : x.next_due || "";
  }
  return t;
}

// The explainer: a link when there is one; otherwise the coach writes it, and the page checks on the job.
function explainerBlock(p) {
  const box = withClass(document.createElement("section"), "explainer");
  if (p.explainer) {
    box.append(withClass(link("Read the explainer", `/explainer/${p.key}`, true), "button primary"));
  } else if (!p.format) {
    offerExplainer(p.key, box);
    checkExplainer(p.key, box);  // a job started earlier may still be running
  }
  return box;
}
function offerExplainer(key, box, note = "No explainer yet. The coach writes one from real Python traces, with a prediction to make at each step.") {
  const write = withClass(button("Write the explainer", () => writeExplainer(key, box)), "primary");
  box.replaceChildren(withClass(elem("p", note), "hint"), write);
}
async function writeExplainer(key, box) {
  await api("POST", "/api/explainer", {pattern: key});
  await checkExplainer(key, box);
}
async function checkExplainer(key, box) {
  let s;
  try {
    s = await api("GET", "/api/explainer?pattern=" + encodeURIComponent(key));
  } catch (e) {
    return fail(e);
  }
  if (route(location.hash).key !== key) return;  // he left the page
  if (s.state === "running") {
    box.replaceChildren(withClass(elem("p", "The coach is writing it. This usually takes one to three minutes."), "hint"));
    pollTimer = setTimeout(() => checkExplainer(key, box), POLL_MS);
  } else if (s.state === "error") {
    offerExplainer(key, box, s.error);
  } else if (s.state === "done") {
    mapData = await api("GET", "/api/map");
    if (mapData.patterns.find((x) => x.key === key)?.explainer) renderLearn(key);
    else offerExplainer(key, box, "The coach finished but didn't register an explainer. Try again, or ask it in the chat.");
  }
}

window.addEventListener("hashchange", show);
document.addEventListener("DOMContentLoaded", show);
```

**Step 4: Wire it into `index.html`**
- In `#bar`, before `#problem`: `<a id="home" href="#/map">Map</a>`.
- After `<main id="solve">…</main>`: `<main id="map" hidden></main>` and `<main id="learn" hidden></main>`. These are shown by view, never by the `hidden` attribute, so remove `hidden` from both and let the CSS below decide.
- After the `app.js` script tag: `<script src="/static/nav.js"></script>`.

**Step 5: Styles in `app.css`.** Reuse the existing tokens; no new colours.

```css
/* --- views: body[data-view] is set by nav.js --- */
body:not([data-view=solve]) #start, body:not([data-view=solve]) #solve,
body:not([data-view=solve]) #progress, body:not([data-view=solve]) #actions { display: none !important; }
body:not([data-view=map]) #map, body:not([data-view=learn]) #learn { display: none !important; }
#home { color: var(--muted); text-decoration: none; font-weight: 600; }
#home:hover { color: var(--fg); }

#map, #learn { flex: 1; overflow: auto; padding: 24px; }
.next-strip { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 16px; max-width: 960px; margin-bottom: 24px; }
.next-strip p { margin: 0; }
.weeks { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(190px, 1fr); gap: 16px; overflow-x: auto; padding-bottom: 12px; }
.week { display: flex; flex-direction: column; gap: 8px; }
.node { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px;
        background: var(--bg); color: var(--fg); text-decoration: none; transition: border-color .15s var(--ease); }
a.node:hover { border-color: var(--accent); }
.node .status, .node .meta { font-size: 12px; color: var(--muted); }
.node .due { font-size: 12px; color: var(--nudge); font-weight: 600; }
.node.stub { border-style: dashed; color: var(--muted); }
.node.s-learning .status, .node.s-exploring .status { color: var(--nudge); }
.node.s-practicing .status, .node.s-retained .status, .node.s-ready .status { color: var(--ok); }

.learn { max-width: 760px; }
.learn h1 { font-size: 26px; margin: 4px 0 12px; }
.learn h2 { font-size: 15px; margin: 22px 0 6px; }
.learn pre { background: var(--chrome); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; }
.learn .explainer { margin: 24px 0; padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: var(--chrome); }
a.button { display: inline-block; padding: 7px 14px; border-radius: 6px; text-decoration: none; }
a.button.primary { background: var(--accent); color: var(--on-accent); font-weight: 600; }
table.problems td, table.problems th { padding: 7px 6px; border-bottom: 1px solid var(--line); }
table.problems .tag { margin-left: 8px; font-size: 11px; font-weight: 600; color: var(--accent); }
@media (max-width: 860px) {
  #map, #learn { padding: 16px; }
  .weeks { grid-auto-flow: row; grid-auto-columns: auto; }
}
```

**Step 6: Run the tests and check the script loads.**

```bash
node --check app/static/nav.js
node --test tests/frontend/
```

Expected: 3 new tests and the 21 existing ones pass.

**Step 7: Commit**

```bash
git add app/static/nav.js app/static/index.html app/static/app.css tests/frontend/nav.test.cjs
git commit -m "Study app: Map and Learn views, with the Solve view one link away"
```

---

### Task 7: Browser check

**Files:**
- Create: `tests/browser/fake_claude.py`, `tests/browser/check_map.py`. Run them by hand; `unittest` discovery skips them, since neither file name starts with `test_`.

**Step 1: `tests/browser/fake_claude.py`** stands in for `claude -p`. It writes the explainer named in the prompt and registers it.

```python
"""Stands in for `claude -p` in the browser check: writes the explainer the prompt asks for and registers it."""
import re
import subprocess
import sys
from pathlib import Path

prompt = sys.argv[2]
key = re.search(r"\(([a-z0-9-]+)\)", prompt).group(1)
root = Path(re.search(r"--root (\S+)", prompt).group(1))
rel = f"concepts/{key}/{key}-explainer.html"
(root / rel).parent.mkdir(parents=True, exist_ok=True)
(root / rel).write_text(f"<h1>{key}, explained</h1>", encoding="utf-8")
coach = Path(__file__).resolve().parents[2] / "skills/dsa-coach/scripts/coach.py"
subprocess.run([sys.executable, str(coach), "--root", str(root), "artifact", "add", "--concept", key,
                "--title", key, "--file", rel], check=True)
```

**Step 2: `tests/browser/check_map.py`** does the following with Playwright:
1. Copies `notebook/` to a temp folder and sets `claude_bin` in its config to `[sys.executable, fake_claude.py]`. The binary is one string, so make `fake_claude.py` executable (`chmod +x`, with a `#!/usr/bin/env python3` line) and point `claude_bin` at it.
2. Starts `app/server.py --root <tmp> --port 0 --no-browser` (read the port from its first line), or calls `server.make_server` in a thread.
3. Opens `/` and checks the map shows 22 pattern nodes plus 3 Foundations stubs.
4. Clicks Binary Search, then checks the problems table lists Blind 75 rows first and each title links to `leetcode.com`.
5. Clicks **Write the explainer**, waits for **Read the explainer**, and opens it: the page holds "binary-search, explained".
6. Opens `#/solve`, checks the Solve view shows, and clicks **Map** to return.
7. Takes screenshots of the map and a Learn page at 1440×900 in light and dark, and at 390 px wide. Checks there's no horizontal page scroll at 390 px (the weeks strip scrolls on its own).
8. Collects page errors; there must be none.

**Step 3: Run it.**

```bash
python3 tests/browser/check_map.py
```

Expected: every check passes and the screenshots look right. Fix anything that doesn't before moving on.

**Step 4: Commit**

```bash
git add tests/browser
git commit -m "Browser check for the Map and Learn views"
```

---

### Task 8: Docs, version, package

**Step 1:** In `docs/CHANGELOG.md`, add a `## 0.6.0 · <date>` entry (what changed and why, in the file's existing style):
- the map;
- Learn pages;
- the catalogue (NeetCode 150 with Blind 75 tagged, plus prefix-sums canonicals and Combination Sum IV);
- `coach.py map`;
- explainers written through `claude -p` (`claude_bin` in `config.json`);
- the Solve view now one link away.

**Step 2:** Bump `metadata.version` in `skills/dsa-coach/SKILL.md` and `SKILL_VERSION` in `coach.py` to `0.6.0`. If SKILL.md lists `coach.py` commands, add `map` with one line.

**Step 3:** In `ARCHITECTURE.md`, add the Map/Learn views, `claude_job.py` and `problems.json` where the app's parts are listed. Change the "2c. Course layer" row to say the map and Learn pages shipped in 0.6.0, and that intake and placement come with testers.

**Step 4:**

```bash
python3 -m unittest discover -s tests
node --test tests/frontend/
python3 skills/dsa-coach/scripts/coach.py validate
python3 skills/dsa-coach/scripts/coach.py package
```

All four must pass.

**Step 5: Commit**

```bash
git add docs/CHANGELOG.md skills/dsa-coach/SKILL.md skills/dsa-coach/scripts/coach.py ARCHITECTURE.md dist
git commit -m "Release 0.6.0: the Map and Learn pages"
```

(Check `git status` first: only add `dist/` if `package` writes there and it is tracked.)

---

## Milestone B: the coach beside LeetCode (outline; plan it in detail after A ships)

1. **Server: extension origin.** Accept requests whose `Origin` is `chrome-extension://<extension_id>` from `config.json` (CORS preflight included); keep the `X-DSA-Coach` check. Test both allowed and refused origins.
2. **Server: `POST /api/coach`.** Runs `claude_job` with the live solve (`solve show --json`), the current code and the question; 90 s timeout. It returns the job status, and `GET /api/coach` polls it. The coach records hint rungs itself through `coach.py solve hint`.
3. **Server: `POST /api/submission`.** Takes `{slug, code, verdict, failing_case?}`. It writes the code to the live attempt file (session-checked, as today's saves are) and appends a failing case to the attempt's `LEETCODE_CASES` list.
4. **Shared stage UI.** Move the stage panel code (stage forms, notes, timer) out of `app.js` into `stages.js`, which both the app and the panel load. Behaviour is unchanged and the existing tests must still pass.
5. **Extension skeleton.**
   - `extension/manifest.json`: MV3, `sidePanel`, host permission `https://leetcode.com/problems/*`.
   - `panel.html` and `panel.js`: Start with a confidence pick, then the stages, notes, timer and Ask coach, talking to `http://127.0.0.1:8765`.
   - `coach.py package` copies `stages.js` into it.
6. **`content.js` and a main-world script.** They read the slug (URL), the code (LeetCode's editor model, on Run or Submit) and the submission result LeetCode's page already receives (status, failing input, output, expected output). Parsing lives in pure functions with node tests built on saved sample responses. Nothing is sent to LeetCode.
7. **Map links.** When `extension_id` is set, the Learn page's problem links say "Solve on LeetCode with the coach".
8. **By hand on real LeetCode:** start, stages, Ask coach, a wrong Submit (the failing case is captured), Accepted then the look-back, an unreadable editor (paste fallback), and the server stopped (the panel's message).
