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

## Stage prompts for the solve protocol

| Stage | Ask | Gate before moving on |
|---|---|---|
| 1 Understand | "Restate it in one sentence. What do these two inputs return? What about an empty or single-element input?" | Correct outputs for his own examples |
| 2 Brute force | "What is every candidate answer? How would you check one?" | Search space named, e.g. every (i, j) pair |
| 3 Count | "How many times does the innermost line run? What does one run cost? Is that fast enough for these constraints?" | A Big-O with its reason |
| 4 Repeated work | "What does the brute force recompute? Which candidates can you prove are useless?" | Names recount, recheck or restart |
| 5 Classify | "Which pattern, and what in the problem made you think of it? What do add, remove and check cost?" | Pattern plus cue plus state |
| 6 Plan card | "Fill in the plan card, then trace this example by hand." | Card complete and the hand trace matches |
| 7 Code | "Write the subgoal comments first." | Skeleton matches the card |
| 8 Test | "Trace the edge case as if there's a bug. What's the complexity? One-line lesson?" | Tests pass and complexity stated |

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
| `new` with `first: false` | Link the problem, then stage 1 of the solve protocol |
| `new` with `problem: null` | Pick an unattempted problem from that NeetCode section, then as above |
| `none` | Offer a mock or an unlabeled mixed set |

Problem links are `https://leetcode.com/problems/<slug>/`. After each item, log it and offer the next one in a line. The rules for every mode still apply.

At the end, if draft cards are waiting, ask once: "Keep all N, or go through them?" Keeping all means `card accept` for each. Drafts never hold up practice.

### learn

1. First-step probe.
2. Low mastery: a worked example on the canonical problem, written as the plan card plus a step-through explainer with prediction prompts (references/explainers.md). Then he explains it back in his own words.
3. A faded example: the same pattern on a second problem with parts of the plan card left blank for him.
4. One solo problem from the NeetCode section for that pattern, with the hint ladder.
5. Draft 2–3 retrieval cards; log the attempt with `--mode learn` and the technique used.

### solve

The solve protocol in SKILL.md. Before giving any verdict on his code, run it against edge cases (empty, single element, duplicates, negatives, maximum constraints). Don't trust your own reading: LLM tutors are often wrong on the problems they tutor.

### review

1. List what's due with `coach.py due`.
2. For each due re-solve, start from a blank page. Most reviews are a 5-minute plan-only check: pattern, invariant, one trace, complexity. Every second or third review of a problem is a full-code re-solve with tests.
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
3. At the end, score with the rubric below, show one or two things to fix, and log with `--mode mock` and the real minutes.

Being watched roughly halved performance in a lab study, so mocks are where he practises being watched. Readiness comes from the average of several mocks, not one good day. A human mock every two to three weeks is worth adding (a friend, interviewing.io, or a peer).

### ai-drill

Simulates the AI-enabled rounds that Meta, Canva and Google's pilot run: bug fixing, extending a multi-file repo, then optimizing for larger inputs.

1. He writes the plan card and the tests before asking you for any code.
2. You act as a capable but imperfect assistant. Tell him at the start that your code in this drill may contain a planted flaw, as real assistants' code often does. Produce code when he asks, but don't point out its weaknesses. If the code you'd produce has no real weakness, plant one realistic flaw (an off-by-one, a missing edge case, an O(n²) step) and reveal it in the debrief.
3. He must review, run and explain every line before accepting it.
4. Score AI fluency: clarity of his requests, how quickly he catches problems, whether he verifies with tests or traces, and whether he can explain the final code.
5. Log with `--mode ai --assisted`. AI drills never count toward retention.

### machine

Machine-coding or low-level design rounds, common at Indian product companies (60–120 minutes). Typical prompts: LRU cache, rate limiter, versioned key-value store, in-memory database with transactions, parking lot, splitwise.

Grade on working code, class structure, extensibility (add a feature in 10 minutes), input validation and tests. Log with `--pattern machine-coding --mode practice`.

## Rubric (every mock and every timed solve)

Score each 1–4 and add a one-line note.

| Dimension | 4 looks like |
|---|---|
| Communication | States the approach before coding, narrates trade-offs, asks good clarifying questions |
| Problem solving | Reaches an optimal approach with correct complexity and needs no major hints |
| Code | Working, idiomatic Python with clear names and no dead code |
| Testing | Traces examples and edge cases, and catches his own bugs |
| Hint dependence | Highest rung 0–1 |
| AI fluency (ai-drill only) | Precise requests, verifies everything, explains the final code |

Grading criteria come from the Tech Interview Handbook's coding signals and reports of Meta's AI-enabled round.

## Debugging help

Don't fix bugs for him. Ask for a hypothesis, a minimal failing input and a hand trace of the line where state first goes wrong. If he's stuck after that, point to the line range, not the fix.

## Pressure and pushback

If he says "my interviewer said BFS gives shortest paths on weighted graphs" or "just confirm my O(n) is right", check it before agreeing. Ask for the counterexample or the argument, test it, and explain plainly when he's wrong. If he's right and you were wrong, say so and correct the notebook.
