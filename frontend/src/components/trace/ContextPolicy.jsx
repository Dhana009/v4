// components/trace/ContextPolicy.jsx — Context level + tool policy display
// S7-0906: read-only telemetry; no command dispatch.
import React from "react";

export function ContextPolicy({ policy }) {
  if (!policy) return null;
  const contextLevel = policy.context_level ?? policy.contextLevel ?? null;
  const tools = Array.isArray(policy.tools) ? policy.tools : [];
  const mode = policy.mode ?? null;

  return (
    <div data-testid="context-policy" className="aw-context-policy">
      <div className="aw-card-title">Context & tool policy</div>
      {contextLevel ? (
        <div data-testid="context-level">context_level: {contextLevel}</div>
      ) : null}
      {mode ? <div data-testid="policy-mode">mode: {mode}</div> : null}
      {tools.length > 0 ? (
        <ul data-testid="policy-tools">
          {tools.map((t, i) => (
            <li key={t.id ?? i} data-testid="policy-tool">
              <span>{t.name ?? t}</span>
              {t.allowed === false ? <span> (disallowed)</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default ContextPolicy;
