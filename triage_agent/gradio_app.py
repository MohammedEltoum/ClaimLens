"""Gradio UI for the multimodal support triage agent."""

from __future__ import annotations

import argparse
import html
import socket
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from .example_cases import SAMPLE_COMPLAINT, SAMPLE_IMAGE_PATH, SUPPORT_EXAMPLES
from .llm import CEREBRAS_DEFAULT_MODEL, GEMINI_DEFAULT_MODEL, normalize_provider
from .orchestrator import TriagePipeline


OutputTuple = Tuple[
    str,
    str,
    str,
    str,
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]

UI_CSS = """
.gradio-container {
  max-width: 1180px !important;
  margin: 0 auto !important;
  color: #18202a;
}
#hero {
  padding: 10px 0 2px;
}
#hero h1 {
  font-size: clamp(30px, 4vw, 48px);
  line-height: 1;
  margin-bottom: 8px;
  letter-spacing: 0;
}
#hero p {
  color: #667085;
  margin: 0;
  font-size: 15px;
}
#intake-card,
#decision-card,
#handoff-card {
  border: 1px solid #d7dfdc;
  border-radius: 14px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 46px rgba(23, 32, 42, 0.08);
}
#run-button button {
  min-height: 44px;
  border-radius: 10px;
  font-weight: 800;
}
.summary-wrap {
  display: grid;
  gap: 14px;
}
.decision-badge {
  display: inline-flex;
  width: fit-content;
  min-height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0 14px;
  color: #0a4b39;
  background: #dff8ee;
  font-size: 13px;
  font-weight: 900;
  text-transform: uppercase;
}
.decision-badge.pending {
  color: #667085;
  background: #eef0ee;
}
.decision-badge.escalate {
  color: #8a4f00;
  background: #fff2d7;
}
.decision-badge.denied {
  color: #9a2218;
  background: #fee4e2;
}
.summary-reason {
  margin: 0;
  color: #475467;
  line-height: 1.48;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.metric {
  border: 1px solid #d7dfdc;
  border-radius: 12px;
  padding: 12px;
  background: #f8faf8;
}
.metric span {
  display: block;
  color: #667085;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 8px;
}
.metric strong {
  display: block;
  color: #18202a;
  font-size: 17px;
  line-height: 1.1;
  overflow-wrap: anywhere;
}
.latency-wrap {
  display: grid;
  gap: 10px;
}
.latency-row {
  display: grid;
  grid-template-columns: 58px 1fr 64px;
  gap: 10px;
  align-items: center;
  color: #667085;
  font-size: 13px;
}
.latency-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #e7ece9;
}
.latency-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #16b7a6;
}
.reply-box textarea {
  font-size: 15px !important;
  line-height: 1.55 !important;
}
.agent-json {
  min-height: 360px;
}
#examples-panel table {
  font-size: 13px;
}
#examples-panel img {
  border-radius: 10px;
}
footer {
  display: none !important;
}
@media (max-width: 760px) {
  .gradio-container {
    padding-left: 10px !important;
    padding-right: 10px !important;
  }
  #hero h1 {
    font-size: 30px;
  }
  #hero p {
    font-size: 14px;
  }
  #intake-card,
  #decision-card,
  #handoff-card {
    padding: 12px;
    border-radius: 12px;
  }
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .metric {
    min-height: 74px;
  }
  .latency-row {
    grid-template-columns: 50px 1fr 54px;
  }
  .agent-json {
    min-height: 260px;
  }
}
"""


def run_triage_ui(
    image_path: str | None,
    complaint: str,
    provider: str = "Cerebras",
    pipeline_factory: Callable[[str], TriagePipeline] | None = None,
) -> OutputTuple:
    """Run live API triage and return values for Gradio components."""

    complaint = (complaint or "").strip()
    if not complaint:
        return _empty_outputs("Complaint text is required.", provider)

    resolved_image = _resolve_image_path(image_path)
    try:
        provider_id = normalize_provider(provider)
        factory = pipeline_factory or (lambda selected_provider: TriagePipeline(provider=selected_provider))
        payload = factory(provider_id).run(image_path=resolved_image, complaint=complaint).to_dict()
        status = f"{provider.title()} API run complete."
    except Exception as exc:
        return _empty_outputs(f"Run failed: {exc}", provider)

    ticket = payload["structured_ticket"]
    latency = payload.get("latency_dashboard", {})
    return (
        status,
        _render_decision_summary(ticket, provider),
        str(ticket.get("reply", "")),
        _render_latency(latency),
        ticket.get("vision", {}),
        ticket.get("intent", {}),
        ticket.get("policy", {}),
        payload,
    )


def build_app():
    """Build and return the Gradio Blocks app."""

    try:
        import gradio as gr
    except ImportError as exc:
        raise RuntimeError("Install Gradio with `pip install -r requirements.txt`.") from exc

    with gr.Blocks(title="ClaimLens Triage", fill_width=True) as app:
        gr.Markdown(
            """
            # ClaimLens Triage
            Multimodal customer support triage for product evidence, complaint intent, policy verdicts, and customer-ready replies.
            """,
            elem_id="hero",
        )

        with gr.Row():
            with gr.Column(scale=4, min_width=300, elem_id="intake-card"):
                gr.Markdown("### Ticket Intake")
                image_input = gr.Image(
                    value=str(SAMPLE_IMAGE_PATH) if SAMPLE_IMAGE_PATH.exists() else None,
                    label="Product photo",
                    type="filepath",
                    sources=["upload", "clipboard"],
                    height=300,
                )
                complaint_input = gr.Textbox(
                    value=SAMPLE_COMPLAINT,
                    label="Customer complaint",
                    lines=7,
                    max_lines=12,
                )
                provider_input = gr.Radio(
                    choices=["Cerebras", "Gemini"],
                    value="Cerebras",
                    label="API provider",
                    info="Cerebras uses CEREBRAS_API_KEY. Gemini uses GEMINI_API_KEY.",
                )
                gr.Examples(
                    examples=[example.as_gradio_row() for example in SUPPORT_EXAMPLES if example.image_path.exists()],
                    example_labels=[example.label for example in SUPPORT_EXAMPLES if example.image_path.exists()],
                    inputs=[image_input, complaint_input],
                    label="Example tickets",
                    examples_per_page=7,
                    elem_id="examples-panel",
                )
                run_button = gr.Button("Run Triage", variant="primary", elem_id="run-button")
                status_output = gr.Markdown("Ready.")

            with gr.Column(scale=7, min_width=300, elem_id="decision-card"):
                gr.Markdown("### Decision Board")
                decision_output = gr.HTML(_render_decision_summary({}, "Cerebras"))
                reply_output = gr.Textbox(
                    label="Draft customer reply",
                    lines=8,
                    interactive=False,
                    elem_classes=["reply-box"],
                )
                latency_output = gr.HTML(_render_latency({}))

        with gr.Group(elem_id="handoff-card"):
            gr.Markdown("### Agent Handoffs")
            with gr.Tabs():
                with gr.Tab("Vision"):
                    vision_output = gr.JSON(label="Image -> defect JSON", elem_classes=["agent-json"])
                with gr.Tab("Intent"):
                    intent_output = gr.JSON(label="Text -> intent JSON", elem_classes=["agent-json"])
                with gr.Tab("Policy"):
                    policy_output = gr.JSON(label="Evidence + policy -> decision JSON", elem_classes=["agent-json"])
                with gr.Tab("Full ticket"):
                    full_ticket_output = gr.JSON(label="Complete structured ticket", elem_classes=["agent-json"])

        run_button.click(
            fn=run_triage_ui,
            inputs=[image_input, complaint_input, provider_input],
            outputs=[
                status_output,
                decision_output,
                reply_output,
                latency_output,
                vision_output,
                intent_output,
                policy_output,
                full_ticket_output,
            ],
        )

    return app


def main() -> None:
    import gradio as gr

    parser = argparse.ArgumentParser(description="Launch the Gradio support triage UI.")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host. Use 0.0.0.0 to make the app reachable on your local network.",
    )
    parser.add_argument("--port", default=7860, type=int)
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share URL.")
    args = parser.parse_args()

    app = build_app()
    print(f"Local URL: http://127.0.0.1:{args.port}/")
    print(f"Local network URL: {_lan_url(args.host, args.port)}")
    app.queue().launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="teal", neutral_hue="slate"),
        css=UI_CSS,
    )


def _resolve_image_path(image_path: str | None) -> Path:
    if image_path:
        return Path(image_path)
    if SAMPLE_IMAGE_PATH.exists():
        return SAMPLE_IMAGE_PATH
    raise FileNotFoundError("Upload a product photo before running triage.")


def _empty_outputs(status: str, provider: str = "Cerebras") -> OutputTuple:
    return status, _render_decision_summary({}, provider), "", _render_latency({}), {}, {}, {}, {}


def _render_decision_summary(ticket: Dict[str, Any], provider: str) -> str:
    vision = ticket.get("vision", {})
    intent = ticket.get("intent", {})
    policy = ticket.get("policy", {})
    decision = str(policy.get("decision", "Pending"))
    badge_class = _decision_badge_class(decision, bool(policy.get("escalate", False)))
    decision_label = html.escape(decision.replace("_", " ").title())
    reason = html.escape(str(policy.get("reasoning", "Run triage to generate a policy decision.")))
    severity = html.escape(str(vision.get("severity", "-")).title())
    urgency = html.escape(str(intent.get("urgency", "-")).title())
    resolution = html.escape(str(intent.get("requested_resolution", "-")).replace("_", " ").title())
    escalate = "Yes" if policy.get("escalate") is True else "No" if policy.get("escalate") is False else "-"
    provider_id = normalize_provider(provider)
    model = GEMINI_DEFAULT_MODEL if provider_id == "gemini" else CEREBRAS_DEFAULT_MODEL
    provider_label = html.escape(provider.title())

    return f"""
    <div class="summary-wrap">
      <span class="decision-badge {badge_class}">{decision_label}</span>
      <p class="summary-reason">{reason}</p>
      <div class="metric-grid">
        <div class="metric"><span>Severity</span><strong>{severity}</strong></div>
        <div class="metric"><span>Urgency</span><strong>{urgency}</strong></div>
        <div class="metric"><span>Resolution</span><strong>{resolution}</strong></div>
        <div class="metric"><span>Escalate</span><strong>{escalate}</strong></div>
      </div>
      <div class="metric"><span>Provider</span><strong>{provider_label}</strong></div>
      <div class="metric"><span>Model</span><strong>{html.escape(model)}</strong></div>
    </div>
    """


def _render_latency(latency: Dict[str, Any]) -> str:
    values = {
        "Vision": int(latency.get("vision_ms", 0) or 0),
        "Intent": int(latency.get("intent_ms", 0) or 0),
        "Policy": int(latency.get("policy_ms", 0) or 0),
        "Reply": int(latency.get("reply_ms", 0) or 0),
    }
    total = int(latency.get("total_wall_clock_ms", 0) or 0)
    max_value = max(values.values(), default=0) or 1
    rows = []
    for label, value in values.items():
        width = max(6, round((value / max_value) * 100)) if value else 0
        rows.append(
            f"""
            <div class="latency-row">
              <strong>{label}</strong>
              <div class="latency-track"><span class="latency-fill" style="width:{width}%"></span></div>
              <span>{value} ms</span>
            </div>
            """
        )
    return f"""
    <div class="latency-wrap">
      <div class="metric"><span>Total wall clock</span><strong>{total} ms</strong></div>
      {''.join(rows)}
    </div>
    """


def _decision_badge_class(decision: str, escalate: bool) -> str:
    normalized = decision.lower()
    if normalized == "pending":
        return "pending"
    if escalate or "escalate" in normalized:
        return "escalate"
    if "deny" in normalized:
        return "denied"
    return "approved"


def _lan_url(host: str, port: int) -> str:
    if host not in {"0.0.0.0", "::"}:
        return f"http://{host}:{port}/"
    return f"http://{_detect_lan_ip()}:{port}/"


def _detect_lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("10.255.255.255", 1))
            return sock.getsockname()[0]
        except OSError:
            return socket.gethostbyname(socket.gethostname())


if __name__ == "__main__":
    main()
