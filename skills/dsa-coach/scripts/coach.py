#!/usr/bin/env python3
"""coach.py: the learning-notebook CLI behind the dsa-coach skill.

Standard library only, Python 3.9+. Run `python3 coach.py --help`.

The notebook is found through --root, then $DSA_NOTEBOOK, then ./notebook,
then the current folder, then ~/.config/dsa-coach/notebook.txt, then the
`notebook/` folder of the workspace the skill lives in.
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import shutil
import sys
import time
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict

SKILL_VERSION = "0.9.2"
SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
WORKSPACE = SKILL_DIR.parent.parent  # <workspace>/skills/dsa-coach
POINTER = Path.home() / ".config" / "dsa-coach" / "notebook.txt"

DELTA_FORMAT = "dsa-coach-delta/1"
RESOLVE_LADDER = [1, 3, 7, 14, 30]
CARD_LADDER = [1, 3, 7, 14, 30, 60]
HELD_DAYS = 5
PATTERN_RETAINED_AT = 2  # a pattern is retained once this many of its problems are
PATTERN_READY_AT = 3     # and ready once this many are
WEAK_SPOT_DAYS = 30      # weak spots count the mistakes logged in this many days
HIGH_CONFIDENCE = 4      # a miss at this confidence or above is worth a second look
MOCKS_FROM_WEEK = 6      # timed mocks start in this week of the plan
MOCK_EVERY_DAYS = 14     # and are suggested again after this many days
MODES = ["learn", "practice", "review", "mock", "ai", "machine"]
OUTCOMES = ["solved", "partial", "failed"]
DIFFICULTIES = ["easy", "medium", "hard"]
MISTAKES = {
    "comp": "misread the problem or constraints",
    "pattern": "wrong pattern or missed cue",
    "invariant": "wrong or vague state / invariant",
    "boundary": "off-by-one or loop bounds",
    "edge": "missed edge case",
    "pytrap": "Python pitfall",
    "complexity": "wrong or missing complexity",
    "impl": "implementation slip",
    "process": "skipped a stage",
    "comm": "unclear explanation",
}
TECHNIQUES = [
    "explainer-predict", "worked-example", "faded-example", "hint-ladder", "plan-card",
    "contrast-pair", "lead-reveal", "analogy", "reading", "none",
]
CARD_TYPES = ["trigger", "invariant", "trap", "complexity", "bug", "pytrap", "trace", "salience", "other"]
GRADES = ["pass", "fail"]
TIMED_MODES = ("practice", "review", "mock")
LONG_FORMATS = ("machine-coding", "ai-assisted", "ml-coding")  # started on purpose, never picked by `next`
SOLVED = ("practicing", "retained", "ready")  # problem statuses: solved unaided at least once
RETAINED = ("retained", "ready")              # and solved unaided again after the delay
LISTS = ("blind75", "nc150", "roadmap")  # problems.json: the two lists, or a canonical problem outside both
BLOCK = 3  # a pattern's first problems stay together (worked, faded, solo); after that, new problems mix
LIVE = Path("sessions") / "current.json"  # the solve in progress, kept by `coach.py solve`
STAGES = [  # the solve protocol in SKILL.md: (stage, Polya phase). The pane repeats the names.
    ("Understand", "Understand"),
    ("Find an approach", "Devise a plan"),
    ("Build it", "Carry out the plan"),
    ("Check and finish", "Look back"),
]
RUNGS = ["none", "a general question", "a nudge for this problem", "the pattern name", "the invariant or state",
         "a skeleton with blanks", "one concrete sub-step", "the full worked solution"]
TOP_RUNG = len(RUNGS) - 1
UNAIDED_MAX_RUNG = 1   # a solve still counts as unaided with help up to this rung
ASSISTED_MIN_RUNG = 5  # from this rung on, the attempt is assisted
FOCUS_MINUTES = {"easy": 15, "medium": 25, "hard": 25}  # one genuine attempt = one focused block
DEFAULT_CONFIG = {
    "learner": "learner",
    "goal": "Ace coding and DSA interviews for AI engineer roles, and get better at planning programs in my head",
    "targets": ["Indian product companies and GCCs", "Global / US remote AI roles", "AI startups"],
    "language": "Python",
    "problem_list": "NeetCode 150",
    "weekly_hours": 11,
    "delay_days": 3,
    "time_caps_min": {"easy": 15, "medium": 25, "hard": 40},
    "review_cap_fraction": 0.3,
}


# --------------------------------------------------------------------------- shapes
# The dicts that pass between functions. They are plain dicts when the program runs; these classes
# only name the keys, for readers and editors. A test checks them against the real data.
class Attempt(TypedDict, total=False):
    """One line of learner/attempts.jsonl."""
    id: str
    date: str  # YYYY-MM-DD
    problem: str  # slug
    pattern: str
    difficulty: str
    mode: str
    outcome: str
    minutes: int | None
    hints: int  # the highest hint-ladder rung used
    assisted: bool
    confidence: int | None  # before starting, 1-5
    technique: str | None
    mistakes: list  # codes from MISTAKES
    complexity_stated: bool
    note: str
    skill_version: str
    source: str  # "cli", or the web chat a delta came from
    session: str  # the live solve it ended, when there was one


class ProblemStatus(TypedDict):
    """What the attempts on one problem add up to (problem_status)."""
    problem: str
    pattern: str
    difficulty: str
    attempts: int
    first: str  # date of the first attempt
    last: str
    last_outcome: str
    streak: int  # unaided solves in a row, ending at the latest attempt
    next_due: str  # date of the next re-solve
    status: str  # learning, practicing, retained or ready
    ids: list


class PatternRow(TypedDict):
    """One roadmap pattern with its progress (pattern_row)."""
    key: str
    name: str
    tier: int | None
    week: int | None  # the week the plan starts it
    target: int  # how many problems the plan asks for
    attempted: int
    practicing: int  # problems solved unaided at least once
    retained: int
    ready: int
    status: str  # not started, exploring, learning, practicing, retained or ready
    last_activity: str | None
    last_attempt: str | None
    next_problem: str | None  # the next canonical problem not yet attempted


class Journey(TypedDict):
    """The journey on one date (compute). Saved as journey.json; JOURNEY.md and learner/summary.md are drawn from it."""
    generated: str  # the date it was computed for
    skill_version: str
    learner: str
    goal: str
    targets: list
    plan: dict  # plan_clock
    focus: str | None  # a pattern key
    patterns: list  # of PatternRow, in roadmap order
    behind: list  # pattern keys
    this_week: list
    ahead: list
    problems: dict  # slug -> ProblemStatus
    due: dict  # due_items
    totals: dict
    weak_spots: list
    calibration: dict
    techniques: list  # the technique ledger, most trials first
    questions: list  # the last five
    artifacts: list
    sessions: list  # the last five, each a date and a one-line summary
    last_mock: str | None
    other_concepts: list  # concepts touched that are not roadmap patterns
    next_steps: list


# --------------------------------------------------------------------------- helpers
def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def today() -> date:
    forced = os.environ.get("DSA_TODAY")
    return date.fromisoformat(forced) if forced else date.today()


def parse_date(value: str | None, default: date | None = None) -> date:
    if not value:
        return default or today()
    try:
        return date.fromisoformat(value)
    except ValueError:
        die(f"bad date {value!r}; use YYYY-MM-DD")
    raise AssertionError  # unreachable


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        die(f"{path} is not valid JSON ({exc})")


def write_text(path: Path, text: str) -> None:
    """Write a temp file beside `path`, then rename it over `path`, so a reader never sees half a file.
    A symlinked `path` stays a link (the real file is replaced), and an existing file keeps its mode."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.urandom(6).hex()}.tmp")
    try:
        with open(tmp, "x", encoding="utf-8") as fh:  # a new file gets the umask's mode; mkstemp would make it 0600
            fh.write(text)
        if path.exists():
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                die(f"{path}:{n} is not valid JSON ({exc})")
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def next_id(prefix: str, existing: list, width: int = 4) -> str:
    nums = [int(x[len(prefix):]) for x in existing if isinstance(x, str) and x.startswith(prefix) and x[len(prefix):].isdigit()]
    return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"


def load_roadmap() -> dict:
    data = read_json(ASSETS / "roadmap.json", None)
    if data is None:
        die(f"missing {ASSETS / 'roadmap.json'}")
    return data


def load_catalogue() -> dict:
    data = read_json(ASSETS / "problems.json", None)
    if data is None:
        die(f"missing {ASSETS / 'problems.json'}")
    return data


def catalogue_issues(catalogue: dict, roadmap: dict) -> list:
    """What in problems.json doesn't fit the roadmap or the format: for validate."""
    issues, seen = [], set()
    patterns = {p["key"]: p for p in roadmap["patterns"]}
    issues += [f"problems.json: {key} isn't a roadmap pattern" for key in catalogue if key not in patterns]
    for key, p in patterns.items():
        listed = {r.get("slug") for r in catalogue.get(key, [])}
        if key not in LONG_FORMATS:
            issues += [f"problems.json: {key} lacks its canonical problem {s}"
                       for s in p.get("canonical", []) if s not in listed]
    for key, rows in catalogue.items():
        for r in rows:
            slug = r.get("slug", "")
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
                issues.append(f"problems.json: bad slug {slug!r} in {key}")
            elif slug in seen:
                issues.append(f"problems.json: {slug} is listed twice")
            seen.add(slug)
            if not r.get("title"):
                issues.append(f"problems.json: {slug} has no title")
            if r.get("difficulty") not in DIFFICULTIES:
                issues.append(f"problems.json: {slug} has difficulty {r.get('difficulty')!r}")
            if not r.get("lists") or set(r["lists"]) - set(LISTS):
                issues.append(f"problems.json: {slug} has lists {r.get('lists')}")
    return issues


def pattern_keys() -> list:
    return [p["key"] for p in load_roadmap()["patterns"]]


def problem_url(roadmap: dict, slug: str) -> str:
    return roadmap["problem_url"].format(slug=slug)


def template(name: str) -> str:
    path = ASSETS / "templates" / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def fmt_list(items, empty: str = "none") -> str:
    items = list(items)
    return ", ".join(items) if items else empty


# --------------------------------------------------------------------------- notebook location
def find_root(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
        if (p / "config.json").exists():
            return p.resolve()
        die(f"no notebook at {p} (missing config.json). Run `coach.py --root {p} init` first.")
    env = os.environ.get("DSA_NOTEBOOK")
    if env:
        p = Path(env).expanduser()
        if (p / "config.json").exists():
            return p.resolve()
        die(f"DSA_NOTEBOOK points to {p}, which has no config.json")
    candidates = [Path.cwd() / "notebook", Path.cwd()]
    if POINTER.exists():
        candidates.append(Path(POINTER.read_text(encoding="utf-8").strip()).expanduser())
    candidates.append(WORKSPACE / "notebook")
    for c in candidates:
        if (c / "config.json").exists():
            return c.resolve()
    die("no notebook found. Run `coach.py init` (optionally with --root PATH) or set DSA_NOTEBOOK.")
    raise AssertionError  # unreachable


def init_root(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    if os.environ.get("DSA_NOTEBOOK"):
        return Path(os.environ["DSA_NOTEBOOK"]).expanduser().resolve()
    return (WORKSPACE / "notebook").resolve()


# --------------------------------------------------------------------------- state
def usable_attempts(rows: list) -> list:
    """Attempts with the fields the analysis needs; the rest are reported by `validate`."""
    good = []
    for a in rows:
        try:
            date.fromisoformat(a["date"])
            if a.get("problem") and a.get("outcome") in OUTCOMES:
                good.append(a)
                continue
        except (KeyError, TypeError, ValueError):
            pass
        print(f"warning: skipping malformed attempt {a.get('id', '?')} (run `coach.py validate`)", file=sys.stderr)
    return good


def load_state(root: Path) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(read_json(root / "config.json", {}))
    concepts_dir = root / "concepts"
    inbox = root / "inbox"
    return {
        "root": root,
        "config": cfg,
        "attempts": usable_attempts(read_jsonl(root / "learner" / "attempts.jsonl")),
        "questions": read_jsonl(root / "learner" / "questions.jsonl"),
        "cards": read_json(root / "learner" / "cards.json", []),
        "registry": read_json(root / "artifacts" / "registry.json", []),
        "concepts": sorted(d.name for d in concepts_dir.iterdir() if d.is_dir()) if concepts_dir.exists() else [],
        "sessions": sorted(p.stem for p in (root / "sessions").glob("*.md")) if (root / "sessions").exists() else [],
        "inbox": sorted(p.name for p in inbox.glob("*.json")) if inbox.exists() else [],
        "preferences": (root / "learner" / "preferences.md").read_text(encoding="utf-8") if (root / "learner" / "preferences.md").exists() else "",
        "roadmap": load_roadmap(),
    }


def is_unaided(attempt: Attempt) -> bool:
    return (attempt.get("outcome") == "solved" and not attempt.get("assisted")
            and int(attempt.get("hints") or 0) <= UNAIDED_MAX_RUNG)


def review_cap(cfg: dict, on: date) -> int | None:
    try:
        target = date.fromisoformat(cfg.get("target_date", ""))
    except ValueError:
        return None
    left = (target - on).days
    if left <= 0:
        return None
    return max(1, int(left * float(cfg.get("review_cap_fraction", 0.3))))


def capped(interval: int, cfg: dict, on: date) -> int:
    cap = review_cap(cfg, on)
    return min(interval, cap) if cap else interval


def by_problem(attempts: list) -> dict:
    """Attempts grouped by problem, oldest first within each."""
    groups: dict = {}
    for attempt in sorted(attempts, key=lambda x: (x.get("date", ""), x.get("id", ""))):
        groups.setdefault(attempt["problem"], []).append(attempt)
    return groups


def problem_status(attempts: list, cfg: dict) -> ProblemStatus:
    """What the attempts on one problem (oldest first) add up to: its status and its next re-solve date."""
    first, last = attempts[0], attempts[-1]
    first_day, last_day = date.fromisoformat(first["date"]), date.fromisoformat(last["date"])
    caps = cfg.get("time_caps_min", DEFAULT_CONFIG["time_caps_min"])
    streak = 0  # unaided solves in a row, ending at the latest attempt
    for attempt in attempts:
        streak = streak + 1 if is_unaided(attempt) else 0
    interval = capped(RESOLVE_LADDER[min(streak, len(RESOLVE_LADDER) - 1)], cfg, last_day)
    unaided = [attempt for attempt in attempts if is_unaided(attempt)]
    delayed = [attempt for attempt in unaided
               if (date.fromisoformat(attempt["date"]) - first_day).days >= int(cfg["delay_days"])]
    # ready: a delayed unaided solve that was also timed, within the cap, with complexity stated
    ready = any(
        attempt.get("mode") in TIMED_MODES
        and attempt.get("minutes") is not None
        and int(attempt["minutes"]) <= int(caps.get(attempt.get("difficulty", "medium"), 25))
        and attempt.get("complexity_stated")
        for attempt in delayed
    )
    return {
        "problem": last["problem"],
        "pattern": last.get("pattern"),
        "difficulty": last.get("difficulty", "medium"),
        "attempts": len(attempts),
        "first": first["date"],
        "last": last["date"],
        "last_outcome": last.get("outcome"),
        "streak": streak,
        "next_due": (last_day + timedelta(days=interval)).isoformat(),
        "status": "ready" if ready else "retained" if delayed else "practicing" if unaided else "learning",
        "ids": [attempt.get("id") for attempt in attempts],
    }


def analyze_problems(state: dict) -> dict:
    """Every attempted problem's status, by slug."""
    return {slug: problem_status(attempts, state["config"]) for slug, attempts in by_problem(state["attempts"]).items()}


def technique_ledger(state: dict) -> dict:
    """Which teaching techniques are followed by unaided solves. A technique used on an attempt gets one trial:
    the first later attempt on that problem at least delay_days on. The trial succeeds if that attempt is unaided."""
    delay = int(state["config"]["delay_days"])
    ledger: dict = {}
    for attempts in by_problem(state["attempts"]).values():
        credited = set()
        for i, later in enumerate(attempts):
            if later.get("mode") == "ai":
                continue
            day = date.fromisoformat(later["date"])
            for earlier in attempts[:i]:
                technique = earlier.get("technique")
                if not technique or technique == "none" or earlier.get("id") in credited:
                    continue
                if (day - date.fromisoformat(earlier["date"])).days < delay:
                    continue
                credited.add(earlier.get("id"))
                entry = ledger.setdefault(f"{technique}|{earlier.get('pattern')}", {
                    "technique": technique, "pattern": earlier.get("pattern"), "trials": 0, "successes": 0, "evidence": []})
                entry["trials"] += 1
                entry["successes"] += 1 if is_unaided(later) else 0
                entry["evidence"].append(f"{earlier.get('id')}->{later.get('id')}")
    for entry in ledger.values():
        entry["estimate"] = round((entry["successes"] + 1) / (entry["trials"] + 2), 2)
        entry["provisional"] = entry["trials"] < 3
    return ledger


def is_card_due(card: dict, on: date) -> bool:
    """An active card whose review date has come."""
    return card.get("status") == "active" and bool(card.get("due")) and date.fromisoformat(card["due"]) <= on


def card_held(card: dict) -> bool:
    """True once a pass happened after a gap of HELD_DAYS or more."""
    prev = card.get("accepted") or card.get("created")
    for h in card.get("history", []):
        if prev and h.get("grade") == "pass" and (date.fromisoformat(h["date"]) - date.fromisoformat(prev)).days >= HELD_DAYS:
            return True
        prev = h.get("date")
    return False


def planned_week(row: PatternRow) -> int:
    """The week a pattern is planned for. One with no week counts as far in the future."""
    return row["week"] or 99


def plan_order(row: PatternRow) -> tuple:
    """Sort key for patterns: by planned week, then by tier."""
    return (planned_week(row), row["tier"] or 9)


def pick_new(rows: list, pattern: str | None = None, week: int | None = None) -> dict | None:
    """The next new problem, or the named pattern's next problem.

    Finish a started pattern's block of BLOCK problems first. Then start the next pattern in plan
    order once its week has come. Otherwise mix: the started pattern practised least recently.
    `block` is false after a pattern's block, and the coach then presents the problem unlabeled.
    """
    def item(row):
        return {"kind": "new", "pattern": row["key"], "name": row["name"], "problem": row["next_problem"],
                "first": row["attempted"] == 0, "block": row["attempted"] < BLOCK}

    if pattern:
        named = [row for row in rows if row["key"] == pattern]
        return item(named[0]) if named else None
    open_rows = [row for row in sorted(rows, key=plan_order)
                 if row["key"] not in LONG_FORMATS and row["attempted"] < row["target"]]
    started = [row for row in open_rows if row["attempted"]]
    in_block = next((row for row in started if row["attempted"] < BLOCK), None)
    if in_block:
        return item(in_block)
    fresh = next((row for row in open_rows if not row["attempted"]), None)
    if fresh and (not started or week is None or planned_week(fresh) <= week):
        return item(fresh)
    if started:
        return item(min(started, key=lambda row: row.get("last_attempt") or ""))
    return None


def pick_next(journey: Journey, pattern: str | None = None) -> dict:
    """One item to practise now. A named pattern skips everything due."""
    due = journey["due"]
    if not pattern:
        if due["inbox"]:
            return {"kind": "inbox", "files": due["inbox"]}
        if due["resolves"]:
            return dict(due["resolves"][0], kind="resolve")
        if due["cards"]:
            return {"kind": "cards", "count": len(due["cards"])}
    return pick_new(journey["patterns"], pattern, journey["plan"]["week"]) or {"kind": "none"}


# compute, one job per function ------------------------------------------------
def plan_clock(cfg: dict, roadmap: dict, on: date) -> dict:
    """Where `on` falls in the plan: the day, the week and the roadmap phase."""
    try:
        start = date.fromisoformat(cfg.get("start_date", on.isoformat()))
    except ValueError:
        start = on
    try:
        target = date.fromisoformat(cfg.get("target_date", ""))
    except ValueError:
        target = None
    day = (on - start).days + 1
    week = max(1, (day - 1) // 7 + 1)
    phases = roadmap["phases"]
    phase = next((ph["name"] for ph in phases if ph["weeks"][0] <= week <= ph["weeks"][1]), phases[-1]["name"])
    return {
        "start_date": start.isoformat(), "target_date": target.isoformat() if target else None,
        "day": day, "total_days": (target - start).days if target else None, "week": week,
        "plan_weeks": roadmap.get("plan_weeks", 12), "phase": phase, "weekly_hours": cfg.get("weekly_hours"),
    }


def last_activity(state: dict) -> dict:
    """The latest date anything touched each pattern or concept: an attempt, a question, an explainer or a card.
    A concept with only a notes folder is listed with an empty date."""
    latest: dict = {}

    def touch(key, when):
        if key:
            latest[key] = max(latest.get(key, ""), when or "")

    for attempt in state["attempts"]:
        touch(attempt.get("pattern"), attempt.get("date"))
    for question in state["questions"]:
        touch(question.get("concept"), question.get("date"))
    for artifact in state["registry"]:
        touch(artifact.get("concept"), artifact.get("updated") or artifact.get("created"))
    for card in state["cards"]:
        touch(card.get("concept"), card.get("created"))
    for concept in state["concepts"]:
        touch(concept, "")
    return latest


def pattern_row(pattern: dict, problems: dict, activity: dict) -> PatternRow:
    """One roadmap pattern with its counts and its status, from the problems attempted in it."""
    key, target = pattern["key"], int(pattern.get("target", 3))
    mine = [problem for problem in problems.values() if problem["pattern"] == key]
    practicing = sum(problem["status"] in SOLVED for problem in mine)
    retained = sum(problem["status"] in RETAINED for problem in mine)
    ready = sum(problem["status"] == "ready" for problem in mine)
    if not mine:
        status = "exploring" if key in activity else "not started"
    elif ready >= min(PATTERN_READY_AT, target):
        status = "ready"
    elif retained >= min(PATTERN_RETAINED_AT, target):
        status = "retained"
    elif practicing:
        status = "practicing"
    else:
        status = "learning"
    return {
        "key": key, "name": pattern["name"], "tier": pattern.get("tier"), "week": pattern.get("week"), "target": target,
        "attempted": len(mine), "practicing": practicing, "retained": retained, "ready": ready,
        "status": status, "last_activity": activity.get(key, "") or None,
        "last_attempt": max((problem["last"] for problem in mine), default=None),
        "next_problem": next((slug for slug in pattern.get("canonical", []) if slug not in problems), None),
    }


def pick_focus(rows: list, activity: dict) -> str | None:
    """The pattern in focus: the one touched most recently that isn't ready, else the next unstarted one in the plan."""
    by_key = {row["key"]: row for row in rows}
    recent = [(when, key) for key, when in activity.items() if key in by_key and by_key[key]["status"] != "ready"]
    if recent:
        return max(recent)[1]
    return next((row["key"] for row in sorted(rows, key=plan_order) if row["status"] == "not started"), None)


def due_items(state: dict, problems: dict, on: date) -> dict:
    """What is waiting on `on`: re-solves and cards (earliest due date first), draft cards and inbox deltas."""
    resolves = [{"problem": problem["problem"], "pattern": problem["pattern"], "due": problem["next_due"],
                 "overdue_days": (on - date.fromisoformat(problem["next_due"])).days, "status": problem["status"]}
                for problem in problems.values() if date.fromisoformat(problem["next_due"]) <= on]
    cards = sorted((card for card in state["cards"] if is_card_due(card, on)), key=lambda card: card["due"])
    return {
        "resolves": sorted(resolves, key=lambda item: item["due"]),
        "cards": [{"id": card["id"], "concept": card.get("concept"), "type": card.get("type"), "due": card["due"]} for card in cards],
        "drafts": sum(card.get("status") == "draft" for card in state["cards"]),
        "inbox": state["inbox"],
    }


def totals(state: dict, problems: dict) -> dict:
    attempts, cards = state["attempts"], state["cards"]
    active = [card for card in cards if card.get("status") == "active"]
    return {
        "problems": len(problems), "attempts": len(attempts), "unaided_solves": sum(is_unaided(attempt) for attempt in attempts),
        "retained": sum(problem["status"] in RETAINED for problem in problems.values()),
        "ready": sum(problem["status"] == "ready" for problem in problems.values()),
        "minutes": sum(int(attempt.get("minutes") or 0) for attempt in attempts),
        "sessions": len(state["sessions"]), "questions": len(state["questions"]),
        "cards_active": len(active), "cards_held": sum(card_held(card) for card in active),
        "cards_draft": sum(card.get("status") == "draft" for card in cards),
        "cards_retired": sum(card.get("status") == "retired" for card in cards),
        "explainers": len(state["registry"]),
    }


def weak_spots(attempts: list, on: date) -> list:
    """The three mistake codes logged most often in the last WEAK_SPOT_DAYS days."""
    since = on - timedelta(days=WEAK_SPOT_DAYS)
    counts: dict = {}
    for attempt in attempts:
        if date.fromisoformat(attempt["date"]) >= since:
            for code in attempt.get("mistakes") or []:
                counts[code] = counts.get(code, 0) + 1
    top = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:3]
    return [{"code": code, "count": count, "meaning": MISTAKES.get(code, "")} for code, count in top]


def calibration(attempts: list) -> dict:
    """Does the confidence he gives before an attempt match how it goes? The average before unaided solves,
    the average before the rest, and the latest misses at HIGH_CONFIDENCE or above."""
    rated = [attempt for attempt in attempts if attempt.get("confidence") is not None]
    unaided = [int(attempt["confidence"]) for attempt in rated if is_unaided(attempt)]
    other = [int(attempt["confidence"]) for attempt in rated if not is_unaided(attempt)]
    misses = [attempt for attempt in rated if int(attempt["confidence"]) >= HIGH_CONFIDENCE and not is_unaided(attempt)]
    return {
        "rated_attempts": len(rated),
        "avg_conf_unaided": round(sum(unaided) / len(unaided), 2) if unaided else None,
        "avg_conf_other": round(sum(other) / len(other), 2) if other else None,
        "high_confidence_misses": [{"id": attempt.get("id"), "problem": attempt.get("problem"), "date": attempt.get("date")}
                                   for attempt in misses[-5:]],
    }


def next_steps(journey: Journey) -> list:
    """Up to six suggestions for the session, in the order to do them. Reads the rest of the journey."""
    on, week, due = date.fromisoformat(journey["generated"]), journey["plan"]["week"], journey["due"]
    names = {row["key"]: row["name"] for row in journey["patterns"]}
    weeks = {row["key"]: row["week"] for row in journey["patterns"]}
    behind, this_week, last_mock = journey["behind"], journey["this_week"], journey["last_mock"]
    misses = journey["calibration"]["high_confidence_misses"]
    steps = []
    if due["inbox"]:
        steps.append(f"Import {len(due['inbox'])} session delta(s) waiting in inbox/ (`coach.py import`).")
    if due["resolves"]:
        steps.append("Re-solve from a blank page: " + ", ".join(item["problem"] for item in due["resolves"][:3])
                     + " (a plan-only check is fine for the first).")
    if due["cards"]:
        steps.append(f"Quiz: {len(due['cards'])} due card(s), about {max(2, len(due['cards']))} minutes (`coach.py quiz`).")
    new = pick_new(journey["patterns"], week=week)
    if new and not new["block"]:
        steps.append(f"Solve {new['problem']} unaided (mixed practice: name the pattern yourself)." if new["problem"]
                     else "Mixed practice: one new problem with the pattern unlabeled (`coach.py next` picks it).")
    elif new and new["problem"]:
        steps.append(f"Solve {new['problem']} unaided to move {new['name']} forward.")
    elif new:
        steps.append(f"Pick an unattempted problem from the NeetCode {new['name']} section.")
    if due["drafts"]:
        steps.append(f"Approve, edit or retire {due['drafts']} draft card(s) (`coach.py card list --drafts`).")
    if behind:
        steps.append(f"Behind plan: start {names[behind[0]]} (planned for week {weeks[behind[0]]}).")
    elif this_week:
        steps.append(f"This week's plan: start {fmt_list(names[key] for key in this_week)}.")
    if week >= MOCKS_FROM_WEEK and (not last_mock or (on - date.fromisoformat(last_mock)).days > MOCK_EVERY_DAYS):
        steps.append("Run a timed mock (`--mode mock`); the last one was " + (f"on {last_mock}." if last_mock else "never."))
    if misses:
        steps.append(f"Revisit high-confidence miss {misses[-1]['id']} ({misses[-1]['problem']}).")
    if not steps:
        steps.append("Nothing due. Start the next pattern in the plan or do an unlabeled mixed set.")
    return steps[:6]


def compute(state: dict, on: date | None = None) -> Journey:
    """The journey on one date, worked out from the notebook's state. Every view shows a part of it."""
    on = on or today()
    cfg, roadmap, attempts = state["config"], state["roadmap"], state["attempts"]
    plan = plan_clock(cfg, roadmap, on)
    problems = analyze_problems(state)
    activity = last_activity(state)
    rows = [pattern_row(pattern, problems, activity) for pattern in roadmap["patterns"]]
    week = plan["week"]
    unstarted = [row for row in rows if row["status"] == "not started"]
    journey: Journey = {
        "generated": on.isoformat(),
        "skill_version": SKILL_VERSION,
        "learner": cfg.get("learner"),
        "goal": cfg.get("goal"),
        "targets": cfg.get("targets", []),
        "plan": plan,
        "focus": pick_focus(rows, activity),
        "patterns": rows,
        "behind": [row["key"] for row in unstarted if planned_week(row) < week],
        "this_week": [row["key"] for row in unstarted if row["week"] == week],
        "ahead": [row["key"] for row in rows if row["status"] != "not started" and (row["week"] or 0) > week],
        "problems": problems,
        "due": due_items(state, problems, on),
        "totals": totals(state, problems),
        "weak_spots": weak_spots(attempts, on),
        "calibration": calibration(attempts),
        "techniques": sorted(technique_ledger(state).values(), key=lambda entry: (-entry["trials"], entry["technique"])),
        "questions": state["questions"][-5:],
        "artifacts": state["registry"],
        "sessions": [session_digest(state["root"], day) for day in state["sessions"][-5:]],
        "last_mock": max((attempt["date"] for attempt in attempts if attempt.get("mode") == "mock"), default=None),
        "other_concepts": sorted(set(activity) - {row["key"] for row in rows}),
    }
    journey["next_steps"] = next_steps(journey)  # it reads the rest of the journey, so it comes last
    return journey


# --------------------------------------------------------------------------- rendering
def render_journey(journey: Journey) -> str:
    plan = journey["plan"]
    by_key = {r["key"]: r for r in journey["patterns"]}
    focus = by_key.get(journey["focus"]) if journey["focus"] else None
    days = f"Day {plan['day']} of {plan['total_days']}" if plan["total_days"] else f"Day {plan['day']}"
    span = f"{plan['start_date']} → {plan['target_date']}" if plan["target_date"] else f"since {plan['start_date']}"
    out = [
        f"# Journey snapshot · {journey['generated']}",
        "",
        f"**Goal:** {journey['goal']}  ",
        f"**Targets:** {fmt_list(journey['targets'])}  ",
        f"**Plan:** {days} ({span}) · Week {plan['week']} of {plan['plan_weeks']} · Phase: {plan['phase']} · {plan['weekly_hours']} h/week  ",
        f"**Focus:** {focus['name'] + ' (' + focus['status'] + ')' if focus else 'not set'} · Skill v{journey['skill_version']}",
        "",
        "_Generated by `coach.py snapshot`. Don't edit by hand; change the logs and run it again._",
        "",
        "## Next steps",
        "",
    ]
    out += [f"{i}. {s}" for i, s in enumerate(journey["next_steps"], 1)]
    out += ["", "## Due today", ""]
    due = journey["due"]
    if not due["resolves"] and not due["cards"]:
        out.append("Nothing due.")
    else:
        out += ["| Type | Item | Due | Note |", "|---|---|---|---|"]
        for d in due["resolves"]:
            note = f"{d['overdue_days']} day(s) overdue" if d["overdue_days"] else "due today"
            out.append(f"| Re-solve | {d['problem']} ({d['pattern']}) | {d['due']} | {note} |")
        for c in due["cards"]:
            out.append(f"| Card | {c['id']} {c['type']} ({c['concept']}) | {c['due']} | |")
    out.append("")
    out.append(f"Draft cards to approve: {due['drafts']} · Session deltas in inbox: {len(due['inbox'])}")
    out += ["", "## Pattern map", "",
            "| Week | Pattern | Tier | Status | Attempted | Unaided | Retained | Ready | Target | Last activity |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(journey["patterns"], key=plan_order):
        out.append(f"| {r['week']} | {r['name']} | {r['tier']} | {r['status']} | {r['attempted']} | {r['practicing']} | {r['retained']} | {r['ready']} | {r['target']} | {r['last_activity'] or ''} |")
    started = sum(r["status"] != "not started" for r in journey["patterns"])
    out += ["", f"Started {started} of {len(journey['patterns'])} patterns. "
            + (f"Behind plan: {fmt_list(by_key[k]['name'] for k in journey['behind'])}. " if journey["behind"] else "Nothing from earlier weeks is behind. ")
            + (f"Planned this week: {fmt_list(by_key[k]['name'] for k in journey['this_week'])}. " if journey["this_week"] else "")
            + (f"Ahead of plan: {fmt_list(by_key[k]['name'] for k in journey['ahead'])}." if journey["ahead"] else "")]
    if journey["other_concepts"]:
        out.append(f"Other concepts touched: {fmt_list(journey['other_concepts'])}.")
    t = journey["totals"]
    out += ["", "## Totals", "",
            f"- Problems attempted: {t['problems']} · unaided solves: {t['unaided_solves']} · retained: {t['retained']} · ready: {t['ready']}",
            f"- Attempts logged: {t['attempts']} · minutes: {t['minutes']} · sessions: {t['sessions']}",
            f"- Cards: {t['cards_active']} active ({t['cards_held']} held at {HELD_DAYS}+ days), {t['cards_draft']} draft, {t['cards_retired']} retired",
            f"- Questions asked: {t['questions']} · explainers saved: {t['explainers']}"]
    out += ["", f"## Weak spots (last {WEAK_SPOT_DAYS} days)", ""]
    out += [f"- {w['code']} ({w['meaning']}): {w['count']}" for w in journey["weak_spots"]] or ["No mistakes logged yet."]
    cal = journey["calibration"]
    out += ["", "## Calibration", ""]
    if cal["rated_attempts"]:
        out.append(f"- Average confidence before unaided solves: {cal['avg_conf_unaided']}; before other attempts: {cal['avg_conf_other']} ({cal['rated_attempts']} rated attempts)")
        out += [f"- High-confidence miss: {m['id']} {m['problem']} ({m['date']})" for m in cal["high_confidence_misses"]]
    else:
        out.append("No confidence ratings yet. Log `--confidence 1-5` before each attempt.")
    out += ["", "## What seems to work (delayed evidence only)", ""]
    if journey["techniques"]:
        out += ["| Technique | Pattern | Delayed checks | Unaided | Estimate | |", "|---|---|---|---|---|---|"]
        for r in journey["techniques"]:
            out.append(f"| {r['technique']} | {r['pattern']} | {r['trials']} | {r['successes']} | {r['estimate']} | {'provisional' if r['provisional'] else ''} |")
    else:
        out.append("No delayed re-solves yet, so no technique has earned credit. Preferences don't count as evidence.")
    out += ["", "## Recent questions", ""]
    out += [f"- {q.get('date')} · {q.get('concept')}: {q.get('text')}" for q in reversed(journey["questions"])] or ["None yet."]
    out += ["", "## Saved explainers", ""]
    if journey["artifacts"]:
        for artifact in journey["artifacts"]:
            where = " · ".join(x for x in [f"[link]({artifact['url']})" if artifact.get("url") else "",
                                           f"`{artifact['file']}`" if artifact.get("file") else ""] if x)
            out.append(f"- {artifact.get('title')} ({artifact.get('concept')}, v{artifact.get('version', 1)}): {where}")
    else:
        out.append("None yet.")
    out += ["", "## Recent sessions", ""]
    out += [f"- {s['date']}: {s['summary']}" for s in reversed(journey["sessions"])] or ["None yet."]
    return "\n".join(out) + "\n"


def session_digest(root: Path, day: str) -> dict:
    """The date plus the first line of the latest entry in that day's session log."""
    path = root / "sessions" / f"{day}.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    entries = [e.strip() for e in text.split("\n## ")[1:]]
    summary = ""
    if entries:
        body = entries[-1].split("\n", 1)[1].strip() if "\n" in entries[-1] else ""
        summary = body.splitlines()[0] if body else ""
    return {"date": day, "summary": (summary[:157] + "...") if len(summary) > 160 else summary}


def render_summary(journey: Journey, preferences: str) -> str:
    plan = journey["plan"]
    by_key = {r["key"]: r for r in journey["patterns"]}
    lines = [
        f"DSA COACH LEARNER SUMMARY · generated {journey['generated']} by coach.py snapshot · skill {journey['skill_version']}",
        f"Learner: {journey['learner']} · Goal: {journey['goal']}",
        f"Targets: {fmt_list(journey['targets'])}",
        f"Plan: day {plan['day']}" + (f" of {plan['total_days']}" if plan["total_days"] else "") + f", week {plan['week']} of {plan['plan_weeks']}, phase {plan['phase']}, target date {plan['target_date']}",
        f"Focus: {by_key[journey['focus']]['name'] + ' (' + by_key[journey['focus']]['status'] + ')' if journey['focus'] else 'not set'}",
        "",
        "Patterns started (status, attempted/unaided/retained/ready of target):",
    ]
    started = [r for r in journey["patterns"] if r["status"] != "not started"]
    lines += [f"- {r['name']}: {r['status']}, {r['attempted']}/{r['practicing']}/{r['retained']}/{r['ready']} of {r['target']}" for r in started] or ["- none yet"]
    if journey["other_concepts"]:
        lines.append(f"Other concepts: {fmt_list(journey['other_concepts'])}")
    d = journey["due"]
    lines += ["", f"Due today: {len(d['resolves'])} re-solve(s) [{fmt_list(x['problem'] for x in d['resolves'][:5])}], {len(d['cards'])} card(s), {d['drafts']} draft card(s), {len(d['inbox'])} inbox delta(s)"]
    lines.append(f"Weak spots ({WEAK_SPOT_DAYS} days): " + fmt_list(f"{w['code']}×{w['count']}" for w in journey["weak_spots"]))
    cal = journey["calibration"]
    if cal["rated_attempts"]:
        lines.append(f"Calibration: avg confidence before unaided solves {cal['avg_conf_unaided'] if cal['avg_conf_unaided'] is not None else 'n/a'}, "
                     f"before other attempts {cal['avg_conf_other'] if cal['avg_conf_other'] is not None else 'n/a'}; "
                     f"high-confidence misses: {fmt_list(m['id'] for m in cal['high_confidence_misses'])}")
    else:
        lines.append("Calibration: no confidence ratings yet")
    if journey["sessions"]:
        last = journey["sessions"][-1]
        lines.append(f"Last session: {last['date']}: {last['summary']}")
    lines.append("Techniques with delayed evidence: " + fmt_list(f"{r['technique']}/{r['pattern']} {r['successes']}/{r['trials']}{' (provisional)' if r['provisional'] else ''}" for r in journey["techniques"][:5]))
    prefs = [ln.strip() for ln in preferences.splitlines() if ln.strip().startswith("- ")][:5]
    lines += ["", "Stated preferences (formatting defaults only, not evidence):"] + (prefs or ["- none recorded"])
    lines += ["", "Recent questions:"] + ([f"- {q.get('date')} {q.get('concept')}: {q.get('text')[:140]}" for q in reversed(journey["questions"][-3:])] or ["- none"])
    lines += ["", "Next steps:"] + [f"{i}. {s}" for i, s in enumerate(journey["next_steps"][:4], 1)]
    lines += ["", "Coach rules: attempt before answers; predict before reveal; credit only delayed unaided success; log everything with coach.py."]
    return "\n".join(lines[:60]) + "\n"


def write_snapshot(root: Path, on: date | None = None) -> Journey:
    state = load_state(root)
    journey = compute(state, on)
    write_json(root / "journey.json", journey)
    write_text(root / "JOURNEY.md", render_journey(journey))
    write_text(root / "learner" / "summary.md", render_summary(journey, state["preferences"]))
    write_json(root / "learner" / "techniques.json", journey["techniques"])
    return journey


# --------------------------------------------------------------------------- commands
NOTEBOOK_README = """# Notebook

Your learning data for the dsa-coach skill. Write to it through `coach.py` (see the skill's references/learner-model.md).

- `JOURNEY.md`: where you are. Regenerate with `coach.py snapshot`.
- `learner/`: attempts, questions, cards, preferences, and the generated summary and technique ledger.
- `concepts/` and `problems/`: your notes, plan cards, solutions and saved explainers.
- `sessions/`: one log per day.
- `artifacts/registry.json`: every saved or published explainer.
- `inbox/`: session deltas from web chats, waiting for `coach.py import`.
- `exports/`: context packs for web chats (`coach.py export`).
"""

PREFERENCES_TEMPLATE = """# Stated preferences

Formatting defaults only. These are not evidence about what helps learning; the technique ledger in JOURNEY.md is.

"""


def cmd_init(args) -> None:
    root = init_root(args.root)
    for sub in ["learner", "concepts", "problems", "sessions", "artifacts", "inbox/imported", "exports"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    cfg_path = root / "config.json"
    if cfg_path.exists():
        print(f"Notebook already initialized at {root}; leaving config.json as it is.")
    else:
        start = parse_date(args.start_date)
        target = parse_date(args.target_date) if args.target_date else start + timedelta(days=args.days)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "learner": args.name or DEFAULT_CONFIG["learner"],
            "start_date": start.isoformat(),
            "target_date": target.isoformat(),
            "weekly_hours": args.weekly_hours,
            "created_with": SKILL_VERSION,
        })
        if args.goal:
            cfg["goal"] = args.goal
        if args.targets:
            cfg["targets"] = [t.strip() for t in args.targets.split(";") if t.strip()]
        write_json(cfg_path, cfg)
        print(f"Created {cfg_path}")
    for rel, content in [
        ("learner/attempts.jsonl", ""), ("learner/questions.jsonl", ""),
        ("learner/preferences.md", PREFERENCES_TEMPLATE), ("README.md", NOTEBOOK_README),
    ]:
        p = root / rel
        if not p.exists():
            p.write_text(content, encoding="utf-8")
    for rel in ["learner/cards.json", "artifacts/registry.json"]:
        if not (root / rel).exists():
            write_json(root / rel, [])
    write_snapshot(root)
    print(f"Notebook ready at {root}. Snapshot written to {root / 'JOURNEY.md'}")


def ensure_problem_notes(root: Path, slug: str, pattern: str, difficulty: str, on: date) -> Path:
    path = root / "problems" / slug / "notes.md"
    if not path.exists():
        url = problem_url(load_roadmap(), slug)
        text = template("problem.md").format(
            problem=slug, url=url, pattern=pattern, difficulty=difficulty, date=on.isoformat(),
            plan_card=template("plan-card.md").strip(),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return path


def ensure_concept_notes(root: Path, slug: str, title: str | None, pattern: str | None, on: date) -> Path:
    path = root / "concepts" / slug / "notes.md"
    if not path.exists():
        text = template("concept.md").format(title=title or slug.replace("-", " ").title(), pattern=pattern or slug, date=on.isoformat())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return path


def is_date(value) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_attempt(a: dict, keys: list) -> list:
    errs = []
    if not a.get("problem"):
        errs.append("problem is required")
    if a.get("pattern") not in keys:
        errs.append(f"pattern {a.get('pattern')!r} is not in roadmap.json ({', '.join(keys)})")
    if a.get("mode", "practice") not in MODES:
        errs.append(f"mode must be one of {MODES}")
    if a.get("outcome") not in OUTCOMES:
        errs.append(f"outcome must be one of {OUTCOMES}")
    if a.get("difficulty", "medium") not in DIFFICULTIES:
        errs.append(f"difficulty must be one of {DIFFICULTIES}")
    try:
        if not 0 <= int(a.get("hints") or 0) <= TOP_RUNG:
            errs.append(f"hints must be 0-{TOP_RUNG}")
    except (TypeError, ValueError):
        errs.append(f"hints must be an integer 0-{TOP_RUNG}")
    conf = a.get("confidence")
    if conf is not None and (not isinstance(conf, int) or not 1 <= conf <= 5):
        errs.append("confidence must be 1-5 or null")
    if a.get("minutes") is not None and (not isinstance(a.get("minutes"), int) or a["minutes"] < 0):
        errs.append("minutes must be a non-negative integer")
    if a.get("technique") not in (None, *TECHNIQUES):
        errs.append(f"technique must be one of {TECHNIQUES}")
    bad = [m for m in a.get("mistakes") or [] if m not in MISTAKES]
    if bad:
        errs.append(f"unknown mistake codes {bad}; use {list(MISTAKES)}")
    if a.get("date") and not is_date(a["date"]):
        errs.append("date must be YYYY-MM-DD")
    return errs


def add_attempt(root: Path, a: dict, source: str = "cli") -> dict:
    existing = read_jsonl(root / "learner" / "attempts.jsonl")
    on = parse_date(a.get("date"))
    hints = int(a.get("hints") or 0)
    mode = a.get("mode", "practice")
    row = {
        "id": next_id("a", [x.get("id") for x in existing]),
        "date": on.isoformat(),
        "problem": slugify(a["problem"]),
        "pattern": a["pattern"],
        "difficulty": a.get("difficulty", "medium"),
        "mode": mode,
        "outcome": a["outcome"],
        "minutes": a.get("minutes"),
        "hints": hints,
        "assisted": bool(a.get("assisted")) or hints >= ASSISTED_MIN_RUNG or mode == "ai",
        "confidence": a.get("confidence"),
        "technique": a.get("technique"),
        "mistakes": list(a.get("mistakes") or []),
        "complexity_stated": bool(a.get("complexity_stated")),
        "note": a.get("note", ""),
        "skill_version": a.get("skill_version", SKILL_VERSION),
        "source": source,
    }
    if a.get("session"):  # the live solve it ended
        row["session"] = a["session"]
    append_jsonl(root / "learner" / "attempts.jsonl", row)
    ensure_problem_notes(root, row["problem"], row["pattern"], row["difficulty"], on)
    if row["note"]:
        notes = root / "problems" / row["problem"] / "notes.md"
        with notes.open("a", encoding="utf-8") as fh:
            fh.write(f"- {row['date']} ({row['id']}, {row['mode']}, {row['outcome']}): {row['note']}\n")
    return row


def split_codes(text: str | None) -> list:
    return [m.strip() for m in (text or "").split(",") if m.strip()]


def cmd_log_attempt(args) -> None:
    root = find_root(args.root)
    log_and_report(root, {
        "problem": args.problem, "pattern": args.pattern, "difficulty": args.difficulty, "mode": args.mode,
        "outcome": args.outcome, "minutes": args.minutes, "hints": args.hints, "assisted": args.assisted,
        "confidence": args.confidence, "technique": args.technique, "mistakes": split_codes(args.mistakes),
        "complexity_stated": args.complexity_stated, "note": args.note or "", "date": args.date,
    })


def log_and_report(root: Path, a: dict, as_json: bool = False) -> None:
    errs = validate_attempt(a, pattern_keys())
    if errs:
        die("; ".join(errs))
    row = add_attempt(root, a)
    write_snapshot(root)
    report_attempt(root, row, as_json)


def report_attempt(root: Path, row: dict, as_json: bool = False, already: bool = False) -> None:
    """What logging an attempt led to: a JSON receipt (--json), or one line for the chat."""
    info = analyze_problems(load_state(root))[row["problem"]]
    kind = "unaided" if is_unaided(row) else "assisted" if row["assisted"] else "not unaided"
    if as_json:
        print(json.dumps({"id": row["id"], "problem": row["problem"], "outcome": row["outcome"], "kind": kind,
                          "status": info["status"], "next_due": info["next_due"]}))
        return
    print(f"{'Already logged' if already else 'Logged'} {row['id']}: {row['problem']} ({row['pattern']}), "
          f"{row['outcome']}, {kind}. Problem status: {info['status']}. Next re-solve due {info['next_due']}.")


def logged_from(root: Path, session: str) -> dict | None:
    """The attempt a solve already logged, so ending it twice logs it once."""
    return next((a for a in read_jsonl(root / "learner" / "attempts.jsonl") if a.get("session") == session), None)


def add_question(root: Path, q: dict, source: str = "cli") -> dict:
    existing = read_jsonl(root / "learner" / "questions.jsonl")
    row = {
        "id": next_id("q", [x.get("id") for x in existing]),
        "date": parse_date(q.get("date")).isoformat(),
        "concept": slugify(q["concept"]),
        "text": q["text"].strip(),
        "source": source,
    }
    append_jsonl(root / "learner" / "questions.jsonl", row)
    notes = root / "concepts" / row["concept"] / "notes.md"
    if notes.exists():
        text = notes.read_text(encoding="utf-8")
        entry = f"- {row['date']} ({row['id']}): {row['text']}\n"
        marker = "## Questions asked\n"
        if marker in text:
            head, tail = text.split(marker, 1)
            tail = tail.lstrip("\n")
            gap = "" if tail.startswith("- ") else "\n"  # newest first; keep a blank line before the next heading
            notes.write_text(f"{head}{marker}\n{entry}{gap}{tail}", encoding="utf-8")
    return row


def cmd_log_question(args) -> None:
    root = find_root(args.root)
    row = add_question(root, {"concept": args.concept, "text": args.text, "date": args.date})
    write_snapshot(root)
    print(f"Logged {row['id']} under {row['concept']}.")


def append_session(root: Path, on: date, text: str, minutes: int | None, platform: str | None = None) -> Path:
    path = root / "sessions" / f"{on.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# Session log · {on.isoformat()}\n\n", encoding="utf-8")
    stamp = datetime.now().strftime("%H:%M")
    meta = " · ".join(x for x in [stamp, f"{minutes} min" if minutes else "", platform or ""] if x)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"## {meta}\n\n{text.strip()}\n\n")
    return path


def cmd_log_session(args) -> None:
    root = find_root(args.root)
    path = append_session(root, parse_date(args.date), args.summary, args.minutes, args.platform)
    write_snapshot(root)
    print(f"Appended to {path}")


def cmd_concept_add(args) -> None:
    root = find_root(args.root)
    slug = slugify(args.slug)
    path = ensure_concept_notes(root, slug, args.title, args.pattern, parse_date(args.date))
    write_snapshot(root)
    print(f"Concept notes at {path}")


# cards ----------------------------------------------------------------------
def load_cards(root: Path) -> list:
    return read_json(root / "learner" / "cards.json", [])


def save_cards(root: Path, cards: list) -> None:
    write_json(root / "learner" / "cards.json", cards)


def find_card(cards: list, cid: str) -> dict:
    for c in cards:
        if c.get("id") == cid:
            return c
    die(f"no card {cid}")
    raise AssertionError  # unreachable


def validate_card(c: dict) -> list:
    errs = []
    if not all(isinstance(c.get(k), str) and c[k].strip() for k in ("concept", "front", "back")):
        errs.append("concept, front and back are required")
    if c.get("type", "other") not in CARD_TYPES:
        errs.append(f"type must be one of {CARD_TYPES}")
    return errs


def add_card(root: Path, c: dict, source: str = "cli") -> dict:
    errs = validate_card(c)
    if errs:
        die("card " + "; ".join(errs))
    cards = load_cards(root)
    on = parse_date(c.get("date"))
    draft = c.get("draft", True)
    card = {
        "id": next_id("c", [x.get("id") for x in cards]),
        "concept": slugify(c["concept"]),
        "type": c.get("type", "other"),
        "front": c["front"].strip(),
        "back": c["back"].strip(),
        "status": "draft" if draft else "active",
        "created": on.isoformat(),
        "accepted": None if draft else on.isoformat(),
        "step": 0,
        "due": None if draft else (on + timedelta(days=1)).isoformat(),
        "history": [],
        "source": source,
    }
    cards.append(card)
    save_cards(root, cards)
    return card


def review_card(root: Path, cid: str, grade: str, on: date) -> dict:
    if grade not in GRADES:
        die(f"grade must be one of {GRADES}")
    cards = load_cards(root)
    card = find_card(cards, cid)
    if card.get("status") != "active":
        die(f"{cid} is {card.get('status')}; accept it first with `card accept --id {cid}`")
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(read_json(root / "config.json", {}))
    if grade == "pass":
        card["step"] = min(int(card.get("step", 0)) + 1, len(CARD_LADDER) - 1)
        interval = CARD_LADDER[card["step"]]
    else:
        card["step"] = 0
        interval = CARD_LADDER[0]
    card["due"] = (on + timedelta(days=capped(interval, cfg, on))).isoformat()
    card.setdefault("history", []).append({"date": on.isoformat(), "grade": grade})
    save_cards(root, cards)
    return card


def cmd_card(args) -> None:
    root = find_root(args.root)
    on = parse_date(getattr(args, "date", None))
    if args.card_cmd == "add":
        card = add_card(root, {"concept": args.concept, "type": args.type, "front": args.front, "back": args.back, "draft": args.draft, "date": args.date})
        print(f"Added {card['id']} ({card['status']}).")
    elif args.card_cmd == "review":
        card = review_card(root, args.id, args.grade, on)
        print(f"{card['id']}: {args.grade}. Next due {card['due']}.")
    elif args.card_cmd in ("accept", "retire", "edit"):
        cards = load_cards(root)
        card = find_card(cards, args.id)
        if args.card_cmd == "accept":
            card.update({"status": "active", "accepted": on.isoformat(), "step": 0, "due": (on + timedelta(days=1)).isoformat()})
        elif args.card_cmd == "retire":
            card.update({"status": "retired", "due": None})
        else:
            for field in ("front", "back", "type", "concept"):
                value = getattr(args, field, None)
                if value:
                    if field == "type" and value not in CARD_TYPES:
                        die(f"card type must be one of {CARD_TYPES}")
                    card[field] = slugify(value) if field == "concept" else value
        save_cards(root, cards)
        print(f"{card['id']}: {card['status']}" + (f", due {card['due']}" if card.get("due") else ""))
    elif args.card_cmd == "list":
        cards = load_cards(root)
        if args.drafts:
            cards = [c for c in cards if c.get("status") == "draft"]
        elif args.due:
            cards = [c for c in cards if is_card_due(c, on)]
        elif not args.all:
            cards = [c for c in cards if c.get("status") != "retired"]
        if args.concept:
            cards = [c for c in cards if c.get("concept") == slugify(args.concept)]
        if args.json:
            print(json.dumps(cards, indent=2, ensure_ascii=False))
            return
        if not cards:
            print("No cards match.")
        for c in cards:
            print(f"{c['id']} [{c['status']}{', due ' + c['due'] if c.get('due') else ''}] {c['type']} · {c['concept']}\n  Q: {c['front']}\n  A: {c['back']}")
        return  # a query: it runs without the lock, so it must not rewrite the snapshot
    write_snapshot(root)


def cmd_quiz(args) -> None:
    root = find_root(args.root)
    on = today()
    cards = [c for c in load_cards(root) if is_card_due(c, on)]
    if args.concept:
        cards = [c for c in cards if c.get("concept") == slugify(args.concept)]
    cards = sorted(cards, key=lambda c: c["due"])[: args.n]
    if args.json:
        print(json.dumps(cards, indent=2, ensure_ascii=False))
        return
    if not cards:
        print("No cards due. Nice.")
        return
    print(f"{len(cards)} card(s) due. Answer each before revealing; record with `card review --id ID --grade pass|fail`.\n")
    for i, c in enumerate(cards, 1):
        print(f"{i}. [{c['id']} · {c['type']} · {c['concept']}] {c['front']}")


def cmd_due(args) -> None:
    root = find_root(args.root)
    journey = compute(load_state(root), parse_date(args.date))
    d = journey["due"]
    if args.json:
        print(json.dumps(d, indent=2, ensure_ascii=False))
        return
    if not d["resolves"] and not d["cards"]:
        print("Nothing due.")
    for r in d["resolves"]:
        print(f"re-solve  {r['problem']} ({r['pattern']}) due {r['due']}" + (f", {r['overdue_days']} day(s) overdue" if r["overdue_days"] else ""))
    for c in d["cards"]:
        print(f"card      {c['id']} {c['type']} ({c['concept']}) due {c['due']}")
    if d["drafts"]:
        print(f"drafts    {d['drafts']} card(s) waiting for approval")
    if d["inbox"]:
        print(f"inbox     {len(d['inbox'])} delta(s) to import: {', '.join(d['inbox'])}")


def render_next(item: dict) -> str:
    kind = item["kind"]
    if kind == "inbox":
        return f"Import {len(item['files'])} session delta(s) waiting in inbox/: {', '.join(item['files'])}."
    if kind == "resolve":
        return f"Re-solve {item['problem']} ({item['pattern']}) from a blank page."
    if kind == "cards":
        return f"Quiz: {item['count']} due card(s)."
    mixed = "" if item.get("block", True) else " Mixed practice: present it without the pattern name."
    if kind == "new" and item["problem"]:
        return f"Solve {item['problem']} ({item['name']}).{mixed}"
    if kind == "new":
        return f"Pick an unattempted problem from the NeetCode {item['name']} section.{mixed}"
    return "Plan finished. Run a mock or an unlabeled mixed set."


def cmd_next(args) -> None:
    root = find_root(args.root)
    pattern = slugify(args.pattern) if args.pattern else None
    if pattern and pattern not in pattern_keys():
        die(f"unknown pattern {pattern}. Choose from: {', '.join(pattern_keys())}")
    item = pick_next(compute(load_state(root), parse_date(args.date)), pattern)
    print(json.dumps(item, indent=2, ensure_ascii=False) if args.json else render_next(item))



def list_progress(problems: list, name: str) -> dict:
    on = [x for x in problems if name in x["lists"]]
    return {"done": sum(x["status"] in SOLVED for x in on), "total": len(on)}


def map_view(journey: Journey, roadmap: dict, catalogue: dict) -> dict:
    """The panel's map: every pattern with its status, explainer and problems (Blind 75 first)."""
    explainers = {a["concept"]: a["file"] for a in journey["artifacts"] if (a.get("file") or "").endswith(".html")}
    due = {d["problem"] for d in journey["due"]["resolves"]}
    status = {r["key"]: r["status"] for r in journey["patterns"]}
    patterns = []
    for p in roadmap["patterns"]:
        problems = []
        for c in sorted(catalogue.get(p["key"], []), key=lambda c: "blind75" not in c["lists"]):
            seen = journey["problems"].get(c["slug"]) or {}
            problems.append({**c, "url": problem_url(roadmap, c["slug"]),
                             "status": seen.get("status", "not started"), "last_outcome": seen.get("last_outcome"),
                             "next_due": seen.get("next_due"), "due": c["slug"] in due})
        patterns.append({
            "key": p["key"], "name": p["name"], "week": p.get("week"), "tier": p.get("tier"),
            "cues": p.get("cues", []), "invariant": p.get("invariant", ""), "template": p.get("template", ""),
            "resources": p.get("resources", []), "status": status[p["key"]], "format": p["key"] in LONG_FORMATS,
            "explainer": explainers.get(p["key"]), "due": sum(x["due"] for x in problems),
            "lists": {name: list_progress(problems, name) for name in ("blind75", "nc150")},
            "problems": problems,
        })
    nxt = pick_next(journey)
    return {"plan": journey["plan"], "next": nxt, "next_text": render_next(nxt),
            "next_url": problem_url(roadmap, nxt["problem"]) if nxt.get("problem") else None,
            "patterns": patterns}


def render_map(view: dict) -> str:
    lines = []
    for p in view["patterns"]:
        b, n = p["lists"]["blind75"], p["lists"]["nc150"]
        lists = f" · Blind 75 {b['done']}/{b['total']} · NeetCode 150 {n['done']}/{n['total']}" if b["total"] or n["total"] else ""
        lines.append(f"{p['name']}: {p['status']}{lists}")
    return "\n".join(lines)


def cmd_map(args) -> None:
    root = find_root(args.root)
    state = load_state(root)
    journey, roadmap = compute(state, parse_date(args.date)), state["roadmap"]
    live = load_live(root, required=False)
    due = dict(journey["due"], resolves=[dict(r, url=problem_url(roadmap, r["problem"])) for r in journey["due"]["resolves"]])
    view = dict(map_view(journey, roadmap, load_catalogue()), due=due, live=live_view(live) if live else None)
    print(json.dumps(view, indent=2, ensure_ascii=False) if args.json else render_map(view))

# live solve -----------------------------------------------------------------
def now() -> datetime:
    forced = os.environ.get("DSA_NOW")
    return datetime.fromisoformat(forced) if forced else datetime.now().astimezone()


def stamp() -> str:
    return now().isoformat(timespec="seconds")


def load_live(root: Path, required: bool = True) -> dict | None:
    live = read_json(root / LIVE, None)
    if live is None and required:
        die("no live solve. Start one with `coach.py solve start --problem SLUG`.")
    return live


def block_minutes(block: dict, at: datetime, length: int) -> float:
    """Minutes in a focus block, from its start to its end (or now), less any idle time older solves paused out.
    A block counts at most its length: one left open overnight is one block, not the hours since."""
    end = datetime.fromisoformat(block["end"]) if block.get("end") else at
    minutes = (end - datetime.fromisoformat(block["start"])).total_seconds() / 60 - block.get("paused", 0) / 60
    return min(max(0.0, minutes), length)


def open_block(live: dict) -> dict | None:
    blocks = live["blocks"]
    return blocks[-1] if blocks and not blocks[-1].get("end") else None


def live_view(live: dict) -> dict:
    """The live solve plus what follows from it: stage and rung names, minutes so far, the current block, and
    `line`, the state in words (never the pattern: the app shows it as it is)."""
    at, current = now(), open_block(live)
    blocks, length = live["blocks"], live["block_minutes"]
    stage, phase = STAGES[live["stage"] - 1]
    minutes = int(sum(block_minutes(b, at, length) for b in blocks) + 0.5)
    elapsed = int(block_minutes(current, at, length)) if current else None
    timer = f"block {len(blocks)}: {elapsed} of {length} min" if current else f"on a break after block {len(blocks)}"
    return dict(live, stage_name=stage, phase=phase, rung_name=RUNGS[live["rung"]], minutes=minutes,
                block={"number": len(blocks), "open": current is not None, "length": length, "elapsed": elapsed},
                line=f"stage {live['stage']}/{len(STAGES)} {stage} · hint rung {live['rung']}/{TOP_RUNG} · {timer} · {minutes} min in all")


def describe_live(v: dict) -> str:
    """One line. The pattern appears only when the problem is labeled: naming it is hint rung 3."""
    label = f" ({v['pattern_name']})" if v["labeled"] else ""
    return f"{v['problem']}{label} · {v['line']}"


def print_live(live: dict) -> None:
    print(f"Live solve: {describe_live(live_view(live))}\nOn LeetCode: {live['url']}")


def solve_start(root: Path, args) -> None:
    if load_live(root, required=False):
        die("a solve is already live (`coach.py solve show`). End it with `solve end --outcome ...` or `solve end --discard`.")
    slug = slugify(args.problem)
    if not slug:
        die(f"--problem {args.problem!r} has no letters or digits to make a slug from")
    roadmap = load_roadmap()
    past = [a for a in usable_attempts(read_jsonl(root / "learner" / "attempts.jsonl")) if a["problem"] == slug]
    listed = next(((key, p) for key, ps in load_catalogue().items() for p in ps if p["slug"] == slug), (None, {}))
    canonical = next((p["key"] for p in roadmap["patterns"] if slug in p.get("canonical", [])), None)
    pattern = args.pattern or (past[-1]["pattern"] if past else None) or listed[0] or canonical
    if not pattern:
        die(f"which pattern is {slug}? Pass --pattern ({', '.join(pattern_keys())}).")
    difficulty = args.difficulty or (past[-1].get("difficulty") if past else None) or listed[1].get("difficulty") or "medium"
    pattern_name = next(p["name"] for p in roadmap["patterns"] if p["key"] == pattern)
    url = problem_url(roadmap, slug)
    live = {
        "problem": slug, "pattern": pattern, "pattern_name": pattern_name, "labeled": not args.unlabeled,
        "difficulty": difficulty, "mode": args.mode, "confidence": args.confidence, "url": url,
        "session_id": os.urandom(16).hex(), "stage": 1, "rung": 0, "block_minutes": FOCUS_MINUTES[difficulty],
        "blocks": [{"start": stamp(), "end": None}],
        "skill_version": SKILL_VERSION,
    }
    write_json(root / LIVE, live)
    print_live(live)


def solve_end(root: Path, live: dict, args) -> None:
    if args.discard:
        (root / LIVE).unlink()
        print(f"Discarded the live solve of {live['problem']}; nothing logged.")
        return
    if not args.outcome:
        die("give --outcome (solved, partial or failed), or --discard")
    session = live["session_id"]
    row = logged_from(root, session)  # an end that stopped after logging: finish it, don't log again
    if row:
        report_attempt(root, row, args.json, already=True)
    else:
        v = live_view(live)
        log_and_report(root, {
            "problem": live["problem"], "pattern": live["pattern"], "difficulty": live["difficulty"], "mode": live["mode"],
            "outcome": args.outcome, "minutes": v["minutes"] if args.minutes is None else args.minutes,
            "hints": live["rung"], "assisted": args.assisted,
            "confidence": live.get("confidence") if args.confidence is None else args.confidence,
            "technique": args.technique, "mistakes": split_codes(args.mistakes),
            "complexity_stated": args.complexity_stated, "note": args.note or "", "skill_version": live["skill_version"],
            "session": session,
        }, args.json)
    notes = root / "problems" / live["problem"] / "notes.md"
    if live.get("notes") and not re.search(rf"^### .* \({re.escape(session)}\)$", notes.read_text(encoding="utf-8"), re.M):
        add_stage_notes(notes, f"{today().isoformat()} ({session})", live["notes"])
    (root / LIVE).unlink()


def add_stage_notes(path: Path, heading: str, notes: dict) -> None:
    """A solve's stage notes go at the end of the ## Stage notes section, which sits just above ## Lessons
    (lesson lines are appended at the end of the file), so the oldest solve stays first.
    It expects the ## Lessons heading that problem.md starts with. In a hand-edited file without one, the section
    goes at the end of the file, and later lesson lines follow it."""
    bullets = "".join(f"- **{n}. {STAGES[int(n) - 1][0]}:** " + notes[n].strip().replace("\n", "\n  ") + "\n"
                      for n in sorted(notes, key=int))
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## Lessons[ \t\r]*$", text, re.M)  # a note's lines are indented, so none can match
    head, rest = (text[:m.start()], text[m.start():]) if m else (text, "")
    section = "" if re.search(r"^## Stage notes\n", head, re.M) else "## Stage notes\n\n"
    head = head.rstrip("\n") + f"\n\n{section}### {heading}\n\n{bullets}"
    path.write_text(head + ("\n" + rest if rest else ""), encoding="utf-8")


def cmd_solve(args) -> None:
    root, action = find_root(args.root), args.solve_cmd
    if action == "start":
        return solve_start(root, args)
    live = load_live(root, required=action != "show")
    if action == "show":
        if live is None:
            print("null" if args.json else "No live solve.")
        elif args.json:
            print(json.dumps(live_view(live), indent=2, ensure_ascii=False))
        else:
            print_live(live)
        return
    if action == "end":
        return solve_end(root, live, args)
    current = open_block(live)
    if action == "stage":
        live["stage"] = args.n
    elif action == "hint":
        live["rung"] = min(TOP_RUNG, max(live["rung"], args.rung if args.rung is not None else live["rung"] + 1))
    elif action == "note":  # a blank note clears the stage's note
        notes = live.setdefault("notes", {})
        if args.text.strip():
            notes[str(args.stage)] = args.text
        else:
            notes.pop(str(args.stage), None)
    elif action in ("break", "block"):
        if current:
            current["end"] = stamp()
        if action == "block":
            live["blocks"].append({"start": stamp(), "end": None})
    write_json(root / LIVE, live)
    print(f"Live solve: {describe_live(live_view(live))}")


# artifacts ------------------------------------------------------------------
def add_artifact(root: Path, a: dict, source: str = "cli") -> dict:
    reg = read_json(root / "artifacts" / "registry.json", [])
    on = parse_date(a.get("date")).isoformat()
    concept = slugify(a["concept"])
    rel_file = None
    if a.get("file"):
        src = Path(a["file"]).expanduser()
        if not src.exists():
            die(f"file not found: {src}")
        src = src.resolve()
        try:
            rel_file = str(src.relative_to(root))
        except ValueError:
            dest = root / "concepts" / concept / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            rel_file = str(dest.relative_to(root))
    match = next((x for x in reg if x.get("concept") == concept and x.get("title") == a["title"]), None)
    if match:
        match["version"] = int(a.get("version") or int(match.get("version", 1)) + 1)
        match["updated"] = on
        if a.get("url"):
            match["url"] = a["url"]
        if rel_file:
            match["file"] = rel_file
        if a.get("note"):
            match["note"] = a["note"]
        row = match
    else:
        row = {
            "id": next_id("x", [x.get("id") for x in reg]),
            "concept": concept, "title": a["title"], "url": a.get("url"), "file": rel_file,
            "version": int(a.get("version") or 1), "created": on, "updated": on,
            "note": a.get("note", ""), "source": source,
        }
        reg.append(row)
    write_json(root / "artifacts" / "registry.json", reg)
    return row


def cmd_artifact(args) -> None:
    root = find_root(args.root)
    if args.artifact_cmd == "add":
        if not args.url and not args.file:
            die("give --url, --file or both")
        row = add_artifact(root, {"concept": args.concept, "title": args.title, "url": args.url, "file": args.file,
                                  "version": args.version, "note": args.note, "date": args.date})
        write_snapshot(root)
        print(f"Registered {row['id']}: {row['title']} v{row['version']}" + (f" · {row['file']}" if row.get("file") else ""))
    else:
        for a in read_json(root / "artifacts" / "registry.json", []):
            print(f"{a['id']} {a['title']} ({a['concept']}, v{a.get('version', 1)}) {a.get('url') or ''} {a.get('file') or ''}")


# snapshot / status ----------------------------------------------------------
def cmd_snapshot(args) -> None:
    root = find_root(args.root)
    journey = write_snapshot(root, parse_date(args.date) if args.date else None)
    print(f"Snapshot written: {root / 'JOURNEY.md'} (day {journey['plan']['day']}, week {journey['plan']['week']}, {journey['plan']['phase']}).")
    if args.print:
        print()
        print((root / "JOURNEY.md").read_text(encoding="utf-8"))


def cmd_status(args) -> None:
    root = find_root(args.root)
    journey = write_snapshot(root)
    plan = journey["plan"]
    by_key = {r["key"]: r for r in journey["patterns"]}
    focus = by_key.get(journey["focus"]) if journey["focus"] else None
    d = journey["due"]
    print(f"DSA Coach · {journey['generated']} · day {plan['day']}" + (f"/{plan['total_days']}" if plan["total_days"] else "")
          + f" · week {plan['week']} · {plan['phase']} · skill {SKILL_VERSION}")
    print(f"Focus: {focus['name'] + ' (' + focus['status'] + ')' if focus else 'not set'}")
    print(f"Due: {len(d['resolves'])} re-solve(s) · {len(d['cards'])} card(s) · {d['drafts']} draft card(s) to approve · {len(d['inbox'])} inbox delta(s)")
    live = load_live(root, required=False)
    if live:
        print(f"Live solve: {describe_live(live_view(live))}. Resume it: `coach.py solve show --json`.")
    if not args.brief:
        started = [r for r in journey["patterns"] if r["status"] != "not started"]
        if started:
            print("Patterns: " + "; ".join(f"{r['name']} {r['status']} ({r['attempted']}/{r['target']})" for r in started))
        if journey["weak_spots"]:
            print("Weak spots: " + ", ".join(f"{w['code']}×{w['count']}" for w in journey["weak_spots"]))
    print("Next:")
    for i, s in enumerate(journey["next_steps"][: (3 if args.brief else 6)], 1):
        print(f"  {i}. {s}")
    print(f"Notebook: {root} (JOURNEY.md, learner/summary.md)")


# export / import ------------------------------------------------------------
def skill_body() -> str:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) == 3 else text


def delta_section() -> str:
    text = (SKILL_DIR / "references" / "platforms.md").read_text(encoding="utf-8")
    idx = text.find("## Session delta format")
    return text[idx:].strip() if idx >= 0 else ""


def cmd_export(args) -> None:
    root = find_root(args.root)
    journey = write_snapshot(root)
    on = today().isoformat()
    out = Path(args.out).expanduser() if args.out else root / "exports" / f"pack-{on}.md"
    due = journey["due"]
    lines = [
        f"# DSA Coach context pack · {on}",
        "",
        f"Attach this file at the start of a {args.platform} chat. You are the coach described below. "
        "This chat has no access to the notebook, so at the end of the session output a session delta "
        "(format at the bottom) for the learner to save into `notebook/inbox/`.",
        "",
        "## Learner summary",
        "",
        (root / "learner" / "summary.md").read_text(encoding="utf-8").strip(),
        "",
        "## Due items",
        "",
    ]
    lines += [f"- Re-solve {r['problem']} ({r['pattern']}), due {r['due']}" for r in due["resolves"]] or ["- No re-solves due."]
    cards = [c for c in load_cards(root) if c["id"] in {x["id"] for x in due["cards"]}]
    lines += [f"- Card {c['id']} ({c['type']}, {c['concept']}): Q: {c['front']} | A (hide until answered): {c['back']}" for c in cards] or ["- No cards due."]
    lines += ["", "## Coach instructions (SKILL.md)", "", skill_body(), "", delta_section(), ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len(out.read_text(encoding='utf-8')):,} characters). Attach it in the web chat.")


def validate_delta(d, keys: list, cards: dict) -> list:
    """Every problem in a delta, found before anything is written: an import writes all of it or nothing.
    cards: id -> status of the cards already in the notebook."""
    if not isinstance(d, dict):
        return ["a delta is a JSON object"]
    errs = []
    if d.get("format") != DELTA_FORMAT:
        errs.append(f"format must be {DELTA_FORMAT!r}")
    session = d.get("session") or {}
    if not isinstance(session, dict) or ("date" in session and not is_date(session["date"])):
        errs.append("session: date must be YYYY-MM-DD")
    for section in ("attempts", "questions", "cards", "card_reviews", "artifacts"):
        rows = d.get(section) or []
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            errs.append(f"{section} must be a list of objects")
            continue
        for i, r in enumerate(rows):
            if "date" in r and not is_date(r["date"]):
                errs.append(f"{section}[{i}]: date must be YYYY-MM-DD")
    if errs:
        return errs
    for i, a in enumerate(d.get("attempts") or []):
        errs += [f"attempts[{i}]: {e}" for e in validate_attempt(a, keys)]
    for i, q in enumerate(d.get("questions") or []):
        if not q.get("concept") or not q.get("text"):
            errs.append(f"questions[{i}]: concept and text are required")
    for i, c in enumerate(d.get("cards") or []):
        errs += [f"cards[{i}]: {e}" for e in validate_card(c)]
    for i, r in enumerate(d.get("card_reviews") or []):
        if r.get("id") not in cards:
            errs.append(f"card_reviews[{i}]: unknown card id {r.get('id')!r}")
        elif cards[r["id"]] != "active":
            errs.append(f"card_reviews[{i}]: {r['id']} is {cards[r['id']]}; only active cards can be reviewed")
        if r.get("grade") not in GRADES:
            errs.append(f"card_reviews[{i}]: grade must be pass or fail")
    for i, a in enumerate(d.get("artifacts") or []):
        if not a.get("concept") or not a.get("title") or not (a.get("url") or a.get("file")):
            errs.append(f"artifacts[{i}]: concept, title and url (or file) are required")
        elif a.get("file") and not Path(a["file"]).expanduser().is_file():
            errs.append(f"artifacts[{i}]: file not found: {a['file']}")
    return errs


def imported_before(root: Path, source: str) -> bool:
    rows = [*read_jsonl(root / "learner" / "attempts.jsonl"), *read_jsonl(root / "learner" / "questions.jsonl"),
            *load_cards(root), *read_json(root / "artifacts" / "registry.json", [])]
    return any(r.get("source") == source for r in rows)


def cmd_import(args) -> None:
    root = find_root(args.root)
    inbox = root / "inbox"
    files = [Path(f).expanduser() for f in args.files] if args.files else sorted(inbox.glob("*.json"))
    if not files:
        print("No session deltas to import.")
        return
    keys = pattern_keys()
    for path in files:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"skip {path.name}: can't read it ({exc})")
            continue
        errs = validate_delta(d, keys, {c.get("id"): c.get("status") for c in load_cards(root)})
        if errs:
            print(f"skip {path.name}: nothing imported; fix these fields and import again:")
            for e in errs:
                print(f"  - {e}")
            continue
        source = f"import:{path.name}"
        if imported_before(root, source):
            print(f"skip {path.name}: already imported (rows with source {source} exist)")
            continue
        session = d.get("session") or {}
        on = session.get("date") or today().isoformat()
        counts = {"attempts": 0, "questions": 0, "cards": 0, "card_reviews": 0, "artifacts": 0}
        for a in d.get("attempts") or []:
            version = a.get("skill_version") or d.get("skill_version") or SKILL_VERSION
            add_attempt(root, {**a, "date": a.get("date") or on, "skill_version": version}, source)
            counts["attempts"] += 1
        for q in d.get("questions") or []:
            add_question(root, {**q, "date": q.get("date") or on}, source)
            counts["questions"] += 1
        for c in d.get("cards") or []:
            add_card(root, {**c, "date": c.get("date") or on, "draft": c.get("draft", True)}, source)
            counts["cards"] += 1
        for r in d.get("card_reviews") or []:
            review_card(root, r["id"], r["grade"], parse_date(r.get("date") or on))
            counts["card_reviews"] += 1
        for a in d.get("artifacts") or []:
            add_artifact(root, {**a, "date": a.get("date") or on}, source)
            counts["artifacts"] += 1
        if session.get("summary"):
            append_session(root, parse_date(on), session["summary"], session.get("minutes"), d.get("platform"))
        if path.parent.resolve() == inbox.resolve():
            dest = inbox / "imported" / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            path.replace(dest)
        print(f"Imported {path.name}: " + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
    write_snapshot(root)


# packaging / install / validation ------------------------------------------
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def cmd_package(args) -> None:
    out = Path(args.out).expanduser() if args.out else WORKSPACE / "dist" / f"{SKILL_DIR.name}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SKILL_DIR.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts or path.name == ".DS_Store" or path.suffix == ".pyc":
                continue
            zf.write(path, Path(SKILL_DIR.name) / path.relative_to(SKILL_DIR))
            count += 1
    print(f"Wrote {out} ({count} files, {out.stat().st_size:,} bytes). Upload it as a skill in Claude, or unzip it into a skills folder.")


def place(src: Path, dst: Path, copy: bool, force: bool) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        if dst.is_symlink() and dst.resolve() == src.resolve() and not copy:
            return f"already linked: {dst}"
        if not force:
            return f"skipped {dst}: it already exists (use --force to replace it)"
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    if copy:
        shutil.copytree(src, dst, ignore=IGNORE)
        return f"copied to {dst}"
    dst.symlink_to(os.path.relpath(src, dst.parent), target_is_directory=True)
    return f"linked {dst} -> {os.path.relpath(src, dst.parent)}"


def cmd_install(args) -> None:
    claude = args.claude or not (args.claude or args.codex)
    codex = args.codex or not (args.claude or args.codex)
    base = Path.home() if args.user else WORKSPACE
    msgs = []
    if claude:
        msgs.append(place(SKILL_DIR, base / ".claude" / "skills" / SKILL_DIR.name, args.copy, args.force))
    if codex:
        msgs.append(place(SKILL_DIR, base / ".agents" / "skills" / SKILL_DIR.name, args.copy, args.force))
    if claude and not args.user and not args.no_hook:
        msgs.append(install_hook())
    if args.user:
        nb = WORKSPACE / "notebook"
        if (nb / "config.json").exists():
            POINTER.parent.mkdir(parents=True, exist_ok=True)
            POINTER.write_text(str(nb.resolve()) + "\n", encoding="utf-8")
            msgs.append(f"notebook pointer written to {POINTER}")
    for m in msgs:
        print(m)


def install_hook() -> str:
    """The SessionStart status hook. Removes the guard and activity hooks that versions before 0.9.0 installed."""
    path = WORKSPACE / ".claude" / "settings.json"
    base = 'python3 "$CLAUDE_PROJECT_DIR/skills/dsa-coach/scripts/coach.py" --root "$CLAUDE_PROJECT_DIR/notebook"'
    command = f"{base} status --brief"
    settings = read_json(path, {}) if path.exists() else {}
    hooks = settings.setdefault("hooks", {})
    for event in list(hooks):  # coach.py's own hooks other than the status one are from older versions
        groups = [dict(g, hooks=[h for h in g.get("hooks", []) if not h.get("command", "").startswith(base)
                                 or (event == "SessionStart" and h["command"] == command)]) for g in hooks[event]]
        hooks[event] = [g for g in groups if g["hooks"]]
        if not hooks[event]:
            del hooks[event]
    starts = hooks.setdefault("SessionStart", [])
    if any(h.get("command") == command for g in starts for h in g.get("hooks", [])):
        msg = f"SessionStart hook already present in {path}"
    else:
        starts.append({"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command", "command": command}]})
        msg = f"SessionStart hook added to {path} (Claude Code loads your status at the start of each session)"
    write_json(path, settings)
    return msg


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    data = {}
    for line in block.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def cmd_validate(args) -> None:
    issues = []
    skill_md = SKILL_DIR / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        issues.append(f"SKILL.md name {name!r} must be 1-64 chars of a-z, 0-9 and single hyphens")
    if name != SKILL_DIR.name:
        issues.append(f"SKILL.md name {name!r} must match the folder name {SKILL_DIR.name!r}")
    if not 1 <= len(desc) <= 1024:
        issues.append(f"description is {len(desc)} characters (1-1024 allowed)")
    if len(fm.get("compatibility", "")) > 500:
        issues.append("compatibility is longer than 500 characters")
    extra = set(fm) - {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    if extra:
        issues.append(f"frontmatter keys outside the Agent Skills spec: {sorted(extra)}")
    version = re.search(r'^\s+version:\s*"?([^"\s]+)', text.split("---", 2)[1], re.M)
    if not version or version.group(1) != SKILL_VERSION:
        issues.append(f"SKILL.md metadata.version {version and version.group(1)!r} must match SKILL_VERSION {SKILL_VERSION!r} in coach.py")
    n_lines = text.count("\n") + 1
    if n_lines >= 500:
        issues.append(f"SKILL.md has {n_lines} lines; keep it under 500")
    for ref in re.findall(r"references/[a-z0-9\-]+\.md|assets/[a-z0-9\-/]+\.json", text):
        if not (SKILL_DIR / ref).exists():
            issues.append(f"SKILL.md mentions {ref}, which doesn't exist")
    roadmap = load_roadmap()
    keys = [p["key"] for p in roadmap["patterns"]]
    if len(keys) != len(set(keys)):
        issues.append("roadmap.json has duplicate pattern keys")
    issues += catalogue_issues(load_catalogue(), roadmap)
    root = None
    try:
        root = find_root(args.root) if (args.root or os.environ.get("DSA_NOTEBOOK") or (Path.cwd() / "notebook" / "config.json").exists() or (WORKSPACE / "notebook" / "config.json").exists()) else None
    except SystemExit:
        root = None
    if root:
        for i, a in enumerate(read_jsonl(root / "learner" / "attempts.jsonl")):
            issues += [f"attempts line {i + 1} ({a.get('id')}): {e}" for e in validate_attempt(a, keys)]
        for c in read_json(root / "learner" / "cards.json", []):
            if c.get("type") not in CARD_TYPES or c.get("status") not in ("draft", "active", "retired"):
                issues.append(f"card {c.get('id')}: bad type or status")
        read_json(root / "artifacts" / "registry.json", [])
    print(f"Skill: {name} v{SKILL_VERSION} · SKILL.md {n_lines} lines · description {len(desc)} chars")
    if root:
        print(f"Notebook: {root}")
    if issues:
        print("Issues:")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    print("OK")


# --------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coach.py", description="Learning notebook for the dsa-coach skill.")
    p.add_argument("--root", help="notebook folder (default: $DSA_NOTEBOOK, ./notebook, or the workspace's notebook/)")
    p.add_argument("--version", action="version", version=f"dsa-coach {SKILL_VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create the notebook folder and config")
    s.add_argument("--name")
    s.add_argument("--goal")
    s.add_argument("--targets", help="semicolon-separated list")
    s.add_argument("--start-date")
    s.add_argument("--target-date")
    s.add_argument("--days", type=int, default=90, help="plan length when --target-date is not given")
    s.add_argument("--weekly-hours", type=int, default=11)
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("status", help="where you are and what's due (also refreshes the snapshot)")
    s.add_argument("--brief", action="store_true")
    s.set_defaults(func=cmd_status)

    log = sub.add_parser("log", help="log an attempt, a question or a session").add_subparsers(dest="log_cmd", required=True)
    s = log.add_parser("attempt")
    s.add_argument("--problem", required=True, help="LeetCode slug or a short name")
    s.add_argument("--pattern", required=True, choices=pattern_keys())
    s.add_argument("--difficulty", default="medium", choices=DIFFICULTIES)
    s.add_argument("--mode", default="practice", choices=MODES)
    s.add_argument("--outcome", required=True, choices=OUTCOMES)
    s.add_argument("--minutes", type=int)
    s.add_argument("--hints", type=int, default=0, help=f"highest hint-ladder rung used, 0-{TOP_RUNG}")
    s.add_argument("--assisted", action="store_true", help="saw a solution or used AI")
    s.add_argument("--confidence", type=int, choices=range(1, 6), help="confidence before starting, 1-5")
    s.add_argument("--technique", choices=TECHNIQUES)
    s.add_argument("--mistakes", help=f"comma-separated codes: {', '.join(MISTAKES)}")
    s.add_argument("--complexity-stated", action="store_true")
    s.add_argument("--note")
    s.add_argument("--date")
    s.set_defaults(func=cmd_log_attempt)
    s = log.add_parser("question")
    s.add_argument("--concept", required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--date")
    s.set_defaults(func=cmd_log_question)
    s = log.add_parser("session")
    s.add_argument("--summary", required=True)
    s.add_argument("--minutes", type=int)
    s.add_argument("--platform")
    s.add_argument("--date")
    s.set_defaults(func=cmd_log_session)

    s = sub.add_parser("concept", help="create concept notes").add_subparsers(dest="concept_cmd", required=True).add_parser("add")
    s.add_argument("--slug", required=True)
    s.add_argument("--title")
    s.add_argument("--pattern")
    s.add_argument("--date")
    s.set_defaults(func=cmd_concept_add)

    card = sub.add_parser("card", help="retrieval cards").add_subparsers(dest="card_cmd", required=True)
    s = card.add_parser("add")
    s.add_argument("--concept", required=True)
    s.add_argument("--type", default="other", choices=CARD_TYPES)
    s.add_argument("--front", required=True)
    s.add_argument("--back", required=True)
    s.add_argument("--draft", action="store_true", help="needs the learner's approval before it is scheduled")
    s.add_argument("--date")
    s = card.add_parser("review")
    s.add_argument("--id", required=True)
    s.add_argument("--grade", required=True, choices=GRADES)
    s.add_argument("--date")
    for name in ("accept", "retire"):
        s = card.add_parser(name)
        s.add_argument("--id", required=True)
        s.add_argument("--date")
    s = card.add_parser("edit")
    s.add_argument("--id", required=True)
    s.add_argument("--front")
    s.add_argument("--back")
    s.add_argument("--type")
    s.add_argument("--concept")
    s = card.add_parser("list")
    s.add_argument("--due", action="store_true")
    s.add_argument("--drafts", action="store_true")
    s.add_argument("--all", action="store_true", help="include retired cards")
    s.add_argument("--concept")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    card.required = True
    for name, sp in card.choices.items():
        sp.set_defaults(func=cmd_card, lock=name != "list")

    s = sub.add_parser("quiz", help="due card fronts (answers with --json)")
    s.add_argument("--n", type=int, default=10)
    s.add_argument("--concept")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_quiz, lock=False)

    s = sub.add_parser("due", help="list due re-solves and cards")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    s.set_defaults(func=cmd_due, lock=False)

    s = sub.add_parser("next", help="the one thing to practise now")
    s.add_argument("--pattern", help="pick a new problem from this pattern, skipping anything due")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    s.set_defaults(func=cmd_next, lock=False)

    s = sub.add_parser("map", help="every pattern with its status, explainer and problems, plus what's due and the live solve (the panel's data)")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    s.set_defaults(func=cmd_map, lock=False)

    solve = sub.add_parser("solve", help="the live solve: stage, hint rung and focus blocks").add_subparsers(dest="solve_cmd", required=True)
    s = solve.add_parser("start", help="start a solve; he writes and runs the code on LeetCode")
    s.add_argument("--problem", required=True, help="LeetCode slug or a short name")
    s.add_argument("--pattern", choices=pattern_keys(), help="default: an earlier attempt's, the problem list's, or the roadmap's")
    s.add_argument("--difficulty", choices=DIFFICULTIES, help="default: an earlier attempt's, the problem list's, or medium")
    s.add_argument("--mode", default="practice", choices=MODES)
    s.add_argument("--confidence", type=int, choices=range(1, 6), help="confidence before starting, 1-5")
    s.add_argument("--unlabeled", action="store_true", help="mixed practice: keep the pattern out of the status")
    s = solve.add_parser("stage", help="move to a solve-protocol stage")
    s.add_argument("n", type=int, choices=range(1, len(STAGES) + 1))
    s = solve.add_parser("hint", help="record the next hint rung (or --rung N); the highest rung is kept")
    s.add_argument("--rung", type=int, choices=range(1, TOP_RUNG + 1))
    s = solve.add_parser("note", help="save the learner's note for a stage (replaces that stage's note)")
    s.add_argument("--stage", type=int, required=True, choices=range(1, len(STAGES) + 1))
    s.add_argument("--text", required=True)
    solve.add_parser("break", help="end the current focus block")
    solve.add_parser("block", help="start a new focus block")
    s = solve.add_parser("show", help="the live solve")
    s.add_argument("--json", action="store_true")
    s = solve.add_parser("end", help="log the attempt from the live solve, or --discard it")
    s.add_argument("--outcome", choices=OUTCOMES)
    s.add_argument("--discard", action="store_true", help="drop the live solve without logging")
    s.add_argument("--minutes", type=int, help="default: the minutes in focus blocks, each counted up to its length")
    s.add_argument("--assisted", action="store_true", help="saw a solution or used AI")
    s.add_argument("--confidence", type=int, choices=range(1, 6), help="default: the one given at start")
    s.add_argument("--technique", choices=TECHNIQUES)
    s.add_argument("--mistakes", help=f"comma-separated codes: {', '.join(MISTAKES)}")
    s.add_argument("--complexity-stated", action="store_true")
    s.add_argument("--note")
    s.add_argument("--json", action="store_true", help="print the receipt: id, outcome, kind, status, next_due")
    for name, sp in solve.choices.items():
        sp.set_defaults(func=cmd_solve, lock=name != "show")

    art = sub.add_parser("artifact", help="saved explainers and published pages").add_subparsers(dest="artifact_cmd", required=True)
    s = art.add_parser("add")
    s.add_argument("--concept", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--url")
    s.add_argument("--file")
    s.add_argument("--version", type=int)
    s.add_argument("--note")
    s.add_argument("--date")
    s.set_defaults(func=cmd_artifact)
    s = art.add_parser("list")
    s.set_defaults(func=cmd_artifact, lock=False)

    s = sub.add_parser("snapshot", help="regenerate JOURNEY.md, journey.json and learner/summary.md")
    s.add_argument("--date", help="compute as of this date")
    s.add_argument("--print", action="store_true", help="also print JOURNEY.md")
    s.set_defaults(func=cmd_snapshot)

    s = sub.add_parser("export", help="write a context pack for a web chat")
    s.add_argument("--platform", default="Claude or ChatGPT web")
    s.add_argument("--out")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("import", help="import session deltas (default: everything in inbox/)")
    s.add_argument("files", nargs="*")
    s.set_defaults(func=cmd_import)

    s = sub.add_parser("package", help="zip the skill for uploading to Claude")
    s.add_argument("--out")
    s.set_defaults(func=cmd_package, lock=False)

    s = sub.add_parser("install", help="make the skill visible to Claude Code and Codex")
    s.add_argument("--claude", action="store_true", help="only Claude Code (.claude/skills)")
    s.add_argument("--codex", action="store_true", help="only Codex / ChatGPT desktop (.agents/skills)")
    s.add_argument("--user", action="store_true", help="install for your user account instead of this workspace")
    s.add_argument("--copy", action="store_true", help="copy instead of symlinking")
    s.add_argument("--force", action="store_true", help="replace an existing install")
    s.add_argument("--no-hook", action="store_true", help="don't add the Claude Code SessionStart hook")
    s.set_defaults(func=cmd_install, lock=False)

    s = sub.add_parser("validate", help="check the skill against the Agent Skills spec and the notebook files")
    s.set_defaults(func=cmd_validate, lock=False)
    return p


@contextmanager
def notebook_lock(root: Path, timeout: float = 5):
    """One writer at a time across processes (a hook, the coach, another agent). Stdlib file locking."""
    path = root / "sessions" / ".notebook.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            def lock(mode):
                handle.seek(0)
                msvcrt.locking(handle.fileno(), mode, 1)
            acquire, release = (lambda: lock(msvcrt.LK_NBLCK)), (lambda: lock(msvcrt.LK_UNLCK))
        else:
            import fcntl
            acquire = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # noqa: E731
            release = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # noqa: E731
        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("the notebook is busy; try again in a moment") from None
                time.sleep(0.025)
        try:
            yield
        finally:
            release()


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if not getattr(args, "lock", True):  # only a command defined with lock=False runs without the lock
        return args.func(args)
    root = init_root(args.root) if args.cmd == "init" else find_root(args.root)
    try:
        with notebook_lock(root):
            args.func(args)
    except TimeoutError as exc:
        die(str(exc))


if __name__ == "__main__":
    main()
