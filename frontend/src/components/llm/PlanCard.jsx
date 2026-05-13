// components/llm/PlanCard.jsx — Plan-ready review card
// S7-0604: confirm_plan dispatched only with plan_id + plan_version.
import React from "react";

export function PlanCard({ plan, onConfirm, onReject }) {
  if (!plan) return null;
  const plan_id = plan.plan_id ?? plan.id ?? null;
  const plan_version = plan.version ?? plan.plan_version ?? null;
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  const canConfirm = !!plan_id;

  return (
    <div data-testid="plan-card" className="aw-card aw-plan-card">
      <div className="aw-card-title">Plan ready</div>
      <ol data-testid="plan-steps">
        {steps.map((s, i) => (
          <li key={s.step_id ?? s.id ?? i}>
            {s.description ?? s.text ?? s.action ?? `Step ${i + 1}`}
          </li>
        ))}
      </ol>
      <div className="aw-card-actions">
        <button
          type="button"
          data-testid="plan-confirm"
          disabled={!canConfirm}
          onClick={() =>
            typeof onConfirm === "function" &&
            onConfirm({ type: "confirm_plan", plan_id, plan_version })
          }
        >
          Confirm plan
        </button>
        <button
          type="button"
          data-testid="plan-reject"
          onClick={() =>
            typeof onReject === "function" &&
            onReject({ type: "correction", plan_id, plan_version })
          }
        >
          Discuss
        </button>
      </div>
    </div>
  );
}

export default PlanCard;
