# The plan card

The plan card is how he learns to plan a program in his head: he writes it before any code or animation, and the scaffold fades as his accuracy rises. Experts plan by recognizing a structure, stating what stays true, and simulating partial designs in their head. The card makes each of those steps explicit until he can do them silently.

The template lives at `assets/templates/plan-card.md` and is copied into `notebook/problems/<slug>/notes.md` the first time a problem is logged.

## Template

```text
Problem:
Pattern + cue:         (which words in the problem pointed here)
State (one sentence):  e.g. "window = s[l..r], the shortest valid window ending at r"
Invariant:             what is true every time the loop condition is checked
  diagram:             a[..lo) < target | a[lo..hi) unknown | a[hi..] >= target
Initialization:        slide the boundaries back to the start: what makes the invariant true at first?
Loop guard:            slide them forward: when is the unknown part empty?
Body:                  how one step makes progress and restores the invariant
Termination measure:   a number that shrinks each step, e.g. hi - lo, or n - r
Complexity:            one-line argument, e.g. "l and r each move forward at most n times"
Edge cases:            empty, one element, duplicates, negatives, no answer
Hand trace:            one example, a row per iteration, only the variables that change
```

## Deriving code from the invariant (Cornell CS2110 style)

1. Sketch the invariant as segments of the array or string.
2. Name one variable per boundary.
3. Write the invariant as a comment above the loop.
4. Slide the boundaries back to the start to get the initialization.
5. Slide them forward until the unknown segment is empty to get the loop guard.
6. Write a body that makes progress and restores the invariant.

Example for binary search on a sorted array (first index with `a[i] >= t`):

```text
invariant: a[0..lo) < t  and  a[hi..n) >= t     unknown: a[lo..hi)
init:      lo = 0, hi = n                       (everything unknown)
guard:     while lo < hi                         (stop when unknown is empty)
body:      mid = (lo + hi) // 2
           if a[mid] < t: lo = mid + 1          (a[..mid] < t joins the left part)
           else:          hi = mid              (a[mid..] >= t joins the right part)
measure:   hi - lo shrinks every step
answer:    lo
```

## The fading ladder

Track the level per pattern family in the problem notes. Move up after about 90% accuracy on three consecutive probes, and drop back a level after an error. These thresholds are design choices, not tested values.

| Level | What he writes | Probe |
|---|---|---|
| 1 | Full state table, a row per iteration | You compare the table with the executed trace |
| 2 | Only the changing variables plus the invariant | "What are l, r and best after iteration 3?" |
| 3 | Mental trace with checkpoints | You ask for values at 2–3 checkpoints only |
| 4 | Invariant and correctness argument only | "Why can l never move left?" |

Complete traces matter: in one study, complete line-by-line traces were 92% correct against 9% for incomplete ones. A short lesson on keeping an explicit memory table also raised tracing accuracy (d = 0.72). Tracing doesn't automatically improve code writing, though, so the card always ends in code.

## Common invariants worth knowing by heart

| Pattern | Invariant |
|---|---|
| Hash scan (two sum) | The map holds exactly the elements to the left of i |
| Two pointers, opposite ends | No pair outside [l..r] can beat the best found so far |
| Sliding window | s[l..r] is the best valid window ending at r; the counts describe exactly s[l..r] |
| Binary search | The answer is in [lo, hi), and the predicate is monotone |
| Monotonic stack | The stack is monotone, and every popped index has found its answer |
| Heap top-k | The heap holds the k best seen so far; its root is the worst of them |
| BFS | Nodes leave the queue in order of distance; visited nodes are never re-entered |
| Dijkstra | A node popped with the smallest tentative distance is final (non-negative weights) |
| Backtracking | The path is a valid partial solution; every choice is undone after recursing |
| Dynamic programming | Each cell holds the optimum of its subproblem and reads only cells already filled |
| Union-find | Two nodes have the same root exactly when they are connected |
