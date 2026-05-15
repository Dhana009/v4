import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render } from "@testing-library/react";

import { App } from "../src/panel-v2/app.jsx";
import { PanelV2LiveHost } from "../src/panel-v2-adapter/live-host.jsx";
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

function makeVm(phase = "idle") {
  return mapTransportToViewModel(
    makeTransport(phase === "exec" ? { runState: "executing", interactionMode: "executing" } : {}),
    {
      connected: true, run_id: "run_test",
      phase: phase === "exec" ? "executing" : "idle",
      interaction_mode: "idle",
      pending_steps: [], recorded_steps: [], code_preview: null, trace_entries: [],
      agents: null, pending_permission: null, pending_recovery: null, pending_clarification: null,
      no_browser_state: null, api_key_required_state: null, human_input_required_state: null,
      e2e_pending_state: null,
    }
  );
}

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("live idle: demo locator content does NOT leak", () => {
  it("live idle does not show locator disambiguation card text", () => {
    // DEMO_TWEAK_DEFAULTS.state = 'locator', which shows candidate picker
    // In live idle mode, this must NOT appear
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.textContent).not.toMatch(/Three visible/i);
    expect(container.textContent).not.toMatch(/pick a candidate/i);
  });

  it("live idle does not show Stop run button (exec state card)", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    const buttons = Array.from(container.querySelectorAll("button"));
    const stopBtn = buttons.find(b => b.textContent.includes("Stop run"));
    expect(stopBtn).toBeUndefined();
  });

  it("live idle does not show Confirm & run button (plan card)", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    const buttons = Array.from(container.querySelectorAll("button"));
    const confirmBtn = buttons.find(b => b.textContent.includes("Confirm"));
    expect(confirmBtn).toBeUndefined();
  });

  it("live idle does not show Allow once button (permission card)", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    const buttons = Array.from(container.querySelectorAll("button"));
    const allowBtn = buttons.find(b => b.textContent.includes("Allow once"));
    expect(allowBtn).toBeUndefined();
  });
});

describe("live idle: LLM thread shows idle state, not demo state", () => {
  it("live idle renders .aw-panel-body (thread container exists)", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelector(".aw-panel-body")).not.toBeNull();
  });

  it("live idle does not render CardExecution card", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    // CardExecution renders .aw-card.exec
    expect(container.querySelector(".aw-card.exec")).toBeNull();
  });

  it("live idle does not render CardPermission card", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    // CardPermission renders .aw-card.perm
    expect(container.querySelector(".aw-card.perm")).toBeNull();
  });

  it("live exec state DOES render CardExecution card", () => {
    const vm = makeVm("exec");
    const { container } = render(<App viewModel={vm} mode="live" />);
    // In exec state, CardExecution should be visible
    const stopBtns = Array.from(container.querySelectorAll("button")).filter(b => b.textContent.includes("Stop run"));
    expect(stopBtns.length).toBeGreaterThan(0);
  });
});

describe("PanelV2LiveHost: no demo data with empty transport", () => {
  it("PanelV2LiveHost idle transport does not show CardExecution", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-card.exec")).toBeNull();
  });

  it("PanelV2LiveHost idle transport does not show CardPermission", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-card.perm")).toBeNull();
  });

  it("PanelV2LiveHost renders .aw-panel", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-panel")).not.toBeNull();
  });
});
