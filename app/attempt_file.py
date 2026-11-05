"""The two parts of an attempt file that the Solve tab edits: the plan card in the docstring, and EXAMPLES.

Both work on text and never parse the whole file, so they keep working while the code is half-written.
"""
import ast
import re

PLAN_FIELDS = ["State", "Invariant", "Relies on", "Breaks if", "Termination", "Complexity", "Hand trace"]
FIELD = re.compile(r"^    (" + "|".join(re.escape(f) for f in PLAN_FIELDS) + r"):(.*)$")
MORE = " " * 8  # a continuation line of a multi-line field


def _docstring_end(lines: list) -> int | None:
    """Index of the line that closes the module docstring, if the file starts with one."""
    if not lines or not lines[0].startswith('"""'):
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
    """Replace the fields named in card; leave every other line as it is."""
    lines = text.split("\n")
    end = _docstring_end(lines)
    if end is None:
        raise ValueError("the attempt file has no docstring with a plan card")
    out, i = lines[:1], 1
    while i < end:
        line = lines[i]
        i += 1
        m = FIELD.match(line)
        if not m or m.group(1) not in card:
            out.append(line)
            continue
        while i < end and lines[i].startswith(MORE):  # drop the old value's continuation lines
            i += 1
        first, *rest = str(card[m.group(1)]).strip().split("\n")
        out.append(f"    {m.group(1)}: {first}".rstrip())
        out.extend(MORE + r for r in rest)
    return "\n".join(out + lines[end:])


def _examples_span(lines: list) -> tuple | None:
    """(first, last) line indexes of the EXAMPLES = [ ... ] block."""
    for i, line in enumerate(lines):
        if line.startswith("EXAMPLES = ["):
            if line.rstrip().endswith("]"):
                return i, i
            for j in range(i + 1, len(lines)):
                if lines[j].rstrip() == "]":
                    return i, j
            return None
    return None


def read_examples(text: str) -> list:
    """Rows as {"args": source text, "expected": source text, "edge": bool}."""
    lines = text.split("\n")
    span = _examples_span(lines)
    if span is None:
        return []
    block_lines = lines[span[0]:span[1] + 1]
    block = "\n".join(block_lines)
    try:
        node = ast.parse(block).body[0].value
    except SyntaxError as e:
        raise ValueError(f"EXAMPLES has a syntax error: {e.msg}") from None
    rows = []
    for elt in node.elts if isinstance(node, ast.List) else []:
        if not (isinstance(elt, ast.Tuple) and len(elt.elts) == 2 and isinstance(elt.elts[0], ast.Tuple)):
            continue
        args, expected = elt.elts
        rows.append({"args": ", ".join(ast.get_source_segment(block, a) for a in args.elts),
                     "expected": ast.get_source_segment(block, expected),
                     "edge": block_lines[elt.end_lineno - 1].rstrip().endswith("# edge")})
    return rows


def format_row(row: dict) -> str:
    args, expected = str(row.get("args", "")).strip(), str(row.get("expected", "")).strip()
    for source, what in ((f"({args},)", "the inputs"), (expected, "the expected output")):
        try:
            ast.literal_eval(source)
        except (ValueError, SyntaxError):
            raise ValueError(f"{what} must be Python values such as [1, 2], 3 or 'abc': got {source!r}") from None
    return f"    (({args},), {expected}),{'  # edge' if row.get('edge') else ''}"


def write_examples(text: str, rows: list) -> str:
    lines = text.split("\n")
    span = _examples_span(lines)
    if span is None:
        raise ValueError("the attempt file has no EXAMPLES list")
    lines[span[0]:span[1] + 1] = ["EXAMPLES = ["] + [format_row(r) for r in rows] + ["]"]
    return "\n".join(lines)
