# S7-0804 — Replay One and Replay All UI

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-0805]
**Blocked by:** [S7-0500 (command dispatcher)]

---

## Objective

Build replay control UI with "Replay one step" and "Replay all steps" buttons. Dispatch typed `replay_one` and `replay_all` commands to backend. Disable during replay. Show replay reason/status.

After S7-0804:
- Replay buttons exist in Recorded tab or separate Replay panel
- Buttons dispatch typed commands with required context (step_id for one, run_id for all)
- Buttons disable during replay
- Command payload includes run_id, session_id where needed
- Stale commands rejected by backend

---

## Source Rules

- PRD-05-REPLAY-001: replay_one and replay_all commands with specified payloads
- PRD-03-FE-007: Frontend sends typed commands only
- PRD-04-BACKEND-007: Command validation includes stale step_id/run_id checks
- GOV-S7-C0-004: Negative tests required

---

## Current Known Context

### What exists
- `replay_engine.py` exists in backend
- PRD defines replay_one/replay_all payload formats
- Frontend command dispatcher infrastructure (S7-0500) should exist

### What gaps exist
- No Replay button UI
- No command dispatcher for replay commands
- No disabled state during replay
- `replay_one`/`replay_all` not in `SUPPORTED_FRONTEND_COMMAND_TYPES`

---

## Tests First

### Unit Tests

```python
test_replay_one_command_payload_with_step_id()  # PRD-05-REPLAY-001
test_replay_all_command_payload_with_run_id()  # PRD-05-REPLAY-001
test_replay_command_includes_session_context()  # PRD-05-REPLAY-001
test_replay_button_disabled_when_no_recorded_steps()  # PRD-03-FE-007
test_replay_button_disabled_during_replay()  # PRD-03-FE-007
```

### Command Dispatcher Tests

```python
test_dispatch_replay_one_command()  # PRD-03-FE-007
test_dispatch_replay_all_command()  # PRD-03-FE-007
test_dispatch_replay_rejects_missing_step_id()  # GOV-S7-C0-004
test_dispatch_replay_rejects_missing_run_id()  # GOV-S7-C0-004
```

### Component Tests

```python
test_replay_button_renders_when_recorded_steps_exist()  # PRD-05-REPLAY-001
test_replay_one_button_dispatches_command()  # PRD-05-REPLAY-001
test_replay_all_button_dispatches_command()  # PRD-05-REPLAY-001
test_replay_button_disabled_during_replay()  # PRD-03-FE-007
```

### Negative Tests

```python
test_replay_command_without_step_id_rejected()  # GOV-S7-C0-004
test_replay_command_with_stale_step_id_rejected()  # PRD-04-BACKEND-007
test_replay_button_disabled_if_no_run_id()  # PRD-03-FE-007
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/replay/ReplayControls.jsx (new)
- frontend/src/commands/replayCommands.js (new)
- frontend/src/store/handlers/replay_dispatch_handler.js (new)
- tests/test_frontend_replay_ui.py (new)
```

### Forbidden Files

```
- agent.py
- runtime/replay_engine.py (read-only; do not modify)
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Create `ReplayControls` component with two buttons: "Replay one" (disabled if no selected step), "Replay all"
2. Add `replay_one` and `replay_all` to `SUPPORTED_FRONTEND_COMMAND_TYPES`
3. Create command dispatcher that validates step_id/run_id presence
4. Wire command dispatch to button click handler
5. Disable buttons during replay (watch `replayingStepId` or `replayInProgress` state)

---

## Stop Conditions

Stop if:

- Backend replay_one/replay_all handlers missing (coordinate with Cluster 1)
- Command dispatcher infrastructure incomplete
- Implementation requires modifying `replay_engine.py`
- Coverage below 95%

