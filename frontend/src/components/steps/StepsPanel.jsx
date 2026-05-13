// components/steps/StepsPanel.jsx — Live steps list
// S7-0701: renders pendingSteps from store; identity by step_id; no demo.
import React from "react";

export function StepsPanel({ pendingSteps = [], selectedStepIds = [], onToggleSelect }) {
  const steps = Array.isArray(pendingSteps) ? pendingSteps : [];
  if (steps.length === 0) {
    return (
      <div data-testid="steps-empty" className="aw-steps-empty">
        No steps yet.
      </div>
    );
  }
  return (
    <ul data-testid="steps-list" className="aw-steps">
      {steps.map((s, i) => {
        const step_id = s.step_id ?? s.id ?? `step-${i}`;
        const checked = selectedStepIds.includes(step_id);
        return (
          <li key={step_id} data-testid="steps-item" data-step-id={step_id}>
            <label>
              <input
                type="checkbox"
                checked={checked}
                onChange={() =>
                  typeof onToggleSelect === "function" && onToggleSelect(step_id)
                }
              />
              <span data-testid="steps-step-description">
                {s.description ?? s.text ?? s.action ?? step_id}
              </span>
            </label>
            <span data-testid="steps-step-status">{s.status ?? "pending"}</span>
          </li>
        );
      })}
    </ul>
  );
}

export default StepsPanel;
