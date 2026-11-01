# dsa-coach

My step-by-step coach for DSA and coding interviews (AI engineer roles), built as a portable Agent Skill plus a learning notebook and a journey snapshot. The same skill works in Claude Code, Cowork, Claude web, Codex and ChatGPT.

## What's in this folder

```text
dsa-coach/
├── skills/dsa-coach/      the skill: SKILL.md, references/, scripts/coach.py, assets/
├── notebook/              my data: JOURNEY.md, attempts, cards, concepts, problems, sessions, saved explainers
├── docs/                  architecture, platform setup, the research behind the design
├── tests/                 tests for coach.py
├── dist/dsa-coach.zip     the skill packaged for uploading to Claude
├── CLAUDE.md, AGENTS.md   project instructions for Claude Code and Codex
└── .claude/, .agents/     links that make the skill visible to Claude Code and Codex
```

## Where am I?

Open `notebook/JOURNEY.md`. It shows the day and week of the plan, the focus pattern, what's due, a map of all 22 patterns, weak spots, calibration and which teaching techniques have earned credit. Refresh it any time:

```bash
cd ~/Desktop/dsa-coach
python3 skills/dsa-coach/scripts/coach.py status      # short version, also refreshes JOURNEY.md
python3 skills/dsa-coach/scripts/coach.py snapshot --print
```

## Start a session

| Where | How |
|---|---|
| Claude Code | `cd ~/Desktop/dsa-coach && claude`, then `/practice` to start right away, or "where am I?", "teach me two pointers", "review" or "quiz me". The status loads automatically at session start. |
| Codex or ChatGPT desktop | `cd ~/Desktop/dsa-coach && codex`, then `$dsa-coach where am I?` |
| Cowork | A "DSA Coach" project with this folder connected (setup in docs/PLATFORMS.md) |
| Claude web or ChatGPT web | `coach.py export`, attach the pack, study, then save the session delta into `notebook/inbox/` and run `coach.py import` |

Full setup for each platform: [docs/PLATFORMS.md](docs/PLATFORMS.md).

## Everyday commands

The coach runs these for you; they're here so you can check or fix things by hand.

| Command | Does |
|---|---|
| `coach.py status` | Where you are, what's due, next steps |
| `coach.py next` | The one thing to practise now (`--pattern` to choose one, `--json` for the coach) |
| `coach.py due` | Due re-solves and cards |
| `coach.py quiz` | Due card fronts (`--json` adds answers) |
| `coach.py card list --drafts` | Cards waiting for your approval (`card accept`, `card edit`, `card retire`) |
| `coach.py log attempt ...` | Log an attempt (`--help` lists every field) |
| `coach.py artifact list` | Saved explainers and published pages |
| `coach.py export` / `coach.py import` | Web-chat round trip |
| `coach.py validate` | Check the skill and the notebook files |
| `coach.py package` | Rebuild `dist/dsa-coach.zip` |

## On another machine

The repo is private on GitHub: https://github.com/HimanshuBhardwaj2398/dsa-coach

```bash
git clone https://github.com/HimanshuBhardwaj2398/dsa-coach.git
cd dsa-coach
python3 skills/dsa-coach/scripts/coach.py install    # links and hook are in the repo; this only repairs them
python3 skills/dsa-coach/scripts/coach.py package    # rebuilds dist/dsa-coach.zip for Claude web
python3 skills/dsa-coach/scripts/coach.py status
```

After a study session, commit the notebook so every machine sees the same journey:

```bash
git add -A && git commit -m "Session 2026-11-02: two pointers" && git push
```

## Changing the skill

1. Edit files in `skills/dsa-coach/`.
2. Run `python3 -m unittest discover -s tests` and `coach.py validate`.
3. Bump the version in two places: `metadata.version` in SKILL.md and `SKILL_VERSION` in coach.py.
4. `coach.py package`, then re-upload `dist/dsa-coach.zip` wherever you uploaded it (Claude web, Cowork). Claude Code and Codex use the folder directly.

## How it's designed

[ARCHITECTURE.md](ARCHITECTURE.md) covers the layers, the data flow, the platform matrix, the design decisions and the build roadmap. The research behind the teaching rules is in `docs/research/`.
