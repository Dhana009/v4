# S7-0004 — Frontend-Backend Seam Readiness Matrix

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Audit every event and command required by the real frontend, determine current backend readiness, and produce a gap list that drives Cluster 1 story scoping. This matrix is the authoritative reference for what must be implemented in Cluster 1 before frontend wiring can begin in Cluster 2.

---

## Source Rules

- PRD `04_BACKEND_EVENT_CONTRACT.md`: Required backend→frontend lifecycle events; required frontend→backend commands
- PRD `03_FRONTEND_RUNTIME.md`: Frontend interaction modes and UX feedback states
- Sprint 6 HANDOFF: "Frontend (Cluster 10) is contract-only — no actual frontend/ source was implemented"
- `runtime/event_contracts.py`: Current implementation of event builders
- `frontend/src/main.jsx`: Current WS transport and state (lines 1–100 confirm live WS transport exists)

---

## Current Known Context

### What currently exists in `runtime/event_contracts.py`

- `build_backend_event_envelope()` — generic envelope builder (schema version, type, payload, run_id, event_id, emitted_at, source)
- `build_frontend_command_envelope()` — generic command envelope builder
- `build_runtime_rejection_payload()` — typed rejection for invalid commands
- `build_run_completed_payload()` — run_completed event builder (exists, completeness to be verified)
- `build_recovery_needed_payload()` — recovery_needed event builder (exists, Sprint 6 done)
- `build_session_state_event()` — session_state event builder (exists, completeness to be verified)
- `normalize_frontend_command()` — command normalizer
- `SUPPORTED_FRONTEND_COMMAND_TYPES = {"confirmed", "correction", "option_selected"}` — only 3 types currently registered

### What currently exists in `runtime/session_store.py`

- In-memory only: `_STORE: dict[str, SessionSpec]`
- `save_session(spec)` → returns `session_id`
- `load_session(session_id)` → returns `SessionSpec | None`
- `restore_session_state(session_id)` → returns `SessionState` with minimal fields
- No file/JSON persistence
- No WS command wiring

### What currently exists in `frontend/src/main.jsx`

- Live WS transport with reconnect logic
- `RUN_STATE_ALIASES` and `INTERACTION_MODE_ALIASES` normalization maps
- `normalizeRunState()`, `normalizeInteractionMode()`, `toPanelState()` functions
- `DEFAULT_CONFIG` with state, tab, panelWidth, density
- Shadow DOM host/mount IDs
- Live WS state is NOT fully threaded into `IDEPanel` — can fall back to static/demo content

---

## Tests First

This is a documentation/audit story. No implementation tests required.

### Verification
- Every event and command in PRD-04 is listed in the matrix
- Gap column is accurate based on code inspection
- Gap list drives Cluster 1 story scoping

---

## Events Readiness Matrix

### Backend → Frontend Events

| Event | PRD Required Payload | Builder Exists? | Payload Complete? | WS Emitted? | Gap | Cluster 1 Story |
|-------|---------------------|-----------------|-------------------|-------------|-----|-----------------|
| `ready` | session_id, workspace, mode, url | Partial (envelope only) | No — missing browser_ready fields | Yes (server.py) | Typed envelope missing | S7-0105 |
| `browser_ready` | browser readiness fields | No | — | No | Full new event needed | S7-0105 |
| `run_started` | run_id, steps[] | No | — | No | New builder + emission seam | S7-0101 |
| `plan_ready` | run_id, plan, steps[], summary | Via envelope | Verify | Yes | Payload completeness check | Verify in S7-0101 |
| `clarification_needed` | run_id, question, options?, step_id? | Via envelope | Verify | Yes | Payload completeness check | Verify |
| `recovery_needed` | run_id, step_id, operation_id?, error_summary, current_url, tried[], options? | `build_recovery_needed_payload()` | Yes (Sprint 6) | Yes | None | Maintained |
| `step_validating` | step_id, operation_id?, locator? | No | — | No | New builder + emission seam | S7-0102 |
| `step_executing` | step_id, operation_id?, action | No | — | No | New builder + emission seam | S7-0102 |
| `step_recorded` | step with parent/children metadata | Via envelope | Verify | Yes | Payload completeness check | Verify |
| `step_failed` | step_id, operation_id?, error, status | No distinct event | — | No | New builder + emission seam | S7-0103 |
| `step_skipped` | step_id, reason | No distinct event | — | No | New builder + emission seam | S7-0103 |
| `code_update` | step_id?, operation_id?, lines[], full_spec_preview, diagnostics[] | Via envelope | Verify | Yes | Payload completeness check | Verify |
| `replay_started` | run_id, step_ids | No | — | No | Sprint 8 | Deferred |
| `replay_result` | step_id, operation_id?, passed, error? | No | — | No | Sprint 8 | Deferred |
| `run_completed` | run_id, summary, recorded_count, skipped_count | `build_run_completed_payload()` | Partial — missing failed_count, code_status | Verify | Payload extension | S7-0106 |
| `session_state` | full snapshot | `build_session_state_event()` | Partial — reconnect fields incomplete | Yes | Payload completeness | S7-0110 |
| `capability_gap_recorded` | gap_id, needed_capability, path | No | — | No | Sprint 8 | Deferred |
| `save_result` | path, name, session_id | No | — | No | New event for S7-0109 | S7-0109 |
| `load_result` | path, name, step_count, session_id | No | — | No | New event for S7-0109 | S7-0109 |
| `permission_required` | run_id, operation_id, action_type, risk_level, message, options? | No distinct event | — | No | New builder + emission seam | S7-0104 |

---

## Commands Readiness Matrix

### Frontend → Backend Commands

| Command | PRD Required Payload | Backend Handler Exists? | SUPPORTED_COMMAND_TYPES Registered? | Gap | Cluster 1 Story |
|---------|---------------------|------------------------|--------------------------------------|-----|-----------------|
| `run_steps` / `llm_run` | steps[] | Yes (agent.py) | Not in normalize set | Verify routing | Verify |
| `confirmed` | run_id? | Yes | Yes (`confirmed` in set) | None | Maintained |
| `correction` | message, run_id?, step_id? | Yes | Yes | None | Maintained |
| `option_selected` | value, answer?, run_id? | Yes | Yes | None | Maintained |
| `replay_step` / `replay_one` | step_id | Partial | No | Sprint 8 | Deferred |
| `replay_operation` | step_id, operation_id | No | No | Sprint 8 | Deferred |
| `replay_all` | stop_on_error | Partial | No | Sprint 8 | Deferred |
| `skip_step` | step_id (+ run_id) | No | No | New handler + registration | S7-0108 |
| `stop_run` | run_id | No | No | New handler + registration | S7-0107 |
| `save_session` | path?, name? | Stub only (no WS) | No | WS command wiring + result event | S7-0109 |
| `load_session` | path | Stub only (no WS) | No | WS command wiring + result event | S7-0109 |
| `update_locator` | step_id, operation_id?, constraints? | Partial | No | Sprint 8 | Deferred |
| `permission_decision` | run_id, operation_id, decision (approve/deny) | No | No | New handler + registration | S7-0104 |

---

## Gap Summary

### Must-Have Gaps (Cluster 1 scope)

| # | Gap | Story | Priority |
|---|-----|-------|---------|
| 1 | `run_started` event builder and emission seam | S7-0101 | P0 |
| 2 | `step_validating` event builder and emission seam | S7-0102 | P0 |
| 3 | `step_executing` event builder and emission seam | S7-0102 | P0 |
| 4 | `step_failed` distinct event (not buried in recovery_needed) | S7-0103 | P0 |
| 5 | `step_skipped` distinct event | S7-0103 | P0 |
| 6 | `permission_required` event emission | S7-0104 | P0 |
| 7 | Typed `ready`/`browser_ready` envelope | S7-0105 | P0 |
| 8 | `run_completed` payload extension (failed_count, code_status) | S7-0106 | P0 |
| 9 | `stop_run` command handler + registration | S7-0107 | P0 |
| 10 | `skip_step` command handler + registration | S7-0108 | P0 |
| 11 | `save_session` / `load_session` WS command wiring | S7-0109 | P0 |
| 12 | `session_state` reconnect payload completeness | S7-0110 | P0 |

### Deferred Gaps (Sprint 8)

| Gap | Sprint |
|-----|-------|
| `replay_started`, `replay_result` events | Sprint 8 |
| `replay_step`, `replay_operation`, `replay_all` commands | Sprint 8 |
| `capability_gap_recorded` event | Sprint 8 |
| `update_locator` command full implementation | Sprint 8 |

---

## Implementation Boundaries

This is a documentation/audit story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0004-Frontend-backend-seam-readiness-matrix.md` (this file)

---

## Forbidden Files

- No product code changes
- No test file changes
- No runtime/ changes
- No frontend/ changes

---

## Acceptance Criteria

- [ ] All PRD-04 events are listed with readiness status
- [ ] All PRD-04 commands are listed with readiness status
- [ ] Gap summary maps to exactly the Cluster 1 stories S7-0101 through S7-0110
- [ ] Deferred items are clearly not Sprint 7 scope
- [ ] Matrix is referenced by all Cluster 1 story files

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`
- [ ] All matrix rows populated

---

## Stop Conditions

- An event or command is found in PRD-04 that is not in this matrix — update before Cluster 1 starts
- A Cluster 1 story attempts to implement a deferred gap — stop and reassign to Sprint 8
