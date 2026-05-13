// store/reducer.js — Pure frontend state reducer
// S7-0502: Frontend reducer and event store

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
    trace_entries: [],
    errors: [],
    interaction_mode: "idle",
    last_error: null,
    session_metadata: null,
  };
}

export function reducer(state, event) {
  const { type, payload = {} } = event || {};

  switch (type) {
    case EVENT_TYPES.session_state: {
      return {
        ...state,
        connected: true,
        run_id: payload.run_id ?? state.run_id,
        phase: payload.phase ?? payload.state ?? state.phase,
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

    case EVENT_TYPES.step_validating: {
      return {
        ...state,
        phase: "executing",
        interaction_mode: "executing",
      };
    }

    case EVENT_TYPES.step_executing: {
      return {
        ...state,
        phase: "executing",
        interaction_mode: "executing",
      };
    }

    case EVENT_TYPES.step_failed: {
      return {
        ...state,
        errors: [...state.errors, payload],
        last_error: payload.reason ?? payload.message ?? null,
      };
    }

    case EVENT_TYPES.step_skipped: {
      const skipId = payload.step_id ?? payload.id;
      return {
        ...state,
        pending_steps: state.pending_steps.filter(
          (s) => (s.step_id ?? s.id) !== skipId
        ),
      };
    }

    case EVENT_TYPES.step_recorded: {
      return {
        ...state,
        recorded_steps: [...state.recorded_steps, payload],
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
      return {
        ...state,
        pending_recommendations: [...state.pending_recommendations, payload],
      };
    }

    case EVENT_TYPES.recovery_needed: {
      return {
        ...state,
        phase: "recovery",
        interaction_mode: "recovery",
        pending_recovery: payload,
        last_error: payload.reason ?? payload.message ?? null,
      };
    }

    case EVENT_TYPES.code_update: {
      return {
        ...state,
        code_preview: payload.code ?? payload.content ?? payload,
      };
    }

    default:
      return state;
  }
}
