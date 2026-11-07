# DSA Coach improvement plans

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
