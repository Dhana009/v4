// components/locator/LocatorCandidates.jsx — Locator candidate list
// S7-0706: candidates display backend-validated status only; pending until backend confirms.
import React from "react";

export function LocatorCandidates({ candidates = [], onSelect }) {
  const list = Array.isArray(candidates) ? candidates : [];
  if (list.length === 0) {
    return (
      <div data-testid="locator-candidates-empty" className="aw-locator-empty">
        No locator candidates.
      </div>
    );
  }
  return (
    <ul data-testid="locator-candidates" className="aw-locator-candidates">
      {list.map((c, i) => {
        const id = c.id ?? c.candidate_id ?? `cand-${i}`;
        const validated = c.validated === true;
        const pending = !validated;
        return (
          <li key={id} data-testid="locator-candidate" data-validated={validated ? "1" : "0"}>
            <span data-testid="locator-candidate-locator">
              {c.locator ?? c.selector ?? c.description ?? id}
            </span>
            <span data-testid="locator-candidate-status">
              {validated ? "validated" : "pending-validation"}
            </span>
            <button
              type="button"
              data-testid={`locator-select-${i}`}
              disabled={pending}
              onClick={() =>
                typeof onSelect === "function" &&
                onSelect({ type: "choose_locator_candidate", candidate_id: id })
              }
            >
              Select
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default LocatorCandidates;
