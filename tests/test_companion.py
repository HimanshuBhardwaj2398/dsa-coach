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
        data["code"] = "class Solution: ..."
        system, stream = companion.request(data, {"stage": 3}, "Stage protocol")
        event = json.loads(stream)
        content = event["message"]["content"]
        self.assertEqual(content[1]["source"]["media_type"], "image/png")
        self.assertEqual(json.loads(content[0]["text"])["page_text"], "return []")
        self.assertEqual(json.loads(content[0]["text"])["code"], "class Solution: ...")
        self.assertIn("[[LOOK]]", system)
        self.assertIn("RUNG: n", system)
        self.assertIn("untrusted observations", system)
        args = companion.argv("claude", system)
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--no-session-persistence", args)
        self.assertNotIn(data["screenshot"], args)

    def test_bad_inputs_are_rejected_before_launch(self):
        for patch in ({"question": ""}, {"page_text": "x" * 24001}, {"code": "x" * 24001}, {"history": [{}]},
                      {"screenshot": "data:image/svg+xml;base64,abc"},
                      {"screenshot": "data:image/png;base64,aW52YWxpZA=="}):
            with self.subTest(patch=list(patch)), self.assertRaises(ValueError):
                companion.request({"problem": "two-sum", "question": "Help", **patch}, None, "")

    def test_only_a_successful_result_event_becomes_a_reply(self):
        result = json.dumps({"type": "result", "is_error": False, "result": "What happens for an empty list?"})
        self.assertEqual(companion.response('not JSON\n{"type":"assistant"}\n' + result),
                         {"reply": "What happens for an empty list?", "rung": None, "look": False})
        for output in ("", '{"type":"result","is_error":true,"result":"Sign in first"}', '{"type":"assistant"}'):
            with self.assertRaises(ValueError):
                companion.response(output)

    def test_the_reply_carries_its_rung_and_a_request_to_look(self):
        self.assertEqual(companion.parse_reply("Try a set.\n\nRUNG: 3"), {"reply": "Try a set.", "rung": 3, "look": False})
        self.assertEqual(companion.parse_reply("Try a set.\n**RUNG: 2**"), {"reply": "Try a set.", "rung": 2, "look": False})
        self.assertEqual(companion.parse_reply("[[LOOK]]\nRUNG: 0"), {"reply": "[[LOOK]]", "rung": 0, "look": True})
        for text in ("Try a set.\nRUNG: 9", "Try a set.\nRUNG: three", "RUNG: 3 is the pattern rung, then more"):
            with self.subTest(text=text):
                self.assertIsNone(companion.parse_reply(text)["rung"])
