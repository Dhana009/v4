# S7-0809 — Save/Load Session UI

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** [S7-0810]
**Blocked by:** [S7-0500]

---

## Objective

Build Save/Load UI backed by typed `save_session` and `load_session` commands. Save current session to snapshot. Load saved session from list. Render `save_result`/`load_result` events or `session_state` backend events. Frontend does not restore session locally without backend validation.

After S7-0809:
- Save button exists; dispatches typed `save_session` command with active run context
- Load button exists; shows saved session list; dispatches typed `load_session` command
- `save_result` event renders success/failure
- `load_result` or `session_state` event validates and applies restored session
- UI disabled if backend command handlers missing

---

## Source Rules

- PRD-05-SESSION-001: save_session and load_session command/event payloads
- PRD-03-FE-C8-004: Frontend never restores session without backend validation event
- PRD-03-FE-019: Frontend sends typed commands; renders typed events

---

## Current Known Context

### What exists
- `session_store.py` in backend with in-memory save/load
- `replay_engine.py` uses session snapshots
- PRD defines command/event payloads

### What gaps exist
- No `save_session`/`load_session` command handlers in `server.py`/`ws/`
- No Save/Load UI components
- No `save_result`/`load_result` event handlers in frontend store
- No saved session list display
- No backend command availability check

---

## Tests First

### Unit Tests

```python
test_save_session_command_payload()  # PRD-05-SESSION-001
test_load_session_command_payload()  # PRD-05-SESSION-001
test_save_command_requires_active_run()  # PRD-05-SESSION-001
test_load_command_requires_session_id()  # PRD-05-SESSION-001
```

### Reducer Tests

```python
test_reducer_save_result_updates_saved_sessions()  # PRD-05-SESSION-001
test_reducer_load_result_clears_local_and_waits_session_state()  # PRD-03-FE-C8-004
test_reducer_session_state_applies_restored_state()  # PRD-03-FE-C8-004
```

### Command Dispatcher Tests

```python
test_dispatch_save_session_command()  # PRD-05-SESSION-001
test_dispatch_load_session_command()  # PRD-05-SESSION-001
test_dispatch_save_requires_active_run_context()  # PRD-05-SESSION-001
test_dispatch_load_rejects_missing_session_id()  # GOV-S7-C0-009
```

### Component Tests

```python
test_save_button_renders_when_run_active()  # PRD-05-SESSION-001
test_load_button_renders()  # PRD-05-SESSION-001
test_saved_sessions_list_displays()  # PRD-05-SESSION-001
test_save_result_shows_success_or_failure()  # PRD-05-SESSION-001
test_load_result_prevents_local_restoration()  # PRD-03-FE-C8-004
test_session_state_event_applies_restoration()  # PRD-03-FE-C8-004
test_ui_disabled_if_backend_command_unavailable()  # PRD-03-FE-019
```

### Negative Tests

```python
test_save_command_without_active_run_rejected()  # PRD-05-SESSION-001
test_load_command_without_session_id_rejected()  # GOV-S7-C0-009
test_malformed_save_result_rejected()  # GOV-S7-C0-009
test_stale_load_result_ignored()  # GOV-S7-C0-009
test_save_button_disabled_when_no_active_run()  # PRD-05-SESSION-001
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/session/SaveSessionButton.jsx (new)
- frontend/src/components/session/LoadSessionPanel.jsx (new)
- frontend/src/commands/sessionCommands.js (new)
- frontend/src/store/sessionSlice.js (new)
- frontend/src/store/handlers/save_result_handler.js (new)
- frontend/src/store/handlers/load_result_handler.js (new)
- frontend/src/store/handlers/session_state_handler.js (new)
- tests/test_frontend_session_ui.py (new)
```

### Backend Seam (may be in this story or Cluster 1)
```
- server.py (add command routing for save_session/load_session if missing)
- ws/router.py or similar (add handlers if missing)
```

### Forbidden Files

```
- agent.py (no changes)
- runtime/session_store.py (read-only; used by backend)
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Add `save_session` and `load_session` to `SUPPORTED_FRONTEND_COMMAND_TYPES`
2. Create Save button disabled if no active run
3. Create Load panel with saved session list (fetch from backend or from frontend event history)
4. Dispatch typed commands with required context
5. Add reducers for `save_result`, `load_result`, `session_state` events
6. **Critical:** Do not apply load_result locally; wait for backend `session_state` event to validate and apply
7. Show disabled reason if backend command handlers missing

---

## Stop Conditions

Stop if:

- Backend `save_session`/`load_session` handlers not wired (coordinate with Cluster 1)
- `save_result`/`load_result`/`session_state` event schema incomplete
- Implementation requires mutating session state locally (violates C8-4 rule)
- Coverage below 95%


---

## Evidence Recorded

- **Commit:** 4abbb27 — Cluster 8 components
- **Tests:** tests/test_frontend_recorded_code_replay_cards.py (27 tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2444 passed / 1 skipped / 0 failed
