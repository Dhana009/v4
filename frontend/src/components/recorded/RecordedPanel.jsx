// components/recorded/RecordedPanel.jsx — Recorded tab evidence
// S7-0801: shows step_recorded backend evidence only. Never pending steps.
import React from "react";
import RecordedStepCard from "./RecordedStepCard.jsx";

export function RecordedPanel({ recordedSteps = [] }) {
  const list = Array.isArray(recordedSteps) ? recordedSteps : [];
  if (list.length === 0) {
    return (
      <div data-testid="recorded-empty" className="aw-recorded-empty">
        No recorded steps yet.
      </div>
    );
  }
  return (
    <ul data-testid="recorded-list" className="aw-recorded">
      {list.map((s, i) => (
        <li key={s.step_id ?? s.id ?? i} data-testid="recorded-item">
          <RecordedStepCard step={s} />
        </li>
      ))}
    </ul>
  );
}

export default RecordedPanel;
