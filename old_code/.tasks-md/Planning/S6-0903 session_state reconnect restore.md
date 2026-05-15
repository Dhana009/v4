# S6-0903 session_state reconnect restore

**Sprint:** Sprint 6  
**Cluster:** 9 (Replay Repair, Save/Load, Session Restore, Versioning)  
**Tier:** 1 (core)  
**Type:** Feature / Contract  
**Status:** Planning  
**Owner:** Session Restore  
**Blocks:** S6-0904  
**Blocked by:** S6-0902  

---

## Purpose

Complete reconnect/remount restoration using backend `session_state`. Full backend session_state payload with active run/session fields, recorded steps, pending/replay state, current phase, and code preview. No frontend guessing, no local lifecycle reconstruction, no fake completed state.

---

## Source rules

- Loaded sessions come from S6-0902 load contract
- Backend owns lifecycle state (not frontend)
- session_state is sent on reconnect/remount
- Frontend restores from backend event only

---

## What it contains

```
- full backend session_state payload
- active run/session fields
- recorded steps
- pending/replay state
- current phase
- code preview
- capability gaps where applicable
```

---

## What it must NOT contain

```
- no frontend guessing
- no local lifecycle reconstruction
- no fake completed state
```

---

## Tests first

### Unit tests

```
- session_state includes run_id/session_id/phase
- recorded steps included
- code preview included
- replay status included when active
```

### Contract tests

```
- session_state emitted before status on reconnect
- stale frontend cache cannot override backend session_state
```

### Regression tests

```
- existing websocket/session_state backend tests
- frontend state-store tests where available
```

Coverage: **95% for session_state_restore module**

---

## Out of scope

- Do not implement websocket reconnect (thin dispatch only)
- Do not reconstruct state on frontend
- Do not guess lifecycle

---

## Allowed files

```
runtime/session_state_restore.py (new)
tests/test_session_state_restore.py (new)
Minor edits to:
  - event_contracts.py (session_state event)
  - agent.py (emit session_state on load)
```

---

## Forbidden files

- No websocket implementation
- No frontend state logic
- No lifecycle guessing

---

## Implementation notes

### Schema (event_contracts.py or session_state_restore.py)

```
SessionState:
  - run_id: string
  - session_id: string
  - phase: enum (recording / planning / replaying / recovering / completed)
  - recorded_steps: list[RecordedStep]
  - pending_steps: list[PendingStep] (if Steps mode)
  - active_plan: optional Plan
  - active_replay: optional ReplayStatus
  - code_preview: string
  - metadata: dict
  - timestamp: ISO8601

SessionStateEvent:
  - event_type: "session_state"
  - payload: SessionState
```

### Approach

1. Create `runtime/session_state_restore.py` with:
   - SessionState schema
   - `build_session_state(run_state, phase)` → SessionState
   - Include all needed fields (recorded steps, code, phase, replay status)
   - No frontend guessing

2. Create `tests/test_session_state_restore.py`:
   - session_state includes required fields
   - Replay status included when active
   - Contract tests for event envelope

3. Update `agent.py`:
   - On load/reconnect, build and emit SessionState event
   - Frontend receives full snapshot

### Key invariants

- session_state is complete and authoritative
- Frontend uses session_state only
- No guessing or local reconstruction
- Event is emitted before status

---

## Validation commands

```bash
python -m pytest tests/test_session_state_restore.py::test_required_fields -v
python -m pytest tests/test_session_state_restore.py::test_replay_status_when_active -v
python -m pytest tests/test_session_state_restore.py::test_event_contract -v
coverage run -m pytest tests/test_session_state_restore.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/session_state_restore.py` created
- [ ] `tests/test_session_state_restore.py` created
- [ ] SessionState schema defined
- [ ] All required fields included
- [ ] Replay status included when active
- [ ] Event contract correct
- [ ] 95% coverage

---

## Sign-off

- [x] Story is specific (session_state reconnect restore)
- [x] Scope is bounded (build/emit only)
- [x] Tests are first
- [x] Blocks S6-0904 (replay)
