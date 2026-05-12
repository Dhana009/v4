# Sprint 6 Cluster 11: Trace, Artifacts, Observability, Redaction

## Cluster Goal

Make every Complete LLM Mode run diagnosable.

The scenario spec says observability is part of the architecture. Each run must produce structured trace evidence, and every failure must answer what was expected, what happened, which layer failed, what evidence exists, and what the next legal action is.

The frontend spec says Trace tab must show event timeline, LLM calls/token estimates, context policy, locator decisions, permission decisions, precondition checks, failures/recoveries, artifact paths, and filters.

## Cluster Scope

**8 stories:**
- S6-1101: Structured trace event model completion
- S6-1102: Backend lifecycle/event trace emission
- S6-1103: LLM call artifact completeness
- S6-1104: Artifact bundle standardization
- S6-1105: Redaction policy and redaction report
- S6-1106: Failure context artifact
- S6-1107: Trace export and frontend trace data contract
- S6-1108: Cluster 11 observability integration proof

## Key Invariants

1. **Trace cannot mutate runtime truth** — trace mirrors but does not replace backend event stream
2. **No secrets in artifacts** — redaction policy applied before all writes
3. **Every failure has context** — failure-context.json with expected/actual/evidence/next-actions
4. **Paid E2E enforces artifacts** — blocked without required manifest/bundle
5. **Structured not raw** — no unbounded terminal dumps, bounded payload previews

## Allowed Implementation Modules

```
runtime/trace_events.py
runtime/trace_writer.py
runtime/artifact_manifest.py
runtime/artifact_bundle.py
runtime/redaction_policy.py
runtime/failure_context.py
runtime/trace_export.py
tests/e2e/artifacts/**
tests/test_trace_events.py
tests/test_artifact_bundle.py
tests/test_redaction_policy.py
tests/test_failure_context.py
tests/test_trace_export.py
```

## Forbidden

- No raw secrets in prompts/logs/artifacts
- No frontend lifecycle inference from trace
- No trace as truth for runtime state
- No raw full DOM unless explicit redacted artifact
- No unbounded payload dumps

## Definition of Done

✅ Structured trace event model exists and is tested.
✅ Backend lifecycle events produce trace records.
✅ LLM calls are artifacted on success and failure.
✅ Artifact bundle standard is enforced.
✅ Redaction policy and redaction report are enforced.
✅ Every failed run/test has failure-context.json.
✅ Frontend Trace tab receives structured trace data.
✅ Trace cannot mutate runtime truth.
✅ Paid E2E blocked without required artifacts.
✅ 95% coverage exists for new/changed modules.
✅ Sprint 6 regression guard passes.
