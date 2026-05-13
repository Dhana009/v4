# S7-0805 — Replay Result Rendering

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0804]

---

## Objective

Render `replay_started` and `replay_result` backend events in Replay tab/panel. Show replay in-progress state, replay success, replay failure with reason, and next actions. Frontend does not mark replay passed until `replay_result` event confirms it.

After S7-0805:
- `replay_started` event shows running indicator
- `replay_result` success shows confirmation
- `replay_result` failure shows reason and next action
- Frontend state does not mutate replay without backend event
- Stale replay_result ignored with diagnostic

---

## Source Rules

- PRD-04-BACKEND-008: replay_started/replay_result event payload and semantics
- PRD-03-FE-C8-003: Frontend never mutates recorded evidence based on local replay state
- PRD-03-FE-007: Frontend renders backend truth; no inference

---

## Current Known Context

### What exists
- `replay_engine.py` in backend
- `replay_started` and `replay_result` events defined in PRD
- S7-0804 creates replay button; event handlers missing

### What gaps exist
- No `replay_started`/`replay_result` event handlers in frontend store
- No replay result display component
- No failure reason display
- No next action guidance

---

## Tests First

### Unit Tests

```python
test_replay_result_from_event_payload()  # PRD-04-BACKEND-008
test_replay_result_success_vs_failure()  # PRD-04-BACKEND-008
test_replay_failure_reason_display()  # PRD-04-BACKEND-008
test_replay_rejects_stale_result()  # GOV-S7-C0-004
```

### Reducer Tests

```python
test_reducer_replay_started_sets_replayInProgress()  # PRD-04-BACKEND-008
test_reducer_replay_result_clears_replayInProgress()  # PRD-04-BACKEND-008
test_reducer_replay_result_stores_result_summary()  # PRD-04-BACKEND-008
```

### Component Tests

```python
test_replay_panel_renders_empty_state()  # PRD-03-FE-007
test_replay_panel_renders_running_on_replay_started()  # PRD-04-BACKEND-008
test_replay_panel_renders_success_on_replay_result()  # PRD-04-BACKEND-008
test_replay_panel_renders_failure_reason()  # PRD-04-BACKEND-008
test_replay_panel_shows_next_actions_on_failure()  # PRD-04-BACKEND-008
```

### Negative Tests

```python
test_replay_result_malformed_rejected()  # GOV-S7-C0-004
test_replay_result_missing_step_id_rejected()  # GOV-S7-C0-004
test_stale_replay_result_ignored()  # GOV-S7-C0-004
test_replay_failure_does_not_mutate_recorded_evidence()  # PRD-03-FE-C8-003
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/replay/ReplayResultPanel.jsx (new)
- frontend/src/store/handlers/replay_result_handler.js (new)
- frontend/src/store/replaySlice.js (new or extend)
- tests/test_frontend_replay_ui.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/replay_engine.py
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Add reducer for `replay_started` and `replay_result` events
2. Create `ReplayResultPanel` to show result summary
3. Display failure reason and next actions when available
4. Reject stale result (check replay_id or step_id correlation)
5. Do not mutate `recordedSteps` or any other state based on replay result

---

## Stop Conditions

Stop if:

- `replay_result` event schema missing required fields
- Implementation requires mutating recorded evidence
- Coverage below 95%

