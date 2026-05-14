// FE-LAYOUT-001 — Preview dock/stage layout contract.
//
// Pins:
// - PreviewShell renders a ROOT-style flex stage with website + panel-cell
//   siblings (NOT three stacked position:fixed divs).
// - Dock variants swap `aw-stage--dock-*` class on the stage root.
// - TweaksPanel `panelWidth` slider drives `.aw-panel-cell` width (no remount).
// - Stage and panel-cell are flush — no padding/top-offset/margin in docked modes.
// - Live `mount()` path (no `demo:true`) does NOT render the preview stage.
// - Inner panel layout (header/tabs/body/composer/footer flex column) is
//   shared by both modes via the existing IDEPanel root width/height 100%.
import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";

import { PreviewShell } from "../src/main.jsx";

function activateTweaks() {
  act(() => {
    window.postMessage({ type: "__activate_edit_mode" }, "*");
  });
  return new Promise((r) => setTimeout(r, 30));
}

describe("FE-LAYOUT-001 preview dock/stage contract", () => {
  it("renders aw-stage flex container with website + panel-cell (dock-right default)", () => {
    render(<PreviewShell />);
    const stage = screen.getByTestId("aw-preview-stage");
    expect(stage).toBeInTheDocument();
    expect(stage.className).toMatch(/\baw-stage\b/);
    expect(stage.className).toMatch(/aw-stage--dock-right/);
    expect(screen.getByTestId("aw-website-region")).toBeInTheDocument();
    expect(screen.getByTestId("aw-panel-cell")).toBeInTheDocument();
  });

  it("stage uses flex layout (display:flex)", () => {
    render(<PreviewShell />);
    const stage = screen.getByTestId("aw-preview-stage");
    expect(stage.style.display).toBe("flex");
  });

  it("dock-left / dock-top / dock-float toggling swaps aw-stage--dock-* class", async () => {
    render(<PreviewShell />);
    await activateTweaks();
    fireEvent.click(screen.getByTestId("aw-tweaks-dock-left"));
    expect(screen.getByTestId("aw-preview-stage").className).toMatch(/aw-stage--dock-left/);
    fireEvent.click(screen.getByTestId("aw-tweaks-dock-top"));
    expect(screen.getByTestId("aw-preview-stage").className).toMatch(/aw-stage--dock-top/);
    fireEvent.click(screen.getByTestId("aw-tweaks-dock-float"));
    expect(screen.getByTestId("aw-preview-stage").className).toMatch(/aw-stage--dock-float/);
  });

  it("collapsed toggle adds aw-stage--collapsed class", async () => {
    render(<PreviewShell />);
    await activateTweaks();
    fireEvent.click(screen.getByTestId("aw-tweaks-collapsed"));
    expect(screen.getByTestId("aw-preview-stage").className).toMatch(/aw-stage--collapsed/);
  });

  it("panelWidth slider drives .aw-panel-cell width without remount", async () => {
    render(<PreviewShell />);
    await activateTweaks();
    const slider = screen.getByTestId("aw-tweaks-panelWidth");
    fireEvent.change(slider, { target: { value: "420" } });
    const cell = screen.getByTestId("aw-panel-cell");
    expect(cell.style.width).toBe("420px");
  });

  it("docked panel-cell is flush — no top offset, no margin-top, no padding gap", () => {
    render(<PreviewShell />);
    const stage = screen.getByTestId("aw-preview-stage");
    const cell = screen.getByTestId("aw-panel-cell");
    // Stage occupies viewport, no padding inset.
    const stagePadding = stage.style.padding || "";
    expect(stagePadding === "" || stagePadding === "0px" || stagePadding === "0").toBe(true);
    // Panel-cell flush to stage edge — no inline offsets.
    expect(cell.style.top || "").toBe("");
    expect(cell.style.marginTop || "").toBe("");
    // No "floating-card" boxShadow on docked cell.
    expect(cell.style.boxShadow || "").toBe("");
  });

  it("website-region is a flex sibling (flex:1) — gets remaining width, not fixed", () => {
    render(<PreviewShell />);
    const website = screen.getByTestId("aw-website-region");
    // Either inline flex:1 or class — assert NOT position:fixed.
    expect(website.style.position).not.toBe("fixed");
    // No explicit width pin — flex fills.
    expect(website.style.width || "").toBe("");
  });

  it("PreviewShell passes inStage:true so live mount() is unaffected", () => {
    const src = fs.readFileSync(path.resolve(__dirname, "../src/main.jsx"), "utf-8");
    // PreviewShell tells mount() to skip the live fixed-shell wrapper.
    expect(src).toMatch(/inStage:\s*true/);
    // Live mount path still exists and is a distinct function.
    expect(src).toMatch(/^function mount\b/m);
  });

  it("inner IDEPanel root keeps width/height 100% (shared inner layout)", () => {
    // aw-ide-panel.jsx exposes data-testid="aw-stage" on the inner root with
    // width/height 100%. Layer assertion via source check — jsdom shadow DOM
    // probing is brittle.
    const src = fs.readFileSync(path.resolve(__dirname, "../aw-ide-panel.jsx"), "utf-8");
    // The inner root must NOT introduce its own position:fixed.
    expect(src).not.toMatch(/data-testid="aw-stage"[^>]*style=\{\{[^}]*position:\s*"fixed"/);
    // Width/height 100% retained.
    expect(src).toMatch(/data-testid="aw-stage"[^>]*\n?\s*style=\{\{\s*width:\s*"100%",\s*height:\s*"100%"/);
  });

  it("live mode: AutoWorkbenchRuntime selects relative outer when inStage=true", () => {
    const src = fs.readFileSync(path.resolve(__dirname, "../src/main.jsx"), "utf-8");
    // Implementation MUST branch outerStyle on an inStage flag.
    expect(src).toMatch(/inStage/);
    // Demo fixtures still gated on config.demo === true.
    expect(src).toMatch(/config\?\.demo\s*===\s*true/);
  });
});
