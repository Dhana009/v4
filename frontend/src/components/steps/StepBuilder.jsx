// components/steps/StepBuilder.jsx — Add/edit/delete/reorder/duplicate
// S7-0702: draft/command-driven; never sets recorded steps locally.
import React, { useState } from "react";

export function StepBuilder({
  step,
  onAdd,
  onEdit,
  onDelete,
  onReorder,
  onDuplicate,
}) {
  const [text, setText] = useState(step?.description ?? "");

  const fire = (cb, payload) => {
    if (typeof cb === "function") cb(payload);
  };

  return (
    <div data-testid="step-builder" className="aw-step-builder">
      <textarea
        data-testid="step-builder-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="aw-step-builder-actions">
        <button
          type="button"
          data-testid="step-builder-add"
          disabled={!text.trim()}
          onClick={() => fire(onAdd, { description: text.trim() })}
        >
          Add
        </button>
        <button
          type="button"
          data-testid="step-builder-edit"
          disabled={!step?.step_id || !text.trim()}
          onClick={() =>
            fire(onEdit, { step_id: step?.step_id, description: text.trim() })
          }
        >
          Edit
        </button>
        <button
          type="button"
          data-testid="step-builder-delete"
          disabled={!step?.step_id}
          onClick={() => fire(onDelete, { step_id: step?.step_id })}
        >
          Delete
        </button>
        <button
          type="button"
          data-testid="step-builder-reorder-up"
          disabled={!step?.step_id}
          onClick={() => fire(onReorder, { step_id: step?.step_id, direction: -1 })}
        >
          ↑
        </button>
        <button
          type="button"
          data-testid="step-builder-reorder-down"
          disabled={!step?.step_id}
          onClick={() => fire(onReorder, { step_id: step?.step_id, direction: 1 })}
        >
          ↓
        </button>
        <button
          type="button"
          data-testid="step-builder-duplicate"
          disabled={!step?.step_id}
          onClick={() => fire(onDuplicate, { step_id: step?.step_id })}
        >
          Duplicate
        </button>
      </div>
    </div>
  );
}

export default StepBuilder;
