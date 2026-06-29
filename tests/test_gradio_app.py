import unittest

from triage_agent.gradio_app import _lan_url, run_triage_ui


class FakePipelineResult:
    def to_dict(self):
        return {
            "structured_ticket": {
                "vision": {"severity": "moderate"},
                "intent": {
                    "requested_resolution": "replacement",
                    "urgency": "high",
                },
                "policy": {
                    "decision": "approve_replacement",
                    "reasoning": "Visible damage satisfies the policy.",
                    "escalate": False,
                },
                "reply": "We can send a replacement.",
            },
            "latency_dashboard": {
                "vision_ms": 100,
                "intent_ms": 90,
                "policy_ms": 80,
                "reply_ms": 70,
                "total_wall_clock_ms": 250,
            },
        }


class FakePipeline:
    def run(self, *, image_path, complaint):
        return FakePipelineResult()


class GradioAppTests(unittest.TestCase):
    def test_api_mode_returns_component_outputs(self):
        status, decision_html, reply, latency_html, vision, intent, policy, ticket = run_triage_ui(
            None,
            "The item arrived cracked and I need a replacement.",
            "Gemini",
            pipeline_factory=lambda provider: FakePipeline(),
        )

        self.assertIn("Gemini API run complete", status)
        self.assertIn("Approve Replacement", decision_html)
        self.assertIn("Gemini", decision_html)
        self.assertEqual(vision["severity"], "moderate")
        self.assertEqual(intent["requested_resolution"], "replacement")
        self.assertEqual(policy["decision"], "approve_replacement")
        self.assertTrue(reply)
        self.assertIn("Total wall clock", latency_html)
        self.assertIn("structured_ticket", ticket)

    def test_empty_complaint_returns_status(self):
        status, decision_html, reply, latency_html, vision, intent, policy, ticket = run_triage_ui(
            None,
            " ",
            "Gemini",
        )

        self.assertEqual(status, "Complaint text is required.")
        self.assertIn("Pending", decision_html)
        self.assertEqual(vision, {})
        self.assertEqual(intent, {})
        self.assertEqual(policy, {})
        self.assertEqual(reply, "")
        self.assertIn("0 ms", latency_html)
        self.assertEqual(ticket, {})

    def test_lan_url_keeps_explicit_host(self):
        self.assertEqual(_lan_url("127.0.0.1", 7860), "http://127.0.0.1:7860/")


if __name__ == "__main__":
    unittest.main()
