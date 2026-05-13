# S7-0107 — stop_run Command

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** S7-0110
**Blocked by:** S7-0101 (run_id needed for command routing)

---

## Objective

Add a backend command handler for `stop_run` that safely halts the active run when the frontend requests it. Stale stop_run commands (no active run, wrong run_id, duplicate) are rejected with a typed error. After stop, no further execution occurs and a typed event confirms the halt.

Before this story: there is no `stop_run` command handler; the frontend stop button has no backend effect.
After this story: `stop_run` command is registered, validated, and handled; active run is cancelled safely; frontend receives a typed confirmation; duplicate/stale stops are idempotent or rejected.

---

## Source Rules

- `PRD-04-CMD-001`: `stop_run` command with `run_id`; stops current run safely.
- `PRD-03-FE-007`: `recovery` / stop controls must send typed backend commands.
- `GOV-S7-C0-001`: Backend owns runtime truth — only backend decides the run is stopped.
- `GOV-S7-C0-005`: Stale commands must be rejected with typed error.
- `GOV-S7-C0-009`: No negative tests → no merge.

---

## Current Known Context

### What exists in the repo

- `server.py`: routes `confirmed`, `correction`, `option_selected` commands; no `stop_run` routing
- `SUPPORTED_FRONTEND_COMMAND_TYPES`: does not include `"stop_run"`
- `agent.py`: `_ws_disconnected` flag and `control_queue` exist for cancellation signaling
- `server.py`: `WebSocketRunSession` has `run_task` and `control_queue` that could be used to stop a run
- `event_contracts.py`: `build_runtime_rejection_payload()` exists for stale rejection

### What gaps exist

- `"stop_run"` not in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- No command handler for `stop_run` in `server.py`
- No typed event confirming that the run was stopped (a `run_stopped` or `run_completed` with stop status)
- No test for the stop flow

### Current test status

- No tests for `stop_run` command

---

## Tests First

### Unit Tests

File: `tests/test_stop_run_command_contract.py`

```python
def test_stop_run_command_type_registered_in_supported_types():  # PRD-04-CMD-001
    ...

def test_build_runtime_rejection_for_stale_stop_run():  # GOV-S7-C0-005
    ...

def test_stop_run_command_envelope_shape():  # PRD-04-CMD-001
    ...
```

### Contract Tests

File: `tests/test_stop_run_command_contract.py`

```python
def test_stop_run_handler_rejects_when_no_active_run():  # PRD-04-CMD-001
    ...

def test_stop_run_handler_rejects_mismatched_run_id():  # PRD-04-CMD-001
    ...

def test_stop_run_emits_typed_result_event():  # PRD-04-CMD-001
    # either run_completed with stop_reason or a dedicated run_stopped event
    ...
```

### Integration Tests

File: `tests/test_stop_run_command_contract.py`

```python
def test_stop_run_cancels_active_run():  # PRD-04-CMD-001
    ...

def test_no_further_execution_after_stop_run():  # PRD-04-CMD-001
    # step_executing not emitted after stop_run is processed
    ...

def test_stop_run_result_event_emitted_after_cancellation():  # PRD-04-CMD-001
    ...
```

### Negative Tests (required)

File: `tests/test_stop_run_command_contract.py`

```python
def test_stop_run_rejected_when_no_active_run():  # GOV-S7-C0-005
    ...

def test_stop_run_rejected_with_wrong_run_id():  # GOV-S7-C0-005
    ...

def test_duplicate_stop_run_is_safe():  # PRD-04-CMD-001
    # second stop_run after run is already stopped does not crash
    ...

def test_stop_run_without_run_id_field_rejected():  # PRD-04-CMD-001
    ...

def test_execution_does_not_resume_after_stop():  # PRD-04-CMD-001
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_stop_run_command_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py                  ← add "stop_run" to SUPPORTED_FRONTEND_COMMAND_TYPES; add stop result event builder if needed
server.py                                   ← add stop_run command routing and handler
tests/test_stop_run_command_contract.py     ← new test file
```

Optional: `runtime/command_handlers.py` (new module) if stop_run handler logic is non-trivial and would bloat `server.py`.

### Forbidden Files

```
frontend/
agent.py                                    ← agent.py control_queue may be read; do not add new logic beyond a cancel signal
runtime/llm_runtime_controller.py
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Add `"stop_run"` to `SUPPORTED_FRONTEND_COMMAND_TYPES` in `event_contracts.py`.
2. In `server.py`, add routing for `stop_run` command:
   - Validate `run_id` against active run session
   - If no active run or wrong `run_id`, call `build_runtime_rejection_payload()` and return
   - Cancel the active `run_task` using the existing `control_queue` or task cancellation
   - Emit a typed stop confirmation (either `run_completed` with `stop_reason="user_stop"` or a new `run_stopped` event)
3. The stop is idempotent: if run is already stopped, return a success acknowledgement (not an error).
4. After stop, the run session is cleaned up (no lingering state that would block a new run).

### Key Invariants

- `stop_run` only accepted when an active run session exists with matching `run_id`.
- After stop, no `step_executing`, `step_validating`, or `step_recorded` events are emitted.
- Duplicate `stop_run` (run already stopped) does not crash — returns safe acknowledgement.
- `stop_run` with wrong `run_id` returns a typed rejection with `rejection_code="stale_run_id"`.
- `stop_run` with missing `run_id` returns a typed rejection with `rejection_code="missing_run_id"`.

### Known Risks

- Risk: Cancelling `run_task` may leave partial WS state in server.py.
  Mitigation: Use existing disconnect grace/cleanup logic; verify with a test.
- Risk: `run_task.cancel()` may raise `CancelledError` that is not caught.
  Mitigation: Wrap in try/except in the handler; existing pattern in server.py for disconnects.

---

## Coverage Requirement

```bash
python -m pytest tests/test_stop_run_command_contract.py --cov=server --cov-fail-under=80
```

Note: `server.py` is harder to reach 95% on due to async/WS dependencies; 80% minimum with contract tests is acceptable. New focused command_handlers module (if created) targets 95%.

---

## Acceptance Criteria

- [ ] `"stop_run"` registered in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- [ ] `stop_run` handler rejects when no active run with typed error
- [ ] `stop_run` handler rejects mismatched `run_id` with typed error
- [ ] Active run is cancelled safely
- [ ] No further execution events after stop
- [ ] Duplicate stop is safe (no crash)
- [ ] All tests pass
- [ ] Coverage meets threshold
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `server.py` stop_run routing — committed
- [ ] `tests/test_stop_run_command_contract.py` — committed (10+ tests)
- [ ] pytest output
- [ ] Regression output
- [ ] Coverage output

---

## Stop Conditions

- `run_task.cancel()` requires changes to agent.py lifecycle that are not a thin seam — file story
- Cancellation leaks state that blocks a new run — investigate before merging
- Stale rejection cannot be returned without a WS send call that is hard to unit test — use an integration test instead
