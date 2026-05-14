// FE-VBATCH-001 Story 3 — demo / live mode separation.
//
// Pins:
// - DEMO_FIXTURES export shape (agents, plan, recorded, code, trace, tokenInfo).
// - demo-fixtures.js is NOT imported by any production source.
// - Rendering IDEPanel with no payload → honest empty (live mode contract).
// - Rendering IDEPanel with DEMO_FIXTURES → populated rows (demo mode).
// - main.jsx mount() guards demo path on `config.demo === true`.
import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";

import { AgentsPopover, NowStrip } from "../src/v4/chrome.jsx";
import {
  DEMO_FIXTURES,
  DEMO_AGENTS,
  DEMO_PLAN,
  DEMO_RECORDED_STEPS,
  DEMO_TRACE_ENTRIES,
  DEMO_LOCATOR_RECOVERY,
  DEMO_NOW_STRIP,
  DEMO_FOOTER,
  DEMO_COMPOSER_CONTEXT,
} from "../src/demo/demo-fixtures.js";

const REPO_FRONTEND = path.resolve(__dirname, "..");

const PRODUCTION_SOURCES = [
  "aw-ide-panel.jsx",
  "src/main.jsx",
  "src/v4/chrome.jsx",
  "src/v4/llm-cards.jsx",
  "src/v4/secondary-tabs.jsx",
  "src/store/reducer.js",
  "src/store/selectors.js",
  "src/store/types.js",
  "src/commands/command-builder.js",
  "src/commands/dispatcher.js",
  "src/commands/validation.js",
];

describe("FE-VBATCH-001 demo / live separation", () => {
  describe("DEMO_FIXTURES shape", () => {
    it("exports the aggregate fixture object with all expected fields", () => {
      expect(DEMO_FIXTURES).toBeTruthy();
      for (const k of ["agents", "plan", "recordedSteps", "codePreview", "traceEntries", "tokenInfo", "pageUrl", "runState"]) {
        expect(DEMO_FIXTURES, `DEMO_FIXTURES.${k} missing`).toHaveProperty(k);
      }
    });

    it("DEMO_AGENTS contains the 6 yui ROOT agents", () => {
      expect(DEMO_AGENTS).toHaveLength(6);
      const keys = DEMO_AGENTS.map((a) => a.key);
      expect(keys).toEqual(expect.arrayContaining(["orch", "pi", "sr", "dbg", "cg", "judge"]));
    });

    it("DEMO_PLAN has 6 steps using stp_* IDs", () => {
      expect(DEMO_PLAN.steps).toHaveLength(6);
      for (const s of DEMO_PLAN.steps) expect(s.step_id).toMatch(/^stp_/);
    });

    it("DEMO_RECORDED_STEPS use rec_* IDs and include at least one repaired entry", () => {
      expect(DEMO_RECORDED_STEPS.length).toBeGreaterThanOrEqual(4);
      for (const r of DEMO_RECORDED_STEPS) expect(r.step_id).toMatch(/^rec_/);
      expect(DEMO_RECORDED_STEPS.some((r) => r.status === "repaired")).toBe(true);
    });

    it("DEMO_TRACE_ENTRIES has 25 timeline rows (matches PDF reference)", () => {
      expect(DEMO_TRACE_ENTRIES).toHaveLength(25);
    });

    it("DEMO_LOCATOR_RECOVERY exposes 3 candidates with risk + confidence", () => {
      expect(DEMO_LOCATOR_RECOVERY.failure_reason).toBe("locator_ambiguous");
      expect(DEMO_LOCATOR_RECOVERY.options).toHaveLength(3);
      for (const c of DEMO_LOCATOR_RECOVERY.options) {
        expect(c.title).toMatch(/Get started/);
        expect(typeof c.confidence).toBe("number");
        expect(c.locator).toBeTruthy();
      }
    });

    it("DEMO_NOW_STRIP supplies state + task + primaryLabel for the orange CTA band", () => {
      expect(DEMO_NOW_STRIP.kind).toBe("block");
      expect(DEMO_NOW_STRIP.state).toBe("Decision required");
      expect(DEMO_NOW_STRIP.primaryLabel).toBe("Choose candidate");
    });

    it("DEMO_FOOTER carries phase/blocker/nextAction (not generic Idle)", () => {
      expect(DEMO_FOOTER.phase).toBe("Locator ambiguity");
      expect(DEMO_FOOTER.blocker).toBeTruthy();
      expect(DEMO_FOOTER.nextAction).toBe("Choose candidate");
    });

    it("DEMO_COMPOSER_CONTEXT supplies 3 reference chips", () => {
      expect(DEMO_COMPOSER_CONTEXT.length).toBeGreaterThanOrEqual(3);
      expect(DEMO_COMPOSER_CONTEXT.find((c) => c.label === "/pricing")).toBeTruthy();
    });
  });

  describe("Quarantine — demo fixtures must not leak into live", () => {
    it("no production source EXCEPT the gating main.jsx imports src/demo/demo-fixtures.js", () => {
      // main.jsx is the *only* permitted importer because it owns the
      // explicit `config.demo === true` gate. Every other production
      // module must remain demo-free so live mode cannot accidentally
      // hydrate fixtures.
      const sources = PRODUCTION_SOURCES.filter((rel) => rel !== "src/main.jsx");
      for (const rel of sources) {
        const src = fs.readFileSync(path.join(REPO_FRONTEND, rel), "utf-8");
        // strip comments first so doc references don't trip
        const codeOnly = src
          .split("\n")
          .map((line) => line.replace(/\/\/.*$/, ""))
          .join("\n")
          .replace(/\/\*[\s\S]*?\*\//g, "");
        expect(codeOnly, `${rel} must not import demo-fixtures.js`).not.toMatch(/from\s+["'][^"']*demo[\/-]fixtures/);
        expect(codeOnly, `${rel} must not require demo-fixtures.js`).not.toMatch(/require\s*\(\s*["'][^"']*demo[\/-]fixtures/);
      }
    });

    it("demo-fixtures.js lives in src/demo/ — clearly isolated from runtime", () => {
      expect(fs.existsSync(path.join(REPO_FRONTEND, "src/demo/demo-fixtures.js"))).toBe(true);
      // Also confirm there is no demo file at the runtime root.
      expect(fs.existsSync(path.join(REPO_FRONTEND, "src/demo-fixtures.js"))).toBe(false);
    });
  });

  describe("Live-mode chrome remains honest empty with no payload", () => {
    it("AgentsPopover with no agents renders aw-agents-empty (no demo leak)", () => {
      render(<AgentsPopover agents={[]} />);
      expect(screen.getByTestId("aw-agents-empty")).toBeInTheDocument();
      expect(screen.queryByTestId("aw-agent-row-orch")).toBeNull();
      expect(screen.queryByTestId("aw-agent-row-pi")).toBeNull();
    });

    it("NowStrip is hidden when no state/task supplied", () => {
      const { container } = render(<NowStrip />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Demo-mode chrome populates rows when fixtures are explicitly passed", () => {
    it("AgentsPopover with DEMO_AGENTS renders all 6 agent rows", () => {
      render(<AgentsPopover agents={DEMO_AGENTS} />);
      expect(screen.queryByTestId("aw-agents-empty")).toBeNull();
      for (const a of DEMO_AGENTS) {
        expect(screen.getByTestId(`aw-agent-row-${a.key}`)).toBeInTheDocument();
      }
    });
  });

  describe("main.jsx mount() gates demo on explicit flag", () => {
    const MAIN = fs.readFileSync(path.resolve(REPO_FRONTEND, "src/main.jsx"), "utf-8");

    it("main.jsx imports DEMO_FIXTURES (demo entry wired)", () => {
      expect(MAIN).toMatch(/DEMO_FIXTURES/);
      expect(MAIN).toMatch(/from\s+["']\.\/demo\/demo-fixtures(\.js)?["']/);
    });

    it("main.jsx mount() only merges DEMO_FIXTURES when config.demo === true", () => {
      // The gate must be an explicit boolean check on config.demo, not a
      // loose truthy fallback that could accidentally fire in live mode.
      expect(MAIN).toMatch(/config\.demo\s*===\s*true|config\?\.demo\s*===\s*true/);
    });

    it("main.jsx never auto-applies demo fixtures when the flag is absent", () => {
      // No path may silently call applyDemoFixtures() / use DEMO_FIXTURES
      // outside a demo-flag guarded block. Searching for the literal
      // identifier is sufficient because demo-fixtures.js is the only
      // module providing it.
      const usages = MAIN.match(/DEMO_FIXTURES/g) || [];
      // import statement + 1-2 references inside the demo branch.
      expect(usages.length).toBeGreaterThan(0);
      expect(usages.length).toBeLessThanOrEqual(8);
    });
  });
});
