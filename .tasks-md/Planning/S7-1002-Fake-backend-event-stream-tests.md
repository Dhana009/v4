# S7-1002 — Fake Backend Event Stream Tests

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-1003, S7-1004, S7-1005, S7-1006, S7-1007, S7-1008, S7-1009]
**Blocked by:** [S7-1001]

---

## Objective

Create deterministic fake backend event stream for E2E testing without real backend or LLM. After S7-1002:
- E2E tests can feed fake events to real frontend
- Events are immutable, timestamp-injected, and ordered
- Frontend renders each event correctly in isolation
- No stale/malformed event crashes renderer
- All 11 event types (session_state, clarification_needed, plan_ready, etc.) have fake fixtures
- E2E flows reproducible without external dependencies

---

## Source Rules

- PRD-04-BACKEND-001: All backend event schemas and payloads
- PRD-03-FE-011: Frontend renders backend truth only; no demo fallback
- GOV-S7-C0-007: No source rule → no test
- GOV-S7-C10-002: Local E2E; fake LLM only; no paid APIs

---

## Current Known Context

### What exists
- `tests/fake_llm_factory.py` has fake LLM fixtures
- `runtime/event_contracts.py` has event builders
- E2E tests can poll backend but no fake-only path exists
- No event stream injector for frontend

### What gaps exist
- No deterministic fake event stream for E2E
- No event injection mechanism in frontend
- No fake event ordering/timing fixtures
- No malformed event test cases

### Current test status
- Backend event builders are tested; frontend event handlers not isolated-tested

---

## Tests First

### Unit Tests

```python
# tests/e2e/test_fake_event_stream.py

test_fake_session_state_event()  # PRD-04-BACKEND-001
test_fake_clarification_needed_event()  # PRD-04-BACKEND-001
test_fake_plan_ready_event()  # PRD-04-BACKEND-001
test_fake_permission_required_event()  # PRD-04-BACKEND-001
test_fake_locator_ambiguous_event()  # PRD-04-BACKEND-001
test_fake_recovery_needed_event()  # PRD-04-BACKEND-001
test_fake_step_recorded_event()  # PRD-04-BACKEND-001
test_fake_code_update_event()  # PRD-04-BACKEND-001
test_fake_replay_result_event()  # PRD-04-BACKEND-001
test_fake_run_completed_event()  # PRD-04-BACKEND-001
test_fake_runtime_rejected_event()  # PRD-04-BACKEND-001
  # Each test creates fake event, verifies required fields, checks timestamp

test_event_stream_maintains_order()  # GOV-S7-C10-002
  # Stream events in creation order; no shuffling

test_event_stream_immutable()  # GOV-S7-C10-002
  # Fake events returned as copies; modification doesn't affect originals
```

### Contract Tests

```python
test_fake_event_payload_matches_schema()  # PRD-04-BACKEND-001
  # For each event type, assert payload matches backend schema
  # All required fields present and typed correctly

test_malformed_event_injection_safe()  # GOV-S7-C0-009
  # Frontend event handler receives malformed event (missing field, wrong type)
  # Frontend handles safely (does not crash, shows diagnostic)
```

### Integration Tests

```python
test_frontend_renders_fake_session_state()  # PRD-03-FE-011
  # Inject session_state event → frontend store updates → state visible in UI
  # Assert no static demo UI appears

test_frontend_renders_fake_plan_ready()  # PRD-03-FE-011
  # Inject plan_ready event → plan card appears with correct data
  # Assert no demo fallback

test_frontend_handles_malformed_event_stream()  # GOV-S7-C0-009
  # Stream with missing/wrong-typed fields → frontend rejects safely
```

### Negative Tests

```python
test_event_stream_rejects_duplicate_event_ids()  # GOV-S7-C0-009
test_event_stream_rejects_null_timestamp()  # GOV-S7-C0-009
test_event_stream_rejects_missing_run_id()  # GOV-S7-C0-009
test_frontend_ignores_stale_event()  # GOV-S7-C0-009
  # Event for old run_id ignored when new run active
```

---

## Implementation Boundaries

### Allowed Files

```
- tests/e2e/fake_event_stream.py (new — event stream injector)
- tests/e2e/test_fake_event_stream.py (new — tests)
- tests/fake_llm_factory.py (may extend with E2E event fixtures)
- frontend/src/store/ (if adding event injection hook)
```

### Forbidden Files

```
- agent.py, server.py (no changes)
- runtime/ (use existing builders only)
```

---

## Implementation Notes

1. Create `FakeEventStream` class that generates events with ISO timestamps, proper envelope
2. Add event fixture functions: `fake_session_state()`, `fake_plan_ready()`, etc.
3. Implement event injection into frontend store or WS mock
4. Test each event type isolates without backend
5. Verify frontend renders without demo fallback

---

## Acceptance Criteria

- [ ] All 11 event types have fake fixtures
- [ ] 12 unit tests pass (red → green)
- [ ] 2 contract tests pass
- [ ] 3 integration tests pass
- [ ] 5 negative tests pass
- [ ] E2E can inject events without backend
- [ ] Frontend renders all event types
- [ ] No demo UI fallback in fake event mode

---

## Evidence Required

- [ ] tests/e2e/fake_event_stream.py committed
- [ ] tests/e2e/test_fake_event_stream.py committed with all tests passing
- [ ] Fake event fixtures added to tests/fake_llm_factory.py (if used)
- [ ] All tests passing; coverage ≥ 90%

---

## Stop Conditions

- Cannot inject events without modifying frontend main.jsx (architectural issue)
- Frontend demo fallback appears even with valid fake events (indicates Cluster 6–9 incomplete)
- Event schema conflicts between backend and frontend (indicates Cluster 1–2 mismatch)
