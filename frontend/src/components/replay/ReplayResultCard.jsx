// components/replay/ReplayResultCard.jsx — Replay result rendering
// S7-0805: renders replay_result event only; empty when no result.
import React from "react";

export function ReplayResultCard({ result }) {
  if (!result) return null;
  const outcome = result.outcome ?? result.status ?? "unknown";
  const isSuccess = outcome === "success" || outcome === "pass";
  const isFailure = outcome === "failure" || outcome === "failed";
  const diff = result.diff ?? null;
  const stepId = result.step_id ?? null;

  return (
    <div
      data-testid={isFailure ? "replay-result-failure" : "replay-result"}
      data-outcome={outcome}
      className={`aw-replay-result aw-replay-${outcome}`}
    >
      <div className="aw-card-title">
        Replay {isSuccess ? "succeeded" : isFailure ? "failed" : outcome}
      </div>
      {stepId ? <div data-testid="replay-result-step-id">{stepId}</div> : null}
      {diff ? (
        <pre data-testid="replay-result-diff">
          {typeof diff === "string" ? diff : JSON.stringify(diff, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export default ReplayResultCard;
