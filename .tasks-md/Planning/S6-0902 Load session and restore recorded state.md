# S6-0902 Load session and restore recorded state

**Sprint:** Sprint 6  
**Cluster:** 9 (Replay Repair, Save/Load, Session Restore, Versioning)  
**Tier:** 1 (core)  
**Type:** Feature / Contract  
**Status:** Planning  
**Owner:** Session Load  
**Blocks:** S6-0903  
**Blocked by:** S6-0901  

---

## Purpose

Load saved sessions and restore backend-owned state. Load_session command, session file validation, recorded steps restored, code preview restored, locator context restored, and replay-ready state restored. No frontend local reconstruction as truth, no unsafe load of malformed session, no replay execution yet.

---

## Source rules

- Saved sessions come from S6-0901 save contract
- Backend owns recorded state (frontend cannot guess)
- Malformed sessions must be rejected safely
- Loaded state must be deep-copied (not referenced)

---

## What it contains

```
- load_session command
- session file validation
- recorded steps restored
- code preview restored
- locator context restored
- replay-ready state restored
```

---

## What it must NOT contain

```
- no frontend local reconstruction as truth
- no unsafe load of malformed session
- no replay execution yet
```

---

## Tests first

### Unit tests

```
- valid saved session loads recorded steps
- malformed session returns typed error
- missing fields rejected safely
- loaded state is deep-copied
```

### Contract tests

```
- load_session emits session_state
- frontend can restore from backend event only
- invalid load emits runtime_rejected / load_failed
```

### Integration tests

```
- save session → load session → recorded steps/code preview match
```

Coverage: **95% for session_load module**

---

## Out of scope

- Do not execute replay
- Do not guess frontend state
- Do not implement replay

---

## Allowed files

```
runtime/session_load_contracts.py (new)
tests/test_session_load_contracts.py (new)
Minor edits to:
  - agent.py (dispatch to load)
```

---

## Forbidden files

- No replay logic
- No frontend state reconstruction
- No unsafe deserialization

---

## Implementation notes

### Schema (session_load_contracts.py)

```
LoadSessionCommand:
  - session_path: string (workspace-relative or absolute)

LoadSessionResult:
  - success: bool
  - run_id: string
  - session_id: string
  - recorded_steps: list[RecordedStep]
  - code_preview: string
  - error: optional string

LoadSessionError:
  - type: enum (file_not_found / invalid_json / missing_fields / corrupted)
  - details: string
```

### Approach

1. Create `runtime/session_load_contracts.py` with:
   - LoadSessionCommand, LoadSessionResult, LoadSessionError schema
   - `load_session(command)` → LoadSessionResult
   - File exists check
   - JSON parse with error handling
   - Schema validation (required fields)
   - Deep copy loaded state
   - Return result or error

2. Create `tests/test_session_load_contracts.py`:
   - Valid session loads
   - Invalid JSON rejected
   - Missing fields rejected
   - State is deep-copied

3. Update `agent.py`:
   - Listen for load_session command
   - Call session_load()
   - Emit session_state or load_failed event

### Key invariants

- Validation enforces schema
- Errors are typed and explicit
- State is deep-copied (safe from mutation)
- No replay until user confirms

---

## Validation commands

```bash
python -m pytest tests/test_session_load_contracts.py::test_valid_load -v
python -m pytest tests/test_session_load_contracts.py::test_invalid_json -v
python -m pytest tests/test_session_load_contracts.py::test_missing_fields -v
python -m pytest tests/test_session_load_contracts.py::test_deep_copy -v
coverage run -m pytest tests/test_session_load_contracts.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/session_load_contracts.py` created
- [ ] `tests/test_session_load_contracts.py` created
- [ ] LoadSessionCommand/Result/Error defined
- [ ] Valid sessions load
- [ ] Invalid sessions rejected safely
- [ ] State is deep-copied
- [ ] 95% coverage

---

## Sign-off

- [x] Story is specific (load session and restore state)
- [x] Scope is bounded (load only, no replay)
- [x] Tests are first
- [x] Blocks S6-0903 (session_state restore)
