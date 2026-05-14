// store/reducer.js — Pure frontend state reducer
// S7-0502: Frontend reducer and event store
// S7-0503: session_state restore
// S7-0504: run_completed/runtime_rejected/error handlers
// S7-0505: step lifecycle correlation
// S7-0506: permission/recommendation/recovery handlers

import { EVENT_TYPES } from "./types.js";

export function createInitialState() {
  return {
    connected: false,
    run_id: null,
    phase: "idle",
    plan: null,
    pending_steps: [],
    recorded_steps: [],
    pending_clarification: null,
    pending_permission: null,
    pending_recovery: null,
    pending_recommendations: [],
    code_preview: null,
    code_save_result: null,
    trace_entries: [],
    errors: [],
    interaction_mode: "idle",
    last_error: null,
    session_metadata: null,
  };
}

function isStaleRunId(state, payload) {
  if (!state || !state.run_id) return false;
  const incoming = payload?.run_id;
  if (!incoming) return false;
  return incoming !== state.run_id;
}

function dedupeRecordedSteps(existing, incoming) {
  if (!incoming) return existing;
  const incomingId = incoming.step_id ?? incoming.id;
  if (!incomingId) return [...existing, incoming];
  const filtered = existing.filter((s) => (s.step_id ?? s.id) !== incomingId);
  return [...filtered, incoming];
}

export function reducer(state, event) {
  const { type, payload = {} } = event || {};

  switch (type) {
    case EVENT_TYPES.session_state: {
      // S7-0503: replace stale local state with backend session truth.
      // Use ?? to fall back to current state when fields are missing.
      return {
        ...state,
        connected: true,
        run_id: payload.run_id ?? state.run_id,
        phase: payload.phase ?? payload.state ?? state.phase,
        plan: payload.plan ?? state.plan,
        pending_steps: payload.pending_steps ?? state.pending_steps,
        recorded_steps: payload.recorded_steps ?? state.recorded_steps,
        code_preview: payload.code_preview ?? payload.code ?? state.code_preview,
        pending_clarification: payload.pending_clarification ?? state.pending_clarification,
        pending_permission: payload.pending_permission ?? state.pending_permission,
        pending_recovery: payload.pending_recovery ?? state.pending_recovery,
        pending_recommendations: payload.pending_recommendations ?? state.pending_recommendations,
        interaction_mode: payload.interaction_mode ?? state.interaction_mode,
        session_metadata: payload,
      };
    }

    case EVENT_TYPES.run_started: {
      return {
        ...createInitialState(),
        connected: state.connected,
        run_id: payload.run_id ?? state.run_id,
        phase: "planning",
        interaction_mode: "planning",
      };
    }

    case EVENT_TYPES.plan_ready: {
      return {
        ...state,
        plan: payload.plan ?? payload,
        pending_steps: payload.plan?.steps ?? payload.steps ?? state.pending_steps,
        phase: "awaiting_confirmation",
        interaction_mode: "plan_review",
        pending_clarification: null,
      };
    }

    case EVENT_TYPES.clarification_needed: {
      return {
        ...state,
        phase: "awaiting_confirmation",
        interaction_mode: "clarification",
        pending_clarification: payload.clarification ?? payload,
      };
    }

    case EVENT_TYPES.run_completed: {
      // S7-0504: never enter completed while recovery is open
      if (state.pending_recovery) {
        return {
          ...state,
          last_error: "run_completed received while pending_recovery open",
        };
      }
      return {
        ...state,
        phase: "completed",
        interaction_mode: "completed",
        pending_steps: [],
      };
    }

    case EVENT_TYPES.runtime_rejected: {
      return {
        ...state,
        last_error: payload.rejection_reason ?? payload.reason ?? null,
        errors: [...state.errors, payload],
      };
    }

    case "error":
    case EVENT_TYPES.schema_error: {
      return {
        ...state,
        last_error: payload.message ?? payload.reason ?? type,
        errors: [...state.errors, { type, ...payload }],
      };
    }

    case EVENT_TYPES.step_validating: {
      if (isStaleRunId(state, payload)) return state;
      return {
        ...state,
        phase: "executing",
        interaction_mode: "executing",
      };
    }

    case EVENT_TYPES.step_executing: {
      if (isStaleRunId(state, payload)) return state;
      return {
        ...state,
        phase: "executing",
        interaction_mode: "executing",
      };
    }

    case EVENT_TYPES.step_failed: {
      if (isStaleRunId(state, payload)) return state;
      return {
        ...state,
        errors: [...state.errors, payload],
        last_error: payload.reason ?? payload.message ?? null,
      };
    }

    case EVENT_TYPES.step_skipped: {
      if (isStaleRunId(state, payload)) return state;
      const skipId = payload.step_id ?? payload.id;
      return {
        ...state,
        pending_steps: state.pending_steps.filter(
          (s) => (s.step_id ?? s.id) !== skipId
        ),
      };
    }

    case EVENT_TYPES.step_recorded: {
      if (isStaleRunId(state, payload)) return state;
      // S7-0505: dedupe by step_id to keep reconnect safe
      return {
        ...state,
        recorded_steps: dedupeRecordedSteps(state.recorded_steps, payload),
      };
    }

    case EVENT_TYPES.permission_required: {
      return {
        ...state,
        interaction_mode: "executing",
        pending_permission: payload,
      };
    }

    case EVENT_TYPES.recommendation_ready: {
      const incoming = Array.isArray(payload.recommendations)
        ? payload.recommendations
        : [payload];
      return {
        ...state,
        pending_recommendations: incoming,
      };
    }

    case EVENT_TYPES.recovery_needed: {
      const options = Array.isArray(payload.options) ? payload.options : [];
      return {
        ...state,
        phase: "recovery",
        interaction_mode: "recovery",
        pending_recovery: { ...payload, options },
        last_error: payload.reason ?? payload.message ?? null,
      };
    }

    case EVENT_TYPES.recovery_resolved: {
      // S7-0506: only backend event clears recovery state
      const currentPhase = state.phase;
      const currentMode = state.interaction_mode;
      return {
        ...state,
        pending_recovery: null,
        phase: currentPhase === "recovery" ? "executing" : currentPhase,
        interaction_mode: currentMode === "recovery" ? "executing" : currentMode,
      };
    }

    case EVENT_TYPES.code_update: {
      return {
        ...state,
        code_preview: payload.code ?? payload.content ?? payload,
        // Clear any prior save result when a new code_update arrives
        code_save_result: null,
      };
    }

    case EVENT_TYPES.export_code_result: {
      const ok = payload && payload.ok === true;
      return {
        ...state,
        code_save_result: ok
          ? { ok: true, path: payload.path ?? null }
          : { ok: false, error: payload?.error ?? "unknown error" },
      };
    }

    default:
      return state;
  }
}
