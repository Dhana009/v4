// components/steps/RunControls.jsx — Run selected / Run all
// S7-0703: blocked when no selection or runtime blocked.
import React from "react";

export function RunControls({
  selectedStepIds = [],
  pendingSteps = [],
  blocked = false,
  blockedReason = "",
  onRunSelected,
  onRunAll,
}) {
  const hasSelection = selectedStepIds.length > 0;
  const hasSteps = pendingSteps.length > 0;
  const runSelectedDisabled = blocked || !hasSelection;
  const runAllDisabled = blocked || !hasSteps;

  return (
    <div data-testid="run-controls" className="aw-run-controls">
      {blocked && blockedReason ? (
        <div data-testid="run-controls-blocked">{blockedReason}</div>
      ) : null}
      <button
        type="button"
        data-testid="run-selected"
        disabled={runSelectedDisabled}
        onClick={() =>
          typeof onRunSelected === "function" &&
          onRunSelected({ type: "run_steps", step_ids: selectedStepIds, mode: "selected" })
        }
      >
        Run selected ({selectedStepIds.length})
      </button>
      <button
        type="button"
        data-testid="run-all"
        disabled={runAllDisabled}
        onClick={() =>
          typeof onRunAll === "function" &&
          onRunAll({
            type: "run_steps",
            step_ids: pendingSteps.map((s) => s.step_id ?? s.id),
            mode: "all",
          })
        }
      >
        Run all
      </button>
    </div>
  );
}

export default RunControls;
