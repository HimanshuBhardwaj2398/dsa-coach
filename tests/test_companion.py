import base64
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import companion


class CompanionTest(unittest.TestCase):
    def test_text_and_image_are_stdin_content_with_tools_disabled(self):
        data = {"problem": "two-sum", "question": "What should I check?", "page_text": "return []",
                "history": [{"role": "assistant", "text": "Try an edge case."}],
                "screenshot": "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode()}
        system, stream = companion.request(data, {"stage": 7}, "Stage protocol")
        event = json.loads(stream)
        content = event["message"]["content"]
        self.assertEqual(content[1]["source"]["media_type"], "image/png")
        self.assertEqual(json.loads(content[0]["text"])["page_text"], "return []")
        self.assertIn("untrusted observations", system)
        args = companion.argv("claude", system)
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--no-session-persistence", args)
        self.assertNotIn(data["screenshot"], args)

    def test_bad_inputs_are_rejected_before_launch(self):
        for patch in ({"question": ""}, {"page_text": "x" * 24001}, {"history": [{}]},
                      {"screenshot": "data:image/svg+xml;base64,abc"},
                      {"screenshot": "data:image/png;base64,aW52YWxpZA=="}):
            with self.subTest(patch=list(patch)), self.assertRaises(ValueError):
                companion.request({"problem": "two-sum", "question": "Help", **patch}, None, "")

    def test_only_a_successful_result_event_becomes_a_reply(self):
        result = json.dumps({"type": "result", "is_error": False, "result": "What happens for an empty list?"})
        self.assertEqual(companion.response('not JSON\n{"type":"assistant"}\n' + result), "What happens for an empty list?")
        for output in ("", '{"type":"result","is_error":true,"result":"Sign in first"}', '{"type":"assistant"}'):
            with self.assertRaises(ValueError):
                companion.response(output)
