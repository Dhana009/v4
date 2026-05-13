# S7-0102 — step_validating and step_executing Events

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** S7-0110
**Blocked by:** S7-0101 (run_id must be stable)

---

## Objective

Emit typed progress events `step_validating` and `step_executing` so the frontend can show real execution progress per step and per operation, without inferring state from LLM output or absence of events.

Before this story: frontend has no signal that validation or execution of a specific step has begun; it may show a generic spinner or nothing.
After this story: backend emits `step_validating` before validation of a step/operation and `step_executing` during execution; frontend can show per-step progress accurately.

---

## Source Rules

- `PRD-04-BE-002`: `step_validating` event with `step_id`, `operation_id?`, `locator?`; frontend behavior: show validation status.
- `PRD-04-BE-003`: `step_executing` event with `step_id`, `operation_id?`, `action`; frontend behavior: show executing status.
- `PRD-03-FE-006`: `executing` interaction mode must be triggered by step execution events, not inferred.
- `GOV-S7-C0-001`: Backend owns runtime truth — events report what is happening now.
- `GOV-S7-C0-012`: Touch `agent.py` at thin seams only.

---

## Current Known Context

### What exists in the repo

- `runtime/event_contracts.py`: `build_backend_event_envelope()` available
- `agent.py`: validation and execution happen in the planning/execution loop; no step-level progress events are emitted
- `tests/test_backend_event_contract*.py`: generic envelope tests (Sprint 6)

### What gaps exist

- No `build_step_validating_payload()` builder
- No `build_step_executing_payload()` builder
- No emission points in `agent.py` for these events
- No tests for step progress event payloads or emission ordering

### Current test status

- No existing tests for `step_validating` or `step_executing`

---

## Tests First

### Unit Tests

File: `tests/test_step_progress_events_contract.py`

```python
def test_build_step_validating_payload_includes_step_id():  # PRD-04-BE-002
    ...

def test_build_step_validating_payload_includes_optional_operation_id():  # PRD-04-BE-002
    ...

def test_build_step_validating_payload_includes_optional_locator():  # PRD-04-BE-002
    ...

def test_build_step_executing_payload_includes_step_id():  # PRD-04-BE-003
    ...

def test_build_step_executing_payload_includes_action():  # PRD-04-BE-003
    ...

def test_build_step_executing_payload_includes_run_id():  # PRD-04-BE-003
    ...
```

### Contract Tests

File: `tests/test_step_progress_events_contract.py`

```python
def test_step_validating_event_type_field_correct():  # PRD-04-BE-002
    ...

def test_step_executing_event_type_field_correct():  # PRD-04-BE-003
    ...

def test_step_validating_uses_backend_event_envelope():  # PRD-04-BE-002
    ...

def test_step_executing_uses_backend_event_envelope():  # PRD-04-BE-003
    ...
```

### Integration Tests

File: `tests/test_step_progress_events_contract.py`

```python
def test_step_validating_emitted_before_step_executing():  # PRD-04-BE-002
    # ordering: validating before executing
    ...

def test_step_executing_emitted_before_step_recorded_or_step_failed():  # PRD-04-BE-003
    # ordering: executing before terminal events
    ...

def test_step_progress_events_include_consistent_run_id():  # PRD-04-BE-001
    # run_id matches run_started run_id
    ...
```

### Negative Tests (required)

File: `tests/test_step_progress_events_contract.py`

```python
def test_build_step_validating_rejects_empty_step_id():  # PRD-04-BE-002
    ...

def test_build_step_executing_rejects_empty_step_id():  # PRD-04-BE-003
    ...

def test_build_step_executing_rejects_empty_action():  # PRD-04-BE-003
    ...

def test_step_executing_not_emitted_before_step_validating():  # PRD-04-BE-002
    # execution without prior validation is invalid
    ...

def test_fake_success_not_emitted_if_step_executing_not_completed():  # GOV-S7-C0-001
    # step_recorded must not follow step_executing without actual execution
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_step_progress_events_contract.py tests/test_run_started_event_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py                         ← add build_step_validating_payload(), build_step_executing_payload()
agent.py                                           ← add thin emission seams at validation/execution points
tests/test_step_progress_events_contract.py        ← new test file
```

### Forbidden Files

```
frontend/
server.py
runtime/llm_runtime_controller.py
runtime/llm_policy_gateway.py
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Add `build_step_validating_payload(step_id, run_id, *, operation_id=None, locator=None)` to `event_contracts.py`.
2. Add `build_step_executing_payload(step_id, run_id, action, *, operation_id=None)` to `event_contracts.py`.
3. In `agent.py`, emit `step_validating` at the point where locator/validation begins for a step.
4. Emit `step_executing` at the point where the Playwright action is about to be executed.
5. Maintain ordering: `step_validating` always before `step_executing` for the same step.

### Key Invariants

- `step_validating` precedes `step_executing` for the same `step_id`.
- `step_executing` precedes `step_recorded` or `step_failed` for the same `step_id`.
- Both events carry `run_id` consistent with `run_started`.
- `operation_id` is included when the step has child operations.
- Empty `step_id` raises `ValueError`.
- Empty `action` in `step_executing` raises `ValueError`.

### Known Risks

- Risk: Finding the correct emission point in `agent.py` may require reading the execution loop carefully.
  Mitigation: Do not refactor the loop — add emissions only. If the loop structure prevents thin seam insertion, file a new story.
- Risk: Events might be emitted too frequently (once per retry instead of once per step).
  Mitigation: Emit validating/executing once per logical step, not per retry attempt. Add test to verify.

---

## Coverage Requirement

```bash
python -m pytest tests/test_step_progress_events_contract.py --cov=runtime.event_contracts --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_step_validating_payload()` and `build_step_executing_payload()` exist in `runtime/event_contracts.py`
- [ ] Both builders reject empty `step_id`
- [ ] `step_executing` builder rejects empty `action`
- [ ] Emission seams exist in `agent.py` at correct points
- [ ] Ordering verified: validating → executing → (recorded | failed)
- [ ] `run_id` consistency verified
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `agent.py` emission seams — committed
- [ ] `tests/test_step_progress_events_contract.py` — committed (10+ tests)
- [ ] pytest output showing all tests pass
- [ ] Regression suite output
- [ ] Coverage ≥ 95% output

---

## Stop Conditions

- Emission point requires restructuring the execution loop — stop; file a modular boundary story
- `step_executing` ordering cannot be guaranteed without a broad refactor — stop; escalate
- Coverage < 95% — add tests, do not lower threshold

---

## Evidence Recorded

- **Implementation commit:** `0dd4506`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_step_validating_payload()`, `build_step_executing_payload()`
  - `agent.py` — emission seam in `_mark_step_executing()` emitting step_validating then step_executing
- **Tests added:** `tests/test_step_progress_events_contract.py`
- **Validation commands:**
  - `python -m pytest tests/test_step_progress_events_contract.py -q`
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
