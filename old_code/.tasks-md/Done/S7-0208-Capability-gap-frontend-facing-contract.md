# S7-0208 Capability Gap Frontend-Facing Contract

**Sprint:** Sprint 7  
**Cluster:** 2  
**Story:** S7-0208  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `02_LLM_RUNTIME.md` (capability constraints).
2. **Frontend UI Spec** — Frontend must show "not supported" state.
3. **Cluster 2 Goal** — Unsupported actions visible, not silent failures.

---

## Objective

Emit typed `capability_gap` events when user/LLM attempts unsupported action (e.g., unsupported assertion type, unsupported browser capability). Today, unsupported actions may fail silently or fake success. After S7-0208, frontend shows clear "not supported" card with reason and next step.

---

## Tests First

### Unit Tests

**Test: Capability registry lookup**
- Given action type and assertion type, check if supported.
- Return bool + reason if unsupported.

### Contract Tests

**Test: capability_gap event**
- Fields: action (str), assertion_type (str), reason (str), next_legal_action (str), timestamp (ISO).
- reason: human-friendly explanation.
- next_legal_action: what user can do instead.

### Integration Tests

**Test: Unsupported assertion → capability_gap**
- Plan includes unsupported assertion type.
- capability_gap event emitted before execution attempt.
- Execution skipped.

### Negative Tests

**Test: Supported action not flagged**
- Verify only unsupported actions emit capability_gap.

---

## Implementation Boundaries

### Allowed Changes

- **Modify:** `runtime/event_contracts.py`
  - Add: `CapabilityGap` event class.

- **New or modify:** `runtime/capability_registry.py`
  - Function: `check_capability(action, assertion_type) → tuple[bool, str]`.
  - Exhaustive list of supported vs. unsupported.

- **Modify:** `runtime/llm_runtime_controller.py` or step runner
  - Before executing action, check capability.
  - If gap, emit capability_gap and skip execution.

- **New tests:** `tests/test_capability_gap_event.py`

### Forbidden Changes

- No silent failure on unsupported action.

---

## Acceptance Criteria

✅ **All tests green.**
✅ **Unsupported actions caught and reported.**
✅ **No silent failures.**
✅ **Evidence: test file, commits, regression green.**

---

## Stop Conditions

- ❌ Regression failure.
- ❌ Unsupported action executes anyway.

---

## Evidence Recorded

- **Implementation commit:** `0f2198b`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_capability_gap_event` (validates action/reason/next_legal_action, default severity="error")
  - `runtime/capability_registry.py` — pre-existing; `BASELINE_CAPABILITIES` frozenset, `get_capability_status()`, `CapabilityStatus` enum already present; case-insensitive lookup confirmed
- **Tests added:** `tests/test_capability_gap_event.py` (21 tests: type, action, reason, next_legal_action, envelope, schema_version, severity, contract invariants, registry unit tests, negative validation)
- **Validation commands:**
  - `python -m pytest tests/test_capability_gap_event.py -q`
  - `python -m pytest -q`
- **Result summary:**
  - 21 passed
  - Full suite: 2078 passed, 0 failed, 1 skipped
  - `runtime/event_contracts.py` coverage: 99%
- **Confirmation:**
  - type ≠ step_recorded, ≠ code_update
  - `drag_and_drop` not in BASELINE_CAPABILITIES
  - `click`, `fill`, `hover` in BASELINE_CAPABILITIES
  - Case-insensitive: `CLICK` → SUPPORTED
- **Remaining gaps:** None.

