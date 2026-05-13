# S7-0108 — skip_step Command

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** S7-0110
**Blocked by:** S7-0103 (step_skipped event builder must exist), S7-0101 (run_id)

---

## Objective

Add a backend command handler for `skip_step` that allows the frontend to skip a failed or current step safely. The step is marked as skipped (not recorded), execution cursor advances or the run enters the correct post-skip state, and `step_skipped` event is emitted. Stale skip commands are rejected.

Before this story: there is no `skip_step` command handler; the frontend skip button has no backend effect.
After this story: `skip_step` command is registered; backend validates run_id and step_id; emits `step_skipped`; advances execution correctly; stale skips are rejected.

---

## Source Rules

- `PRD-04-CMD-002`: `skip_step` command with `step_id`; skip failed/current step.
- `PRD-04-BE-005`: `step_skipped` event emitted when step is skipped.
- `GOV-S7-C0-001`: Backend owns runtime truth — only backend confirms a step as skipped.
- `GOV-S7-C0-005`: Stale commands rejected with typed error.
- `GOV-S7-C0-009`: Negative tests required — skipped step must not emit step_recorded or code_update.

---

## Current Known Context

### What exists in the repo

- `server.py`: no `skip_step` routing
- `SUPPORTED_FRONTEND_COMMAND_TYPES`: does not include `"skip_step"`
- `agent.py`: step lifecycle management; no skip handling
- `runtime/event_contracts.py`: `build_step_skipped_payload()` will exist after S7-0103

### What gaps exist

- `"skip_step"` not in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- No command handler in `server.py`
- No emission of `step_skipped` on skip (S7-0103 adds the builder; this story wires the command)
- Execution cursor advancement after skip not implemented

### Current test status

- No tests for `skip_step` command

---

## Tests First

### Unit Tests

File: `tests/test_skip_step_command_contract.py`

```python
def test_skip_step_command_type_registered():  # PRD-04-CMD-002
    ...

def test_skip_step_command_requires_step_id():  # PRD-04-CMD-002
    ...

def test_skip_step_command_requires_run_id():  # PRD-04-CMD-002
    ...
```

### Contract Tests

File: `tests/test_skip_step_command_contract.py`

```python
def test_skip_step_handler_rejects_when_no_active_run():  # GOV-S7-C0-005
    ...

def test_skip_step_handler_rejects_mismatched_run_id():  # GOV-S7-C0-005
    ...

def test_skip_step_handler_rejects_unknown_step_id():  # PRD-04-CMD-002
    ...

def test_skip_step_emits_step_skipped_event():  # PRD-04-BE-005
    ...
```

### Integration Tests

File: `tests/test_skip_step_command_contract.py`

```python
def test_skip_step_advances_execution_cursor_safely():  # PRD-04-CMD-002
    ...

def test_skip_step_run_enters_correct_state_if_last_step():  # PRD-04-CMD-002
    ...
```

### Negative Tests (required)

File: `tests/test_skip_step_command_contract.py`

```python
def test_skipped_step_does_not_emit_step_recorded():  # GOV-S7-C0-009
    ...

def test_skipped_step_does_not_emit_code_update():  # GOV-S7-C0-009
    ...

def test_skip_step_rejected_for_already_recorded_step():  # PRD-04-CMD-002
    # cannot skip a step that is already recorded
    ...

def test_stale_skip_rejected_after_run_completed():  # GOV-S7-C0-005
    ...

def test_skip_step_without_step_id_rejected():  # PRD-04-CMD-002
    ...

def test_skip_step_without_run_id_rejected():  # PRD-04-CMD-002
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_skip_step_command_contract.py tests/test_step_terminal_events_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py                   ← add "skip_step" to SUPPORTED_FRONTEND_COMMAND_TYPES
server.py                                    ← add skip_step command routing
agent.py                                     ← add thin skip handling seam (calls step_skipped emit from S7-0103)
tests/test_skip_step_command_contract.py     ← new test file
```

Optional: `runtime/command_handlers.py` if it was created for S7-0107.

### Forbidden Files

```
frontend/
runtime/llm_runtime_controller.py
runtime/llm_policy_gateway.py
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Add `"skip_step"` to `SUPPORTED_FRONTEND_COMMAND_TYPES` in `event_contracts.py`.
2. In `server.py`, add routing for `skip_step` command:
   - Validate `run_id` against active run
   - Validate `step_id` against known pending/in-progress steps
   - Reject unknown step_id and already-recorded steps
   - Signal skip via `control_queue` or direct call to the step execution context
3. In `agent.py`, at the skip signal point: emit `step_skipped` (using builder from S7-0103), advance cursor.
4. After skip: execution cursor moves to the next pending step or run enters `completed` if last step.
5. Skip cannot be applied to an already-recorded step (idempotency check).

### Key Invariants

- `skip_step` only accepted when active run exists with matching `run_id`.
- `skip_step` only accepted for a step that is pending, in-progress, or failed — not recorded.
- After skip: `step_skipped` is emitted; no `step_recorded` or `code_update` follows for that step.
- Execution cursor advances: next pending step starts or run completes.
- Stale `skip_step` (no active run, wrong run_id, completed step) returns typed rejection.

### Known Risks

- Risk: Signaling a skip to the execution loop mid-execution may need careful sequencing.
  Mitigation: Use the existing `control_queue` pattern; test the ordering.
- Risk: Cursor advancement logic is in `agent.py` execution loop.
  Mitigation: Wire at the thinnest seam; do not restructure the loop.

---

## Coverage Requirement

```bash
python -m pytest tests/test_skip_step_command_contract.py --cov=server --cov-fail-under=80
```

---

## Acceptance Criteria

- [ ] `"skip_step"` registered in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- [ ] `skip_step` handler validates run_id and step_id
- [ ] Skipped step emits `step_skipped`, not `step_recorded`
- [ ] No `code_update` emitted for skipped step
- [ ] Stale/invalid skips rejected with typed error
- [ ] Execution cursor advances safely after skip
- [ ] All tests pass
- [ ] Coverage meets threshold
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `server.py` skip_step routing — committed
- [ ] `agent.py` skip seam — committed
- [ ] `tests/test_skip_step_command_contract.py` — committed (10+ tests)
- [ ] pytest output
- [ ] Regression output
- [ ] Coverage output

---

## Stop Conditions

- Skip signal mechanism requires restructuring the execution loop — stop; file a boundary story
- Cursor advancement after skip requires reading step order state that is not exposed — file story
- S7-0103 `step_skipped` builder is not done — block on S7-0103 first
