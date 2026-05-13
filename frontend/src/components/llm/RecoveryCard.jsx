// components/llm/RecoveryCard.jsx — Recovery-needed card
// S7-0609: retry_recovery/skip_step/stop_run dispatched typed; no success inference.
import React, { useState } from "react";

export function RecoveryCard({ recovery, onRetry, onSkip, onStop }) {
  const [text, setText] = useState("");
  if (!recovery) return null;
  const step_id = recovery.step_id ?? null;
  const failure_reason = recovery.failure_reason ?? recovery.reason ?? "";
  const options = Array.isArray(recovery.options) ? recovery.options : [];

  return (
    <div data-testid="recovery-card" className="aw-card aw-recovery">
      <div className="aw-card-title">Recovery needed</div>
      {failure_reason ? (
        <div data-testid="recovery-reason">{failure_reason}</div>
      ) : null}
      <ul data-testid="recovery-options">
        {options.map((opt, i) => (
          <li key={opt.id ?? i}>
            <button
              type="button"
              onClick={() =>
                typeof onRetry === "function" &&
                onRetry({
                  type: "retry_recovery",
                  step_id,
                  recovery_action: opt.action ?? opt.value ?? opt,
                })
              }
            >
              {opt.label ?? opt.action ?? `Option ${i + 1}`}
            </button>
          </li>
        ))}
      </ul>
      <textarea
        data-testid="recovery-instruction"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="aw-card-actions">
        <button
          type="button"
          data-testid="recovery-retry"
          disabled={!text.trim()}
          onClick={() =>
            typeof onRetry === "function" &&
            onRetry({ type: "retry_recovery", step_id, recovery_action: text.trim() })
          }
        >
          Retry
        </button>
        <button
          type="button"
          data-testid="recovery-skip"
          onClick={() =>
            typeof onSkip === "function" &&
            onSkip({ type: "skip_step", step_id })
          }
        >
          Skip step
        </button>
        <button
          type="button"
          data-testid="recovery-stop"
          onClick={() =>
            typeof onStop === "function" &&
            onStop({ type: "stop_run" })
          }
        >
          Stop run
        </button>
      </div>
    </div>
  );
}

export default RecoveryCard;
