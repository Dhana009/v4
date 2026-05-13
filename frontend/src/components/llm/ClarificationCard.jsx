// components/llm/ClarificationCard.jsx — Clarification question/options card
// S7-0602: backend-driven; dispatches typed option_selected command.
import React, { useState } from "react";

export function ClarificationCard({ clarification, onAnswer }) {
  const [text, setText] = useState("");
  if (!clarification) return null;
  const question = clarification.question ?? "";
  const options = Array.isArray(clarification.options) ? clarification.options : [];
  const target_step = clarification.target_step ?? null;
  const question_id = clarification.question_id ?? clarification.id ?? null;

  const dispatch = (answer) => {
    if (typeof onAnswer === "function") {
      onAnswer({
        type: "option_selected",
        question_id,
        target_step,
        answer,
      });
    }
  };

  return (
    <div data-testid="clarification-card" className="aw-card aw-clarification">
      <div className="aw-card-title">{question || "Clarification needed"}</div>
      {options.length > 0 ? (
        <ul data-testid="clarification-options">
          {options.map((opt, i) => (
            <li key={opt.id ?? i}>
              <button type="button" onClick={() => dispatch(opt.value ?? opt.label ?? opt)}>
                {opt.label ?? opt.value ?? String(opt)}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="aw-card-input">
        <textarea
          data-testid="clarification-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          type="button"
          data-testid="clarification-send"
          disabled={!text.trim()}
          onClick={() => dispatch(text.trim())}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ClarificationCard;
