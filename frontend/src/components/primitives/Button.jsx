import React from "react";

const VARIANT_STYLES = {
  primary: {
    background: "var(--aw-acc)",
    color: "var(--aw-tx-inverse)",
    border: "1px solid transparent",
  },
  secondary: {
    background: "var(--aw-bg-tray)",
    color: "var(--aw-tx-2)",
    border: "1px solid var(--aw-br-strong)",
  },
  danger: {
    background: "var(--aw-red-bg)",
    color: "var(--aw-red)",
    border: "1px solid var(--aw-red)",
  },
  ghost: {
    background: "transparent",
    color: "var(--aw-tx-3)",
    border: "1px solid transparent",
  },
};

export function Button({
  children,
  variant = "secondary",
  disabled = false,
  onClick,
  "aria-label": ariaLabel,
  "data-testid": testId = "aw-button",
  type = "button",
  style,
  ...rest
}) {
  const variantStyle = VARIANT_STYLES[variant] ?? VARIANT_STYLES.secondary;

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={disabled ? undefined : onClick}
      aria-label={ariaLabel}
      data-testid={testId}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--aw-space-1)",
        padding: "var(--aw-space-2) var(--aw-space-3)",
        borderRadius: "var(--aw-r)",
        fontSize: "var(--aw-text-sm)",
        fontWeight: "var(--aw-weight-medium)",
        lineHeight: "var(--aw-line-snug)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "opacity var(--aw-transition)",
        ...variantStyle,
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export default Button;
