> **Archived.** Four stages built in 0.8.0 and kept; finishing a solve in the panel was removed in 0.9.0. Kept for history: paths inside are as they were when it was written.

# Plan: four solve stages, and finishing a solve in the panel (0.8.0)

Design: `docs/superpowers/specs/2026-11-09-panel-completion-design.md` (see "Approved scope (trimmed)").
Test-first for each step. Never touch the real `notebook/` in tests.

## A. Four stages

1. **coach.py** — `STAGES` becomes Understand, Find an approach, Build it, Check and finish (Polya phases unchanged). New solves carry `"protocol": 2`. `load_live` migrates a legacy solve: stage 1→1, 2–6→2, 7→3, 8→4; old notes 2–6 merge into note 2, each under its original label; notes 1, 7 and 8 move unchanged to 1, 3 and 4. The migrated solve is written back on the next locked command. `solve stage` and `solve note --stage` accept 1–4; status reads "stage n/4".
2. **Teaching text** — protocol.md's stage table becomes four stages with the teaching moves (find something that works, count concretely, connect to the limit, find a reason to improve, keep a short plan, bridge plan to code, look back). SKILL.md's protocol section follows. plan-card.md, retention.md, platforms.md and the solve.py template lose old stage numbers.
3. **Study app (app.js)** — four `STAGES`; the panels are 1 restatement + examples, 2 approach note + plan card, 3 build notes (plan-empty nudge), 4 look back + finish. Each stage has **Help me think**: in the panel it asks the panel coach for one question for this stage; in the full app it copies that prompt. Bump the draft version.
4. **Companion (companion.js)** — four stage names; counts come from `STAGES.length`.
5. **Pane (register.tsx)** — four stages and four dots; a solve without `protocol: 2` maps its stage as in step 1.
6. **Consistency test** — stage names in coach.py, app.js, companion.js and register.tsx match.

## B. Finish in the panel

1. **coach.py** — `solve end` writes `session` (the session identity) into the attempt row, and takes `--json` to print a receipt `{id, problem, outcome, kind, status, next_due}`. With `--expected-session S`, when an attempt for S is already logged, it prints that receipt and logs nothing more. If the live solve is still S, it finishes the stage notes and removes the live solve.
2. **app/completion.py** — `prompt(...)` builds the review request: stage notes, plan card, examples, rung, outcome, lesson, outside help, LeetCode code and page text. `parse(text)` accepts only strict JSON: `{feedback, missing[], outcome, complexity_stated, technique|null, mistakes[], rung}`, with enums checked against coach.py. `missing` non-empty means not recordable. Claiming "solved" with no test evidence in the inputs counts as missing evidence.
3. **server.py** — `POST /api/finish/review` snapshots the inputs, starts a tool-less Claude job and returns an id. `GET /api/finish/review?id=` polls the job, validates the reply, records any rung through `record_rung`, then stores `{fingerprint, record}` for the solve. `POST /api/finish/save` recomputes the fingerprint from the live solve plus the supplied finish inputs and code, and answers 409 "changed since the review" on a mismatch. Otherwise it runs `solve end --json --expected-session ...` with the reviewed fields and returns the receipt. A repeat after the solve has ended returns the same receipt.
4. **Panel UI** — in stage 4 inside the panel: outcome, lesson and an "I used outside help or saw a solution" checkbox, then **Review attempt** (captures LeetCode, polls), the review card (feedback, missing evidence, proposed record), **Save attempt** (enabled only for a recordable, current review) and a receipt with the next review date plus **Continue practice**. Buttons are disabled while a request runs.
5. **Docs and release** — SKILL.md, PRODUCT.md, extension README, walkthrough, CHANGELOG 0.8.0; bump `metadata.version` and `SKILL_VERSION`; run the unit tests, frontend tests, pane tests and `coach.py validate`, then `coach.py package`.
