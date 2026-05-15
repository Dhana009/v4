import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render } from "@testing-library/react";

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
    run_id: "run_thm_dflt_001",
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

describe("Live mode theme: default to light when no saved theme", () => {
  it("renders with no aw-theme in localStorage and applies light theme to documentElement", () => {
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("aw-theme absent: light is default, not dark", () => {
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).not.toBe("dark");
  });
});

describe("Live mode theme: reads saved aw-theme=dark from localStorage", () => {
  it("initializes dark when aw-theme=dark is stored", () => {
    localStorage.setItem("aw-theme", "dark");
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("Live mode theme: reads saved aw-theme=light from localStorage", () => {
  it("initializes light when aw-theme=light is stored", () => {
    localStorage.setItem("aw-theme", "light");
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("Demo mode: theme still works without viewModel", () => {
  it("demo mode renders and applies light theme by default", () => {
    render(<App />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("demo mode reads aw-theme=dark from localStorage", () => {
    localStorage.setItem("aw-theme", "dark");
    render(<App />);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
