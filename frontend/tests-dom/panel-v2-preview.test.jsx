import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

import { Preview } from "../src/panel-v2/preview.jsx";

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("panel-v2 preview: entry renders", () => {
  it("Preview component renders without crashing", () => {
    const { container } = render(<Preview />);
    expect(container.firstChild).not.toBeNull();
  });

  it("website preview is present (.aw-website)", () => {
    const { container } = render(<Preview />);
    expect(container.querySelector(".aw-website")).not.toBeNull();
  });

  it("header/chrome is present (.aw-header)", () => {
    const { container } = render(<Preview />);
    expect(container.querySelector(".aw-header")).not.toBeNull();
  });

  it("tab strip is present (.aw-tabs)", () => {
    const { container } = render(<Preview />);
    expect(container.querySelector(".aw-tabs")).not.toBeNull();
  });

  it("LLM tab is active by default", () => {
    const { container } = render(<Preview />);
    const activeTab = container.querySelector(".aw-tab.active");
    expect(activeTab).not.toBeNull();
    expect(activeTab.textContent).toMatch(/LLM/i);
  });

  it("all 5 tabs are present", () => {
    const { container } = render(<Preview />);
    const tabs = container.querySelectorAll(".aw-tab");
    expect(tabs.length).toBe(5);
  });
});

describe("panel-v2 preview: tab switching", () => {
  it("clicking Steps tab makes it active", () => {
    const { container } = render(<Preview />);
    const tabs = container.querySelectorAll(".aw-tab");
    const stepsTab = Array.from(tabs).find((t) => t.textContent.includes("Steps"));
    expect(stepsTab).not.toBeNull();
    fireEvent.click(stepsTab);
    expect(stepsTab.classList.contains("active")).toBe(true);
  });

  it("clicking Recorded tab makes it active", () => {
    const { container } = render(<Preview />);
    const tabs = container.querySelectorAll(".aw-tab");
    const recTab = Array.from(tabs).find((t) => t.textContent.includes("Recorded"));
    expect(recTab).not.toBeNull();
    fireEvent.click(recTab);
    expect(recTab.classList.contains("active")).toBe(true);
  });

  it("switching tabs deactivates previous tab", () => {
    const { container } = render(<Preview />);
    const tabs = container.querySelectorAll(".aw-tab");
    const llmTab = Array.from(tabs).find((t) => t.textContent.includes("LLM"));
    const stepsTab = Array.from(tabs).find((t) => t.textContent.includes("Steps"));
    fireEvent.click(stepsTab);
    expect(llmTab.classList.contains("active")).toBe(false);
    expect(stepsTab.classList.contains("active")).toBe(true);
  });
});

describe("panel-v2 preview: tweaks panel", () => {
  it("TweaksPanel opens on __activate_edit_mode message", async () => {
    const { container } = render(<Preview />);
    expect(container.querySelector(".twk-panel")).toBeNull();
    await act(async () => {
      window.dispatchEvent(new MessageEvent("message", {
        data: { type: "__activate_edit_mode" }
      }));
    });
    expect(container.querySelector(".twk-panel")).not.toBeNull();
  });
});

describe("panel-v2 preview: dock and theme controls", () => {
  it("dock controls are present in panel", () => {
    const { container } = render(<Preview />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
    expect(container.querySelector(".aw-panel")).not.toBeNull();
  });

  it("panel starts with dock-right class", () => {
    const { container } = render(<Preview />);
    const stage = container.querySelector(".aw-stage");
    expect(stage.classList.contains("dock-right")).toBe(true);
  });

  it("LLM/Manual mode switch is present", () => {
    const { container } = render(<Preview />);
    expect(container.querySelector(".aw-mode-switch")).not.toBeNull();
  });
});

describe("panel-v2 preview: no backend required", () => {
  it("renders without WebSocket or backend connection", () => {
    expect(() => render(<Preview />)).not.toThrow();
  });
});

describe("panel-v2 preview: static audit of preview.jsx", () => {
  const PREVIEW_PATH = join(import.meta.dirname, "../src/panel-v2/preview.jsx");

  it("preview.jsx exists", () => {
    expect(existsSync(PREVIEW_PATH)).toBe(true);
  });

  it("preview.jsx does not import from src/v4", () => {
    const content = readFileSync(PREVIEW_PATH, "utf-8");
    expect(content).not.toMatch(/from\s+['"].*\/v4\//);
    expect(content).not.toMatch(/['"].*\/v4\/.*['"]/);
  });

  it("preview.jsx does not import from latest_frontend_design", () => {
    const content = readFileSync(PREVIEW_PATH, "utf-8");
    expect(content).not.toMatch(/latest_frontend_design/);
  });

  it("preview.jsx does not use WebSocket", () => {
    const content = readFileSync(PREVIEW_PATH, "utf-8");
    expect(content).not.toMatch(/WebSocket|new WebSocket/);
  });
});
