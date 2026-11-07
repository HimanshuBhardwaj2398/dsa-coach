#!/usr/bin/env python3
"""Offline Claude stream fixture for the browser companion check."""
import json
import sys

assert sys.argv[sys.argv.index("--tools") + 1] == ""
event = json.loads(sys.stdin.readline())
context = json.loads(event["message"]["content"][0]["text"])
assert context["problem"] == "two-sum"
assert context["page_text"] == "LeetCode fixture"
assert event["message"]["content"][1]["type"] == "image"
print(json.dumps({"type": "result", "is_error": False,
                  "result": "I can see your LeetCode context. What should happen when the same value appears twice?"}))
