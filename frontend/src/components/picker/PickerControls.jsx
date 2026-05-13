// components/picker/PickerControls.jsx — Arm/cancel picker
// S7-0704: AutoWorkbench UI excluded from picker targets.
import React from "react";

// Mirror of layout/picker-exclusion selector; documents that picker must
// honor this set when emitting candidates (server validates as well).
// PICKER_EXCLUSION_SELECTOR / data-autoworkbench / data-aw-ui
export const PICKER_EXCLUDE_TOKENS = [
  "#autoworkbench-root",
  "#aw-shadow-host",
  "[data-autoworkbench]",
  "[data-aw-ui]",
];

export function PickerControls({
  armed = false,
  targetType = "element",
  stepId = null,
  onArm,
  onCancel,
}) {
  return (
    <div
      data-testid="picker-controls"
      data-autoworkbench="1"
      data-aw-ui="picker-controls"
      className="aw-picker-controls"
    >
      <select
        data-testid="picker-target-type"
        value={targetType}
        onChange={(e) =>
          typeof onArm === "function" &&
          onArm({
            type: "arm_picker",
            step_id: stepId,
            target_type: e.target.value,
            exclude: PICKER_EXCLUDE_TOKENS,
          })
        }
      >
        <option value="element">element</option>
        <option value="section">section</option>
      </select>
      <button
        type="button"
        data-testid="picker-arm"
        disabled={armed}
        onClick={() =>
          typeof onArm === "function" &&
          onArm({
            type: "arm_picker",
            step_id: stepId,
            target_type: targetType,
            exclude: PICKER_EXCLUDE_TOKENS,
          })
        }
      >
        Arm picker
      </button>
      <button
        type="button"
        data-testid="picker-cancel"
        disabled={!armed}
        onClick={() =>
          typeof onCancel === "function" && onCancel({ type: "cancel_picker" })
        }
      >
        Cancel
      </button>
    </div>
  );
}

export default PickerControls;
