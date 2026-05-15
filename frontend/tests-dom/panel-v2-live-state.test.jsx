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

function makeStoreState(overrides = {}) {
  return {
    connected: true,
    run_id: "run_live_001",
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

describe("S1 App props interface", () => {
  it("App renders with live viewModel", () => {
    const vm = mapTransportToViewModel(makeTransport(), null);
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("App without viewModel renders demo preview (default demo mode)", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("App in live mode does not render demo idle text 'Tell me what to automate'", () => {
    const vm = mapTransportToViewModel(makeTransport({ runState: "idle" }), null);
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.textContent).not.toMatch(/Tell me what to automate/);
  });

  it("App in live mode renders .aw-stage", () => {
    const vm = mapTransportToViewModel(makeTransport(), null);
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("App in live mode has 5 tabs", () => {
    const vm = mapTransportToViewModel(makeTransport(), null);
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelectorAll(".aw-tab").length).toBe(5);
  });
});

describe("S3 state-bridge reads storeState", () => {
  it("reads agents from storeState", () => {
    const agents = [{ id: "a1", name: "Main Orchestrator" }];
    const vm = mapTransportToViewModel(makeTransport(), makeStoreState({ agents }));
    expect(vm.agents).toEqual(agents);
  });

  it("agents null when storeState.agents is null", () => {
    const vm = mapTransportToViewModel(makeTransport(), makeStoreState({ agents: null }));
    expect(vm.agents).toBeNull();
  });

  it("pending_permission in storeState → phase='permit'", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ runState: "executing", interactionMode: "executing" }),
      makeStoreState({ pending_permission: { step_id: "stp_x" }, phase: "executing" })
    );
    expect(vm.runtime.phase).toBe("permit");
  });

  it("pending_recovery in storeState → phase='recover'", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ runState: "recovery" }),
      makeStoreState({ pending_recovery: { reason: "assertion failed" }, phase: "recovery" })
    );
    expect(vm.runtime.phase).toBe("recover");
  });

  it("no_browser_state in storeState → phase='nobrowser'", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ runState: "idle" }),
      makeStoreState({ no_browser_state: { reason: "no context" } })
    );
    expect(vm.runtime.phase).toBe("nobrowser");
  });

  it("api_key_required_state in storeState → phase='apikey'", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ runState: "idle" }),
      makeStoreState({ api_key_required_state: { provider: "anthropic" } })
    );
    expect(vm.runtime.phase).toBe("apikey");
  });

  it("pending_steps from storeState preferred over transport.pendingSteps", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ pendingSteps: [{ id: "t1" }] }),
      makeStoreState({ pending_steps: [{ id: "s1" }, { id: "s2" }] })
    );
    expect(vm.counts.steps).toBe(2);
  });

  it("run_id from storeState used when available", () => {
    const vm = mapTransportToViewModel(makeTransport(), makeStoreState({ run_id: "run_live_999" }));
    expect(vm.runtime.runId).toBe("run_live_999");
  });

  it("storeState phase=awaiting_confirmation + interaction_mode=clarification → phase='clarify'", () => {
    const vm = mapTransportToViewModel(
      makeTransport(),
      makeStoreState({ phase: "awaiting_confirmation", interaction_mode: "clarification" })
    );
    expect(vm.runtime.phase).toBe("clarify");
  });

  it("storeState phase=awaiting_confirmation + interaction_mode=plan_review → phase='plan'", () => {
    const vm = mapTransportToViewModel(
      makeTransport(),
      makeStoreState({ phase: "awaiting_confirmation", interaction_mode: "plan_review" })
    );
    expect(vm.runtime.phase).toBe("plan");
  });

  it("storeState phase=executing → phase='exec'", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ runState: "executing" }),
      makeStoreState({ phase: "executing" })
    );
    expect(vm.runtime.phase).toBe("exec");
  });

  it("storeState phase=completed → phase='done'", () => {
    const vm = mapTransportToViewModel(
      makeTransport({ runState: "completed" }),
      makeStoreState({ phase: "completed" })
    );
    expect(vm.runtime.phase).toBe("done");
  });
});

describe("S2 PanelV2LiveHost passes VM into App", () => {
  it("renders App with live mode", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("renders 5 tabs in live mode", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelectorAll(".aw-tab").length).toBe(5);
  });

  it("does not render demo idle text with idle transport", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport({ runState: "idle" })} />);
    expect(container.textContent).not.toMatch(/Tell me what to automate/);
  });

  it("live-host.jsx does not import DEMO_STATE_META, DEMO_TWEAK_DEFAULTS, or demo-bridge", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"), "utf-8"
    );
    expect(src).not.toMatch(/DEMO_STATE_META/);
    expect(src).not.toMatch(/DEMO_TWEAK_DEFAULTS/);
    expect(src).not.toMatch(/demo-bridge/);
  });
});
