import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, act } from "@testing-library/react";

import { PanelV2LiveHost } from "../src/panel-v2-adapter/live-host.jsx";

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

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("004C PanelV2LiveHost: renders", () => {
  it("renders without crashing given live transport", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.firstChild).not.toBeNull();
  });

  it("renders .aw-panel", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelector(".aw-panel")).not.toBeNull();
  });

  it("renders 5 tabs", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport()} />);
    expect(container.querySelectorAll(".aw-tab").length).toBe(5);
  });
});

describe("004C PanelV2LiveHost: no demo data leak", () => {
  it("does not render demo STATE_META text in idle mode", () => {
    const { container } = render(<PanelV2LiveHost transport={makeTransport({ runState: "idle" })} />);
    expect(container.textContent).not.toMatch(/Tell me what to automate/);
  });
});

describe("004C PanelV2LiveHost: source audit", () => {
  it("live-host.jsx imports App from panel-v2", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/panel-v2\/app/);
  });

  it("live-host.jsx imports mapTransportToViewModel from state-bridge", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/mapTransportToViewModel/);
    expect(src).toMatch(/state-bridge/);
  });

  it("live-host.jsx does not import demo-bridge", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).not.toMatch(/demo-bridge/);
  });
});
