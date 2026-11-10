# 003: Make coaching sessions independent of local editors

Planned at `eee3d4c`, 2026-11-10. P1, effort M, risk MED. Status: IN PROGRESS. No dependencies; integrate together with 002.

## Why and current evidence

User will always code/test on LeetCode and use the existing computer-use agent for observation. `coach.py:1339` currently creates a Python file for every solve, `:1397` uses it as note identity, and protocol/platform references tell the coach to inspect it. `:1285` infers attention from activity events that the removed extension supplied. `:1347` ignores catalogue metadata. Imports can mutate attempts before rejecting draft-card reviews (`:1649`, `:1685`, `:1696`), and direct writers do not share solve's lock.

## Scope

Only `skills/dsa-coach/`, `.claude/settings.json`, `.claude/commands/practice.md`, `tests/test_coach.py`, `tests/test_stages.py`, `tests/test_catalogue.py`, optional new `tests/test_import.py`, `docs/CHANGELOG.md`, `docs/cowork-project-instructions.md`. No notebook edits, app/, plugins/, extensions/, root product docs, plans/ or research edits. Read docs/research and writing-for-agents skill before changing skill instructions. Main reviewer owns packaging in the main workspace after integration.

## Steps

1. Work in isolated worktree from eee3d4c. New sessions identify problem URL, session ID, stage, highest hint, notes and focus blocks without generating a local attempt Python file. Remove scaffolding template if unused. Legacy live sessions with file fields continue to show/end/discard; never delete historical files. Stage-note identity uses session ID with legacy compatibility. Keep idempotent solve end.
2. Resolve metadata explicit override → prior attempt → existing catalogue → fallback; include noncanonical catalogue problems. Don't add a new metadata store.
3. New sessions use explicit start/break/block/end elapsed timing rather than hidden activity inference. Preserve historical stored timing for legacy sessions; describe elapsed blocks honestly and require learner-confirmed `--minutes` before using duration as performance evidence if needed. Remove automatic UserPromptSubmit touches and file edit guard installation; remove dead guard CLI if no retained consumer. Preserve existing unrelated hook settings. Keep SessionStart status hook. Don't recreate telemetry through computer-use screenshots.
4. Map JSON keeps existing fields and adds `due` with resolves/cards/drafts arrays from the existing computed model, plus `live` read-only session metadata (or null). No mutation or new scheduling logic on map reads. App executor consumes these.
5. Update skill/protocol/platform/practice docs: code on LeetCode, observe via available computer-use tools only when useful/requested, distinguish partial visible evidence from complete code/result; if unavailable request the missing code/result text. No hardcoded selectors, scraping, extension or local attempt requirement. Keep attempt-before-answer, hint ladder, four phases, prediction and delayed unaided retention. Explain creation/revision of saved explainers in normal agent conversation. Bump SKILL.md and SKILL_VERSION to 0.9.0; changelog records reasons and scope.
6. Fix notebook write coordination at the CLI mutation entry seam using existing lock without nesting solve locks. Cover concurrent direct attempt/card writers with tests. Fix known import validation failures before writes (card status, dates, artifact source existence/types and malformed shapes), and repeat-import handling if it can be done without a storage redesign. Explicitly report residual crash-atomicity limitations; do not claim full transactional imports from prevalidation alone. Preserve all existing data formats/records. If import fix becomes a broad storage rewrite, stop that substep and document exact remaining issue for reviewer instead of adding a framework.

## Verification

Run `python3 -m unittest discover -s tests` and `python3 skills/dsa-coach/scripts/coach.py validate`, scoped `git diff --check`. Baseline 172 Python tests passed. Add tests: no new attempt .py; old session with file can finish and preserve it; stage notes survive; long no-chat explicit block counts elapsed; break excludes time; catalogue metadata; map due/live; concurrent writer IDs/cards preserved; rejected import writes nothing; repeated explicit import safe if implemented. Old app tests in this worktree may assume attempt files; report those expected failures since 002 deletes that product slice, but all retained core tests must pass.

## Git, stop and maintenance

Create temporary worktree branch `simplify/external-coaching`. Do not commit/push/merge or edit main workspace. Return path, changes, checks and residual risks. If learner data requires migration writes or teaching evidence rules would change, stop and report. Keep stdlib and one canonical scheduler. Avoid decomposing the CLI just because it is long; delete obsolete responsibilities first.
