// components/session/SessionPanel.jsx — Save/load session UI
// S7-0809: dispatches save_session/load_session; success only from backend events.
import React, { useState } from "react";

export function SessionPanel({ runId, phase = "idle", lastResult = null, onSave, onLoad }) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");

  const canSave = !!runId && phase === "completed" && !!name.trim();
  const canLoad = phase === "idle" && !!path.trim();

  return (
    <div data-testid="session-panel" className="aw-session">
      <div className="aw-session-save">
        <input
          data-testid="session-name"
          placeholder="session name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          type="button"
          data-testid="session-save"
          disabled={!canSave}
          onClick={() =>
            typeof onSave === "function" &&
            onSave({ type: "save_session", run_id: runId, session_name: name.trim() })
          }
        >
          Save session
        </button>
      </div>
      <div className="aw-session-load">
        <input
          data-testid="session-path"
          placeholder="session id or path"
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <button
          type="button"
          data-testid="session-load"
          disabled={!canLoad}
          onClick={() =>
            typeof onLoad === "function" &&
            onLoad({ type: "load_session", session_id: path.trim() })
          }
        >
          Load session
        </button>
      </div>
      {lastResult ? (
        <div data-testid="session-last-result" data-outcome={lastResult.outcome ?? ""}>
          {lastResult.message ?? lastResult.outcome ?? ""}
        </div>
      ) : null}
    </div>
  );
}

export default SessionPanel;
