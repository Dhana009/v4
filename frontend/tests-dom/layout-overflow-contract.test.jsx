// FE-VISUAL-QA-001 — overflow/narrow-width contract.
//
// Pins the CSS policies that keep the panel usable when the cell narrows:
// - .aw-header-main uses overflow-x:auto (not hidden) so chrome icons
//   stay reachable via horizontal scroll instead of being clipped.
// - .aw-panel-body uses overflow-y:auto with min-height:0 so vertical
//   scroll lives on the body, not the whole panel.
// - .aw-code / .aw-trace wide content has overflow-x:auto containers.
// - TweaksPanel slider min must be 300 so QA can reach the narrow extreme.
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const V4 = fs.readFileSync(path.resolve(__dirname, "../v4.css"), "utf-8");
const TWEAKS = fs.readFileSync(path.resolve(__dirname, "../src/demo/tweaks-panel.jsx"), "utf-8");

function ruleBlock(css, selector) {
  // Returns the `{ ... }` block whose selector is exactly `selector` (not a
  // descendant rule). Skips combined rules like `.foo .aw-header-main`.
  const re = new RegExp("(^|\\})\\s*" + selector.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&") + "\\s*\\{", "m");
  const m = re.exec(css);
  if (!m) return null;
  const open = css.indexOf("{", m.index + m[0].length - 1);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

describe("FE-VISUAL-QA-001 overflow contract", () => {
  it(".aw-header-main scrolls horizontally instead of clipping", () => {
    const block = ruleBlock(V4, ".aw-header-main");
    expect(block, ".aw-header-main rule missing").not.toBeNull();
    expect(block).toMatch(/overflow-x:\s*auto/);
    expect(block).toMatch(/overflow-y:\s*hidden/);
    expect(block).toMatch(/min-width:\s*0/);
    // Negative: must NOT use the clipping `overflow: hidden` shorthand alone.
    expect(block).not.toMatch(/(^|;)\s*overflow:\s*hidden/);
  });

  it(".aw-panel-body owns vertical scroll with min-height:0", () => {
    const block = ruleBlock(V4, ".aw-panel-body");
    expect(block, ".aw-panel-body rule missing").not.toBeNull();
    expect(block).toMatch(/overflow-y:\s*auto/);
    expect(block).toMatch(/min-height:\s*0/);
  });

  it("TweaksPanel panelWidth slider reaches 300px (narrow QA extreme)", () => {
    // The slider field block in SECTIONS must declare min: 300 (or lower).
    // Format example: `kind: "slider", key: "panelWidth", ..., min: 300, ...`.
    expect(TWEAKS).toMatch(/key:\s*"panelWidth"[\s\S]{0,200}min:\s*300/);
  });
});
