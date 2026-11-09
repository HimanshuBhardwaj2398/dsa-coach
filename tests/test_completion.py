import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import completion  # noqa: E402

GOOD = {"feedback": "Your set check is right and you traced the empty list.", "missing": [],
        "evidence": "LeetCode page shows Accepted, 75/75 tests", "outcome": "solved", "complexity_stated": True,
        "technique": None, "mistakes": [], "rung": 0}
INPUTS = {"problem": "contains-duplicate", "stage_notes": {"2": "seen set"}, "plan_card": {}, "examples": [],
          "rung": 1, "outcome": "solved", "lesson": "a set answers 'seen before?' in O(1)",
          "outside_help": False, "code": "class Solution: ..."}


def result(text):
    return json.dumps({"type": "result", "is_error": False, "result": text})


class CompletionTest(unittest.TestCase):
    def test_a_valid_review_is_recordable(self):
        review = completion.parse(result(json.dumps(GOOD)), "solved")
        self.assertTrue(review["recordable"])
        self.assertEqual(review["outcome"], "solved")

    def test_a_fenced_reply_is_read(self):
        review = completion.parse(result("```json\n" + json.dumps(GOOD) + "\n```"), "solved")
        self.assertEqual(review["feedback"], GOOD["feedback"])

    def test_missing_evidence_is_not_recordable(self):
        review = completion.parse(result(json.dumps({**GOOD, "missing": ["Run the empty-list case and share the result"]})), "solved")
        self.assertFalse(review["recordable"])

    def test_the_record_is_never_better_than_the_learners_own_outcome(self):
        self.assertEqual(completion.parse(result(json.dumps(GOOD)), "partial")["outcome"], "partial")
        self.assertEqual(completion.parse(result(json.dumps({**GOOD, "outcome": "failed"})), "solved")["outcome"], "failed")

    def test_invalid_reviews_are_rejected(self):
        for bad in [{**GOOD, "outcome": "great"}, {**GOOD, "technique": "magic"}, {**GOOD, "mistakes": ["typo"]},
                    {**GOOD, "rung": 9}, {**GOOD, "rung": True}, {**GOOD, "complexity_stated": "yes"},
                    {**GOOD, "feedback": ""}, {k: v for k, v in GOOD.items() if k != "missing"}, [GOOD]]:
            with self.assertRaises(ValueError, msg=bad):
                completion.parse(result(json.dumps(bad)), "solved")
        with self.assertRaises(ValueError):
            completion.parse(result("Looks good to me!"), "solved")
        with self.assertRaises(ValueError):
            completion.parse(json.dumps({"type": "result", "is_error": True, "result": "not signed in"}), "solved")

    def test_fingerprint_follows_what_the_review_assessed(self):
        same = completion.fingerprint(dict(INPUTS))
        self.assertEqual(completion.fingerprint({**INPUTS, "page_text": "timer 12:01"}), same)  # not assessed
        for key, value in [("code", "changed"), ("lesson", "other"), ("outcome", "partial"), ("outside_help", True),
                           ("rung", 2), ("stage_notes", {"2": "seen list"}), ("examples", [{"args": "[]"}])]:
            self.assertNotEqual(completion.fingerprint({**INPUTS, key: value}), same, key)

    def test_request_sends_inputs_as_data_with_tools_off_by_the_caller(self):
        system, stream = completion.request(INPUTS, "page says Accepted")
        self.assertIn("JSON", system)
        self.assertIn("never claim", system.lower())
        message = json.loads(stream)["message"]["content"][0]["text"]
        self.assertEqual(json.loads(message)["page_text"], "page says Accepted")
        self.assertEqual(json.loads(message)["lesson"], INPUTS["lesson"])


if __name__ == "__main__":
    unittest.main()
