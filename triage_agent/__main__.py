"""Command-line entry point for the support triage app."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .llm import CEREBRAS_DEFAULT_MODEL, DEFAULT_PROVIDER, GEMINI_DEFAULT_MODEL, normalize_provider
from .orchestrator import TriagePipeline
from .policy import load_policy_text


def main() -> None:
    args = _parse_args()
    complaint = _load_complaint(args.complaint, args.complaint_file)
    policy_text = load_policy_text(args.policy)
    provider = normalize_provider(args.provider)
    model = args.model or _default_model_for_provider(provider)

    pipeline = TriagePipeline(provider=provider, model=model, policy_text=policy_text)
    result = pipeline.run(image_path=args.image, complaint=complaint)
    payload = result.to_dict()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        _print_human_summary(payload, output_path=Path(args.output) if args.output else None)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Gemma 4 multimodal customer support triage agent."
    )
    parser.add_argument("--image", required=True, help="Path to the product photo.")
    parser.add_argument("--complaint", help="Complaint text.")
    parser.add_argument("--complaint-file", help="Path to a text file containing the complaint.")
    parser.add_argument("--policy", help="Path to a Markdown policy document.")
    parser.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        choices=["cerebras", "gemini"],
        help="API provider to use.",
    )
    parser.add_argument("--model", help="Model name. Defaults depend on --provider.")
    parser.add_argument("--output", help="Optional path to write the full JSON ticket.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON ticket.")
    return parser.parse_args()


def _default_model_for_provider(provider: str) -> str:
    return GEMINI_DEFAULT_MODEL if provider == "gemini" else CEREBRAS_DEFAULT_MODEL


def _load_complaint(complaint: str | None, complaint_file: str | None) -> str:
    if complaint and complaint_file:
        raise SystemExit("Use either --complaint or --complaint-file, not both.")
    if complaint_file:
        return Path(complaint_file).read_text(encoding="utf-8").strip()
    if complaint:
        return complaint.strip()
    raise SystemExit("Provide --complaint or --complaint-file.")


def _print_human_summary(payload: dict, *, output_path: Path | None) -> None:
    ticket = payload["structured_ticket"]
    latency = payload["latency_dashboard"]

    print("\nStructured Ticket")
    print(json.dumps(ticket, indent=2))
    print("\nLatency Dashboard")
    for key, value in latency.items():
        print(f"  {key}: {value} ms")
    if output_path:
        print(f"\nSaved full ticket JSON to {output_path}")


if __name__ == "__main__":
    main()
