// components/code/CodePanel.jsx — Code tab live renderer
// S7-0806: renders backend codePreview only; no code before code_update.
import React from "react";

export function CodePanel({ codePreview }) {
  if (!codePreview) {
    return (
      <div data-testid="code-empty" className="aw-code-empty">
        Awaiting code_update…
      </div>
    );
  }
  const text =
    typeof codePreview === "string"
      ? codePreview
      : codePreview.code ?? codePreview.content ?? JSON.stringify(codePreview, null, 2);
  return (
    <pre data-testid="code-preview" className="aw-code-preview">
      {text}
    </pre>
  );
}

export default CodePanel;
