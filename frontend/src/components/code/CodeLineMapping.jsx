// components/code/CodeLineMapping.jsx — Code line to recorded step mapping
// S7-0807: graceful fallback when mapping missing (unmapped marker).
import React from "react";

export function CodeLineMapping({ codePreview, recordedSteps = [] }) {
  if (!codePreview) return null;
  const lines =
    typeof codePreview === "string"
      ? codePreview.split("\n")
      : Array.isArray(codePreview.lines)
      ? codePreview.lines
      : [];
  const mapping =
    typeof codePreview === "object" && codePreview && codePreview.line_to_step
      ? codePreview.line_to_step
      : {};
  return (
    <ol data-testid="code-line-mapping" className="aw-code-mapping">
      {lines.map((line, i) => {
        const stepId = mapping[i] ?? mapping[String(i)] ?? null;
        const unmapped = !stepId;
        return (
          <li
            key={i}
            data-testid="code-line"
            data-unmapped={unmapped ? "1" : "0"}
            data-step-id={stepId ?? ""}
          >
            <code>{line}</code>
            <span data-testid="code-line-step">
              {stepId ?? "unmapped (fallback ?)"}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export default CodeLineMapping;
