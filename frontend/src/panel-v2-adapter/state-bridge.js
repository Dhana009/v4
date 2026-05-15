import { PANEL_V2_VIEW_MODEL_VERSION } from "./types.js";

function derivePhaseFromStore(storeState, transport) {
  if (!storeState) return derivePhaseFromTransport(transport);

  const { connectionStatus } = transport;
  if (connectionStatus === "offline") return "offline";

  if (storeState.no_browser_state) return "nobrowser";
  if (storeState.api_key_required_state) return "apikey";
  if (storeState.pending_permission) return "permit";
  if (storeState.pending_recovery) return "recover";

  const phase = storeState.phase;
  const mode = storeState.interaction_mode;

  if (phase === "awaiting_confirmation") {
    if (mode === "clarification") return "clarify";
    if (mode === "plan_review") return "plan";
    return "plan";
  }
  if (phase === "executing") return "exec";
  if (phase === "recovery") return "recover";
  if (phase === "completed") return "done";
  if (phase === "planning") return "planning";
  return "idle";
}

function derivePhaseFromTransport(transport) {
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

export function mapTransportToViewModel(transport, storeState) {
  const phase = derivePhaseFromStore(storeState, transport);
  const connection = deriveConnection(transport);

  const pendingSteps = storeState?.pending_steps ?? transport.pendingSteps ?? [];
  const recordedSteps = storeState?.recorded_steps ?? transport.recordedSteps ?? [];
  const codePreview = storeState?.code_preview ?? transport.codePreview ?? null;
  const traceEntries = storeState?.trace_entries ?? transport.traceEntries ?? [];
  const conversation = transport.conversation ?? [];

  const runId = storeState?.run_id ?? transport.run_id ?? null;
  const agents = storeState?.agents ?? null;

  return {
    _version: PANEL_V2_VIEW_MODEL_VERSION,
    mode: "live",
    runtime: {
      phase,
      connection,
      runId,
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
    agents,
    steps: pendingSteps,
    recorded: recordedSteps,
    code: codePreview,
    trace: traceEntries,
  };
}
