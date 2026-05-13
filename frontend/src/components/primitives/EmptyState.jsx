import React from "react";

export function EmptyState({
  message = "No data yet",
  icon,
  "data-testid": testId = "aw-empty-state",
}) {
  return (
    <div
      data-testid={testId}
      role="status"
      aria-label={message}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--aw-space-2)",
        padding: "var(--aw-space-5)",
        color: "var(--aw-tx-4)",
        fontSize: "var(--aw-text-sm)",
        textAlign: "center",
      }}
    >
      {icon && (
        <span aria-hidden="true" style={{ fontSize: "var(--aw-text-lg)", opacity: 0.5 }}>
          {icon}
        </span>
      )}
      <span>{message}</span>
    </div>
  );
}

export default EmptyState;
