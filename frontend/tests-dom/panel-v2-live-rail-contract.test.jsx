import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, fireEvent } from "@testing-library/react";

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
    run_id: "run_rail_001",
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

describe("App live mode: onCollapseChange callback contract", () => {
  it("clicking Collapse icon calls onCollapseChange(true)", () => {
    const onCollapseChange = vi.fn();
    const { container } = render(
      <App viewModel={makeVm()} mode="live" onCollapseChange={onCollapseChange} />
    );
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    expect(collapseBtn).not.toBeNull();
    onCollapseChange.mockClear();
    fireEvent.click(collapseBtn);
    expect(onCollapseChange).toHaveBeenCalledWith(true);
  });

  it("clicking Expand from rail calls onCollapseChange(false)", () => {
    const onCollapseChange = vi.fn();
    const { container } = render(
      <App viewModel={makeVm()} mode="live" onCollapseChange={onCollapseChange} />
    );
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    fireEvent.click(collapseBtn);
    onCollapseChange.mockClear();
    const rail = container.querySelector(".aw-collapsed-rail");
    expect(rail).not.toBeNull();
    const expandBtn = rail.querySelector('button[title="Expand"]');
    expect(expandBtn).not.toBeNull();
    fireEvent.click(expandBtn);
    expect(onCollapseChange).toHaveBeenCalledWith(false);
  });

  it("demo mode (no onCollapseChange) does not throw on collapse click", () => {
    const { container } = render(<App />);
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    if (collapseBtn) fireEvent.click(collapseBtn);
  });
});

describe("PanelV2LiveHost: forwards onCollapseChange", () => {
  it("PanelV2LiveHost passes onCollapseChange to App", () => {
    const onCollapseChange = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport()}
        storeState={makeStoreState()}
        onCollapseChange={onCollapseChange}
      />
    );
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    expect(collapseBtn).not.toBeNull();
    onCollapseChange.mockClear();
    fireEvent.click(collapseBtn);
    expect(onCollapseChange).toHaveBeenCalledWith(true);
  });
});

describe("App live mode: rail still renders inside aw-panel when collapsed", () => {
  it("CollapsedRail visible when t.collapsed becomes true", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    fireEvent.click(collapseBtn);
    expect(container.querySelector(".aw-collapsed-rail")).not.toBeNull();
  });
});
