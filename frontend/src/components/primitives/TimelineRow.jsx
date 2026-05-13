import React from "react";

const SEVERITY_COLOR = {
  info:    "var(--aw-tx-3)",
  ok:      "var(--aw-grn)",
  warn:    "var(--aw-yel)",
  err:     "var(--aw-red)",
};

export function TimelineRow({
  event,
  timestamp,
  severity = "info",
  "data-testid": testId = "aw-timeline-row",
}) {
  const color = SEVERITY_COLOR[severity] ?? SEVERITY_COLOR.info;

  return (
    <div
      data-testid={testId}
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: "var(--aw-space-2)",
        padding: "var(--aw-space-1) 0",
        fontSize: "var(--aw-text-xs)",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: color,
          flexShrink: 0,
          marginTop: 2,
        }}
      />
      <span style={{ flex: 1, color: "var(--aw-tx-2)", lineHeight: "var(--aw-line-base)" }}>
        {event}
      </span>
      {timestamp && (
        <span style={{ color: "var(--aw-tx-4)", flexShrink: 0 }}>{timestamp}</span>
      )}
    </div>
  );
}

export default TimelineRow;
