import React from "react";

export function CodeBlock({
  code = "",
  language,
  "data-testid": testId = "aw-code-block",
  "aria-label": ariaLabel = "Code block",
}) {
  return (
    <pre
      data-testid={testId}
      aria-label={ariaLabel}
      data-language={language}
      style={{
        background: "var(--aw-bg-code)",
        color: "var(--aw-tx-inverse)",
        fontFamily: "var(--aw-font-mono)",
        fontSize: "var(--aw-text-sm)",
        lineHeight: "var(--aw-line-base)",
        padding: "var(--aw-space-3) var(--aw-space-4)",
        borderRadius: "var(--aw-r)",
        overflowX: "auto",
        margin: 0,
        whiteSpace: "pre",
      }}
    >
      <code>{code}</code>
    </pre>
  );
}

export default CodeBlock;
