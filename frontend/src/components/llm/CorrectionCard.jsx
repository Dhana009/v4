// components/llm/CorrectionCard.jsx — Plan correction discussion
// S7-0605: dispatches "correction" command; does NOT mutate plan locally.
import React, { useState } from "react";

export function CorrectionCard({ plan, onSendCorrection }) {
  const [text, setText] = useState("");
  if (!plan) return null;
  const plan_id = plan.plan_id ?? plan.id ?? null;
  const plan_version = plan.version ?? plan.plan_version ?? null;

  const send = () => {
    if (typeof onSendCorrection === "function") {
      onSendCorrection({
        type: "correction",
        plan_id,
        plan_version,
        correction_text: text.trim(),
      });
    }
    setText("");
  };

  return (
    <div data-testid="correction-card" className="aw-card aw-correction">
      <div className="aw-card-title">Discuss correction</div>
      <textarea
        data-testid="correction-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        type="button"
        data-testid="correction-send"
        disabled={!text.trim()}
        onClick={send}
      >
        Send correction
      </button>
    </div>
  );
}

export default CorrectionCard;
