// components/replay/ReplayControls.jsx — Replay one / replay all
// S7-0804: dispatches typed commands; never marks replay success locally.
import React from "react";

export function ReplayControls({ stepId, runId, hasRecorded = false, onReplayOne, onReplayAll }) {
  const canOne = !!runId && !!stepId && hasRecorded;
  const canAll = !!runId && hasRecorded;
  return (
    <div data-testid="replay-controls" className="aw-replay-controls">
      <button
        type="button"
        data-testid="replay-one"
        disabled={!canOne}
        onClick={() =>
          typeof onReplayOne === "function" &&
          onReplayOne({ type: "replay_one", run_id: runId, step_id: stepId })
        }
      >
        Replay one
      </button>
      <button
        type="button"
        data-testid="replay-all"
        disabled={!canAll}
        onClick={() =>
          typeof onReplayAll === "function" &&
          onReplayAll({ type: "replay_all", run_id: runId })
        }
      >
        Replay all
      </button>
    </div>
  );
}

export default ReplayControls;
