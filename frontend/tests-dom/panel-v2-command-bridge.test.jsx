import { describe, it, expect } from "vitest";

import {
  buildPanelV2Command,
  PANEL_V2_SUPPORTED_ACTIONS,
  PANEL_V2_DEFERRED_ACTIONS,
} from "../src/panel-v2-adapter/command-bridge.js";

const RUN = "run_abc123";
const PLAN = "plan_xyz";

describe("command-bridge: all supported actions produce valid envelopes", () => {
  PANEL_V2_SUPPORTED_ACTIONS.forEach((action) => {
    it(`${action} is supported`, () => {
      const payload = { run_id: RUN };
      // Add required payload fields per action
      if (action === "confirm_plan" || action === "confirmed") payload.plan_id = PLAN;
      if (action === "skip_step") payload.step_id = "stp_001";
      if (action === "permission_allow" || action === "permission_deny") payload.step_id = "stp_d8e2";

      const result = buildPanelV2Command(action, payload, RUN);
      expect(result.supported).toBe(true);
      expect(result.command).not.toBeNull();
      expect(typeof result.command.type).toBe("string");
      expect(result.command.run_id).toBe(RUN);
    });
  });
});

describe("command-bridge: all deferred actions are unsupported", () => {
  PANEL_V2_DEFERRED_ACTIONS.forEach((action) => {
    it(`${action} is deferred (supported=false)`, () => {
      const result = buildPanelV2Command(action, { run_id: RUN }, RUN);
      expect(result.supported).toBe(false);
      expect(result.command).toBeNull();
      expect(result.reason).toBeTruthy();
    });
  });
});

describe("command-bridge: command envelope integrity", () => {
  it("version field is autoworkbench.command.v1", () => {
    const { command } = buildPanelV2Command("stop_run", { run_id: RUN }, RUN);
    expect(command.version).toBe("autoworkbench.command.v1");
  });

  it("command_id is unique per call", () => {
    const r1 = buildPanelV2Command("stop_run", { run_id: RUN }, RUN);
    const r2 = buildPanelV2Command("stop_run", { run_id: RUN }, RUN);
    expect(r1.command.command_id).not.toBe(r2.command.command_id);
  });

  it("timestamp is a recent number", () => {
    const before = Date.now();
    const { command } = buildPanelV2Command("stop_run", { run_id: RUN }, RUN);
    const after = Date.now();
    expect(command.timestamp).toBeGreaterThanOrEqual(before);
    expect(command.timestamp).toBeLessThanOrEqual(after);
  });

  it("permission_allow sets payload.decision=allow", () => {
    const { command } = buildPanelV2Command("permission_allow", { run_id: RUN, step_id: "stp_x" }, RUN);
    expect(command.payload.decision).toBe("allow");
  });

  it("permission_deny sets payload.decision=deny", () => {
    const { command } = buildPanelV2Command("permission_deny", { run_id: RUN, step_id: "stp_x" }, RUN);
    expect(command.payload.decision).toBe("deny");
  });
});

describe("command-bridge: does not import demo-bridge", () => {
  it("command-bridge.js has no demo-bridge import", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/command-bridge.js"), "utf-8"
    );
    expect(src).not.toMatch(/demo-bridge/);
    expect(src).not.toMatch(/DEMO_/);
  });
});
