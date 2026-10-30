# dsa-coach workspace

This folder is Himanshu's DSA and coding-interview workspace.

- For any request to learn, practise, review, quiz, visualize or check progress on DSA, use the **dsa-coach** skill (`.agents/skills/dsa-coach`, a link to `skills/dsa-coach`).
- At the start of every session run `python3 skills/dsa-coach/scripts/coach.py status --brief` and open from its output: where he is, what's due, a proposed plan.
- All learner data lives in `notebook/`. Read and write it with `coach.py`. Never hand-edit the generated files: `JOURNEY.md`, `journey.json`, `learner/summary.md`, `learner/techniques.json`.
- If `notebook/inbox/` has session deltas from web chats, say what they contain and import them (`coach.py import`) before anything else.
- coach.py needs no network access and writes only inside this workspace.
- After a session, offer to commit the notebook changes (`git add notebook && git commit -m "Session YYYY-MM-DD: ..."`). Push only when he asks.
- When improving the skill itself: edit `skills/dsa-coach`, run `python3 -m unittest discover -s tests` and `coach.py validate`, bump the version in SKILL.md (`metadata.version`) and coach.py (`SKILL_VERSION`), then run `coach.py package`. Record the change in `docs/CHANGELOG.md`.
