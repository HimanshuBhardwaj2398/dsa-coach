# Learning How to Learn, How to Solve It and Programming as Theory Building

Three more sources, reviewed for version 0.3.0 (November 2026):
- Barbara Oakley and Terrence Sejnowski's *Learning How to Learn*.
- George Polya's *How to Solve It*.
- Peter Naur's "Programming as Theory Building", as read by Pol Alvarez Vecino in "Why LLMs can't make your code simpler".

Most of what *Learning How to Learn* teaches was already in the design, through the research in `dsa-learning-skill-research.md`: retrieval over rereading, spacing, attempts before help, and credit only for delayed success. The three sources still add four things:
- how to help (Polya);
- when to step away (Oakley);
- what understanding a solution means, and how to test for it (Naur);
- why an LLM coach has to work at keeping code simple (Vecino).

This page records the principles and where each one lives in the skill, so later changes can be checked against the reasons behind them.

## Learning How to Learn

Sources: Oakley and Sejnowski's Coursera course and Oakley's *A Mind for Numbers* (2014). The course has four modules: what learning is, chunking, procrastination and memory, and renaissance learning.

**Focused and diffuse modes.**
- A hard problem needs focused work first. Then it needs time away (a walk, a break, sleep) while the brain keeps working on it in the background.
- Einstellung, fixation on a first idea, is the usual way people get stuck.
- *In the skill:* a genuine attempt is one focused block. When the block ends unsolved, a short break comes before more help, and parking a problem until tomorrow is a legitimate move.
- Polya's "subconscious work" says the same thing. The evidence is measured but supportive:
  - A meta-analysis of incubation studies found a reliable benefit from breaks, larger after longer work on the problem first (Sio & Ormerod 2009).
  - In one experiment, sleep more than doubled the share of people who found a hidden shortcut in a task (Wagner et al. 2004).

**Chunking, with context.**
- A chunk forms through focused attention, understanding the core idea, and practice.
- It is complete only with context: knowing when to use it and when not to.
- *In the skill:* the plan card's Relies on and Breaks if lines. Roadmap cues say when to use a pattern; these lines say when it fails.

**Illusions of competence.**
- Rereading, watching a solution or highlighting feels like learning because the material looks familiar.
- Recall (closing the page and producing the idea) and self-testing are the fix.
- *In the skill:* already covered by predict before reveal and by the cards. Added:
  - the core idea in the learner's own words after an explainer;
  - recall after any linked resource;
  - an attempt offered before more examples or animation.

**Spacing, interleaving and deliberate practice.**
- Spread practice over days.
- Mix problem types, so the skill of choosing a technique gets practised too.
- Spend effort on what is hard.
- *In the skill:* spacing and mistake repair were already there. Interleaving was promised in the roadmap, but `coach.py next` served problems in blocks. From 0.3.0, `next` mixes patterns after each pattern's first three problems.

**Procrastination: process over product.**
- Commit to time on task (a 25-minute Pomodoro), not outcomes ("solve five problems").
- A habit has a cue, a routine, a reward and a belief.
- Plan the next session before stopping.
- *In the skill:*
  - Sessions are planned in 25-minute blocks.
  - Each session ends by agreeing when the next block happens and what it starts with.

**Tests.**
- "Hard start, jump to easy": look at everything, start a hard problem, and switch to an easy one as soon as you are stuck, so the hard one keeps working in the background.
- Sleep before the test.
- *In the skill:* the OA variant of mock mode. It is compared against easy-first, not assumed to be better.

## How to Solve It

George Polya, 1945. Part I sets out four phases and how a teacher should help. Part III is a short dictionary of heuristics.

**Four phases:** understand the problem, devise a plan, carry out the plan, look back.
- *In the skill:* the solve protocol's eight stages now sit under these four phases, which are easier to hold in mind than eight separate stages.

**Understand: the unknown, the data, the condition.** Draw a figure; introduce notation.
- *In the skill:* stage 1 names all three before predicting outputs.

**Plan: questions that point toward a solution.**
- Have you seen a problem with the same unknown?
- Did you use all the data?
- Can you solve a more special or more general problem? Can you drop part of the condition, work backwards, or introduce an auxiliary element?
- *In the skill:* the question table in `references/protocol.md`, with DSA examples. A sorted input invites two pointers or binary search; n ≤ 20 invites backtracking.

**Carry out: check each step.**
- *In the skill:* stage 7 checks each step against the invariant.

**Look back.** Check the result another way, see it at a glance, and use the result or the method for another problem.
- Polya notes that even fairly good students skip this phase, and miss an important and instructive part of the work.
- *In the skill:* stage 8 asks why the solution works, in one sentence. It then asks one rotating question: another approach and its trade-off, a changed constraint, or another problem the method solves.

**How to help.**
- "The teacher should help, but not too much and not too little, so that the student shall have a reasonable share of the work."
- Questions should be general (useful on many problems) and natural (something the student could have asked).
- The teacher repeats the same questions until the student asks them unprompted.
- *In the skill:*
  - The hint ladder starts by asking which question the learner would ask themselves.
  - Rung 1 is one of the general questions.
  - A leading question that contains the answer counts as the rung it gives away.

## Programming as Theory Building, and why LLMs can't make code simpler

Peter Naur, 1985; Pol Alvarez Vecino, Answer.AI, August 2026.

**A program is a theory held in someone's head.**
- Code and documentation are incomplete artifacts of that theory.
- Naur's test for having the theory is that you can:
  - explain how the program maps to the problem it solves;
  - justify why each part is what it is;
  - respond well to a request for change.
- *In the skill:* this is what understanding a solution means.
  - Reviews and mocks now include a changed-constraint question, and the look-back step asks why the solution works.
  - Reproducing code from memory can pass a re-solve; adapting it can't be faked.
  - Interviewers probe the same way, with variants and follow-ups.

**Theory is built by doing.**
- A theory can't be fully handed over through documents.
- This is the deepest reason for attempt-before-answers: an LLM's worked solution is an artifact of a theory the learner doesn't have yet.

**The complexity that matters is the theory's.**
- Line counts, Halstead volume and cyclomatic complexity miss it. A one-liner can be harder to justify than three plain lines.
- *In the skill:* code is judged by whether every line can be justified, not by its length.

**LLMs push code toward complexity unless someone checks.**
- Vecino lists duplicated methods, defensive code for cases that can't happen, and early optimisation. He also notes that labs earn more when more tokens are used.
- *In the skill:*
  - Rule 8 holds the coach's own code to the plan card.
  - AI drills can plant needless complexity as well as bugs.
  - AI fluency is scored partly on whether the learner simplifies the code.

**Weigh every suggestion against your theory.**
- In Vecino's example, a frontier model recommended going back to the payment design the team had just abandoned.
- *In the skill:* in AI drills, the learner turns down suggestions that don't fit the plan card and says why. Rule 5 already covers the other direction: the coach doesn't give in to wrong claims.

**Choose abstractions for the changes you expect.**
- Vecino keeps two near-duplicate client classes because one provider is about to be dropped.
- *In the skill:* in machine-coding rounds, the learner first asks which requirements are likely to change, and abstracts only around those.

**This applies to the skill itself.**
- Claude maintains the skill and will tend to add rules and code.
- CLAUDE.md and AGENTS.md now ask for every change to be checked against `docs/research/`, replacing or simplifying rules rather than adding more.

## Where the three agree

| Principle | Sources | Where it lives |
|---|---|---|
| Understanding is a theory you build: explain, justify, adapt | Naur, Polya, Oakley | Attempt before answers (rule 1); look back (stage 8); changed-constraint checks in reviews and mocks |
| Help with general questions first, and never more than needed | Polya | Hint ladder; Polya's questions in protocol.md |
| Four phases, and always look back | Polya; Oakley on chunking | Solve protocol |
| A chunk includes when it works and when it breaks | Oakley, Polya, Naur | Plan card (Relies on, Breaks if); card targets |
| Focus, then step away | Oakley, Polya | Hint ladder: when a block ends unsolved |
| Retrieve, don't rewatch | Oakley; the visualization research | Rules 2 and 6; explainers.md; learn mode |
| Mix problem types after a short block | Oakley; Rohrer & Taylor 2007 | `coach.py next`; mixed problems are presented unlabeled |
| Process, not product | Oakley | Session start and end |
| Simple code is code you can justify | Vecino, Naur; Polya's "see it at a glance" | Rule 8; rubric; AI drill; machine coding |
| Practise the test, including its strategy | Oakley | Mock mode, OA variant |
| Credit only delayed, unaided success | All three | Rule 4, unchanged |

## Not adopted

- **Memory palaces and mnemonics.** Oakley teaches them for facts. Interview DSA is a procedural skill, and cards plus re-solves already cover the facts it needs.
- **Code metrics in grading.** Vecino's argument is that they miss the complexity that matters.
- **Polya's whole dictionary.** Twelve questions cover interview problems; a longer list would get skimmed.
- **A minutes-against-plan metric in JOURNEY.md.** It could turn process into a score to feel bad about. Revisit if logged attempts stay at zero.
- **Enforced breaks.** No timers or hooks: the coach suggests a break, and the learner decides.

## Sources

- Barbara Oakley and Terrence Sejnowski, *Learning How to Learn* (Coursera, since 2014): https://www.coursera.org/learn/learning-how-to-learn
- Barbara Oakley, *A Mind for Numbers* (2014).
- George Polya, *How to Solve It* (Princeton University Press, 1945).
- Peter Naur, "Programming as Theory Building", *Microprocessing and Microprogramming* 15(5), 1985: https://pages.cs.wisc.edu/~remzi/Naur.pdf
- Pol Alvarez Vecino, "Why LLMs can't make your code simpler" (Answer.AI, 2026-08-19): https://www.answer.ai/posts/2026-08-19-llms-code-simpler.html
- Ut Na Sio and Thomas Ormerod, "Does incubation enhance problem solving? A meta-analytic review", *Psychological Bulletin* 135(1), 2009: https://doi.org/10.1037/a0014212
- Ullrich Wagner, Steffen Gais, Hilde Haider, Rolf Verleger and Jan Born, "Sleep inspires insight", *Nature* 427, 2004: https://doi.org/10.1038/nature02223
- Rohrer & Taylor 2007 on interleaving, and the visualization studies, are cited in `dsa-learning-skill-research.md`.
