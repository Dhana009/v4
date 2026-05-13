// components/manual/ManualActionBuilder.jsx — Manual action draft
// S7-0709: required fields validated; dispatches typed draft command; never sets recorded.
import React, { useState } from "react";

export function ManualActionBuilder({ stepId, onSubmit }) {
  const [action, setAction] = useState("click");
  const [target, setTarget] = useState("");
  const [value, setValue] = useState("");

  const needsValue = action === "type" || action === "select";
  const isRequiredFilled =
    !!action && !!target.trim() && (!needsValue || !!value.trim());
  const disabled = !isRequiredFilled;

  return (
    <div data-testid="manual-action-builder" className="aw-manual-action">
      <select
        data-testid="manual-action-type"
        value={action}
        onChange={(e) => setAction(e.target.value)}
      >
        <option value="click">click</option>
        <option value="type">type</option>
        <option value="select">select</option>
        <option value="navigate">navigate</option>
      </select>
      <input
        data-testid="manual-action-target"
        placeholder="target (required)"
        value={target}
        onChange={(e) => setTarget(e.target.value)}
      />
      {needsValue ? (
        <input
          data-testid="manual-action-value"
          placeholder="value (required)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      ) : null}
      <button
        type="button"
        data-testid="manual-action-submit"
        disabled={disabled}
        onClick={() =>
          typeof onSubmit === "function" &&
          onSubmit({
            type: "manual_action_draft",
            step_id: stepId,
            action,
            target,
            value: needsValue ? value : null,
          })
        }
      >
        Add action
      </button>
    </div>
  );
}

export default ManualActionBuilder;
