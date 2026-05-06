# Skill: Observability and Trace

## Purpose
Make backend, LLM, locator, frontend, and E2E behavior debuggable without terminal guessing.

## When to use
Use when touching logging, trace_summary, LLM telemetry, E2E artifacts, Trace tab, failure handling, locator decisions, token reporting, WebSocket lifecycle.

## Source of truth
- Frontend/UI Trace tab spec
- Backend/UI state contract
- LLM Runtime Policy observability requirements

## Non-negotiable rules
1. Logs must be compact but useful.
2. Every failure must have a typed classification.
3. Trace must expose what happened, why, evidence, and next action.
4. LLM calls must log purpose/model/context/skills/tools/tokens.
5. Locator decisions must show candidates, selected locator, validation count, confidence.
6. E2E failures must capture artifacts.
7. Do not dump full DOM/logs by default.
8. UI should show trace_summary; detailed trace should be filterable.
9. Trace reports behavior; it does not define behavior.

## Required trace fields
```text
run_id
phase
event_type
step_id
operation_id
purpose
model
context_level
skills_loaded
tools_exposed
token_estimate
duration_ms
status
error_type
reason
artifact_path
```

## Required failure evidence
```text
what failed
where it failed
expected
actual
evidence
attempted recoveries
next allowed actions
artifact links
```

## Required tests
- trace_summary update tests
- LLM telemetry tests
- locator trace tests
- E2E artifact capture tests
- WebSocket disconnect/reconnect trace tests where relevant

## Verification commands
```bash
python -m pytest tests/test_*trace* tests/test_*telemetry* tests/test_e2e_harness.py -q
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- failure is only generic error text
- no artifact path exists for E2E failure
- LLM calls lack purpose/token trace
- logs become too verbose for normal runs
- UI cannot display latest blocking reason

## Reporting format
Report:
1. Trace fields added/changed
2. Error classifications
3. Artifacts captured
4. Tests/results
5. Noise/token/log risks
