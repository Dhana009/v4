// FE-REF-002: Re-port shell chrome from yui (1)/ ROOT visual reference.
//
// These tests pin the ROOT-derived visual structure of <Header>, <TabStrip>,
// <NowStrip>, <Footer>, <AgentsPopover>, and <CollapsedRail> while preserving
// the backend-driven live-mode contract:
//
//   - Backend remains runtime truth.
//   - Frontend renders backend props only.
//   - No fabricated agents/steps/code/trace data.
//   - NowStrip CTA labels come from props, not local lifecycle invention.
//
// Source of design truth: yui (1)/chrome.jsx ROOT + AutoWorkbench.html.
// NOT yui (1)/v4/ (older checkpoint).

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";

import {
  Header,
  TabStrip,
  NowStrip,
  Footer,
  AgentsPopover,
  CollapsedRail,
} from "../src/v4/chrome.jsx";

describe("FE-REF-002 shell chrome ROOT re-port", () => {
  describe("Header shell structure (yui ROOT)", () => {
    it("renders the ROOT shell parts: brand, status pill, mode switch, agents, page pill, token pill, dock trigger, collapse", () => {
      render(
        <Header
          status="connected"
          dock="right"
          tokenInfo={{ tok: "8.4k", cost: "0.12" }}
          runState="run_a91b"
          agentsSummary={["on", "on", "off"]}
          pageUrl="acme.dev/pricing"
        />,
      );
      const header = screen.getByTestId("aw-header");
      expect(header).toBeInTheDocument();
      expect(within(header).getByText("AutoWorkbench")).toBeInTheDocument();
      expect(screen.getByTestId("aw-status-pill")).toBeInTheDocument();
      expect(screen.getByTestId("aw-mode-toggle")).toBeInTheDocument();
      expect(screen.getByTestId("aw-agents-toggle")).toBeInTheDocument();
      expect(screen.getByTestId("aw-run-pill")).toBeInTheDocument();
      expect(screen.getByTestId("aw-dock-toggle")).toBeInTheDocument();
      expect(screen.getByTestId("aw-collapse")).toBeInTheDocument();
      expect(screen.getByTestId("aw-settings")).toBeInTheDocument();
    });

    it("uses ROOT class names (aw-mode-switch, aw-token-pill, aw-dock-wrap, aw-brand-divider)", () => {
      const { container } = render(<Header tokenInfo={{ tok: "0", cost: "0.00" }} />);
      expect(container.querySelector(".aw-mode-switch")).not.toBeNull();
      expect(container.querySelector(".aw-token-pill")).not.toBeNull();
      expect(container.querySelector(".aw-dock-wrap")).not.toBeNull();
      expect(container.querySelector(".aw-brand-divider")).not.toBeNull();
    });

    it("dock dropdown opens on click and reveals four dock options + collapse option (ROOT pattern)", () => {
      const setDock = vi.fn();
      const setCollapsed = vi.fn();
      render(<Header dock="right" setDock={setDock} setCollapsed={setCollapsed} />);
      fireEvent.click(screen.getByTestId("aw-dock-toggle"));
      // Portal renders to document.body; query via screen.
      expect(screen.getByTestId("aw-dock-right")).toBeInTheDocument();
      expect(screen.getByTestId("aw-dock-left")).toBeInTheDocument();
      expect(screen.getByTestId("aw-dock-top")).toBeInTheDocument();
      expect(screen.getByTestId("aw-dock-float")).toBeInTheDocument();
      expect(screen.getByTestId("aw-dock-collapse")).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("aw-dock-left"));
      expect(setDock).toHaveBeenCalledWith("left");
    });

    it("dock menu collapse option toggles collapsed via setCollapsed", () => {
      const setCollapsed = vi.fn();
      render(<Header dock="right" collapsed={false} setCollapsed={setCollapsed} />);
      fireEvent.click(screen.getByTestId("aw-dock-toggle"));
      fireEvent.click(screen.getByTestId("aw-dock-collapse"));
      expect(setCollapsed).toHaveBeenCalledWith(true);
    });

    it("settings button posts __activate_edit_mode to window (ROOT tweaks hook)", () => {
      const spy = vi.spyOn(window, "postMessage");
      render(<Header />);
      fireEvent.click(screen.getByTestId("aw-settings"));
      expect(spy).toHaveBeenCalledWith({ type: "__activate_edit_mode" }, "*");
      spy.mockRestore();
    });

    it("Manual mode button stays disabled with explicit sprint-8 reason (backend-truth, not visual regression)", () => {
      render(<Header />);
      const manual = screen.getByTestId("aw-mode-manual");
      expect(manual).toBeDisabled();
      expect(manual).toHaveAttribute("data-disabled-reason", "sprint-8");
    });

    it("renders honest empty placeholder for agents when payload empty (BUG-S8-AGENT-001)", () => {
      render(<Header agentsSummary={[]} />);
      expect(screen.getByTestId("aw-agents-setup")).toBeInTheDocument();
      expect(screen.queryByTestId("aw-agents-dots")).toBeNull();
    });

    it("renders dots only when backend supplies agentsSummary (no fabrication)", () => {
      render(<Header agentsSummary={["on", "off", "run"]} />);
      expect(screen.getByTestId("aw-agents-dots")).toBeInTheDocument();
      expect(screen.queryByTestId("aw-agents-setup")).toBeNull();
    });

    it("page-url pill falls back to '—' when pageUrl missing (no fabricated acme.dev)", () => {
      const { container } = render(<Header pageUrl="" />);
      const shrinkable = container.querySelector(".aw-status-pill.shrinkable");
      expect(shrinkable).not.toBeNull();
      expect(shrinkable.textContent).toContain("—");
      expect(shrinkable.textContent.toLowerCase()).not.toContain("acme.dev");
    });
  });

  describe("TabStrip ROOT structure", () => {
    it("renders the 5 ROOT tabs in order (llm/steps/rec/code/trace)", () => {
      render(<TabStrip tab="llm" setTab={() => {}} counts={{}} />);
      const tabs = screen.getAllByRole("tab");
      expect(tabs).toHaveLength(5);
      expect(tabs[0]).toHaveAttribute("data-testid", "aw-tab-llm");
      expect(tabs[1]).toHaveAttribute("data-testid", "aw-tab-steps");
      expect(tabs[2]).toHaveAttribute("data-testid", "aw-tab-rec");
      expect(tabs[3]).toHaveAttribute("data-testid", "aw-tab-code");
      expect(tabs[4]).toHaveAttribute("data-testid", "aw-tab-trace");
    });

    it("badge shown when counts > 0; absent when count is null/undefined", () => {
      render(<TabStrip tab="llm" setTab={() => {}} counts={{ steps: 5, rec: null, trace: undefined }} />);
      const steps = screen.getByTestId("aw-tab-steps");
      expect(within(steps).getByText("5")).toBeInTheDocument();
      const rec = screen.getByTestId("aw-tab-rec");
      expect(within(rec).queryByText("0")).toBeNull();
    });
  });

  describe("NowStrip CTA derived from props, not local lifecycle invention", () => {
    it("primary button label is the prop string verbatim", () => {
      render(
        <NowStrip
          kind="decide"
          state="Decision required"
          task="Confirm plan v2"
          primaryLabel="Confirm & run"
        />,
      );
      const btn = screen.getByTestId("aw-now-primary");
      expect(btn).toHaveTextContent("Confirm & run");
    });

    it("no primary button when primaryLabel is absent", () => {
      render(<NowStrip kind="idle" state="Idle" task="—" />);
      expect(screen.queryByTestId("aw-now-primary")).toBeNull();
    });

    it("kind class applied to root for accent rail", () => {
      const { container } = render(<NowStrip kind="block" state="Blocked" task="Locator ambiguous" />);
      expect(container.firstChild).toHaveClass("aw-now");
      expect(container.firstChild).toHaveClass("block");
    });
  });

  describe("Footer renders from props only", () => {
    it("falls back to 'Idle' / '—' defaults instead of inventing lifecycle truth", () => {
      render(<Footer />);
      const footer = screen.getByTestId("aw-footer");
      expect(footer).toHaveTextContent("Idle");
      expect(footer).toHaveTextContent("—");
    });

    it("renders busy bar only when prop busy=true", () => {
      const { container, rerender } = render(<Footer phase="Idle" event="—" />);
      expect(container.querySelector(".aw-bar")).toBeNull();
      rerender(<Footer phase="Executing" event="step 1" busy={true} />);
      expect(container.querySelector(".aw-bar")).not.toBeNull();
    });
  });

  describe("AgentsPopover live-mode contract preserved", () => {
    it("honest empty when no agents payload (no DEFAULT_AGENTS regression)", () => {
      render(<AgentsPopover agents={[]} />);
      expect(screen.getByTestId("aw-agents-empty")).toBeInTheDocument();
      expect(screen.queryByTestId("aw-agent-row-orch")).toBeNull();
    });

    it("renders rows from prop payload only", () => {
      const agents = [
        { key: "orch", name: "Main Orchestrator", initials: "MO", model: "x", status: "active", last: "ok", required: true },
        { key: "pi", name: "Page Intelligence", initials: "PI", model: "y", status: "standby", last: "idle" },
      ];
      render(<AgentsPopover agents={agents} />);
      expect(screen.getByTestId("aw-agent-row-orch")).toBeInTheDocument();
      expect(screen.getByTestId("aw-agent-row-pi")).toBeInTheDocument();
    });
  });

  describe("CollapsedRail ROOT structure", () => {
    it("renders 5 rail tabs + expand button (collapsed dock-mode shell)", () => {
      render(<CollapsedRail tab="llm" setTab={() => {}} setCollapsed={() => {}} />);
      expect(screen.getByTestId("aw-collapsed-rail")).toBeInTheDocument();
      for (const id of ["llm", "steps", "rec", "code", "trace"]) {
        expect(screen.getByTestId(`aw-rail-tab-${id}`)).toBeInTheDocument();
      }
    });
  });

  describe("source guard — no `yui (1)/v4/` reference baked into chrome", () => {
    it("chrome.jsx text does not name yui v4 as a design source", async () => {
      // Static guard already enforced by static-audit.test.jsx for all
      // PRODUCTION_SOURCES; this is the focused per-file restatement.
      const { readFileSync } = await import("node:fs");
      const { resolve } = await import("node:path");
      const src = readFileSync(resolve(__dirname, "../src/v4/chrome.jsx"), "utf-8");
      expect(src).not.toMatch(/yui[^\n]*\(1\)[^\n]*\/v4|yui\/v4/);
    });
  });
});
