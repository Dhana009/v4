// store/types.js — Frontend state type definitions (stub)
// Full implementation: S7-0501 (Typed frontend event model)

/**
 * @stub S7-0306
 * Declares the shape of frontend state. S7-0501 fills type definitions.
 * S7-0502 implements the reducer that uses these types.
 */
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
