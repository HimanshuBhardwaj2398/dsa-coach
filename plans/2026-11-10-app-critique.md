# App and architecture critique, 2026-11-10

Baseline eee3d4c, skill 0.8.0. User decision: keep the learning map, saved explainers and review progress; solve on LeetCode, with the existing agent observing through computer use.

## Verdict

The product expanded from a portable coach and durable notebook into a miniature practice site plus a browser extension plus a second AI chat runtime. Most maintenance complexity lives in those duplicated responsibilities. The useful core is the learning record, review selection, teaching protocol, problem catalogue and saved explainers.

Keep a small read-only learning app and one deterministic notebook writer. LeetCode owns the editor and judge. The agent owns teaching and observation. Computer use is a capability of that agent, not another integration to implement in this repository. Screenshots can be incomplete; never infer an accepted submission or unaided success from missing evidence.

## Vetted findings

Evidence refers to the pre-change baseline. Effort S = hours, M = roughly a day, L = multiple days. All findings are high confidence unless stated otherwise.

| Priority | Finding and evidence | Impact | Effort / risk | Decision |
|---|---|---|---|---|
| 1 | Local solving is an obsolete vertical slice: app/server.py:200, app/static/app.js:1330, index.html:108 | Editor, source parsing, test runner, fetching, autosave/conflict recovery serve a workflow the user rejects | M / medium, preserve data | Delete in 002 |
| 2 | Map/Learn depend on solve globals: nav.js:2,52,69; app.js:1285,1365 | Learning views load attempts, poll state and mark theory browsing as solving activity | S / low | Decouple and remove polling in 002 |
| 3 | Separate browser capture and restricted Claude chat: server.py:357, companion.py:26, extension sidepanel.js:63 | Duplicated context transport, coach prompts and lifecycle | M / medium | Delete extension and runtime in 002 |
| 4 | Missing hint metadata is accepted: companion.py:99, server.py:399 | Assistance can be shown without increasing recorded hint level | S / low | Removed with redundant coach |
| 5 | Rendered Monaco lines are treated as complete code: sidepanel.js:69–80 | Viewport-only text can be assessed as a full solution | S / low | Remove capture adapter; describe partial observations honestly |
| 6 | Finish-review inputs are unlocked before completion: server.py:418–437,486–512 | Same-session changes can escape the stale-review check | M / medium; code-confirmed, no concurrency reproduction | Remove duplicate finish system |
| 7 | Route requests race: nav.js:48–61 | Previous topic can overwrite current route; reproduced with reversed response order | S / low | Fix in 002 |
| 8 | Progress refresh depends on navigation: nav.js:57,218 | External agent updates do not update visible map | S / low | Explicit/focus refresh in 002 |
| 9 | New solve requires a local Python file: coach.py:1353–1372,1397 | Empty/stale second representation after moving coding to LeetCode | M / medium | Remove requirement, preserve legacy files in 003 |
| 10 | Time inferred from chat/browser events: coach.py:1285,1310; .claude/settings.json:25 | Quiet LeetCode work disappears; unrelated chat can count | M / medium | Explicit focus blocks for new sessions in 003 |
| 11 | Import validation permits late failure: coach.py:1649,1685,1696,1703 | Valid attempt plus draft-card review partially imports; retry duplicates attempt, reproduced in temporary notebook | M / medium | Preflight/retry protection in 003; audit residual crash limits |
| 12 | Direct notebook writers lack shared lock: coach.py:883,1034,1502 | Concurrent agents can allocate duplicate IDs or overwrite cards/artifacts | M / medium; control-flow confirmed | Coordinate mutations at CLI seam in 003 |
| 13 | Session metadata ignores catalogue: coach.py:1347,1351 | Two Sum defaults to medium/25 minutes; noncanonical catalogue problems need manual pattern | S / low | Use existing metadata in 003 |
| 14 | Product/setup docs describe retired workflow: PRODUCT.md:9,13; README.md:108 | New contributors rebuild the wrong product and miss frontend checks | S / low | Replace active docs alongside removal |

## Product and interface critique

Inspected a copied notebook in Chrome at localhost. The map is readable, but its header still names an active solve and timer; a blue welcome-back banner interrupts browsing theory. There are two competing actions for the same problem, “Open on LeetCode” and “Resume” in the local editor. Nonfunctional foundations cards get the first column. Ten weeks extend horizontally, making later topics require sideways exploration.

The learning page has useful substance: cues, invariant, compact template, resources and problem statuses. Keep this. Give it a learning identity, put the next useful action and review counts first, make weeks fit normal page flow, and eliminate unavailable foundations placeholders. Saved explainers should remain one click away. A generation button must say when it is handing a prompt to the external agent rather than promising an in-app background job.

The old map's solve title and timing are misleading even when visually muted. Removing them is a purpose correction, not a cosmetic redesign. Retain system typography and system light/dark themes; no new design framework is justified.

## Architecture choices

- Keep files, Python stdlib, vanilla JS, catalogue URLs and the existing CLI. A useful link is not bespoke LeetCode integration.
- Keep four coaching phases, highest hint rung, delayed unaided retention and prediction-based explainers. The research in docs/research requires these learning behaviors, not a custom editor or activity telemetry.
- Remove pane plugin and headless Claude launcher too: both reproduce behavior the normal agent conversation already owns. Saved artifacts remain vendor-independent.
- Preserve every notebook artifact and live session. Preserve raw browser drafts with an export affordance at their original origin; do not silently clear them.
- Do not split the 2,060-line CLI into many thin modules purely to reduce file size. The useful seam is a small command interface around notebook state, with common mutation coordination.

## Scope, verification and limitations

Reviewed all runtime areas: CLI, persistence, scheduling, hooks, pane, HTTP server, runner/parser/fetcher, browser extension, frontend, tests, product/architecture/platform docs and learning rationale. Three read-only audit passes covered core, backend and frontend; their findings were checked against source. Baseline: all 172 Python tests and all 33 Node tests passed. Thus a passing suite did not establish correctness of import retries or route races.

Native Chrome inspection covered map and Learn on an isolated notebook. No real Claude execution or live LeetCode capture was used. The optional Impeccable detector was attempted and failed with `Error: bundled detector not found.` No overlay or automated design score is claimed. No claims about current vendor pricing, versions or browser capabilities are necessary for this source-based critique. Historical specs are not treated as current requirements after the user's scope decision.

## Considered and rejected

- Framework/database migration: no demonstrated need for a single-user read-only learning app.
- Generic browser/provider adapter: would recreate the removed integration under a new name.
- More pedagogy, gamification or course systems: no evidence that these improve the requested workflow.
- Fixing retired runner/capture behavior before deleting it: effort would not survive the simplification.
- A full CLI file split before responsibility removal: higher change risk without a smaller caller interface.

Implementation and final check results will be recorded in plans/README.md.
