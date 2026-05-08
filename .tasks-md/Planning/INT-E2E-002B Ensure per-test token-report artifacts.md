# INT-E2E-002B Ensure per-test token-report artifacts

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: E2E / Evidence
Priority: P0

## Problem

Every E2E artifact must include token-report.json so cost changes are auditable.

## Source / architecture rule

- tests/e2e/harness.py
- tests/test_e2e_harness.py
- runtime/token_report.py
- Sprint 3 token diagnosis report

## Scope

Ensure E2ESession.close() or equivalent teardown writes token-report.json for every E2E artifact.

## Out of scope

- Changing telemetry emission
- Changing product behavior
- Hard CI budget failures

## Required tests

- harness writes token-report.json from backend stdout telemetry
- missing telemetry does not crash artifact finalization
- summary includes calls, total input tokens, largest call, top source

## Acceptance criteria

- token-report.json exists after E2E run
- report includes tool_schema_tokens
- existing harness tests pass

## Cost-aware verification plan

Run tests/test_e2e_harness.py.
Do not run E2E unless final acceptance.

## Evidence

To be filled during implementation.

## Notes

This keeps token optimization measurable for every E2E artifact.
