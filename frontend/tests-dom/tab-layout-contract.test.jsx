// FE-VISUAL-QA-001 — tab layout container contract.
//
// Each tab body renders into the same single .aw-panel-body container,
// which must own vertical scroll. Wide-content tabs (Code, Trace) must
// declare horizontal-scroll containers so long lines don't push the
// whole panel sideways.
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const V4 = fs.readFileSync(path.resolve(__dirname, "../v4.css"), "utf-8");
const IDEPANEL = fs.readFileSync(path.resolve(__dirname, "../aw-ide-panel.jsx"), "utf-8");

function blocks(css, selector) {
  const out = [];
  let i = 0;
  while (true) {
    const idx = css.indexOf(selector, i);
    if (idx === -1) break;
    const open = css.indexOf("{", idx);
    const close = css.indexOf("}", open);
    out.push(css.slice(open + 1, close));
    i = close;
  }
  return out;
}

describe("FE-VISUAL-QA-001 tab-layout contract", () => {
  it("body has a single stable testid for every tab", () => {
    expect(IDEPANEL).toMatch(/data-testid="aw-panel-body"/);
  });

  it("code container scrolls horizontally for wide lines", () => {
    // .aw-code OR .aw-codeblock must declare overflow-x:auto somewhere.
    const codeRules = [...blocks(V4, ".aw-code"), ...blocks(V4, ".aw-codeblock")];
    const anyScrolls = codeRules.some((b) => /overflow-x:\s*auto/.test(b));
    expect(anyScrolls, "no .aw-code/.aw-codeblock rule with overflow-x:auto").toBe(true);
  });

  it("trace container scrolls horizontally for wide rows", () => {
    const traceRules = blocks(V4, ".aw-trace");
    expect(traceRules.length, ".aw-trace rules missing").toBeGreaterThan(0);
    const anyScrolls = traceRules.some((b) => /overflow-x:\s*auto/.test(b));
    expect(anyScrolls, "no .aw-trace rule with overflow-x:auto").toBe(true);
  });
});
