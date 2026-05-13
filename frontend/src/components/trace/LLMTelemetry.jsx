// components/trace/LLMTelemetry.jsx — LLM call/token/cost summary
// S7-0905: never displays raw prompts, API keys, or secrets.
import React from "react";

// Hard guard: keys never shown in this component.
const FORBIDDEN_FIELDS = new Set(["api_key", "raw_prompt", "secret", "token_value"]);

function safeFields(telemetry) {
  if (!telemetry || typeof telemetry !== "object") return [];
  return Object.entries(telemetry).filter(([k]) => !FORBIDDEN_FIELDS.has(k));
}

export function LLMTelemetry({ telemetry }) {
  if (!telemetry) return null;
  const tokens = telemetry.tokens ?? telemetry.token_count ?? null;
  const cost = telemetry.cost ?? telemetry.price ?? null;
  const calls = telemetry.calls ?? telemetry.call_count ?? null;
  const model = telemetry.model ?? null;
  const others = safeFields(telemetry).filter(
    ([k]) => !["tokens", "token_count", "cost", "price", "calls", "call_count", "model"].includes(k)
  );

  return (
    <div data-testid="llm-telemetry" className="aw-llm-telemetry">
      <div className="aw-card-title">LLM telemetry</div>
      {model ? <div data-testid="llm-model">model: {model}</div> : null}
      {tokens != null ? (
        <div data-testid="llm-tokens">tokens: {String(tokens)}</div>
      ) : null}
      {cost != null ? (
        <div data-testid="llm-cost">cost: {String(cost)}</div>
      ) : null}
      {calls != null ? (
        <div data-testid="llm-calls">calls: {String(calls)}</div>
      ) : null}
      {others.length > 0 ? (
        <ul data-testid="llm-extra">
          {others.map(([k, v]) => (
            <li key={k}>
              {k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default LLMTelemetry;
