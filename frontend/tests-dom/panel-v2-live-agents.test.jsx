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
    run_id: "run_agt_001",
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

function makeVm(overrides = {}) {
  return mapTransportToViewModel(makeTransport(), makeStoreState(overrides));
}

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

function openAgents(container) {
  const btn = container.querySelector(".aw-agents-btn");
  expect(btn).not.toBeNull();
  fireEvent.click(btn);
}

describe("AgentsPopover live mode: empty state when no agents payload", () => {
  it("renders empty-state element when viewModel.agents is null", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    openAgents(container);
    const empty = document.querySelector('[data-testid="aw-agents-empty"]');
    expect(empty).not.toBeNull();
  });

  it("does NOT render hardcoded demo agent 'Page Intelligence' in live empty mode", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    openAgents(container);
    const pop = document.querySelector(".aw-agents-pop");
    expect(pop).not.toBeNull();
    expect(pop.textContent).not.toMatch(/Page Intelligence/);
  });

  it("does NOT render hardcoded demo agent 'Main Orchestrator' in live empty mode", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    openAgents(container);
    const pop = document.querySelector(".aw-agents-pop");
    expect(pop.textContent).not.toMatch(/Main Orchestrator/);
  });

  it("does NOT render hardcoded demo agent 'Step Runner' in live empty mode", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    openAgents(container);
    const pop = document.querySelector(".aw-agents-pop");
    expect(pop.textContent).not.toMatch(/Step Runner/);
  });
});

describe("AgentsPopover live mode: renders real backend agents", () => {
  it("renders agent row for each backend agent", () => {
    const agents = [
      { key: "agt_orch", name: "Orchestrator", initials: "OR", model: "claude", status: "running", last: "running step 3", required: true },
      { key: "agt_dbg", name: "Debug Agent", initials: "DA", model: "claude", status: "standby", last: "idle", required: false },
    ];
    const { container } = render(
      <App viewModel={makeVm({ agents })} mode="live" />
    );
    openAgents(container);
    expect(document.querySelector('[data-testid="aw-agent-row-agt_orch"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="aw-agent-row-agt_dbg"]')).not.toBeNull();
  });

  it("does NOT render empty-state when agents present", () => {
    const agents = [{ key: "agt_orch", name: "Orchestrator", initials: "OR", model: "claude", status: "running", last: "x", required: true }];
    const { container } = render(
      <App viewModel={makeVm({ agents })} mode="live" />
    );
    openAgents(container);
    expect(document.querySelector('[data-testid="aw-agents-empty"]')).toBeNull();
  });

  it("non-required agent toggle is disabled in read-only mode (no silent fake commands)", () => {
    const agents = [{ key: "agt_dbg", name: "Debug Agent", initials: "DA", model: "x", status: "standby", last: "idle", required: false }];
    const { container } = render(
      <App viewModel={makeVm({ agents })} mode="live" />
    );
    openAgents(container);
    const toggle = document.querySelector('[data-testid="aw-agent-toggle-agt_dbg"]');
    expect(toggle).not.toBeNull();
    expect(toggle.disabled).toBe(true);
  });
});

describe("AgentsPopover demo mode: unchanged demo behavior", () => {
  it("demo mode still shows demo agent 'Main Orchestrator'", () => {
    const { container } = render(<App />);
    openAgents(container);
    const pop = document.querySelector(".aw-agents-pop");
    expect(pop).not.toBeNull();
    expect(pop.textContent).toMatch(/Main Orchestrator/);
  });
});
