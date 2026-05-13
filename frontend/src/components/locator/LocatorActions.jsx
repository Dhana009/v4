// components/locator/LocatorActions.jsx — Validate / improve locator commands
// S7-0707: dispatches typed commands; never activates locator locally.
import React from "react";

export function LocatorActions({ stepId, locator, onValidate, onImprove }) {
  const canSend = !!stepId && !!locator;
  return (
    <div data-testid="locator-actions" className="aw-locator-actions">
      <button
        type="button"
        data-testid="locator-validate"
        disabled={!canSend}
        onClick={() =>
          typeof onValidate === "function" &&
          onValidate({ type: "validate_locator", step_id: stepId, locator })
        }
      >
        Validate locator
      </button>
      <button
        type="button"
        data-testid="locator-improve"
        disabled={!canSend}
        onClick={() =>
          typeof onImprove === "function" &&
          onImprove({ type: "improve_locator", step_id: stepId, locator })
        }
      >
        Improve locator
      </button>
    </div>
  );
}

export default LocatorActions;
