import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  StepsTab,
  RecordedTab,
  CodeTab,
  TraceTab,
} from "../src/v4/secondary-tabs.jsx";

describe("v4 secondary tabs (real DOM render)", () => {
  it("StepsTab shows empty state and Run-all disabled with no steps", () => {
    render(<StepsTab pendingSteps={[]} />);
    expect(screen.getByTestId("steps-empty")).toBeInTheDocument();
    expect(screen.getByTestId("steps-run-all")).toBeDisabled();
  });

  it("StepsTab renders editor row, intent input, outcome chips, and attach button", () => {
    const onChangeIntent = vi.fn();
    const onChangeOutcome = vi.fn();
    const onAttach = vi.fn();
    render(
      <StepsTab
        pendingSteps={[{ id: "s1", intent: "click Get started" }]}
        onChangeIntent={onChangeIntent}
        onChangeExpectedOutcome={onChangeOutcome}
        onAttachElement={onAttach}
      />
    );
    expect(screen.getByTestId("step-row-s1")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("step-input-s1"), { target: { value: "click pricing card" } });
    expect(onChangeIntent).toHaveBeenCalledWith("s1", "click pricing card");
    fireEvent.click(screen.getByTestId("step-outcome-chip-navigation-s1"));
    expect(onChangeOutcome).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({ type: "navigation", source: "user" })
    );
    fireEvent.click(screen.getByTestId("step-attach-s1"));
    expect(onAttach).toHaveBeenCalledWith("s1");
  });

  it("StepsTab Run-all dispatches typed run_steps over all step ids", () => {
    const onRunAll = vi.fn();
    render(
      <StepsTab
        pendingSteps={[
          { id: "s1", intent: "first" },
          { id: "s2", intent: "second" },
        ]}
        onRunAll={onRunAll}
      />
    );
    fireEvent.click(screen.getByTestId("steps-run-all"));
    expect(onRunAll).toHaveBeenCalledWith(
      expect.objectContaining({ type: "run_steps", mode: "all", step_ids: ["s1", "s2"] })
    );
  });

  it("StepsTab Run-selected dispatches typed run_steps scoped to selected ids", () => {
    const onRunSelected = vi.fn();
    render(
      <StepsTab
        pendingSteps={[
          { id: "s1", intent: "one" },
          { id: "s2", intent: "two" },
          { id: "s3", intent: "three" },
        ]}
        selectedStepIds={["s1", "s3"]}
        onRunSelected={onRunSelected}
      />
    );
    const btn = screen.getByTestId("steps-run-selected");
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(onRunSelected).toHaveBeenCalledWith(
      expect.objectContaining({ type: "run_steps", mode: "selected", step_ids: ["s1", "s3"] })
    );
  });

  it("StepsTab uses stable step id for testids regardless of display order", () => {
    render(
      <StepsTab
        pendingSteps={[
          { id: "stp_zeta", intent: "first card" },
          { id: "stp_alpha", intent: "second card" },
        ]}
      />
    );
    expect(screen.getByTestId("step-row-stp_zeta")).toBeInTheDocument();
    expect(screen.getByTestId("step-row-stp_alpha")).toBeInTheDocument();
    expect(screen.getByTestId("step-input-stp_zeta")).toBeInTheDocument();
    expect(screen.getByTestId("step-input-stp_alpha")).toBeInTheDocument();
  });

  it("StepsTab Run-all disabled when blocked even with runnable steps", () => {
    const onRunAll = vi.fn();
    render(
      <StepsTab
        pendingSteps={[{ id: "s1", intent: "click" }]}
        onRunAll={onRunAll}
        blocked
        blockedReason="Run blocked while permission is pending"
      />
    );
    expect(screen.getByTestId("steps-run-all")).toBeDisabled();
    expect(screen.getByTestId("steps-blocked").textContent).toMatch(/permission/i);
    fireEvent.click(screen.getByTestId("steps-run-all"));
    expect(onRunAll).not.toHaveBeenCalled();
  });

  it("StepsTab renders malformed step row without crashing and never claims ready", () => {
    render(<StepsTab pendingSteps={[{ id: "stp_bad" }]} />);
    const row = screen.getByTestId("step-row-stp_bad");
    expect(row).toBeInTheDocument();
    const status = screen.getByTestId("step-status-stp_bad");
    expect(status.textContent.toLowerCase()).not.toContain("ready");
  });

  it("RecordedTab shows empty state when no recorded steps", () => {
    render(<RecordedTab recordedSteps={[]} />);
    expect(screen.getByTestId("recorded-empty")).toBeInTheDocument();
  });

  it("RecordedTab renders backend evidence including repaired diff", () => {
    render(
      <RecordedTab
        recordedSteps={[
          {
            step_id: "rec1",
            state: "recorded",
            description: "Verify hero",
            locator: 'getByRole("heading")',
            duration_ms: 412,
          },
          {
            step_id: "rec2",
            state: "repaired",
            description: "Pro price",
            repaired_from: "toHaveText('$49 / mo')",
            repaired_to: "toContainText('$49')",
            duration_ms: 622,
          },
          {
            step_id: "rec3",
            state: "skipped",
            description: "FAQ accordion",
          },
        ]}
      />
    );
    expect(screen.getByTestId("recorded-item-rec1")).toHaveAttribute("data-state", "recorded");
    expect(screen.getByTestId("recorded-item-rec2")).toHaveAttribute("data-state", "repaired");
    expect(screen.getByTestId("recorded-item-rec3")).toHaveAttribute("data-state", "skipped");
  });

  it("CodeTab shows awaiting-empty state and disables copy until code_update", () => {
    render(<CodeTab codePreview={null} />);
    expect(screen.getByTestId("code-empty")).toBeInTheDocument();
    expect(screen.getByTestId("code-copy")).toBeDisabled();
  });

  it("CodeTab renders backend code_update and enables copy/save", () => {
    const onCopy = vi.fn();
    render(
      <CodeTab
        codePreview={{ file: "tests/pricing.spec.ts", code: "test('x', () => {});" }}
        codeDiagnostics={[{ level: "warning", message: "fragile selector" }]}
        onCopy={onCopy}
      />
    );
    expect(screen.getByTestId("code-preview").textContent).toContain("test('x'");
    expect(screen.getByTestId("code-diagnostics")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("code-copy"));
    expect(onCopy).toHaveBeenCalledWith(expect.objectContaining({ type: "copy_code" }));
  });

  it("TraceTab renders empty state and known vs unknown event tagging", () => {
    const { rerender } = render(<TraceTab traceEntries={[]} />);
    expect(screen.getByTestId("trace-empty")).toBeInTheDocument();

    rerender(
      <TraceTab
        traceEntries={[
          { id: 1, type: "step.recorded", text: "stp_a1 recorded", timestamp: "11:42:00.000" },
          { id: 2, type: "totally_unknown_event", text: "wat", timestamp: "11:42:01.000" },
        ]}
      />
    );
    const known = screen.getByTestId("trace-row-0");
    const unknown = screen.getByTestId("trace-row-1");
    expect(known).toHaveAttribute("data-known", "1");
    expect(unknown).toHaveAttribute("data-known", "0");
  });
});
