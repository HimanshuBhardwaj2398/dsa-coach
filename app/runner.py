"""Run an attempt file's EXAMPLES against its class Solution, in a child process with a time limit.

    python3 app/runner.py FILE     prints the result as JSON

The child imports the file under a name other than __main__, so the file's own test loop doesn't run.
It prints a JSON line as each example starts and ends, so a time limit can name the example it stopped.
Each of those lines starts with MARK, and the parent reads no others: the attempt may write to stdout too.
"""
import contextlib
import copy
import io
import json
import runpy
import subprocess
import sys
import traceback
from pathlib import Path

TIMEOUT_S = 5
MARK = "\x1erunner "  # starts each line the child writes for the parent
CAP = 2000  # characters kept of a row's args, expected, got and stdout


def run(path, timeout: float = TIMEOUT_S) -> dict:
    """{"ok", "method", "rows": [{"ok", "args", "expected", "got", "stdout", "error"}], "error"}"""
    try:
        proc = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--child", str(path)],
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
        stdout = proc.stdout
    except subprocess.TimeoutExpired as e:
        proc, stdout = None, e.stdout  # what it wrote before the time limit stopped it
    messages = _messages(stdout)
    results = [m["result"] for m in messages if "result" in m]
    if results:  # even after the time limit: it finished, but something it started, such as a thread, didn't
        return results[-1]
    if proc is None:
        rows, where = _partial(messages, "timed out on this example")
        return {"ok": False, "method": None, "rows": rows,
                "error": f"timed out after {timeout:g} s{where}: an infinite loop, or too slow for these inputs"}
    crash = (proc.stderr.decode(errors="replace").strip() or "the runner stopped without a result")[-3000:]
    rows, where = _partial(messages, crash)  # a segfault, or os._exit
    return {"ok": False, "method": None, "rows": rows, "error": f"crashed{where}: {crash}" if where else crash}


def _messages(stdout) -> list:
    """The child's complete marked JSON lines; anything else on stdout is the attempt's own, and is skipped."""
    messages = []
    for line in (stdout or b"").decode(errors="replace").split("\n")[:-1]:
        if not line.startswith(MARK):
            continue
        try:
            message = json.loads(line[len(MARK):])
        except json.JSONDecodeError:
            continue
        if isinstance(message, dict):
            messages.append(message)
    return messages


def _partial(messages: list, unfinished: str) -> tuple:
    """(rows, where) when the child stopped early: the rows that finished, then the example it stopped in,
    if one had started, with `unfinished` as its error; where names that example for the top-level error."""
    rows = [m["row"] for m in messages if "row" in m]
    started = messages[-1].get("start") if messages else None
    if not started:
        return rows, ""
    rows.append({"ok": False, "args": started["args"], "expected": started["expected"], "got": None,
                 "stdout": "", "error": unfinished})
    return rows, f" on the example ({_short(started['args'], 100)}) -> {_short(started['expected'], 100)}"


def _short(text: str, n: int = CAP) -> str:
    """text, or its first n characters and "..." if it's longer, so a huge input can't flood the page."""
    return text if len(text) <= n else text[:n] + "..."


def _say(**message) -> None:
    """One marked JSON line for the parent, flushed so it gets there even if the time limit kills the child.
    It starts with a newline in case the attempt left a line unfinished on the real stdout."""
    print("\n" + MARK + json.dumps(message), flush=True)


def _trace() -> str:
    return traceback.format_exc()[-3000:]


def run_row(solution: type, name: str, row) -> dict:
    try:
        args, expected = row
        args = tuple(args)
    except (TypeError, ValueError):
        return {"ok": False, "args": _short(repr(row)), "expected": "", "got": "", "stdout": "",
                "error": "Each example must be ((args, ...), expected)."}
    result = {"ok": False, "args": _short(", ".join(map(repr, args))), "expected": _short(repr(expected)),
              "got": "", "stdout": "", "error": None}
    _say(start={"args": result["args"], "expected": result["expected"]})
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            got = getattr(solution(), name)(*copy.deepcopy(args))
        result.update(ok=bool(got == expected), got=_short(repr(got)))  # ok from the values, before the cut
    except BaseException:  # sys.exit() and exit() too, so the other rows still run
        result["error"] = _trace()
    result["stdout"] = buf.getvalue()[-CAP:]
    return result


def child(path: str) -> dict:
    out = {"ok": False, "method": None, "rows": [], "error": None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns = runpy.run_path(path, run_name="attempt")
    except BaseException:
        out["error"] = "The file didn't load:\n" + _trace()
        return out
    solution = ns.get("Solution")
    if not isinstance(solution, type):
        out["error"] = "There's no class Solution in the file."
        return out
    out["method"] = next((m for m, v in vars(solution).items() if not m.startswith("_") and callable(v)), None)
    if out["method"] is None:
        out["error"] = "Write the method inside class Solution first."
        return out
    examples = ns.get("EXAMPLES")
    if not examples:
        out["error"] = "No examples yet. Add them in stage 1."
        return out
    for row in examples:
        out["rows"].append(run_row(solution, out["method"], row))
        _say(row=out["rows"][-1])
    out["ok"] = all(r["ok"] for r in out["rows"])
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        _say(result=child(sys.argv[2]))
    elif len(sys.argv) == 2:
        print(json.dumps(run(sys.argv[1]), indent=2))
    else:
        sys.exit("usage: python3 app/runner.py FILE")
