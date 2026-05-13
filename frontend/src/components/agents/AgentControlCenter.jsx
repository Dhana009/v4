// components/agents/AgentControlCenter.jsx — Limited live view + honest disabled controls
// S7-0909: unsupported controls disabled with reason; required agents cannot be disabled.
import React from "react";

export function AgentControlCenter({ agents = [], onToggle }) {
  const list = Array.isArray(agents) ? agents : [];
  if (list.length === 0) {
    return (
      <div data-testid="agent-control-empty" className="aw-agent-control-empty">
        Agent control unavailable.
      </div>
    );
  }
  return (
    <ul data-testid="agent-control" className="aw-agent-control">
      {list.map((a, i) => {
        const id = a.id ?? a.name ?? `agent-${i}`;
        const required = !!a.required;
        const supported = a.supported !== false;
        const reason = a.disabled_reason ?? (
          required
            ? "required agent (cannot disable)"
            : !supported
            ? "unsupported (backend does not implement)"
            : ""
        );
        const isDisabled = required || !supported;
        const enabled = a.enabled !== false;
        return (
          <li key={id} data-testid="agent-control-row" data-required={required ? "1" : "0"}>
            <label>
              <input
                type="checkbox"
                data-testid={`agent-toggle-${id}`}
                checked={enabled}
                disabled={isDisabled}
                onChange={(e) =>
                  typeof onToggle === "function" &&
                  onToggle({
                    type: "agent_toggle",
                    agent_id: id,
                    enabled: e.target.checked,
                  })
                }
              />
              {a.name ?? id}
            </label>
            {isDisabled && reason ? (
              <span data-testid={`agent-disabled-reason-${id}`}>{reason}</span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export default AgentControlCenter;
