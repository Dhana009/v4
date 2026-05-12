# S6-0901 Workspace save session/spec contract

**Sprint:** Sprint 6  
**Cluster:** 9 (Replay Repair, Save/Load, Session Restore, Versioning)  
**Tier:** 1 (core)  
**Type:** Feature / Contract  
**Status:** Planning  
**Owner:** Session Persistence  
**Blocks:** S6-0902  
**Blocked by:** S6-0408  

---

## Purpose

Finish save behavior for recorded sessions and generated specs using active workspace paths. Workspace-relative default output paths, save_session command contract, saved session JSON, generated spec preview/file, metadata linking session + generated spec, and redaction-safe saved payload.

---

## Source rules

- Cluster 8 recording is complete with code_update events
- Session path must be workspace-relative (not hardcoded .hermes)
- Secrets must not appear in logs or saved metadata
- Product workflow doc requires save session/spec as part of complete loop

---

## What it contains

```
- workspace-relative default output paths
- save_session command contract
- saved session JSON
- generated spec preview/file
- metadata linking session + generated spec
- redaction-safe saved payload
```

---

## What it must NOT contain

```
- no hardcoded .hermes user output
- no replay repair
- no frontend full UI
- no broad storage refactor
```

---

## Tests first

### Unit tests

```
- default save path is workspace-relative
- custom save path/name accepted
- session and spec metadata linked
- secrets are not saved in logs/spec metadata
```

### Contract tests

```
- save_session command has typed validity
- save result event includes path/status/diagnostics
```

### Integration tests

```
- recorded steps + code preview → save session/spec → files exist
```

Coverage: **95% for new/changed save/persistence modules**

---

## Out of scope

- Do not implement replay (defer to S6-0904)
- Do not implement frontend UI
- Do not refactor storage broadly

---

## Allowed files

```
runtime/session_save_contracts.py (new)
tests/test_session_save_contracts.py (new)
Minor edits to:
  - agent.py (thin dispatch to save)
  - event_contracts.py if needed
```

---

## Forbidden files

- No replay logic
- No frontend code
- No broad storage refactor

---

## Implementation notes

### Schema (session_save_contracts.py)

```
SessionPayload:
  - run_id: string
  - session_id: string
  - created_at: ISO8601
  - recorded_steps: list[RecordedStep]
  - code_preview: string
  - metadata: dict (no secrets)

SaveSessionCommand:
  - session_id: string
  - custom_path: optional string
  - custom_name: optional string

SaveSessionResult:
  - success: bool
  - path: string (workspace-relative)
  - session_json_size: int
  - spec_json_size: int
  - metadata_hash: string (for change detection)
  - error: optional string
```

### Approach

1. Create `runtime/session_save_contracts.py` with:
   - SessionPayload, SaveSessionCommand, SaveSessionResult schema
   - `save_session(command, run_state)` → SaveSessionResult
   - Workspace-relative path resolution
   - Redact secrets from metadata (API keys, passwords, etc.)
   - Write session JSON
   - Write spec JSON
   - Return result

2. Create `tests/test_session_save_contracts.py`:
   - Default path is workspace-relative
   - Custom path accepted
   - Secrets redacted
   - Files created correctly

3. Update `agent.py`:
   - Listen for save_session command
   - Call session_save()
   - Emit session_saved event

### Key invariants

- Paths are workspace-relative
- Secrets are redacted
- Metadata links session + spec
- Files are created atomically

---

## Validation commands

```bash
python -m pytest tests/test_session_save_contracts.py::test_default_path_relative -v
python -m pytest tests/test_session_save_contracts.py::test_secrets_redacted -v
python -m pytest tests/test_session_save_contracts.py::test_files_created -v
coverage run -m pytest tests/test_session_save_contracts.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/session_save_contracts.py` created
- [ ] `tests/test_session_save_contracts.py` created
- [ ] SessionPayload/SaveSessionCommand/SaveSessionResult defined
- [ ] Default path is workspace-relative
- [ ] Secrets redacted
- [ ] Metadata links session + spec
- [ ] Files created correctly
- [ ] 95% coverage

---

## Stop conditions

- Workspace path resolution unclear (define in story examples)
- Secret list incomplete (enumerate in story)

---

## Sign-off

- [x] Story is specific (save session/spec contract)
- [x] Scope is bounded (save only, no replay)
- [x] Tests are first
- [x] Blocks S6-0902 (load)
