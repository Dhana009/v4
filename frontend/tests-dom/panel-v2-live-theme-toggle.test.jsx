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

function findThemeToggle(container) {
  return container.querySelector('[data-testid="aw-theme-toggle"]');
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

describe("Theme toggle button: visible in expanded live panel", () => {
  it("theme toggle button is present in the live header", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const toggle = findThemeToggle(container);
    expect(toggle).not.toBeNull();
  });

  it("theme toggle button is visible (not hidden by data-wide=1)", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const panel = container.querySelector(".aw-panel");
    expect(panel.getAttribute("data-wide")).toBe("1");
    const toggle = findThemeToggle(container);
    expect(toggle).not.toBeNull();
  });
});

describe("Theme toggle: changes state light -> dark", () => {
  it("clicking toggle switches from light to dark", () => {
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("light");
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const toggle = findThemeToggle(container);
    fireEvent.click(toggle);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("clicking toggle twice returns to light", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const toggle = findThemeToggle(container);
    fireEvent.click(toggle);
    expect(document.documentElement.dataset.theme).toBe("dark");
    fireEvent.click(toggle);
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("Theme toggle: writes to localStorage", () => {
  it("clicking toggle writes aw-theme=dark to localStorage", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const toggle = findThemeToggle(container);
    fireEvent.click(toggle);
    expect(localStorage.getItem("aw-theme")).toBe("dark");
  });

  it("clicking toggle twice writes aw-theme=light to localStorage", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const toggle = findThemeToggle(container);
    fireEvent.click(toggle);
    fireEvent.click(toggle);
    expect(localStorage.getItem("aw-theme")).toBe("light");
  });
});

describe("Theme toggle: applies data-theme to shadow host in ShadowRoot", () => {
  it("clicking toggle in shadow DOM updates shadow host data-theme", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const shadow = host.attachShadow({ mode: "open" });
    const mount = document.createElement("div");
    shadow.appendChild(mount);
    try {
      const { container } = render(<App viewModel={makeVm()} mode="live" />, { container: mount });
      const toggle = findThemeToggle(container);
      fireEvent.click(toggle);
      expect(host.getAttribute("data-theme")).toBe("dark");
    } finally {
      host.remove();
    }
  });
});

describe("Demo mode: theme toggle also works", () => {
  it("demo mode has theme toggle via TweaksPanel (gear button, not inline)", () => {
    const { container } = render(<App />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });
});
