// components/trace/FailureDetailPanel.jsx — Failure detail
// S7-0903: surfaces expected, actual, layer, evidence from backend payload.
import React from "react";

export function FailureDetailPanel({ failure }) {
  if (!failure) return null;
  const expected = failure.expected ?? failure.expected_value ?? "";
  const actual = failure.actual ?? failure.actual_value ?? "";
  const layer = failure.layer ?? failure.failure_layer ?? "";
  const evidence = failure.evidence ?? failure.evidence_refs ?? [];

  return (
    <div data-testid="failure-detail" className="aw-failure-detail">
      <div className="aw-card-title">Failure detail</div>
      {expected ? (
        <div>
          <span>expected:</span>
          <span data-testid="failure-expected">{String(expected)}</span>
        </div>
      ) : null}
      {actual ? (
        <div>
          <span>actual:</span>
          <span data-testid="failure-actual">{String(actual)}</span>
        </div>
      ) : null}
      {layer ? <div data-testid="failure-layer">layer: {layer}</div> : null}
      {Array.isArray(evidence) && evidence.length > 0 ? (
        <ul data-testid="failure-evidence">
          {evidence.map((e, i) => (
            <li key={i}>{typeof e === "string" ? e : (e.label ?? e.url ?? "")}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default FailureDetailPanel;
