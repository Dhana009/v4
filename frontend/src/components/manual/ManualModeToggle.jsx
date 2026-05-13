// components/manual/ManualModeToggle.jsx — Manual Mode interaction toggle
// S7-0708: blocked during run/recovery/save-load; manual mode does not call LLM.
import React from "react";

export function ManualModeToggle({
  manual = false,
  phase = "idle",
  disabledReason = "",
  onToggle,
}) {
  const blockedPhases = ["executing", "recovery", "saving", "loading"];
  const disabled =
    blockedPhases.includes(phase) || !!disabledReason;

  return (
    <div data-testid="manual-mode-toggle" className="aw-manual-toggle">
      <label>
        <input
          type="checkbox"
          data-testid="manual-mode-checkbox"
          checked={manual}
          disabled={disabled}
          onChange={(e) =>
            typeof onToggle === "function" &&
            onToggle({ type: "set_manual_mode", manual: e.target.checked })
          }
        />
        Manual Mode
      </label>
      {disabled && disabledReason ? (
        <span data-testid="manual-mode-disabled-reason">{disabledReason}</span>
      ) : disabled ? (
        <span data-testid="manual-mode-disabled-reason">
          Not available during {phase}.
        </span>
      ) : null}
    </div>
  );
}

export default ManualModeToggle;
