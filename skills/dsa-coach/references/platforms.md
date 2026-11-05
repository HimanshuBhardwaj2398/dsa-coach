# Running on different platforms

The skill follows the open Agent Skills format (agentskills.io), so the same folder works in Claude (Claude Code, Cowork, claude.ai) and in OpenAI's Codex and ChatGPT desktop app. What changes between platforms is whether you can run `coach.py` and write to the notebook. Work out which level you're on at the start of a session.

## Level A: a local agent with the workspace folder

Claude Code, Codex CLI or IDE extension, Cowork with the dsa-coach folder connected, ChatGPT desktop with local skills.

- Run `scripts/coach.py` directly. It finds the notebook through `--root`, `$DSA_NOTEBOOK`, `./notebook`, the current directory, `~/.config/dsa-coach/notebook.txt`, then the original workspace's `notebook/`, in that order.
- Edit notes in `notebook/concepts/` and `notebook/problems/` directly.
- Save explainers into `notebook/concepts/<slug>/` and register them with `artifact add`.
- At session start, `coach.py status` also reports deltas waiting in `notebook/inbox/`. Import them with `coach.py import` before anything else, after telling him what they contain.
- Run every solve through `coach.py solve`.
  - Claude Code adds two things on top. A PreToolUse guard (`coach.py guard`, installed by project-level `coach.py install`, not `install --user`) keeps your edits out of his attempt files until rung 7. Copying or unzipping the skill alone does not install this hook.
  - The optional `dsa-coach-pane` plugin (`plugins/dsa-coach-pane/` in the workspace) shows the live solve beside the chat.
  - Elsewhere, the same state lives in `notebook/sessions/current.json`, so the next session can resume it.

### Standalone setup

The ZIP contains the `dsa-coach/` skill folder, without learner data or the optional pane plugin. Extract it into the host's skills directory and run its `scripts/coach.py` from there.

For an existing notebook, pass `--root /absolute/path/to/notebook` before the command, or set `DSA_NOTEBOOK` to that path. For a new notebook, use the location chosen by the learner explicitly; plain `init` assumes the original repository layout:

```bash
python3 /path/to/dsa-coach/scripts/coach.py --root /path/to/notebook init --name Himanshu
python3 /path/to/dsa-coach/scripts/coach.py --root /path/to/notebook status --brief
```

When reusing this repository's notebook from other projects, run `python3 skills/dsa-coach/scripts/coach.py install --user --codex` from the repository. It links the skill into `~/.agents/skills` and saves the notebook location for discovery.

## Level B: code execution but no persistent folder

claude.ai with the skill uploaded and code execution on, or ChatGPT with a code interpreter.

1. Ask him to attach the newest export pack (`notebook/exports/pack-YYYY-MM-DD.md`, made with `coach.py export`). It contains the summary, due items, active patterns and the core rules.
2. Teach normally. You can run Python in the sandbox to execute traces and test his code.
3. At the end, write a session delta file named `delta-YYYY-MM-DD-<platform>.json` (format below) and give it to him to download. He drops it into `notebook/inbox/`, and the next local session imports it.

## Level C: plain chat without code

1. Ask him to paste the export pack or `learner/summary.md`.
2. Say clearly that traces you show are hand-derived, not executed.
3. At the end, output the session delta as a single JSON code block for him to save into `notebook/inbox/`.

## Explainers by platform

| Platform | How to deliver | Saving |
|---|---|---|
| Claude (any surface with artifacts) | Publish a single-file HTML page as an artifact; keep the URL | Level A: save the file and `artifact add --url`. Otherwise list the URL in the delta's `artifacts` |
| ChatGPT | A single self-contained HTML file to download, or canvas | List it in the delta; he saves the file into `notebook/concepts/<slug>/` |
| Claude Code or Codex | Write the HTML file into `notebook/concepts/<slug>/` and tell him to open it in a browser | `artifact add --file` |

## Platform memory

Keep the learner model in the notebook. Claude's or ChatGPT's own memory should hold at most a few stable facts (his goal, level and format defaults), never progress, mastery or technique judgments.

## Session delta format (`dsa-coach-delta/1`)

Every list is optional. Dates default to the session date. Field meanings are in references/learner-model.md. A full example lives at `assets/delta-example.json`.

```json
{
  "format": "dsa-coach-delta/1",
  "platform": "claude-web",
  "skill_version": "0.1.0",
  "session": {"date": "2026-11-02", "minutes": 60, "summary": "Two pointers: learned the opposite-ends template; solved 3Sum with hints."},
  "attempts": [
    {"problem": "3sum", "pattern": "two-pointers", "difficulty": "medium", "mode": "learn",
     "outcome": "solved", "minutes": 35, "hints": 3, "assisted": false, "confidence": 3,
     "technique": "faded-example", "mistakes": ["edge"], "complexity_stated": true,
     "note": "skip duplicates after moving both pointers"}
  ],
  "questions": [{"concept": "two-pointers", "text": "Why can't the left pointer ever move back?"}],
  "cards": [{"concept": "two-pointers", "type": "invariant", "front": "...", "back": "...", "draft": true}],
  "card_reviews": [{"id": "c0003", "grade": "pass"}],
  "artifacts": [{"concept": "two-pointers", "title": "Two Pointers on the (i, j) Grid", "url": "https://..."}]
}
```

Validation rules: `pattern` must be a key in assets/roadmap.json; `mode`, `outcome`, `difficulty`, `technique`, mistake codes and card types must use the documented values; `hints` 0–7; `confidence` 1–5 or null. `coach.py import` rejects a delta that breaks these rules and says which field is wrong, so fix it and import again.
