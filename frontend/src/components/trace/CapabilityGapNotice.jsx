// components/trace/CapabilityGapNotice.jsx — Capability gap notices
// S7-0907: surfaces capability_gap entries from backend telemetry.
import React from "react";

export function CapabilityGapNotice({ gaps = [] }) {
  const list = Array.isArray(gaps) ? gaps.filter(Boolean) : [];
  if (list.length === 0) return null;
  return (
    <ul data-testid="capability-gap-notices" role="alert">
      {list.map((g, i) => {
        const name = g.name ?? g.capability ?? g.id ?? `gap-${i}`;
        const reason = g.reason ?? g.message ?? "capability missing";
        return (
          <li
            key={name}
            data-testid="capability-gap"
            data-capability={name}
            className="aw-capability-gap"
          >
            <span data-testid="capability-gap-name">{name}</span>
            <span data-testid="capability-gap-reason">{reason}</span>
          </li>
        );
      })}
    </ul>
  );
}

export default CapabilityGapNotice;
