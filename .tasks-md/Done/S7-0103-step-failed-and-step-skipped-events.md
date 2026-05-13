# S7-0103 — step_failed and step_skipped Events

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** S7-0110
**Blocked by:** S7-0101 (run_id), S7-0102 (step progress ordering)

---

## Objective

Expose distinct typed failure and skip states rather than hiding everything under `recovery_needed`. Frontend must know whether a step explicitly failed (needs recovery/user action) or was explicitly skipped (run can continue), without inferring from prose or absence of success.

Before this story: failure and skip share or overlap with `recovery_needed`, making it impossible for the frontend to distinguish them cleanly.
After this story: `step_failed` is a distinct event emitted when a step execution fails; `step_skipped` is a distinct event emitted when a step is deliberately skipped; `recovery_needed` remains for situations requiring user input.

---

## Source Rules

- `PRD-04-BE-004`: `step_failed` event with `step_id`, `operation_id?`, `error`, `status`; frontend behavior: show failed/recovery pending.
- `PRD-04-BE-005`: `step_skipped` event with `step_id`, `reason`; frontend behavior: mark skipped.
- `PRD-03-FE-007`: `recovery` interaction mode triggered by `recovery_needed` (not `step_failed` alone).
- `GOV-S7-C0-001`: Backend owns runtime truth — a step is failed or skipped only when backend confirms it.
- `GOV-S7-C0-009`: No negative tests → no merge. Both events require negative tests.

---

## Current Known Context

### What exists in the repo

- `runtime/event_contracts.py`: `build_recovery_needed_payload()` exists (Sprint 6)
- `agent.py`: failure handling emits `recovery_needed`; no distinct `step_failed` event
- `runtime/recovery_manager.py`: classifies failure types (Sprint 6)
- Step skip behavior exists (skip_step command planned in S7-0108) but no typed event is emitted

### What gaps exist

- No `build_step_failed_payload()` builder
- No `build_step_skipped_payload()` builder
- No distinction between "step failed and recovery needed" vs "step failed and run can continue"
- `step_failed` is not emitted when a step fails — only `recovery_needed` (or nothing) is emitted
- `step_skipped` is not emitted when a step is skipped

### Current test status

- `tests/test_backend_event_contract*.py`: generic coverage only
- No tests for `step_failed` or `step_skipped` distinct events

---

## Tests First

### Unit Tests

File: `tests/test_step_terminal_events_contract.py`

```python
def test_build_step_failed_payload_includes_step_id():  # PRD-04-BE-004
    ...

def test_build_step_failed_payload_includes_error():  # PRD-04-BE-004
    ...

def test_build_step_failed_payload_includes_status():  # PRD-04-BE-004
    ...

def test_build_step_failed_payload_includes_optional_operation_id():  # PRD-04-BE-004
    ...

def test_build_step_failed_payload_includes_run_id():  # PRD-04-BE-004
    ...

def test_build_step_skipped_payload_includes_step_id():  # PRD-04-BE-005
    ...

def test_build_step_skipped_payload_includes_reason():  # PRD-04-BE-005
    ...

def test_build_step_skipped_payload_includes_run_id():  # PRD-04-BE-005
    ...
```

### Contract Tests

File: `tests/test_step_terminal_events_contract.py`

```python
def test_step_failed_event_type_field_correct():  # PRD-04-BE-004
    ...

def test_step_skipped_event_type_field_correct():  # PRD-04-BE-005
    ...

def test_step_failed_uses_backend_event_envelope():  # PRD-04-BE-004
    ...

def test_step_skipped_uses_backend_event_envelope():  # PRD-04-BE-005
    ...
```

### Integration Tests

File: `tests/test_step_terminal_events_contract.py`

```python
def test_execution_failure_emits_step_failed():  # PRD-04-BE-004
    ...

def test_recovery_needed_still_emitted_after_step_failed_when_unresolved():  # PRD-03-FE-007
    # step_failed and recovery_needed are not mutually exclusive
    ...

def test_step_skip_emits_step_skipped_not_step_failed():  # PRD-04-BE-005
    ...

def test_run_completed_blocked_if_unresolved_recovery_remains():  # PRD-04-BE-008
    # run cannot complete while a step is in unresolved failed/recovery state
    ...
```

### Negative Tests (required)

File: `tests/test_step_terminal_events_contract.py`

```python
def test_step_failed_followed_by_step_recorded_is_invalid():  # GOV-S7-C0-001
    # a failed step cannot also emit step_recorded
    ...

def test_step_skipped_followed_by_step_recorded_is_invalid():  # GOV-S7-C0-001
    # a skipped step cannot also emit step_recorded
    ...

def test_build_step_failed_rejects_empty_step_id():  # PRD-04-BE-004
    ...

def test_build_step_failed_rejects_empty_error():  # PRD-04-BE-004
    ...

def test_build_step_skipped_rejects_empty_reason():  # PRD-04-BE-005
    ...

def test_step_failed_not_emitted_when_recovery_resolves_successfully():  # GOV-S7-C0-001
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_step_terminal_events_contract.py tests/test_step_progress_events_contract.py tests/test_run_started_event_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py                          ← add build_step_failed_payload(), build_step_skipped_payload()
agent.py                                            ← add thin emission seams at failure and skip points
tests/test_step_terminal_events_contract.py         ← new test file
```

### Forbidden Files

```
frontend/
server.py
runtime/llm_runtime_controller.py
runtime/recovery_manager.py                        ← no changes to failure classification logic
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Add `build_step_failed_payload(step_id, run_id, error, status, *, operation_id=None)` to `event_contracts.py`.
2. Add `build_step_skipped_payload(step_id, run_id, reason)` to `event_contracts.py`.
3. In `agent.py`, emit `step_failed` when an execution failure occurs, before emitting `recovery_needed`.
4. In `agent.py`, emit `step_skipped` when a step is deliberately skipped (via `skip_step` command, handled in S7-0108).
5. `recovery_needed` continues to be emitted when recovery is needed — the two events are NOT mutually exclusive.
6. A step that is failed and requires user input emits both: `step_failed` (to mark failure state) and `recovery_needed` (to request user guidance).

### Key Invariants

- `step_failed` marks the step as failed. It does not prevent `recovery_needed` from following.
- `step_skipped` marks the step as explicitly skipped. It does not emit `step_recorded` or `code_update`.
- A failed step cannot emit `step_recorded` — only `step_failed` or recovery → eventual `step_recorded` if repair succeeds.
- `run_completed` must not fire while any step has an unresolved `step_failed` without a subsequent `step_recorded`, `step_skipped`, or explicit run abort.
- Both events carry `run_id` consistent with `run_started`.

### Known Risks

- Risk: Adding `step_failed` emission before `recovery_needed` may cause ordering-sensitive tests to fail.
  Mitigation: Check Sprint 6 recovery tests; if ordering is tested, update test expectations carefully.
- Risk: Skip behavior depends on S7-0108 (skip_step command) which is a separate story.
  Mitigation: Emit the event builder and emission seam in this story; the command handler in S7-0108 calls the emit.

---

## Coverage Requirement

```bash
python -m pytest tests/test_step_terminal_events_contract.py --cov=runtime.event_contracts --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_step_failed_payload()` and `build_step_skipped_payload()` exist in `runtime/event_contracts.py`
- [ ] `step_failed` is emitted at execution failure point in `agent.py`
- [ ] `step_skipped` emission seam exists (used by S7-0108 skip_step handler)
- [ ] `recovery_needed` still emitted where appropriate
- [ ] A failed/skipped step cannot also emit `step_recorded`
- [ ] `run_completed` blocked if unresolved recovery remains (contract test)
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `agent.py` emission seams — committed
- [ ] `tests/test_step_terminal_events_contract.py` — committed (12+ tests)
- [ ] pytest output showing all tests pass
- [ ] Regression suite output
- [ ] Coverage ≥ 95% output

---

## Stop Conditions

- Emitting `step_failed` breaks existing Sprint 6 recovery tests — investigate before fixing
- A step can emit both `step_failed` and `step_recorded` in a code path — stop; this is a bug
- Recovery manager needs changes to support the event split — file a separate story

---

## Evidence Recorded

- **Implementation commit:** `0dd4506`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_step_failed_payload()`, `build_step_skipped_payload()`
  - `agent.py` — emission seam in `_mark_step_failed()` (before recovery_needed) and `_mark_step_skipped()`
- **Tests added:** `tests/test_step_terminal_events_contract.py`
- **Validation commands:**
  - `python -m pytest tests/test_step_terminal_events_contract.py -q`
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
