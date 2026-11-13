# DSA Coach

A coach that trains one learner for coding interviews by having him solve problems himself, then keeps a record of what he has learned and schedules what comes back.

## People and places

**Learner**:
The one person being coached. Docs and prompts call him "he".
_Avoid_: user, student

**Coach**:
The AI that teaches through questions and hints, following the skill.
_Avoid_: assistant, tutor, companion

**Notebook**:
The learner's record: everything he has attempted, asked and saved, and what follows from it.
_Avoid_: database, data, state

**Journey**:
Where the learner stands on one date, worked out from the notebook: plan position, pattern statuses, what is due and the next steps.
_Avoid_: snapshot (that is the saved copy of a journey), progress, dashboard

## What he studies

**Pattern**:
One of the roadmap's techniques for a family of problems, such as Sliding Window or Two Pointers.
_Avoid_: topic, category, section

**Concept**:
Anything he studies that has its own notes: every pattern is a concept, and so is a side topic such as Python collections.
_Avoid_: topic, subject

**Problem**:
One interview question, named by its LeetCode slug.
_Avoid_: question (that is something he asks), exercise, task

**Roadmap**:
The plan's order of patterns, by week and phase, with each pattern's canonical problems and target.
_Avoid_: curriculum, syllabus

**Plan**:
The learner's dated programme: a start date, a target date, and the roadmap laid over those weeks.
_Avoid_: schedule (that is the review timing)

## Solving

**Attempt**:
One go at one problem, recorded with its outcome, the hints used and the minutes taken.
_Avoid_: submission, try, run

**Live solve**:
The attempt in progress: its stage, hint rung and focus blocks, until it ends and becomes an attempt.
_Avoid_: session, current solve, solve session

**Stage**:
One of the four steps of the solve protocol: Understand, Find an approach, Build it, Check and finish.
_Avoid_: step, phase (a phase belongs to the plan)

**Hint ladder**:
The eight levels of help, from none to the full worked solution. Each level is a **rung**.
_Avoid_: hint level, help level

**Focus block**:
One stretch of focused work on a problem, 15 minutes for an easy and 25 otherwise.
_Avoid_: block (alone), pomodoro, timer

**Learning block**:
A pattern's first three problems, solved together with the pattern named, before it joins mixed practice.
_Avoid_: block (alone), batch

**Mixed practice**:
New problems drawn from several started patterns and given without the pattern's name, so he has to recognise it.
_Avoid_: interleaving, random practice, unlabeled set

**Unaided solve**:
An attempt solved with no help beyond a general question, without seeing a solution or using AI.
_Avoid_: clean solve, independent solve

**Assisted attempt**:
An attempt where he saw a solution, used AI, or reached the skeleton rung of the hint ladder or beyond.
_Avoid_: helped attempt, cheated

**Parked problem**:
A problem he stepped away from after a stuck focus block; it comes back the next day as a re-solve.
_Avoid_: skipped, abandoned

## Remembering

**Re-solve**:
Solving an earlier problem again from a blank page when it falls due.
_Avoid_: resolve, retry, review (that is a coaching mode)

**Plan-only check**:
A re-solve done from memory as a plan, with no code written: the pattern, the invariant, one trace, the complexity and one changed constraint. It keeps the review schedule moving and earns no status.
_Avoid_: quick review, light re-solve

**Due**:
Waiting for him today or earlier: a re-solve whose date has come, or a card whose review date has come.
_Avoid_: pending, overdue (overdue means due on an earlier day)

**Delay**:
The days that must pass after a problem's first attempt before a solve counts as remembered rather than fresh.
_Avoid_: gap, spacing

**Card**:
A retrieval prompt with a front and a back, about one concept, quizzed on a schedule. A card is **active** once he keeps it and **retired** when he drops it. One that arrives from a web chat waits as a **draft** until he decides.
_Avoid_: flashcard, note

**Held card**:
An active card he has passed after a gap of five days or more.
_Avoid_: learned card, mastered card

## Status

**Problem status**:
How far a problem has come: **learning** (attempted, never solved unaided), **practicing** (solved unaided at least once), **retained** (solved unaided again after the delay), **ready** (one of those later unaided solves was also timed, within the time cap, with the complexity stated).
_Avoid_: mastered, done, complete

**Solved problem**:
A problem at practicing or beyond.
_Avoid_: unaided problem, practicing problem (when counting them)

**Pattern status**:
How far a pattern has come: **not started**, **exploring** (studied but no attempts), then learning, practicing, retained and ready, judged from the statuses of its problems.
_Avoid_: level, progress

**Focus**:
The pattern the learner is working on now: the one his next new problem comes from.
_Avoid_: current pattern, active pattern

**Weak spot**:
A kind of mistake he has made often in the last thirty days.
_Avoid_: weakness, gap

**Calibration**:
How well his confidence before an attempt matches how it goes. A **high-confidence miss** is an attempt rated four or five that wasn't an unaided solve.
_Avoid_: self-assessment

## Teaching

**Coaching mode**:
What a coaching conversation is for: practice, learn, solve, review, quiz, explain, mock, AI drill, machine coding or journey.
_Avoid_: mode (alone; an attempt has its own mode)

**Attempt mode**:
How an attempt was run: learn, practice, review, mock, AI (for an AI drill) or machine coding.
_Avoid_: mode (alone), type

**Technique**:
A teaching move used on an attempt, such as a worked example or a plan card, credited only when a later delayed attempt is unaided.
_Avoid_: method, strategy, intervention

**Plan card**:
A short plan he writes before coding: the pattern, what to remember, what stays true, and how each step moves.
_Avoid_: outline, approach note

**Explainer**:
An interactive page that walks through an algorithm step by step, with predictions for him to make.
_Avoid_: artifact, visualization, animation, page

**Mock**:
A timed, talk-aloud attempt under interview conditions, where the coach only watches.
_Avoid_: test, exam, interview

## Improving the coach

**Feedback note**:
One remark about the coach or its tools, logged in a line during a session and left alone until triage.
_Avoid_: note (alone; a stage has notes too), idea, issue, bug report

**Backlog**:
The triaged feedback notes: what the next version takes, what waits, and what was declined and why.
_Avoid_: roadmap (that is the order of patterns), todo list

**Test period**:
A stretch of real study sessions on one unchanged version, after which the feedback notes are triaged.
_Avoid_: beta, trial, freeze (the freeze is the rule that holds during it)

## Web chats

**Session**:
One day's coaching, written as a short log.
_Avoid_: conversation, chat (when you mean the log)

**Context pack**:
A summary of the journey to paste into a web chat that can't read the notebook.
_Avoid_: export (that is the command that writes it), prompt

**Session delta**:
What a web chat sends back for the notebook: its attempts, questions, card reviews and explainers, waiting in the inbox until imported.
_Avoid_: diff, patch, update
