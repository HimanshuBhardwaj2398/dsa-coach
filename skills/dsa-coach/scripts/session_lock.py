"""Cooperating solve writers share a bounded cross-process lock (stdlib only)."""
from contextlib import contextmanager
import errno
import hashlib
import os
from pathlib import Path
import time


def session_identity(live):
    """Legacy sessions receive a stable identity without a migration write."""
    return live.get("session_id") or hashlib.sha256(
        (live["file"] + "\0" + live["started"]).encode()).hexdigest()


@contextmanager
def session_lock(root, timeout=5):
    path = Path(root) / "sessions" / ".solve.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            def acquire():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            def release():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def acquire():
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            def release():
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("the solve is busy; try again in a moment") from None
                time.sleep(min(0.025, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            release()
