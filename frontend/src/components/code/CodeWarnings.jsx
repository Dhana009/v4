// components/code/CodeWarnings.jsx — Code warnings/placeholder/capability notices
// S7-0808: surfaces warning, placeholder, capability_gap states from diagnostics.
import React from "react";

const KIND_LABEL = {
  warning: "Warning",
  placeholder: "Placeholder",
  capability: "Capability gap",
  capability_gap: "Capability gap",
};

export function CodeWarnings({ diagnostics = [] }) {
  const list = Array.isArray(diagnostics) ? diagnostics.filter(Boolean) : [];
  if (list.length === 0) return null;
  return (
    <ul data-testid="code-warnings" aria-label="Code warnings">
      {list.map((d, i) => {
        const kind = (d.kind ?? d.level ?? d.severity ?? "warning").toLowerCase();
        const label = KIND_LABEL[kind] ?? "Notice";
        return (
          <li
            key={d.id ?? i}
            data-testid="code-warning"
            data-kind={kind}
            className={`aw-code-warning aw-code-${kind}`}
          >
            <span data-testid="code-warning-label">{label}</span>
            <span data-testid="code-warning-message">
              {d.message ?? d.text ?? d.reason ?? ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default CodeWarnings;
