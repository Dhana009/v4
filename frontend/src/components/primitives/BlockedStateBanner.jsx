// components/primitives/BlockedStateBanner.jsx — Visible blocked-state notices
// S7-0712: surfaces wrong_page / missing_data / weak_locator with reason.
import React from "react";

export const BLOCKED_KINDS = ["wrong_page", "missing_data", "weak_locator"];

const KIND_LABELS = {
  wrong_page: "Wrong page",
  missing_data: "Missing data",
  weak_locator: "Weak locator",
};

export function BlockedStateBanner({ kind, reason, onResolve }) {
  if (!kind) return null;
  const safeKind = BLOCKED_KINDS.includes(kind) ? kind : "unknown";
  const label = KIND_LABELS[safeKind] ?? "Blocked";
  return (
    <div
      data-testid={`blocked-${safeKind}`}
      data-blocked-kind={safeKind}
      className="aw-blocked-banner"
      role="alert"
    >
      <div className="aw-blocked-label">{label}</div>
      {reason ? (
        <div data-testid="blocked-reason" className="aw-blocked-reason">
          {reason}
        </div>
      ) : null}
      {typeof onResolve === "function" ? (
        <button
          type="button"
          data-testid="blocked-resolve"
          onClick={() => onResolve({ kind: safeKind })}
        >
          Resolve
        </button>
      ) : null}
    </div>
  );
}

export default BlockedStateBanner;
