import unittest

from triage_agent.example_cases import SUPPORT_EXAMPLES


class SupportExampleTests(unittest.TestCase):
    def test_examples_have_existing_images(self):
        self.assertGreaterEqual(len(SUPPORT_EXAMPLES), 6)
        for example in SUPPORT_EXAMPLES:
            self.assertTrue(example.image_path.exists(), example.image_path)

    def test_examples_fill_image_and_complaint_only(self):
        row = SUPPORT_EXAMPLES[0].as_gradio_row()

        self.assertEqual(len(row), 2)
        self.assertTrue(row[0])
        self.assertTrue(row[1])


if __name__ == "__main__":
    unittest.main()
