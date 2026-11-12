> **Archived.** Four stages built in 0.8.0 and kept; finishing a solve in the panel was removed in 0.9.0. Kept for history: paths inside are as they were when it was written.

# A simpler guided solve, finished inside the coach panel

Date: 2026-11-09
Status: approved 2026-11-09 with the trims below; plan in `docs/superpowers/plans/2026-11-09-four-stages-and-panel-finish.md`

## Approved scope (trimmed)

Himanshu approved the four stages, the coaching guidance inside them, migration of old solves, and the review-then-save finish in the panel. The rest of this document stands except for the following:

- **No sync or conflict machinery.** One learner works on one machine. The existing browser draft and save behaviour stays as it is: no base-version comparison on reload, no keep-both conflict UI, and no offline retry queue. Old browser drafts become unreadable once the draft version is bumped, and they are kept for copying through the existing recovery banner.
- **No resource-catalogue changes.** Learn stays as it is: no new resource metadata, recall questions, "Bring an idea back" notes or opened-link tracking.
- **The review lives in server memory, not in `coach.py`.** The server keeps the latest accepted review per solve, together with a fingerprint of the inputs it assessed. Restarting the server means asking for a fresh review. `coach.py` adds only the originating session to each attempt row, so a repeated save returns the attempt already recorded.
- **One stage table per consumer, with a test that checks they match.** This replaces a shared machine-readable stage file. The pane maps a legacy stage number itself, because it reads `current.json` directly.
- **The full study app keeps its copy-to-chat finish.** Direct save is built for the LeetCode panel only, as the scope section below says.

## Goal

Make a practice session easier to enter and follow, then finish it beside LeetCode: four understandable stages, help with the reasoning inside each stage, and a reviewed learning record saved without opening the main coach chat.

Success means the learner can understand the next action without facing eight stages or a long form, still practise the important reasoning, and create exactly one accurate attempt when finishing. The existing review scheduler determines the next review and retention status.

## Four stages, with guidance inside them

The user identified both too many stages and insufficient help with thinking through them. Renaming or hiding the existing eight-step checklist would not address both concerns.

| Stage | Learner's immediate task | Coach support |
|---|---|---|
| 1. Understand | Explain what is asked and predict a small example | Start with a concrete input and output; introduce constraints and a relevant edge case as needed |
| 2. Find an approach | Describe a workable method and why it should work | Help derive brute force, count its work, find useful improvements, and settle on a short plan |
| 3. Build it | Turn that plan into code | Connect each plain-language action to variables, initialization, loop/recursion steps, and the returned result |
| 4. Check and finish | Test, explain the result, and record the lesson | Inspect evidence, revisit complexity, ask one useful follow-up, then review and save the attempt |

Alternative designs considered: three stages would combine planning and coding, weakening a distinction the workspace is explicitly training. Five stages would make improvement a separate stage, but improvement is not always necessary and would add another required stop. Four matches the project's existing understand/plan/carry-out/look-back foundation while reducing visible navigation.

### Interaction rules

- Show four stage names and one current prompt. Do not expose a second numbered checklist of eight mandatory substeps.
- Each stage has a short starter question, an editable working note, and **Help me think**. Show richer examples/plan tools when useful, not every field at once.
- The coach can work through several ideas within one stage, but does not require a separate form submission for every thought. Reuse saved answers instead of asking the learner to restate them.
- Offer one manageable next question. A response that already demonstrates several ideas covers them together; do not force redundant questions.
- Let the learner revise earlier reasoning and move between stages without losing work. A UI visit is not proof of mastery.
- Use familiar language first: “What do we need to remember?” before “state”; “What stays true after each step?” before “invariant”. Introduce the formal name after the idea is understood.
- General explanations of counting or translating a plan into code are available when requested, without making the learner wait out a focus block. Problem-specific clues still follow the hint ladder and count at the level of information they reveal.
- Help should fade with demonstrated independent performance. Familiar problems need a short plan, not mandatory completion of novice scaffolds.

### Helping with brute force, counting and improvement

These are the coach's available teaching moves in **Find an approach**, not a questionnaire displayed all at once:

1. **Find something that works:** “If speed did not matter, what possibilities could you try?” If that is too abstract, use a tiny input and ask how the learner would get the answer by hand. Separate listing candidates from checking one candidate.
2. **Make counting concrete:** “Pick one action your method repeats. When does it happen?” Trace a small case, count that action, then describe how the count depends on input size. If the work changes between iterations, add the different counts; do not teach that two loops automatically mean quadratic time. Account for work hidden inside operations such as copying, slicing or membership checks. Discuss extra memory separately. Execute any concrete trace/count presented as evidence.
3. **Connect the count to the limit:** “If the input gets bigger, which part grows fastest? Is that workable for the given limit?” Introduce Big-O after the count has meaning. A small trace helps form the argument but does not prove the general bound.
4. **Find a reason to improve:** “What did you calculate more than once?” or “Which possibilities can you safely stop checking?” Derive a useful change from the observed repeated work or a property of the input. Ask for its correctness reason, then recount the work. If the simple approach already fits, do not force an optimized approach.
5. **Keep a short plan:** Record what is remembered, what one step does, and why it is safe. Existing complexity and trace evidence remains available. Pattern naming can follow the reasoning rather than serving as an entry requirement.

Generic concept help can use a separate toy example followed by a learner prediction. It must not silently supply the current practice problem's optimal data structure, invariant or code. If it does reveal these, record the corresponding hint level.

### Helping with implementation

Replace “write pseudocode, then code” as the only instruction with a concrete bridge from the learner's own plan:

- “What information from your plan needs a variable?”
- “What should those variables mean before the first step?”
- “Take one action from your plan. What must the program read or update?”
- “What makes the next iteration or recursive call move forward, and when should it stop?”
- “Where is the answer at that point?”

Use only the question relevant to the current difficulty. Show the plan beside the work when possible; let the learner write one meaningful part and trace its effect. Comments or pseudocode are useful when they bridge a gap, not mandatory duplicate paperwork for every learner. Avoid demanding full brute-force code unless implementing it serves a specific learning or checking purpose.

### Consistent state and compatibility

Use the same four-stage protocol in the skill, CLI status, study app, companion, and Claude pane. Keep the definition in one machine-readable source for programmatic consumers rather than maintaining independent stage-name arrays. Written coaching guidance explains how to use those stages.

Version the live-solve protocol so legacy stage numbers cannot be mistaken for the new stages. Migrate through `coach.py`: old 1 maps to Understand, old 2–6 to Find an approach, old 7 to Build it, and old 8 to Check and finish. Preserve every old note with its original label and retain the attempt file, hint level and timing. Do not rewrite historical attempts. Old browser drafts must remain recoverable with their original labels; never reinterpret an old stage-4 draft as the new finish form.

The current solve at old stage 4 therefore resumes within Find an approach, with its repeated-work note available. Compatibility tests use a copy in a temporary notebook rather than modifying the real active solve.

Implement the four-stage protocol and guidance first, then connect completion to Check and finish. These are two work packages within the same approved learner flow.

### Moving between tabs and stages without losing state

Review the proposed interaction in `app/prototypes/guided-solve-preview.html`. This is a standalone, throwaway prototype with simulated coach replies and notebook saves. Its isolated browser storage never touches the real notebook. The final implementation must preserve these distinctions:

| State | Owner | Behavior when navigating |
|---|---|---|
| Current progress and explicitly completed stages | Saved live solve | Viewing another stage does not change either; only a deliberate continuation advances progress |
| Stage answers, plan and completion inputs | Per-session draft, acknowledged into the notebook | Capture edits as they happen; switching a tab never clears them or submits them as completed work |
| Selected tab, viewed stage, opened help, per-view scroll position | Browser view state | Restore the same place when returning; keep separate from learning progress |
| Unsent chat message and the current panel conversation | Browser state scoped to notebook and solve | Retain across tabs and browser recovery; do not mix messages into another problem or call them notebook learning records |
| Latest coach review | Versioned saved proposal | Ordinary navigation does not invalidate it; changes to the evidence or answers do |
| Completed attempt and receipt | Notebook | A repeated save or reload returns the same attempt, not another attempt |

Write browser drafts immediately, then save notebook changes in the background. Say “Saved” only after acknowledgement; show “Kept in this browser” or an offline state while saving is unavailable. If browser recovery is unavailable, say so without pretending work will survive closing.

Each save carries the session identity and the saved version it started from. A late acknowledgement can update the saved version but cannot replace newer typing. On reload, compare the draft's base version with the current saved version before retrying: an offline draft must not silently overwrite changes made in another window.

When copies conflict, preserve both and show the differing values. Offer an explicit choice to keep the local draft or use the saved version, with a way to copy/recover the displaced draft. Resolve the actual changed fields in production rather than presenting an unrelated whole-file replacement as a harmless save.

Coach replies and reviews stay attached to the solve and input version that requested them. A reply arriving while the learner is in Learn should be available in Chat without switching their tab. A review of older answers cannot enable Save for the newer answers. If a request is interrupted by closing/reloading, retain its inputs and offer retry; do not display an indefinite pending state.

Browsing an earlier stage after finishing is read-only and retains the receipt. Starting a new solve is an explicit action with new draft/message keys. Preserve recoverable work from the previous solve instead of carrying it into the next one.

### Learn: curated external resources

Include a small selection of external written explanations and videos that develop an argument from examples, operation counts, invariants or correctness reasoning. Prefer written resources first, with a video alternative. Use at most three recommendations for the current learning need, not a wall of links or a mandatory course playlist.

Each recommendation includes its author/provider, format and language, why it is relevant, the particular section to focus on, and a question to recall or apply the idea after leaving the resource. Mark worked-solution content and access restrictions when relevant. Avoid suggesting a solution to the active problem as if it were neutral concept help; keep the assistance record honest when such help is used.

The preview's verified starting set (checked 2026-11-09) is:

- [Hello Algo: time complexity](https://www.hello-algo.com/en/chapter_computational_complexity/time_complexity/), especially §2.3.3; derive costs from operations using its Python examples.
- [Cornell CS 2110: loop invariants](https://courses.cs.cornell.edu/courses/cs2110/2026fa/lectures/lec04/); work out initialization, the stopping condition and loop body. Label its Java examples and pair with the Python resource rather than assuming the learner knows Java.
- [MIT 6.006: Algorithms and Computation](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/lecture-1-algorithms-and-computation/); video and transcript introducing computational problems, correctness and efficiency.

Open external resources in a new tab, preserving the solve and Learn position. An opened link means only “opened”, never “read”, “learned” or “completed”. Offer an optional “Bring an idea back” note, retained across navigation/reload and scoped to the solve/resource. “Discuss with coach” adds the learner's recall and source to their message draft, preserving any existing unsent message. “Add to my approach” explicitly appends the learner's idea to the stage note, so an existing finish review becomes stale. Neither action grants mastery credit.

In production, extend the existing curated resource catalogue with format, focus, recall question, language, access and checked-date metadata. Recommendations should use the learner's current difficulty or concept, while avoiding premature pattern disclosure on unlabeled problems. The prototype uses a fixed shortlist for its sample problem; it does not claim to implement adaptive recommendations.

## Approaches considered

1. **Coach review, then learner confirmation — recommended.** Keep the panel's AI without file-writing tools. Have it prepare a structured review; show the record to the learner; let an explicit Save button ask the local server to record it through `coach.py`. Preserves the existing rule that the coach assesses mistakes and complexity while removing the chat handoff.
2. **A manual completion form.** Simplest implementation, but moves the coach's assessment of complexity and teaching technique onto the learner and risks misleading learning credit.
3. **Give the panel AI tools to finish the solve itself.** Reuses main-chat behavior but gives ordinary panel replies much broader powers and makes the save harder to inspect and retry safely.

## Learner flow

Use the new Check and finish stage and existing visual style. Completion follows the simpler guided flow above.

1. The learner saves their look-back answers, chooses solved/partial/failed, and writes the lesson. Collect test evidence and an explicit choice about outside help or seeing a solution. Reuse already-saved evidence instead of presenting duplicate fields. Explain that solved means the relevant tests passed, not merely that the code looks plausible.
2. **Review attempt** saves Check and finish, captures the current LeetCode code/page context using the existing extension mechanism, and asks the panel coach to review that evidence. A failed capture is visible; the learner can supply code/result context explicitly and retry.
3. The coach returns either missing evidence with a specific follow-up, or a proposed record. Solved requires test evidence; complexity credit requires the learner's own correct time/space explanation. Unknown teaching technique remains unspecified, rather than guessed from the final reply.
4. Show a concise completion summary: outcome, test evidence, lesson, hint level, assistance, time, complexity assessment, and any observed mistakes/teaching technique. The learner can correct their inputs and request a fresh review. AI assessments are displayed in plain language.
5. **Save attempt** is an explicit action after the review. It records the reviewed result through the local server and `coach.py`. It does not send a prompt to the main chat.
6. Show a durable completion receipt with the recorded outcome, next review date and next recommended action. Offer **Continue practice** without automatically starting another solve.

Partial or failed work can still be recorded honestly. Missing complexity evidence means no complexity credit; it need not prevent saving an otherwise supported outcome. An unsupported solved claim is returned for clarification, with parking still available.

## Responsibilities

### Panel

- Collect/save learner inputs before requesting review.
- Show the review, pending state, errors and completion receipt.
- Disable duplicate actions while requests are running.
- Preserve unsaved completion inputs using the existing browser draft mechanism.
- Keep normal coaching available for follow-up questions.

### Coach review helper

- Use the existing signed-in Claude CLI and job runner with tools disabled.
- Receive saved stage notes, plan/examples, current hint level, learner-declared outside help, completion inputs, and supplied LeetCode context.
- Follow a dedicated completion-review prompt using the existing learner-model meanings.
- Return a strictly validated structured result: feedback, missing evidence, proposed outcome, complexity assessment, optional technique, mistake codes, and any hint rung given by the review.
- Never claim it executed code or independently verified a LeetCode submission. Distinguish observed page text from the learner's report.
- Never grant retention status or reduce recorded hints/assistance.

Keep review validation in a focused module rather than expanding general conversation parsing into a mixed chat-and-completion parser.

### Local server

- Start/poll a completion-review job separately from ordinary conversation requests while reusing the existing job infrastructure.
- Validate the response and associate the proposed record with the notebook, live session and reviewed inputs. Reject unknown enums, malformed fields and unsupported success claims.
- Store an accepted review draft through `coach.py`; it is not a completed attempt and earns no learning credit.
- At save time, use the stored reviewed fields and fresh server-owned session values. Do not trust client-supplied hint level, duration, confidence or arbitrary assessment fields.
- Record any review hint through the existing upward-only hint mechanism before establishing the saved review version.
- Return a receipt from the persisted attempt and newly calculated review schedule.

### coach.py

- Own the saved review draft, attempt creation, archived notes, completion identity and receipt lookup.
- Reuse current solve-end logging and scheduling behavior; avoid a separate scheduler or mastery calculation.
- Carry a stable originating session identity into new attempt records so retries can find an already-recorded completion. Existing historical rows without this optional identity remain valid.
- Make completion retryable: a repeated save returns the same recorded attempt, never appends another one. If an attempt was appended but later archive/cleanup work failed, retry finishes that work without duplicating the attempt or archived notes.
- Under the existing session lock, validate the expected session and reviewed-input version before committing completion. An old request must never end a newer solve.

## Stale reviews and honest credit

A review applies only to the inputs it assessed. Changes to outcome, lesson, outside-help answer, result evidence, saved reasoning, plan/examples, code context, or hint level require a fresh review. Activity timestamps alone do not invalidate the review; elapsed time is taken from the current session when saving.

Before saving, the panel captures the LeetCode context again and compares the reviewed code and problem identity. A changed problem/code invalidates the review. Because LeetCode is a separate application, this is a checked snapshot, not a claim that its editor is locked between capture and save.

Assistance is conservative: explicit outside help is preserved, and existing high-hint/AI-mode rules still apply. No review can reset a higher saved hint rung. The current definitions of unaided, retained and ready remain unchanged.

The saved lesson/notes include a concise record of the test-evidence source and assessment. This feature does not introduce automatic synchronization between the LeetCode editor and the local attempt file, nor does it persist the entire panel conversation.

## Failure and recovery behavior

- Claude unavailable, timeout, malformed review or missing evidence: keep the solve and inputs; show a useful retry or follow-up action; do not create an attempt.
- Wrong/stale session, changed inputs or newer hints: require a fresh review and preserve work.
- Double-click, repeated request or lost save response: return the same completion receipt once saved.
- Reload after saving: recognize the completed session from its receipt; do not resubmit or show the old draft as an unfinished solve.
- Concurrent completion in the main chat: detect the recorded originating session and show that result; do not append another completion.
- A receipt lookup for an old session never mutates a newer live solve.

## Scope

Implement the four-stage guided protocol consistently across entry points, then implement direct completion inside the LeetCode companion. The ordinary study app's main-chat finish flow and parking behavior remain supported. Update shared CLI completion internals only where needed for reliable identity/retries and protocol migration.

No autonomous LeetCode submission, cloud storage, full chat-history persistence, card-generation workflow, or broad rewrite of teaching prompts is included.

## Verification

Use test-first development for the behavior:

0. Four stages appear consistently across the CLI, study app and pane. Legacy solves/notes and browser drafts retain their meaning and recoverability. The learner sees one current prompt rather than eight required substeps. Check representative coaching cases for brute-force derivation, uneven loop counts, a sufficient simple approach, translating a learner-authored plan into code, and accidental solution disclosure. Deterministic tests check saved state and prompts; reviewed response examples assess teaching quality without claiming that software tests prove improved learning.

1. Review parsing rejects invalid schemas/enums and distinguishes missing evidence from a recordable attempt.
2. An end-to-end server test with a fake Claude reviewer completes a temporary-notebook solve, archives stage notes, saves assistance/complexity correctly, and returns the existing scheduler's review date.
3. Double-click, lost response, retry after partial persistence, reload, concurrent main-chat completion and a new active session cannot create duplicate attempts or overwrite the wrong solve.
4. Changed code/reasoning/outcome/help/rung invalidates the proposal; ordinary timer activity does not.
5. Failed review/save preserves completion inputs; unavailable evidence never creates success credit.
6. Existing parking, normal panel chat and ordinary study-app completion still work.
7. A browser test exercises the panel flow in a temporary notebook, including the narrow panel and keyboard access. Do not complete the learner's real active solve while testing.

Run the Python suite, relevant frontend/browser/pane checks and `coach.py validate`. Update the skill, protocol/plan-card/platform references, PRODUCT.md, extension README and architecture walkthrough to describe the four stages and new finish flow. Bump skill and CLI versions together, record the change in `docs/CHANGELOG.md`, and rebuild the skill package as required by AGENTS.md.

## Design rationale and review

This follows the existing research rationale: make the thinking process explicit, help the learner use it, and fade support as they become independent. The project's learning-principles document already groups its eight steps into Polya's four phases. Four visible stages are a design choice to address the user's reported burden, not a claim that a four-stage interface has been shown to improve retention here. Keep testing delayed unaided performance.

AI still teaches and assesses; scripts keep auditable records; delayed unaided performance earns retention credit. The final stage retains look-back work and makes the final write visible to the learner.

Sources checked: `docs/research/dsa-learning-skill-research.md` (honest learning records and delayed evidence), `docs/research/learning-principles.md` (look back and delayed unaided success), the current learner-model reference, `app/static/app.js`, `app/server.py`, `app/companion.py`, and `coach.py` solve-end logic.

Self-review: scope now includes the user's requested four-stage guided experience, compatibility across entry points, and the originally requested panel completion handoff. Outcome review, explicit save and retry behavior have separate responsibilities. Guidance is not eight hidden mandatory steps, and help does not silently grant unaided credit. This revised proposal awaits user review before the implementation plan.
