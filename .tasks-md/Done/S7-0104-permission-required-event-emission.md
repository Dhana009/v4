# S7-0104 — permission_required Event Emission

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** S7-0110
**Blocked by:** S7-0101 (run_id)

---

## Objective

Emit `permission_required` when the permission policy blocks or needs a user decision before a high-risk action can proceed. Frontend shows the permission request and waits for `permission_decision` command. No execution occurs before permission is granted.

Before this story: permission blocking may be handled internally without a typed frontend signal; frontend cannot show a permission request UI.
After this story: `permission_required` is emitted with action type, risk level, and message; execution is blocked until `permission_decision` is received; stale decisions are rejected.

---

## Source Rules

- `PRD-04-BE-006`: `permission_required` event when policy blocks/needs user decision.
- `PRD-04-CMD-005`: `permission_decision` command; accepted only for matching `run_id` and `operation_id`.
- `GOV-S7-C0-001`: Backend owns runtime truth — execution does not proceed until backend permission is granted.
- `GOV-S7-C0-009`: No negative tests → no merge. Stale and mismatched permission decisions must be tested.
- Sprint 6 Cluster 7 (S6-0701 etc.): Permission policy and capability registry were implemented in Sprint 6 — this story wires the frontend event emission only.

---

## Current Known Context

### What exists in the repo

- `runtime/permission_policy*.py` (or similar): Permission policy module from Sprint 6 Cluster 7
- `agent.py`: Permission checks exist but no `permission_required` typed event is emitted to frontend
- `SUPPORTED_FRONTEND_COMMAND_TYPES`: Does not include `permission_decision`
- `runtime/event_contracts.py`: No `build_permission_required_payload()` builder

### What gaps exist

- No `build_permission_required_payload()` builder
- No `permission_required` event emission to frontend
- `permission_decision` command not in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- No command handler for `permission_decision`
- Stale permission decision rejection is not implemented

### Current test status

- Sprint 6 Cluster 7 has permission policy tests
- No tests for frontend-facing `permission_required` event emission
- No tests for `permission_decision` command receipt

---

## Tests First

### Unit Tests

File: `tests/test_permission_required_event_contract.py`

```python
def test_build_permission_required_payload_includes_run_id():  # PRD-04-BE-006
    ...

def test_build_permission_required_payload_includes_operation_id():  # PRD-04-BE-006
    ...

def test_build_permission_required_payload_includes_action_type():  # PRD-04-BE-006
    ...

def test_build_permission_required_payload_includes_risk_level():  # PRD-04-BE-006
    ...

def test_build_permission_required_payload_includes_message():  # PRD-04-BE-006
    ...

def test_build_permission_required_payload_includes_optional_options():  # PRD-04-BE-006
    ...
```

### Contract Tests

File: `tests/test_permission_required_event_contract.py`

```python
def test_permission_required_event_type_field_correct():  # PRD-04-BE-006
    ...

def test_permission_required_uses_backend_event_envelope():  # PRD-04-BE-006
    ...

def test_permission_decision_command_registered_in_supported_types():  # PRD-04-CMD-005
    ...
```

### Integration Tests

File: `tests/test_permission_required_event_contract.py`

```python
def test_high_risk_action_emits_permission_required():  # PRD-04-BE-006
    ...

def test_no_execution_before_permission_decision():  # PRD-04-BE-006
    ...

def test_permission_approved_continues_only_for_matching_run_and_operation():  # PRD-04-CMD-005
    ...

def test_permission_denied_blocks_action_safely():  # PRD-04-CMD-005
    ...
```

### Negative Tests (required)

File: `tests/test_permission_required_event_contract.py`

```python
def test_stale_permission_decision_rejected():  # PRD-04-CMD-005
    # decision for expired/completed run_id rejected
    ...

def test_permission_decision_for_wrong_operation_id_rejected():  # PRD-04-CMD-005
    ...

def test_permission_decision_for_wrong_run_id_rejected():  # PRD-04-CMD-005
    ...

def test_build_permission_required_rejects_empty_run_id():  # PRD-04-BE-006
    ...

def test_build_permission_required_rejects_empty_action_type():  # PRD-04-BE-006
    ...

def test_execution_not_resumed_after_denied_permission():  # PRD-04-CMD-005
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_permission_required_event_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py                              ← add build_permission_required_payload()
server.py                                               ← add permission_decision command routing seam
agent.py                                                ← add permission_required emission before high-risk actions
tests/test_permission_required_event_contract.py        ← new test file
```

Note: Adding `permission_decision` to `SUPPORTED_FRONTEND_COMMAND_TYPES` in `event_contracts.py` is required.

### Forbidden Files

```
frontend/
runtime/llm_policy_gateway.py                          ← no LLM policy changes
runtime/permission_policy*.py                          ← no permission logic changes (just wire the event)
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Add `build_permission_required_payload(run_id, operation_id, action_type, risk_level, message, *, options=None)` to `event_contracts.py`.
2. Add `"permission_decision"` to `SUPPORTED_FRONTEND_COMMAND_TYPES`.
3. In `agent.py`, at the point where a high-risk action is flagged by the permission policy, emit `permission_required` and await the decision.
4. In `server.py`, add command routing for `permission_decision` — validate `run_id` and `operation_id`, reject stale decisions with `build_runtime_rejection_payload()`.
5. A pending permission state blocks further action on that operation until resolved.

### Key Invariants

- `permission_required` is emitted before any high-risk action proceeds.
- No execution occurs between `permission_required` emission and `permission_decision` receipt.
- `permission_decision` for a different `run_id` or `operation_id` is rejected immediately.
- `permission_decision` for a completed or expired run is rejected.
- A denied decision does not trigger execution; a safe failure path is taken instead.

### Known Risks

- Risk: Awaiting the decision may need an async gate in the execution loop.
  Mitigation: Use `asyncio.Queue` or an event flag already present in the control queue.
- Risk: The permission policy (Sprint 6) may have internal state that needs to be consulted.
  Mitigation: Read Sprint 6 permission policy module before implementing; wire at the seam without changing internal logic.

---

## Coverage Requirement

```bash
python -m pytest tests/test_permission_required_event_contract.py --cov=runtime.event_contracts --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_permission_required_payload()` exists in `runtime/event_contracts.py`
- [ ] `permission_decision` registered in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- [ ] `permission_required` emitted before high-risk action execution
- [ ] Command handler for `permission_decision` rejects stale decisions
- [ ] No execution proceeds without a valid permission decision
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `agent.py` permission gate seam — committed
- [ ] `server.py` `permission_decision` routing — committed
- [ ] `tests/test_permission_required_event_contract.py` — committed (12+ tests)
- [ ] pytest output
- [ ] Regression output
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Permission awaiting requires restructuring the execution loop — stop; file a story
- Sprint 6 permission policy module has a conflicting internal state model — file a bug ticket
- `permission_decision` routing cannot be added to `server.py` without a broad refactor — file a modular boundary story
