# dsa-coach workspace

This folder is Himanshu's DSA and coding-interview workspace.

- For any request to learn, practise, review, quiz, visualize or check progress on DSA, use the **dsa-coach** skill (`.agents/skills/dsa-coach`, a link to `skills/dsa-coach`).
- At the start of every session run `python3 skills/dsa-coach/scripts/coach.py status --brief` and open from its output: where he is, what's due, a proposed plan. If he asks to practise, skip the opening and start on the item `coach.py next` picks.
- All learner data lives in `notebook/`. Read and write it with `coach.py`. Never hand-edit the generated files: `JOURNEY.md`, `journey.json`, `learner/summary.md`, `learner/techniques.json`.
- If `notebook/inbox/` has session deltas from web chats, say what they contain and import them (`coach.py import`) before anything else.
- coach.py needs no network access and writes only inside this workspace.
- After a session, offer to commit the notebook changes (`git add notebook && git commit -m "Session YYYY-MM-DD: ..."`). Push only when he asks.
- When he remarks on the coach or its tools, log it with `coach.py log feedback` and carry on. Notes are triaged between versions, in `plans/backlog.md`.
- `plans/backlog.md` says whether a test period is running. While one is, the product is frozen: fix only what blocks a session or corrupts the record. If he asks for another change, say a test period is running and offer to log it as a feedback note; build it only if he then says to.
- When improving the skill itself: check the change against the reasons in `docs/research/`, and prefer replacing or simplifying a rule over adding one. Edit `skills/dsa-coach`, run `python3 -m unittest discover -s tests` and `coach.py validate`, bump the version in SKILL.md (`metadata.version`) and coach.py (`SKILL_VERSION`), then run `coach.py package`. Run `docs/coach-check.md` before a release that changes how the coach teaches. Record the change in `docs/CHANGELOG.md`.
