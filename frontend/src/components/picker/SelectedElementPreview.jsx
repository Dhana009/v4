// components/picker/SelectedElementPreview.jsx — Selected element preview
// S7-0705: redacts sensitive values (password/email/credit card style fields).
import React from "react";

const SENSITIVE_KEYS = [
  "password",
  "passwd",
  "secret",
  "token",
  "credit_card",
  "creditcard",
  "ccnumber",
  "cvv",
  "ssn",
  "email",
];

function redact(value, key) {
  if (value == null) return "";
  const lower = String(key ?? "").toLowerCase();
  if (SENSITIVE_KEYS.some((k) => lower.includes(k))) {
    return "•••••• (redacted sensitive)";
  }
  const text = String(value);
  if (text.length > 200) return `${text.slice(0, 200)}…`;
  return text;
}

export function SelectedElementPreview({ element }) {
  if (!element) {
    return (
      <div data-testid="selected-element-empty" className="aw-selected-empty">
        No element selected.
      </div>
    );
  }
  const fields = Object.entries(element).filter(([k]) => k !== "raw_html");
  return (
    <div data-testid="selected-element" className="aw-selected-element">
      <div className="aw-card-title">Selected element</div>
      <dl>
        {fields.map(([k, v]) => (
          <React.Fragment key={k}>
            <dt data-testid={`selected-field-${k}`}>{k}</dt>
            <dd data-testid={`selected-value-${k}`}>{redact(v, k)}</dd>
          </React.Fragment>
        ))}
      </dl>
    </div>
  );
}

export default SelectedElementPreview;
