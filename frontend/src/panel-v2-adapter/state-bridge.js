import { PANEL_V2_VIEW_MODEL_VERSION } from "./types.js";

function derivePhase(transport) {
  const { connectionStatus, runState, interactionMode } = transport;
  if (connectionStatus === "offline") return "offline";
  if (runState === "idle" || !runState) return "idle";
  if (runState === "planning") return "planning";
  if (runState === "awaiting_confirmation") {
    if (interactionMode === "plan_review") return "plan";
    if (interactionMode === "clarification") return "clarify";
    return "plan";
  }
  if (runState === "executing") return "exec";
  if (runState === "recovery") return "recover";
  if (runState === "completed") return "done";
  return "idle";
}

function deriveConnection(transport) {
  const { connectionStatus, runState } = transport;
  if (connectionStatus === "offline") return "offline";
  if (runState === "executing") return "busy";
  return connectionStatus || "connected";
}

export function mapTransportToViewModel(transport, _storeState) {
  const phase = derivePhase(transport);
  const connection = deriveConnection(transport);

  const pendingSteps = transport.pendingSteps ?? [];
  const recordedSteps = transport.recordedSteps ?? [];
  const codePreview = transport.codePreview ?? null;
  const traceEntries = transport.traceEntries ?? [];
  const conversation = transport.conversation ?? [];

  return {
    _version: PANEL_V2_VIEW_MODEL_VERSION,
    mode: "live",
    runtime: {
      phase,
      connection,
      runId: transport.run_id ?? null,
      pageUrl: transport.pageUrl ?? null,
    },
    counts: {
      steps: pendingSteps.length,
      rec: recordedSteps.length,
      code: codePreview ? 1 : 0,
      trace: traceEntries.length,
    },
    llm: {
      messages: conversation,
    },
    steps: pendingSteps,
    recorded: recordedSteps,
    code: codePreview,
    trace: traceEntries,
  };
}
