# BUG-E2E-004 Exact text flow missing deterministic expected text derivation

Status: Done
Sprint: Sprint 3
Type: Bug
Severity: P0
Owner: Fast Path / E2E
Priority: P0
Started: 2026-05-08 21:23 IST

## Expected

The picked exact-text flow should use the picked element text as the deterministic expected text when the step intent provides an exact-text assertion but no explicit `expected_text` field.

## Actual

`exact_text_assertion_flow` did not reach `plan_ready` and instead asked the user for clarification.

Artifact:

`test-results/autoworkbench-e2e/exact_text_assertion_flow-20260508-203403-46422`

## Root cause

The deterministic fast-path builder only reads `expected_text` / `expectedText` from the step payload and does not derive it from the picked element text for exact-text assertions.

## Fix plan

- Derive `expected_text` from selected element context when the intent is exact-text and the explicit field is missing.

## Verification

- Focused tests:
  - `python -m pytest tests/test_deterministic_fast_path.py -q`
- Paid E2E:
  - `python -m pytest tests/e2e/test_exact_text_assertion_flow.py -q -s`
- Result:
  - deterministic fast path now derives exact expected text from the picked element
  - `exact_text_assertion_flow` passed with `0` LLM calls
