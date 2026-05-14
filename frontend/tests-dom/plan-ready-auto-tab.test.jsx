import React, { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";

import { reducer, createInitialState } from "../src/store/reducer.js";
import { usePlanReadyAutoTab } from "../src/panel-hooks/use-plan-ready-auto-tab.js";

// Side-effect import so window.IDEPanel is registered for the integration test.
import "../aw-ide-panel.jsx";

const IDEPanel = window.IDEPanel;

function event(type, payload) {
  return { type, payload };
}

/** Minimal harness that mirrors AutoWorkbenchRuntime's tab/setTab + hook wiring. */
function Harness({ initialTab, storeState, onTab }) {
  const [tab, setTab] = useState(initialTab);
  usePlanReadyAutoTab({
    plan: storeState.plan ?? null,
    phase: storeState.phase ?? null,
    currentTab: tab,
    setTab: (next) => {
      setTab(next);
      onTab?.(next);
    },
  });
  return <div data-testid="active-tab">{tab}</div>;
}

/** Full runtime stub for integration assertion against real IDEPanel. */
function buildRuntime(state) {
  return {
    live: true,
    connectionStatus: state.connected ? "connected" : "disconnected",
    conversation: [],
    timeline: [],
    traceEntries: state.trace_entries ?? [],
    plan: state.plan ?? null,
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

describe("usePlanReadyAutoTab — Sprint 7 routing fix", () => {
  it("switches Steps tab → LLM tab when plan_ready arrives", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));

    const onTab = vi.fn();
    const { rerender } = render(
      <Harness initialTab="steps" storeState={state} onTab={onTab} />
    );
    expect(screen.getByTestId("active-tab").textContent).toBe("steps");

    state = reducer(
      state,
      event("plan_ready", {
        run_id: "r1",
        plan: {
          plan_id: "p1",
          version: 1,
          steps: [{ step_id: "s1", description: "Verify hero" }],
        },
      })
    );

    rerender(<Harness initialTab="steps" storeState={state} onTab={onTab} />);
    expect(onTab).toHaveBeenCalledWith("llm");
    expect(screen.getByTestId("active-tab").textContent).toBe("llm");
  });

  it("stays on Steps tab when step_recorded arrives (no plan_ready)", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));

    const onTab = vi.fn();
    const { rerender } = render(
      <Harness initialTab="steps" storeState={state} onTab={onTab} />
    );

    state = reducer(
      state,
      event("step_recorded", {
        run_id: "r1",
        step: { step_id: "s1", description: "Recorded" },
      })
    );

    rerender(<Harness initialTab="steps" storeState={state} onTab={onTab} />);
    expect(onTab).not.toHaveBeenCalled();
    expect(screen.getByTestId("active-tab").textContent).toBe("steps");
  });

  it("does not re-route when plan_ready arrives but tab is already LLM", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));

    const onTab = vi.fn();
    const { rerender } = render(
      <Harness initialTab="llm" storeState={state} onTab={onTab} />
    );

    state = reducer(
      state,
      event("plan_ready", {
        run_id: "r1",
        plan: {
          plan_id: "p1",
          version: 1,
          steps: [{ step_id: "s1", description: "Verify hero" }],
        },
      })
    );

    rerender(<Harness initialTab="llm" storeState={state} onTab={onTab} />);
    expect(onTab).not.toHaveBeenCalled();
    expect(screen.getByTestId("active-tab").textContent).toBe("llm");
  });

  it("integration: after auto-switch, IDEPanel renders Confirm-Plan card", () => {
    let state = createInitialState();
    state = reducer(state, event("run_started", { run_id: "r1" }));
    state = reducer(
      state,
      event("plan_ready", {
        run_id: "r1",
        plan: {
          plan_id: "p1",
          version: 1,
          steps: [{ step_id: "s1", description: "Verify hero" }],
        },
      })
    );

    // Simulate the AutoWorkbenchRuntime tab state after auto-switch (tab="llm").
    const runtime = buildRuntime({ ...state, connected: true });
    render(<IDEPanel state="awaiting_confirmation" tab="llm" runtime={runtime} onTabChange={() => {}} />);
    expect(screen.getByTestId("card-plan-ready")).toBeInTheDocument();
  });
});
