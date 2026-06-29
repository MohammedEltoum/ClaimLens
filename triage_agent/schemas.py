"""Shared data shapes used by the triage pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, TypedDict


Severity = Literal["none", "minor", "moderate", "severe"]
Urgency = Literal["low", "medium", "high"]
Decision = Literal["approve_refund", "approve_replacement", "deny", "escalate"]


class VisionOutput(TypedDict, total=False):
    defect_type: str
    severity: Severity
    description: str
    visible_evidence: List[str]
    confidence: float


class IntentOutput(TypedDict, total=False):
    sentiment: str
    requested_resolution: str
    urgency: Urgency
    complaint_summary: str
    key_details: List[str]


class PolicyOutput(TypedDict, total=False):
    decision: Decision
    reasoning: str
    escalate: bool
    next_steps: List[str]
    policy_refs: List[str]


@dataclass(frozen=True)
class AgentResult:
    """One agent output plus timing metadata."""

    name: str
    output: Any
    latency_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TriageResult:
    """Final pipeline artifact suitable for display or persistence."""

    image_path: str
    complaint: str
    vision: AgentResult
    intent: AgentResult
    policy: AgentResult
    reply: AgentResult
    total_latency_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": {
                "image_path": self.image_path,
                "complaint": self.complaint,
            },
            "agents": {
                "vision": self.vision.to_dict(),
                "intent": self.intent.to_dict(),
                "policy": self.policy.to_dict(),
                "reply": self.reply.to_dict(),
            },
            "latency_dashboard": {
                "vision_ms": self.vision.latency_ms,
                "intent_ms": self.intent.latency_ms,
                "policy_ms": self.policy.latency_ms,
                "reply_ms": self.reply.latency_ms,
                "total_wall_clock_ms": self.total_latency_ms,
            },
            "structured_ticket": {
                "vision": self.vision.output,
                "intent": self.intent.output,
                "policy": self.policy.output,
                "reply": self.reply.output,
            },
        }
