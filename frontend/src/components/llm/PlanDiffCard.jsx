// components/llm/PlanDiffCard.jsx — Plan-diff apply/reject card
// S7-0606: apply_plan_diff/reject_plan_diff dispatched typed; no local plan mutation.
import React from "react";

export function PlanDiffCard({ diff, onApply, onReject }) {
  if (!diff) return null;
  const diff_id = diff.diff_id ?? diff.id ?? null;
  const plan_id = diff.plan_id ?? null;
  const operations = Array.isArray(diff.operations ?? diff.ops)
    ? (diff.operations ?? diff.ops)
    : [];

  return (
    <div data-testid="plan-diff-card" className="aw-card aw-plan-diff">
      <div className="aw-card-title">Plan diff proposed</div>
      <ul data-testid="plan-diff-operations">
        {operations.map((op, i) => (
          <li key={op.id ?? i}>
            <span data-testid="diff-op-kind">{op.kind ?? op.type ?? "op"}</span>
            <span data-testid="diff-op-text">{op.description ?? op.text ?? ""}</span>
          </li>
        ))}
      </ul>
      <div className="aw-card-actions">
        <button
          type="button"
          data-testid="plan-diff-apply"
          disabled={!diff_id}
          onClick={() =>
            typeof onApply === "function" &&
            onApply({ type: "apply_plan_diff", plan_id, diff_id, operations })
          }
        >
          Apply diff
        </button>
        <button
          type="button"
          data-testid="plan-diff-reject"
          disabled={!diff_id}
          onClick={() =>
            typeof onReject === "function" &&
            onReject({ type: "reject_plan_diff", plan_id, diff_id })
          }
        >
          Reject diff
        </button>
      </div>
    </div>
  );
}

export default PlanDiffCard;
