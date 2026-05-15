import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, existsSync } from "fs";
import { join } from "path";

const PANEL_V2_DIR = join(import.meta.dirname, "../src/panel-v2");

describe("panel-v2 static audit", () => {
  it("panel-v2 directory exists", () => {
    expect(existsSync(PANEL_V2_DIR)).toBe(true);
  });

  it("panel-v2 contains expected files", () => {
    const files = readdirSync(PANEL_V2_DIR);
    for (const required of [
      "app.jsx",
      "chrome.jsx",
      "llm-tab.jsx",
      "secondary-tabs.jsx",
      "tweaks-panel.jsx",
      "website.jsx",
      "icons.jsx",
    ]) {
      expect(files, `panel-v2 must contain ${required}`).toContain(required);
    }
  });

  it("panel-v2 files do not import from src/v4", () => {
    const files = readdirSync(PANEL_V2_DIR).filter(
      (f) => f.endsWith(".jsx") || f.endsWith(".js")
    );
    for (const file of files) {
      const content = readFileSync(join(PANEL_V2_DIR, file), "utf-8");
      expect(content, `${file} must not import from src/v4`).not.toMatch(
        /from\s+['"].*\/v4\//
      );
      expect(content, `${file} must not import from v4`).not.toMatch(
        /['"].*\/v4\/.*['"]/
      );
    }
  });

  it("panel-v2 files do not import from latest_frontend_design", () => {
    const files = readdirSync(PANEL_V2_DIR).filter(
      (f) => f.endsWith(".jsx") || f.endsWith(".js")
    );
    for (const file of files) {
      const content = readFileSync(join(PANEL_V2_DIR, file), "utf-8");
      expect(
        content,
        `${file} must not import from latest_frontend_design`
      ).not.toMatch(/latest_frontend_design/);
    }
  });

  it("panel-v2 files do not use window.I as a global (must import I)", () => {
    const files = readdirSync(PANEL_V2_DIR).filter(
      (f) => f.endsWith(".jsx") || f.endsWith(".js") && f !== "icons.jsx"
    );
    for (const file of files) {
      if (file === "icons.jsx") continue;
      const content = readFileSync(join(PANEL_V2_DIR, file), "utf-8");
      expect(
        content,
        `${file} must not reference window.I`
      ).not.toMatch(/window\.I\b/);
    }
  });

  it("panel-v2 files do not assign to window globals", () => {
    const files = readdirSync(PANEL_V2_DIR).filter(
      (f) => f.endsWith(".jsx") || f.endsWith(".js")
    );
    for (const file of files) {
      const content = readFileSync(join(PANEL_V2_DIR, file), "utf-8");
      expect(
        content,
        `${file} must not assign to window.*`
      ).not.toMatch(/window\.\w+\s*=/);
    }
  });
});
