import React from "react";

export function CandidateCard({
  candidate,
  onSelect,
  selected = false,
  "data-testid": testId = "aw-candidate-card",
}) {
  if (!candidate) return null;

  const { id, semantic_label, scope, risk, confidence, preview } = candidate;

  const riskColor = {
    low:    "var(--aw-grn)",
    medium: "var(--aw-yel)",
    high:   "var(--aw-red)",
  }[risk] ?? "var(--aw-tx-3)";

  return (
    <div
      data-testid={testId}
      aria-selected={selected}
      style={{
        padding: "var(--aw-space-3)",
        background: selected ? "var(--aw-bg-active)" : "var(--aw-bg-card)",
        border: `1px solid ${selected ? "var(--aw-acc)" : "var(--aw-br)"}`,
        borderRadius: "var(--aw-r)",
        cursor: "pointer",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span style={{ fontWeight: "var(--aw-weight-medium)", fontSize: "var(--aw-text-sm)" }}>
          {semantic_label ?? id}
        </span>
        {confidence !== undefined && (
          <span style={{ fontSize: "var(--aw-text-xs)", color: "var(--aw-tx-3)" }}>
            {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
      {scope && (
        <div style={{ fontSize: "var(--aw-text-xs)", color: "var(--aw-tx-3)", marginTop: 2 }}>
          {scope}
        </div>
      )}
      {risk && (
        <div style={{ fontSize: "var(--aw-text-xs)", color: riskColor, marginTop: 2 }}>
          {risk} risk
        </div>
      )}
      {preview && (
        <div
          style={{
            marginTop: "var(--aw-space-2)",
            fontFamily: "var(--aw-font-mono)",
            fontSize: "var(--aw-text-xs)",
            color: "var(--aw-tx-3)",
            background: "var(--aw-bg-tray)",
            padding: "var(--aw-space-1) var(--aw-space-2)",
            borderRadius: "var(--aw-r-sm)",
          }}
        >
          {preview}
        </div>
      )}
      {onSelect && (
        <button
          data-testid={`${testId}-select`}
          aria-label={`Select ${semantic_label ?? id}`}
          onClick={() => onSelect(candidate)}
          style={{
            marginTop: "var(--aw-space-2)",
            fontSize: "var(--aw-text-xs)",
            color: "var(--aw-acc)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          Use this
        </button>
      )}
    </div>
  );
}

export default CandidateCard;
