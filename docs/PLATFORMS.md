# Setting up each platform

Everything below assumes the workspace is at `~/Desktop/dsa-coach`. Commands use `coach.py` as short for `python3 skills/dsa-coach/scripts/coach.py`, run from the workspace folder.

## Claude Code

Already set up: `.claude/skills/dsa-coach` links to the skill, and `.claude/settings.json` has a SessionStart hook that prints your status when a session starts.

```bash
cd ~/Desktop/dsa-coach
claude
> where am I?
```

- If Claude Code doesn't list the skill (`/skills`), replace the link with a copy: `coach.py install --claude --copy --force`. Re-run it after you edit the skill.
- To use the coach from any folder, install it for your user account: `coach.py install --user`. That links the skill into `~/.claude/skills` and `~/.agents/skills` and writes `~/.config/dsa-coach/notebook.txt`, so coach.py finds this notebook from anywhere.

## Codex (CLI or IDE extension)

Codex loads skills from `.agents/skills` in the folder you start it in, and `AGENTS.md` tells it to run the status first.

```bash
cd ~/Desktop/dsa-coach
codex
> $dsa-coach where am I?
```

Codex runs without network by default and may only write inside the workspace. coach.py needs neither network nor anything outside the workspace, so the default "Auto" mode works.

## ChatGPT desktop app

Standalone skills load from `~/.agents/skills`. Run `coach.py install --user --codex` once, then mention `@dsa-coach` in a chat. If the app can't run the scripts or write files in this folder, use the web flow below.

## Cowork (Claude desktop app)

1. Create a project named "DSA Coach" and connect this folder to it.
2. Paste [cowork-project-instructions.md](cowork-project-instructions.md) into the project instructions.
3. Optional: upload `dist/dsa-coach.zip` as a skill in Claude's settings, so the coach is available in every chat, including Claude on the web.

Cowork can run coach.py in the connected folder, so the full loop works there, and explainers can be published as artifacts with their URLs registered in the notebook.

## Claude on the web

1. Upload `dist/dsa-coach.zip` as a skill in Claude's settings (code execution needs to be on). Re-upload it after each new version.
2. Before a session, run `coach.py export` and attach the newest `notebook/exports/pack-YYYY-MM-DD.md` to the chat.
3. At the end, the coach gives you a session delta (a JSON file or code block). Save it into `notebook/inbox/`.
4. Back at the Mac, run `coach.py import`, or let the next Claude Code or Codex session import it.

## ChatGPT on the web

As of October 2026 ChatGPT on the web runs skills only when they come inside plugins, so use the pack directly: attach `notebook/exports/pack-YYYY-MM-DD.md` (it includes the coach instructions) to a chat or a ChatGPT project, and finish with a session delta saved into `notebook/inbox/`, as above.

## Keeping things in sync

| You changed | Do this |
|---|---|
| The skill | Tests, `coach.py validate`, bump the version, `coach.py package`, re-upload the zip where you uploaded it |
| Anything in a web chat | Save the delta into `notebook/inbox/`, then `coach.py import` |
| The plan (dates, hours) | Edit `notebook/config.json`, then `coach.py snapshot` |
