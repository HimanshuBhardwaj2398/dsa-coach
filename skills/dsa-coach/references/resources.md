# Resources: one crisp source per building block

Rules: link at most three per turn; say what to read or watch and why; prefer the official Python docs for anything about Python behaviour; pair any C++ or Java source with a Python one. Problem links are `https://leetcode.com/problems/<slug>/` (slugs in assets/roadmap.json).

## By building block

| Building block | Read first | Visualize | Practice |
|---|---|---|---|
| Complexity and amortized cost | [Competitive Programmer's Handbook (CPH)](https://cses.fi/book/book.pdf) ch. 2; [Python time complexity of built-in types](https://docs.python.org/3/builtins/time-complexity.html) | Per-line counts across n from your own traces | State time and space on every problem |
| Two pointers, monotonic stack and queue | [CPH](https://cses.fi/book/book.pdf) ch. 8: six pages, one amortized argument for all three | [Python Tutor](https://pythontutor.com/visualize.html) | NeetCode 150 Two Pointers (5) and Stack (7) |
| Sliding window | [Hello Interview: sliding window](https://www.hellointerview.com/learn/code/sliding-window/fixed-length) (fixed vs variable windows; partly paid) | Python Tutor; the (i, j) grid page in notebook/concepts/sliding-window | NeetCode 150 Sliding Window (6) |
| Prefix sums | [USACO Guide: prefix sums](https://usaco.guide/silver/prefix-sums) (has Python code) | Python Tutor | Subarray Sum Equals K, Range Sum Query |
| Binary search, including on the answer | [TopCoder: binary search](https://www.topcoder.com/thrive/articles/Binary%20Search) (about 20 minutes) plus [`bisect`](https://docs.python.org/3/library/bisect.html) | Python Tutor | NeetCode 150 Binary Search (7) plus Split Array Largest Sum |
| Linked lists and trees | [Tech Interview Handbook cheatsheets](https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/); [MIT 6.006](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/lecture-notes/) lectures 6–7 | Python Tutor; [VisuAlgo BST](https://visualgo.net/en/bst) | NeetCode 150 Linked List (11) and Trees (15) |
| Heaps and top-k | [`heapq`](https://docs.python.org/3/library/heapq.html) including its implementation notes; MIT 6.006 lecture 8 | [VisuAlgo heap](https://visualgo.net/en/heap) | NeetCode 150 Heap (7) |
| Graphs: BFS, DFS, topological sort, Dijkstra, union-find | [WilliamFiset graph theory playlist](https://www.youtube.com/playlist?list=PLDV1Zeh2NRsDGO4--qE8yH72HFL1Km93P), then [CP-Algorithms](https://cp-algorithms.com/) for exact code | [VisuAlgo](https://visualgo.net/en); [Red Blob Games: pathfinding](https://redblobgames.com/pathfinding/a-star/introduction.html) | NeetCode 150 Graphs (13) and Advanced Graphs (6) |
| Recursion and backtracking | [Erickson, *Algorithms*](https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf) ch. 2, "The General Pattern" | [Recursion Tree Visualizer](https://recursion.vercel.app/) | NeetCode 150 Backtracking (9) |
| Dynamic programming | MIT 6.006 lectures 15–16 (SRTBOT), then CPH ch. 7 | [VisuAlgo: recursion tree vs DAG](https://visualgo.net/en/recursion) | NeetCode 150 1-D DP (12) and 2-D DP (11) |
| Loop invariants | [Cornell CS2110 lecture 4](https://www.cs.cornell.edu/courses/cs2110/2026fa/lectures/lec04) | Your own plan cards | Invariants for binary search, Sort Colors and Kadane's algorithm |
| ML coding from scratch | [Karpathy, Neural Networks: Zero to Hero](https://karpathy.ai/zero-to-hero.html) | None needed | [Deep-ML](https://www.deep-ml.com/); [Tensor Puzzles](https://github.com/srush/Tensor-Puzzles) |

## Python references for interviews

- [Time complexity of built-in types](https://docs.python.org/3/builtins/time-complexity.html): list, dict, set, deque costs.
- [`heapq`](https://docs.python.org/3/library/heapq.html): min-heap only; use `(priority, counter, item)` tuples for tie-breaking and lazy deletion. Max-heap functions arrived only in Python 3.14, so negate keys by default.
- [`bisect`](https://docs.python.org/3/library/bisect.html): states its partition invariant outright; `bisect_left` is "first index with a[i] >= x".
- [`collections`](https://docs.python.org/3/library/collections.html): `Counter` (missing keys read as 0; `<=` is multiset inclusion from 3.10), `deque` (O(1) at both ends), `defaultdict`.

## Problem lists

| List | Use it for |
|---|---|
| [NeetCode 150](https://neetcode.io/practice) | The default spine: 18 pattern sections with solution videos |
| [Grind 75](https://www.techinterviewhandbook.org/grind75) | Fixed deadlines: orders 169 ranked problems around the hours you have |
| [NeetCode 250](https://neetcode.io/practice/practice/neetcode250) | Weak sections only |
| [LeetCode Patterns](https://seanprashad.com/leetcode-patterns/) | "More problems on pattern X" lookups |

## Books and courses worth the time

- [Competitive Programmer's Handbook](https://cses.fi/book/book.pdf) and [Erickson's *Algorithms*](https://jeffe.cs.illinois.edu/teaching/algorithms/) give more depth per hour than CLRS.
- [Hello Algo](https://www.hello-algo.com/en/): animated chapters with Python code, good for a first pass.
- CLRS (*Introduction to Algorithms*): §2.1 loop invariants, §2.2 line-by-line cost analysis, and the amortized analysis chapter (16 in the 4th edition, 17 in the 3rd).

## Interview format and grading

- [Tech Interview Handbook: coding signals](https://www.techinterviewhandbook.org/coding-signals/): the rubric the mock mode uses.
- [Tech Interview Handbook: study plan](https://www.techinterviewhandbook.org/coding-interview-study-plan/): pacing and pattern priorities.
- [Hello Interview: Meta's AI-enabled coding round](https://www.hellointerview.com/blog/meta-ai-enabled-coding): what AI-assisted rounds look like.
- [Canva: AI in our interviews](https://canva.dev/blog/engineering/yes-you-can-use-ai-in-our-interviews).

## AI-engineer rounds beyond DSA

- [Karpathy, Zero to Hero](https://karpathy.ai/zero-to-hero.html) (the micrograd lecture alone builds backprop from scratch) and [Tensor Puzzles](https://github.com/srush/Tensor-Puzzles) for NumPy and PyTorch fluency.
- [Deep-ML](https://www.deep-ml.com/) for ML coding problems in an interview format.
- Karpathy's nanochat replaces the now-deprecated [nanoGPT](https://github.com/karpathy/nanoGPT) as the end-to-end reference.
- [Chip Huyen, *AI Engineering*](https://github.com/chiphuyen/aie-book) for the eval-heavy RAG and agent take-homes.
