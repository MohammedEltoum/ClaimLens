import base64
import unittest

from triage_agent.llm import normalize_provider, parse_data_url


class LLMHelperTests(unittest.TestCase):
    def test_normalize_provider(self):
        self.assertEqual(normalize_provider("Cerebras"), "cerebras")
        self.assertEqual(normalize_provider("Gemini"), "gemini")
        self.assertEqual(normalize_provider("Google Gemini"), "gemini")

    def test_parse_data_url(self):
        encoded = base64.b64encode(b"image bytes").decode("ascii")
        mime_type, data = parse_data_url(f"data:image/png;base64,{encoded}")

        self.assertEqual(mime_type, "image/png")
        self.assertEqual(data, b"image bytes")


if __name__ == "__main__":
    unittest.main()
