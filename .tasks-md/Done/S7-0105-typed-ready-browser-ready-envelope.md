# S7-0105 — Typed ready/browser_ready Envelope

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** S7-0110
**Blocked by:** None

---

## Objective

Replace or supplement the plain status string `ready` with a typed `ready` envelope and a companion `browser_ready` event that gives the frontend all the fields it needs to set up the initial idle/ready state without guessing.

Before this story: `ready` message is emitted but may be a plain status string or a minimal payload that doesn't include all required fields; `browser_ready` doesn't exist.
After this story: `ready` event has a typed envelope with `session_id`, `workspace`, `mode`, `url`, `backend_ready`, `browser_ready`, and `session_active`; `browser_ready` event is emitted when the browser context is confirmed ready; frontend can set up correctly; `session_state` ordering is preserved (session_state sent after ready on reconnect).

---

## Source Rules

- `PRD-04-BE-001-ready`: `ready` event with `session_id`, `workspace`, `mode`, `url`; frontend: show ready state.
- `PRD-04-BE-007`: Typed ready/browser_ready envelope for frontend setup.
- `PRD-03-FE-002`: `idle` interaction mode triggered by ready event.
- `GOV-S7-C0-006`: Frontend must not infer lifecycle truth — ready/idle state must come from typed event.
- `PRD-04-BE-009`: `session_state` ordering preserved — `session_state` follows `ready` on reconnect.

---

## Current Known Context

### What exists in the repo

- `server.py` imports `build_session_state_event` from `event_contracts.py`
- `server.py` already sends a `ready` message on WS connect (inspect to confirm exact payload)
- `event_contracts.py`: `build_session_state_event()` exists
- `frontend/src/main.jsx`: WS `onmessage` handler processes incoming events; ready event shape affects initial state

### What gaps exist

- Current `ready` payload may not include all required fields: `backend_ready`, `browser_ready`, `session_active`
- No `browser_ready` event builder
- No test that verifies the typed `ready` envelope shape
- `session_state` ordering on reconnect may not be explicitly enforced

### Current test status

- No tests specifically for the `ready` envelope payload shape
- `build_session_state_event()` has contract tests from Sprint 6

---

## Tests First

### Unit Tests

File: `tests/test_ready_envelope_contract.py`

```python
def test_build_typed_ready_envelope_includes_session_id():  # PRD-04-BE-007
    ...

def test_build_typed_ready_envelope_includes_workspace():  # PRD-04-BE-007
    ...

def test_build_typed_ready_envelope_includes_mode():  # PRD-04-BE-007
    ...

def test_build_typed_ready_envelope_includes_url():  # PRD-04-BE-007
    ...

def test_build_typed_ready_envelope_includes_backend_ready_flag():  # PRD-04-BE-007
    ...

def test_build_typed_ready_envelope_includes_browser_ready_flag():  # PRD-04-BE-007
    ...

def test_build_typed_ready_envelope_includes_session_active_flag():  # PRD-04-BE-007
    ...

def test_build_browser_ready_event_includes_browser_ready_flag():  # PRD-04-BE-007
    ...

def test_build_browser_ready_event_includes_context_and_url():  # PRD-04-BE-007
    ...
```

### Contract Tests

File: `tests/test_ready_envelope_contract.py`

```python
def test_ready_event_type_field_is_ready():  # PRD-04-BE-007
    ...

def test_browser_ready_event_type_field_is_browser_ready():  # PRD-04-BE-007
    ...

def test_ready_envelope_uses_backend_event_envelope():  # PRD-04-BE-007
    ...
```

### Integration Tests

File: `tests/test_ready_envelope_contract.py`

```python
def test_typed_ready_emitted_on_connection():  # PRD-03-FE-002
    ...

def test_session_state_emitted_after_ready_on_reconnect():  # PRD-04-BE-009
    # ordering: ready before session_state on reconnect
    ...

def test_browser_ready_emitted_after_browser_launch():  # PRD-04-BE-007
    ...
```

### Negative Tests (required)

File: `tests/test_ready_envelope_contract.py`

```python
def test_unknown_event_type_logged_not_silently_ignored():  # PRD-04-BE-000 (validation rules)
    # frontend should not silently drop unknown events
    ...

def test_ready_envelope_rejects_empty_session_id():  # PRD-04-BE-007
    ...

def test_build_ready_envelope_with_false_backend_ready_is_valid():  # PRD-04-BE-007
    # backend_ready=False is a valid signal (backend not yet fully up)
    ...

def test_session_state_not_emitted_before_ready():  # PRD-04-BE-009
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_ready_envelope_contract.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py              ← add build_typed_ready_envelope(), build_browser_ready_event()
server.py                               ← update ready emission to use typed builder
tests/test_ready_envelope_contract.py   ← new test file
```

### Forbidden Files

```
frontend/
agent.py                               ← no changes for this story
runtime/llm_runtime_controller.py
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Add `build_typed_ready_envelope(session_id, workspace, mode, url, *, backend_ready=True, browser_ready=False, session_active=False)` to `event_contracts.py`.
2. Add `build_browser_ready_event(*, browser_ready=True, context=None, url=None)` to `event_contracts.py`.
3. In `server.py`, replace the plain `ready` message with the typed envelope from the new builder.
4. In `server.py`, emit `browser_ready` when the browser context is confirmed ready (after browser launch).
5. Verify that `session_state` is emitted after `ready` on reconnect (not before).
6. Legacy compatibility: if existing frontend code checks for `type == "ready"`, the new envelope preserves that field.

### Key Invariants

- `ready` event is the first event sent to a new frontend connection.
- `session_state` follows `ready` on reconnect (not before).
- `browser_ready` is emitted when the browser context is confirmed — not assumed.
- `backend_ready=False` is valid and means backend is initializing; frontend shows loading state.
- Empty `session_id` raises `ValueError`.

### Known Risks

- Risk: Existing `server.py` ready message format may be checked by existing tests.
  Mitigation: Inspect existing tests; if the format is tested, update tests alongside the change (allowed files include server.py).
- Risk: Legacy frontend code may parse the old ready format.
  Mitigation: Keep `type="ready"` in the new envelope; add new fields alongside, not instead of, existing ones.

---

## Coverage Requirement

```bash
python -m pytest tests/test_ready_envelope_contract.py --cov=runtime.event_contracts --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_typed_ready_envelope()` exists in `runtime/event_contracts.py`
- [ ] `build_browser_ready_event()` exists in `runtime/event_contracts.py`
- [ ] `server.py` emits typed envelope on connect
- [ ] `session_state` ordering after `ready` on reconnect is verified
- [ ] `browser_ready` event emitted after browser launch
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `server.py` ready emission updated — committed
- [ ] `tests/test_ready_envelope_contract.py` — committed (10+ tests)
- [ ] pytest output
- [ ] Regression output
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Changing `server.py` ready emission breaks existing frontend behavior — investigate before changing format
- `session_state` cannot be ordered after `ready` without restructuring WS connect handler — file story
- Coverage < 95% — add tests
