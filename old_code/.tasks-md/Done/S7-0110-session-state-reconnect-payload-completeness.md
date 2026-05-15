# S7-0110 — session_state Reconnect Payload Completeness

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** None (final Cluster 1 story)
**Blocked by:** S7-0101, S7-0102, S7-0103, S7-0104, S7-0105, S7-0106, S7-0107, S7-0108, S7-0109

---

## Objective

Ensure the `session_state` event emitted on connect/reconnect contains the complete backend truth that the frontend needs to restore its UI without guessing — including `run_id`, `phase`, `plan`, `pending_steps`, `recorded_steps`, `code_preview`, `recovery_state`, and `replay_state` where available. Frontend stale local state cannot override backend `session_state`.

Before this story: `build_session_state_event()` exists but payload may be incomplete; reconnect may not send all fields; frontend may not fully restore from it.
After this story: `session_state` payload is complete; emitted on every connect/reconnect after `ready`; frontend can fully restore without inference.

---

## Source Rules

- `PRD-04-BE-009`: `session_state` event with full snapshot; frontend behavior: reconcile frontend after reconnect/load.
- `PRD-03-FE-010`: Session state reconnect restores UI from backend truth.
- `GOV-S7-C0-006`: Frontend must not infer lifecycle truth — session_state is the source of truth on reconnect.
- `GOV-S7-C0-001`: Backend owns runtime truth — stale local frontend state cannot override backend session_state.
- S7-0105: `session_state` ordering: must follow `ready` on reconnect (not before).

---

## Current Known Context

### What exists in the repo

- `runtime/event_contracts.py`: `build_session_state_event()` exists (Sprint 6)
- `server.py`: imports `build_session_state_event` and calls it on reconnect
- `runtime/session_store.py`: `restore_session_state()` returns `SessionState` with only `session_id`, `current_step_index`, `status`
- Current `session_state` payload fields (to verify): `session_id`, `status` — likely missing: `run_id`, `phase`, `plan`, `pending_steps`, `recorded_steps`, `code_preview`, `recovery_state`, `replay_state`

### What gaps exist

- `build_session_state_event()` likely has minimal fields; needs extension
- `session_store.py` `restore_session_state()` returns minimal state; needs full snapshot
- No test verifying all required reconnect fields are present
- `phase` (planning/executing/recovery/completed) is not in current payload
- `plan` (pending plan if in plan_review mode) is not in current payload
- `pending_steps` and `recorded_steps` are not in current payload
- `code_preview` is not in current payload
- `recovery_state` is not in current payload

### Current test status

- Sprint 6 has some `build_session_state_event()` tests
- No tests verify complete reconnect payload

---

## Tests First

### Unit Tests

File: `tests/test_session_state_reconnect.py`

```python
def test_build_session_state_includes_run_id():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_phase():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_plan_when_in_plan_review():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_pending_steps():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_recorded_steps():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_code_preview():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_recovery_state_when_in_recovery():  # PRD-04-BE-009
    ...

def test_build_session_state_includes_replay_state_when_in_replay():  # PRD-04-BE-009
    ...
```

### Contract Tests

File: `tests/test_session_state_reconnect.py`

```python
def test_session_state_event_type_correct():  # PRD-04-BE-009
    ...

def test_session_state_uses_backend_event_envelope():  # PRD-04-BE-009
    ...

def test_session_state_fields_are_stable_types():  # PRD-04-BE-009
    # run_id is string, phase is string, steps are lists, code_preview is string or null
    ...
```

### Integration Tests

File: `tests/test_session_state_reconnect.py`

```python
def test_session_state_emitted_after_ready_on_reconnect():  # S7-0105, PRD-04-BE-009
    ...

def test_session_state_emitted_on_new_connection():  # PRD-04-BE-009
    ...

def test_frontend_can_consume_session_state_without_guessing():  # PRD-03-FE-010
    # session_state alone is sufficient to restore all frontend modes
    ...
```

### Negative Tests (required)

File: `tests/test_session_state_reconnect.py`

```python
def test_stale_local_frontend_state_cannot_override_backend_session_state():  # GOV-S7-C0-001
    # backend session_state takes precedence over any local frontend state
    # verified by checking that session_state payload has all required fields
    ...

def test_session_state_not_emitted_before_ready():  # S7-0105
    ...

def test_build_session_state_with_no_active_run_returns_idle_phase():  # PRD-04-BE-009
    ...

def test_build_session_state_rejects_unknown_phase_value():  # PRD-04-BE-009
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_session_state_reconnect.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py                      ← extend build_session_state_event() with all required fields
runtime/session_store.py                        ← extend restore_session_state() to return full snapshot
server.py                                       ← verify session_state emission order (after ready)
tests/test_session_state_reconnect.py           ← new test file
```

### Forbidden Files

```
frontend/
agent.py                                        ← no changes for session_state shape (agent provides data; it does not build the event)
runtime/llm_runtime_controller.py
tests/e2e/
Any Sprint 6 test files
```

---

## Implementation Notes

### Approach

1. Audit `build_session_state_event()` in `event_contracts.py` — identify missing fields.
2. Extend `build_session_state_event()` to accept and include: `run_id`, `phase`, `plan`, `pending_steps`, `recorded_steps`, `code_preview`, `recovery_state`, `replay_state`.
3. All new fields have sensible defaults: `None` or `[]` when not applicable.
4. Extend `restore_session_state()` in `session_store.py` to return all these fields from the active session.
5. In `server.py`, verify that `session_state` is sent after `ready` on reconnect — if not, fix ordering.
6. `session_state` is the single source of truth for frontend reconnect — frontend must be able to render any mode from it.

### Key Invariants

- `session_state` is emitted on every connect and reconnect, after `ready`.
- `session_state` payload contains all fields needed for frontend to render any interaction mode.
- `session_state` is always current backend truth — frontend cannot override it with stale local state.
- Missing/unknown `phase` raises `ValueError` in the builder (must be a known phase string).
- `pending_steps` and `recorded_steps` are lists (empty list if none).

### Known Risks

- Risk: Gathering all fields (run_id, plan, steps, code_preview, recovery_state) requires access to live agent state.
  Mitigation: Pass these fields explicitly from the server-side call; do not have the builder reach into the agent.
- Risk: Existing Sprint 6 tests for `build_session_state_event()` may assert minimal fields.
  Mitigation: Adding new fields with defaults is backward compatible; check and update Sprint 6 tests if needed.
- Risk: This is the last Cluster 1 story — all prior stories (0101–0109) must be done before full validation.
  Mitigation: Plan for this; implement the payload completeness incrementally, verifying each new field with its source story.

---

## Coverage Requirement

```bash
python -m pytest tests/test_session_state_reconnect.py --cov=runtime.event_contracts --cov=runtime.session_store --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_session_state_event()` includes all fields: `run_id`, `phase`, `plan`, `pending_steps`, `recorded_steps`, `code_preview`, `recovery_state`, `replay_state`
- [ ] All fields have typed defaults (not undefined/missing)
- [ ] `session_state` emitted after `ready` on reconnect (ordering verified)
- [ ] Frontend can determine interaction mode from `session_state` alone
- [ ] Stale frontend state cannot override backend session_state (architectural test)
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `runtime/session_store.py` extended — committed
- [ ] `server.py` ordering verified — committed (or confirmed unchanged if already correct)
- [ ] `tests/test_session_state_reconnect.py` — committed (12+ tests)
- [ ] pytest output
- [ ] Regression output
- [ ] Coverage ≥ 95%
- [ ] Cluster 1 completion evidence: all 10 stories Done

---

## Stop Conditions

- Gathering `plan` and `recorded_steps` from live agent state is not straightforward — file a state-access boundary story
- `session_state` size becomes very large due to full recorded steps — add a `compact_session_state` option and test both
- Ordering fix in `server.py` requires restructuring the connect handler — file a new story
- Sprint 6 `session_state` tests conflict with new fields — update them as part of this story (allowed)

---

## Evidence Recorded

- **Implementation commit:** `0dd4506`
- **Implementation files:**
  - `runtime/event_contracts.py` — extended `build_session_state_event()` with `pending_steps`, `plan`, `code_preview`, `recovery_state`, `replay_state`
  - `server.py` — reconnect path emits enriched session_state envelope
- **Tests added:** `tests/test_session_state_reconnect.py`
- **Validation commands:**
  - `python -m pytest tests/test_session_state_reconnect.py -q`
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
