// components/agents/AgentActivity.jsx — Compact agent activity view
// S7-0908: shows real agent events; honest "unavailable" when missing.
import React from "react";

export function AgentActivity({ agents = [] }) {
  const list = Array.isArray(agents) ? agents : [];
  if (list.length === 0) {
    return (
      <div data-testid="agents-unavailable" className="aw-agents-empty">
        No agent activity (unavailable).
      </div>
    );
  }
  return (
    <ul data-testid="agents-activity" className="aw-agents">
      {list.map((a, i) => {
        const id = a.id ?? a.name ?? `agent-${i}`;
        const status = a.status ?? "unknown";
        return (
          <li key={id} data-testid="agent-row" data-status={status}>
            <span data-testid="agent-name">{a.name ?? id}</span>
            <span data-testid="agent-status">{status}</span>
            {a.activity ? (
              <span data-testid="agent-activity-text">{a.activity}</span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export default AgentActivity;
