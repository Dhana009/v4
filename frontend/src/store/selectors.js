// store/selectors.js — Frontend state selectors
// S7-0502: Frontend reducer and event store

export function selectPlan(state) {
  return state.plan ?? null;
}

export function selectInteractionMode(state) {
  return state.interaction_mode ?? "idle";
}

export function selectPendingSteps(state) {
  return state.pending_steps ?? [];
}

export function selectRecordedSteps(state) {
  return state.recorded_steps ?? [];
}

export function selectRunId(state) {
  return state.run_id ?? null;
}

export function selectPhase(state) {
  return state.phase ?? "idle";
}

export function selectErrors(state) {
  return state.errors ?? [];
}

export function selectLastError(state) {
  return state.last_error ?? null;
}

export function selectConnected(state) {
  return state.connected ?? false;
}

export function selectCodePreview(state) {
  return state.code_preview ?? null;
}

export function selectPendingClarification(state) {
  return state.pending_clarification ?? null;
}

export function selectPendingPermission(state) {
  return state.pending_permission ?? null;
}

export function selectPendingRecommendations(state) {
  return state.pending_recommendations ?? [];
}
