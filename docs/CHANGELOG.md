# Changelog

## 0.9.3 · 2026-11-12 · Errors are raised, not exits; a torn log line costs one row

- **`CoachError` replaces `die()`.** Helpers raise it, and only `main` prints `error: ...` and exits 1, so code that imports coach.py (tests, the app) keeps its process. `validate` catches `CoachError` instead of `SystemExit`. The CLI's messages and exit codes are unchanged.
- **A line in `attempts.jsonl` or `questions.jsonl` that isn't JSON is skipped with a warning**, where before it stopped every command, the session-start `status --brief` included. `validate` lists it as an issue.
- **`append_jsonl` ends a torn last line before writing**, so the next row isn't glued onto the fragment and lost with it.
- Tests: `test_helpers_raise_and_only_main_exits`, `test_a_torn_last_line_is_skipped_and_the_next_row_starts_clean`.

## 0.9.2 · 2026-11-11 · The lock is the default; `compute` is split into named steps

No rule or schedule changed. On a copy of the notebook, `compute`, `JOURNEY.md`, `learner/summary.md` and `map` come out the same before and after, on 10 dates.

- **Every command takes the notebook lock unless it is defined with `lock=False`.** Before, a command ran unlocked unless someone remembered `writes=True`; that is how `card list` (0.9.1) and `init` came to write without it. `init` now waits like any other writer. The unlocked commands are the reads (`quiz`, `due`, `next`, `map`, `card list`, `solve show`, `artifact list`, `validate`) and the two that write outside the notebook (`package`, `install`).
- **`JOURNEY.md` and `learner/summary.md` are replaced whole**, as `journey.json` already was: `write_text` writes a temp file and renames it, and `write_json` is that plus `json.dumps`.
- **`compute` reads as a list of steps.** Its nine jobs are functions: `plan_clock`, `last_activity`, `pattern_row`, `pick_focus`, `due_items`, `totals`, `weak_spots`, `calibration`, `next_steps`. `analyze_problems` is `problem_status` once per problem. In `journey.json`, `next_steps` is now the last key.
- **Thresholds have names** in the constants block: `PATTERN_RETAINED_AT`, `PATTERN_READY_AT`, `WEAK_SPOT_DAYS`, `HIGH_CONFIDENCE`, `MOCKS_FROM_WEEK`, `MOCK_EVERY_DAYS`, `UNAIDED_MAX_RUNG`, `ASSISTED_MIN_RUNG`, `TOP_RUNG`. `delay_days` has one default, in `DEFAULT_CONFIG`.
- **Names and shapes:** the journey dict is `journey` everywhere (it was `j`). `Attempt`, `ProblemStatus`, `PatternRow` and `Journey` are declared as TypedDicts, plain dicts at run time. `is_card_due` and `plan_order` replace three copies each.
- Tests: `test_init_waits_for_the_notebook_lock`, `test_only_reads_skip_the_lock_and_they_change_nothing` (it fails when a new unlocked command isn't listed as a read), `test_snapshot_replaces_the_markdown_files_whole`, `test_the_declared_shapes_match_the_data`.

## 0.9.1 · 2026-11-10 · Three fixes from the code critique (pane 0.2.1)

- **`card list` is a query:** it no longer rewrites `JOURNEY.md` and `journey.json`. Reads run without the notebook lock, so a read that wrote could race a real write.
- **One minutes rule:** the pane floored each block and summed (76 min on the contains-duplicate solve) where `coach.py` sums and rounds (78). The pane now counts as `live_view` does: the total rounds the sum, the open block shows whole minutes.
- **`validate` checks the version:** it fails when SKILL.md `metadata.version` and `SKILL_VERSION` in coach.py differ.
- Tests: `test_card_list_is_a_query`, `test_validate_flags_version_drift`, and a pane test for rounding the total.

## 0.9.0 · 2026-11-10 · Solve on LeetCode; the app becomes a read-only learning view (extension 0.3.0, pane 0.2.0)

He always solves on LeetCode, and the coach can look at LeetCode with its own browser and computer-use tools. So everything that existed to solve somewhere else, or to read LeetCode for the coach, is gone. What stays is the record (`coach.py`), the teaching (the skill), and read-only views of both. Critique and plans: `plans/2026-11-10-app-critique.md`, `plans/002-learning-app.md`, `plans/003-external-coaching.md`. The browser panel and the pane are kept (he asked for both), cut down to showing progress and theory.

- **No attempt files:** `solve start` no longer writes `problems/<slug>/<date>.py`; it prints the LeetCode link. Stage notes are filed under the solve's session id. Older attempt files stay as history.
- **Seeing his work:** SKILL.md tells the coach to look at the LeetCode tab with a browser or computer-use tool where it has one, else to ask him to paste code and results; a screenshot shows only what is on screen, and the coach only looks, never types. The PreToolUse guard on attempt files is gone with them.
- **One timing rule:** a focus block counts from its start to its end (or now), at most its length. Activity tracking is gone (`solve touch`, the idle pause, the welcome-back, the UserPromptSubmit hook), because chat activity said little about quiet work on LeetCode. Idle time an older solve already paused out still counts as paused. `coach.py install` removes the retired hooks. After pulling this, start a new Claude Code session: a session still running the old hooks blocks edits, because `coach.py guard` no longer exists.
- **The learning app is read-only:** `app/server.py` serves Today (live solve, due, next), the map and Learn pages, and saved explainers, all from `coach.py map --json` (now with `due` and `live`). It answers every write with 405. Removed: the Solve tab, editor and test runner (`runner.py`, `attempt_file.py`), the LeetCode statement fetcher (`statement.py`), the panel's own coach chat and finish review (`companion.py`, `completion.py`), and the headless explainer job (`claude_job.py`). The explainer buttons now hand him a prompt to paste into the coach chat. Unsaved drafts from the old Solve tab can be downloaded from the page; they are never cleared.
- **The extension only frames the app:** permissions are the side panel, storage and the local server. No content scripts, no LeetCode access, no screenshots, no editor reading.
- **The pane shows state only:** problem, stage, timer, rung, due. No buttons, no attempt-file line, no eight-stage mapping.
- **One notebook lock:** every `coach.py` command that writes takes `sessions/.notebook.lock` (from `scripts/session_lock.py`, now folded into `coach.py`), so two agents can't hand out the same ID or overwrite each other's cards. Readers don't wait.
- **Imports are checked whole:** a delta with any bad part (a malformed list, a bad date, a review of a card that isn't active, a missing artifact file) is skipped before anything is written, and a delta whose rows were already imported is skipped too. A crash part-way through an import can still leave it half written.
- **Problem metadata:** a new solve takes its pattern and difficulty from an earlier attempt, then the problem list (`problems.json`), then the roadmap. Two Sum is easy, with a 15-minute block.
- **Removed migrations:** eight-stage solves, `--expected-session` and the legacy session identity. The only live solve already used the four stages and had a session id.

## 0.8.0 · 2026-11-09 · Four stages, and finishing in the panel

Fewer stages to navigate, more help with the thinking inside them, and a solve can be finished beside LeetCode. Design: `docs/superpowers/specs/2026-11-09-panel-completion-design.md` (approved with trims).

- **Four stages:** Understand, Find an approach, Build it, Check and finish, one for each of Polya's phases. The old stages 2–6 (brute force, count, repeated work, classify, plan card) are now teaching moves inside Find an approach. The coach asks the one that fits and doesn't make him fill in each one. `references/protocol.md` spells out the moves: find something that works, count the work concretely (uneven loops are added, hidden work counted), connect the count to the limit, improve only for a reason, and keep a short plan. Build it bridges the plan to code with one question at a time. Why (`learning-principles.md`): the four phases were already the frame, and eight visible stops were a burden that didn't add practice.
- **Old solves move over:** a live solve from before 0.8.0 maps stage 1→1, 2–6→2, 7→3, 8→4 (`protocol: 2` marks new ones). Notes from old stages 2–6 are joined into stage 2, each under its old name. Archived notes and logged attempts are unchanged. The pane maps an unmigrated solve the same way. Browser drafts saved before 0.8.0 can't be restored into the new stages; the recovery banner keeps them for copying.
- **Help me think:** every stage in the study app and the panel has a button that asks the coach for one question for that stage, without giving away the method.
- **Finish in the panel:** in stage 4 the panel asks for the outcome, a lesson and whether he used outside help. **Review attempt** sends these with his saved notes and the LeetCode code to a tool-less coach (`app/completion.py`). The coach either lists missing evidence or proposes the record: outcome (never better than his own), evidence, complexity credit and mistakes. **Save attempt** logs it through `coach.py solve end`, but only if nothing the review assessed has changed (a fingerprint of answers, notes, plan, examples, rung and code). Solved needs test evidence. The review lives in server memory, and a restart means reviewing again.
- **Ending twice logs once:** attempts from `solve end` carry `session`. Ending a solve that already logged an attempt (a double click, a lost response, a retry after an interrupted end) returns that attempt's receipt (`solve end --json`) and finishes any leftover cleanup. It never logs again and never touches a newer solve.
- **Not included (trimmed from the design):** multi-window conflict handling and Learn resource metadata.

## 0.7.0 · 2026-11-08 · Solve flow (extension 0.2.0)

Focus blocks count active time, coming back is a fresh start, and the panel's coach sees the page and records its hints.

- **Active time:** a block counted wall-clock time, so an open block read "1044 of 15 min" and ending the solve would have logged 2059 minutes. Now five quiet minutes stop the clock at the last activity, and the quiet time is paused out of the block (`paused` seconds per block, `last_active` on the solve). After 30 minutes away the block closes at the last activity and a fresh one starts (`resumed`). Breaks still go by his choice, as `learning-principles.md` asks: nothing is enforced.
- **Activity:** `coach.py solve touch` (and every solve command) records it. The study app touches on typing and clicks (at most once a minute, visible page only), the browser panel relays typing on the LeetCode tab, and a `UserPromptSubmit` hook touches on each chat message (`install` adds it).
- **Old solves:** blocks from before 0.7.0 are capped at the block length, so the live solve now reads 45 minutes, not 2059.
- **Welcome back:** after a long absence the app shows the stage and last note once, and the status line says "back at HH:MM, fresh block". The block-over banner no longer comes back after a reload.
- **The panel sees the page:** each message carries the code from LeetCode's editor and the end of the page. When that isn't enough, the coach replies `[[LOOK]]`; the panel takes a screenshot and asks again, once. Screenshots without a toolbar click need the optional all-sites permission (one button).
- **Panel hints on the ladder:** each reply ends with `RUNG: n`. The server strips it and records a higher rung with `solve hint`.
- **The pane** counts minutes by the same rule.

## 2026-11-07 · Browser companion 0.1.0

- **Browser extension:** `extensions/dsa-coach` adds a Chrome/Edge side panel beside LeetCode. App problem links can open it, and the toolbar opens it directly. The panel follows the current problem without replacing an active solve.
- **Coaching in the panel:** questions, saved stage answers, plan cards, examples and optional page text/screenshots go to the local Claude CLI. Replies appear in the panel. The coach has no tools and cannot modify code or execute tests. Coding and running remain in LeetCode; final attempt logging remains in the main coach chat.
- **Context capture:** selected/page text, visible-tab screenshots and pasted/uploaded PNG/JPEGs, reviewed before sending. Captures clear when switching problems and stay out of notebook files. Chat is temporary.
- **Embedding:** a dedicated `/companion` route permits only the pinned extension origin. Other pages retain frame denial and the existing API header checks.
- **Improve a theory page:** the panel's Learn cards and the app's Learn page can ask the coach to write a missing explainer, or to revise one: say what should change, and the coach rewrites the page in place (`POST /api/explainer` with `feedback`) and logs the feedback as a question. The form repeats `explainers.md`'s advice to attempt one problem first.
- **Verification:** server/input/extension tests and a Chromium integration check against a temporary notebook and fake Claude. Live text and image CLI transport smoke checks passed.

## 0.6.0 · 2026-11-07

The study app opens on a map of the roadmap. Each pattern has a Learn page, and Solve is one link away.

- **Map:** the home page. Patterns are laid out by roadmap week, each showing its status, Blind 75 and NeetCode 150 progress, and how many re-solves are due. A strip at the top names the next item from `coach.py next`, with its LeetCode link and a link back to a live solve. Foundations appears as three stubs, to be written for testers.
- **Learn pages:** one per pattern (`#/learn/<key>`), with cues, invariant, template, two or three resources, and the pattern's problems. Blind 75 problems come first, and each title links to LeetCode, with its status and next re-solve.
- **Catalogue:** `assets/problems.json` holds NeetCode 150 by roadmap pattern, with Blind 75 tagged. It adds Combination Sum IV (Blind 75's one problem outside NeetCode 150) and the prefix-sums canonical problems. `validate` checks it against the roadmap.
- **Resources:** each pattern in `roadmap.json` lists its resources. Every URL comes from `references/resources.md`, and a test keeps it that way.
- **`coach.py map`:** joins the catalogue with progress. The app reads `--json`; without the flag it prints one line per pattern.
- **Explainers from the app:** when a pattern has none, **Write the explainer** runs the coach headless (`claude -p`, one job at a time, five-minute limit) to write and register one, and the page checks on the job until it's done. Set `claude_bin` in `notebook/config.json` if `claude` isn't on the PATH. The explainer is served at `/explainer/<key>` in a sandbox, so its scripts can't call the app's API.
- **Solve:** unchanged, now at `#/solve`, with **Map** in the bar to return.
- **Browser check:** `tests/browser/check_map.py`, run by hand, drives the views with Playwright against a copy of the notebook and a fake `claude`.

## 0.5.2 · 2026-11-07

Practice saves, session ownership, and browser recovery.

- **Run:** saves pending code and stage examples before execution. A failed save or typing during preparation stops the run with a retry message. Late save responses preserve newer typing.
- **Session identity:** browser actions carry the solve they were started for; stale actions, including forced overwrites, cannot affect a replacement solve. The CLI accepts optional `--expected-session` on solve mutations while retaining existing chat commands.
- **Cooperating writes:** a bounded cross-process lock serializes solve mutations and app attempt operations. Content revisions detect external edits, including edits that preserve a file timestamp.
- **Draft recovery:** local browser drafts preserve code, stage fields, examples, plan cards, statement drafts, and finish fields. Restore is explicit and retains conflict checks; ended sessions are copy-only. Drafts do not count as notebook saves or completed attempts.
- **Portability:** POSIX locking is tested on macOS. The standard-library Windows branch is implemented but has not been runtime-verified on this host.

A calmer Solve tab (page only; the server, API and files are unchanged).

- **Layout:** two panes. On the left, the Description, Stage and Notes tabs. On the right, the editor above a collapsible console. The bar has the problem (its path on hover), eight stage dots with the stage's name, the timer, and Ask coach, Save and Run; unsaved code shows as a dot on Run. The hint rung appears once a hint is used.
- **Editor:** on load, the plan-card docstring, EXAMPLES and the run block fold into one-line markers. They are still in the file, and a fold he opens stays open across saves and polls.
- **Console:** Testcases shows a chip per EXAMPLES row, edge rows marked. After Run, Result gives a verdict and a pass/fail chip per case, with its input, error, output, expected value and stdout. Tracebacks keep only the attempt file's frames.
- **Description:** renders the fetched statement (examples as blocks, constraints as a list) and reads `problem.md` again each time the tab opens. A first load with no statement opens on it, with the fetch/paste flow.
- **Timer:** an overrun block reads "over by 9 h 47 min", not "593 of 15 min", and clicking it brings back the end-of-block choices after the banner is closed.
- **Start screen:** one card with the next pick. Pattern and the due line are under More options.
- **Design context:** `PRODUCT.md` records who the page is for and the principles it follows.

## 0.5.1 · 2026-11-07

The Solve tab fetches the problem statement.

- **Statement:** when a solve opens without a statement, the app asks LeetCode for that one problem (the GraphQL endpoint its own site uses) and saves it as plain text in `problems/<slug>/problem.md`: the title, the link, then the statement with its examples and constraints. One request per problem, never on a poll and never in bulk.
- **Fallback:** if the fetch fails (offline, the endpoint changed, a premium problem), the paste box appears with the reason and a **Fetch from LeetCode** retry button.
- **Certificates:** a Python with no root certificates of its own (python.org's macOS installer before "Install Certificates.command") fetches with `certifi` if installed, else the system's bundle (`/etc/ssl/cert.pem` on macOS), instead of failing with CERTIFICATE_VERIFY_FAILED.
- **Git:** `notebook/problems/*/problem.md` is ignored, fetched or pasted. Statements are LeetCode's text, and the repo is public.
- **Why:** pasting each statement was a chore on every new problem, and the app should stay out of the way of the solve itself.

## 0.5.0 · 2026-11-06

A study app for long solves: the Solve tab.

- **Study app:** `python3 app/server.py` opens a local page with a stage panel for the 8 stages, an editor without autocomplete (CodeMirror 5, with a textarea fallback) and a test runner. It is bound to 127.0.0.1, checks the Host, needs an `X-DSA-Coach: 1` header on API calls and can't be framed, so other web pages can't run code through it.
- **Stages:** stage 1 asks for a one-sentence restatement and predicted examples with at least one edge case; the examples become the tests. Stage 6 writes the plan card into the attempt file. Jumping ahead asks which stage he is in. The plan card before code is a nudge, not a lock.
  - The examples table never drops a row it can't read back, and a row or plan-card value that would break the file is refused.
- **Runner:** the examples run in a separate child process (`python -I`, no stdin) with a 5 s limit. A timeout or crash keeps the finished rows and names the example it stopped on.
- **Chat:** it stays in Claude Code or Codex. "Ask the coach" copies a prompt; the page re-reads the live solve every 3 seconds, so hints recorded in the chat show up there. Stage 8's Done copies a prompt with his outcome and lesson, and the coach logs the attempt with technique, mistake codes and the complexity check; parking ends a solve in the app. If the solve ends from the chat while he has unsaved code or stage text, a banner offers to copy it.
- **`coach.py`:**
  - `solve note --stage N --text T` keeps one note per stage; a blank text clears it. At `solve end` the notes go into the problem's `notes.md`, in a `## Stage notes` section just above `## Lessons`, one `### <date> (<file>)` block per solve.
  - `due --json`, which the app's start screen reads.
  - JSON files are written to a temp file and renamed into place, so a reader never sees half a file.
- **Attempt template:** LeetCode-shaped: the plan card with a hand-trace field, `class Solution` under `from __future__ import annotations` (so LeetCode's `List[int]` hints load), and `EXAMPLES` rows with `# edge` marks. `python3 file.py` prints ok or FAIL per example and stops at the first error with its traceback.
- **Limits:** examples are Python values (lists, numbers, strings, True/False/None), so linked-list and tree problems (`ListNode`, `TreeNode`) don't run in the app yet.
- **Python 3.9:** the app and its tests run on 3.9 and later, like `coach.py`.
- **Skill text:** in the app, the coach reads his notes and the attempt file instead of asking him to paste them, and ends the solve from stage 8's prompt with the full fields (SKILL.md, protocol.md); platforms.md says how to start it.
- **Why:** in the 2026-11-05 Binary Search solve he went straight to code, and the bug was the one-element case stage 1 predictions catch (protocol.md: predicting outputs before coding raised correct completion from 53% to 76% in a CS1 study). Hints stay in the chat, where the ladder asks which question he'd ask himself first: answer-giving help lowered exam scores in the field study behind rule 1.

## 0.4.1 · 2026-11-05

Package the existing DSA coach for reuse outside this workspace.

- Move runtime requirements from `compatibility` frontmatter into the skill body so both the notebook and skill-creator validators accept the package.
- Include `$dsa-coach` in the Codex default prompt.
- Document explicit notebook selection and initialization for an extracted skill, and distinguish the optional project hook from the skill's teaching instructions.
- Preserve the teaching protocol and separate notebook data, as described in `docs/research/`; no changes to learning schedules or scoring.

## 0.4.0 · 2026-11-05

Long solves, in an editor file and a pane beside the chat.

- **`coach.py solve`:** start, stage, hint, break, block, show and end keep the live solve in `notebook/sessions/current.json`.
  - `start` creates a blank attempt file, `problems/<slug>/<date>.py`, with the link, a short plan card and an examples block. A re-solve always gets a new file.
  - `end` logs the attempt. Minutes come from the focus blocks and hints from the highest rung.
  - `--unlabeled` keeps the pattern out of the file, `solve show` and the status.
- **Status:** `status` prints the live solve, so the SessionStart hook brings it back after a compaction or in a new session.
- **Guard:** `coach.py guard`, a PreToolUse hook that `install` adds, blocks Claude's Write and Edit on the live problem's `.py` files until hint rung 7. Rule 1 is now enforced, not only asked.
- **Coach pane:** `plugins/dsa-coach-pane`, a Claude Code plugin, shows the problem, the stage, the focus-block timer and the hint rung beside the chat. Its buttons send prompts to the coach: check my code, stage done, next hint, block over.
  - It names the pattern only for labeled problems.
  - It announces a finished block once.
  - It installs from the workspace's own marketplace (`.claude-plugin/marketplace.json`).
- **Skill text:** SKILL.md, the practice mode, `/practice` and platforms.md run every solve through `coach.py solve`.

## 0.3.0 · 2026-11-05

Principles from *Learning How to Learn*, *How to Solve It* and "Programming as Theory Building" (docs/research/learning-principles.md).

- **Solve protocol:** the eight stages sit under Polya's four phases. Stage 8 is now "test and look back": why the solution works in one sentence, plus one rotating question (another approach, a changed constraint, or another problem).
- **Hint ladder:**
  - It starts with "which question would you ask yourself?"
  - Rung 1 is a general Polya question (table in references/protocol.md).
  - A leading question counts as the rung it gives away.
- **Attempts:**
  - A genuine attempt is one focused block of about 25 minutes.
  - When a block ends unsolved: a short break, then another block, the next rung, or park it until tomorrow (`partial` with a `parked:` note).
- **Reviews and mocks:** both add a changed-constraint question. Mock mode gets an OA variant (2–3 problems, hard start, jump to easy).
- **Plan card:** new Relies on and Breaks if lines, and the invariants table says what each pattern relies on.
- **Keep it simple:**
  - New rule 8.
  - AI drills can plant needless complexity, and the learner turns down suggestions that don't fit the plan card.
  - Machine coding abstracts only around likely changes.
- **`coach.py next` interleaves:**
  - A pattern's first three problems stay together.
  - After that, new problems rotate across started patterns, least recently practised first, with `block: false` so the coach presents them unlabeled.
  - A new pattern starts when its week arrives.
- **Retrieval:**
  - After an explainer, the core idea goes into the concept notes in the learner's own words.
  - After a linked resource, recall comes before discussion.
  - An attempt is offered before more examples or animation.
- **Sessions:** planned in 25-minute blocks, and each ends by agreeing when the next block happens.

## 0.2.0 · 2026-11-01

One-step practice.

- `/practice` command and practice mode: one item, no opening report. Takes an optional pattern or problem.
- `coach.py next`: picks inbox, due re-solves, due cards, then a new problem in plan order. Long formats are never picked.
- `status` and JOURNEY.md use the same pick, and practice comes before draft approval.

## 0.1.0 · 2026-10-30

First version (build step 1: core).

- Skill: rules for every mode, session start and end, eight modes, the eight-stage solve protocol, the hint ladder, adaptation by measured mastery.
- References: protocol and rubrics, plan card and fading ladder, explainer rules and the trace-first pipeline, learner model and evidence rules, retention (cards, schedule, quizzes), 12-week roadmap, resources, platforms and the session delta format.
- coach.py: init, status, log (attempt, question, session), concept, card (add, accept, edit, retire, review, list), quiz, due, artifact, snapshot (JOURNEY.md, journey.json, summary.md, technique ledger), export, import, package, install (links and Claude Code hook), validate.
- Notebook seeded with the sliding-window explainer, the questions asked so far and six draft cards.
