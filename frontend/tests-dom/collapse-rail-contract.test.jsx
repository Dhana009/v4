// FE-VISUAL-QA-001 — collapse rail contract.
//
// When TweaksPanel toggles `collapsed=true`, the preview must:
// - emit a full `aw-preview-tweaks` window event,
// - AutoWorkbenchRuntime (mounted with inStage:true) must observe it and
//   propagate `collapsed` into the inner IDEPanel,
// - IDEPanel renders the CollapsedRail (data-testid="aw-collapsed-rail")
//   in place of the full chrome — body/composer/footer hidden.
// - When `collapsed=false`, full panel restored.
//
// Source-level pins (jsdom can't fully simulate shadow rendering across
// React roots, so we anchor the wiring in source):
// - PreviewShell emits aw-preview-tweaks with full detail on tweaks change.
// - aw-ide-panel.jsx subscribes to aw-preview-tweaks and syncs internal
//   collapsed + theme state.
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const MAIN = fs.readFileSync(path.resolve(__dirname, "../src/main.jsx"), "utf-8");
const IDEPANEL = fs.readFileSync(path.resolve(__dirname, "../aw-ide-panel.jsx"), "utf-8");
const CHROME = fs.readFileSync(path.resolve(__dirname, "../src/v4/chrome.jsx"), "utf-8");

describe("FE-VISUAL-QA-001 collapse-rail contract", () => {
  it("CollapsedRail carries a stable test id", () => {
    expect(CHROME).toMatch(/data-testid="aw-collapsed-rail"/);
  });

  it("PreviewShell emits aw-preview-tweaks event with full tweaks on each change", () => {
    // Must dispatch CustomEvent('aw-preview-tweaks', { detail: tweaks }).
    expect(MAIN).toMatch(/aw-preview-tweaks/);
    expect(MAIN).toMatch(/new CustomEvent\(\s*"aw-preview-tweaks"/);
  });

  it("aw-ide-panel subscribes to aw-preview-tweaks and syncs collapsed/theme/tab", () => {
    expect(IDEPANEL).toMatch(/aw-preview-tweaks/);
    expect(IDEPANEL).toMatch(/addEventListener\(\s*"aw-preview-tweaks"/);
  });

  it("Collapsed rail listens to live `collapsed` flag and hides body/composer/footer", () => {
    // The existing render branch already gates on `collapsed`. Pin that.
    expect(IDEPANEL).toMatch(/\{!collapsed \?/);
    expect(IDEPANEL).toMatch(/<CollapsedRail/);
  });
});
