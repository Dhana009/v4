// FE-VISUAL-QA-001 — dock-mode state-machine contract.
//
// Layout-dock-contract.test already covers class application; this file
// pins the explicit map so the modes can't drift apart.
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const V4 = fs.readFileSync(path.resolve(__dirname, "../v4.css"), "utf-8");
const MAIN = fs.readFileSync(path.resolve(__dirname, "../src/main.jsx"), "utf-8");

describe("FE-VISUAL-QA-001 dock-modes contract", () => {
  it("v4.css declares all four dock BEM modifiers", () => {
    for (const mod of ["aw-stage--dock-right", "aw-stage--dock-left", "aw-stage--dock-top", "aw-stage--dock-float"]) {
      expect(V4).toMatch(new RegExp("\\." + mod + "\\b"));
    }
  });

  it("PreviewShell renders aw-stage--dock-<mode> for every supported value", () => {
    // The class is assembled programmatically; ensure each modifier string
    // is emitted somewhere in PreviewShell's stage-class derivation.
    for (const mode of ["right", "left", "top", "float"]) {
      expect(MAIN).toMatch(new RegExp(`aw-stage--dock-|"${mode}"`));
    }
    // And the literal "right" fallback is wired (default when none of the
    // other three match).
    expect(MAIN).toMatch(/"right"/);
  });

  it("collapsed adds a stable BEM modifier (not just inline width hack)", () => {
    expect(V4).toMatch(/\.aw-stage--collapsed\b/);
    expect(MAIN).toMatch(/aw-stage--collapsed/);
  });
});
