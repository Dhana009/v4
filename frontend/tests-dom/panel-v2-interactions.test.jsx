import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { readFileSync } from "fs";
import { join } from "path";
import { App } from "../src/panel-v2/app.jsx";

const SRC = join(import.meta.dirname, "../src/panel-v2");

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
});

async function openTweaks(container) {
  await act(async () => {
    window.dispatchEvent(
      new MessageEvent("message", { data: { type: "__activate_edit_mode" } })
    );
  });
  return container.querySelector(".twk-panel");
}

// Dock control renders as <select> (4 options → falls outside fitsAsSegments)
// selects order in TweaksPanel: [0]=Dock, [1]=Tab, [2]=State
// Theme renders as segmented (.twk-seg): [0]=Theme, [1]=Mode, [2]=Highlight CTA
// In jsdom, getBoundingClientRect()={width:0,...}, so segAt(0)→idx=1→"dark", segAt(1000)→idx=0→"light"
// Toggles (.twk-toggle): [0]=Collapsed, [1]=Show website behind, [2]=Agent Control Center

describe("panel-v2 interactions: TweaksPanel controls", () => {
  it("TweaksPanel opens on __activate_edit_mode", async () => {
    const { container } = render(<App />);
    expect(container.querySelector(".twk-panel")).toBeNull();
    const panel = await openTweaks(container);
    expect(panel).not.toBeNull();
  });

  it("TweaksPanel has a dock select control", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const selects = twk.querySelectorAll("select.twk-field");
    expect(selects.length).toBeGreaterThan(0);
    // first select is Dock; default value is "right"
    expect(selects[0].value).toBe("right");
  });

  it("TweaksPanel has a theme segmented control", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const segs = twk.querySelectorAll(".twk-seg");
    expect(segs.length).toBeGreaterThan(0);
  });

  it("TweaksPanel has collapsed toggle", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const toggles = twk.querySelectorAll(".twk-toggle");
    expect(toggles.length).toBeGreaterThan(0);
  });
});

describe("panel-v2 interactions: dock controls update state", () => {
  it("changing dock select to 'left' updates stage to dock-left", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const dockSelect = twk.querySelectorAll("select.twk-field")[0];
    await act(async () => {
      fireEvent.change(dockSelect, { target: { value: "left" } });
    });
    expect(container.querySelector(".aw-stage").classList.contains("dock-left")).toBe(true);
  });

  it("changing dock select to 'top' updates stage to dock-top", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const dockSelect = twk.querySelectorAll("select.twk-field")[0];
    await act(async () => {
      fireEvent.change(dockSelect, { target: { value: "top" } });
    });
    expect(container.querySelector(".aw-stage").classList.contains("dock-top")).toBe(true);
  });

  it("changing dock select to 'float' updates stage to dock-float", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const dockSelect = twk.querySelectorAll("select.twk-field")[0];
    await act(async () => {
      fireEvent.change(dockSelect, { target: { value: "float" } });
    });
    expect(container.querySelector(".aw-stage").classList.contains("dock-float")).toBe(true);
  });
});

describe("panel-v2 interactions: theme controls update state", () => {
  it("app sets data-theme=light on documentElement by default", () => {
    render(<App />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("theme segmented control has 'light' and 'dark' options", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const themeSeg = twk.querySelectorAll(".twk-seg")[0];
    const buttons = themeSeg.querySelectorAll("button");
    const labels = Array.from(buttons).map((b) => b.textContent.trim());
    expect(labels).toContain("light");
    expect(labels).toContain("dark");
  });

  it("theme segment 'light' button is aria-checked by default", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const themeSeg = twk.querySelectorAll(".twk-seg")[0];
    const lightBtn = Array.from(themeSeg.querySelectorAll("button"))
      .find((b) => b.textContent.trim() === "light");
    expect(lightBtn.getAttribute("aria-checked")).toBe("true");
  });
});

describe("panel-v2 interactions: collapsed state", () => {
  it("clicking collapsed toggle shows collapsed rail", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    const collapsedToggle = twk.querySelectorAll(".twk-toggle")[0];
    await act(async () => {
      fireEvent.click(collapsedToggle);
    });
    expect(container.querySelector(".aw-collapsed-rail")).not.toBeNull();
  });

  it("collapsed stage has 'collapsed' class", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    await act(async () => {
      fireEvent.click(twk.querySelectorAll(".twk-toggle")[0]);
    });
    expect(container.querySelector(".aw-stage").classList.contains("collapsed")).toBe(true);
  });

  it("collapsed rail has expand button", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    await act(async () => {
      fireEvent.click(twk.querySelectorAll(".twk-toggle")[0]);
    });
    const rail = container.querySelector(".aw-collapsed-rail");
    expect(rail.querySelector("button[title='Expand']")).not.toBeNull();
  });

  it("clicking expand in collapsed rail un-collapses", async () => {
    const { container } = render(<App />);
    await openTweaks(container);
    const twk = container.querySelector(".twk-panel");
    await act(async () => {
      fireEvent.click(twk.querySelectorAll(".twk-toggle")[0]);
    });
    const expandBtn = container.querySelector(".aw-collapsed-rail button[title='Expand']");
    await act(async () => {
      fireEvent.click(expandBtn);
    });
    expect(container.querySelector(".aw-collapsed-rail")).toBeNull();
    expect(container.querySelector(".aw-stage").classList.contains("collapsed")).toBe(false);
  });
});

describe("panel-v2 interactions: no forbidden imports", () => {
  const files = ["app.jsx", "chrome.jsx", "icons.jsx", "llm-tab.jsx",
                 "secondary-tabs.jsx", "tweaks-panel.jsx", "website.jsx", "preview.jsx"];

  files.forEach((f) => {
    it(`${f} does not import from src/v4`, () => {
      const src = readFileSync(join(SRC, f), "utf-8");
      expect(src).not.toMatch(/from\s+['"].*\/v4\//);
    });

    it(`${f} does not import from latest_frontend_design/v4`, () => {
      const src = readFileSync(join(SRC, f), "utf-8");
      expect(src).not.toMatch(/latest_frontend_design\/v4/);
    });
  });
});
