import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  CardClarification,
  CardPlanReady,
  CardRecommendation,
  CardPermission,
  CardCompleted,
  CardLocatorAmbiguity,
  CardRecovery,
  CardOffline,
  Composer,
  LlmThread,
} from "../src/v4/llm-cards.jsx";

describe("v4 LLM cards (real DOM render)", () => {
  it("ClarificationCard renders nothing without payload", () => {
    const { container } = render(<CardClarification />);
    expect(container.firstChild).toBeNull();
  });

  it("ClarificationCard renders question + options and dispatches typed answer", () => {
    const onAnswer = vi.fn();
    render(
      <CardClarification
        clarification={{
          question_id: "q1",
          question: "Smoke or sanity?",
          options: [
            { id: "smoke", label: "Smoke" },
            { id: "sanity", label: "Sanity" },
          ],
        }}
        onAnswer={onAnswer}
      />
    );
    expect(screen.getByTestId("card-clarification")).toBeInTheDocument();
    expect(screen.getByText("Smoke or sanity?")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("clarification-option-smoke"));
    fireEvent.click(screen.getByTestId("clarification-submit"));
    expect(onAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ type: "option_selected", question_id: "q1", answer: "smoke" })
    );
  });

  it("PlanReadyCard renders steps and dispatches confirm_plan with plan_id", () => {
    const onConfirm = vi.fn();
    render(
      <CardPlanReady
        plan={{
          plan_id: "p1",
          version: 1,
          steps: [
            { step_id: "s1", description: "Verify hero" },
            { step_id: "s2", description: "Three cards" },
          ],
        }}
        onConfirm={onConfirm}
      />
    );
    expect(screen.getByTestId("card-plan-ready")).toBeInTheDocument();
    expect(screen.getByTestId("plan-step-count").textContent).toBe("2");
    fireEvent.click(screen.getByTestId("plan-confirm"));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ type: "confirm_plan", plan_id: "p1", plan_version: 1 })
    );
  });

  it("PlanReadyCard confirm button is disabled without plan_id", () => {
    render(
      <CardPlanReady
        plan={{ steps: [{ step_id: "s1", description: "X" }] }}
        onConfirm={vi.fn()}
      />
    );
    expect(screen.getByTestId("plan-confirm")).toBeDisabled();
  });

  it("RecommendationCard accept is disabled until selection", () => {
    const onAccept = vi.fn();
    render(
      <CardRecommendation
        recommendations={[
          { id: "r1", label: "Hero visible", checked: false },
          { id: "r2", label: "Pricing cards count", checked: false },
        ]}
        onAccept={onAccept}
      />
    );
    const accept = screen.getByTestId("recommendation-accept");
    expect(accept).toBeDisabled();
    fireEvent.click(screen.getByTestId("recommendation-item-r1").querySelector("input"));
    expect(accept).not.toBeDisabled();
    fireEvent.click(accept);
    expect(onAccept).toHaveBeenCalledWith(
      expect.objectContaining({ type: "accept_recommendations", selected_recs: ["r1"] })
    );
  });

  it("PermissionCard dispatches typed allow/deny", () => {
    const onDecision = vi.fn();
    render(
      <CardPermission
        permission={{ operation: 'page.click("Get started")', risk_level: "medium", reason: "may navigate" }}
        onDecision={onDecision}
      />
    );
    fireEvent.click(screen.getByTestId("permission-allow-once"));
    expect(onDecision).toHaveBeenCalledWith(
      expect.objectContaining({ type: "permission_decision", decision: "allow", scope: "once" })
    );
    fireEvent.click(screen.getByTestId("permission-deny"));
    expect(onDecision).toHaveBeenCalledWith(
      expect.objectContaining({ type: "permission_decision", decision: "deny" })
    );
  });

  it("LocatorAmbiguityCard requires selection before confirm", () => {
    const onChoose = vi.fn();
    render(
      <CardLocatorAmbiguity
        ambiguity={{
          step_id: "s4",
          candidates: [
            { id: "c1", title: "Header CTA", locator: "nav .cta", scope: "nav" },
            { id: "c2", title: "Hero CTA", locator: ".hero .cta", scope: ".hero" },
          ],
        }}
        onChoose={onChoose}
      />
    );
    expect(screen.getByTestId("locator-confirm")).toBeDisabled();
    fireEvent.click(screen.getByTestId("locator-candidate-c1"));
    expect(screen.getByTestId("locator-confirm")).not.toBeDisabled();
    fireEvent.click(screen.getByTestId("locator-confirm"));
    expect(onChoose).toHaveBeenCalledWith(
      expect.objectContaining({ type: "choose_locator_candidate", candidate_id: "c1", step_id: "s4" })
    );
  });

  it("RecoveryCard dispatches retry/skip/stop without inferring success", () => {
    const onRetry = vi.fn();
    const onStop = vi.fn();
    render(
      <CardRecovery
        recovery={{ step_id: "s5", failure_reason: "assertion mismatch" }}
        onRetry={onRetry}
        onStop={onStop}
      />
    );
    fireEvent.click(screen.getByTestId("recovery-retry"));
    expect(onRetry).toHaveBeenCalledWith(
      expect.objectContaining({ type: "retry_recovery", recovery_action: "retry_as_is" })
    );
    fireEvent.click(screen.getByTestId("recovery-stop"));
    expect(onStop).toHaveBeenCalledWith(expect.objectContaining({ type: "stop_run" }));
  });

  it("CompletedCard reads completion outcome from props and never infers", () => {
    render(
      <CardCompleted
        completion={{ outcome: "ok", passed: 5, repaired: 1, failed: 0, elapsed: "31.2s" }}
      />
    );
    expect(screen.getByTestId("completed-state").textContent).toBe("ok");
    expect(screen.getByTestId("completed-summary-grid")).toBeInTheDocument();
  });

  it("OfflineCard is hidden when connection is connected", () => {
    const { container } = render(<CardOffline connection={{ connected: true }} />);
    expect(container.firstChild).toBeNull();
  });

  it("OfflineCard shows when disconnected and dispatches reconnect", () => {
    const onReconnect = vi.fn();
    render(<CardOffline connection={{ connected: false }} onReconnect={onReconnect} />);
    expect(screen.getByTestId("card-offline")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("offline-reconnect"));
    expect(onReconnect).toHaveBeenCalledWith(expect.objectContaining({ type: "reconnect" }));
  });
});

describe("v4 Composer pick (D-107)", () => {
  it("aw-composer-pick renders and is enabled by default when onPickElement provided", () => {
    render(<Composer onPickElement={vi.fn()} />);
    const btn = screen.getByTestId("aw-composer-pick");
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
  });

  it("aw-composer-pick has descriptive title attribute", () => {
    render(<Composer onPickElement={vi.fn()} />);
    const btn = screen.getByTestId("aw-composer-pick");
    expect(btn.title).toBe("Pick a page element to attach to your task");
  });

  it("clicking aw-composer-pick dispatches via onPickElement callback", () => {
    const onPickElement = vi.fn();
    render(<Composer onPickElement={onPickElement} />);
    fireEvent.click(screen.getByTestId("aw-composer-pick"));
    expect(onPickElement).toHaveBeenCalledTimes(1);
    expect(onPickElement).toHaveBeenCalledWith(expect.objectContaining({ type: "arm_picker" }));
  });

  it("aw-composer-pick is disabled when disabled prop is true; click does not dispatch", () => {
    const onPickElement = vi.fn();
    render(<Composer onPickElement={onPickElement} disabled={true} />);
    const btn = screen.getByTestId("aw-composer-pick");
    expect(btn).toBeDisabled();
    fireEvent.click(btn);
    expect(onPickElement).not.toHaveBeenCalled();
  });

  it("no aw-composer-camera or screenshot button anywhere in Composer DOM", () => {
    const { container } = render(<Composer onPickElement={vi.fn()} />);
    expect(container.querySelector("[data-testid='aw-composer-camera']")).toBeNull();
    expect(container.querySelector("[data-testid*='screenshot']")).toBeNull();
    expect(container.querySelector("[data-testid*='camera']")).toBeNull();
  });

  it("aw-composer-send button still present (regression guard)", () => {
    render(<Composer onSend={vi.fn()} />);
    expect(screen.getByTestId("aw-composer-send")).toBeInTheDocument();
  });
});

// Regression: draft pending step on Steps tab made currentStep truthy, which
// killed the LLM-tab welcome card (LlmEmpty) and rendered a blank thread div
// because every other card was null-gated. See debug report: post-Batch-D
// LLM empty-state regression. Fix removed currentStep from the empty-state
// gate; currentStep continues to flow to CardExecution which renders only on
// phase === "executing".
describe("v4 LlmThread empty-state gate (post-Batch-D regression)", () => {
  it("renders LlmEmpty welcome card even when a draft pending step exists and no LLM activity has occurred", () => {
    render(
      <LlmThread
        conversation={[]}
        plan={null}
        pendingClarification={null}
        pendingRecommendations={[]}
        pendingPermission={null}
        pendingDiff={null}
        pendingRecovery={null}
        ambiguity={null}
        completion={null}
        rejection={null}
        connection={{ connected: true }}
        phase="idle"
        currentStep={{ step_id: "s1", intent: "click hero", id: "s1" }}
        recordedSteps={[]}
        pendingSteps={[{ step_id: "s1", intent: "click hero", id: "s1" }]}
        dispatchers={{}}
        onSeed={vi.fn()}
      />
    );
    expect(screen.getByTestId("llm-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("aw-thread")).toBeNull();
  });

  it("renders aw-thread (not LlmEmpty) when real LLM activity is present even with no currentStep", () => {
    render(
      <LlmThread
        conversation={[{ role: "user", text: "hi", id: "m1" }]}
        plan={null}
        pendingClarification={null}
        pendingRecommendations={[]}
        pendingPermission={null}
        pendingDiff={null}
        pendingRecovery={null}
        ambiguity={null}
        completion={null}
        rejection={null}
        connection={{ connected: true }}
        phase="idle"
        currentStep={null}
        recordedSteps={[]}
        pendingSteps={[]}
        dispatchers={{}}
      />
    );
    expect(screen.getByTestId("aw-thread")).toBeInTheDocument();
    expect(screen.queryByTestId("llm-empty")).toBeNull();
  });

  it("renders CardExecution inside aw-thread when phase === 'executing' and currentStep present (regression guard)", () => {
    render(
      <LlmThread
        conversation={[]}
        plan={null}
        pendingClarification={null}
        pendingRecommendations={[]}
        pendingPermission={null}
        pendingDiff={null}
        pendingRecovery={null}
        ambiguity={null}
        completion={null}
        rejection={null}
        connection={{ connected: true }}
        phase="executing"
        currentStep={{ step_id: "s1", intent: "click hero", id: "s1" }}
        recordedSteps={[]}
        pendingSteps={[{ step_id: "s1", intent: "click hero", id: "s1" }]}
        dispatchers={{}}
      />
    );
    expect(screen.getByTestId("aw-thread")).toBeInTheDocument();
    expect(screen.queryByTestId("llm-empty")).toBeNull();
  });
});
