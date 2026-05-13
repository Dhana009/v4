// components/llm/LocatorAmbiguityCard.jsx — Locator candidate selection
// S7-0608: choose_locator_candidate dispatched typed; no local activation.
import React from "react";

export function LocatorAmbiguityCard({ ambiguity, onChoose }) {
  if (!ambiguity) return null;
  const candidates = Array.isArray(ambiguity.candidates) ? ambiguity.candidates : [];
  const step_id = ambiguity.step_id ?? ambiguity.target_step ?? null;

  return (
    <div data-testid="locator-card" className="aw-card aw-locator">
      <div className="aw-card-title">Locator ambiguity</div>
      <ul data-testid="locator-candidates">
        {candidates.map((c, i) => {
          const candidate_id = c.id ?? c.candidate_id ?? `cand-${i}`;
          return (
            <li key={candidate_id}>
              <span>{c.locator ?? c.selector ?? c.description ?? candidate_id}</span>
              <button
                type="button"
                data-testid={`locator-choose-${i}`}
                onClick={() =>
                  typeof onChoose === "function" &&
                  onChoose({
                    type: "choose_locator_candidate",
                    step_id,
                    candidate_id,
                  })
                }
              >
                Choose
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default LocatorAmbiguityCard;
