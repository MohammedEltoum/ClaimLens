import unittest

from triage_agent.json_utils import JSONExtractionError, extract_json


class ExtractJsonTests(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(extract_json('{"severity": "moderate"}'), {"severity": "moderate"})

    def test_fenced_json(self):
        text = '```json\n{"decision": "approve_replacement"}\n```'
        self.assertEqual(extract_json(text), {"decision": "approve_replacement"})

    def test_prefixed_json(self):
        text = 'Here is the result: {"urgency": "high", "key_details": ["gift"]}'
        self.assertEqual(
            extract_json(text),
            {"urgency": "high", "key_details": ["gift"]},
        )

    def test_raises_on_missing_json(self):
        with self.assertRaises(JSONExtractionError):
            extract_json("not json at all")


if __name__ == "__main__":
    unittest.main()
