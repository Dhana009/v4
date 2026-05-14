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

  // Pass 4b-4 — backend-driven blocked step strip
  it("StepsTab does not render blocked strip when step has no blocked payload", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "click" }]} />);
    expect(screen.queryByTestId("step-blocked-s1")).toBeNull();
  });

  it("StepsTab renders blocked strip with reason and message from payload", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s1",
            intent: "fill salary form",
            blocked: {
              reason: "missing_data",
              message: "salaries.csv not uploaded",
              refs: ["salaries.csv"],
              action_label: "Upload now",
            },
          },
        ]}
      />
    );
    const strip = screen.getByTestId("step-blocked-s1");
    expect(strip).toHaveAttribute("data-reason", "missing_data");
    expect(screen.getByTestId("step-blocked-reason-s1").textContent).toContain("missing data");
    expect(screen.getByTestId("step-blocked-reason-s1").textContent).toContain("salaries.csv not uploaded");
    expect(screen.getByTestId("step-blocked-ref-s1-salaries.csv")).toBeInTheDocument();
    const action = screen.getByTestId("step-blocked-action-s1");
    expect(action).toBeDisabled();
    expect(action).toHaveAttribute("title", expect.stringMatching(/not yet wired/i));
  });

  it("StepsTab clamps invalid blocked reason to unknown but preserves raw value", () => {
    render(
      <StepsTab
        pendingSteps={[
          { id: "s2", blocked: { reason: "totally_bogus" } },
        ]}
      />
    );
    const strip = screen.getByTestId("step-blocked-s2");
    expect(strip).toHaveAttribute("data-reason", "unknown");
    expect(strip).toHaveAttribute("data-raw-reason", "totally_bogus");
  });

  it("StepsTab ignores malformed blocked value (string) without crashing", () => {
    render(<StepsTab pendingSteps={[{ id: "s3", blocked: "not a dict" }]} />);
    expect(screen.queryByTestId("step-blocked-s3")).toBeNull();
  });

  it("StepsTab blocked step status badge reads 'blocked', never 'ready'", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s4",
            intent: "click Sign in",
            expected_outcome: { type: "navigation" },
            blocked: { reason: "missing_data" },
          },
        ]}
      />
    );
    const status = screen.getByTestId("step-status-s4");
    expect(status.textContent.toLowerCase()).toContain("blocked");
    expect(status.textContent.toLowerCase()).not.toContain("ready");
  });

  it("StepsTab blocked strip carries refs as separate testid rows", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s5",
            blocked: {
              reason: "missing_data",
              refs: ["users.json", { id: "doc-1", name: "policy.pdf" }],
            },
          },
        ]}
      />
    );
    expect(screen.getByTestId("step-blocked-ref-s5-users.json")).toBeInTheDocument();
    expect(screen.getByTestId("step-blocked-ref-s5-doc-1")).toBeInTheDocument();
  });

  // Pass 4b-5 — backend-driven precondition strip
  it("StepsTab does not render precondition strip without payload", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "click" }]} />);
    expect(screen.queryByTestId("step-precondition-s1")).toBeNull();
  });

  it("StepsTab does not render precondition strip when status=passed", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s1",
            precondition: { status: "passed", expected_url: "/docs", current_url: "/docs" },
          },
        ]}
      />
    );
    expect(screen.queryByTestId("step-precondition-s1")).toBeNull();
  });

  it("StepsTab renders precondition strip with expected/current URLs when status=failed", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "s1",
            precondition: {
              status: "failed",
              expected_url: "/docs",
              current_url: "/pricing",
              message: "Navigate to /docs first",
            },
          },
        ]}
      />
    );
    const strip = screen.getByTestId("step-precondition-s1");
    expect(strip).toHaveAttribute("data-status", "failed");
    expect(screen.getByTestId("step-precondition-expected-s1").textContent).toContain("/docs");
    expect(screen.getByTestId("step-precondition-current-s1").textContent).toContain("/pricing");
    const action = screen.getByTestId("step-precondition-action-s1");
    expect(action).toBeDisabled();
    expect(action).toHaveAttribute("title", expect.stringMatching(/not yet wired/i));
  });

  it("StepsTab ignores malformed precondition without crashing", () => {
    render(
      <StepsTab pendingSteps={[{ id: "s2", precondition: "not a dict" }]} />
    );
    expect(screen.queryByTestId("step-precondition-s2")).toBeNull();
  });

  it("StepsTab does not render precondition strip when status=unknown", () => {
    render(
      <StepsTab
        pendingSteps={[
          { id: "s3", precondition: { status: "garbage", expected_url: "/x" } },
        ]}
      />
    );
    // Frontend never claims failure without explicit backend status="failed".
    expect(screen.queryByTestId("step-precondition-s3")).toBeNull();
  });

  // Pass 4b-6 — backend-driven child operation count badge
  it("StepsTab does not render child count badge without payload", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", intent: "click" }]} />);
    expect(screen.queryByTestId("step-child-count-s1")).toBeNull();
  });

  it("StepsTab renders child count badge from payload", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", child_op_count: 3 }]} />);
    const badge = screen.getByTestId("step-child-count-s1");
    expect(badge).toHaveAttribute("data-count", "3");
    expect(badge.textContent).toContain("3 child ops");
  });

  it("StepsTab pluralizes child count correctly for 1", () => {
    render(<StepsTab pendingSteps={[{ id: "s1", child_op_count: 1 }]} />);
    expect(screen.getByTestId("step-child-count-s1").textContent).toContain("1 child op");
    expect(screen.getByTestId("step-child-count-s1").textContent).not.toContain("1 child ops");
  });

  it("StepsTab does not render child count badge for invalid values", () => {
    render(
      <StepsTab
        pendingSteps={[
          { id: "s1", child_op_count: -1 },
          { id: "s2", child_op_count: "many" },
          { id: "s3", child_op_count: 2.5 },
          { id: "s4", child_op_count: null },
        ]}
      />
    );
    expect(screen.queryByTestId("step-child-count-s1")).toBeNull();
    expect(screen.queryByTestId("step-child-count-s2")).toBeNull();
    expect(screen.queryByTestId("step-child-count-s3")).toBeNull();
    expect(screen.queryByTestId("step-child-count-s4")).toBeNull();
  });

  it("StepsTab child count badge and children list coexist cleanly", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "sect",
            step_kind: "section",
            child_op_count: 2,
            children: [
              { child_id: "a", description: "first" },
              { child_id: "b", description: "second" },
            ],
          },
        ]}
      />
    );
    expect(screen.getByTestId("step-child-count-sect")).toHaveAttribute("data-count", "2");
    expect(screen.getByTestId("step-children-sect")).toHaveAttribute("data-count", "2");
  });

  it("StepsTab renders locator/kind/blocked/precondition/children/count together without breaking", () => {
    render(
      <StepsTab
        pendingSteps={[
          {
            id: "fat",
            intent: "Section: Pricing",
            step_kind: "section",
            locator_kind: "ok",
            locator_strength: "strong",
            blocked: { reason: "missing_data" },
            precondition: { status: "failed", expected_url: "/docs", current_url: "/pricing" },
            child_op_count: 2,
            children: [{ child_id: "a" }, { child_id: "b" }],
          },
        ]}
      />
    );
    expect(screen.getByTestId("step-locator-fat")).toHaveAttribute("data-strength", "strong");
    expect(screen.getByTestId("step-kind-fat")).toHaveAttribute("data-kind", "section");
    expect(screen.getByTestId("step-child-count-fat")).toHaveAttribute("data-count", "2");
    expect(screen.getByTestId("step-blocked-fat")).toHaveAttribute("data-reason", "missing_data");
    expect(screen.getByTestId("step-precondition-fat")).toHaveAttribute("data-status", "failed");
    expect(screen.getByTestId("step-children-fat")).toHaveAttribute("data-count", "2");
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

  // Pass 5 (D-102) — Recorded tab evidence view
  it("RecordedTab disables Replay all when no backend onReplayAll is wired", () => {
    render(
      <RecordedTab
        recordedSteps={[{ step_id: "r1", description: "x", state: "recorded" }]}
      />
    );
    expect(screen.getByTestId("recorded-replay-all")).toBeDisabled();
  });

  it("RecordedTab renders expected and observed outcomes from payload only", () => {
    render(
      <RecordedTab
        recordedSteps={[
          {
            step_id: "rec",
            description: "Click pricing",
            state: "recorded",
            expected_outcome: { type: "navigation", description: "/pricing" },
            observed_outcome: { type: "navigation", description: "/pricing" },
          },
        ]}
      />
    );
    const exp = screen.getByTestId("recorded-expected-rec");
    expect(exp).toHaveAttribute("data-expected-type", "navigation");
    expect(exp.textContent.toLowerCase()).toContain("navigation");
    expect(exp.textContent).toContain("/pricing");
    const obs = screen.getByTestId("recorded-observed-rec");
    expect(obs).toHaveAttribute("data-observed-type", "navigation");
    expect(obs.textContent).toContain("/pricing");
  });

  it("RecordedTab does not render outcomes when payload omits them", () => {
    render(
      <RecordedTab recordedSteps={[{ step_id: "rec", state: "recorded" }]} />
    );
    expect(screen.queryByTestId("recorded-expected-rec")).toBeNull();
    expect(screen.queryByTestId("recorded-observed-rec")).toBeNull();
  });

  it("RecordedTab renders locator with locator_kind attribute from payload", () => {
    render(
      <RecordedTab
        recordedSteps={[
          {
            step_id: "rec",
            description: "click",
            state: "recorded",
            locator: 'getByRole("button")',
            locator_kind: "ok",
          },
        ]}
      />
    );
    const loc = screen.getByTestId("recorded-locator-rec");
    expect(loc).toHaveAttribute("data-locator-kind", "ok");
    expect(loc.textContent).toContain('getByRole("button")');
  });

  it("RecordedTab status badge reflects backend state for failed records (no fake success)", () => {
    render(
      <RecordedTab
        recordedSteps={[{ step_id: "rec", state: "failed", description: "click" }]}
      />
    );
    const status = screen.getByTestId("recorded-status-rec");
    expect(status).toHaveAttribute("data-status", "failed");
    expect(status.textContent.toLowerCase()).toContain("failed");
    expect(status.className).toContain("err");
  });

  it("RecordedTab unresolved status renders with unresolved badge", () => {
    render(
      <RecordedTab
        recordedSteps={[{ step_id: "rec", state: "unresolved" }]}
      />
    );
    const status = screen.getByTestId("recorded-status-rec");
    expect(status).toHaveAttribute("data-status", "unresolved");
  });

  it("RecordedTab unknown status renders with unknown badge instead of fake recorded", () => {
    render(<RecordedTab recordedSteps={[{ step_id: "rec" }]} />);
    const status = screen.getByTestId("recorded-status-rec");
    expect(status).toHaveAttribute("data-status", "unknown");
  });

  it("RecordedTab replay button is disabled and titled when step has no backend id", () => {
    const onReplayOne = vi.fn();
    render(
      <RecordedTab
        recordedSteps={[{ description: "no id", state: "recorded" }]}
        onReplayOne={onReplayOne}
      />
    );
    const btn = screen.getByTestId("recorded-replay-r-0");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("title", expect.stringMatching(/no backend step id/i));
    fireEvent.click(btn);
    expect(onReplayOne).not.toHaveBeenCalled();
  });

  it("RecordedTab replay button dispatches typed replay_one when backend id and handler exist", () => {
    const onReplayOne = vi.fn();
    render(
      <RecordedTab
        recordedSteps={[
          { step_id: "rec_a", description: "x", state: "recorded" },
        ]}
        onReplayOne={onReplayOne}
      />
    );
    const btn = screen.getByTestId("recorded-replay-rec_a");
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(onReplayOne).toHaveBeenCalledWith(
      expect.objectContaining({ type: "replay_one", step_id: "rec_a" })
    );
  });

  it("RecordedTab renders child operations with stable testids and op-status", () => {
    render(
      <RecordedTab
        recordedSteps={[
          {
            step_id: "rec",
            state: "recorded",
            children: [
              { child_id: "op_a", operation: "click", description: "click cta", status: "passed" },
              { child_id: "op_b", operation: "assert", description: "verify", status: "failed" },
            ],
          },
        ]}
      />
    );
    const list = screen.getByTestId("recorded-child-list-rec");
    expect(list).toHaveAttribute("data-count", "2");
    expect(screen.getByTestId("recorded-child-rec-op_a")).toHaveAttribute("data-op-type", "click");
    expect(screen.getByTestId("recorded-child-rec-op_a")).toHaveAttribute("data-op-status", "passed");
    expect(screen.getByTestId("recorded-child-rec-op_b")).toHaveAttribute("data-op-status", "failed");
  });

  it("RecordedTab drops malformed child entries without crashing", () => {
    render(
      <RecordedTab
        recordedSteps={[
          {
            step_id: "rec",
            state: "recorded",
            children: [null, 42, "bad", { child_id: "good", description: "real" }],
          },
        ]}
      />
    );
    const list = screen.getByTestId("recorded-child-list-rec");
    expect(list).toHaveAttribute("data-count", "1");
    expect(screen.getByTestId("recorded-child-rec-good")).toBeInTheDocument();
  });

  it("RecordedTab renders artifacts as links with stable testids when payload provides them", () => {
    render(
      <RecordedTab
        recordedSteps={[
          {
            step_id: "rec",
            state: "recorded",
            artifacts: [
              "screenshots/rec.png",
              { id: "log-1", label: "trace.log", url: "/artifacts/trace.log" },
            ],
          },
        ]}
      />
    );
    const a1 = screen.getByTestId("recorded-artifact-rec-screenshots/rec.png");
    expect(a1.getAttribute("href")).toContain("screenshots/rec.png");
    const a2 = screen.getByTestId("recorded-artifact-rec-log-1");
    expect(a2.getAttribute("href")).toBe("/artifacts/trace.log");
    expect(a2.textContent).toContain("trace.log");
  });

  it("RecordedTab tolerates malformed step entry without rendering fake evidence", () => {
    render(<RecordedTab recordedSteps={[null, 42, { step_id: "ok", state: "recorded", description: "x" }]} />);
    // Only the valid one renders evidence.
    expect(screen.getByTestId("recorded-item-ok")).toBeInTheDocument();
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
