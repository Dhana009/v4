// components/manual/ManualAssertionBuilder.jsx — Manual assertion draft
// S7-0710: expected value required for relevant assertions.
import React, { useState } from "react";

export function ManualAssertionBuilder({ stepId, onSubmit }) {
  const [assertionType, setAssertionType] = useState("visible");
  const [target, setTarget] = useState("");
  const [expected, setExpected] = useState("");

  const needsExpected = ["text_equals", "text_contains", "value_equals"].includes(
    assertionType
  );
  const isFilled = !!target.trim() && (!needsExpected || !!expected.trim());
  const disabled = !isFilled;

  return (
    <div data-testid="manual-assertion-builder" className="aw-manual-assertion">
      <select
        data-testid="manual-assertion-type"
        value={assertionType}
        onChange={(e) => setAssertionType(e.target.value)}
      >
        <option value="visible">visible</option>
        <option value="hidden">hidden</option>
        <option value="enabled">enabled</option>
        <option value="text_equals">text_equals</option>
        <option value="text_contains">text_contains</option>
        <option value="value_equals">value_equals</option>
      </select>
      <input
        data-testid="manual-assertion-target"
        placeholder="target (required)"
        value={target}
        onChange={(e) => setTarget(e.target.value)}
      />
      {needsExpected ? (
        <input
          data-testid="manual-assertion-expected"
          placeholder="expected value (required)"
          value={expected}
          onChange={(e) => setExpected(e.target.value)}
        />
      ) : null}
      <button
        type="button"
        data-testid="manual-assertion-submit"
        disabled={disabled}
        onClick={() =>
          typeof onSubmit === "function" &&
          onSubmit({
            type: "manual_assertion_draft",
            step_id: stepId,
            assertion_type: assertionType,
            target,
            expected: needsExpected ? expected : null,
          })
        }
      >
        Add assertion
      </button>
    </div>
  );
}

export default ManualAssertionBuilder;
