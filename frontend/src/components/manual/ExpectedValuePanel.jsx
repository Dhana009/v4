// components/manual/ExpectedValuePanel.jsx — Expected value / test data inputs
// S7-0711: missing expected value or test data blocks run with reason.
import React from "react";

export function ExpectedValuePanel({ step, onChange }) {
  if (!step) return null;
  const stepId = step.step_id ?? step.id;
  const needsExpected = !!step.needs_expected_value;
  const needsTestData = !!step.needs_test_data;
  const expected = step.expected_value ?? "";
  const testData = step.test_data ?? "";

  const missing = [];
  if (needsExpected && !expected.trim()) missing.push("expected_value");
  if (needsTestData && !testData.trim()) missing.push("test_data");

  return (
    <div data-testid="expected-value-panel" className="aw-expected-value">
      {needsExpected ? (
        <label>
          Expected value (required)
          <input
            data-testid="expected-value-input"
            value={expected}
            onChange={(e) =>
              typeof onChange === "function" &&
              onChange({ step_id: stepId, expected_value: e.target.value })
            }
          />
        </label>
      ) : null}
      {needsTestData ? (
        <label>
          Test data (required)
          <input
            data-testid="test-data-input"
            value={testData}
            onChange={(e) =>
              typeof onChange === "function" &&
              onChange({ step_id: stepId, test_data: e.target.value })
            }
          />
        </label>
      ) : null}
      {missing.length > 0 ? (
        <div data-testid="expected-value-blocked" className="aw-blocked">
          Run blocked: missing {missing.join(", ")}.
        </div>
      ) : null}
    </div>
  );
}

export default ExpectedValuePanel;
