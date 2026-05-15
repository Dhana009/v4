import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, fireEvent } from "@testing-library/react";

import { App } from "../src/panel-v2/app.jsx";
import { mapTransportToViewModel } from "../src/panel-v2-adapter/state-bridge.js";

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
    run_id: "run_cmd_001",
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

function makeVm(phase) {
  const phaseToTransport = {
    idle:   { runState: "idle",      interactionMode: "idle" },
    exec:   { runState: "executing", interactionMode: "executing" },
    plan:   { runState: "idle",      interactionMode: "idle" },
    permit: { runState: "executing", interactionMode: "executing" },
  };
  const phaseToStore = {
    idle:   { phase: "idle" },
    exec:   { phase: "executing" },
    plan:   { phase: "awaiting_confirmation", interaction_mode: "plan_review" },
    permit: { phase: "executing", pending_permission: { step_id: "stp_x" } },
  };
  return mapTransportToViewModel(
    makeTransport(phaseToTransport[phase] ?? {}),
    makeStoreState({ ...phaseToStore[phase] ?? {}, run_id: "run_cmd_001" })
  );
}

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("S4 App accepts onCommand prop", () => {
  it("App renders without crashing when onCommand is provided", () => {
    const onCommand = vi.fn();
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("onCommand is not called on initial render", () => {
    const onCommand = vi.fn();
    const vm = makeVm("idle");
    render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    expect(onCommand).not.toHaveBeenCalled();
  });
});

describe("S4 Composer Send fires correction command", () => {
  it("clicking Send calls onCommand with action='correction'", () => {
    const onCommand = vi.fn();
    const vm = makeVm("exec");
    const { container } = render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    const sendBtn = container.querySelector(".aw-send");
    expect(sendBtn).not.toBeNull();
    fireEvent.click(sendBtn);
    expect(onCommand).toHaveBeenCalledWith(
      "correction",
      expect.objectContaining({ run_id: "run_cmd_001" })
    );
  });

  it("Composer Send does NOT call onCommand in demo mode (no onCommand)", () => {
    const { container } = render(<App />);
    const sendBtn = container.querySelector(".aw-send");
    if (!sendBtn) return; // demo may not show composer at idle
    // Just confirm it doesn't throw — no mock to verify
    fireEvent.click(sendBtn);
  });
});

describe("S4 CardPlanReady Confirm fires confirm_plan", () => {
  it("'Confirm & run' button calls onCommand with action='confirm_plan'", () => {
    const onCommand = vi.fn();
    const vm = makeVm("plan");
    const { container } = render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    // Find the confirm button inside a plan card
    const allButtons = Array.from(container.querySelectorAll("button"));
    const confirmBtn = allButtons.find(b => b.textContent.includes("Confirm"));
    expect(confirmBtn).not.toBeNull();
    fireEvent.click(confirmBtn);
    expect(onCommand).toHaveBeenCalledWith(
      "confirm_plan",
      expect.objectContaining({ run_id: "run_cmd_001" })
    );
  });
});

describe("S4 CardPermission fires permission commands", () => {
  it("'Allow once' button calls onCommand with action='permission_allow'", () => {
    const onCommand = vi.fn();
    const vm = makeVm("permit");
    const { container } = render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    const allButtons = Array.from(container.querySelectorAll("button"));
    const allowBtn = allButtons.find(b => b.textContent.includes("Allow once"));
    expect(allowBtn).not.toBeNull();
    fireEvent.click(allowBtn);
    expect(onCommand).toHaveBeenCalledWith(
      "permission_allow",
      expect.objectContaining({ run_id: "run_cmd_001" })
    );
  });

  it("'Deny' button calls onCommand with action='permission_deny'", () => {
    const onCommand = vi.fn();
    const vm = makeVm("permit");
    const { container } = render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    const allButtons = Array.from(container.querySelectorAll("button"));
    const denyBtn = allButtons.find(b => b.textContent.trim() === "Deny");
    expect(denyBtn).not.toBeNull();
    fireEvent.click(denyBtn);
    expect(onCommand).toHaveBeenCalledWith(
      "permission_deny",
      expect.objectContaining({ run_id: "run_cmd_001" })
    );
  });
});

describe("S4 CardExecution Stop fires stop_run", () => {
  it("'Stop run' button calls onCommand with action='stop_run'", () => {
    const onCommand = vi.fn();
    const vm = makeVm("exec");
    const { container } = render(<App viewModel={vm} mode="live" onCommand={onCommand} />);
    const allButtons = Array.from(container.querySelectorAll("button"));
    const stopBtn = allButtons.find(b => b.textContent.includes("Stop run"));
    expect(stopBtn).not.toBeNull();
    fireEvent.click(stopBtn);
    expect(onCommand).toHaveBeenCalledWith(
      "stop_run",
      expect.objectContaining({ run_id: "run_cmd_001" })
    );
  });
});
