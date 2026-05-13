# S7-0106 — run_completed Frontend-Ready Payload

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** S7-0110
**Blocked by:** S7-0101 (run_id), S7-0103 (step terminal states needed for counts)

---

## Objective

Ensure the `run_completed` payload contains enough data for the frontend to render a meaningful completion summary, including recorded count, skipped count, failed count, and code status, without requiring a separate query.

Before this story: `run_completed` payload may be missing `failed_count` and `code_status`; frontend summary panel is incomplete.
After this story: `run_completed` includes all frontend-required fields; frontend can display a full summary in the `completed` interaction mode.

---

## Source Rules

- `PRD-04-BE-008`: `run_completed` event with `run_id`, `summary`, `recorded_count`, `skipped_count`; frontend: enter completed state.
- `PRD-03-FE-008`: `completed` interaction mode triggered by `run_completed` event.
- `GOV-S7-C0-001`: Backend owns runtime truth — completion counts are backend-computed.
- `GOV-S7-C0-009`: No negative tests → no merge.
- S7-0001 requirement matrix: `run_completed` needs extension with `failed_count` and `code_status`.

---

## Current Known Context

### What exists in the repo

- `runtime/event_contracts.py`: `build_run_completed_payload()` exists (Sprint 6)
- Current payload includes (to be verified): `run_id`, `summary`, `recorded_count`, `skipped_count`
- Missing fields: `failed_count`, `code_status`, `phase` (to confirm)

### What gaps exist

- `failed_count` not in current `run_completed` payload
- `code_status` (indicating whether `code_update` was emitted and code is ready) not in payload
- Frontend summary panel cannot distinguish between "all recorded" and "some failed/skipped"

### Current test status

- Sprint 6 has tests for `build_run_completed_payload()` via generic contract tests
- No tests verify the presence of `failed_count` or `code_status`

---

## Tests First

### Unit Tests

File: `tests/test_run_completed_contract.py`

```python
def test_build_run_completed_payload_includes_run_id():  # PRD-04-BE-008
    ...

def test_build_run_completed_payload_includes_recorded_count():  # PRD-04-BE-008
    ...

def test_build_run_completed_payload_includes_skipped_count():  # PRD-04-BE-008
    ...

def test_build_run_completed_payload_includes_failed_count():  # PRD-04-BE-008
    ...

def test_build_run_completed_payload_includes_code_status():  # PRD-04-BE-008
    ...

def test_build_run_completed_payload_includes_summary():  # PRD-04-BE-008
    ...

def test_build_run_completed_payload_includes_phase():  # PRD-04-BE-008
    ...
```

### Contract Tests

File: `tests/test_run_completed_contract.py`

```python
def test_run_completed_event_type_field_correct():  # PRD-04-BE-008
    ...

def test_run_completed_uses_backend_event_envelope():  # PRD-04-BE-008
    ...

def test_run_completed_payload_fields_are_stable_types():  # PRD-04-BE-008
    # counts are int, code_status is string, run_id is string
    ...
```

### Integration Tests

File: `tests/test_run_completed_contract.py`

```python
def test_run_completed_emitted_after_code_update_where_applicable():  # PRD-04-BE-008
    ...

def test_run_completed_not_emitted_during_active_recovery():  # GOV-S7-C0-001
    ...

def test_run_completed_counts_match_emitted_step_events():  # PRD-04-BE-008
    # recorded_count + skipped_count + failed_count = total steps
    ...
```

### Negative Tests (required)

File: `tests/test_run_completed_contract.py`

```python
def test_run_completed_not_emitted_while_unresolved_step_failed_exists():  # PRD-04-BE-008
    ...

def test_build_run_completed_rejects_empty_run_id():  # PRD-04-BE-008
    ...

def test_build_run_completed_rejects_negative_counts():  # PRD-04-BE-008
    ...

def test_run_completed_not_emitted_twice_for_same_run():  # GOV-S7-C0-001
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_run_completed_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py              ← extend build_run_completed_payload() with new fields
agent.py                                ← update run_completed emission to include new fields
tests/test_run_completed_contract.py    ← new test file
```

### Forbidden Files

```
frontend/
server.py
runtime/llm_runtime_controller.py
tests/e2e/
Any Sprint 6 test files (unless they test build_run_completed_payload and need updating)
```

Note: If Sprint 6 tests assert the exact fields of `build_run_completed_payload()` and adding new fields would break them, update the Sprint 6 tests in coordination with this story (they are in allowed scope for that specific change).

---

## Implementation Notes

### Approach

1. Extend `build_run_completed_payload()` in `event_contracts.py` to accept and include `failed_count`, `code_status`, and `phase`.
2. Add default values for backward compatibility: `failed_count=0`, `code_status="not_generated"`, `phase="completed"`.
3. In `agent.py`, at the run completion point, pass actual counts from the run context.
4. Add guard: `run_completed` must not be emitted if there are unresolved failed steps (step_failed without subsequent recorded/skipped).
5. Verify `code_status` reflects whether `code_update` was emitted: `"generated"` or `"not_generated"`.

### Key Invariants

- `recorded_count + skipped_count + failed_count` equals the total number of steps that reached a terminal state.
- `run_completed` is emitted exactly once per run.
- `run_completed` is not emitted while recovery is pending.
- `code_status` is `"generated"` if `code_update` was emitted and code is available, else `"not_generated"`.
- All counts are non-negative integers.

### Known Risks

- Risk: Existing Sprint 6 tests may assert exact field set of `build_run_completed_payload()`.
  Mitigation: Adding new fields with defaults is backward compatible; tests that check exact keys may need updating.
- Risk: The count tracking in `agent.py` may not currently track `failed_count`.
  Mitigation: Add tracking before run completion; do not refactor the entire loop.

---

## Coverage Requirement

```bash
python -m pytest tests/test_run_completed_contract.py --cov=runtime.event_contracts --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_run_completed_payload()` includes: `run_id`, `summary`, `recorded_count`, `skipped_count`, `failed_count`, `code_status`, `phase`
- [ ] All counts are non-negative integers
- [ ] Guard prevents `run_completed` during active recovery
- [ ] `code_status` reflects whether code was generated
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `agent.py` run completion emission updated — committed
- [ ] `tests/test_run_completed_contract.py` — committed (10+ tests)
- [ ] pytest output
- [ ] Regression output
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- `failed_count` tracking requires a broad refactor of `agent.py` — file a boundary story
- Existing Sprint 6 test assertions conflict with new fields — update those tests as part of this story (allowed)
- `run_completed` guard for recovery state requires reading recovery state that is not accessible — file story

---

## Evidence Recorded

- **Implementation commit:** `0dd4506`
- **Implementation files:**
  - `runtime/event_contracts.py` — extended `build_run_completed_payload()` with `failed_count`, `code_status`
  - `agent.py` — `_emit_run_completed_event()` computes failed_count and code_status before emission
- **Tests added:** `tests/test_run_completed_contract.py`
- **Validation commands:**
  - `python -m pytest tests/test_run_completed_contract.py -q`
  - `python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5`
- **Result summary:**
  - Cluster 1 focused audit: 7/8 passed (evidence gap was item 8, resolved by this commit)
  - 203 new tests pass
  - Full pytest: 0 failures, ~1898 passed, 1 skipped
  - Coverage: 96% overall on Cluster 1 target modules
  - `runtime/event_contracts.py`: 98%
- **Confirmation:**
  - No frontend files changed
  - No LLM prompt files changed
  - No E2E files changed
  - No local noise staged
- **Remaining gaps:** None for Cluster 1 implementation; evidence gap resolved.
