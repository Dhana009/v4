// commands/command-builder.js — Frontend command envelope builder
// S7-0507: Typed command dispatcher

import { COMMAND_TYPES } from "../store/types.js";

export { COMMAND_TYPES };

export const FRONTEND_COMMAND_SCHEMA_VERSION = "autoworkbench.command.v1";

export function createCommandId() {
  const crypto = globalThis?.crypto;
  if (crypto && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `cmd-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function buildCommand(type, payload, runId) {
  return {
    version: FRONTEND_COMMAND_SCHEMA_VERSION,
    command_id: createCommandId(),
    type,
    run_id: runId ?? payload?.run_id ?? null,
    payload: payload ?? {},
    timestamp: Date.now(),
  };
}
