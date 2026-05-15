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
    run_id: "run_dock_001",
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

function openDockMenu(container) {
  const btn = container.querySelector('button[title="Dock position"]');
  expect(btn).not.toBeNull();
  fireEvent.click(btn);
}

function findDockOption(label) {
  const all = Array.from(document.body.querySelectorAll("button"));
  return all.find((b) => b.textContent.includes(label));
}

describe("App live mode: onDockChange callback contract", () => {
  it("selecting 'Dock right' calls onDockChange('right')", () => {
    const onDockChange = vi.fn();
    const { container } = render(
      <App viewModel={makeVm()} mode="live" onDockChange={onDockChange} />
    );
    openDockMenu(container);
    const opt = findDockOption("Dock right");
    expect(opt).not.toBeNull();
    fireEvent.click(opt);
    expect(onDockChange).toHaveBeenCalledWith("right");
  });

  it("selecting 'Dock left' calls onDockChange('left')", () => {
    const onDockChange = vi.fn();
    const { container } = render(
      <App viewModel={makeVm()} mode="live" onDockChange={onDockChange} />
    );
    openDockMenu(container);
    const opt = findDockOption("Dock left");
    fireEvent.click(opt);
    expect(onDockChange).toHaveBeenCalledWith("left");
  });

  it("selecting 'Dock top' calls onDockChange('top')", () => {
    const onDockChange = vi.fn();
    const { container } = render(
      <App viewModel={makeVm()} mode="live" onDockChange={onDockChange} />
    );
    openDockMenu(container);
    const opt = findDockOption("Dock top");
    fireEvent.click(opt);
    expect(onDockChange).toHaveBeenCalledWith("top");
  });

  it("selecting 'Floating' calls onDockChange('float')", () => {
    const onDockChange = vi.fn();
    const { container } = render(
      <App viewModel={makeVm()} mode="live" onDockChange={onDockChange} />
    );
    openDockMenu(container);
    const opt = findDockOption("Floating");
    fireEvent.click(opt);
    expect(onDockChange).toHaveBeenCalledWith("float");
  });

  it("demo mode does not call onDockChange when dock menu used", () => {
    const onDockChange = vi.fn();
    const { container } = render(<App onDockChange={onDockChange} />);
    openDockMenu(container);
    const opt = findDockOption("Dock left");
    if (opt) fireEvent.click(opt);
    expect(onDockChange).not.toHaveBeenCalled();
  });
});

describe("PanelV2LiveHost: forwards onDockChange", () => {
  it("PanelV2LiveHost passes onDockChange through to App", () => {
    const onDockChange = vi.fn();
    const { container } = render(
      <PanelV2LiveHost
        transport={makeTransport()}
        storeState={makeStoreState()}
        onDockChange={onDockChange}
      />
    );
    openDockMenu(container);
    const opt = findDockOption("Dock left");
    fireEvent.click(opt);
    expect(onDockChange).toHaveBeenCalledWith("left");
  });
});
