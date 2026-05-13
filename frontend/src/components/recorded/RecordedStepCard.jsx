// components/recorded/RecordedStepCard.jsx — Single recorded step + children
// S7-0802 child operation evidence. S7-0803 repaired/skipped/unresolved states.
import React from "react";

const STATE_LABELS = {
  ok: "Recorded",
  pass: "Recorded",
  recorded: "Recorded",
  repaired: "Repaired",
  skipped: "Skipped",
  unresolved: "Unresolved",
  failed: "Failed",
};

export function RecordedStepCard({ step }) {
  if (!step) return null;
  const state = (step.state ?? step.status ?? "recorded").toLowerCase();
  const label = STATE_LABELS[state] ?? state;
  const isPass = state === "ok" || state === "pass" || state === "recorded";
  const skipped = state === "skipped";
  const repaired = state === "repaired";
  const unresolved = state === "unresolved";
  const children = Array.isArray(step.children) ? step.children : [];

  return (
    <div
      data-testid="recorded-step-card"
      data-state={state}
      data-is-pass={isPass && !skipped ? "1" : "0"}
      className={`aw-recorded-card aw-recorded-${state}`}
    >
      <div className="aw-card-title">
        {step.description ?? step.action ?? step.step_id ?? "Step"}
      </div>
      <div data-testid="recorded-state-label">{label}</div>
      {repaired ? (
        <div data-testid="recorded-repaired">
          <div data-testid="repaired-old">{step.repaired_from ?? ""}</div>
          <div data-testid="repaired-new">{step.repaired_to ?? ""}</div>
        </div>
      ) : null}
      {skipped ? (
        <div data-testid="recorded-skipped-reason">
          {step.skipped_reason ?? "Skipped"}
        </div>
      ) : null}
      {unresolved ? (
        <div data-testid="recorded-unresolved-reason">
          {step.unresolved_reason ?? "Unresolved"}
        </div>
      ) : null}
      {children.length > 0 ? (
        <ol data-testid="recorded-children" className="aw-recorded-children">
          {children.map((child, i) => (
            <li key={child.id ?? i} data-testid="recorded-child">
              <span data-testid="child-operation">
                {child.operation ?? child.operationId ?? child.kind ?? ""}
              </span>
              <span data-testid="child-description">
                {child.description ?? child.text ?? ""}
              </span>
              {Array.isArray(child.code_lines) ? (
                <pre data-testid="child-code-lines">
                  {child.code_lines.join("\n")}
                </pre>
              ) : null}
              {child.generated_line ? (
                <code data-testid="child-generated-line">
                  {child.generated_line}
                </code>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

export default RecordedStepCard;
