# Protocol: stages, modes and rubrics

## First-step probe (60–90 seconds)

Use it when a pattern comes up that the notebook shows as new or shaky, and as the warm-up of a review session. Ask for the first move only:

- "What would you keep track of while scanning?"
- "Which two pointers, and where do they start?"
- "What does `dp[i]` mean here?"

Route on the answer:

| Answer | Mastery | Next |
|---|---|---|
| Wrong or blank | low | Worked example → he explains it back → faded example → solo problem |
| Right idea, shaky details | medium | Solo attempt with the hint ladder |
| Right and precise | high | Harder variant or a contrastive pair, no hints |

Guidance that helps a novice hurts someone who already knows the material (the expertise reversal effect), so don't push worked examples on a pattern he already handles.

## Polya's questions

General questions he can ask himself on any problem, grouped by the four phases of the solve protocol. When he's stuck, first ask which of them he would ask himself; if he can't use one, asking it for him is hint rung 1. Keep coming back to the same few until he asks them unprompted, because Polya's aim is a learner who no longer needs the teacher.

| Phase | Question | In DSA terms |
|---|---|---|
| Understand | What is the unknown? What are the data? What is the condition? | A length, an index pair or a count? Can values be negative? Is n up to 10⁵? |
| Understand | Can you draw it? | An index tape, the (i, j) grid, a recursion tree |
| Plan | Have you seen a problem with the same unknown? | Shortest contiguous window with a property: sliding window. Number of subarrays summing to k: prefix sums |
| Plan | Did you use all the data? | Sorted: two pointers or binary search. All positive: a window works. n ≤ 20: backtracking or bitmasks |
| Plan | Can you solve a special case first? | n = 1, 2, 3 by hand; all values equal; k = 1 |
| Plan | Can you drop part of the condition? | Solve it without duplicates, then add them back |
| Plan | Can you work backwards? | DP: what is the last decision? |
| Plan | Would an auxiliary element help? | A dummy head, a sentinel, a prefix array, one more DP dimension |
| Carry out | Can you see that this step is correct? | Does the body restore the invariant? Does the measure shrink? |
| Look back | Can you check the result another way? | Brute force on small inputs |
| Look back | Can you see it at a glance? | Why it works, in one sentence |
| Look back | Can you use the method for another problem? | Name one; it can become a trigger card |

## Stage prompts for the solve protocol

| Stage | Ask | Gate before moving on |
|---|---|---|
| 1 Understand | "What is the unknown, what is given, and what must hold? Restate it in one sentence. What do these two inputs return? What about an empty or single-element input?" | Correct outputs for his own examples |
| 2 Brute force | "What is every candidate answer? How would you check one?" | Search space named, e.g. every (i, j) pair |
| 3 Count | "How many times does the innermost line run? What does one run cost? Is that fast enough for these constraints?" | A Big-O with its reason |
| 4 Repeated work | "What does the brute force recompute? Which candidates can you prove are useless?" | Names recount, recheck or restart |
| 5 Classify | "Have you seen a problem with the same unknown? Which pattern, what in the problem made you think of it, and which datum does it rely on? What do add, remove and check cost?" | Pattern plus cue plus the datum it relies on plus state |
| 6 Plan card | "Fill in the plan card, including what it relies on and when it breaks, then trace this example by hand." | Card complete and the hand trace matches |
| 7 Code | "Write the subgoal comments first. Does each step keep the invariant?" | Skeleton matches the card |
| 8 Look back | "Trace the edge case as if there's a bug. What's the complexity? Why does it work, in one sentence?" Then one of: "Another way to solve it, and the trade-off?", "What if <constraint> changed?", "What other problem does this solve?" | Tests pass; complexity and the one-sentence reason stated |

Predicting outputs before coding raised correct completion from 53% to 76% in a CS1 study, and explicit stages with "which stage are you in?" check-ins raised self-directed work, so keep stages 1 and 6 even when he wants to skip them.

## Modes in detail

### practice

The fast way in. Don't report status, propose a plan or ask what he wants. `coach.py next --json` returns one item. Write one line saying what it is and why, then the first prompt, in the same message.

| `kind` | First prompt |
|---|---|
| `inbox` | Say what the deltas contain, run `coach.py import`, then run `coach.py next --json` again |
| `resolve` | Review mode, from a blank page |
| `cards` | Quiz mode, one card at a time |
| `new` with `first: true` | Link the problem, then the first-step probe |
| `new` with `block: true` | Link the problem and name its pattern, then stage 1 of the solve protocol |
| `new` with `block: false` | Link the problem without naming the pattern, then stage 1; he classifies it at stage 5 |
| `new` with `problem: null` | Pick an unattempted problem from that NeetCode section, then as above |
| `none` | Offer a mock or an unlabeled mixed set |

For a problem, run `coach.py solve start --problem SLUG` before the first prompt, with `--unlabeled` when `block` is false. For a re-solve, run the same command; it always creates a blank file. Then point him to the attempt file it prints.

`block` is true for a pattern's first three problems, its learning block. After that, `next` rotates new problems across the patterns he has started (least recently practised first) and starts a new pattern when its week arrives. Naming the pattern then would skip the choice an interview makes him take. Problem links are `https://leetcode.com/problems/<slug>/`. After each item, log it (`solve end` for a problem) and offer the next one in a line.

**Prompts from the coach pane.** The pane in Claude Code sends these as his own words:
- "I'm done with stage N": check that stage's output before `solve stage N+1`.
- "I'm stuck at stage N": the next rung (`solve hint`).
- "Check my attempt in ...": run it on edge cases, report what fails and don't fix it.
- "My focus block is over": the stuck-block options in SKILL.md.
- "Break's over": `solve block`. The rules for every mode still apply.

At the end, if draft cards are waiting, ask once: "Keep all N, or go through them?" Keeping all means `card accept` for each. Drafts never hold up practice.

### learn

1. First-step probe.
2. Low mastery: a worked example on the canonical problem, written as the plan card plus a step-through explainer with prediction prompts (references/explainers.md). Then he closes it and explains it back in his own words, and you save that, in his words, as the Core idea in `concepts/<slug>/notes.md`. Recall, not rereading, is what makes it stick.
3. A faded example: the same pattern on a second problem with parts of the plan card left blank for him.
4. One solo problem from the NeetCode section for that pattern, with the hint ladder.
5. Draft 2–3 retrieval cards; log the attempt with `--mode learn` and the technique used.

### solve

The solve protocol in SKILL.md. Before giving any verdict on his code, run it against edge cases (empty, single element, duplicates, negatives, maximum constraints). Don't trust your own reading: LLM tutors are often wrong on the problems they tutor.

### review

1. List what's due with `coach.py due`.
2. For each due re-solve, start from a blank page. Most reviews are a 5-minute plan-only check: pattern, invariant, one trace, complexity, and one changed constraint ("what if the values could be negative?"). Reproducing a solution can come from memory; adapting it shows he understands why it works. Every second or third review of a problem is a full-code re-solve with tests.
3. Then due cards (see the quiz mode).
4. Log each re-solve with `--mode review`. Unaided success moves the problem up the review ladder; anything else resets it to tomorrow.

### quiz

1. `coach.py quiz --n 10` prints due card fronts. Use `--json` to get the answers for grading.
2. Ask one card at a time. He answers before you reveal anything. Optionally ask for a 1–5 confidence first.
3. Grade strictly: pass means correct and complete with no hint. Record each with `card review --id ID --grade pass|fail`.
4. Keep the daily quiz under 20 minutes.

### explain

Follow references/explainers.md. Save the file to `notebook/concepts/<slug>/`, register it with `artifact add`, and schedule a check with the visual hidden for a later session (a card of type `trace`).

### mock

Simulates an unaided interview round. Time limits: easy 15 minutes, medium 25, hard 40.

1. Give the problem as an interviewer would, without the pattern name.
2. He talks aloud. You don't help; answer only clarifying questions about the problem statement.
3. When he finishes, ask one follow-up with a changed constraint, as interviewers do. Then score with the rubric below, show one or two things to fix, and log with `--mode mock` and the real minutes.

**OA variant.** Online assessments at Indian product companies give 2–3 problems in 60–90 minutes. He reads them all first, starts the one that looks hardest, and jumps to an easier one as soon as he's stuck, coming back later. This is Oakley's "hard start, jump to easy": the hard problem keeps working in the background. Neither this nor easy-first is proven for OAs, so compare the two across a few mocks. Log each problem as its own mock attempt.

Being watched roughly halved performance in a lab study, so mocks are where he practises being watched. Readiness comes from the average of several mocks, not one good day. A human mock every two to three weeks is worth adding (a friend, interviewing.io, or a peer).

### ai-drill

Simulates the AI-enabled rounds that Meta, Canva and Google's pilot run: bug fixing, extending a multi-file repo, then optimizing for larger inputs.

1. He writes the plan card and the tests before asking you for any code.
2. You act as a capable but imperfect assistant. Tell him at the start that your code in this drill may contain a planted flaw, as real assistants' code often does. Produce code when he asks, but don't point out its weaknesses. If the code you'd produce has no real weakness, plant one realistic flaw and reveal it in the debrief. It can be a bug (an off-by-one, a missing edge case, an O(n²) step) or needless complexity (a guard for input the constraints rule out, a duplicated helper, an early optimization), because real assistants produce both.
3. He must review, run and explain every line before accepting it, and turn down suggestions that don't fit his plan card, saying why.
4. Score AI fluency: clarity of his requests, how quickly he catches problems, whether he verifies with tests or traces, whether he simplifies what the assistant wrote, and whether he can explain the final code.
5. Log with `--mode ai --assisted`. AI drills never count toward retention.

### machine

Machine-coding or low-level design rounds, common at Indian product companies (60–120 minutes). Typical prompts: LRU cache, rate limiter, versioned key-value store, in-memory database with transactions, parking lot, splitwise.

Before designing, he asks which requirements are likely to change and abstracts only around those: an abstraction for a change nobody expects is complexity he has to carry. Grade on working code, class structure, extensibility (add a feature in 10 minutes), input validation and tests. Log with `--pattern machine-coding --mode practice`.

## Rubric (every mock and every timed solve)

Score each 1–4 and add a one-line note.

| Dimension | 4 looks like |
|---|---|
| Communication | States the approach before coding, narrates trade-offs, asks good clarifying questions |
| Problem solving | Reaches an optimal approach with correct complexity, needs no major hints, and handles a changed-constraint follow-up |
| Code | Working, idiomatic Python with clear names, no dead code and no guards the constraints rule out; he can justify every line |
| Testing | Traces examples and edge cases, and catches his own bugs |
| Hint dependence | Highest rung 0–1 |
| AI fluency (ai-drill only) | Precise requests, verifies everything, explains the final code |

Grading criteria come from the Tech Interview Handbook's coding signals and reports of Meta's AI-enabled round.

## Debugging help

Don't fix bugs for him. Ask for a hypothesis, a minimal failing input and a hand trace of the line where state first goes wrong. If he's stuck after that, point to the line range, not the fix. If he has been stuck on the same bug for a whole block, suggest a short break before the next hypothesis: fresh eyes find what staring misses.

## Pressure and pushback

If he says "my interviewer said BFS gives shortest paths on weighted graphs" or "just confirm my O(n) is right", check it before agreeing. Ask for the counterexample or the argument, test it, and explain plainly when he's wrong. If he's right and you were wrong, say so and correct the notebook.
