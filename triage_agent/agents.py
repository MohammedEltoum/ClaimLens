"""Agent definitions for the multimodal support triage pipeline."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from .llm import GemmaClient, image_data_url
from .schemas import AgentResult


JSON_ONLY = "Return only valid JSON. Do not wrap it in Markdown. Do not include commentary."


class VisionAgent:
    name = "vision"

    def __init__(self, llm: GemmaClient) -> None:
        self.llm = llm

    def run(self, image_path: str | Path) -> AgentResult:
        start = time.perf_counter()
        output = self.llm.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a visual evidence analyst for customer support. "
                        "Assess product damage from the image only. "
                        "Use severity one of: none, minor, moderate, severe. "
                        + JSON_ONLY
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Inspect this product photo and produce JSON with keys: "
                                "defect_type, severity, description, visible_evidence, confidence. "
                                "visible_evidence must be an array of short strings. confidence is 0 to 1."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url(image_path)},
                        },
                    ],
                },
            ]
        )
        return AgentResult(self.name, output, _elapsed_ms(start))


class IntentAgent:
    name = "intent"

    def __init__(self, llm: GemmaClient) -> None:
        self.llm = llm

    def run(self, complaint: str) -> AgentResult:
        start = time.perf_counter()
        output = self.llm.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a customer intent analyst. Extract the customer's ask, "
                        "sentiment, urgency, and important details. "
                        "Use urgency one of: low, medium, high. "
                        + JSON_ONLY
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Complaint text:\n"
                        f"{complaint}\n\n"
                        "Produce JSON with keys: sentiment, requested_resolution, urgency, "
                        "complaint_summary, key_details. key_details must be an array."
                    ),
                },
            ]
        )
        return AgentResult(self.name, output, _elapsed_ms(start))


class PolicyAgent:
    name = "policy"

    def __init__(self, llm: GemmaClient, policy_text: str) -> None:
        self.llm = llm
        self.policy_text = policy_text

    def run(self, vision: Dict[str, Any], intent: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        vision_json = json.dumps(vision, indent=2)
        intent_json = json.dumps(intent, indent=2)
        output = self.llm.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a policy compliance agent. Apply the provided support policy "
                        "to the vision and intent JSON. If evidence and request conflict, "
                        "or if safety/legal/fraud risk is present, set escalate true. "
                        "Decision must be one of: approve_refund, approve_replacement, deny, escalate. "
                        + JSON_ONLY
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Support policy:\n"
                        f"{self.policy_text}\n\n"
                        f"Vision JSON:\n{vision_json}\n\n"
                        f"Intent JSON:\n{intent_json}\n\n"
                        "Produce JSON with keys: decision, reasoning, escalate, next_steps, policy_refs. "
                        "next_steps and policy_refs must be arrays."
                    ),
                },
            ]
        )
        return AgentResult(self.name, output, _elapsed_ms(start))


class ReplyAgent:
    name = "reply"

    def __init__(self, llm: GemmaClient) -> None:
        self.llm = llm

    def run(self, policy_decision: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        policy_json = json.dumps(policy_decision, indent=2)
        output = self.llm.chat_text(
            [
                {
                    "role": "system",
                    "content": (
                        "You write concise, empathetic customer support replies. "
                        "Use the policy decision exactly. Do not invent benefits, timelines, "
                        "or approvals that are not in the decision. If escalation is required, "
                        "say a specialist will review the case."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Policy decision JSON:\n{policy_json}\n\n"
                        "Draft the customer-facing reply in 120 words or fewer."
                    ),
                },
            ]
        ).strip()
        return AgentResult(self.name, output, _elapsed_ms(start))


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)
