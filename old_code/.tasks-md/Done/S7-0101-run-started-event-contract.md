# S7-0101 — run_started Event Contract

**Sprint:** Sprint 7
**Cluster:** 1 (Backend Event and Command Seams)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** S7-0102, S7-0103, S7-0104, S7-0106, S7-0110
**Blocked by:** None

---

## Objective

Emit a typed `run_started` backend event when a new run begins, so the frontend can enter the `planning`/`executing` interaction mode without inferring state from LLM text or prior messages. This is the foundational event that anchors all subsequent step-level events to a consistent `run_id`.

Before this story: frontend has no typed signal that a new run has begun; it may fall back to static/demo content or guess from `plan_ready`.
After this story: backend emits `run_started` with `run_id`, `steps[]`, and `phase` before any `plan_ready` or step events; frontend can enter planning state reliably.

---

## Source Rules

- `PRD-04-BE-001`: `run_started` event must include `run_id` and `steps[]`. Frontend behavior: set executing/planning state.
- `PRD-03-FE-003`: `planning` interaction mode must be triggered by a typed backend event, not inferred.
- `GOV-S7-C0-007`: No source rule → no test; no test → no implementation.
- `GOV-S7-C0-001`: Backend owns runtime truth — `run_started` reports that the run has begun, not that it will begin.
- `GOV-S7-C0-012`: Touch `agent.py` at thin event-emission seam only; no broad refactor.

---

## Current Known Context

### What exists in the repo

- `runtime/event_contracts.py`: `build_backend_event_envelope()` generic builder exists
- `runtime/event_contracts.py`: `build_run_completed_payload()` exists (Sprint 6)
- `runtime/event_contracts.py`: `build_recovery_needed_payload()` exists (Sprint 6)
- `agent.py`: emits `plan_ready`, `recovery_needed`, `run_completed` via envelope; no `run_started` emission
- `server.py`: routes `confirmed`, `correction`, `option_selected` commands; `run_started` not emitted on connect

### What gaps exist

- No `build_run_started_payload()` builder in `event_contracts.py`
- No emission point in `agent.py` for `run_started` before planning loop begins
- No tests for `run_started` payload shape or emission ordering
- `plan_ready` event may already include `run_id` — needs verification that `run_started` uses the same `run_id`

### Current test status

- `tests/test_backend_event_contract*.py` covers `build_backend_event_envelope()` generically (Sprint 6)
- No story-specific tests for `run_started`

---

## Tests First

### Unit Tests

File: `tests/test_run_started_event_contract.py`

```python
def test_build_run_started_payload_includes_run_id():  # PRD-04-BE-001
    ...

def test_build_run_started_payload_includes_steps_list():  # PRD-04-BE-001
    ...

def test_build_run_started_payload_includes_phase_planning():  # PRD-04-BE-001
    ...

def test_build_run_started_payload_schema_version_set():  # GOV-S7-C0-007
    ...

def test_build_run_started_payload_emitted_at_iso_format():  # GOV-S7-C0-007
    ...
```

### Contract Tests

File: `tests/test_run_started_event_contract.py`

```python
def test_run_started_event_type_field_is_run_started():  # PRD-04-BE-001
    ...

def test_run_started_event_run_id_matches_subsequent_plan_ready():  # PRD-04-BE-001
    # run_id from run_started must be consistent with plan_ready run_id
    ...

def test_run_started_envelope_is_valid_backend_event_envelope():  # PRD-04-BE-001
    ...
```

### Integration Tests

File: `tests/test_run_started_event_contract.py`

```python
def test_run_started_emitted_before_plan_ready_in_sequence():  # PRD-04-BE-001
    # Verify event ordering: run_started must precede plan_ready
    ...

def test_run_started_not_emitted_if_no_active_run():  # GOV-S7-C0-001
    ...
```

### Negative Tests (required)

File: `tests/test_run_started_event_contract.py`

```python
def test_build_run_started_payload_rejects_empty_run_id():  # PRD-04-BE-001
    ...

def test_build_run_started_payload_rejects_none_steps():  # PRD-04-BE-001
    ...

def test_run_started_not_emitted_twice_for_same_run():  # GOV-S7-C0-001
    ...

def test_stale_run_id_in_run_started_rejected_by_envelope_builder():  # GOV-S7-C0-007
    ...
```

### Regression Tests

```bash
python -m pytest tests/test_backend_event_contract*.py -q
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## Implementation Boundaries

### Allowed Files

```
runtime/event_contracts.py         ← add build_run_started_payload()
agent.py                           ← add thin emission seam before planning loop
tests/test_run_started_event_contract.py  ← new test file
```

### Forbidden Files

```
frontend/                          ← no UI changes
server.py                          ← no changes (command routing is separate)
runtime/llm_runtime_controller.py  ← no LLM prompt changes
runtime/llm_policy_gateway.py      ← no gateway changes
aw-ide-panel.jsx                   ← Cluster 3 scope
tests/e2e/                         ← Cluster 4 scope
Any Sprint 6 test files            ← do not modify
```

---

## Implementation Notes

### Approach

1. Add `build_run_started_payload(run_id, steps, phase="planning", ...)` to `runtime/event_contracts.py`.
2. Ensure payload uses `build_backend_event_envelope()` with `event_type="run_started"`.
3. Add thin emission call in `agent.py` at the point where a new run context is initialized — before any planning call.
4. The `run_id` emitted in `run_started` must be the same `run_id` used in subsequent `plan_ready`, `step_*`, and `run_completed` events.
5. Do not change any existing event builders or emission logic.

### Key Invariants

- `run_started` is emitted exactly once per run, before any plan-related events.
- `run_id` in `run_started` is consistent with `run_id` in all subsequent run-scoped events.
- If no run is active, `run_started` is not emitted.
- Empty or missing `run_id` raises `ValueError` in the builder (not silently accepted).

### Known Risks

- Risk: Duplicate `run_started` if planning loop retries.
  Mitigation: Guard with a "run already started" check; emit only once per run_id.
- Risk: `run_id` is not yet stable at the emission point.
  Mitigation: Verify `run_id` is assigned before the emit; add assertion in test.

---

## Coverage Requirement

```bash
python -m pytest tests/test_run_started_event_contract.py --cov=runtime.event_contracts --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] `build_run_started_payload()` exists in `runtime/event_contracts.py`
- [ ] Payload includes: `run_id`, `steps[]`, `phase`, `schema_version`, `emitted_at`, `type="run_started"`
- [ ] Builder raises `ValueError` for empty/None `run_id`
- [ ] Emission seam exists in `agent.py` before planning begins
- [ ] `run_id` consistency verified across `run_started` → `plan_ready` sequence
- [ ] All tests pass
- [ ] Coverage ≥ 95%
- [ ] Regression suite passes at baseline

---

## Evidence Required

- [ ] `runtime/event_contracts.py` updated — committed
- [ ] `agent.py` emission seam — committed
- [ ] `tests/test_run_started_event_contract.py` — committed (8+ tests)
- [ ] pytest output showing all tests pass
- [ ] Regression suite output showing no new failures
- [ ] Coverage ≥ 95% output

---

## Stop Conditions

- `run_id` is not stable before the planned emission point — investigate and adjust scope
- Builder requires changes to LLM controller or policy gateway — stop; file separate story
- Emission introduces a duplicate event in existing tests — stop; investigate before fixing
- Coverage < 95% after adding tests — do not lower threshold; add more tests

---

## Evidence Recorded

- **Implementation commit:** `0dd4506`
- **Implementation files:**
  - `runtime/event_contracts.py` — added `build_run_started_payload()`
  - `agent.py` — emission seam before planning loop; `_run_started_emitted` guard in `_reset_lifecycle_state()`
- **Tests added:** `tests/test_run_started_event_contract.py` (28 tests including coverage gap closers)
- **Validation commands:**
  - `python -m pytest tests/test_run_started_event_contract.py -q`
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
