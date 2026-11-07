#!/usr/bin/env python3
"""Stands in for `claude -p` in the browser check: writes the explainer the prompt asks for and registers it."""
import re
import subprocess
import sys
from pathlib import Path

prompt = sys.argv[2]
key = re.search(r"\(([a-z0-9-]+)\)", prompt).group(1)
root = re.search(r"--root (\S+)", prompt).group(1)
path = Path(re.search(r"--file (\S+)", prompt).group(1))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(f"<h1>{key}, explained</h1>", encoding="utf-8")
coach = Path(__file__).resolve().parents[2] / "skills/dsa-coach/scripts/coach.py"
subprocess.run([sys.executable, str(coach), "--root", root, "artifact", "add", "--concept", key,
                "--title", key, "--file", str(path)], check=True)
