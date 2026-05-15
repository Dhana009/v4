import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

// These imports will fail (RED) until adapter files are created
import { mapTransportToViewModel } from "../src/panel-v2-adapter/state-bridge.js";
import { buildPanelV2Command, PANEL_V2_DEFERRED_ACTIONS } from "../src/panel-v2-adapter/command-bridge.js";
import { getDemoViewModel, DEMO_TWEAK_DEFAULTS, DEMO_STATE_META } from "../src/panel-v2-adapter/demo-bridge.js";
import { PANEL_V2_VIEW_MODEL_VERSION } from "../src/panel-v2-adapter/types.js";

const ADAPTER_DIR = join(import.meta.dirname, "../src/panel-v2-adapter");

// Minimal mock transport shape (what useAutoWorkbenchTransport returns)
function makeMockTransport(overrides = {}) {
  return {
    connectionStatus: "connected",
    runState: "idle",
    interactionMode: "idle",
    conversation: [],
    pendingSteps: [],
    recordedSteps: [],
    codePreview: null,
    traceEntries: [],
    tokenInfo: null,
    pageUrl: "acme.dev/pricing",
    ...overrides,
  };
}

describe("004A state-bridge: module shape", () => {
  it("state-bridge exports mapTransportToViewModel", () => {
    expect(typeof mapTransportToViewModel).toBe("function");
  });

  it("view model has required top-level keys", () => {
    const vm = mapTransportToViewModel(makeMockTransport(), null);
    expect(vm).toHaveProperty("mode");
    expect(vm).toHaveProperty("runtime");
    expect(vm).toHaveProperty("counts");
    expect(vm).toHaveProperty("llm");
    expect(vm).toHaveProperty("steps");
    expect(vm).toHaveProperty("recorded");
    expect(vm).toHaveProperty("code");
    expect(vm).toHaveProperty("trace");
  });

  it("view model mode is 'live'", () => {
    const vm = mapTransportToViewModel(makeMockTransport(), null);
    expect(vm.mode).toBe("live");
  });
});

describe("004A state-bridge: connection mapping", () => {
  it("connected transport → connection 'connected'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ connectionStatus: "connected" }), null);
    expect(vm.runtime.connection).toBe("connected");
  });

  it("offline transport → connection 'offline'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ connectionStatus: "offline" }), null);
    expect(vm.runtime.connection).toBe("offline");
  });

  it("busy transport (executing) → connection 'busy'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ connectionStatus: "connected", runState: "executing" }), null);
    expect(vm.runtime.connection).toBe("busy");
  });
});

describe("004A state-bridge: phase/state mapping", () => {
  it("idle → phase 'idle'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ runState: "idle", interactionMode: "idle" }), null);
    expect(vm.runtime.phase).toBe("idle");
  });

  it("planning → phase 'planning'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ runState: "planning", interactionMode: "planning" }), null);
    expect(vm.runtime.phase).toBe("planning");
  });

  it("awaiting_confirmation + plan_review → phase 'plan'", () => {
    const vm = mapTransportToViewModel(
      makeMockTransport({ runState: "awaiting_confirmation", interactionMode: "plan_review" }), null
    );
    expect(vm.runtime.phase).toBe("plan");
  });

  it("awaiting_confirmation + clarification → phase 'clarify'", () => {
    const vm = mapTransportToViewModel(
      makeMockTransport({ runState: "awaiting_confirmation", interactionMode: "clarification" }), null
    );
    expect(vm.runtime.phase).toBe("clarify");
  });

  it("executing → phase 'exec'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ runState: "executing", interactionMode: "executing" }), null);
    expect(vm.runtime.phase).toBe("exec");
  });

  it("recovery → phase 'recover'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ runState: "recovery", interactionMode: "recovery" }), null);
    expect(vm.runtime.phase).toBe("recover");
  });

  it("completed → phase 'done'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ runState: "completed", interactionMode: "completed" }), null);
    expect(vm.runtime.phase).toBe("done");
  });

  it("offline connectionStatus → phase 'offline'", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ connectionStatus: "offline" }), null);
    expect(vm.runtime.phase).toBe("offline");
  });
});

describe("004A state-bridge: counts derivation", () => {
  it("derives step counts from transport arrays", () => {
    const vm = mapTransportToViewModel(
      makeMockTransport({
        pendingSteps: [{ id: "s1" }, { id: "s2" }],
        recordedSteps: [{ id: "r1" }],
        codePreview: "const x = 1;",
        traceEntries: [1, 2, 3],
      }),
      null
    );
    expect(vm.counts.steps).toBe(2);
    expect(vm.counts.rec).toBe(1);
    expect(vm.counts.code).toBe(1);
    expect(vm.counts.trace).toBe(3);
  });

  it("empty arrays give zero counts", () => {
    const vm = mapTransportToViewModel(makeMockTransport(), null);
    expect(vm.counts.steps).toBe(0);
    expect(vm.counts.rec).toBe(0);
    expect(vm.counts.code).toBe(0);
    expect(vm.counts.trace).toBe(0);
  });
});

describe("004A state-bridge: no demo fixtures", () => {
  it("state-bridge.js does not import demo-bridge", () => {
    const src = readFileSync(join(ADAPTER_DIR, "state-bridge.js"), "utf-8");
    expect(src).not.toMatch(/demo-bridge/);
    expect(src).not.toMatch(/DEMO_FIXTURES/);
    expect(src).not.toMatch(/demo-fixtures/);
  });

  it("live view model does not contain demo-only STATE_META text", () => {
    const vm = mapTransportToViewModel(makeMockTransport({ runState: "idle" }), null);
    // Demo STATE_META has specific text like "Tell me what to automate"
    expect(JSON.stringify(vm)).not.toMatch(/Tell me what to automate/);
  });
});

describe("004A command-bridge: supported commands", () => {
  const RUN_ID = "run_test_001";
  const PLAN_ID = "plan_abc";

  it("stop_run returns supported command envelope", () => {
    const result = buildPanelV2Command("stop_run", { run_id: RUN_ID }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command).not.toBeNull();
    expect(result.command.type).toBe("stop_run");
    expect(result.command.run_id).toBe(RUN_ID);
  });

  it("correction returns supported command envelope", () => {
    const result = buildPanelV2Command("correction", { run_id: RUN_ID, text: "try again" }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command.type).toBe("correction");
  });

  it("confirm_plan returns supported command envelope", () => {
    const result = buildPanelV2Command("confirm_plan", { run_id: RUN_ID, plan_id: PLAN_ID }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command.type).toBe("confirm_plan");
  });

  it("skip_step returns supported command envelope", () => {
    const result = buildPanelV2Command("skip_step", { run_id: RUN_ID, step_id: "stp_001" }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command.type).toBe("skip_step");
  });

  it("option_selected returns supported command envelope", () => {
    const result = buildPanelV2Command("option_selected", { run_id: RUN_ID, option: "a" }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command.type).toBe("option_selected");
  });

  it("permission_allow returns supported permission_decision command", () => {
    const result = buildPanelV2Command("permission_allow", { run_id: RUN_ID, step_id: "stp_d8e2" }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command.type).toBe("permission_decision");
    expect(result.command.payload.decision).toBe("allow");
  });

  it("permission_deny returns supported permission_decision command", () => {
    const result = buildPanelV2Command("permission_deny", { run_id: RUN_ID, step_id: "stp_d8e2" }, RUN_ID);
    expect(result.supported).toBe(true);
    expect(result.command.type).toBe("permission_decision");
    expect(result.command.payload.decision).toBe("deny");
  });
});

describe("004A command-bridge: deferred/unsupported commands", () => {
  const RUN_ID = "run_test_001";

  it("update_agent_settings is deferred", () => {
    const result = buildPanelV2Command("update_agent_settings", { run_id: RUN_ID }, RUN_ID);
    expect(result.supported).toBe(false);
    expect(result.command).toBeNull();
    expect(result.reason).toBeTruthy();
  });

  it("select_locator_candidate is deferred", () => {
    const result = buildPanelV2Command("select_locator_candidate", { run_id: RUN_ID }, RUN_ID);
    expect(result.supported).toBe(false);
  });

  it("apply_recovery is deferred", () => {
    const result = buildPanelV2Command("apply_recovery", { run_id: RUN_ID }, RUN_ID);
    expect(result.supported).toBe(false);
  });

  it("revalidate_locator is deferred", () => {
    const result = buildPanelV2Command("revalidate_locator", { run_id: RUN_ID }, RUN_ID);
    expect(result.supported).toBe(false);
  });

  it("PANEL_V2_DEFERRED_ACTIONS lists all deferred actions", () => {
    expect(PANEL_V2_DEFERRED_ACTIONS).toContain("update_agent_settings");
    expect(PANEL_V2_DEFERRED_ACTIONS).toContain("select_locator_candidate");
    expect(PANEL_V2_DEFERRED_ACTIONS).toContain("apply_recovery");
    expect(PANEL_V2_DEFERRED_ACTIONS).toContain("revalidate_locator");
  });

  it("unknown action is unsupported", () => {
    const result = buildPanelV2Command("nonexistent_action", { run_id: RUN_ID }, RUN_ID);
    expect(result.supported).toBe(false);
  });
});

describe("004A command-bridge: command envelope structure", () => {
  it("supported command has version, command_id, type, run_id, payload, timestamp", () => {
    const result = buildPanelV2Command("stop_run", { run_id: "run_x" }, "run_x");
    const { command } = result;
    expect(command).toHaveProperty("version");
    expect(command).toHaveProperty("command_id");
    expect(command).toHaveProperty("type");
    expect(command).toHaveProperty("run_id");
    expect(command).toHaveProperty("payload");
    expect(command).toHaveProperty("timestamp");
  });
});

describe("004A demo-bridge: module shape", () => {
  it("getDemoViewModel returns view model with mode=demo", () => {
    const vm = getDemoViewModel();
    expect(vm.mode).toBe("demo");
  });

  it("demo view model has same top-level keys as live", () => {
    const demo = getDemoViewModel();
    expect(demo).toHaveProperty("runtime");
    expect(demo).toHaveProperty("counts");
    expect(demo).toHaveProperty("llm");
    expect(demo).toHaveProperty("steps");
    expect(demo).toHaveProperty("recorded");
  });

  it("DEMO_TWEAK_DEFAULTS is exported and has required keys", () => {
    expect(DEMO_TWEAK_DEFAULTS).toHaveProperty("tab");
    expect(DEMO_TWEAK_DEFAULTS).toHaveProperty("state");
    expect(DEMO_TWEAK_DEFAULTS).toHaveProperty("dock");
    expect(DEMO_TWEAK_DEFAULTS).toHaveProperty("theme");
  });

  it("DEMO_STATE_META covers all lifecycle states", () => {
    const requiredStates = ["idle", "planning", "plan", "exec", "recover", "done", "offline"];
    requiredStates.forEach((s) => {
      expect(DEMO_STATE_META).toHaveProperty(s);
    });
  });

  it("demo-bridge does not import state-bridge", () => {
    const src = readFileSync(join(ADAPTER_DIR, "demo-bridge.js"), "utf-8");
    expect(src).not.toMatch(/state-bridge/);
  });
});

describe("004A types: exports", () => {
  it("PANEL_V2_VIEW_MODEL_VERSION is a string", () => {
    expect(typeof PANEL_V2_VIEW_MODEL_VERSION).toBe("string");
    expect(PANEL_V2_VIEW_MODEL_VERSION.length).toBeGreaterThan(0);
  });
});
