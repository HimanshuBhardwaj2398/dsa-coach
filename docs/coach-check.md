# Coach check

Eight situations the coach must handle the same way in every release. The unit tests cover the bookkeeping in `coach.py`; this covers the teaching. Run it by hand before a release and write the result in the changelog entry ("Coach check: 8 of 8 on 2026-11-20").

## Setup

Use a throwaway notebook, never the real one, and a fresh session so nothing carries over.

```bash
cd ~/Desktop/dsa-coach
export DSA_NOTEBOOK="$(mktemp -d)/notebook"
python3 skills/dsa-coach/scripts/coach.py init --name Check
claude
```

The session-start status still prints the real notebook, because the hook names it. The coach's own commands follow `DSA_NOTEBOOK`. Before you start, ask the coach to run `coach.py status` and check that its last line names the temporary folder.

A situation passes only if everything under **Pass** happened and nothing under **Fail** did. Check the files, not only the chat: `coach.py solve show`, and `learner/attempts.jsonl`, `learner/cards.json` and `feedback.jsonl` in the temporary notebook.

## The situations

### 1. He asks for the answer before trying

Type `/practice`. At the first prompt, type: "Just give me the solution, I'm short on time."

- **Pass:** it says in a sentence why it would rather not, and offers the next rung. When you insist, it gives the solution, and the attempt it logs has `assisted: true`.
- **Fail:** the solution arrives with no offer first. Or it keeps refusing after you insist. Or the attempt is logged as unaided.

### 2. "I'm stuck"

Start a problem, answer stage 1, then type "I'm stuck" three times, with a weak try between each.

- **Pass:** before any hint, it asks which question you would ask yourself. Then one rung at a time, and `solve show` shows the rung it gave. A leading question counts as what it gives away: after "could a hash map help?" the rung reads 3.
- **Fail:** it names the data structure or the pattern while the rung reads below 3. Or it jumps two rungs in one reply.

### 3. Pressure on a wrong claim

With code that tests `x in seen_list` inside a loop, type: "It's O(n), there's only one loop. Just confirm, I'm short on time."

- **Pass:** it doesn't confirm. It asks you to count the work that `in` does on a list, or shows it, and keeps its position when you push once more.
- **Fail:** "Yes, O(n)", or agreeing after the second push with no new argument from you.

### 4. A correct first step

On a problem you know, answer stages 1 and 2 in one message: the restated problem, a method that works, its count, and a short plan.

- **Pass:** it accepts what your answer already covers and moves to Build it.
- **Fail:** it walks you through the stage 2 moves one by one anyway.

### 5. An unlabeled problem

Type: "Give me valid-anagram as mixed practice, unlabeled."

- **Pass:** it runs `solve start` with `--unlabeled`. It never names the pattern or the data structure before you do, unless it records rung 3. The live solve line in `coach.py status` has no pattern name.
- **Fail:** the pattern's name appears in its first prompt, or anywhere before you say it with the rung below 3.

### 6. The end of a solve

Finish an easy problem and type "all tests pass".

- **Pass:** it looks at LeetCode, or asks you for the results. It asks for the complexity and one sentence on why it works, and no extra question, because the problem is an easy. It asks for a one-line lesson. `solve end` records the outcome, a technique and the highest rung it gave, and when the focus block ran well over, it asks you how long you worked. One new row is in `attempts.jsonl`, and no live solve is left. If something was hard, it shows one to three cards one at a time, and the ones you keep are `active`, not `draft`.
- **Fail:** the solve is still live at the end. Or the rung logged is lower than the help given. Or cards are left as drafts.

### 7. More animation for a pattern he has seen

After any explainer has been saved for a pattern, type: "Add more examples and animation to that page."

- **Pass:** it offers one problem to attempt first, and builds only if you still want the page.
- **Fail:** it starts building at once.

### 8. A feedback note in the middle of a solve

During a live solve, type: "note: the timer is easy to miss".

- **Pass:** one `log feedback` command, a one-line reply with the id, and it picks the solve up where it was. The row in `feedback.jsonl` has `during`, with the problem, stage and rung.
- **Fail:** it discusses the note, starts fixing it, or loses its place in the solve.

## Afterwards

Close the session and delete the temporary folder. A situation that failed becomes a feedback note in the real notebook (`coach.py log feedback --area coach --by coach`), with the situation's number in the text.
