# Interactive explainers

Build an explainer when a pattern is new to him, when a question or a prediction error shows a misconception, or when he asks to see something. The reference example is the "Sliding Window, Derived" page saved in `notebook/concepts/sliding-window/`.

## What the evidence says, in one paragraph

How the learner uses a visualization matters more than what it shows: studies that varied engagement found effects far more often (10 of 12) than studies that varied the graphics (3 of 9), and passive viewing does about as well as no visualization. Animation adds little over static frames (d ≈ 0.2–0.4) and can make material feel easier while hurting transfer. What reliably helps: stepping under his control, small segments, highlighting what changed, naming parts before the run, predicting at decision points, a curated input, and comparing two algorithms on the same state.

## The seven beats

1. **Pre-training card.** Names of the parts (pointers, state, invariant). This doubles as the plan card.
2. **Stepper on a curated input.** One step per meaningful event (loop iteration, call, relaxation, sift). Highlight the deltas. Show the Python with the current line and live per-line run counts.
3. **Predictions at decision points only.** "Expand or shrink?", "Which pointer moves?", "Is this branch pruned?" Put a prompt where a wrong invariant would break, not on every step. Always show the gap between his prediction and the real result.
4. **Permanent history.** A trace table beside the stepper (one row per iteration, only the variables that change), so nothing he needs is transient.
5. **Faded stretch.** Some state cells show "?" for him to fill before he can step on.
6. **Edge case or comparison.** An edge-case preset, or brute force and the optimized algorithm in lockstep on the same input (the (i, j) grid is ideal for this).
7. **Check with the visual hidden.** Reproduce the state after step k, state the invariant, or trace a fresh input on paper. Then add a `trace` card so the check repeats days later.

Completion must depend on answers, not clicks: in one e-textbook, a quarter of slideshows were clicked through at under a second per slide.

## Interface rules

- Step, Back, Play, Reset and End controls; Step is the main one. Arrow keys step.
- Discrete frames. Tween only movements that are the concept (a pointer advancing, a swap, an edge relaxing). Respect `prefers-reduced-motion`.
- Colour means the same state in every view. Use sequential colour scales for distance or depth.
- Show both tree and array for heaps and union-find.
- Narration in an `aria-live` region, readable at phone width, light and dark themes.
- For new patterns use fine steps and more checkpoints. For familiar ones, open on the whole-run view (for example per-line counts at n = 8, 16, 32, 64) with fewer prompts.

## Visual idioms by pattern

| Pattern | Primary visual | Invariant on screen | Prediction at the decision point |
|---|---|---|---|
| Hashing (two-sum family) | Index tape plus a live hash-map table; the (i, j) grid where one lookup answers a whole column | The map holds exactly `nums[..j)` | "Is target − x already in the map?" |
| Two pointers, opposite ends | Tape with ruled-out segments; the upper-triangle (i, j) grid where each move greys a row or column | No unexamined pair outside [l..r] beats best | "Which pointer moves, and which pairs does that rule out?" |
| Sliding window | Window bracket, a counts panel, a validity light; the (i, j) grid as a staircase of at most 2n moves | s[l..r] valid; l is the smallest valid start for r | "Expand or shrink? What is the new l?" |
| Binary search (index or answer) | lo/mid/hi with segments and a shrinking unknown part; for answer spaces, a number line coloured by feasible(x) | Answer in [lo, hi); predicate monotone | "Which half survives? New lo and hi?" |
| Monotonic stack or deque | Bar chart with the stack as a staircase; each pop draws an arrow to the bar that resolved it | Stack monotone; every popped index has its answer | "How many pops when this bar arrives?" |
| Linked lists | Box-and-pointer nodes; the old edge stays dashed until replaced; unreachable nodes grey out | prev heads the reversed part, curr the rest | "After `curr.next = prev`, can we still reach node 3?" |
| Heap and top-k | Tree and 0-based array together, sift path animated in both | `a[k] <= a[2k+1]` and `a[k] <= a[2k+2]` | "Where does the new item stop sifting?" |
| Graph BFS and Dijkstra | Reached, frontier and unreached colours; came-from arrows; distance labels; a queue or heap panel including stale entries | Settled distances are final | "Which node settles next? Does this edge relax?" |
| Backtracking | Decision tree drawn depth-first; pruned branches as stubs with the reason; a path stack | The path is a valid partial solution | "Will this branch be pruned?" |
| Dynamic programming | Table with arrows into each written cell and the recurrence with numbers substituted; a memo tree collapsing into a DAG | Each cell is the optimum of its subproblem | "Which cells does this cell read, and what is its value?" |
| Union-find | Forest and parent array side by side; path compression re-points the find path | Same root means same component | "After `find(0)`, what is `parent[0]`?" |

Build the (i, j) state-space grid first and reuse it: it shows brute force as every cell, hashing as answering a column at once, two pointers as row and column eliminations, the sliding window as a monotone staircase, and 2-D or interval DP as the table itself.

## Trace-first build pipeline

No frame comes from imagination. Splitting execution from rendering (the LLM writes a Python tracker that emits a JSON trace, and a fixed renderer draws it) raised LLM visualization success from 82.5% to 99.8% on 200 LeetCode tasks.

1. **Reference.** Write `reference.py` with the real algorithm. Record a step at each meaningful event: a small full snapshot of the state, the operation that produced it (compare, push, move-left, record), the line number, a narration string, and an optional prediction prompt with its answer.
2. **Oracle check.** Compare the reference with a brute-force solution on small generated inputs: empty, single element, duplicates, negatives, no answer.
3. **Invariant checks.** Assert the invariant at every step (window valid, stack monotone, heap property, each DP cell equal to its brute-force value). Every visual claim is an assertion.
4. **Renderer.** Views are pure functions of the step record. Precompute traces for 3–5 curated inputs and embed them as JSON in the page.
5. **Your-own-input mode (optional).** A JavaScript port may run live inputs, but it must be checked against the Python trace on every step's values. Line counts alone are a weak check: `max(best, r - l)` and `max(best, r - l + 1)` run every line the same number of times and give different answers.
6. **Page check.** If a browser is available, step through the built page and compare the displayed state with the trace, then look at it once at phone width.

When you can't execute code, generate the page from a JavaScript step generator that checks its own invariants and shows a visible "invariant violated at step k" badge, and say the trace wasn't verified against Python.

## Output and saving

- In Claude, publish the page as an artifact when possible: a single HTML file, inline CSS and JS, scripts only from the allowed CDNs. Keep the URL.
- Elsewhere (ChatGPT, Codex), write a single self-contained HTML file he can open in a browser.
- Always save the file to `notebook/concepts/<slug>/` and run:

```bash
coach.py artifact add --concept <slug> --title "<page title>" --file <path> [--url <published url>] [--version 1]
```

- When a follow-up question changes a page, bump the version, add a line to the concept's changelog in `concepts/<slug>/notes.md`, and register the new version.

## Later (build step 2)

A reusable component library (grid, tape, tree, graph, trace table, code panel with live counts, player controls, prediction prompts) will live in `assets/` so pages are assembled from tested parts. Until then, reuse the structure of the sliding-window page.
