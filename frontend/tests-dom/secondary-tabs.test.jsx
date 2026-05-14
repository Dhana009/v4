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

  // Pass 4b-1 — backend-driven locator strength chip
  it("StepsTab does not render locator chip when backend has not classified", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "click Submit" }]} />);
    expect(screen.queryByTestId("step-locator-s1")).toBeNull();
  });

  it("StepsTab renders strong locator chip from step.locator_kind payload", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s1",
            intent: "click Submit",
            locator_kind: "ok",
            locator_strength: "strong",
            locator_reason: "uses data-testid",
          },
        ]}
      />
    );
    const chip = screen.getByTestId("step-locator-s1");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute("data-kind", "ok");
    expect(chip).toHaveAttribute("data-strength", "strong");
    expect(chip.textContent.toLowerCase()).toContain("strong");
    expect(chip.textContent.toLowerCase()).toContain("data-testid");
  });

  it("StepsTab renders weak locator chip with backend reason from element_info", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s2",
            intent: "click 2nd card",
            element_info: {
              tag: "div",
              locator_kind: "warn",
              locator_strength: "weak",
              locator_reason: "no strong identifier — relies on class / tag",
            },
          },
        ]}
      />
    );
    const chip = screen.getByTestId("step-locator-s2");
    expect(chip).toHaveAttribute("data-kind", "warn");
    expect(chip).toHaveAttribute("data-strength", "weak");
    expect(chip.textContent.toLowerCase()).toContain("weak");
    expect(chip.textContent.toLowerCase()).toContain("class / tag");
  });

  it("StepsTab renders medium locator chip without claiming strong/weak", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s3",
            intent: "click Sign in",
            locator_kind: "med",
            locator_strength: "medium",
            locator_reason: "uses accessible label / role",
          },
        ]}
      />
    );
    const chip = screen.getByTestId("step-locator-s3");
    expect(chip).toHaveAttribute("data-kind", "med");
    const txt = chip.textContent.toLowerCase();
    expect(txt).toContain("medium");
    expect(txt).not.toContain("strong locator");
    expect(txt).not.toContain("weak locator");
  });

  it("StepsTab tolerates malformed locator metadata without claiming success", () => {
    render(
      <StepsTab
        pendingSteps={[
          { id: "s4", intent: "click", locator_kind: "garbage_value", locator_strength: 42 },
        ]}
      />
    );
    const chip = screen.getByTestId("step-locator-s4");
    expect(chip).toHaveAttribute("data-kind", "garbage_value");
    // Strength=42 falls through to "locator unknown".
    expect(chip.textContent.toLowerCase()).toContain("unknown");
  });

  // Pass 4b-2 — backend-driven step kind chip
  it("StepsTab does not render kind chip when backend has not classified", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "click Submit" }]} />);
    expect(screen.queryByTestId("step-kind-s1")).toBeNull();
  });

  it("StepsTab renders atomic kind chip from step_kind payload", () => {
    render(
      <StepsTab
        pendingSteps={[{ id: "s1", intent: "click Submit", step_kind: "atomic" }]}
      />
    );
    const chip = screen.getByTestId("step-kind-s1");
    expect(chip).toHaveAttribute("data-kind", "atomic");
    expect(chip.textContent.toLowerCase()).toContain("atomic");
  });

  it("StepsTab renders loop kind chip from step_kind payload", () => {
    render(
      <StepsTab
        pendingSteps={[{ id: "s2", intent: "Each pricing card", step_kind: "loop" }]}
      />
    );
    const chip = screen.getByTestId("step-kind-s2");
    expect(chip).toHaveAttribute("data-kind", "loop");
    expect(chip.textContent.toLowerCase()).toContain("loop");
  });

  it("StepsTab renders section kind chip from step_kind payload", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s3",
            intent: "Section: Pricing grid",
            step_kind: "section",
            children: [{ description: "a" }, { description: "b" }],
          },
        ]}
      />
    );
    const chip = screen.getByTestId("step-kind-s3");
    expect(chip).toHaveAttribute("data-kind", "section");
    expect(chip.textContent.toLowerCase()).toContain("section");
  });

  it("StepsTab normalizes malformed step_kind to unknown without crashing", () => {
    render(
      <StepsTab
        pendingSteps={[{ id: "s4", intent: "click", step_kind: "garbage_value" }]}
      />
    );
    const chip = screen.getByTestId("step-kind-s4");
    // Original raw value preserved for trace/debug, but data-kind clamped to unknown.
    expect(chip).toHaveAttribute("data-kind", "unknown");
    expect(chip).toHaveAttribute("data-raw-kind", "garbage_value");
    expect(chip.textContent.toLowerCase()).toContain("unknown");
  });

  it("StepsTab renders locator chip and kind chip together without breaking either", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s5",
            intent: "click Submit",
            step_kind: "atomic",
            locator_kind: "ok",
            locator_strength: "strong",
            locator_reason: "uses data-testid",
          },
        ]}
      />
    );
    expect(screen.getByTestId("step-locator-s5")).toHaveAttribute("data-strength", "strong");
    expect(screen.getByTestId("step-kind-s5")).toHaveAttribute("data-kind", "atomic");
  });

  // Pass 4b-3 — backend-driven section child-op list
  it("StepsTab does not render children list when step has no children payload", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "click" }]} />);
    expect(screen.queryByTestId("step-children-s1")).toBeNull();
  });

  it("StepsTab does not render children list when children is empty array", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "section", children: [] }]} />);
    expect(screen.queryByTestId("step-children-s1")).toBeNull();
  });

  it("StepsTab renders section child operations from backend payload with stable child_ids", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "sect",
            intent: "Section: Pricing grid",
            step_kind: "section",
            children: [
              { child_id: "op_a", type: "click", description: "click Pro card" },
              { child_id: "op_b", type: "assert", description: "verify price" },
              { child_id: "op_c", type: "click", description: "click CTA" },
            ],
          },
        ]}
      />
    );
    const list = screen.getByTestId("step-children-sect");
    expect(list).toBeInTheDocument();
    expect(list).toHaveAttribute("data-count", "3");
    expect(screen.getByTestId("step-child-sect-op_a")).toHaveAttribute("data-op-type", "click");
    expect(screen.getByTestId("step-child-label-sect-op_a").textContent).toContain("click Pro card");
    expect(screen.getByTestId("step-child-sect-op_b")).toHaveAttribute("data-op-type", "assert");
    expect(screen.getByTestId("step-child-label-sect-op_c").textContent).toContain("click CTA");
  });

  it("StepsTab child status renders only when payload provides status", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "sect",
            children: [
              { child_id: "a", type: "click", description: "first", status: "recorded" },
              { child_id: "b", type: "click", description: "second" },
            ],
          },
        ]}
      />
    );
    const aStatus = screen.getByTestId("step-child-status-sect-a");
    expect(aStatus).toHaveAttribute("data-status", "recorded");
    expect(aStatus.textContent).toContain("recorded");
    expect(screen.queryByTestId("step-child-status-sect-b")).toBeNull();
  });

  it("StepsTab uses safe fallback child_id when backend omits it", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "sect",
            children: [
              { type: "click", description: "no id child" },
              { type: "assert", description: "also no id" },
            ],
          },
        ]}
      />
    );
    const list = screen.getByTestId("step-children-sect");
    expect(list).toHaveAttribute("data-count", "2");
    // Frontend falls back to op_1, op_2 when child_id missing.
    expect(screen.getByTestId("step-child-sect-op_1")).toBeInTheDocument();
    expect(screen.getByTestId("step-child-sect-op_2")).toBeInTheDocument();
  });

  it("StepsTab drops malformed (non-dict) child entries without crashing", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "sect",
            children: [null, 42, "bad", { child_id: "good", description: "real op" }],
          },
        ]}
      />
    );
    const list = screen.getByTestId("step-children-sect");
    // Only the one valid dict child renders.
    expect(list).toHaveAttribute("data-count", "1");
    expect(screen.getByTestId("step-child-sect-good")).toBeInTheDocument();
  });

  it("StepsTab tolerates non-array children payload by rendering nothing", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", children: "not a list" }]} />);
    expect(screen.queryByTestId("step-children-s1")).toBeNull();
  });

  it("StepsTab renders locator chip, kind chip, and children list together", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "sect",
            intent: "Section: Pricing",
            step_kind: "section",
            locator_kind: "ok",
            locator_strength: "strong",
            locator_reason: "uses data-testid",
            children: [
              { child_id: "c1", description: "first op" },
              { child_id: "c2", description: "second op" },
            ],
          },
        ]}
      />
    );
    expect(screen.getByTestId("step-locator-sect")).toHaveAttribute("data-strength", "strong");
    expect(screen.getByTestId("step-kind-sect")).toHaveAttribute("data-kind", "section");
    expect(screen.getByTestId("step-children-sect")).toHaveAttribute("data-count", "2");
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
