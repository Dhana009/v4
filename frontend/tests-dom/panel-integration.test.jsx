import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { reducer, createInitialState } from "../src/store/reducer.js";

// IDEPanel is registered as a window global by aw-ide-panel.jsx.
// Importing the file for its side effect attaches window.IDEPanel.
import "../aw-ide-panel.jsx";

const IDEPanel = window.IDEPanel;

function buildRuntime(state) {
  // Mirror the runtime shape that main.jsx threads into the panel.
  return {
    live: true,
    connectionStatus: state.connected ? "connected" : "disconnected",
    conversation: [],
    timeline: [],
    traceEntries: state.trace_entries ?? [],
    plan: null,
    pendingSteps: state.pending_steps ?? [],
    pendingCommands: [],
    recordedSteps: state.recorded_steps ?? [],
    codePreview: state.code_preview ?? null,
    codeDiagnostics: [],
    storeState: state,
    storePlan: state.plan ?? null,
    storePendingClarification: state.pending_clarification ?? null,
    storePendingPermission: state.pending_permission ?? null,
    storePendingRecovery: state.pending_recovery ?? null,
    storePendingRecommendations: state.pending_recommendations ?? [],
    storeRecordedSteps: state.recorded_steps ?? [],
    storePendingSteps: state.pending_steps ?? [],
    storeCodePreview: state.code_preview ?? null,
    storeTraceEntries: state.trace_entries ?? [],
    storeErrors: state.errors ?? [],
    storeLastError: state.last_error ?? null,
    storeInteractionMode: state.interaction_mode ?? "idle",
    run_id: state.run_id ?? null,
    phase: state.phase ?? "idle",
    handleConfirmPlan: vi.fn(),
    handleSendPlanCorrection: vi.fn(),
    handleSendClarificationAnswer: vi.fn(),
    handleSendRecoveryInstruction: vi.fn(),
    handleAttachElement: vi.fn(),
    handleRunPendingSteps: vi.fn(),
    handleReplayRecordedStep: vi.fn(),
    handleReplayAllRecordedSteps: vi.fn(),
    handleSaveSnapshot: vi.fn(),
    handleCopyRecordedStep: vi.fn(),
    onSendUserMessage: vi.fn(),
    onAcceptRecommendations: vi.fn(),
    onApplyPlanDiff: vi.fn(),
    onRejectPlanDiff: vi.fn(),
    onPermissionDecision: vi.fn(),
    onChooseLocatorCandidate: vi.fn(),
    addPendingStep: vi.fn(),
    removePendingStep: vi.fn(),
    updatePendingStepIntent: vi.fn(),
    updatePendingStepExpectedOutcome: vi.fn(),
    updatePendingStepElementTarget: vi.fn(),
    onAddPendingStep: vi.fn(),
    onDeletePendingStep: vi.fn(),
  };
}

function event(type, payload) {
  return { type, payload };
}

describe("v4 panel ↔ store integration (real DOM render)", () => {
  beforeEach(() => {
    // jsdom resets between tests
  });

  it("IDEPanel mounts with empty state and shows panel chrome", () => {
    const state = createInitialState();
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="idle" tab="llm" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("aw-panel")).toBeInTheDocument();
    expect(screen.getByTestId("aw-tabs")).toBeInTheDocument();
    expect(screen.getByTestId("aw-footer")).toBeInTheDocument();
  });

  it("plan_ready event → PlanReady card renders and Confirm dispatches typed cmd", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(
      state,
      event("plan_ready", {
        run_id: "r1",
        plan: {
          plan_id: "p1",
          version: 1,
          steps: [
            { step_id: "s1", description: "Verify hero" },
            { step_id: "s2", description: "Three cards" },
          ],
        },
      })
    );
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="awaiting_confirmation" tab="llm" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("card-plan-ready")).toBeInTheDocument();
    expect(screen.getByTestId("plan-step-count").textContent).toBe("2");
    fireEvent.click(screen.getByTestId("plan-confirm"));
    expect(runtime.handleConfirmPlan).toHaveBeenCalledWith(
      expect.objectContaining({ type: "confirm_plan", plan_id: "p1", plan_version: 1 })
    );
  });

  it("clarification_needed event → ClarificationCard renders, Submit dispatches", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(
      state,
      event("clarification_needed", {
        run_id: "r1",
        clarification: {
          question_id: "q1",
          question: "Which depth?",
          options: [
            { id: "smoke", label: "Smoke" },
            { id: "sanity", label: "Sanity" },
          ],
        },
      })
    );
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="clarification" tab="llm" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("card-clarification")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("clarification-option-smoke"));
    fireEvent.click(screen.getByTestId("clarification-submit"));
    expect(runtime.handleSendClarificationAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ type: "option_selected", question_id: "q1", answer: "smoke" })
    );
  });

  it("step_recorded events flow into Recorded tab", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(state, event("step_recorded", { run_id: "r1", step_id: "s1", description: "Hero" }));
    state = reducer(state, event("step_recorded", { run_id: "r1", step_id: "s2", description: "Cards" }));
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="executing" tab="rec" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("recorded-tab")).toBeInTheDocument();
    expect(screen.getByTestId("recorded-item-s1")).toBeInTheDocument();
    expect(screen.getByTestId("recorded-item-s2")).toBeInTheDocument();
  });

  it("code_update event flows into Code tab and copy enabled", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(state, event("code_update", { run_id: "r1", code: "test('flow', ()=>{});" }));
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="executing" tab="code" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("code-tab")).toBeInTheDocument();
    expect(screen.getByTestId("code-preview").textContent).toContain("test('flow'");
    expect(screen.getByTestId("code-copy")).not.toBeDisabled();
  });

  it("recovery_needed event keeps panel out of completed even after run_completed", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(
      state,
      event("recovery_needed", {
        run_id: "r1",
        step_id: "s5",
        failure_reason: "click_failed",
        options: [{ id: "retry", label: "Retry" }],
      })
    );
    state = reducer(state, event("run_completed", { run_id: "r1" }));
    expect(state.phase).not.toBe("completed");
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="recovery" tab="llm" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("card-recovery")).toBeInTheDocument();
  });

  it("locator_ambiguous reuses recovery channel: ambiguity card renders, choose dispatches typed", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(
      state,
      event("recovery_needed", {
        run_id: "r1",
        step_id: "s4",
        failure_reason: "locator_ambiguous",
        options: [
          { id: "c1", title: "Header CTA", locator: "nav .cta" },
          { id: "c2", title: "Hero CTA", locator: ".hero .cta" },
        ],
      })
    );
    const runtime = buildRuntime({ ...state, connected: true });
    runtime.onChooseLocatorCandidate = vi.fn();
    render(<IDEPanel state="recovery" tab="llm" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("card-locator-ambiguity")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("locator-candidate-c1"));
    fireEvent.click(screen.getByTestId("locator-confirm"));
    expect(runtime.onChooseLocatorCandidate).toHaveBeenCalledWith(
      expect.objectContaining({ type: "choose_locator_candidate", candidate_id: "c1", step_id: "s4" })
    );
  });

  it("tab switching changes body via onTabChange callback", () => {
    let activeTab = "llm";
    const setTab = vi.fn((t) => {
      activeTab = t;
    });
    const state = createInitialState();
    const runtime = buildRuntime({ ...state, connected: true });
    const { rerender } = render(
      <IDEPanel state="idle" tab={activeTab} runtime={runtime} onTabChange={setTab} />
    );
    fireEvent.click(screen.getByTestId("aw-tab-steps"));
    expect(setTab).toHaveBeenCalledWith("steps");
    rerender(<IDEPanel state="idle" tab="steps" runtime={runtime} onTabChange={setTab} />);
    expect(screen.getByTestId("steps-tab")).toBeInTheDocument();
  });

  it("Steps tab deep workflow: intent edit, outcome chip, attach, and run dispatch through runtime", () => {
    const state = createInitialState();
    const runtime = buildRuntime({
      ...state,
      connected: true,
      pending_steps: [
        { id: "stp_1", intent: "click Get started", expected_outcome: null },
        { id: "stp_2", intent: "verify hero", expected_outcome: { type: "navigation" } },
      ],
    });
    render(<IDEPanel state="idle" tab="steps" runtime={runtime} onTabChange={() => {}} />);

    expect(screen.getByTestId("steps-tab")).toBeInTheDocument();
    expect(screen.getByTestId("step-row-stp_1")).toBeInTheDocument();
    expect(screen.getByTestId("step-row-stp_2")).toBeInTheDocument();

    fireEvent.change(screen.getByTestId("step-input-stp_1"), {
      target: { value: "click Sign up" },
    });
    expect(runtime.updatePendingStepIntent).toHaveBeenCalledWith("stp_1", "click Sign up");

    fireEvent.click(screen.getByTestId("step-outcome-chip-navigation-stp_1"));
    expect(runtime.updatePendingStepExpectedOutcome).toHaveBeenCalledWith(
      "stp_1",
      expect.objectContaining({ type: "navigation", source: "user" })
    );

    fireEvent.click(screen.getByTestId("step-attach-stp_1"));
    expect(runtime.handleAttachElement).toHaveBeenCalledWith("stp_1");

    fireEvent.click(screen.getByTestId("steps-run-all"));
    expect(runtime.handleRunPendingSteps).toHaveBeenCalled();
  });

  it("Steps tab Run-all is disabled and shows blocker copy when blocked by pending recovery", () => {
    const state = createInitialState();
    const runtime = buildRuntime({
      ...state,
      connected: true,
      pending_steps: [{ id: "stp_a", intent: "click Sign in" }],
      pending_recovery: {
        step_id: "stp_a",
        failure_reason: "click_failed",
        options: [{ id: "retry", label: "Retry" }],
      },
    });
    render(<IDEPanel state="recovery" tab="steps" runtime={runtime} onTabChange={() => {}} />);

    expect(screen.getByTestId("steps-tab")).toBeInTheDocument();
    expect(screen.getByTestId("steps-run-all")).toBeDisabled();
    expect(screen.getByTestId("steps-blocked").textContent).toMatch(/recovery/i);

    fireEvent.click(screen.getByTestId("steps-run-all"));
    expect(runtime.handleRunPendingSteps).not.toHaveBeenCalled();
  });

  it("Steps tab surfaces backend-driven step.blocked strip from store payload", () => {
    const state = createInitialState();
    const runtime = buildRuntime({
      ...state,
      connected: true,
      pending_steps: [
        {
          id: "stp_blocked",
          intent: "fill salary form",
          blocked: {
            reason: "missing_data",
            message: "salaries.csv not uploaded",
            refs: ["salaries.csv"],
          },
        },
      ],
    });
    render(<IDEPanel state="idle" tab="steps" runtime={runtime} onTabChange={() => {}} />);
    const strip = screen.getByTestId("step-blocked-stp_blocked");
    expect(strip).toHaveAttribute("data-reason", "missing_data");
    expect(screen.getByTestId("step-status-stp_blocked").textContent.toLowerCase()).toContain("blocked");
  });

  it("Steps tab renders safely when a pending step has no stable id", () => {
    const state = createInitialState();
    const runtime = buildRuntime({
      ...state,
      connected: true,
      // Malformed step: no `id` / `step_id`. Must not crash.
      pending_steps: [{ intent: "click somewhere" }],
    });
    render(<IDEPanel state="idle" tab="steps" runtime={runtime} onTabChange={() => {}} />);

    expect(screen.getByTestId("steps-tab")).toBeInTheDocument();
    // Empty state must NOT render for a present (if malformed) step.
    expect(screen.queryByTestId("steps-empty")).toBeNull();
  });
});
