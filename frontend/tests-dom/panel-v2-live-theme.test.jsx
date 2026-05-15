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
    run_id: "run_thm_001",
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
  document.documentElement.removeAttribute("data-theme");
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("Theme application in live mode with shadow host", () => {
  it("live mode inside a ShadowRoot writes data-theme to shadow host element", () => {
    // Create a host element with an attached shadow root, mount App inside it.
    const host = document.createElement("div");
    host.id = "test-shadow-host";
    document.body.appendChild(host);
    const shadow = host.attachShadow({ mode: "open" });
    const mount = document.createElement("div");
    shadow.appendChild(mount);
    try {
      const { unmount } = render(<App viewModel={makeVm()} mode="live" />, { container: mount });
      expect(host.getAttribute("data-theme")).toBe("light");
      unmount();
    } finally {
      host.remove();
    }
  });
});

describe("Theme application fallback in live mode without shadow host", () => {
  it("live mode without a shadow root falls back to documentElement", () => {
    render(<App viewModel={makeVm()} mode="live" />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("Theme application in demo mode unchanged", () => {
  it("demo mode writes data-theme to documentElement", () => {
    render(<App />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
