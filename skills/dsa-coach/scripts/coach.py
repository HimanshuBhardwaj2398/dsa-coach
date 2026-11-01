#!/usr/bin/env python3
"""coach.py: the learning-notebook CLI behind the dsa-coach skill.

Standard library only, Python 3.9+. Run `python3 coach.py --help`.

The notebook is found through --root, then $DSA_NOTEBOOK, then ./notebook,
then the current folder, then ~/.config/dsa-coach/notebook.txt, then the
`notebook/` folder of the workspace the skill lives in.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

SKILL_VERSION = "0.2.0"
SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
WORKSPACE = SKILL_DIR.parent.parent  # <workspace>/skills/dsa-coach
POINTER = Path.home() / ".config" / "dsa-coach" / "notebook.txt"

DELTA_FORMAT = "dsa-coach-delta/1"
RESOLVE_LADDER = [1, 3, 7, 14, 30]
CARD_LADDER = [1, 3, 7, 14, 30, 60]
HELD_DAYS = 5
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


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def pattern_keys() -> list:
    return [p["key"] for p in load_roadmap()["patterns"]]


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


def is_unaided(a: dict) -> bool:
    return a.get("outcome") == "solved" and not a.get("assisted") and int(a.get("hints") or 0) <= 1


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
    groups: dict = {}
    for a in sorted(attempts, key=lambda x: (x.get("date", ""), x.get("id", ""))):
        groups.setdefault(a["problem"], []).append(a)
    return groups


def analyze_problems(state: dict) -> dict:
    cfg = state["config"]
    delay = int(cfg.get("delay_days", 3))
    caps = cfg.get("time_caps_min", DEFAULT_CONFIG["time_caps_min"])
    out = {}
    for slug, rows in by_problem(state["attempts"]).items():
        first = date.fromisoformat(rows[0]["date"])
        streak = 0
        for a in rows:
            streak = streak + 1 if is_unaided(a) else 0
        last = rows[-1]
        last_day = date.fromisoformat(last["date"])
        interval = capped(RESOLVE_LADDER[min(streak, len(RESOLVE_LADDER) - 1)], cfg, last_day)
        unaided = [a for a in rows if is_unaided(a)]
        delayed = [a for a in unaided if (date.fromisoformat(a["date"]) - first).days >= delay]
        retained = bool(delayed)
        # ready: a delayed unaided solve that was also timed, within the cap, with complexity stated
        ready = any(
            a.get("mode") in TIMED_MODES
            and a.get("minutes") is not None
            and int(a["minutes"]) <= int(caps.get(a.get("difficulty", "medium"), 25))
            and a.get("complexity_stated")
            for a in delayed
        )
        status = "ready" if ready else "retained" if retained else "practicing" if unaided else "learning"
        out[slug] = {
            "problem": slug,
            "pattern": last.get("pattern"),
            "difficulty": last.get("difficulty", "medium"),
            "attempts": len(rows),
            "first": rows[0]["date"],
            "last": last["date"],
            "last_outcome": last.get("outcome"),
            "streak": streak,
            "next_due": (last_day + timedelta(days=interval)).isoformat(),
            "status": status,
            "ids": [a.get("id") for a in rows],
        }
    return out


def technique_ledger(state: dict) -> dict:
    delay = int(state["config"].get("delay_days", 3))
    ledger: dict = {}
    for rows in by_problem(state["attempts"]).values():
        credited = set()
        for i, a in enumerate(rows):
            if a.get("mode") == "ai":
                continue
            day = date.fromisoformat(a["date"])
            for e in rows[:i]:
                tech = e.get("technique")
                if not tech or tech == "none" or e.get("id") in credited:
                    continue
                if (day - date.fromisoformat(e["date"])).days < delay:
                    continue
                credited.add(e.get("id"))
                key = f"{tech}|{e.get('pattern')}"
                row = ledger.setdefault(key, {"technique": tech, "pattern": e.get("pattern"), "trials": 0, "successes": 0, "evidence": []})
                row["trials"] += 1
                row["successes"] += 1 if is_unaided(a) else 0
                row["evidence"].append(f"{e.get('id')}->{a.get('id')}")
    for row in ledger.values():
        row["estimate"] = round((row["successes"] + 1) / (row["trials"] + 2), 2)
        row["provisional"] = row["trials"] < 3
    return ledger


def card_due(card: dict) -> date | None:
    due = card.get("due")
    return date.fromisoformat(due) if due else None


def card_held(card: dict) -> bool:
    """True once a pass happened after a gap of HELD_DAYS or more."""
    prev = card.get("accepted") or card.get("created")
    for h in card.get("history", []):
        if prev and h.get("grade") == "pass" and (date.fromisoformat(h["date"]) - date.fromisoformat(prev)).days >= HELD_DAYS:
            return True
        prev = h.get("date")
    return False


def pick_new(rows: list, pattern: str | None = None) -> dict | None:
    """The next new problem: first pattern in plan order under its target, or the named pattern."""
    pool = [r for r in rows if r["key"] == pattern] if pattern else [r for r in rows if r["key"] not in LONG_FORMATS]
    for r in sorted(pool, key=lambda r: (r["week"] or 99, r["tier"] or 9)):
        if pattern or r["attempted"] < r["target"]:
            return {"kind": "new", "pattern": r["key"], "name": r["name"], "problem": r["next_problem"], "first": r["attempted"] == 0}
    return None


def pick_next(j: dict, pattern: str | None = None) -> dict:
    """One item to practise now. A named pattern skips everything due."""
    d = j["due"]
    if not pattern:
        if d["inbox"]:
            return {"kind": "inbox", "files": d["inbox"]}
        if d["resolves"]:
            return dict(d["resolves"][0], kind="resolve")
        if d["cards"]:
            return {"kind": "cards", "count": len(d["cards"])}
    return pick_new(j["patterns"], pattern) or {"kind": "none"}


def compute(state: dict, on: date | None = None) -> dict:
    on = on or today()
    cfg = state["config"]
    roadmap = state["roadmap"]
    patterns = roadmap["patterns"]
    problems = analyze_problems(state)
    try:
        start = date.fromisoformat(cfg.get("start_date", on.isoformat()))
    except ValueError:
        start = on
    try:
        target = date.fromisoformat(cfg.get("target_date", ""))
    except ValueError:
        target = None
    day_index = (on - start).days + 1
    total_days = (target - start).days if target else None
    week = max(1, (day_index - 1) // 7 + 1)
    phase = roadmap["phases"][-1]["name"]
    for ph in roadmap["phases"]:
        if ph["weeks"][0] <= week <= ph["weeks"][1]:
            phase = ph["name"]
            break

    # activity per pattern / concept
    activity: dict = {}

    def touch(key, when):
        if key:
            activity[key] = max(activity.get(key, ""), when or "")

    for a in state["attempts"]:
        touch(a.get("pattern"), a.get("date"))
    for q in state["questions"]:
        touch(q.get("concept"), q.get("date"))
    for art in state["registry"]:
        touch(art.get("concept"), art.get("updated") or art.get("created"))
    for c in state["cards"]:
        touch(c.get("concept"), c.get("created"))
    for c in state["concepts"]:
        touch(c, activity.get(c, ""))

    rows = []
    for p in patterns:
        key = p["key"]
        probs = [v for v in problems.values() if v["pattern"] == key]
        practicing = sum(v["status"] in ("practicing", "retained", "ready") for v in probs)
        retained = sum(v["status"] in ("retained", "ready") for v in probs)
        ready = sum(v["status"] == "ready" for v in probs)
        target_n = int(p.get("target", 3))
        touched = key in activity
        if not probs:
            status = "exploring" if touched else "not started"
        elif ready >= min(3, target_n):
            status = "ready"
        elif retained >= min(2, target_n):
            status = "retained"
        elif practicing:
            status = "practicing"
        else:
            status = "learning"
        rows.append({
            "key": key, "name": p["name"], "tier": p.get("tier"), "week": p.get("week"), "target": target_n,
            "attempted": len(probs), "practicing": practicing, "retained": retained, "ready": ready,
            "status": status, "last_activity": activity.get(key, "") or None,
            "next_problem": next((s for s in p.get("canonical", []) if s not in problems), None),
        })
    by_key = {r["key"]: r for r in rows}

    # focus: most recent activity on a pattern that isn't ready; else the next planned pattern
    recent = sorted(((when, k) for k, when in activity.items() if k in by_key and by_key[k]["status"] != "ready"), reverse=True)
    if recent:
        focus = recent[0][1]
    else:
        pending = [r for r in sorted(rows, key=lambda r: (r["week"] or 99, r["tier"] or 9)) if r["status"] == "not started"]
        focus = pending[0]["key"] if pending else None

    behind = [r["key"] for r in rows if (r["week"] or 99) < week and r["status"] == "not started"]
    this_week = [r["key"] for r in rows if r["week"] == week and r["status"] == "not started"]
    ahead = [r["key"] for r in rows if (r["week"] or 0) > week and r["status"] != "not started"]

    due_resolves = sorted(
        ({"problem": v["problem"], "pattern": v["pattern"], "due": v["next_due"], "overdue_days": (on - date.fromisoformat(v["next_due"])).days, "status": v["status"]}
         for v in problems.values() if date.fromisoformat(v["next_due"]) <= on),
        key=lambda d: d["due"],
    )
    active_cards = [c for c in state["cards"] if c.get("status") == "active"]
    due_cards = sorted((c for c in active_cards if card_due(c) and card_due(c) <= on), key=lambda c: c["due"])
    drafts = [c for c in state["cards"] if c.get("status") == "draft"]

    since = on - timedelta(days=30)
    recent_attempts = [a for a in state["attempts"] if date.fromisoformat(a["date"]) >= since]
    mistakes: dict = {}
    for a in recent_attempts:
        for m in a.get("mistakes") or []:
            mistakes[m] = mistakes.get(m, 0) + 1
    weak = sorted(mistakes.items(), key=lambda kv: (-kv[1], kv[0]))[:3]

    rated = [a for a in state["attempts"] if a.get("confidence") is not None]
    good = [int(a["confidence"]) for a in rated if is_unaided(a)]
    bad = [int(a["confidence"]) for a in rated if not is_unaided(a)]
    hi_miss = [a for a in rated if int(a["confidence"]) >= 4 and not is_unaided(a)]

    ledger = technique_ledger(state)
    unaided_total = sum(is_unaided(a) for a in state["attempts"])
    last_mock = max((a["date"] for a in state["attempts"] if a.get("mode") == "mock"), default=None)

    steps = []
    if state["inbox"]:
        steps.append(f"Import {len(state['inbox'])} session delta(s) waiting in inbox/ (`coach.py import`).")
    if due_resolves:
        steps.append("Re-solve from a blank page: " + ", ".join(d["problem"] for d in due_resolves[:3]) + " (a plan-only check is fine for the first).")
    if due_cards:
        steps.append(f"Quiz: {len(due_cards)} due card(s), about {max(2, len(due_cards))} minutes (`coach.py quiz`).")
    new = pick_new(rows)
    if new and new["problem"]:
        steps.append(f"Solve {new['problem']} unaided to move {new['name']} forward.")
    elif new:
        steps.append(f"Pick an unattempted problem from the NeetCode {new['name']} section.")
    if drafts:
        steps.append(f"Approve, edit or retire {len(drafts)} draft card(s) (`coach.py card list --drafts`).")
    if behind:
        steps.append(f"Behind plan: start {by_key[behind[0]]['name']} (planned for week {by_key[behind[0]]['week']}).")
    elif this_week:
        steps.append(f"This week's plan: start {fmt_list(by_key[k]['name'] for k in this_week)}.")
    if week >= 6 and (not last_mock or (on - date.fromisoformat(last_mock)).days > 14):
        steps.append("Run a timed mock (`--mode mock`); the last one was " + (f"on {last_mock}." if last_mock else "never."))
    if hi_miss:
        steps.append(f"Revisit high-confidence miss {hi_miss[-1].get('id')} ({hi_miss[-1].get('problem')}).")
    if not steps:
        steps.append("Nothing due. Start the next pattern in the plan or do an unlabeled mixed set.")

    return {
        "generated": on.isoformat(),
        "skill_version": SKILL_VERSION,
        "learner": cfg.get("learner"),
        "goal": cfg.get("goal"),
        "targets": cfg.get("targets", []),
        "plan": {
            "start_date": start.isoformat(), "target_date": target.isoformat() if target else None,
            "day": day_index, "total_days": total_days, "week": week, "plan_weeks": roadmap.get("plan_weeks", 12),
            "phase": phase, "weekly_hours": cfg.get("weekly_hours"),
        },
        "focus": focus,
        "patterns": rows,
        "behind": behind,
        "this_week": this_week,
        "ahead": ahead,
        "problems": problems,
        "due": {"resolves": due_resolves, "cards": [{"id": c["id"], "concept": c.get("concept"), "type": c.get("type"), "due": c["due"]} for c in due_cards],
                "drafts": len(drafts), "inbox": state["inbox"]},
        "totals": {
            "problems": len(problems), "attempts": len(state["attempts"]), "unaided_solves": unaided_total,
            "retained": sum(v["status"] in ("retained", "ready") for v in problems.values()),
            "ready": sum(v["status"] == "ready" for v in problems.values()),
            "minutes": sum(int(a.get("minutes") or 0) for a in state["attempts"]),
            "sessions": len(state["sessions"]), "questions": len(state["questions"]),
            "cards_active": len(active_cards), "cards_held": sum(card_held(c) for c in active_cards),
            "cards_draft": len(drafts), "cards_retired": sum(c.get("status") == "retired" for c in state["cards"]),
            "explainers": len(state["registry"]),
        },
        "weak_spots": [{"code": k, "count": v, "meaning": MISTAKES.get(k, "")} for k, v in weak],
        "calibration": {
            "rated_attempts": len(rated),
            "avg_conf_unaided": round(sum(good) / len(good), 2) if good else None,
            "avg_conf_other": round(sum(bad) / len(bad), 2) if bad else None,
            "high_confidence_misses": [{"id": a.get("id"), "problem": a.get("problem"), "date": a.get("date")} for a in hi_miss[-5:]],
        },
        "techniques": sorted(ledger.values(), key=lambda r: (-r["trials"], r["technique"])),
        "questions": state["questions"][-5:],
        "artifacts": state["registry"],
        "sessions": [session_digest(state["root"], d) for d in state["sessions"][-5:]],
        "last_mock": last_mock,
        "next_steps": steps[:6],
        "other_concepts": sorted(k for k in activity if k not in by_key),
    }


# --------------------------------------------------------------------------- rendering
def render_journey(j: dict) -> str:
    plan = j["plan"]
    by_key = {r["key"]: r for r in j["patterns"]}
    focus = by_key.get(j["focus"]) if j["focus"] else None
    days = f"Day {plan['day']} of {plan['total_days']}" if plan["total_days"] else f"Day {plan['day']}"
    span = f"{plan['start_date']} → {plan['target_date']}" if plan["target_date"] else f"since {plan['start_date']}"
    out = [
        f"# Journey snapshot · {j['generated']}",
        "",
        f"**Goal:** {j['goal']}  ",
        f"**Targets:** {fmt_list(j['targets'])}  ",
        f"**Plan:** {days} ({span}) · Week {plan['week']} of {plan['plan_weeks']} · Phase: {plan['phase']} · {plan['weekly_hours']} h/week  ",
        f"**Focus:** {focus['name'] + ' (' + focus['status'] + ')' if focus else 'not set'} · Skill v{j['skill_version']}",
        "",
        "_Generated by `coach.py snapshot`. Don't edit by hand; change the logs and run it again._",
        "",
        "## Next steps",
        "",
    ]
    out += [f"{i}. {s}" for i, s in enumerate(j["next_steps"], 1)]
    out += ["", "## Due today", ""]
    due = j["due"]
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
    for r in sorted(j["patterns"], key=lambda r: (r["week"] or 99, r["tier"] or 9)):
        out.append(f"| {r['week']} | {r['name']} | {r['tier']} | {r['status']} | {r['attempted']} | {r['practicing']} | {r['retained']} | {r['ready']} | {r['target']} | {r['last_activity'] or ''} |")
    started = sum(r["status"] != "not started" for r in j["patterns"])
    out += ["", f"Started {started} of {len(j['patterns'])} patterns. "
            + (f"Behind plan: {fmt_list(by_key[k]['name'] for k in j['behind'])}. " if j["behind"] else "Nothing from earlier weeks is behind. ")
            + (f"Planned this week: {fmt_list(by_key[k]['name'] for k in j['this_week'])}. " if j["this_week"] else "")
            + (f"Ahead of plan: {fmt_list(by_key[k]['name'] for k in j['ahead'])}." if j["ahead"] else "")]
    if j["other_concepts"]:
        out.append(f"Other concepts touched: {fmt_list(j['other_concepts'])}.")
    t = j["totals"]
    out += ["", "## Totals", "",
            f"- Problems attempted: {t['problems']} · unaided solves: {t['unaided_solves']} · retained: {t['retained']} · ready: {t['ready']}",
            f"- Attempts logged: {t['attempts']} · minutes: {t['minutes']} · sessions: {t['sessions']}",
            f"- Cards: {t['cards_active']} active ({t['cards_held']} held at {HELD_DAYS}+ days), {t['cards_draft']} draft, {t['cards_retired']} retired",
            f"- Questions asked: {t['questions']} · explainers saved: {t['explainers']}"]
    out += ["", "## Weak spots (last 30 days)", ""]
    out += [f"- {w['code']} ({w['meaning']}): {w['count']}" for w in j["weak_spots"]] or ["No mistakes logged yet."]
    cal = j["calibration"]
    out += ["", "## Calibration", ""]
    if cal["rated_attempts"]:
        out.append(f"- Average confidence before unaided solves: {cal['avg_conf_unaided']}; before other attempts: {cal['avg_conf_other']} ({cal['rated_attempts']} rated attempts)")
        out += [f"- High-confidence miss: {m['id']} {m['problem']} ({m['date']})" for m in cal["high_confidence_misses"]]
    else:
        out.append("No confidence ratings yet. Log `--confidence 1-5` before each attempt.")
    out += ["", "## What seems to work (delayed evidence only)", ""]
    if j["techniques"]:
        out += ["| Technique | Pattern | Delayed checks | Unaided | Estimate | |", "|---|---|---|---|---|---|"]
        for r in j["techniques"]:
            out.append(f"| {r['technique']} | {r['pattern']} | {r['trials']} | {r['successes']} | {r['estimate']} | {'provisional' if r['provisional'] else ''} |")
    else:
        out.append("No delayed re-solves yet, so no technique has earned credit. Preferences don't count as evidence.")
    out += ["", "## Recent questions", ""]
    out += [f"- {q.get('date')} · {q.get('concept')}: {q.get('text')}" for q in reversed(j["questions"])] or ["None yet."]
    out += ["", "## Saved explainers", ""]
    if j["artifacts"]:
        for a in j["artifacts"]:
            where = " · ".join(x for x in [f"[link]({a['url']})" if a.get("url") else "", f"`{a['file']}`" if a.get("file") else ""] if x)
            out.append(f"- {a.get('title')} ({a.get('concept')}, v{a.get('version', 1)}): {where}")
    else:
        out.append("None yet.")
    out += ["", "## Recent sessions", ""]
    out += [f"- {s['date']}: {s['summary']}" for s in reversed(j["sessions"])] or ["None yet."]
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


def render_summary(j: dict, preferences: str) -> str:
    plan = j["plan"]
    by_key = {r["key"]: r for r in j["patterns"]}
    lines = [
        f"DSA COACH LEARNER SUMMARY · generated {j['generated']} by coach.py snapshot · skill {j['skill_version']}",
        f"Learner: {j['learner']} · Goal: {j['goal']}",
        f"Targets: {fmt_list(j['targets'])}",
        f"Plan: day {plan['day']}" + (f" of {plan['total_days']}" if plan["total_days"] else "") + f", week {plan['week']} of {plan['plan_weeks']}, phase {plan['phase']}, target date {plan['target_date']}",
        f"Focus: {by_key[j['focus']]['name'] + ' (' + by_key[j['focus']]['status'] + ')' if j['focus'] else 'not set'}",
        "",
        "Patterns started (status, attempted/unaided/retained/ready of target):",
    ]
    started = [r for r in j["patterns"] if r["status"] != "not started"]
    lines += [f"- {r['name']}: {r['status']}, {r['attempted']}/{r['practicing']}/{r['retained']}/{r['ready']} of {r['target']}" for r in started] or ["- none yet"]
    if j["other_concepts"]:
        lines.append(f"Other concepts: {fmt_list(j['other_concepts'])}")
    d = j["due"]
    lines += ["", f"Due today: {len(d['resolves'])} re-solve(s) [{fmt_list(x['problem'] for x in d['resolves'][:5])}], {len(d['cards'])} card(s), {d['drafts']} draft card(s), {len(d['inbox'])} inbox delta(s)"]
    lines.append("Weak spots (30 days): " + fmt_list(f"{w['code']}×{w['count']}" for w in j["weak_spots"]))
    cal = j["calibration"]
    if cal["rated_attempts"]:
        lines.append(f"Calibration: avg confidence before unaided solves {cal['avg_conf_unaided'] if cal['avg_conf_unaided'] is not None else 'n/a'}, "
                     f"before other attempts {cal['avg_conf_other'] if cal['avg_conf_other'] is not None else 'n/a'}; "
                     f"high-confidence misses: {fmt_list(m['id'] for m in cal['high_confidence_misses'])}")
    else:
        lines.append("Calibration: no confidence ratings yet")
    if j["sessions"]:
        last = j["sessions"][-1]
        lines.append(f"Last session: {last['date']}: {last['summary']}")
    lines.append("Techniques with delayed evidence: " + fmt_list(f"{r['technique']}/{r['pattern']} {r['successes']}/{r['trials']}{' (provisional)' if r['provisional'] else ''}" for r in j["techniques"][:5]))
    prefs = [ln.strip() for ln in preferences.splitlines() if ln.strip().startswith("- ")][:5]
    lines += ["", "Stated preferences (formatting defaults only, not evidence):"] + (prefs or ["- none recorded"])
    lines += ["", "Recent questions:"] + ([f"- {q.get('date')} {q.get('concept')}: {q.get('text')[:140]}" for q in reversed(j["questions"][-3:])] or ["- none"])
    lines += ["", "Next steps:"] + [f"{i}. {s}" for i, s in enumerate(j["next_steps"][:4], 1)]
    lines += ["", "Coach rules: attempt before answers; predict before reveal; credit only delayed unaided success; log everything with coach.py."]
    return "\n".join(lines[:60]) + "\n"


def write_snapshot(root: Path, on: date | None = None) -> dict:
    state = load_state(root)
    j = compute(state, on)
    write_json(root / "journey.json", j)
    (root / "JOURNEY.md").write_text(render_journey(j), encoding="utf-8")
    (root / "learner").mkdir(parents=True, exist_ok=True)
    (root / "learner" / "summary.md").write_text(render_summary(j, state["preferences"]), encoding="utf-8")
    write_json(root / "learner" / "techniques.json", j["techniques"])
    return j


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
        url = load_roadmap().get("problem_url", "https://leetcode.com/problems/{slug}/").format(slug=slug)
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
        if not 0 <= int(a.get("hints") or 0) <= 7:
            errs.append("hints must be 0-7")
    except (TypeError, ValueError):
        errs.append("hints must be an integer 0-7")
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
    if a.get("date"):
        try:
            date.fromisoformat(a["date"])
        except ValueError:
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
        "assisted": bool(a.get("assisted")) or hints >= 5 or mode == "ai",
        "confidence": a.get("confidence"),
        "technique": a.get("technique"),
        "mistakes": list(a.get("mistakes") or []),
        "complexity_stated": bool(a.get("complexity_stated")),
        "note": a.get("note", ""),
        "skill_version": a.get("skill_version", SKILL_VERSION),
        "source": source,
    }
    append_jsonl(root / "learner" / "attempts.jsonl", row)
    ensure_problem_notes(root, row["problem"], row["pattern"], row["difficulty"], on)
    if row["note"]:
        notes = root / "problems" / row["problem"] / "notes.md"
        with notes.open("a", encoding="utf-8") as fh:
            fh.write(f"- {row['date']} ({row['id']}, {row['mode']}, {row['outcome']}): {row['note']}\n")
    return row


def cmd_log_attempt(args) -> None:
    root = find_root(args.root)
    a = {
        "problem": args.problem, "pattern": args.pattern, "difficulty": args.difficulty, "mode": args.mode,
        "outcome": args.outcome, "minutes": args.minutes, "hints": args.hints, "assisted": args.assisted,
        "confidence": args.confidence, "technique": args.technique,
        "mistakes": [m.strip() for m in (args.mistakes or "").split(",") if m.strip()],
        "complexity_stated": args.complexity_stated, "note": args.note or "", "date": args.date,
    }
    errs = validate_attempt(a, pattern_keys())
    if errs:
        die("; ".join(errs))
    row = add_attempt(root, a)
    info = analyze_problems(load_state(root))[row["problem"]]
    write_snapshot(root)
    kind = "unaided" if is_unaided(row) else "assisted" if row["assisted"] else "not unaided"
    print(f"Logged {row['id']}: {row['problem']} ({row['pattern']}), {row['outcome']}, {kind}. "
          f"Problem status: {info['status']}. Next re-solve due {info['next_due']}.")


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


def add_card(root: Path, c: dict, source: str = "cli") -> dict:
    if c.get("type", "other") not in CARD_TYPES:
        die(f"card type must be one of {CARD_TYPES}")
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
            cards = [c for c in cards if c.get("status") == "active" and card_due(c) and card_due(c) <= on]
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
    write_snapshot(root)


def cmd_quiz(args) -> None:
    root = find_root(args.root)
    on = today()
    cards = [c for c in load_cards(root) if c.get("status") == "active" and card_due(c) and card_due(c) <= on]
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
    j = compute(load_state(root), parse_date(args.date))
    d = j["due"]
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
    if kind == "new" and item["problem"]:
        return f"Solve {item['problem']} ({item['name']})."
    if kind == "new":
        return f"Pick an unattempted problem from the NeetCode {item['name']} section."
    return "Plan finished. Run a mock or an unlabeled mixed set."


def cmd_next(args) -> None:
    root = find_root(args.root)
    pattern = slugify(args.pattern) if args.pattern else None
    if pattern and pattern not in pattern_keys():
        die(f"unknown pattern {pattern}. Choose from: {', '.join(pattern_keys())}")
    item = pick_next(compute(load_state(root), parse_date(args.date)), pattern)
    print(json.dumps(item, indent=2, ensure_ascii=False) if args.json else render_next(item))


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
    j = write_snapshot(root, parse_date(args.date) if args.date else None)
    print(f"Snapshot written: {root / 'JOURNEY.md'} (day {j['plan']['day']}, week {j['plan']['week']}, {j['plan']['phase']}).")
    if args.print:
        print()
        print((root / "JOURNEY.md").read_text(encoding="utf-8"))


def cmd_status(args) -> None:
    root = find_root(args.root)
    j = write_snapshot(root)
    plan = j["plan"]
    by_key = {r["key"]: r for r in j["patterns"]}
    focus = by_key.get(j["focus"]) if j["focus"] else None
    d = j["due"]
    print(f"DSA Coach · {j['generated']} · day {plan['day']}" + (f"/{plan['total_days']}" if plan["total_days"] else "")
          + f" · week {plan['week']} · {plan['phase']} · skill {SKILL_VERSION}")
    print(f"Focus: {focus['name'] + ' (' + focus['status'] + ')' if focus else 'not set'}")
    print(f"Due: {len(d['resolves'])} re-solve(s) · {len(d['cards'])} card(s) · {d['drafts']} draft card(s) to approve · {len(d['inbox'])} inbox delta(s)")
    if not args.brief:
        started = [r for r in j["patterns"] if r["status"] != "not started"]
        if started:
            print("Patterns: " + "; ".join(f"{r['name']} {r['status']} ({r['attempted']}/{r['target']})" for r in started))
        if j["weak_spots"]:
            print("Weak spots: " + ", ".join(f"{w['code']}×{w['count']}" for w in j["weak_spots"]))
    print("Next:")
    for i, s in enumerate(j["next_steps"][: (3 if args.brief else 6)], 1):
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
    j = write_snapshot(root)
    on = today().isoformat()
    out = Path(args.out).expanduser() if args.out else root / "exports" / f"pack-{on}.md"
    due = j["due"]
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


def validate_delta(d: dict, keys: list, card_ids: set) -> list:
    errs = []
    if d.get("format") != DELTA_FORMAT:
        errs.append(f"format must be {DELTA_FORMAT!r}")
    for i, a in enumerate(d.get("attempts") or []):
        errs += [f"attempts[{i}]: {e}" for e in validate_attempt(a, keys)]
    for i, q in enumerate(d.get("questions") or []):
        if not q.get("concept") or not q.get("text"):
            errs.append(f"questions[{i}]: concept and text are required")
    new_cards = 0
    for i, c in enumerate(d.get("cards") or []):
        if not all(c.get(k) for k in ("concept", "front", "back")):
            errs.append(f"cards[{i}]: concept, front and back are required")
        if c.get("type", "other") not in CARD_TYPES:
            errs.append(f"cards[{i}]: type must be one of {CARD_TYPES}")
        new_cards += 1
    for i, r in enumerate(d.get("card_reviews") or []):
        if r.get("id") not in card_ids:
            errs.append(f"card_reviews[{i}]: unknown card id {r.get('id')!r}")
        if r.get("grade") not in GRADES:
            errs.append(f"card_reviews[{i}]: grade must be pass or fail")
    for i, a in enumerate(d.get("artifacts") or []):
        if not a.get("concept") or not a.get("title") or not (a.get("url") or a.get("file")):
            errs.append(f"artifacts[{i}]: concept, title and url (or file) are required")
    return errs


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
        card_ids = {c.get("id") for c in load_cards(root)}
        errs = validate_delta(d, keys, card_ids)
        if errs:
            print(f"skip {path.name}: fix these fields and import again:")
            for e in errs:
                print(f"  - {e}")
            continue
        session = d.get("session") or {}
        on = session.get("date") or today().isoformat()
        source = f"import:{path.name}"
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
    path = WORKSPACE / ".claude" / "settings.json"
    command = 'python3 "$CLAUDE_PROJECT_DIR/skills/dsa-coach/scripts/coach.py" --root "$CLAUDE_PROJECT_DIR/notebook" status --brief'
    entry = {"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command", "command": command}]}
    settings = read_json(path, {}) if path.exists() else {}
    hooks = settings.setdefault("hooks", {}).setdefault("SessionStart", [])
    if any(x.get("command") == command for h in hooks for x in h.get("hooks", [])):
        return f"SessionStart hook already present in {path}"
    hooks.append(entry)
    write_json(path, settings)
    return f"SessionStart hook added to {path} (Claude Code loads your status at the start of each session)"


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
    s.add_argument("--hints", type=int, default=0, help="highest hint-ladder rung used, 0-7")
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
    for sp in card.choices.values():
        sp.set_defaults(func=cmd_card)

    s = sub.add_parser("quiz", help="due card fronts (answers with --json)")
    s.add_argument("--n", type=int, default=10)
    s.add_argument("--concept")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_quiz)

    s = sub.add_parser("due", help="list due re-solves and cards")
    s.add_argument("--date")
    s.set_defaults(func=cmd_due)

    s = sub.add_parser("next", help="the one thing to practise now")
    s.add_argument("--pattern", help="pick a new problem from this pattern, skipping anything due")
    s.add_argument("--json", action="store_true")
    s.add_argument("--date")
    s.set_defaults(func=cmd_next)

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
    s.set_defaults(func=cmd_artifact)

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
    s.set_defaults(func=cmd_package)

    s = sub.add_parser("install", help="make the skill visible to Claude Code and Codex")
    s.add_argument("--claude", action="store_true", help="only Claude Code (.claude/skills)")
    s.add_argument("--codex", action="store_true", help="only Codex / ChatGPT desktop (.agents/skills)")
    s.add_argument("--user", action="store_true", help="install for your user account instead of this workspace")
    s.add_argument("--copy", action="store_true", help="copy instead of symlinking")
    s.add_argument("--force", action="store_true", help="replace an existing install")
    s.add_argument("--no-hook", action="store_true", help="don't add the Claude Code SessionStart hook")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("validate", help="check the skill against the Agent Skills spec and the notebook files")
    s.set_defaults(func=cmd_validate)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
