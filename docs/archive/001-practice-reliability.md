> **Archived.** Superseded by plans 002 and 003 (0.9.0). Kept for history: paths inside are as they were when it was written.

# Plan 001: Keep practice work safe and run the examples currently shown

> Follow the steps in order and run each verification gate. This is an implementation handoff, not a record of completed changes. Preserve existing learner work. Update `plans/README.md` only after verification.
>
> First run `git diff --stat a9ee6fc..HEAD -- app skills/dsa-coach tests docs/CHANGELOG.md` and `git diff -- app skills/dsa-coach tests docs/CHANGELOG.md`. Compare any changes with the excerpts below. Do not overwrite intervening work or assume the planned-at commit includes uncommitted changes.

## Status

- Priority: P1
- Effort: L; deliver as three independently verified implementation steps
- Risk: MED; saving, session ownership, and draft recovery interact
- Depends on: none
- Category: bug / reliability
- Planned at: `a9ee6fc`, 2026-11-07, release 0.5.1

Execution reconciliation: the main checkout has concurrent certificate fixes in `app/statement.py`, `tests/test_statement.py`, and a v0.5.1 changelog bullet. They do not change this plan's contracts. Implement in `/tmp/dsa-coach-reliability` on `advisor/001-practice-reliability`; preserve those fixes when transferring reviewed changes, especially the changelog. Windows runtime verification is unavailable on this macOS host; implement its lock branch and explicitly report that platform as unverified, without blocking macOS completion.

## Why this matters

Clicking Run after changing an example currently executes the older saved example. Browser actions also target whichever solve happens to be live when the server processes them, so an old tab can affect a replacement session. Unsaved code and stage answers have warnings, but do not survive a tab crash. The intended result is straightforward: Run uses the visible inputs, actions stay attached to their original session, and interrupted work can be recovered without overwriting newer work.

## Current state and conventions

The app is a local Python standard-library server with vanilla JavaScript and optional CDN CodeMirror. `coach.py` owns official learner records. The server writes attempt files and statements; the browser never writes learning records directly. Keep this split and retain the textarea fallback.

- `app/static/app.js:296`, `runTests()`:

  ```js
  if (dirty && !(await save())) return;
  $("results").innerHTML = "<p class='muted'>Running…</p>";
  try {
    renderResults(await api("POST", "/api/run", {}));
  ```

  `savePanel` collects the displayed stage fields, writes changed examples or plan fields through `saveParts`, then records the stage note. `change()` serializes mutations from this browser, but not from other tabs or CLI processes. `saveParts()` installs the returned file with `useAttempt()`, which can replace editor text typed while the request was in flight.

- `app/server.py:154`, `put_attempt()`:

  ```python
  live = live_solve(coach)
  return write_checked(coach.root / live["file"], live, need(d, "text", str, blank_ok=True), d)
  ```

  Stage, note, break, block and end routes similarly carry no expected session identity. `WRITE = threading.Lock()` only serializes attempt writes in this server process. It cannot protect the separate coach CLI.

- `skills/dsa-coach/scripts/coach.py:1243`, `cmd_solve()` loads the current solve, edits it, then calls `write_json(root / LIVE, live)`. Atomic replacement prevents partially written JSON, but does not serialize a read-modify-write transaction across processes.
- `app/server.py:91`, `read_attempt()` reads text and subsequently calls `path.stat()`; a replacement between these operations can pair old content with a new mtime.
- `app/static/app.js:770` registers a `beforeunload` warning for `dirty || panelDirty || statementDraft()`. There is no persistent draft store. Stage 8 outcome and lesson are separate fields, not durable stage-note data.

Match existing conventions: `ApiError` becomes a JSON error with an HTTP status; frontend failures use `banner()` / `fail()` with text content, not interpolated HTML. Use `tests/test_server.py`'s `ServerTest` temporary notebook and localhost ephemeral port, and `tests/test_coach.py`'s subprocess CLI fixtures. Never test against the real `notebook/`.

Learning constraints from the approved Solve design and `docs/research/learning-principles.md`: preserve attempt-before-answer, plan-card nudges, hint tracking, and coach-owned completion. Saving must not advance a stage, count as a successful attempt, or award retention credit. The user explicitly prefers simplifying rules over adding teaching bureaucracy.

## Scope

Only modify these implementation paths as required:

- `app/static/app.js`, `app/static/index.html`, `app/static/app.css`
- `app/server.py`
- `skills/dsa-coach/scripts/coach.py`
- `skills/dsa-coach/scripts/session_lock.py` (new, if needed for shared locking)
- `skills/dsa-coach/SKILL.md` (version only), `skills/dsa-coach/references/platforms.md` (new CLI/behavior documentation)
- `tests/test_server.py`, `tests/test_coach.py`
- `tests/frontend/practice.test.cjs` (new dependency-free Node test harness)
- `docs/CHANGELOG.md`, `plans/README.md`
- `dist/dsa-coach.zip` only as generated by the required package command

Do not edit the real notebook, change scheduling or teaching rules, replace CodeMirror, install a frontend framework, change fetch behavior, integrate a model API, or alter runner comparison semantics. A database and a general application-wide locking framework are outside scope.

## Commands

Run from the repository root. Python and Node are available; Node was v26.13.0 at planning time. No package installation is required.

| Purpose | Command | Expected result |
|---|---|---|
| Existing baseline | `python3 -m unittest discover -s tests` | All tests pass |
| Frontend syntax | `node --check app/static/app.js` | Exit 0 |
| New frontend tests, after creation | `node --test tests/frontend/practice.test.cjs` | All tests pass; no skipped tests |
| Server regressions | `python3 -m unittest discover -s tests -p test_server.py` | All tests pass |
| CLI regressions | `python3 -m unittest discover -s tests -p test_coach.py` | All tests pass |
| Skill validation | `python3 skills/dsa-coach/scripts/coach.py validate` | Exit 0 |
| Release package | `python3 skills/dsa-coach/scripts/coach.py package` | Exit 0; package generated |
| Patch hygiene | `git diff --check -- app skills tests docs plans` | Exit 0 |

## Git workflow

Use an isolated implementation branch, for example `advisor/001-practice-reliability`. The working notebook is already dirty; do not reset, stash, or commit its files. Prefer one reviewable unit per step, following existing messages such as `app: the coach logs the attempt; stage 8 copies the finish prompt`. Do not commit, push, or open a PR unless requested by the operator.

## Step 1: Save the visible examples before running

1. Add `tests/frontend/practice.test.cjs` using Node's built-in `node:test`, `assert`, and `vm`. Evaluate the actual `app.js` without firing DOMContentLoaded, with minimal document/window stubs. Inject controlled collaborators into the VM for the workflow under test; do not duplicate the production orchestration or assert source strings.
2. In `runTests`, save dirty code, collect/save pending stage data, and only then call `/api/run`. On any save conflict or validation failure, do not run. Do not advance the stage. Statement fetching is independent and must not block running code.
3. Avoid losing typing during save requests. Track an editor generation or captured text when a parts save starts. Apply a returned file to the editor only if the editor has not changed since that capture; otherwise preserve the newer buffer, mark it unsaved, and retain the server revision for conflict handling. Stop the pending Run with a clear retry message if code or test inputs changed during preparation; do not silently run a mixed revision.
4. Add controlled-promise tests: code-only edit; example-only edit; code plus examples; save failure; invalid examples; typing while a parts request is pending; repeated clicks; no stage advancement. Assert request ordering and that `/api/run` is never called after an unsuccessful preparation.

**Verify:** `node --test tests/frontend/practice.test.cjs`, `node --check app/static/app.js`, and the server regression command above all exit 0.

## Step 2: Bind every solve action to its session

1. Add an opaque `session_id` to newly started solves. For legacy `current.json` without it, expose a deterministic identity derived from the stored attempt path and start timestamp, so repeated reads are stable without mutating the file. Preserve existing JSON fields and CLI behavior for callers without an expected identity.
2. Add optional `--expected-session` to CLI solve mutations (stage, hint, note, break, block, end). Validate the identity inside the same cross-process critical section as loading and mutating the live solve. Serialize start/end and other solve mutations against that same lock, including legacy CLI callers. Reject a mismatch before writing files, logging an attempt, or deleting the current solve. Extend the server's CLI error mapping to return 409 for this mismatch.
3. Use a shared standard-library file-lock helper under the skill scripts directory so the packaged CLI remains standalone. Lock a stable file under `sessions/`; release with context-manager cleanup on errors. Implement platform handling explicitly (POSIX and Windows stdlib locking), with bounded acquisition and a useful timeout error. Avoid nesting the same lock across server-to-CLI subprocess calls: CLI record mutations acquire it inside the child; direct attempt operations acquire it in the server and read the current JSON within the protected operation.
4. Require expected identity for browser attempt reads/writes, parts writes, run requests, and solve mutations. Capture it when the user initiates an action, before it waits in `change()`; never substitute a later `state.live` when the queued callback runs. `force: true` bypasses a same-session content conflict only, never the session check. Start and slug-addressed statement endpoints retain their distinct contracts.
5. For Run, validate and capture the attempt path under the session lock, then release it before executing learner code. Return the identity with results and ignore results belonging to an obsolete session. Return identity with attempt responses too; discard mismatched poll responses rather than displaying one session's code with another session's header.
6. Fix the read/revision pairing: read content and metadata from the same descriptor, retry if metadata changes during the read, and include a string content revision such as SHA-256 in the response. Compare the expected content revision when saving. Retain old mtime fields for display/backward compatibility, but use the string revision for new browser writes. The server lock protects cooperating writers; external editors remain best-effort conflict detection, not guaranteed transactions.
7. On stale-session errors, preserve unsaved content and refresh the live state. Explain that the previous solve ended or changed. Never replay the old operation automatically onto the new solve.

**Test:** Extend temporary-notebook integration tests to start A, capture its identity, end A, start B, then submit every old mutation and force overwrite. Assert 409 and byte-for-byte unchanged B state, attempt file and attempt log. Verify legacy CLI calls still work, missing browser identity fails, legacy sessions get stable identities, and same-session content conflicts still work. Use deterministic barriers or held locks for concurrent mutation tests, not timing-only sleeps. Verify independent note and hint mutations both survive; lock timeout does not write anything. Simulate file replacement between read and stat to verify content and revision remain paired. Frontend tests must cover a queued A action after B appears and late A responses.

**Verify:** CLI, server, and frontend regression commands above all exit 0. Run the full Python suite before proceeding. Confirm lock behavior on each supported platform before claiming that platform verified; report unavailable coverage explicitly.

## Step 3: Recover unsaved work after reload

1. Add a versioned local draft record keyed by a stable notebook identifier plus session identity. Expose a hash of the canonical notebook path from `/api/state` for namespacing; do not use the port as notebook identity. Browser storage is origin-scoped, so explain that changing the app port does not migrate drafts. Cross-port recovery is outside scope.
2. Persist code, base revision, viewed stage, stage fields by stable field name, example rows including edge flags, plan-card values, statement draft, and stage-8 outcome/lesson. Persist updates after a short debounce and flush on visibility change/pagehide where possible. This is draft persistence, not automatic notebook saving. Use structured values, not rendered HTML or label text as schema keys.
3. On load, show an inline recovery choice when a different local draft exists: restore locally, copy for safekeeping, or discard. Never automatically overwrite a changed disk version. Restore only a matching notebook/session; provide copy-only recovery for ended sessions. Keep draft and server-save status distinct.
4. Clear saved fields only when their exact captured generation was acknowledged by the server. Code saved successfully must not erase unsaved notes, statement text, or finish fields. Finishing a session must not delete unacknowledged drafts. A malformed/unsupported draft, unavailable storage, or quota failure must leave normal editing functional and show that recovery is unavailable.
5. Add frontend tests for serialization/restore of every field category, separate sessions/notebooks, newer disk revision, late save acknowledgements, partial saves, ended-session copy-only recovery, corrupt JSON, unsupported versions, and storage exceptions. Keep the existing unload warning.

**Verify:** frontend tests and `node --check app/static/app.js` pass. On a disposable notebook, manually test reload recovery in both CodeMirror and textarea fallback; confirm actual example rows, edge flags, notes and finish fields survive. Record the browser and results in the implementation report. Do not use the learner's active solve for this check.

## Release and done criteria

- [ ] All regression commands pass, including the full Python suite and new Node tests; report counts.
- [ ] Run executes saved versions of the visible code/examples, or explains why it could not run.
- [ ] Stale-session tests assert no changes to the replacement session, including forced saves and end actions.
- [ ] Controlled asynchronous tests demonstrate that new typing survives late save responses.
- [ ] Draft tests cover every field category and failure case listed above.
- [ ] Browser recovery smoke check completed on a disposable notebook; untested platforms explicitly named.
- [ ] Review the change against `docs/research/learning-principles.md`: no new stage gates, grading rules, or answer reveals.
- [ ] Because the CLI skill changes, bump `metadata.version` and `SKILL_VERSION` together from the latest version to the next appropriate release (0.5.2 if 0.5.1 remains current). Update `docs/CHANGELOG.md` and platform instructions, run validate, then package.
- [ ] `git diff --check -- app skills tests docs plans` passes and the implementation diff contains only scoped files; pre-existing notebook changes remain untouched. Existing generated Markdown trailing spaces outside this scope are not a reason to edit learner files.
- [ ] Update `plans/README.md` to DONE only when all required verification is complete.

## STOP conditions

- Relevant source behavior has changed since this plan; reconcile the plan before editing.
- The existing baseline fails for an unrelated reason; report it rather than expanding this patch.
- The proposed lock would be held by a parent while its child tries to acquire the same lock.
- A solution needs a framework, dependency installation, notebook hand edits, or a change to learning policy.
- Two attempts to fix a failing verification gate do not resolve it; report the blocker with the failing command.
- An unavailable runtime or platform prevents required verification: report the limitation, do not mark that verification complete.

## Maintenance notes

Future Today/review screens must carry session identity and use the same save/recovery workflow. Future fields need draft-schema coverage. Keep standalone packaged-skill tests when changing imports, and preserve the distinction between draft recovery and official learner records. A full app service-layer refactor, cross-port draft migration, generalized locks for unrelated card/import commands, and an improved completion screen are deferred.
