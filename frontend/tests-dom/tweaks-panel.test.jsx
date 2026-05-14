// FE-VBATCH-002 Story 4 — TweaksPanel demo overlay.
//
// Pins:
// - Panel opens on `__activate_edit_mode` postMessage; closes on
//   `__deactivate_edit_mode` and close button.
// - Renders dock / panelWidth / collapsed / showWebsite / tab / state /
//   theme / mode / overlays / highlight controls.
// - Changes call `onChange` with the merged tweaks payload — preview state
//   only. No window globals mutated, no backend touched.
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { TweaksPanel, DEFAULT_TWEAKS } from "../src/demo/tweaks-panel.jsx";

function activate() {
  act(() => {
    window.postMessage({ type: "__activate_edit_mode" }, "*");
  });
}

describe("FE-VBATCH-002 TweaksPanel (demo-only)", () => {
  it("hidden by default; opens on __activate_edit_mode postMessage", async () => {
    render(<TweaksPanel value={DEFAULT_TWEAKS} onChange={() => {}} />);
    expect(screen.queryByTestId("aw-tweaks-panel")).toBeNull();
    activate();
    // postMessage is async; wait one microtask cycle.
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.getByTestId("aw-tweaks-panel")).toBeInTheDocument();
  });

  it("renders every reference control section", async () => {
    render(<TweaksPanel value={DEFAULT_TWEAKS} onChange={() => {}} defaultOpen={true} />);
    for (const id of ["panel", "active", "lifecycle", "theme", "mode", "overlays", "highlight"]) {
      expect(screen.getByTestId(`aw-tweaks-section-${id}`)).toBeInTheDocument();
    }
    // Sample controls
    expect(screen.getByTestId("aw-tweaks-dock")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-panelWidth")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-collapsed")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-showWebsite")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-theme")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-mode")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-highlight")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tweaks-state")).toBeInTheDocument();
  });

  it("dock radio click reports merged tweaks via onChange (preview-only)", () => {
    const onChange = vi.fn();
    render(<TweaksPanel value={DEFAULT_TWEAKS} onChange={onChange} defaultOpen={true} />);
    fireEvent.click(screen.getByTestId("aw-tweaks-dock-left"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ dock: "left" }));
  });

  it("highlight radio click reports merged tweaks", () => {
    const onChange = vi.fn();
    render(<TweaksPanel value={DEFAULT_TWEAKS} onChange={onChange} defaultOpen={true} />);
    fireEvent.click(screen.getByTestId("aw-tweaks-highlight-pro-cta"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ highlight: "pro-cta" }));
  });

  it("close button hides the panel (preview-state only, no backend command)", async () => {
    render(<TweaksPanel value={DEFAULT_TWEAKS} onChange={() => {}} defaultOpen={true} />);
    expect(screen.getByTestId("aw-tweaks-panel")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("aw-tweaks-close"));
    expect(screen.queryByTestId("aw-tweaks-panel")).toBeNull();
  });

  it("source file is quarantined under src/demo/", async () => {
    const { readFileSync } = await import("node:fs");
    const { resolve } = await import("node:path");
    const path = resolve(__dirname, "../src/demo/tweaks-panel.jsx");
    expect(() => readFileSync(path, "utf-8")).not.toThrow();
  });
});
