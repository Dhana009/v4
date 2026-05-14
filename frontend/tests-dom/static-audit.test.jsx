// D-108: Static mock-data gating guard.
//
// Asserts that production runtime source does NOT carry fake step/recorded/
// code/trace/agent data, and that rendering the main v4 tabs with an empty
// store produces honest empty states (no fabricated rows). Mirrors the audit
// in .tasks-md/Audit/S7_MOCK_AUDIT_FINDINGS.md.
//
// This test exists to prevent regression: if a future change introduces a
// `SAMPLE_STEPS`, `MOCK_PLAN`, `FAKE_RECORDED`, etc. into the production
// render path, or seeds the reducer with non-empty defaults, the suite fails
// here with a precise message.

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";

import { createInitialState } from "../src/store/reducer.js";
import { StepsTab, RecordedTab, CodeTab, TraceTab } from "../src/v4/secondary-tabs.jsx";
import { AgentsPopover } from "../src/v4/chrome.jsx";

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

// Identifiers that would indicate fake runtime data embedded in production
// source. DEFAULT_AGENTS was removed in D-106 — guard against it returning.
// (Note: legitimate UI/layout defaults like DEFAULT_CONFIG, DEFAULT_DOCK_MODE,
// DEFAULT_PANEL_MODE are explicitly excluded — those are not runtime data.)
const FORBIDDEN_IDENTIFIERS = [
  "DEFAULT_AGENTS",
  "SAMPLE_STEPS",
  "SAMPLE_PLAN",
  "SAMPLE_RECORDED",
  "SAMPLE_CODE",
  "SAMPLE_TRACE",
  "MOCK_PLAN",
  "MOCK_STEPS",
  "MOCK_RECORDED",
  "MOCK_AGENTS",
  "MOCK_TRACE",
  "FAKE_PLAN",
  "FAKE_STEPS",
  "FAKE_RECORDED",
  "FAKE_AGENTS",
  "FAKE_TRACE",
  "DEMO_PLAN",
  "DEMO_STEPS",
  "DEMO_AGENTS",
  "PROTOTYPE_PLAN",
  "PROTOTYPE_STEPS",
];

function readSrc(rel) {
  return fs.readFileSync(path.join(REPO_FRONTEND, rel), "utf-8");
}

describe("D-108 static mock-data gating audit", () => {
  describe("source-pattern guards", () => {
    for (const rel of PRODUCTION_SOURCES) {
      for (const ident of FORBIDDEN_IDENTIFIERS) {
        it(`${rel} does not declare or reference ${ident}`, () => {
          const src = readSrc(rel);
          // Word-boundary match: prevents catching e.g. NON_MOCK_FOO inside a longer name.
          const re = new RegExp(`\\b${ident}\\b`);
          // A single audit-trail comment about removal is allowed (chrome.jsx
          // documents the absence of DEFAULT_AGENTS). Strip line comments
          // before testing to avoid coupling to comment wording.
          const codeOnly = src
            .split("\n")
            .map((line) => line.replace(/\/\/.*$/, ""))
            .join("\n");
          expect(codeOnly).not.toMatch(re);
        });
      }
    }

    it("no production source uses `|| DEFAULT_AGENTS` or `?? DEFAULT_AGENTS` fallback", () => {
      for (const rel of PRODUCTION_SOURCES) {
        const src = readSrc(rel);
        expect(src).not.toMatch(/\|\|\s*DEFAULT_AGENTS/);
        expect(src).not.toMatch(/\?\?\s*DEFAULT_AGENTS/);
      }
    });

    // Regression R2 (post-D-108): a useMemo synthesized a fake agents array
    // from runtime phase, bypassing the identifier-name guards above.
    // Scan for hardcoded length>2 arrays of dot-state literals
    // (["on"|"off"|"run"]) in production runtime sources.
    it("no production source declares a hardcoded ['on'/'off'/'run'] array of length > 2", () => {
      for (const rel of PRODUCTION_SOURCES) {
        const src = readSrc(rel);
        const codeOnly = src
          .split("\n")
          .map((line) => line.replace(/\/\/.*$/, ""))
          .join("\n")
          .replace(/\/\*[\s\S]*?\*\//g, "");
        // Match arrays with 3+ string literals all in {on,off,run}
        const arrayRe =
          /\[\s*(?:"(?:on|off|run)"|'(?:on|off|run)')\s*(?:,\s*(?:"(?:on|off|run)"|'(?:on|off|run)')\s*){2,}\]/g;
        const matches = codeOnly.match(arrayRe);
        expect(matches, `${rel} contains fabricated agent dot array: ${matches?.[0]}`).toBeNull();
      }
    });

    // Even stricter: catch the original useMemo phase-fabrication pattern.
    it("aw-ide-panel.jsx does not synthesize agentsSummary from phase", () => {
      const src = readSrc("aw-ide-panel.jsx");
      // No ternary on phase that yields a dot-state literal
      expect(src).not.toMatch(/phase\s*===\s*["']planning["']\s*\?\s*["']run["']/);
      expect(src).not.toMatch(/phase\s*===\s*["']executing["']\s*\?\s*["']run["']/);
      expect(src).not.toMatch(/phase\s*===\s*["']recovery["']\s*\?\s*["']on["']/);
    });
  });

  describe("reducer initial state is honest empty", () => {
    const s = createInitialState();

    it("plan is null", () => expect(s.plan).toBeNull());
    it("pending_steps is empty array", () => {
      expect(Array.isArray(s.pending_steps)).toBe(true);
      expect(s.pending_steps).toHaveLength(0);
    });
    it("recorded_steps is empty array", () => {
      expect(Array.isArray(s.recorded_steps)).toBe(true);
      expect(s.recorded_steps).toHaveLength(0);
    });
    it("code_preview is null", () => expect(s.code_preview).toBeNull());
    it("trace_entries is empty array", () => {
      expect(Array.isArray(s.trace_entries)).toBe(true);
      expect(s.trace_entries).toHaveLength(0);
    });
    it("pending_recommendations is empty array", () => {
      expect(Array.isArray(s.pending_recommendations)).toBe(true);
      expect(s.pending_recommendations).toHaveLength(0);
    });
    it("does not declare any `agents` seed field", () => {
      // Agents arrive via storeState only; reducer does not seed a default
      // list. If a future change adds a non-empty default it must be either
      // null/[] — never fabricated entries.
      if ("agents" in s) {
        expect(Array.isArray(s.agents) ? s.agents : []).toHaveLength(0);
      }
    });
  });

  describe("tabs render honest empty state, not fabricated rows", () => {
    it("StepsTab with empty store renders steps-empty marker", () => {
      render(<StepsTab pendingSteps={[]} />);
      expect(screen.getByTestId("steps-empty")).toBeInTheDocument();
      // No fabricated step rows.
      expect(screen.queryAllByTestId(/^step-row-/).length).toBe(0);
    });

    it("RecordedTab with empty store renders recorded-empty marker", () => {
      render(<RecordedTab recordedSteps={[]} />);
      expect(screen.getByTestId("recorded-empty")).toBeInTheDocument();
      expect(screen.queryAllByTestId(/^recorded-row-/).length).toBe(0);
    });

    it("CodeTab with no payload renders code-empty marker", () => {
      render(<CodeTab codePreview={null} />);
      expect(screen.getByTestId("code-empty")).toBeInTheDocument();
    });

    it("TraceTab with empty store renders trace-empty marker", () => {
      render(<TraceTab traceEntries={[]} />);
      expect(screen.getByTestId("trace-empty")).toBeInTheDocument();
      expect(screen.queryAllByTestId(/^trace-row-/).length).toBe(0);
    });

    it("AgentsPopover with empty agents renders aw-agents-empty, no agent rows", () => {
      render(<AgentsPopover agents={[]} onClose={() => {}} />);
      expect(screen.getByTestId("aw-agents-empty")).toBeInTheDocument();
      expect(screen.queryAllByTestId(/^aw-agent-row-/).length).toBe(0);
    });
  });
});
