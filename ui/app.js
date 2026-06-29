const sampleComplaint =
  "The radio arrived with the front casing cracked and one of the knobs loose. I bought it as a birthday gift and need a replacement sent as soon as possible.";

const state = {
  imageDataUrl: null,
  imageName: "radio2.png",
  lastPayload: null,
};

const elements = {
  runButton: document.querySelector("#runButton"),
  exportButton: document.querySelector("#exportButton"),
  sampleButton: document.querySelector("#sampleButton"),
  clearButton: document.querySelector("#clearButton"),
  complaintText: document.querySelector("#complaintText"),
  imageInput: document.querySelector("#imageInput"),
  productPreview: document.querySelector("#productPreview"),
  fileName: document.querySelector("#fileName"),
  decisionBadge: document.querySelector("#decisionBadge"),
  decisionReason: document.querySelector("#decisionReason"),
  escalateMetric: document.querySelector("#escalateMetric"),
  urgencyMetric: document.querySelector("#urgencyMetric"),
  severityMetric: document.querySelector("#severityMetric"),
  totalLatency: document.querySelector("#totalLatency"),
  eventLog: document.querySelector("#eventLog"),
};

const outputIds = {
  vision: "visionOutput",
  intent: "intentOutput",
  policy: "policyOutput",
  reply: "replyOutput",
};

elements.imageInput.addEventListener("change", handleImageChange);
elements.runButton.addEventListener("click", runTriage);
elements.exportButton.addEventListener("click", exportJson);
elements.sampleButton.addEventListener("click", () => {
  elements.complaintText.value = sampleComplaint;
});
elements.clearButton.addEventListener("click", () => {
  elements.complaintText.value = "";
  elements.complaintText.focus();
});

function handleImageChange(event) {
  const [file] = event.target.files;
  if (!file) return;
  state.imageName = file.name;
  elements.fileName.textContent = file.name;

  const reader = new FileReader();
  reader.addEventListener("load", () => {
    state.imageDataUrl = reader.result;
    elements.productPreview.src = reader.result;
  });
  reader.readAsDataURL(file);
}

async function runTriage() {
  const complaint = elements.complaintText.value.trim();
  if (!complaint) {
    addLog("Complaint text is empty.");
    elements.complaintText.focus();
    return;
  }

  resetOutputs();
  setBusy(true);
  addLog("API run started.");

  try {
    const payload = await runLive(complaint);
    state.lastPayload = payload;
    renderPayload(payload);
    addLog("Ticket ready.");
  } catch (error) {
    setAgentStatus("vision", "error");
    setAgentStatus("intent", "error");
    setAgentStatus("policy", "error");
    setAgentStatus("reply", "error");
    addLog(error.message || "Run failed.");
  } finally {
    setBusy(false);
  }
}

async function runLive(complaint) {
  const response = await fetch("/api/triage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      complaint,
      image_data_url: state.imageDataUrl,
      image_name: state.imageName,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "API run failed.");
  }
  return payload;
}

function renderPayload(payload) {
  const ticket = payload.structured_ticket || {};
  const latency = payload.latency_dashboard || {};
  const policy = ticket.policy || {};

  setOutput("vision", ticket.vision || {});
  setOutput("intent", ticket.intent || {});
  setOutput("policy", policy);
  setOutput("reply", ticket.reply || "");

  renderDecision(ticket);
  renderLatency(latency);

  ["vision", "intent", "policy", "reply"].forEach((agent) => {
    setAgentStatus(agent, "done");
  });
}

function renderDecision(ticket) {
  const policy = ticket.policy || {};
  const intent = ticket.intent || {};
  const vision = ticket.vision || {};
  const decision = policy.decision || "pending";

  elements.decisionBadge.textContent = decision.replaceAll("_", " ");
  elements.decisionBadge.className = "decision-badge";
  if (decision.includes("approve")) {
    elements.decisionBadge.classList.add("approved");
  } else if (decision.includes("escalate") || policy.escalate) {
    elements.decisionBadge.classList.add("escalate");
  } else if (decision.includes("deny")) {
    elements.decisionBadge.classList.add("denied");
  } else {
    elements.decisionBadge.classList.add("neutral");
  }

  elements.decisionReason.textContent = policy.reasoning || "Waiting for agent output.";
  elements.escalateMetric.textContent =
    typeof policy.escalate === "boolean" ? (policy.escalate ? "Yes" : "No") : "-";
  elements.urgencyMetric.textContent = intent.urgency || "-";
  elements.severityMetric.textContent = vision.severity || "-";
}

function renderLatency(latency) {
  const values = {
    vision: latency.vision_ms || 0,
    intent: latency.intent_ms || 0,
    policy: latency.policy_ms || 0,
    reply: latency.reply_ms || 0,
  };
  const max = Math.max(...Object.values(values), 1);

  Object.entries(values).forEach(([agent, value]) => {
    document.querySelector(`#${agent}Latency`).textContent = String(value);
    document.querySelector(`#${agent}Bar`).style.width = `${Math.max(
      8,
      Math.round((value / max) * 100),
    )}%`;
  });

  elements.totalLatency.textContent = `${latency.total_wall_clock_ms || 0} ms`;
}

function resetOutputs() {
  ["vision", "intent", "policy"].forEach((agent) => setOutput(agent, {}));
  setOutput("reply", "No reply drafted yet.");
  ["vision", "intent", "policy", "reply"].forEach((agent) =>
    setAgentStatus(agent, "idle"),
  );
  renderDecision({});
  renderLatency({});
  elements.eventLog.innerHTML = "";
}

function setOutput(agent, value) {
  const target = document.querySelector(`#${outputIds[agent]}`);
  if (agent === "reply") {
    target.textContent = value || "No reply drafted yet.";
    return;
  }
  target.textContent = JSON.stringify(value || {}, null, 2);
}

function setAgentStatus(agent, status) {
  const pill = document.querySelector(`[data-status="${agent}"]`);
  const card = document.querySelector(`[data-agent-card="${agent}"]`);
  pill.textContent = status.charAt(0).toUpperCase() + status.slice(1);
  pill.className = `status-pill ${status}`;
  card.classList.remove("idle", "running", "done", "error");
  card.classList.add(status);
}

function addLog(message) {
  const item = document.createElement("li");
  item.textContent = message;
  elements.eventLog.prepend(item);
}

function setBusy(isBusy) {
  elements.runButton.disabled = isBusy;
  elements.runButton.textContent = isBusy ? "Running" : "Run Triage";
}

function exportJson() {
  const payload =
    state.lastPayload ||
    {
      input: {
        image_path: state.imageName,
        complaint: elements.complaintText.value.trim(),
      },
      structured_ticket: {},
      latency_dashboard: {},
    };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "triage-ticket.json";
  link.click();
  URL.revokeObjectURL(link.href);
}
