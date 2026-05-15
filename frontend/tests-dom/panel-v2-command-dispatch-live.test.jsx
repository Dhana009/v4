import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, fireEvent } from "@testing-library/react";

import { PanelV2LiveHost } from "../src/panel-v2-adapter/live-host.jsx";

function makeTransport(overrides = {}) {
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
    pageUrl: "acme.dev",
    ...overrides,
  };
}

function makeStoreState(overrides = {}) {
  return {
    connected: true,
    run_id: "run_dispatch_001",
    phase: "idle",
    interaction_mode: "idle",
    pending_steps: [],
    recorded_steps: [],
    code_preview: null,
    trace_entries: [],
    agents: null,
    pending_permission: null,
    pending_recovery: null,
    pending_clarification: null,
    no_browser_state: null,
    api_key_required_state: null,
    human_input_required_state: null,
    e2e_pending_state: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("P0: command dispatch envelope — stop_run", () => {
  it("onSendCommand receives a command envelope object, not a raw action string", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing" })}
        onSendCommand={onSendCommand}
      />
    );
    const stopBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.includes("Stop run"));
    expect(stopBtn).not.toBeNull();
    fireEvent.click(stopBtn);
    expect(onSendCommand).toHaveBeenCalledTimes(1);
    const arg = onSendCommand.mock.calls[0][0];
    expect(typeof arg).toBe("object");
    expect(typeof arg).not.toBe("string");
  });

  it("stop_run envelope has version: autoworkbench.command.v1", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing" })}
        onSendCommand={onSendCommand}
      />
    );
    const stopBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.includes("Stop run"));
    fireEvent.click(stopBtn);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.version).toBe("autoworkbench.command.v1");
  });

  it("stop_run envelope has type: stop_run", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing" })}
        onSendCommand={onSendCommand}
      />
    );
    const stopBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.includes("Stop run"));
    fireEvent.click(stopBtn);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.type).toBe("stop_run");
  });

  it("stop_run envelope has run_id matching the store run_id", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing", run_id: "run_dispatch_001" })}
        onSendCommand={onSendCommand}
      />
    );
    const stopBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.includes("Stop run"));
    fireEvent.click(stopBtn);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.run_id).toBe("run_dispatch_001");
  });

  it("stop_run envelope has a command_id string", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing" })}
        onSendCommand={onSendCommand}
      />
    );
    const stopBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.includes("Stop run"));
    fireEvent.click(stopBtn);
    const arg = onSendCommand.mock.calls[0][0];
    expect(typeof arg.command_id).toBe("string");
    expect(arg.command_id.length).toBeGreaterThan(0);
  });
});

describe("P0: command dispatch envelope — correction", () => {
  it("correction envelope has version: autoworkbench.command.v1", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing" })}
        onSendCommand={onSendCommand}
      />
    );
    const sendBtn = container.querySelector(".aw-send");
    expect(sendBtn).not.toBeNull();
    fireEvent.click(sendBtn);
    expect(onSendCommand).toHaveBeenCalledTimes(1);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.version).toBe("autoworkbench.command.v1");
    expect(arg.type).toBe("correction");
  });
});

describe("P0: command dispatch envelope — confirm_plan", () => {
  it("confirm_plan envelope has version: autoworkbench.command.v1", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "idle", interactionMode: "idle" })}
        storeState={makeStoreState({ phase: "awaiting_confirmation", interaction_mode: "plan_review" })}
        onSendCommand={onSendCommand}
      />
    );
    const allButtons = Array.from(container.querySelectorAll("button"));
    const confirmBtn = allButtons.find((b) => b.textContent.includes("Confirm"));
    expect(confirmBtn).not.toBeNull();
    fireEvent.click(confirmBtn);
    expect(onSendCommand).toHaveBeenCalledTimes(1);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.version).toBe("autoworkbench.command.v1");
    expect(arg.type).toBe("confirm_plan");
  });
});

describe("P0: command dispatch envelope — permission_allow / permission_deny", () => {
  it("permission_allow maps to type: permission_decision with decision: allow", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing", pending_permission: { step_id: "stp_x" } })}
        onSendCommand={onSendCommand}
      />
    );
    const allButtons = Array.from(container.querySelectorAll("button"));
    const allowBtn = allButtons.find((b) => b.textContent.includes("Allow once"));
    expect(allowBtn).not.toBeNull();
    fireEvent.click(allowBtn);
    expect(onSendCommand).toHaveBeenCalledTimes(1);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.version).toBe("autoworkbench.command.v1");
    expect(arg.type).toBe("permission_decision");
    expect(arg.payload.decision).toBe("allow");
  });

  it("permission_deny maps to type: permission_decision with decision: deny", () => {
    const onSendCommand = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport({ runState: "executing", interactionMode: "executing" })}
        storeState={makeStoreState({ phase: "executing", pending_permission: { step_id: "stp_x" } })}
        onSendCommand={onSendCommand}
      />
    );
    const allButtons = Array.from(container.querySelectorAll("button"));
    const denyBtn = allButtons.find((b) => b.textContent.trim() === "Deny");
    expect(denyBtn).not.toBeNull();
    fireEvent.click(denyBtn);
    expect(onSendCommand).toHaveBeenCalledTimes(1);
    const arg = onSendCommand.mock.calls[0][0];
    expect(arg.version).toBe("autoworkbench.command.v1");
    expect(arg.type).toBe("permission_decision");
    expect(arg.payload.decision).toBe("deny");
  });
});

describe("P0: unsupported actions are not dispatched", () => {
  it("onSendCommand is not called if action is not in PANEL_V2_SUPPORTED_ACTIONS", async () => {
    const { buildPanelV2Command } = await import(
      "../src/panel-v2-adapter/command-bridge.js"
    );
    const onSendCommand = vi.fn();
    const result = buildPanelV2Command("select_locator_candidate", {}, "run_001");
    expect(result.supported).toBe(false);
    expect(onSendCommand).not.toHaveBeenCalled();
  });

  it("buildPanelV2Command returns supported:true for stop_run", async () => {
    const { buildPanelV2Command } = await import(
      "../src/panel-v2-adapter/command-bridge.js"
    );
    const result = buildPanelV2Command("stop_run", {}, "run_001");
    expect(result.supported).toBe(true);
    expect(result.command).not.toBeNull();
    expect(result.command.type).toBe("stop_run");
  });
});
