// components/trace/ArtifactLinks.jsx — Backend artifact refs + redaction status
// S7-0904: only renders backend-supplied refs; surfaces redaction status.
import React from "react";

export function ArtifactLinks({ artifacts = [] }) {
  const list = Array.isArray(artifacts) ? artifacts : [];
  if (list.length === 0) return null;
  return (
    <ul data-testid="artifact-links" className="aw-artifacts">
      {list.map((a, i) => {
        const ref = a.ref ?? a.url ?? a.path ?? null;
        const label = a.label ?? a.kind ?? "artifact";
        const redacted = !!a.redacted;
        return (
          <li key={a.id ?? i} data-testid="artifact" data-redacted={redacted ? "1" : "0"}>
            <span data-testid="artifact-label">{label}</span>
            {ref ? (
              <span data-testid="artifact-ref">{String(ref)}</span>
            ) : null}
            <span data-testid="artifact-redaction-status">
              {redacted ? "redacted" : "not-redacted"}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default ArtifactLinks;
