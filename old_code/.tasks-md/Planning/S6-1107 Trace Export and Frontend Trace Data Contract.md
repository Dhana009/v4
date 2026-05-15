# S6-1107: Trace Export and Frontend Trace Data Contract

## Objective

Provide the frontend Trace tab with structured data, not terminal spam.

## Acceptance Criteria

- [ ] Trace query/export command implemented
- [ ] Trace filters supported (phase, event_type, status, time range)
- [ ] Trace row schema matches frontend expectations
- [ ] Failure detail row schema includes expected/actual/evidence
- [ ] Artifact links are safe and resolvable
- [ ] Redacted payload previews are safe for display
- [ ] Frontend can render without mutation
- [ ] Contract tests verify schema compatibility

## Constraints

- No frontend mutation from trace data
- No raw sensitive data in payload previews
- No backend lifecycle guessing from trace export
- Filters are safe to expose to frontend
- Artifact links are scoped to current artifact bundle

## Integration Points

- Works with S6-1101 (trace event model)
- Works with S6-1102 (lifecycle trace)
- Works with S6-1104 (artifact bundle)
- Works with S6-1105 (redaction)
- Works with S6-1106 (failure context)
