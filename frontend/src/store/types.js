// store/types.js — Frontend state type definitions
// S7-0501: Typed frontend event model

export const RUN_STATES = /** @type {const} */ ([
  "idle",
  "planning",
  "awaiting_confirmation",
  "executing",
  "recovery",
  "completed",
]);

export const INTERACTION_MODES = /** @type {const} */ ([
  "idle",
  "planning",
  "plan_review",
  "clarification",
  "recovery",
  "executing",
  "completed",
]);

export const EVENT_TYPES = /** @type {const} */ ({
  session_state: "session_state",
  run_started: "run_started",
  plan_ready: "plan_ready",
  clarification_needed: "clarification_needed",
  run_completed: "run_completed",
  runtime_rejected: "runtime_rejected",
  step_validating: "step_validating",
  step_executing: "step_executing",
  step_failed: "step_failed",
  step_skipped: "step_skipped",
  step_recorded: "step_recorded",
  permission_required: "permission_required",
  recommendation_ready: "recommendation_ready",
  recovery_needed: "recovery_needed",
  code_update: "code_update",
  export_code_result: "export_code_result",
  recovery_resolved: "recovery_resolved",
  schema_error: "schema_error",
  llm_thinking: "llm_thinking",
  llm_result: "llm_result",
  status: "status",
  error: "error",
  // E1 (B1) — backend agent registry + control mode for AgentsPopover.
  agent_settings: "agent_settings",
  // E2 (B2) — state-card events.
  no_browser: "no_browser",
  api_key_required: "api_key_required",
  human_input_required: "human_input_required",
  e2e_pending: "e2e_pending",
  // E3 (B5) — endpoint registry advertised on WS connect.
  endpoint_registry: "endpoint_registry",
  // E4 (B8/B9/B10) — execution lifecycle events.
  execution_started: "execution_started",
  operation_executed: "operation_executed",
  operation_failed: "operation_failed",
  precondition_failed: "precondition_failed",
  locator_update_request: "locator_update_request",
  locator_update_applied: "locator_update_applied",
});

export const COMMAND_TYPES = /** @type {const} */ ({
  confirm_plan: "confirm_plan",
  permission_decision: "permission_decision",
  skip_step: "skip_step",
  stop_run: "stop_run",
  correction: "correction",
  option_selected: "option_selected",
  confirmed: "confirmed",
});
