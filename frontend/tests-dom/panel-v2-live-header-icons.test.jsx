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
    run_id: "run_hdr_icons_001",
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

function makeVm() {
  return mapTransportToViewModel(makeTransport(), makeStoreState());
}

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("Settings gear not hidden by data-wide in live mode", () => {
  it("data-wide=1 on live panel and settings gear still present", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const panel = container.querySelector(".aw-panel");
    expect(panel.getAttribute("data-wide")).toBe("1");
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });
});

describe("Collapsed rail: full header controls hidden", () => {
  it("settings gear not visible in collapsed rail", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    expect(collapseBtn).not.toBeNull();
    fireEvent.click(collapseBtn);
    const rail = container.querySelector(".aw-collapsed-rail");
    expect(rail).not.toBeNull();
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).toBeNull();
  });

  it("header element itself not visible in collapsed state", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    fireEvent.click(collapseBtn);
    const header = container.querySelector(".aw-header");
    expect(header).toBeNull();
  });
});

describe("Expand from rail: restores full header with settings gear", () => {
  it("expanding restores settings gear visibility", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    fireEvent.click(collapseBtn);
    expect(container.querySelector('button[title="Settings & Tweaks"]')).toBeNull();
    const expandBtn = container.querySelector('.aw-collapsed-rail button[title="Expand"]');
    expect(expandBtn).not.toBeNull();
    fireEvent.click(expandBtn);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });

  it("expanding restores aw-header element", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const collapseBtn = container.querySelector('button[title="Collapse"]');
    fireEvent.click(collapseBtn);
    const expandBtn = container.querySelector('.aw-collapsed-rail button[title="Expand"]');
    fireEvent.click(expandBtn);
    expect(container.querySelector(".aw-header")).not.toBeNull();
  });
});

describe("Preview/demo mode: still works after gear click", () => {
  it("demo mode App renders correctly without viewModel", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".aw-panel")).not.toBeNull();
    expect(container.querySelector(".aw-header")).not.toBeNull();
  });

  it("demo mode settings gear present", () => {
    const { container } = render(<App />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });
});

describe("Old v4 fallback: demo mode still renders", () => {
  it("no viewModel = demo mode, no error", () => {
    expect(() => render(<App />)).not.toThrow();
  });
});
