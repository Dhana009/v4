import React from "react";

const STATUS_MAP = {
  completed: { color: "var(--aw-grn)", label: "Completed", dot: "●" },
  running:   { color: "var(--aw-acc)", label: "Running",   dot: "◉" },
  failed:    { color: "var(--aw-red)", label: "Failed",    dot: "●" },
  paused:    { color: "var(--aw-yel)", label: "Paused",    dot: "◌" },
  idle:      { color: "var(--aw-tx-4)", label: "Idle",     dot: "○" },
};

export function StatusPill({
  status,
  label,
  "data-testid": testId = "aw-status-pill",
}) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.idle;
  const displayLabel = label ?? s.label;

  return (
    <span
      data-testid={testId}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--aw-space-1)",
        fontSize: "var(--aw-text-xs)",
        color: s.color,
        fontWeight: "var(--aw-weight-medium)",
      }}
    >
      <span aria-hidden="true" style={{ fontSize: "8px", lineHeight: 1 }}>{s.dot}</span>
      {displayLabel}
    </span>
  );
}

export default StatusPill;
