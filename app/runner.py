"""Run an attempt file's EXAMPLES against its class Solution, in a child process with a time limit.

    python3 app/runner.py FILE     prints the result as JSON

The child imports the file under a name other than __main__, so the file's own test loop doesn't run.
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


def run(path, timeout: float = TIMEOUT_S) -> dict:
    """{"ok", "method", "rows": [{"ok", "args", "expected", "got", "stdout", "error"}], "error"}"""
    try:
        proc = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--child", str(path)],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "method": None, "rows": [],
                "error": f"timed out after {timeout:g} s: an infinite loop, or too slow for these inputs"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "method": None, "rows": [],
                "error": (proc.stderr or proc.stdout or "the runner stopped without a result").strip()[-3000:]}


def _trace() -> str:
    return traceback.format_exc()[-3000:]


def run_row(solution: type, name: str, row) -> dict:
    try:
        args, expected = row
        args = tuple(args)
    except (TypeError, ValueError):
        return {"ok": False, "args": repr(row), "expected": "", "got": "", "stdout": "",
                "error": "Each example must be ((args, ...), expected)."}
    result = {"ok": False, "args": ", ".join(map(repr, args)), "expected": repr(expected), "got": "",
              "stdout": "", "error": None}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            got = getattr(solution(), name)(*copy.deepcopy(args))
        result.update(ok=bool(got == expected), got=repr(got))
    except Exception:
        result["error"] = _trace()
    result["stdout"] = buf.getvalue()[-2000:]
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
    out["rows"] = [run_row(solution, out["method"], row) for row in examples]
    out["ok"] = all(r["ok"] for r in out["rows"])
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        print(json.dumps(child(sys.argv[2])))
    elif len(sys.argv) == 2:
        print(json.dumps(run(sys.argv[1]), indent=2))
    else:
        sys.exit("usage: python3 app/runner.py FILE")
