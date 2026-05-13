// components/llm/CompletedCard.jsx — Run summary card (completed/failed/rejected)
// S7-0610: rendered only when completion prop present; never inferred from step counts.
import React from "react";

export function CompletedCard({ completion }) {
  if (!completion) return null;
  const summary = completion.summary ?? completion.text ?? "";
  const outcome = completion.outcome ?? completion.status ?? "completed";
  const duration = completion.duration ?? null;
  const failed = outcome === "failed" || outcome === "rejected" || !!completion.error;
  const rejectionReason = completion.rejection_reason ?? completion.error ?? null;

  return (
    <div
      data-testid={failed ? "completed-card-failed" : "completed-card"}
      className={`aw-card aw-completed ${failed ? "aw-completed-failed" : ""}`}
    >
      <div className="aw-card-title">
        {failed ? "Run failed" : "Run completed"}
      </div>
      <div data-testid="completed-outcome">{outcome}</div>
      {summary ? <div data-testid="completed-summary">{summary}</div> : null}
      {duration ? <div data-testid="completed-duration">{duration}</div> : null}
      {rejectionReason ? (
        <div data-testid="completed-error">{rejectionReason}</div>
      ) : null}
    </div>
  );
}

export default CompletedCard;
