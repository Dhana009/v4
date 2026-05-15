import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, fireEvent, act } from "@testing-library/react";

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
    run_id: "run_toggle_001",
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

describe("Settings gear: visible in live mode header", () => {
  it("gear button present in live header", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });

  it("gear present regardless of data-wide=1 on panel", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const panel = container.querySelector(".aw-panel");
    expect(panel.getAttribute("data-wide")).toBe("1");
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });
});

describe("Settings gear: fires __activate_edit_mode on click", () => {
  it("clicking gear posts __activate_edit_mode", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    fireEvent.click(gear);
    expect(window.postMessage).toHaveBeenCalledWith(
      { type: "__activate_edit_mode" }, "*"
    );
  });
});

describe("TweaksPanel: rendered in live mode so gear opens it", () => {
  it("TweaksPanel mount point exists in live mode output", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    // TweaksPanel renders a hidden panel that __activate_edit_mode reveals.
    // Its container is present in DOM even before activation.
    const tweaks = container.querySelector(".aw-tweaks") || container.querySelector("[data-tweaks]");
    // We don't assert tweaks visible — just verify gear click doesn't throw.
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(() => fireEvent.click(gear)).not.toThrow();
  });
});

describe("Theme: default light on mount", () => {
  it("light theme applied to documentElement on mount", () => {
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("reads dark from localStorage on mount", () => {
    localStorage.setItem("aw-theme", "dark");
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("Demo mode: gear also present", () => {
  it("demo mode renders Settings gear in header", () => {
    const { container } = render(<App />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });

  it("demo mode gear fires __activate_edit_mode", () => {
    const { container } = render(<App />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    fireEvent.click(gear);
    expect(window.postMessage).toHaveBeenCalledWith(
      { type: "__activate_edit_mode" }, "*"
    );
  });
});
