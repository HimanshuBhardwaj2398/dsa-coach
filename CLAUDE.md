# dsa-coach workspace

This folder is Himanshu's DSA and coding-interview workspace.

- For any request to learn, practise, review, quiz, visualize or check progress on DSA, use the **dsa-coach** skill (`skills/dsa-coach`, linked at `.claude/skills/dsa-coach`).
- All learner data lives in `notebook/`. Read and write it with `python3 skills/dsa-coach/scripts/coach.py`. Never hand-edit the generated files: `JOURNEY.md`, `journey.json`, `learner/summary.md`, `learner/techniques.json`.
- A SessionStart hook prints `coach.py status --brief` at the start of each session. Open from it: where he is, what's due, a proposed plan. If he asks to practise or runs `/practice`, skip the opening and start on the item `coach.py next` picks.
- If `notebook/inbox/` has session deltas from web chats, say what they contain and import them (`coach.py import`) before anything else.
- Keep learner progress out of Claude's memory; it belongs in `notebook/`.
- After a session, offer to commit the notebook changes (`git add notebook && git commit -m "Session YYYY-MM-DD: ..."`). Push only when he asks.
- When improving the skill itself: edit `skills/dsa-coach`, run `python3 -m unittest discover -s tests` and `coach.py validate`, bump the version in SKILL.md (`metadata.version`) and coach.py (`SKILL_VERSION`), then run `coach.py package`. Record the change in `docs/CHANGELOG.md`.
