"""Pipeline orchestration for the four support triage agents."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .agents import IntentAgent, PolicyAgent, ReplyAgent, VisionAgent
from .llm import DEFAULT_MODEL, DEFAULT_PROVIDER, ProviderName, create_llm_client, load_dotenv_if_available
from .policy import load_policy_text
from .schemas import TriageResult


class TriagePipeline:
    """Runs Vision and Intent in parallel, then Policy and Reply sequentially."""

    def __init__(
        self,
        *,
        provider: ProviderName = DEFAULT_PROVIDER,
        model: str | None = None,
        policy_text: str | None = None,
        api_key: str | None = None,
    ) -> None:
        load_dotenv_if_available()
        llm = create_llm_client(provider=provider, model=model, api_key=api_key)
        resolved_policy = policy_text if policy_text is not None else load_policy_text()

        self.vision_agent = VisionAgent(llm)
        self.intent_agent = IntentAgent(llm)
        self.policy_agent = PolicyAgent(llm, resolved_policy)
        self.reply_agent = ReplyAgent(llm)

    def run(self, *, image_path: str | Path, complaint: str) -> TriageResult:
        start = time.perf_counter()
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        if not complaint.strip():
            raise ValueError("Complaint text is required.")

        with ThreadPoolExecutor(max_workers=2) as executor:
            vision_future = executor.submit(self.vision_agent.run, path)
            intent_future = executor.submit(self.intent_agent.run, complaint)
            vision_result = vision_future.result()
            intent_result = intent_future.result()

        policy_result = self.policy_agent.run(vision_result.output, intent_result.output)
        reply_result = self.reply_agent.run(policy_result.output)
        total_latency_ms = round((time.perf_counter() - start) * 1000)

        return TriageResult(
            image_path=str(path),
            complaint=complaint,
            vision=vision_result,
            intent=intent_result,
            policy=policy_result,
            reply=reply_result,
            total_latency_ms=total_latency_ms,
        )
