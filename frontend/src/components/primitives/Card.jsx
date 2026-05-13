import React from "react";

export function Card({
  children,
  title,
  footer,
  color = "default",
  "data-testid": testId = "aw-card",
  "aria-label": ariaLabel,
  id,
}) {
  const borderColor = {
    default: "var(--aw-br)",
    success: "var(--aw-grn)",
    error: "var(--aw-red)",
    warning: "var(--aw-yel)",
    info: "var(--aw-blu)",
  }[color] ?? "var(--aw-br)";

  return (
    <div
      id={id}
      data-testid={testId}
      aria-label={ariaLabel}
      style={{
        background: "var(--aw-bg-card)",
        border: `1px solid ${borderColor}`,
        borderRadius: "var(--aw-r-lg)",
        boxShadow: "var(--aw-shadow-sm)",
        overflow: "hidden",
      }}
    >
      {title && (
        <div
          style={{
            padding: "var(--aw-space-3) var(--aw-space-4)",
            borderBottom: "1px solid var(--aw-br)",
            fontSize: "var(--aw-text-sm)",
            fontWeight: "var(--aw-weight-medium)",
            color: "var(--aw-tx-2)",
          }}
        >
          {title}
        </div>
      )}
      <div style={{ padding: "var(--aw-space-4)" }}>{children}</div>
      {footer && (
        <div
          style={{
            padding: "var(--aw-space-2) var(--aw-space-4)",
            borderTop: "1px solid var(--aw-br)",
            display: "flex",
            gap: "var(--aw-space-2)",
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
}

export default Card;
