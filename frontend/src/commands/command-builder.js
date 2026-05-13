// commands/command-builder.js — Frontend command envelope builder (stub)
// Full implementation: S7-0507 (Typed command dispatcher)

/**
 * @stub S7-0306
 * Schema version constant used by command builders.
 */
export const FRONTEND_COMMAND_SCHEMA_VERSION = "autoworkbench.command.v1";

export function createCommandId() {
  const crypto = globalThis?.crypto;
  if (crypto && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `cmd-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
