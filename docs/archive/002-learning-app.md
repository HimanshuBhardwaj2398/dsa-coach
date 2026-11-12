> **Archived.** Done in 0.9.0. Kept for history: paths inside are as they were when it was written.

# 002: Keep a learning app, remove the solving infrastructure

Planned at `eee3d4c`, 2026-11-10. P1, effort M, risk MED. Status: IN PROGRESS.
User explicitly selected: keep learning map, saved explainers and review progress; remove solving and browser integration. This supersedes the old product brief and the remainder of plan 001.

## Why

The 219-line Map/Learn module depends on a 1,366-line solve frontend. Hidden solve initialization still loads attempts, polls and records activity. LeetCode owns coding/testing; the agent conversation owns observation and teaching. The app should read the notebook and open learning material, not implement those other responsibilities.

## Current state and conventions

- `app/static/nav.js:2` imports globals from app.js; `show` has no stale-request guard; line 69 links to `#/solve`.
- `app/server.py:526` has 24 route registrations spanning file editing, execution, fetching, chat, completion and learning. Preserve loopback/Host/header checks and sandboxed `/explainer/<key>` serving.
- `app/static/app.js:1191` supports recovery of `dsa-coach:draft:` localStorage values. Keep their raw content recoverable; do not erase browser storage.
- `app/server.py:303` launches Claude for explainers. Replace this with a visible/copyable prompt for the user's existing agent, retaining saved HTML serving.
- Existing vanilla JS uses textContent/DOM creation and Python uses stdlib only. Keep these choices. No framework, database, dependencies or generic provider interface.

## Scope

Only `app/`, `extensions/`, `plugins/`, `.claude-plugin/`, `tests/test_server.py`, retired tests `tests/test_attempt_file.py`, `tests/test_runner.py`, `tests/test_statement.py`, `tests/test_companion.py`, `tests/test_completion.py`, `tests/test_claude_job.py`, `tests/frontend/`, `tests/browser/`, `README.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `docs/PLATFORMS.md`, `docs/DSA-COACH-WALKTHROUGH.md`, `docs/dsa-coach-*` diagrams.
Do not touch notebook/, skills/, .claude/, AGENTS.md, CLAUDE.md, docs/research/, changelog or plans/. A separate executor owns the skill. Its map response will add `due` with arrays `resolves`, `cards`, `drafts`, and `live` as read-only current session metadata (or null). Handle those fields missing while this plan is tested alone. Existing map fields remain.

## Steps

1. In an isolated worktree from eee3d4c, replace app.js with small helpers/recovery export and make nav.js independent. Map defaults on old solve hashes. Remove local solve, editor, activity, save, prompt-to-check-local-file and companion UI. Keep 22 topics, lists, direct external problem links, cues/invariant/template/resources, saved explainers and recommendation. Show review counts, due problem links and existing live session as a link to LeetCode plus a short instruction to resume in agent chat. Avoid teaching hints in an unlabeled next recommendation. Remove nonfunctional foundations stubs.
2. Give the page a clear Learning map title and normal responsive reading layout. Preserve native keyboard focus, light/dark system theme, error/retry/loading states. Refresh on focus and explicit button; avoid continuous polling. Ignore stale responses. Refresh must not overwrite a handoff prompt the user is selecting/editing.
3. Keep existing explainer links. Add small prompt handoff for creation/revision using the skill and notebook, with clipboard success/error and visible manual-copy fallback. Do not pretend a copied prompt created an artifact. Explain in the prompt to save/register using coach.py. No Claude subprocess or model-specific installation.
4. Reduce server to static, GET map and sandboxed registered explainers; all mutations and deleted routes return an appropriate non-success response. Remove imported deleted modules, extension framing exception and temporary chat state. Delete runner, attempt parser, statement scraper, companion/completion/job modules and prototype; delete extension, pane and marketplace manifests. Preserve notebook files and legacy sessions without migration writes.
5. Export old localStorage draft keys as a downloadable JSON object containing raw values only when present; never parse/drop/clear them, including malformed drafts. Explain exports work at the original localhost origin/port. Ensure no fetch or notebook mutation is used for recovery.
6. Rewrite current docs around the new workflow. Historical specs/research stay historical; obsolete generated overview diagrams may be removed if inaccurate. Document test commands and legacy recovery. Replace deleted tests with retained behavior tests, including stale navigation, review/refresh/handoff/recovery and HTTP containment/retired routes. Adapt browser smoke test to new app; no browser automation needs to run in executor (reviewer uses approved computer-use tools).

## Verification

Baseline: 172 Python and 33 Node tests pass. Run `python3 -m unittest discover -s tests`, `node --test tests/frontend/*.test.cjs`, `python3 skills/dsa-coach/scripts/coach.py validate`, and scoped `git diff --check`. Expected exit 0. Browser verification by reviewer: map → Learn → saved explainer; request prompt visible/copyable; refresh; legacy solve hash returns map; no editor/capture controls.
Search app/ for `CodeMirror`, `monaco`, `/api/run`, `/api/solve`, `/api/coaching`, `claude_bin`: no live implementation matches. External leetcode links remain intentionally.

## Git and stop conditions

Use a new temporary worktree and branch `simplify/learning-app`; do not commit, push, merge, or change the main workspace. Return worktree path plus exact verification. If notebook contents must be changed, stop. If deletions lose existing learner artifacts or the new map requires a database/framework, stop. If checks fail twice, report exact failures. Reviewer will inspect and integrate the authorized patch.

## Maintenance

Keep the HTTP surface read-only. Add notebook behavior through the CLI, not frontend copies of its scheduler. A browser screenshot is an observation, not an automatic solved/unaided grade.
