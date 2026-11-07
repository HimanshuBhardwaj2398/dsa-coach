#!/usr/bin/env python3
"""Offline Claude stream fixture for the browser companion check."""
import json
import runpy
import sys
from pathlib import Path

if "--allowedTools" in sys.argv:  # an explainer job, which writes files, rather than the panel's read-only chat
    runpy.run_path(str(Path(__file__).with_name("fake_claude.py")), run_name="__main__")
    sys.exit()
assert sys.argv[sys.argv.index("--tools") + 1] == ""
event = json.loads(sys.stdin.readline())
context = json.loads(event["message"]["content"][0]["text"])
assert context["problem"] == "two-sum"
assert context["page_text"] == "LeetCode fixture"
assert event["message"]["content"][1]["type"] == "image"
print(json.dumps({"type": "result", "is_error": False,
                  "result": "I can see your LeetCode context. What should happen when the same value appears twice?"}))
