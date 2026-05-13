// components/trace/TraceTimeline.jsx — Live trace timeline
// S7-0901: renders traceEntries from store only; never mutates runtime truth.
import React from "react";

const KNOWN_TYPES = new Set([
  "run_started", "plan_ready", "clarification_needed", "recommendation_ready",
  "permission_required", "locator_ambiguous", "recovery_needed",
  "step_validating", "step_executing", "step_failed", "step_skipped", "step_recorded",
  "code_update", "replay_started", "replay_result",
  "run_completed", "runtime_rejected", "session_state", "schema_error", "error",
]);

export function TraceTimeline({ traceEntries = [] }) {
  const list = Array.isArray(traceEntries) ? traceEntries : [];
  if (list.length === 0) {
    return (
      <div data-testid="trace-empty" className="aw-trace-empty">
        No trace yet.
      </div>
    );
  }
  return (
    <ol data-testid="trace-timeline" className="aw-trace-timeline">
      {list.map((entry, i) => {
        const type = entry.type ?? "unknown";
        const isKnown = KNOWN_TYPES.has(type);
        return (
          <li
            key={entry.id ?? i}
            data-testid={isKnown ? "trace-row" : "trace-row-unknown"}
            data-type={type}
            data-known={isKnown ? "1" : "0"}
            className={`aw-trace-row ${isKnown ? "" : "aw-trace-unknown"}`}
          >
            <span data-testid="trace-type">{type}</span>
            {!isKnown ? (
              <span data-testid="trace-diagnostic">unknown event (diagnostic only)</span>
            ) : null}
            <span data-testid="trace-text">{entry.text ?? entry.message ?? ""}</span>
            {entry.timestamp ? (
              <time data-testid="trace-time">{entry.timestamp}</time>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export default TraceTimeline;
