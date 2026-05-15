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
    run_id: "run_hdr_001",
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
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("data-wide attribute: not always '0'", () => {
  it("live mode aw-panel has data-wide='1' (wide header)", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const panel = container.querySelector(".aw-panel");
    expect(panel.getAttribute("data-wide")).toBe("1");
  });
});

describe("Settings gear button: hidden/disabled in live mode", () => {
  it("settings gear button is not rendered in live mode", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).toBeNull();
  });

  it("settings gear button IS rendered in demo mode (unchanged)", () => {
    const { container } = render(<App />);
    const gear = container.querySelector('button[title="Settings & Tweaks"]');
    expect(gear).not.toBeNull();
  });
});

describe("LLM/Manual mode switch: disabled in live mode", () => {
  it("live mode LLM button has disabled attribute", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const llmBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.trim() === "LLM" && b.classList.contains("aw-mode-opt"));
    expect(llmBtn).not.toBeNull();
    expect(llmBtn.disabled).toBe(true);
  });

  it("live mode Manual button has disabled attribute", () => {
    const { container } = render(<App viewModel={makeVm()} mode="live" />);
    const manualBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.trim() === "Manual" && b.classList.contains("aw-mode-opt"));
    expect(manualBtn).not.toBeNull();
    expect(manualBtn.disabled).toBe(true);
  });

  it("demo mode LLM/Manual buttons remain enabled (unchanged)", () => {
    const { container } = render(<App />);
    const llmBtn = Array.from(container.querySelectorAll("button"))
      .find((b) => b.textContent.trim() === "LLM" && b.classList.contains("aw-mode-opt"));
    expect(llmBtn).not.toBeNull();
    expect(llmBtn.disabled).toBe(false);
  });
});
