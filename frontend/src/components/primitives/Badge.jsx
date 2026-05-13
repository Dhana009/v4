import React from "react";

const VARIANT_MAP = {
  success: { bg: "var(--aw-grn-bg)", color: "var(--aw-grn)" },
  error:   { bg: "var(--aw-red-bg)", color: "var(--aw-red)" },
  warning: { bg: "var(--aw-yel-bg)", color: "var(--aw-yel)" },
  info:    { bg: "var(--aw-blu-bg)", color: "var(--aw-blu)" },
  neutral: { bg: "var(--aw-bg-tray)", color: "var(--aw-tx-3)" },
};

export function Badge({
  children,
  variant = "neutral",
  "data-testid": testId = "aw-badge",
}) {
  const s = VARIANT_MAP[variant] ?? VARIANT_MAP.neutral;

  return (
    <span
      data-testid={testId}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--aw-space-1)",
        padding: "1px var(--aw-space-2)",
        borderRadius: "var(--aw-r-full)",
        fontSize: "var(--aw-text-xs)",
        fontWeight: "var(--aw-weight-medium)",
        background: s.bg,
        color: s.color,
        lineHeight: "var(--aw-line-snug)",
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
