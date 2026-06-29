import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from triage_agent.orchestrator import TriagePipeline
from triage_agent.schemas import AgentResult


class FakeAgent:
    def __init__(self, name, output):
        self.name = name
        self.output = output

    def run(self, *args):
        return AgentResult(self.name, self.output, 1)


class PipelineTests(unittest.TestCase):
    def test_pipeline_merges_agent_outputs(self):
        with TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "image.png"
            image_path.write_bytes(b"not a real image but enough for existence check")

            pipeline = TriagePipeline.__new__(TriagePipeline)
            pipeline.vision_agent = FakeAgent("vision", {"severity": "moderate"})
            pipeline.intent_agent = FakeAgent("intent", {"requested_resolution": "replacement"})
            pipeline.policy_agent = FakeAgent(
                "policy",
                {"decision": "approve_replacement", "escalate": False},
            )
            pipeline.reply_agent = FakeAgent("reply", "We will send a replacement.")

            result = pipeline.run(image_path=image_path, complaint="Please replace this.")
            payload = result.to_dict()

            self.assertEqual(
                payload["structured_ticket"]["policy"]["decision"],
                "approve_replacement",
            )
            self.assertEqual(payload["structured_ticket"]["reply"], "We will send a replacement.")
            self.assertIn("total_wall_clock_ms", payload["latency_dashboard"])

    def test_pipeline_requires_complaint(self):
        with TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "image.png"
            image_path.write_bytes(b"x")

            pipeline = TriagePipeline.__new__(TriagePipeline)

            with self.assertRaises(ValueError):
                pipeline.run(image_path=image_path, complaint=" ")


if __name__ == "__main__":
    unittest.main()
