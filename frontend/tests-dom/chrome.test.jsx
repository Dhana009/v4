import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  Header,
  TabStrip,
  NowStrip,
  Footer,
  AgentsPopover,
  CollapsedRail,
} from "../src/v4/chrome.jsx";

describe("v4 chrome (real DOM render)", () => {
  it("Header renders status pill with data-status reflecting connection", () => {
    render(<Header status="connected" />);
    expect(screen.getByTestId("aw-status-pill")).toHaveAttribute("data-status", "connected");
  });

  it("Header dock buttons dispatch setDock", () => {
    const setDock = vi.fn();
    render(<Header dock="right" setDock={setDock} />);
    fireEvent.click(screen.getByTestId("aw-dock-left"));
    expect(setDock).toHaveBeenCalledWith("left");
  });

  it("TabStrip switches tabs", () => {
    const setTab = vi.fn();
    render(<TabStrip tab="llm" setTab={setTab} counts={{ steps: 3 }} />);
    fireEvent.click(screen.getByTestId("aw-tab-steps"));
    expect(setTab).toHaveBeenCalledWith("steps");
  });

  it("NowStrip is hidden when no state/task", () => {
    const { container } = render(<NowStrip />);
    expect(container.firstChild).toBeNull();
  });

  it("NowStrip primary button dispatches onPrimary", () => {
    const onPrimary = vi.fn();
    render(<NowStrip state="Confirm to run" task="Plan ready" primaryLabel="Confirm & run" onPrimary={onPrimary} />);
    fireEvent.click(screen.getByTestId("aw-now-primary"));
    expect(onPrimary).toHaveBeenCalled();
  });

  it("Footer renders phase and blocker when present", () => {
    render(<Footer phase="Recovery needed" event="step failed" blocker="needs recovery" />);
    expect(screen.getByTestId("aw-footer-blocker")).toBeInTheDocument();
  });

  it("AgentsPopover renders honest empty state when no agents payload (D-106)", () => {
    render(<AgentsPopover />);
    expect(screen.getByTestId("aw-agents-popover")).toBeInTheDocument();
    expect(screen.getByTestId("aw-agents-empty")).toBeInTheDocument();
    expect(screen.getByTestId("aw-agents-sprint8-badge")).toBeInTheDocument();
    // No mock/default rows leak in
    expect(screen.queryByTestId("aw-agent-row-orch")).toBeNull();
    expect(screen.queryByTestId("aw-agent-row-sr")).toBeNull();
    expect(screen.queryByTestId("aw-agent-row-pi")).toBeNull();
  });

  it("AgentsPopover renders empty state for empty array (D-106)", () => {
    render(<AgentsPopover agents={[]} />);
    expect(screen.getByTestId("aw-agents-empty")).toBeInTheDocument();
  });

  it("AgentsPopover renders rows only from injected backend payload (D-106)", () => {
    const agents = [
      { key: "orch", name: "Main Orchestrator", initials: "MO", model: "live", status: "running", last: "tick", required: true },
      { key: "pi", name: "Page Intelligence", initials: "PI", model: "live", status: "standby", last: "—", required: false },
    ];
    render(<AgentsPopover agents={agents} />);
    expect(screen.queryByTestId("aw-agents-empty")).toBeNull();
    expect(screen.getByTestId("aw-agent-row-orch")).toBeInTheDocument();
    expect(screen.getByTestId("aw-agent-row-pi")).toBeInTheDocument();
    // Mock-default rows that are NOT in payload must not appear
    expect(screen.queryByTestId("aw-agent-row-sr")).toBeNull();
    expect(screen.queryByTestId("aw-agent-row-dbg")).toBeNull();
    expect(screen.queryByTestId("aw-agent-row-cg")).toBeNull();
  });

  it("AgentsPopover non-required toggle is disabled with Sprint 8 reason (D-106)", () => {
    const agents = [
      { key: "pi", name: "Page Intelligence", initials: "PI", model: "—", status: "standby", last: "—", required: false },
    ];
    render(<AgentsPopover agents={agents} />);
    const toggle = screen.getByTestId("aw-agent-toggle-pi");
    expect(toggle).toBeDisabled();
    expect(toggle.getAttribute("title") || "").toMatch(/BUG-S8-AGENT-001/);
  });

  it("AgentsPopover disabled toggle click does not dispatch (D-106)", () => {
    const agents = [
      { key: "pi", name: "Page Intelligence", initials: "PI", model: "—", status: "standby", last: "—", required: false },
    ];
    const sendPayload = vi.fn();
    render(<AgentsPopover agents={agents} sendPayload={sendPayload} />);
    fireEvent.click(screen.getByTestId("aw-agent-toggle-pi"));
    expect(sendPayload).not.toHaveBeenCalled();
  });

  it("DEFAULT_AGENTS is not exported from chrome module (D-106)", async () => {
    const mod = await import("../src/v4/chrome.jsx");
    expect(mod.DEFAULT_AGENTS).toBeUndefined();
  });

  it("CollapsedRail switches tab and expand toggles", () => {
    const setTab = vi.fn();
    const setCollapsed = vi.fn();
    render(<CollapsedRail tab="llm" setTab={setTab} setCollapsed={setCollapsed} />);
    fireEvent.click(screen.getByTestId("aw-rail-tab-steps"));
    expect(setTab).toHaveBeenCalledWith("steps");
  });
});

describe("v4 Header mode toggle (D-105 Manual Mode disabled)", () => {
  it("renders LLM/Manual mode toggle group", () => {
    render(<Header />);
    expect(screen.getByTestId("aw-mode-toggle")).toBeInTheDocument();
    expect(screen.getByTestId("aw-mode-llm")).toBeInTheDocument();
    expect(screen.getByTestId("aw-mode-manual")).toBeInTheDocument();
  });

  it("Manual option is disabled with aria-disabled and disabled attribute", () => {
    render(<Header />);
    const manual = screen.getByTestId("aw-mode-manual");
    expect(manual).toBeDisabled();
    expect(manual).toHaveAttribute("aria-disabled", "true");
    expect(manual).toHaveAttribute("aria-pressed", "false");
  });

  it("Manual option title cites Sprint 8 and references the D-105 ticket", () => {
    render(<Header />);
    const manual = screen.getByTestId("aw-mode-manual");
    const title = manual.getAttribute("title") || "";
    expect(title).toMatch(/Sprint 8/);
    expect(title).toMatch(/Manual Mode/);
    expect(title).toMatch(/D-105|BUG-S8-MANUAL-001/);
  });

  it("clicking disabled Manual does not dispatch any command and does not toggle pressed state", () => {
    // Sniff: Header receives no dispatcher prop; we assert the click event is
    // suppressed by the disabled attribute (no state change observable).
    // The disabled button must not call any handler — there is no onClick wired,
    // and any future wiring is blocked by `disabled` semantics. We additionally
    // verify aria-pressed stays "false" after a click.
    render(<Header />);
    const manual = screen.getByTestId("aw-mode-manual");
    fireEvent.click(manual);
    expect(manual).toHaveAttribute("aria-pressed", "false");
    // LLM stays the active option after the no-op click.
    expect(screen.getByTestId("aw-mode-llm")).toHaveAttribute("aria-pressed", "true");
  });

  it("LLM option is active, non-disabled, and remains selectable", () => {
    render(<Header />);
    const llm = screen.getByTestId("aw-mode-llm");
    expect(llm).not.toBeDisabled();
    expect(llm).toHaveAttribute("aria-pressed", "true");
    // No exception on interaction.
    fireEvent.click(llm);
    expect(llm).toHaveAttribute("aria-pressed", "true");
  });

  it("no manual-mode builder testids leak into the Header render", () => {
    render(<Header />);
    expect(screen.queryByTestId("manual-mode-checkbox")).toBeNull();
    expect(screen.queryByTestId("manual-action-builder")).toBeNull();
    expect(screen.queryByTestId("manual-assertion-builder")).toBeNull();
  });
});
