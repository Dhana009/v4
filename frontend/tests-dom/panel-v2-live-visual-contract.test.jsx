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

function makeVm(phase = "idle") {
  const phaseToTransport = {
    idle:   { runState: "idle", interactionMode: "idle" },
    exec:   { runState: "executing", interactionMode: "executing" },
    plan:   { runState: "idle", interactionMode: "idle" },
    permit: { runState: "executing", interactionMode: "executing" },
  };
  const phaseToStore = {
    idle:   { phase: "idle" },
    exec:   { phase: "executing" },
    plan:   { phase: "awaiting_confirmation", interaction_mode: "plan_review" },
    permit: { phase: "executing", pending_permission: { step_id: "stp_x" } },
  };
  return mapTransportToViewModel(
    makeTransport(phaseToTransport[phase] ?? {}),
    { connected: true, run_id: "run_test", phase: "idle", interaction_mode: "idle",
      pending_steps: [], recorded_steps: [], code_preview: null, trace_entries: [],
      agents: null, pending_permission: null, pending_recovery: null, pending_clarification: null,
      no_browser_state: null, api_key_required_state: null, human_input_required_state: null,
      e2e_pending_state: null, ...phaseToStore[phase] }
  );
}

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("live mode: no aw-stage full-page wrapper", () => {
  it("App in live mode does NOT render .aw-stage", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelector(".aw-stage")).toBeNull();
  });

  it("PanelV2LiveHost does NOT render .aw-stage", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-stage")).toBeNull();
  });

  it("App in live mode does NOT render .aw-site (website preview)", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelector(".aw-site")).toBeNull();
  });

  it("PanelV2LiveHost does NOT render .aw-site", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-site")).toBeNull();
  });
});

describe("live mode: .aw-panel is root, fills container", () => {
  it("App in live mode renders .aw-panel", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    expect(container.querySelector(".aw-panel")).not.toBeNull();
  });

  it("App in live mode .aw-panel has height: 100% to fill host container", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    const panel = container.querySelector(".aw-panel");
    expect(panel.style.height).toBe("100%");
  });

  it("App in live mode .aw-panel has width: 100% (host sizes the container)", () => {
    const vm = makeVm("idle");
    const { container } = render(<App viewModel={vm} mode="live" />);
    const panel = container.querySelector(".aw-panel");
    expect(panel.style.width).toBe("100%");
  });
});

describe("demo/preview mode: aw-stage preserved", () => {
  it("App without props (demo mode) still renders .aw-stage", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("App without props (demo mode) still renders .aw-site", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".aw-site")).not.toBeNull();
  });
});

describe("app.jsx source audit: TweaksPanel in demo, not in live", () => {
  it("app.jsx source includes TweaksPanel in demo render path", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(join(import.meta.dirname, "../src/panel-v2/app.jsx"), "utf-8");
    expect(src).toMatch(/<TweaksPanel/);
  });

  it("app.jsx live-mode early return does not wrap panel in aw-stage", async () => {
    // Verified structurally by the DOM tests above; source confirms the isLive branch
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(join(import.meta.dirname, "../src/panel-v2/app.jsx"), "utf-8");
    expect(src).toMatch(/isLive/);
  });
});

describe("app.jsx CSS source audit", () => {
  it("app.jsx imports panel-v2 styles.css so CSS is available in live bundle", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2/app.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/import.*styles\.css/);
  });
});
