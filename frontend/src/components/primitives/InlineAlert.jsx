import React from "react";

const VARIANT_MAP = {
  error:   { bg: "var(--aw-red-bg)",  color: "var(--aw-red)",  icon: "✕" },
  warning: { bg: "var(--aw-yel-bg)", color: "var(--aw-yel)", icon: "⚠" },
  info:    { bg: "var(--aw-blu-bg)", color: "var(--aw-blu)",  icon: "ℹ" },
  success: { bg: "var(--aw-grn-bg)", color: "var(--aw-grn)", icon: "✓" },
};

export function InlineAlert({
  variant = "info",
  message,
  children,
  "data-testid": testId = "aw-inline-alert",
}) {
  const s = VARIANT_MAP[variant] ?? VARIANT_MAP.info;
  const content = message ?? children;

  return (
    <div
      role="alert"
      data-testid={testId}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "var(--aw-space-2)",
        padding: "var(--aw-space-2) var(--aw-space-3)",
        background: s.bg,
        borderRadius: "var(--aw-r)",
        fontSize: "var(--aw-text-sm)",
        color: s.color,
      }}
    >
      <span aria-hidden="true" style={{ flexShrink: 0, fontSize: "var(--aw-text-xs)" }}>
        {s.icon}
      </span>
      <span>{content}</span>
    </div>
  );
}

export default InlineAlert;
