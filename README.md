# dsa-coach

My step-by-step coach for DSA and coding interviews (AI engineer roles), built as a portable Agent Skill plus a learning notebook and a journey snapshot. The same skill works in Claude Code, Cowork, Claude web, Codex and ChatGPT.

## What's in this folder

```text
dsa-coach/
├── skills/dsa-coach/      the skill: SKILL.md, references/, scripts/coach.py, assets/
├── notebook/              my data: JOURNEY.md, attempts, cards, concepts, problems, sessions, saved explainers
├── docs/                  platform setup, the coach check, the changelog, the research behind the design
├── plans/                 open work: the backlog that feedback notes are triaged into
├── tests/                 tests for coach.py, the app, the extension (tests/frontend, tests/browser)
├── plugins/dsa-coach-pane the coach pane for Claude Code (the live solve beside the chat)
├── app/                   the learning app: python3 app/server.py serves Today, the map and Learn pages (read-only)
├── extensions/dsa-coach/  Chrome/Edge side panel: the learning app beside LeetCode
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

Claude Code is the one platform proven in real sessions. The others are set up and haven't had a real session yet. Full setup for each: [docs/PLATFORMS.md](docs/PLATFORMS.md).

## How a solve works

You read and code on LeetCode. The coach in Claude Code runs the four stages, gives hints one rung at a time and logs the attempt; it looks at your LeetCode tab with a browser tool when it can, or asks you to paste your code. Nothing in this repo reads or scrapes LeetCode.

## The coach pane (Claude Code)

A pane beside the chat that shows the problem you're solving, the solve stage, the focus-block timer and the hint rung you've used. It only shows state; you talk to the coach in the chat.

Install it once, at the Claude Code prompt in this folder:

```text
/plugin marketplace add ./
/plugin install dsa-coach-pane@dsa-coach
```

- **Where it opens:** it opens by itself in VS Code and the desktop app. Anywhere else, type `/coach`.
- **How it updates:** it's read from `plugins/dsa-coach-pane/`, so after you change it, run `/reload-plugins`.
- **Version needed:** Claude Code 2.1.317 or later.

## The learning app and the browser panel

`python3 app/server.py` opens a read-only page: **Today** (the live solve, what's due, what's next), the **Map** of all 22 patterns, and each pattern's **Learn** page with cues, invariant, template, resources, problems and its saved explainer. To show the same page beside LeetCode, install the [browser extension](extensions/dsa-coach/README.md).

## Everyday commands

The coach runs these for you; they're here so you can check or fix things by hand.

| Command | Does |
|---|---|
| `coach.py status` | Where you are, what's due, next steps |
| `coach.py next` | The one thing to practise now (`--pattern` to choose one, `--json` for the coach) |
| `coach.py solve show` | The solve in progress: stage, hint rung, focus block (`start`, `stage`, `hint`, `note`, `break`, `block`, `end`) |
| `coach.py due` | Due re-solves and cards |
| `coach.py quiz` | Due card fronts (`--json` adds answers) |
| `coach.py card list` | Your cards (`card add`, `card edit`, `card retire`; `--drafts` lists cards from web chats that wait for `card accept`) |
| `coach.py log attempt ...` | Log an attempt (`--help` lists every field) |
| `coach.py log feedback --text "..."` | Note something about the coach or its tools for later (`/note` in Claude Code) |
| `coach.py artifact list` | Saved explainers and published pages |
| `coach.py export` / `coach.py import` | Web-chat round trip |
| `coach.py map --json` | Progress by pattern, what's due and the live solve (what the learning app shows) |
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

## Improving it

When something about the coach or its tools bothers you in a session, say "note: ..." or type `/note ...`. It is logged in `notebook/feedback.jsonl` with the version and where you were in the solve, and the session carries on. Nothing gets built then.

Notes are triaged between versions into [plans/backlog.md](plans/backlog.md): what the next version takes, what waits, and what was declined and why. That file also says whether a test period is running. During one, the product stays as it is, apart from a fix for something that blocks a session or corrupts the record.

## Changing the skill

1. Edit files in `skills/dsa-coach/`.
2. Run `python3 -m unittest discover -s tests`, `node --test tests/frontend/*.test.cjs` and `coach.py validate`. After changing the app or extension, also `python3 tests/browser/check_app.py`. After changing how the coach teaches, also run [docs/coach-check.md](docs/coach-check.md) by hand.
3. Bump the version in two places: `metadata.version` in SKILL.md and `SKILL_VERSION` in coach.py.
4. `coach.py package`, then re-upload `dist/dsa-coach.zip` wherever you uploaded it (Claude web, Cowork). Claude Code and Codex use the folder directly.

## How it's designed

[ARCHITECTURE.md](ARCHITECTURE.md) covers the layers, the data flow, the platform matrix, the design decisions and the build roadmap. The research behind the teaching rules is in `docs/research/`.
