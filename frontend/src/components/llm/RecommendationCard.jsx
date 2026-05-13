// components/llm/RecommendationCard.jsx — Recommendation review card
// S7-0603: backend-driven; dispatches accept_recommendations.
import React, { useState } from "react";

export function RecommendationCard({ recommendations = [], onAccept }) {
  const list = Array.isArray(recommendations) ? recommendations : [];
  const [selected, setSelected] = useState([]);
  if (list.length === 0) return null;

  const toggle = (id) => {
    setSelected((cur) =>
      cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]
    );
  };

  const disabled = selected.length === 0;

  return (
    <div data-testid="recommendation-card" className="aw-card aw-recommendation">
      <div className="aw-card-title">Recommendations</div>
      <ul data-testid="recommendation-options">
        {list.map((r, i) => {
          const id = r.id ?? `rec-${i}`;
          return (
            <li key={id}>
              <label>
                <input
                  type="checkbox"
                  checked={selected.includes(id)}
                  onChange={() => toggle(id)}
                />
                {r.label ?? r.text ?? r.summary ?? id}
              </label>
            </li>
          );
        })}
      </ul>
      <button
        type="button"
        data-testid="recommendation-accept"
        disabled={disabled}
        onClick={() =>
          typeof onAccept === "function" &&
          onAccept({ type: "accept_recommendations", selected_recs: selected })
        }
      >
        Accept selected
      </button>
    </div>
  );
}

export default RecommendationCard;
