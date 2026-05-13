// commands/validation.js — Frontend command validation
// S7-0508: Stale/missing id and disabled command blocking

export function isValidCommandType(commandType) {
  return typeof commandType === "string" && commandType.trim().length > 0;
}

export function validateCommand(command, state) {
  if (!command || !command.type) {
    return { valid: false, reason: "command missing type" };
  }

  if (!command.run_id) {
    return { valid: false, reason: "command missing run_id" };
  }

  if (state && state.run_id && command.run_id !== state.run_id) {
    return { valid: false, reason: "stale run_id: command run_id does not match current_run_id" };
  }

  if (command.type === "confirm_plan" || command.type === "confirmed") {
    const plan_id = command.plan_id ?? command.payload?.plan_id;
    if (!plan_id) {
      return { valid: false, reason: "confirm_plan requires plan_id" };
    }
  }

  if (command.type === "skip_step") {
    const step_id = command.step_id ?? command.payload?.step_id;
    if (!step_id) {
      return { valid: false, reason: "skip_step requires step_id" };
    }
  }

  return { valid: true, reason: null };
}

export function canDispatch(commandType, payload, state) {
  if (!isValidCommandType(commandType)) {
    return { allowed: false, disabledReason: "invalid command type" };
  }

  const run_id = payload?.run_id ?? null;

  if (!run_id) {
    return { allowed: false, disabledReason: "missing run_id" };
  }

  if (state && state.run_id && run_id !== state.run_id) {
    return { allowed: false, disabledReason: "stale run_id: current_run_id mismatch" };
  }

  if (commandType === "confirm_plan" || commandType === "confirmed") {
    if (!payload?.plan_id) {
      return { allowed: false, disabledReason: "confirm_plan requires plan_id" };
    }
  }

  if (commandType === "skip_step") {
    if (!payload?.step_id) {
      return { allowed: false, disabledReason: "skip_step requires step_id" };
    }
  }

  return { allowed: true, disabledReason: null };
}
