"""The two parts of an attempt file that the Solve tab edits: the plan card in the docstring, and EXAMPLES.

Both work on text and never parse the whole file, so they keep working while the code is half-written.
"""
from __future__ import annotations

import ast
import re

PLAN_FIELDS = ["State", "Invariant", "Relies on", "Breaks if", "Termination", "Complexity", "Hand trace"]
FIELD = re.compile(r"^    (" + "|".join(re.escape(f) for f in PLAN_FIELDS) + r"):(.*)$")
MORE = " " * 8  # a continuation line of a multi-line field


def _docstring_end(lines: list) -> int | None:
    """Index of the line that closes the module docstring, if the file starts with a multi-line one."""
    if not lines or not lines[0].startswith('"""') or '"""' in lines[0][3:]:
        return None
    return next((i for i in range(1, len(lines)) if '"""' in lines[i]), None)


def read_plan_card(text: str) -> dict:
    lines = text.split("\n")
    end = _docstring_end(lines) or 0
    card, field = {}, None
    for line in lines[1:end]:
        m = FIELD.match(line)
        if m:
            field = m.group(1)
            card[field] = m.group(2).strip()
        elif field and line.startswith(MORE):
            card[field] += "\n" + line[len(MORE):]
        else:
            field = None
    return card


def write_plan_card(text: str, card: dict) -> str:
    """Replace the fields named in card, ignoring keys that aren't in PLAN_FIELDS; leave every other line as it is.

    ValueError, naming the field, if a value would break the docstring or the docstring has no line for it.
    """
    lines = text.split("\n")
    end = _docstring_end(lines)
    if end is None:
        raise ValueError("the attempt file has no docstring with a plan card")
    values = {field: str(value).strip() for field, value in card.items() if field in PLAN_FIELDS}
    present = {m.group(1) for m in map(FIELD.match, lines[1:end]) if m}
    for field, value in values.items():
        if value and field not in present:
            raise ValueError(f"this file's plan card has no '{field}:' line; add it to the docstring, then save again")
        try:
            ast.literal_eval('"""' + value + '\n"""')
        except (ValueError, SyntaxError):
            raise ValueError(f'{field} would break the docstring: take out any """ and any backslash escape '
                             'such as \\x or \\N') from None
    out, i = lines[:1], 1
    while i < end:
        line = lines[i]
        i += 1
        m = FIELD.match(line)
        if not m or m.group(1) not in values:
            out.append(line)
            continue
        while i < end and lines[i].startswith(MORE):  # drop the old value's continuation lines
            i += 1
        first, *rest = values[m.group(1)].split("\n")
        out.append(f"    {m.group(1)}: {first}".rstrip())
        out.extend(MORE + r for r in rest)
    return "\n".join(out + lines[end:])


def _examples_span(lines: list) -> tuple | None:
    """(first, last) line indexes of the EXAMPLES = [ ... ] block, or None if there's none.

    ValueError if its end can't be found: the closing ] must end the first line or stand alone on a later one.
    """
    for i, line in enumerate(lines):
        if line.startswith("EXAMPLES = ["):
            if line.rstrip().endswith("]"):
                return i, i
            for j in range(i + 1, len(lines)):
                if lines[j].rstrip() == "]":
                    return i, j
            raise ValueError("put the closing ] of EXAMPLES alone at the start of a line")
    return None


def _rows(block: str) -> list:
    """The rows of an EXAMPLES = [ ... ] block; ValueError, for the learner, if the table couldn't show one."""
    try:
        tree = ast.parse(block)
    except SyntaxError as e:
        raise ValueError(f"EXAMPLES has a syntax error: {e.msg}") from None
    except (MemoryError, RecursionError):  # Python 3.12, on input nested thousands deep
        raise ValueError("EXAMPLES is nested too deeply to read") from None
    if len(tree.body) != 1 or not isinstance(tree.body[0].value, ast.List):
        raise ValueError("EXAMPLES must be a single list: EXAMPLES = [ ... ]")
    lines, rows = block.split("\n"), []
    for elt in tree.body[0].value.elts:
        if not (isinstance(elt, ast.Tuple) and len(elt.elts) == 2 and isinstance(elt.elts[0], ast.Tuple)):
            raise ValueError(f"EXAMPLES has a row that isn't ((args, ...), expected): {ast.get_source_segment(block, elt)}")
        args, expected = elt.elts
        after = lines[elt.end_lineno - 1].encode()[elt.end_col_offset:].decode()  # the offset counts UTF-8 bytes
        rows.append({"args": ", ".join(ast.get_source_segment(block, a) for a in args.elts),
                     "expected": ast.get_source_segment(block, expected),
                     "edge": bool(re.search(r"#\s*edge\b", after, re.I))})
    return rows


def read_examples(text: str) -> list:
    """Rows as {"args": source text, "expected": source text, "edge": bool}; ValueError if one can't be shown."""
    lines = text.split("\n")
    span = _examples_span(lines)
    return [] if span is None else _rows("\n".join(lines[span[0]:span[1] + 1]))


def _fits(args: str, expected: str) -> bool:
    """True if both are Python values and the line they make reads back as exactly one row."""
    line = f"    (({args},), {expected}),"
    try:
        ast.literal_eval(f"({args},)")
        ast.literal_eval(expected)
        return len(line.splitlines()) == 1 and len(_rows(f"EXAMPLES = [\n{line}\n]")) == 1
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False


def format_row(row: dict) -> str:
    """The EXAMPLES line for a row; ValueError, quoting what was typed, unless it reads back as that row."""
    typed, expected = str(row.get("args", "")).strip(), str(row.get("expected", "")).strip()
    args = typed.removesuffix(",").rstrip()  # one comma is fine: the template teaches (([7, 1, 5],), 4)
    if not _fits(args, expected):
        bad = [text for text, ok in ((typed, _fits(args, "0")), (expected, _fits("0", expected))) if not ok]
        raise ValueError("write the inputs and the output as Python values, such as [1, 2], 3, 'abc', True or None: "
                         "got " + " and ".join(map(repr, bad or [typed, expected])))
    return f"    (({args},), {expected}),{'  # edge' if row.get('edge') else ''}"


def write_examples(text: str, rows: list) -> str:
    lines = text.split("\n")
    span = _examples_span(lines)
    if span is None:
        raise ValueError("the attempt file has no EXAMPLES list")
    _rows("\n".join(lines[span[0]:span[1] + 1]))  # refuse to save over rows the table couldn't show
    lines[span[0]:span[1] + 1] = ["EXAMPLES = ["] + [format_row(r) for r in rows] + ["]"]
    return "\n".join(lines)
