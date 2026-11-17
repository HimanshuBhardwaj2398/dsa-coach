"""Build a pattern's explainer page from its spec: real Python, traced line by line, checked, then drawn.

    python3 build_explainer.py notebook/concepts/two-pointers/spec.py [--out PAGE.html]

A spec is a Python file with the page's words and its reference code (references/explainers.md, "Specs").
The build runs the reference on every traced input with sys.settrace, compares it with the spec's brute force on
generated inputs, asserts the spec's invariant at every step and its count bound at every measured size, and
writes one self-contained HTML page (the stepper in assets/explainer/ is inlined). Nothing on the page is imagined:
every state, prediction answer, run count and check answer comes from executing the spec's code.
"""
from __future__ import annotations

import argparse
import copy
import html
import importlib.util
import inspect
import json
import random
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
MAX_STEPS = 700  # a curated input stays small enough to step through


class SpecError(Exception):
    pass


# --- what a spec's view functions return ------------------------------------------------------------------------

def show(value) -> str:
    """A value as the trace shows it: Python's repr, shortened."""
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


class V:
    """The views a spec draws. Each is a plain dict the page's stepper renders."""

    @staticmethod
    def array(name, items, ptr=None, cls=None, labels=None):
        """A row of cells. ptr: {label: index} drawn under the cells; cls: {index: css class}."""
        return {"t": "array", "name": name, "items": [x if isinstance(x, str) else show(x) for x in items], "labels": labels,
                "ptr": {k: v for k, v in (ptr or {}).items() if v is not None},
                "cls": {str(k): v for k, v in (cls or {}).items()}}

    @staticmethod
    def items(name, items, cls=None, note=""):
        """A stack, queue, path or result list, left to right."""
        return {"t": "list", "name": name, "items": [x if isinstance(x, str) else show(x) for x in items], "note": note,
                "cls": {str(k): v for k, v in (cls or {}).items()}}

    @staticmethod
    def mapping(name, d, hl=None):
        return {"t": "map", "name": name, "entries": [[show(k), show(v)] for k, v in d.items()],
                "hl": None if hl is None else show(hl)}

    @staticmethod
    def vars(*pairs):
        return {"t": "vars", "items": [[k, show(v)] for k, v in pairs]}

    @staticmethod
    def grid(name, cells, rowh=None, colh=None, cls=None):
        """A table: a DP table, a matrix or a board. cls: {(r, c): css class}."""
        return {"t": "grid", "name": name, "cells": [["" if x is None else x if isinstance(x, str) else show(x) for x in row] for row in cells],
                "rowh": rowh, "colh": colh, "cls": {f"{r},{c}": v for (r, c), v in (cls or {}).items()}}

    @staticmethod
    def graph(name, nodes, edges, directed=False, w=None, h=None):
        """nodes: [{id, label, x, y, cls?, tag?}] in grid units; edges: [{a, b, label?, cls?}]."""
        return {"t": "graph", "name": name, "nodes": nodes, "edges": edges, "directed": directed,
                "w": w or max([n["x"] for n in nodes] + [0]) + 1, "h": h or max([n["y"] for n in nodes] + [0]) + 1}

    @staticmethod
    def bars(name, spans, lo, hi):
        """Intervals on a number line. spans: [(start, end, label, css class)]."""
        return {"t": "bars", "name": name, "spans": [list(s) for s in spans], "lo": lo, "hi": hi}

    @staticmethod
    def text(text):
        return {"t": "text", "text": text}


def tree_layout(root, children) -> dict:
    """x, y for each node of a rooted tree: leaves left to right, a parent centred over its children."""
    pos, nxt = {}, [0]

    def place(node, depth):
        kids = children.get(node, [])
        for kid in kids:
            place(kid, depth + 1)
        if kids:
            x = (pos[kids[0]][0] + pos[kids[-1]][0]) / 2
        else:
            x, nxt[0] = nxt[0], nxt[0] + 1
        pos[node] = (x, depth)

    if root is not None:
        place(root, 0)
    return pos


# --- recording a run ---------------------------------------------------------------------------------------------

class State:
    """One moment of a run, as a spec's functions see it."""

    def __init__(self, ev, code):
        self.kind, self.line, self.func, self.ret = ev["kind"], ev["line"], ev["func"], ev.get("ret")
        self.stack = ev["stack"]                      # [(function name, locals)], outermost first
        self.v = self.stack[-1][1] if self.stack else {}  # the current frame's locals
        self.outer = self.stack[0][1] if self.stack else {}
        self.depth = len(self.stack)
        self.text = code[self.line - 1].strip() if self.line else ""

    def __getattr__(self, name):  # S.l is S.v["l"]
        try:
            return self.__dict__["v"][name]
        except KeyError:
            raise AttributeError(name) from None


def source_of(fn):
    lines, first = inspect.getsourcelines(fn)
    return [line.rstrip("\n") for line in lines], first


def record(fn, args, counts_only=False):
    """Run fn(*args) under sys.settrace. Returns (events, result) or, with counts_only, (runs per line, result).
    An event is a line about to run in a frame of fn (nested functions and recursion included) or a frame returning;
    comprehensions and lambdas run inside a line and aren't steps."""
    code, first = source_of(fn)
    last, filename = first + len(code) - 1, fn.__code__.co_filename
    events, frames, runs, ran = [], [], {}, [None]

    def traced(co):
        return co.co_filename == filename and first <= co.co_firstlineno <= last and not co.co_name.startswith("<")

    def snapshot():
        stack = [(f.f_code.co_name, {k: v for k, v in f.f_locals.items() if not callable(v) and not k.startswith("__")})
                 for f in frames]
        return copy.deepcopy(stack)

    def local(frame, event, arg):
        if event == "line":
            line = frame.f_lineno - first + 1
            if ran[0] == (id(frame), line):  # a comprehension inlined in the line (Python 3.12+): still one run
                return local
            ran[0] = (id(frame), line)
            if counts_only:
                runs[line] = runs.get(line, 0) + 1
            else:
                events.append({"kind": "line", "line": line, "func": frame.f_code.co_name, "stack": snapshot()})
                if len(events) > MAX_STEPS:
                    raise SpecError(f"more than {MAX_STEPS} steps: use a smaller input")
        elif event == "return":
            ran[0] = None
            if not counts_only:
                events.append({"kind": "return", "line": frame.f_lineno - first + 1, "func": frame.f_code.co_name,
                               "stack": snapshot(), "ret": copy.deepcopy(arg)})
            frames.pop()
        return local

    def tracer(frame, event, arg):
        if event == "call" and traced(frame.f_code):
            frames.append(frame)
            ran[0] = None
            return local
        return None

    sys.settrace(tracer)
    try:
        result = fn(*copy.deepcopy(args))
    finally:
        sys.settrace(None)
    return (runs if counts_only else events), result


# --- turning a run into the page's data --------------------------------------------------------------------------

def plain(value) -> bool:
    """Built from Python's own types only, so == compares contents (a node object compares by identity)."""
    if isinstance(value, (int, float, str, bool, type(None))):
        return True
    if isinstance(value, dict):
        return all(plain(k) and plain(v) for k, v in value.items())
    if isinstance(value, (list, tuple, set, frozenset, deque)):
        return all(plain(x) for x in value)
    return False


def auto_say(prev: State, cur: State) -> str:
    """What the line just run changed in the plain locals: 'l: 0 → 1 · mid = 3'. Objects are the spec's say()."""
    if prev.kind == "return":
        return f"{prev.func} returned {show(prev.ret)}."
    if cur.depth > prev.depth:
        return f"Called {cur.func}({', '.join(f'{k}={show(v)}' for k, v in list(cur.v.items())[:3])})."
    if cur.depth != prev.depth:
        return ""
    parts = []
    for k, v in cur.v.items():
        if not plain(v):
            continue
        if k not in prev.v:
            parts.append(f"{k} = {show(v)}")
        elif prev.v[k] != v:
            parts.append(f"{k}: {show(prev.v[k])} → {show(v)}" if len(show(v)) < 30 else f"{k} changed")
    return " · ".join(parts)


def call(f, *args):
    return f(*args) if callable(f) else f


def build_trace(spec, t, check=None):
    fn = t.get("fn", spec.REFERENCE)
    code, _ = source_of(fn)
    events, result = record(fn, t["args"])
    states = [State(e, code) for e in events]
    for k, s in enumerate(states):  # a view may read what came before: S.trace[:S.index]
        s.index, s.trace = k, states
    if "expect" in t and result != t["expect"]:
        raise SpecError(f"trace {t['label']!r}: returned {result!r}, expected {t['expect']!r}")
    predicts = getattr(spec, "PREDICT", {})
    asked, steps, rows = {}, [], []
    for k, s in enumerate(states):
        nxt = states[k + 1] if k + 1 < len(states) else None
        if check:
            ok = check(s)
            if ok is False:
                raise SpecError(f"trace {t['label']!r}: the invariant fails at step {k + 1} (line {s.line}: {s.text})")
        step = {"line": s.line, "ret": s.kind == "return", "views": spec.view(s)}
        prev = states[k - 1] if k else None
        if prev is not None:
            said = spec.say(prev, s) if hasattr(spec, "say") else None
            step["say"] = said if said is not None else auto_say(prev, s)
        else:
            step["say"] = t.get("intro", "Ready. Step runs the highlighted line.")
        if s.kind == "return" and s.depth == 1:
            step["say"] = (step["say"] + " · " if step["say"] else "") + f"Returns {show(s.ret)}."
        p = predicts.get(s.text) if s.kind == "line" and nxt else None
        if p and asked.get(s.text, 0) < p.get("times", 3) and call(p.get("when", True), s) is not False:
            asked[s.text] = asked.get(s.text, 0) + 1
            options = call(p.get("options"), s)
            answer = p["answer"](s, nxt)
            if options is not None and answer not in options:
                raise SpecError(f"prediction at {s.text!r}: answer {answer!r} isn't one of {options!r}")
            step["ask"] = {"q": call(p["q"], s), "options": options, "answer": str(answer),
                           "why": call(p.get("why", ""), s, nxt) if callable(p.get("why")) else p.get("why", "")}
        if nxt is not None and hasattr(spec, "row"):
            r = spec.row(s, nxt)
            if r:
                rows.append({"at": k + 1, "cells": [show(x) if not isinstance(x, str) else x for x in r]})
        steps.append(step)
    return {"label": t["label"], "about": t.get("about", ""), "code": code, "steps": steps, "rows": rows,
            "cols": t.get("cols", getattr(spec, "ROW_COLS", [])), "result": show(result)}


def run_oracle(spec) -> int:
    """Every traced function against brute force: ORACLE is one check or a list of them."""
    checks = getattr(spec, "ORACLE", None)
    if not checks:
        raise SpecError("a spec needs ORACLE: the reference checked against brute force")
    total = 0
    for o in checks if isinstance(checks, list) else [checks]:
        rng, same, n, fn = random.Random(7), o.get("same", lambda a, b: a == b), 0, o.get("fn", spec.REFERENCE)
        for args in o["inputs"](rng):
            got, want = fn(*copy.deepcopy(args)), o["brute"](*copy.deepcopy(args))
            if not same(got, want):
                raise SpecError(f"oracle for {fn.__name__}: {args!r} gave {got!r}, brute force gives {want!r}")
            n += 1
        if n < 20:
            raise SpecError(f"oracle for {fn.__name__}: only {n} inputs; generate at least 20, with the edge cases")
        total += n
    return total


def measure(spec) -> dict:
    c = spec.COUNT
    fn = c.get("fn", spec.REFERENCE)
    code, _ = source_of(fn)
    rows, line = [], None
    for n in c["sizes"]:
        runs, _ = record(fn, c["input"](n), counts_only=True)
        if line is None:
            line = next((i for i, text in enumerate(code, 1) if c["line"] in text), None)
            if line is None:
                raise SpecError(f"COUNT line {c['line']!r} isn't in the reference")
        got, bound = runs.get(line, 0), c["bound"](n)
        if got > bound:
            raise SpecError(f"COUNT: line {line} ran {got} times at n = {n}, over the stated bound {bound}")
        rows.append([n, got, bound, sum(runs.values())])
    return {"line": code[line - 1].strip(), "rows": rows, "bound_text": c["bound_text"], "time": c["time"],
            "space": c["space"], "text": c["text"], "n_name": c.get("n_name", "n")}


def check_answers(spec) -> dict:
    c = spec.CHECK
    t = c["trace"]
    events, result = record(t.get("fn", spec.REFERENCE), t["args"])
    states = [State(e, source_of(t.get("fn", spec.REFERENCE))[0]) for e in events]
    for k, s in enumerate(states):
        s.index, s.trace = k, states
    run = {"result": result, "states": states}
    fields = []
    for label, f in t["fields"]:
        answer = f(run)
        fields.append({"label": label, "answer": answer if isinstance(answer, str) else show(answer)})
    return {"text": t["text"], "fields": fields, "questions": c["questions"], "own": c["own"]}


def problems_index() -> dict:
    data = json.loads((ASSETS / "problems.json").read_text(encoding="utf-8"))
    return {p["slug"]: p for ps in data.values() for p in ps}


def build(spec_path: Path) -> tuple[str, dict]:
    sys.path.insert(0, str(HERE))
    name = "explainer_spec_" + re.sub(r"\W", "_", spec_path.parent.name)
    loader = importlib.util.spec_from_file_location(name, spec_path)
    spec = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(spec)
    tested = run_oracle(spec)
    check = getattr(spec, "INVARIANT", None)
    traces = [build_trace(spec, t, check) for t in spec.TRACES]
    titles = problems_index()
    family = []
    for f in spec.FAMILY:
        probs = []
        for slug in f["problems"]:
            p = titles.get(slug)
            if not p:
                raise SpecError(f"FAMILY: {slug!r} isn't in assets/problems.json")
            probs.append({"slug": slug, "title": p["title"], "difficulty": p["difficulty"]})
        family.append(dict(f, problems=probs))
    data = {"traces": traces, "spot": spec.SPOT, "check": check_answers(spec)}
    page = render(spec, data, family, measure(spec))
    return page, {"steps": sum(len(t["steps"]) for t in traces), "oracle_inputs": tested, "bytes": len(page.encode())}


# --- the page ------------------------------------------------------------------------------------------------------

def md(text: str) -> str:
    """Escaped text with `code` and **bold**."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)


def paras(texts) -> str:
    return "".join(f"<p>{md(t)}</p>" for t in ([texts] if isinstance(texts, str) else texts))


def render(spec, data, family, count) -> str:
    s, p = spec.SPOT, spec.PARTS
    questions = "".join(f"<li><b>{md(q)}</b> {md(a)}</li>" for q, a in s["questions"])
    misses = "".join(f"<li><b>{md(a)}</b> {md(b)}</li>" for a, b in s["near_misses"])
    names = "".join(f"<dt><code>{html.escape(n)}</code></dt><dd>{md(d)}</dd>" for n, d in p["names"])
    plan = "".join(f"<dt>{html.escape(k)}</dt><dd>{md(v)}</dd>" for k, v in p["plan"])
    safe = "".join(f"<li>{md(x)}</li>" for x in p["safe"])
    fam = "".join(
        f"<article class='variant'><h3>{md(f['name'])}</h3>{paras(f['change'])}"
        + (f"<pre class='code'>{html.escape(f['code'])}</pre>" if f.get("code") else "")
        + "<p class='probs'>" + " · ".join(
            f"<a href='https://leetcode.com/problems/{q['slug']}/' target='_blank' rel='noopener'>{html.escape(q['title'])}</a>"
            f" <span class='muted'>{q['difficulty']}</span>" for q in f["problems"]) + "</p></article>"
        for f in family)
    traps = "".join(f"<li><b>{md(a)}</b> {md(b)}</li>" for a, b in spec.TRAPS)
    rows, before = "", None
    for n, got, bound, total in count["rows"]:
        ratio = f"×{got / before:.2f}" if before else ""
        rows += f"<tr><td>{n}</td><td>{got}</td><td>{bound}</td><td>{ratio}</td><td>{total}</td></tr>"
        before = got
    css = (ASSETS / "explainer" / "explainer.css").read_text(encoding="utf-8")
    js = (ASSETS / "explainer" / "explainer.js").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(spec.TITLE)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<header class="bar"><span class="brand">DSA notebook</span>
<nav><a href="#spot">Spot it</a><a href="#parts">Parts</a><a href="#trace">Trace</a><a href="#family">Family</a><a href="#count">Count</a><a href="#check">Check</a></nav>
<button type="button" id="theme" class="ghost" aria-label="Switch light or dark theme">◐</button></header>
<main>
<div class="lesson">
<section class="hero"><h1>{title}</h1><p class="pitch">{md(spec.PITCH)}</p></section>

<section id="spot"><h2>Spot it</h2>{paras(s["idea"])}
<h3>Ask yourself</h3><ol class="questions">{questions}</ol>
<h3>Which fits?</h3><p class="muted">Pick what you would reach for. A wrong pick shows the gap; pick again to move on.</p>
<div id="cases"></div>
<h3>Looks like it, isn't</h3><ul>{misses}</ul></section>

<section id="parts"><h2>The parts</h2>{paras(p.get("intro", []))}
<div class="cards"><div class="card"><h3>Names</h3><dl>{names}</dl></div>
<div class="card"><h3>Your plan card</h3><dl>{plan}</dl></div></div>
<div class="card invariant"><h3>What stays true</h3><p>{md(p["invariant"])}</p></div>
<h3>Why each move is safe</h3><ul>{safe}</ul>
<p><b>Relies on:</b> {md(p["relies_on"])}</p></section>

<section id="trace"><h2>Trace it. Predict the decisions.</h2>
<p class="muted">Step runs the highlighted line. At a decision the stepper waits for your prediction. The numbers beside the code count how often each line has run.</p>
<div id="stepper"></div></section>

<section id="family"><h2>The family</h2>{paras(spec.FAMILY_INTRO)}{fam}</section>

<section id="count"><h2>Count the work</h2>
<p>Count how often each line runs; the line with the most runs decides the Big-O. Here that is <code>{html.escape(count["line"])}</code>.</p>
{paras(count["text"])}
<table class="measure"><thead><tr><th>{html.escape(count["n_name"])}</th><th>runs (measured)</th><th>bound: {md(count["bound_text"])}</th><th>vs the row above</th><th>all lines</th></tr></thead><tbody>{rows}</tbody></table>
<p class="muted">Measured by running the reference under Python's tracer on its worst inputs.</p>
<p><b>Time:</b> {md(count["time"])} · <b>Extra space:</b> {md(count["space"])}</p></section>

<section id="traps"><h2>Where it breaks</h2><ul>{traps}</ul></section>
</div>

<section id="check"><h2>Check it without the visual</h2>
<p>Hide the lesson, then trace a fresh input and answer the transfer questions from memory. A practice check, not proof you'll remember it.</p>
<button type="button" id="hide" class="primary">Hide the lesson and try</button>
<div id="quiz" hidden></div></section>
</main>
<script id="data" type="application/json">{payload}</script>
<script>{js}</script>
</body>
</html>
"""


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="build a pattern's explainer page from its spec")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, help="default: <pattern>-explainer.html beside the spec")
    a = ap.parse_args(argv)
    out = a.out or a.spec.parent / f"{a.spec.parent.name}-explainer.html"
    try:
        page, info = build(a.spec.resolve())
    except SpecError as e:
        raise SystemExit(f"{a.spec}: {e}")
    out.write_text(page, encoding="utf-8")
    print(f"{out}: {info['steps']} steps, oracle on {info['oracle_inputs']} inputs, {info['bytes'] // 1024} KB")


if __name__ == "__main__":
    main()
