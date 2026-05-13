// commands/dispatcher.js — Frontend command dispatcher
// S7-0507: Typed command dispatcher

import { buildCommand } from "./command-builder.js";
import { validateCommand } from "./validation.js";

export function createDispatcher(getState, transport) {
  return {
    dispatch(commandType, payload) {
      return dispatch(commandType, payload, getState, transport);
    },
  };
}

export function dispatch(commandType, payload, getState, transport) {
  if (!transport || typeof transport.send !== "function") {
    return { sent: false, reason: "transport unavailable" };
  }

  const state = typeof getState === "function" ? getState() : null;
  const run_id = payload?.run_id ?? (state ? state.run_id : null);

  const command = buildCommand(commandType, payload, run_id);

  const validation = validateCommand(command, state);
  if (!validation.valid) {
    return { sent: false, reason: validation.reason };
  }

  transport.send(command);
  return { sent: true, reason: null };
}
