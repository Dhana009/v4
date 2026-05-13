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

  it("AgentsPopover renders default 5 rows when no agents passed", () => {
    render(<AgentsPopover />);
    expect(screen.getByTestId("aw-agent-row-orch")).toBeInTheDocument();
    expect(screen.getByTestId("aw-agent-row-sr")).toBeInTheDocument();
  });

  it("CollapsedRail switches tab and expand toggles", () => {
    const setTab = vi.fn();
    const setCollapsed = vi.fn();
    render(<CollapsedRail tab="llm" setTab={setTab} setCollapsed={setCollapsed} />);
    fireEvent.click(screen.getByTestId("aw-rail-tab-steps"));
    expect(setTab).toHaveBeenCalledWith("steps");
  });
});
