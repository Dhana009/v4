import { buildCommand } from "../commands/command-builder.js";

export const PANEL_V2_SUPPORTED_ACTIONS = [
  "stop_run",
  "correction",
  "confirm_plan",
  "confirmed",
  "skip_step",
  "option_selected",
  "permission_allow",
  "permission_deny",
];

export const PANEL_V2_DEFERRED_ACTIONS = [
  "update_agent_settings",
  "select_locator_candidate",
  "apply_recovery",
  "revalidate_locator",
];

export function buildPanelV2Command(action, payload, runId) {
  if (PANEL_V2_DEFERRED_ACTIONS.includes(action)) {
    return { supported: false, command: null, reason: `${action} is deferred — not yet wired in panel-v2` };
  }

  if (!PANEL_V2_SUPPORTED_ACTIONS.includes(action)) {
    return { supported: false, command: null, reason: `${action} is not a known panel-v2 action` };
  }

  if (action === "permission_allow" || action === "permission_deny") {
    const decision = action === "permission_allow" ? "allow" : "deny";
    const cmd = buildCommand("permission_decision", { ...(payload ?? {}), decision }, runId);
    return { supported: true, command: cmd };
  }

  const cmd = buildCommand(action, payload ?? {}, runId);
  return { supported: true, command: cmd };
}
