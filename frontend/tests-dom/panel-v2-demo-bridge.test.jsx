import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render } from "@testing-library/react";
import { readFileSync } from "fs";
import { join } from "path";

import { getDemoViewModel, DEMO_TWEAK_DEFAULTS, DEMO_STATE_META } from "../src/panel-v2-adapter/demo-bridge.js";

const SRC = join(import.meta.dirname, "../src/panel-v2");

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

describe("004B demo-bridge: app.jsx imports from demo-bridge", () => {
  it("app.jsx imports TWEAK_DEFAULTS from panel-v2-adapter/demo-bridge", () => {
    const src = readFileSync(join(SRC, "app.jsx"), "utf-8");
    expect(src).toMatch(/DEMO_TWEAK_DEFAULTS|TWEAK_DEFAULTS.*demo-bridge/);
  });

  it("app.jsx imports STATE_META from panel-v2-adapter/demo-bridge", () => {
    const src = readFileSync(join(SRC, "app.jsx"), "utf-8");
    expect(src).toMatch(/DEMO_STATE_META|STATE_META.*demo-bridge/);
  });

  it("app.jsx does not define TWEAK_DEFAULTS inline anymore", () => {
    const src = readFileSync(join(SRC, "app.jsx"), "utf-8");
    // After moving to demo-bridge, app.jsx should not define the object inline
    // (It may still reference TWEAK_DEFAULTS from the import)
    expect(src).not.toMatch(/^const TWEAK_DEFAULTS\s*=/m);
  });

  it("app.jsx does not define STATE_META inline anymore", () => {
    const src = readFileSync(join(SRC, "app.jsx"), "utf-8");
    expect(src).not.toMatch(/^const STATE_META\s*=/m);
  });
});

describe("004B demo-bridge: view model completeness", () => {
  it("getDemoViewModel('locator') returns locator-specific state", () => {
    const vm = getDemoViewModel({ state: "locator" });
    expect(vm.runtime.phase).toBe("locator");
  });

  it("getDemoViewModel('idle') returns idle state", () => {
    const vm = getDemoViewModel({ state: "idle" });
    expect(vm.runtime.phase).toBe("idle");
  });

  it("getDemoViewModel() defaults to 'locator' (same as TWEAK_DEFAULTS)", () => {
    const vm = getDemoViewModel();
    expect(vm.runtime.phase).toBe(DEMO_TWEAK_DEFAULTS.state);
  });

  it("demo view model counts are preset", () => {
    const vm = getDemoViewModel();
    expect(typeof vm.counts.steps).toBe("number");
    expect(typeof vm.counts.rec).toBe("number");
  });
});

describe("004B demo-bridge: demo data separation", () => {
  it("demo-bridge does not import from live transport/store/commands", () => {
    const src = readFileSync(join(import.meta.dirname, "../src/panel-v2-adapter/demo-bridge.js"), "utf-8");
    expect(src).not.toMatch(/from.*transport/);
    expect(src).not.toMatch(/from.*store\/reducer/);
    expect(src).not.toMatch(/from.*commands\/command-builder/);
  });

  it("state-bridge does not import DEMO_STATE_META or DEMO_TWEAK_DEFAULTS", () => {
    const src = readFileSync(join(import.meta.dirname, "../src/panel-v2-adapter/state-bridge.js"), "utf-8");
    expect(src).not.toMatch(/DEMO_STATE_META/);
    expect(src).not.toMatch(/DEMO_TWEAK_DEFAULTS/);
    expect(src).not.toMatch(/demo-bridge/);
  });
});

describe("004B panel-v2 App: still renders with demo-bridge data", () => {
  it("App renders without crashing (smoke)", async () => {
    const { App } = await import("../src/panel-v2/app.jsx");
    const { container } = render(<App />);
    expect(container.firstChild).not.toBeNull();
  });

  it("App renders .aw-stage", async () => {
    const { App } = await import("../src/panel-v2/app.jsx");
    const { container } = render(<App />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("All 5 tabs still present", async () => {
    const { App } = await import("../src/panel-v2/app.jsx");
    const { container } = render(<App />);
    expect(container.querySelectorAll(".aw-tab").length).toBe(5);
  });

  it("TweaksPanel opens on __activate_edit_mode", async () => {
    const { App } = await import("../src/panel-v2/app.jsx");
    const { container, act: libAct } = await import("@testing-library/react");
    // Re-import act from testing-library
    const { act } = await import("@testing-library/react");
    render(<App />);
    expect(document.querySelector(".twk-panel")).toBeNull();
    await act(async () => {
      window.dispatchEvent(new MessageEvent("message", { data: { type: "__activate_edit_mode" } }));
    });
    expect(document.querySelector(".twk-panel")).not.toBeNull();
  });
});
