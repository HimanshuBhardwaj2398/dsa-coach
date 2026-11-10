# DSA Coach improvement plans

## 2026-11-10 simplification

The user confirmed: keep the learning map, saved explainers and review progress; remove solving and browser integration. [Whole-app critique](2026-11-10-app-critique.md) records evidence, rationale, rejected alternatives and audit limits.

| Plan | Status | Purpose |
|---|---|---|
| [002: Learning app](002-learning-app.md) | DONE (0.9.0, branch simplify-0.9) | Read-only map/Learn; remove local solving and headless coach |
| [003: External coaching](003-external-coaching.md) | DONE (0.9.0, branch simplify-0.9) | File-independent sessions, explicit timing, notebook coordination and updated skill |

Implemented by Claude on 2026-11-10 in the main workspace (the executor worktrees in /private/tmp had stopped part-way and were left untouched). Where it departs from the plans, at the user's request: the Chrome side panel and the Claude Code pane are kept, cut down to read-only views (the panel frames the app's `/panel` page; the pane has no buttons). Timing is one rule rather than two: a block counts from its start to its end or now, at most its length, so `solve end` still logs minutes. Checks: 65 Python tests, 7 Node tests, 6 pane tests, `tests/browser/check_app.py`, and `coach.py validate`.

002 and 003 have disjoint implementation scopes and integrate together. They supersede the unfinished browser QA and future solve-surface work in 001; its historical implementation review remains below. Baseline verified: 172 Python tests and 33 Node tests passed. Notebook contents are protected with before/after hashes; no study attempt is being logged during this engineering task.

The user authorized implementation and selected the product scope, so these plans proceed directly to execution and review without another selection/approval round.

## Previous review

Prepared 2026-11-07 using the improve skill. The user accepted the review's offer of a plan without choosing a track; reliability is first because it protects practice work and supports subsequent UX changes.

| Plan | Priority | Effort | Dependencies | Status |
|---|---|---|---|---|
| [001: Make practice saves and session actions reliable](001-practice-reliability.md) | P1 | L, several focused implementation steps | None | IN PROGRESS: implementation applied; full browser QA remains |

Implement and verify each step before moving on. Update this index only after verification; permitted statuses are TODO, IN PROGRESS, DONE, and BLOCKED with a reason.

## Follow-on direction

After 001, design the Today screen (resume first, one recommended review, one new problem), then group the eight learning stages under Understand / Plan / Code / Reflect, then add a dedicated review flow. These are future design tasks, not implementation authorization within plan 001.

## Considered and deferred

- Framework migration and a database: no demonstrated need for this single-user local app.
- Embedded coach chat: external chat deliberately uses existing subscriptions; keep its current integration.
- Automatic coach grading or logging from the browser: the coach still judges technique, mistakes, and complexity.
- Broad redesign and new learning rules: preserve the research-backed protocol while fixing mechanics.
- Fetch integration: now committed in release 0.5.1 (`a9ee6fc`); preserve it.
- Arbitrary external editor synchronization: cooperating app/CLI operations can be locked; arbitrary editors cannot be made transactional without their cooperation. Detect conflicts and retain recoverable drafts.

## Review baseline

The initial review observed an in-progress fetch change. This plan targets the subsequent committed release `a9ee6fc`, not that intermediate snapshot. Notebook changes already exist and belong to the learner. Do not include them in implementation commits.

Verified during planning: all 116 Python tests passed; `coach.py validate` passed for v0.5.1. An unscoped `git diff --check` reports existing Markdown trailing spaces in `notebook/JOURNEY.md`; leave that generated learner file alone and scope patch checks to implementation files.

Implementation and verification results are recorded in [001 implementation review](001-implementation-review.md). All three implementation steps are applied to the main workspace without committing or pushing. Automated verification is green; the plan remains IN PROGRESS because its full browser smoke criterion has only been partially verified.
