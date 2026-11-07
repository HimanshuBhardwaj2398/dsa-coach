"""Runs the coach headless (`claude -p ...`), one job at a time, so a page can start one and check on it."""
from __future__ import annotations

import subprocess
import threading


class Busy(Exception):
    pass


class Jobs:
    def __init__(self, run=subprocess.run):
        self._run = run  # injectable, for tests
        self._lock = threading.Lock()
        self._jobs: dict = {}
        self._running: str | None = None

    def start(self, key: str, argv: list, cwd, timeout: float, input_text=None, collect=False) -> None:
        with self._lock:
            if self._running:
                raise Busy(f"the coach is busy with {self._running}; try again when it's done")
            self._running = key
            if len(self._jobs) >= 24:
                self._jobs.pop(next(iter(self._jobs)))
            self._jobs[key] = {"state": "running", "error": None}
        threading.Thread(target=self._work, args=(key, argv, cwd, timeout, input_text, collect), daemon=True).start()

    def status(self, key: str) -> dict:
        with self._lock:
            return dict(self._jobs.get(key, {"state": "idle", "error": None}))

    def _work(self, key: str, argv: list, cwd, timeout: float, input_text, collect) -> None:
        output = ""
        try:
            kwargs = {"input": input_text} if input_text is not None else {}
            proc = self._run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, **kwargs)
            if collect:
                output = proc.stdout or ""
            error = None if proc.returncode == 0 else \
                ((proc.stderr or proc.stdout or "").strip()[-500:] or f"{argv[0]} exited with {proc.returncode}")
        except FileNotFoundError:
            error = f"can't find {argv[0]}: set claude_bin in notebook/config.json"
        except subprocess.TimeoutExpired:
            error = f"the coach took longer than {int(timeout)} s and was stopped"
        except OSError as exc:
            error = f"couldn't start the coach: {exc}"
        with self._lock:
            self._jobs[key] = {"state": "error" if error else "done", "error": error}
            if collect and not error:
                self._jobs[key]["output"] = output
            self._running = None
