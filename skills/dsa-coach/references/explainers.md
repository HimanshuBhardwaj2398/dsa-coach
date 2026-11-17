# Interactive explainers

Every pattern has an explainer saved before he reaches it, so learn mode opens a finished page instead of building one in the session. The algorithm patterns are built from specs (below); Arrays & Hashing, Sliding Window, Stack and Binary Search are hand-built pages of the same depth. Build or revise one when a pattern has none, when a question or a prediction error shows a misconception, or when he asks to see something. When he asks for more examples or more animation of a pattern he has already seen, offer one problem to attempt first, and build more only for what the attempt shows he's missing. More watching feels like progress but adds little (an illusion of competence). If he still wants it, build it.

## What an explainer teaches

The pattern, not one problem (f0010, f0013): where it applies, how to recognize it, and why its moves are safe. The Binary Search page (v2) set the standard. A built page has these sections, in this order:

1. **Spot it.** What the pattern is for, the three or four questions he asks himself, six recognition cases ("which fits?", with a near-miss or two among them, each wrong pick explained) and "looks like it, isn't".
2. **The parts.** Names before the run (pre-training), the plan card, what stays true, why each move is safe, and what it relies on.
3. **Trace it.** The stepper on 2–3 curated inputs, one of them an edge case or a contrasting algorithm, with predictions at decision points.
4. **The family.** The variants, what changes in each, and the problems (from `assets/problems.json`) each one solves.
5. **Count the work.** Runs × cost, the line that decides, and a table of counts measured on growing inputs against the stated bound.
6. **Where it breaks.** The usual bugs, one line each.
7. **Check it without the visual.** The lesson is hidden: a fresh trace to write down, two transfer questions, and the core idea in his own words, compared with a model answer. Save his words as the Core idea and add a `trace` card so the check repeats days later.

## What the evidence says, in one paragraph

How the learner uses a visualization matters more than what it shows: studies that varied engagement found effects far more often (10 of 12) than studies that varied the graphics (3 of 9), and passive viewing does about as well as no visualization. Animation adds little over static frames (d ≈ 0.2–0.4) and can make material feel easier while hurting transfer. What reliably helps: stepping under his control, small segments, highlighting what changed, naming parts before the run, predicting at decision points, a curated input, and comparing two algorithms on the same state.

## The seven beats

1. **Pre-training card.** Names of the parts (pointers, state, invariant). This doubles as the plan card.
2. **Stepper on a curated input.** One step per meaningful event (loop iteration, call, relaxation, sift). Highlight the deltas. Show the Python with the current line and live per-line run counts.
3. **Predictions at decision points only.** "Expand or shrink?", "Which pointer moves?", "Is this branch pruned?" Put a prompt where a wrong invariant would break, not on every step. Always show the gap between his prediction and the real result.
4. **Permanent history.** A trace table beside the stepper (one row per iteration, only the variables that change), so nothing he needs is transient.
5. **Faded stretch.** Some state cells show "?" for him to fill before he can step on.
6. **Edge case or comparison.** An edge-case preset, or brute force and the optimized algorithm in lockstep on the same input (the (i, j) grid is ideal for this).
7. **Check with the visual hidden.** Reproduce the state after step k, state the invariant, or trace a fresh input on paper, then say the core idea in his own words (save it as the Core idea in the concept notes). Then add a `trace` card so the check repeats days later.

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

## Specs: the build pipeline

No frame comes from imagination. Splitting execution from rendering (the LLM writes a Python tracker that emits a JSON trace, and a fixed renderer draws it) raised LLM visualization success from 82.5% to 99.8% on 200 LeetCode tasks. Here the tracker is Python's own tracer and the renderer is the shared stepper in `assets/explainer/`.

A pattern's page is built from `notebook/concepts/<slug>/spec.py`:

```bash
python3 <skill-dir>/scripts/build_explainer.py notebook/concepts/<slug>/spec.py   # writes <slug>-explainer.html beside it
```

The spec holds the words of each section (`SPOT`, `PARTS`, `FAMILY`, `TRAPS`, `CHECK`) and the code:

- **`REFERENCE`** and any other traced function: plain, simple Python, the code he would write. The build runs each traced input with `sys.settrace`; one step is one line about to run, and the stepper shows real locals and real run counts.
- **`view(S)`** returns the views for one step (`V.array`, `V.items`, `V.mapping`, `V.vars`, `V.grid`, `V.graph`, `V.bars`), from `S.v` (the frame's locals), `S.stack` and `S.trace[:S.index]` (what came before). `say(S, N)` narrates the line `S` ran; `row(S, N)` adds a history row.
- **`PREDICT`**, keyed by a line's text: the question, the options (or none, for a value he types), and the answer, computed from the state.
- **`ORACLE`**: the reference against brute force on at least 20 generated inputs, edge cases included. **`INVARIANT(S)`**: asserted at every step. **`COUNT`**: the line that decides, worst-case inputs at growing sizes, and a bound the measured runs must not pass.

The build fails on a mismatch with brute force, a broken invariant, a count over its bound, or a prediction whose answer isn't among its options. Specs run 200–350 lines; copy the closest one. `tests/test_explainers.py` builds every spec; `python3 tests/browser/check_explainers.py` opens every saved page the way the learning app serves it.

When you can't execute code, generate the page from a JavaScript step generator that checks its own invariants and shows a visible "invariant violated at step k" badge, and say the trace wasn't verified against Python.

## Output and saving

- The saved file is a whole page that needs nothing from its host: `<!doctype html>`, a `<title>`, inline CSS and JS, and its own colours for light and dark. A built page is all of that already. A widget written for a chat host is a fragment: wrap it in a page before saving. The learning app serves the file sandboxed, where `localStorage` and cookies throw, so keep state in memory or put storage inside `try`/`catch`. Nothing takes focus or scrolls while the page loads.
- In Claude, you may also publish the page as an artifact; keep the URL. Elsewhere (ChatGPT, Codex), write the HTML file he can open in a browser.
- Always save the file to `notebook/concepts/<slug>/` and run:

```bash
coach.py artifact add --concept <slug> --title "<page title>" --file <path> [--url <published url>] [--version 1]
```

- When a follow-up question changes a page, edit the spec (or the page, for a hand-built one), rebuild, bump the version, add a line to the concept's changelog in `concepts/<slug>/notes.md`, and register the new version.
