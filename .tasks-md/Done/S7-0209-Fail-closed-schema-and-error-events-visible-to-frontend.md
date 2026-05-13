# S7-0209 Fail-Closed Schema and Error Events Visible to Frontend

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0209  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `02_LLM_RUNTIME.md` (fail-closed policy).
2. **Sprint 7 Governance** — No silent failures; errors visible.
3. **Cluster 2 Goal** — Schema errors and provider errors visible to frontend.

---

## Objective

Emit typed error events (`schema_error`, `provider_error`, `malformed_output_error`) so frontend knows when LLM output fails validation or provider fails. Today, errors may be logged but not sent to frontend. After S7-0209, frontend receives explicit error events and can show error card.

---

## Tests First

### Unit Tests

**Test: Schema validation failure**
- Given invalid LLM output (missing field, wrong type), validation fails.
- Error logged and event marked for frontend.

**Test: Provider error handling**
- Given provider timeout or API error, caught gracefully.
- Error type and message extracted safely.

### Contract Tests

**Test: schema_error event**
- Fields: purpose (str), error_type (str), error_message (str), retry_count (int), max_retries (int), timestamp (ISO).
- error_type examples: "missing_field", "invalid_type", "malformed_json".

**Test: provider_error event**
- Fields: purpose (str), error_type (str), error_message (str), retryable (bool), timestamp (ISO).
- error_type examples: "timeout", "rate_limit", "api_error".

**Test: malformed_output_error event**
- Fields: purpose (str), error_message (str), example_output (str | null), timestamp (ISO).
- example_output: safe sample (no secrets).

### Integration Tests

**Test: Schema retry exhausted → event**
- LLM output fails schema validation 3 times.
- schema_error event emitted with retry_count=3, max_retries=3.
- Plan not created; execution skipped.

**Test: Provider timeout → event**
- LLM call times out.
- provider_error event emitted with retryable=false.
- Frontend shows "LLM provider error" card.

### Negative Tests

**Test: Valid output not flagged**
- Verify valid outputs do not emit error events.

**Test: Error message is clean**
- Verify no raw Python tracebacks, no API key leakage.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add: `SchemaError`, `ProviderError`, `MalformedOutputError` event classes.

- **Modify:** `runtime/llm_runtime_controller.py`
  - Catch schema validation failures.
  - Catch provider exceptions.
  - Emit typed error events.

- **Modify:** `runtime/schema_validation_policy.py` or similar
  - Error extraction and safe message formatting.

- **New tests:** `tests/test_error_events.py`

### Forbidden Changes

- No silent error suppression.
- No traceback in events.
- No API key leakage.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Schema errors caught and reported.**
✅ **Provider errors caught and reported.**
✅ **No secret leakage in error messages.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Error not reported to frontend.
- ❌ Secret/traceback in error message.

---

## Evidence Recorded

- **Implementation commit:** `0f2198b`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `_redact_api_keys()` helper (regex strips `sk-*`), `build_schema_error_event` (rejects negative retry_count, redacts sk-*), `build_provider_error_event` (redacts sk-*), `build_malformed_output_error_event` (truncates safe_output_sample to 2000 chars)
- **Tests added:** `tests/test_error_events.py` (25 tests: type/purpose/fields, envelope, schema_version, sk-* redaction, no prompt dump, safe sample truncation, negative validation, fail-closed invariants)
- **Validation commands:**
  - `python -m pytest tests/test_error_events.py -q`
  - `python -m pytest -q`
- **Result summary:**
  - 25 passed
  - Full suite: 2078 passed, 0 failed, 1 skipped
  - `runtime/event_contracts.py` coverage: 99%
- **Confirmation:**
  - `sk-abc123` redacted from error_message before event emission
  - `safe_output_sample` truncated at 2000 chars (total payload < 50000 bytes)
  - type ≠ plan_ready (schema_error), type ≠ step_recorded (provider_error)
  - Negative retry_count raises ValueError
- **Remaining gaps:** None.

