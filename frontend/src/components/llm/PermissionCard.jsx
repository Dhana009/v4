// components/llm/PermissionCard.jsx — Permission-required card
// S7-0607: permission_decision dispatched typed; no local approval.
import React from "react";

export function PermissionCard({ permission, onDecision }) {
  if (!permission) return null;
  const operation = permission.operation ?? permission.action ?? "operation";
  const risk_level = permission.risk_level ?? permission.risk ?? "unknown";
  const reason = permission.reason ?? permission.message ?? "";

  const decide = (decision) => {
    if (typeof onDecision === "function") {
      onDecision({
        type: "permission_decision",
        operation,
        decision, // "allow" | "deny"
      });
    }
  };

  return (
    <div data-testid="permission-card" className="aw-card aw-permission">
      <div className="aw-card-title">Permission required</div>
      <div data-testid="permission-operation">{operation}</div>
      <div data-testid="permission-risk">Risk: {risk_level}</div>
      {reason ? <div data-testid="permission-reason">{reason}</div> : null}
      <div className="aw-card-actions">
        <button
          type="button"
          data-testid="permission-allow"
          onClick={() => decide("allow")}
        >
          Allow
        </button>
        <button
          type="button"
          data-testid="permission-deny"
          onClick={() => decide("deny")}
        >
          Deny
        </button>
      </div>
    </div>
  );
}

export default PermissionCard;
