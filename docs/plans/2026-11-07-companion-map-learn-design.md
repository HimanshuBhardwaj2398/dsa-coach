# The companion: Map, Learn, and a coach beside LeetCode

Date: 2026-11-07 · Status: approved in brainstorming · Builds on the study app (0.5.x) and `PRODUCT.md`

## Goal

One path through interview prep that follows the coach's protocol: a map of patterns, a Learn page per pattern with a theory explainer and good resources, and the problems that train it (Blind 75 first, then the rest of NeetCode 150). Solving happens on LeetCode, with the coach in Chrome's side panel. The coach remembers progress in `notebook/` as it does today.

It is for Himanshu first. Beginner topics (Python basics, complexity, how to approach a problem) appear on the map as stubs and are written when testers arrive.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Audience | Himanshu first, beginner-ready later | He is on day 9 of the plan. Writing beginner content up front would delay everything else. |
| Theory pages | Written by the coach the first time a topic opens, saved in `notebook/concepts/<pattern>/` and reused | Uses the explainer rules in `references/explainers.md`, so pages make him predict at each step instead of watching. |
| How they are written | The local server runs `claude -p` with the dsa-coach skill, on his subscription | No API key. The same plumbing serves the side-panel coach in milestone B. |
| Catalogue | NeetCode 150, with Blind 75 tagged, ordered Blind 75 first | Covers the lists he named. Extra problems come later, only for weak patterns. |
| Where solving happens | On LeetCode, with the coach in Chrome's side panel | The site he will practise and interview on. The Solve tab stays as a fallback that nothing links to. |
| Sequencing | One spec, two milestones. **A:** Map and Learn, with problems linking to LeetCode and the coach in Claude Code chat. **B:** the side panel. | A is useful without the riskiest part, the extension. |
| Code | Very simple: stdlib Python, plain JS, no framework, bundler or new dependency | A single-user local tool he maintains himself. |

## Milestone A: Map and Learn

### Screens

- **Map (`#/map`, the new home).**
  - The 22 roadmap patterns as a graph, laid out by phase and week, with edges in the roadmap's order. The layout is our own, drawn from `roadmap.json`; nothing is copied from NeetCode's roadmap.
  - Each node shows its status (not started, learning, practising, solid), Blind 75 and NeetCode 150 progress (for example `3/5 · 6/9`), and a dot when re-solves are due.
  - A strip on top shows `coach.py next`'s pick, plus **Resume** when a solve is live. This replaces the old start screen.
  - The Foundations stubs are marked "coming later".
- **Learn (`#/learn/<pattern>`).**
  - **Top:** the pattern's cues, invariant and template, from `roadmap.json`.
  - **The explainer:** **Read the explainer** when one exists; otherwise **Write the explainer**, which shows progress while the coach writes it.
  - **Resources:** two or three from `references/resources.md`.
  - **Problems:** Blind 75 first, each with its status, last outcome and due date, and a link to `https://leetcode.com/problems/<slug>/`.
- **Solve (`#/solve`).** The current page, unchanged apart from a "← Map" link in the bar. Only Resume and direct URLs reach it.

### Data

- **`skills/dsa-coach/assets/problems.json`:** for each pattern key, an ordered list of `{slug, title, difficulty, lists}`, where `lists` holds `blind75` and/or `nc150`. `coach.py validate` checks that every pattern key exists in `roadmap.json`, that slugs are unique and kebab-case, and that each pattern's canonical problems are listed. The file holds slugs and titles only, never statements or solutions.
- **`coach.py map --json`:** the map's data, worked out from existing records (`attempts.jsonl`, the review schedule, `techniques.json`). There is no new notebook file. Every status is a pure function of those records.

### Server and files

| File | Job |
|---|---|
| `app/claude_job.py` | Runs one `claude -p` at a time with a timeout; returns the text or an error. The binary's path comes from `notebook/config.json` (`claude_bin`), because Homebrew's `claude` is too old. |
| `app/server.py` | `GET /api/map` (runs `coach.py map --json`), `POST /api/explainer {pattern}` (starts a job), `GET /api/explainer?pattern=` (idle, running, done or error). Explainers are served from `notebook/concepts/<pattern>/` in a sandboxed iframe. |
| `app/static/index.html` | Routes by hash. |
| `app/static/shared.js` | The request and banner helpers. |
| `app/static/map.js`, `learn.js` | The two new views. |
| `app/static/solve.js` | Today's `app.js`, renamed. |

**Explainer flow:**
1. **Write the explainer** sends `POST /api/explainer`.
2. `claude_job` runs the coach with the instructions in `references/explainers.md`.
3. The page checks the status every 3 s.
4. The coach writes `notebook/concepts/<pattern>/explainer.html` and registers it with `coach.py artifact add`.
5. The Learn page shows it.

## Milestone B: the coach beside LeetCode

### What he sees

He opens `leetcode.com/problems/<slug>/` and Chrome's side panel shows the coach.

- **With no live solve:** **Start**, with the 1–5 confidence pick.
- **During a solve:** the stage dots, the current stage's question and boxes, Notes, the focus timer and **Ask coach**. These are the same stage components as the app.

### How it reads LeetCode

`content.js`, on problem pages only, reads three things from his own tab:

1. **The slug**, from the URL.
2. **The code**, from the editor, when he presses Run or Submit.
3. **The submission result** LeetCode's page already receives: the status, and on a wrong answer the failing input, his output and the expected output.

It never sends requests to LeetCode, never presses anything and never fetches in bulk.

### Data flow

The panel talks only to `app/server.py`, which writes through `coach.py`:
- Stage answers become solve notes.
- The code from each Submit is saved to `problems/<slug>/<date>.py`.
- Each failing case is kept with the attempt.

### The brain

- **Instant, in the panel:** stage prompts, "which stage are you in?" when code appears before stage 6, the timer and the end-of-block choices.
- **Through the server:** Ask coach, stage checks and hints use `POST /api/coach`, which calls `claude_job` with the live solve and the code.
- **On Wrong Answer:** the panel shows the failing case, then asks for a hypothesis and a hand trace before any hint.
- **The rules stay in the skill:** the hint ladder and no solutions.

### Safety and robustness

- The server accepts requests from the extension only when its origin matches the ID in `notebook/config.json` (`extension_id`). It keeps the `X-DSA-Coach` header check.
- Manifest V3 forbids loading code from a server, so `coach.py package` copies the stage UI files into `extension/`.
- If the editor or the result can't be read, the panel says so and the stages keep working. He can paste the code in instead.
- The panel reminds him once to turn off LeetCode's autocomplete.
- NeetCode comes later. It needs a slug map (`duplicate-integer` → `contains-duplicate`).

## Errors

Each error is one clear line on the page, with a retry where retrying helps:
- `claude` missing or too old.
- A job timeout: 5 min for an explainer, 90 s for a coach reply.
- A job already running.
- The server down (the panel shows `python3 app/server.py`).
- An unreadable editor or result.
- An unknown slug, meaning a problem outside the catalogue: the panel still coaches it, and the map doesn't count it.

## Testing

- **Python `unittest`:** the catalogue validation; `map --json`'s status logic; `claude_job` run against a fake `claude` script (success, timeout, failure, busy); the new routes, including the extension-origin check.
- **Node tests** for pure JS functions: status → label, the map layout, and the parser that turns LeetCode's result into a failing case.
- **Playwright** on a copy of the notebook: Map and Learn in light and dark at 1440×900 and 390 px wide, and a Write-the-explainer run with the fake `claude`.
- **By hand:** the side panel on real LeetCode, because a signed-in LeetCode session can't be automated reliably.
- **As usual:** `coach.py validate`, both test suites, `node --check`.

## Later, not in this spec

- **Stuck-point memory and alternative angles.** It records the stage, the hint rung and what unlocked each stall. An angle is credited only when he later re-solves the problem unaided.
- **Beginner content and tester onboarding:** intake questions and a placement check.
- **NeetCode support and extra-depth problems.**
