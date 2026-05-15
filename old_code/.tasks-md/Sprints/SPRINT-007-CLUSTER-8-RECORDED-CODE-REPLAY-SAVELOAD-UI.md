# Sprint 7 — Cluster 8: Recorded + Code + Replay + Save/Load UI

**Sprint:** Sprint 7
**Cluster:** 8
**Status:** Done
**Date:** 2026-05-14
**HEAD at closure:** 4abbb27
**Expected Commits:** ~5 (test files + implementation per story)

---

## Cluster Goal

Wire the Recorded, Code, Replay, and Save/Load UI features to live backend events and commands. Replace static/demo content with real, backend-driven state.

After Cluster 8:
- Recorded tab renders backend-recorded steps only (never draft intent)
- Code tab renders backend code_update events only (never frontend-generated code)
- Replay UI dispatches typed replay commands and renders replay_result events
- Save/Load UI dispatches typed save_session/load_session commands and renders backend session state
- Frontend does not infer replay success, code generation, or session restoration

---

## Source Rules

**PRD v2.3:**
- `05_CODEGEN_REPLAY_PERSISTENCE.md`: Recorded evidence, code generation, replay, save/load architecture
- `04_BACKEND_EVENT_CONTRACT.md`: run_completed, step_recorded, code_update, replay_started, replay_result event payloads
- `03_FRONTEND_RUNTIME.md`: Frontend rendering rules, command dispatch, no lifecycle inference

**Sprint 7 Governance:**
- `SPRINT-007-CLUSTER-0-GOVERNANCE.md`: Architecture non-negotiables, test-first protocol, modularization rules
- Backend owns runtime truth (no frontend simulation)
- Frontend renders typed backend events only
- No frontend inference of lifecycle state

**Handoff Issues:**
- `SPRINT-006-HANDOFF.md` BUG-S6-FINAL-002: Frontend Complete LLM UI contract-only; Recorded/Code/Trace tabs have zero real implementation

---

## Current Audit Findings

### Recorded Tab
- **Current:** Zero real frontend implementation (contract tests only in `tests/test_frontend_llm_mode_complete.py`)
- **Backend:** `step_recorded` events exist; `recording_evidence` with child operations defined in PRD
- **Gap:** No Recorded tab component, no renderer for recordedSteps[], no display of evidence

### Code Tab
- **Current:** Zero real frontend implementation
- **Backend:** `code_update` events exist; code generation logic in `runtime/codegen_*.py`
- **Gap:** No Code tab component, no renderer for codePreview, no line mapping display

### Replay UI
- **Current:** Zero real frontend implementation; `replay_started`/`replay_result` backend events exist
- **Backend:** `replay_engine.py` completed; replay commands defined but UI wiring missing
- **Gap:** No Replay button/controls; frontend cannot dispatch replay commands

### Save/Load UI
- **Current:** `session_store.py` has in-memory save/load; backend commands not wired
- **Backend:** `save_session`/`load_session` command handlers missing from `server.py`/`ws/`
- **Gap:** No Save/Load UI; backend command handlers missing

### Code Warnings & State
- **Current:** No diagnostic warnings for repaired/skipped/failed steps
- **Backend:** `code_update` payload includes diagnostics; frontend has no UI to show them

---

## Design Prototype Role

`frontend_new_design_prototype/` contains static HTML mockups of Recorded/Code/Replay/Save tabs. These are **design reference only**, not runtime truth. Do not:
- Copy static content into production live mode
- Use prototype styling without extraction to design tokens
- Treat prototype state as working frontend behavior

---

## Recorded/Code/Replay/SaveLoad State Matrix

| Feature | Backend Event | Frontend Command | Frontend State | Display |
|---------|---|---|---|---|
| Recorded tab | `step_recorded` (list) | (none) | recordedSteps[] | parent + child ops |
| Code tab | `code_update` | (none) | codePreview, diagnostics | code + warnings |
| Replay one | — | `replay_one` | replayInProgress | UI disabled until replay_result |
| Replay all | — | `replay_all` | replayInProgress | UI disabled until replay_result |
| Replay result | `replay_result` | — | replayResult | success/failure + next actions |
| Save session | — | `save_session` | savingSession | disabled until save_result |
| Save result | `save_result` (if wired) | — | saveResult | success/failure + session_id |
| Load session | — | `load_session` | loadingSession | disabled until load_result |
| Load result | `load_result` (if wired) or `session_state` | — | loadedSession | restored session or error |

---

## Backend Event Dependency Table

| Story | Requires Backend Event | Requires Backend Command | Status |
|-------|---|---|---|
| S7-0801: Recorded tab | `step_recorded` | — | Event exists; frontend UI missing |
| S7-0802: Child ops | `step_recorded.children[]` | — | Event schema exists; frontend UI missing |
| S7-0803: Repaired/skipped states | `step_recorded.state` | — | Event schema exists; frontend UI missing |
| S7-0804: Replay one/all UI | — | `replay_one`, `replay_all` | Command types not yet in SUPPORTED_FRONTEND_COMMAND_TYPES |
| S7-0805: Replay result | `replay_result` | — | Event schema exists; handler missing in frontend event store |
| S7-0806: Code tab | `code_update` | — | Event exists; frontend UI missing |
| S7-0807: Code line mapping | `code_update.lineMapping` (if available) | — | Metadata may not be in current schema |
| S7-0808: Code warnings | `code_update.diagnostics[]` | — | Schema may need expansion |
| S7-0809: Save/Load UI | `save_result`, `load_result` or `session_state` | `save_session`, `load_session` | Commands missing; events may be missing |
| S7-0810: Export/copy | — | `export_code` (if backend supports) | Command handler missing |

---

## Frontend Command Table

| Command | Payload | Requires Backend Handler | Story |
|---------|---------|---|---|
| `replay_one` | `{step_id, run_id}` | Yes (S7-0804, backend seam cluster) | S7-0804 |
| `replay_all` | `{run_id}` | Yes (S7-0804, backend seam cluster) | S7-0804 |
| `save_session` | `{run_id, name?, metadata?}` | Yes (S7-0809, backend seam cluster) | S7-0809 |
| `load_session` | `{session_id or path}` | Yes (S7-0809, backend seam cluster) | S7-0809 |

---

## No-Frontend-Inference Rules

### Rule C8-1: Recorded Tab Never Infers Recording
Frontend must not:
- Show a step as recorded before `step_recorded` event arrives
- Show draft/pending step as recorded evidence
- Mark step recorded based on local UI state

Frontend must:
- Render only `step_recorded` events from backend event store
- Show empty state if no recorded steps exist
- Reject malformed recorded payload with diagnostic

### Rule C8-2: Code Tab Never Generates Code
Frontend must not:
- Generate or suggest code
- Show code before `code_update` event
- Store code locally without backend validation

Frontend must:
- Render only `code_update` from backend
- Show empty state before first code_update
- Display code_update diagnostics/warnings

### Rule C8-3: Replay Never Mutates Recorded Evidence
Frontend must not:
- Mark replay passed/failed locally
- Mutate recorded step state based on replay result
- Cache replay_result across runs

Frontend must:
- Dispatch typed `replay_one`/`replay_all` commands only
- Wait for `replay_result` event before updating state
- Reject stale replay_result with diagnostic

### Rule C8-4: Save/Load Never Restore Without Backend Event
Frontend must not:
- Restore session_state locally without backend validation
- Mutate run/step state based on load_session command dispatch
- Assume load succeeded until `session_state` or `load_result` event

Frontend must:
- Dispatch typed `save_session`/`load_session` commands only
- Wait for backend `load_result`/`session_state` event
- Reject stale load_result with diagnostic

---

## Story List (Tier 1 — Core Cluster 8 Stories)

1. **S7-0801** Recorded tab live evidence rendering
2. **S7-0802** Child operation evidence display
3. **S7-0803** Repaired, skipped, and unresolved recorded states
4. **S7-0804** Replay one and replay all UI
5. **S7-0805** Replay result rendering
6. **S7-0806** Code tab live code_update rendering
7. **S7-0807** Code line to recorded step mapping
8. **S7-0808** Code warnings, placeholder, and capability states
9. **S7-0809** Save/load session UI
10. **S7-0810** Export and copy code command UI

---

## Allowed Files (Cluster 8 Implementation)

### Frontend Components (new)
- `frontend/src/components/recorded/**` (new — all Recorded tab subcomponents)
- `frontend/src/components/code/**` (new — all Code tab subcomponents)
- `frontend/src/components/replay/**` (new — replay controls)
- `frontend/src/components/session/**` (new — save/load UI)

### Frontend State & Commands
- `frontend/src/store/**` (new or extend — event store handlers for recorded/code/replay/save/load)
- `frontend/src/commands/**` (new or extend — typed command dispatchers)

### Frontend Wiring
- `frontend/src/aw-ide-panel.jsx` (modification at prop/callback boundaries only — no new logic)
- `frontend/src/main.jsx` (modification for thin state threading only)

### Tests
- `tests/test_frontend_recorded_*.py` (new)
- `tests/test_frontend_code_*.py` (new)
- `tests/test_frontend_replay_*.py` (new)
- `tests/test_frontend_session_*.py` (new)
- `tests/test_frontend_recorded_code_rendering.py` (new — integration)

### Backend (if Cluster 1/2 handlers missing)
- `server.py` (only thin command routing seam if needed)
- `ws/router.py` or similar (only thin command routing seam if needed)

---

## Forbidden Files (Cluster 8)

- `agent.py` (no changes; Cluster 1 owns backend event emission)
- `runtime/*.py` (no changes; Cluster 1 owns event builders)
- `frontend/src/aw-workbench.jsx` (not in scope)
- `frontend/src/aw-tabs.jsx` (not in scope; tab infrastructure assumed from prior cluster)
- `frontend_new_design_prototype/` (read-only design reference; do not copy static HTML into production)
- Any `.DS_Store`, `AGENTS.md` files

---

## Tests-First Requirements

### Before Implementation

For each story (S7-0801 through S7-0810):

1. Write unit tests for data transforms (pure functions only)
2. Write contract tests for command/event payloads
3. Write reducer/store tests for event handlers (if frontend state modified)
4. Write command dispatcher tests (if new command types added)
5. Write component render tests (for component story)
6. Write negative tests (malformed/stale/missing data)
7. Run tests — all must fail (red) before implementation
8. Write implementation
9. All tests pass (green)
10. Run regression guard
11. Commit tests + implementation together

### Test File Locations

- `tests/test_frontend_recorded_evidence_rendering.py` — unit + contract + component tests for S7-0801/0802/0803
- `tests/test_frontend_replay_ui.py` — unit + contract + command dispatcher tests for S7-0804/0805
- `tests/test_frontend_code_rendering.py` — unit + contract + component tests for S7-0806/0807/0808
- `tests/test_frontend_session_ui.py` — unit + contract + command dispatcher tests for S7-0809/0810

---

## Definition of Done (Cluster 8)

- [ ] All 10 stories complete (status = Done)
- [ ] All story tests pass (unit, contract, integration, negative, regression)
- [ ] Coverage ≥ 95% for new modules
- [ ] No new failures in cheap regression suite (1689 tests + BUG-S6-FINAL-001 12 pre-existing)
- [ ] No forbidden files modified
- [ ] Recorded tab shows only backend recorded steps (no draft)
- [ ] Code tab shows only backend code_update (no generated code)
- [ ] Replay UI dispatches typed commands and renders backend events (no local success inference)
- [ ] Save/Load UI dispatches typed commands and renders backend session state (no local restoration)
- [ ] Browser smoke test passes for Recorded/Code/Replay/Save/Load flows (Cluster 10, S7-1008)
- [ ] All evidence committed and linked

---

## Stop Conditions

Stop and ask for clarification if:

- Backend `save_session`/`load_session`/`replay_one`/`replay_all` command handlers do not exist in Cluster 1/seam tasks
- Backend `save_result`/`load_result` events are not wired (use `session_state` as fallback if PRD allows)
- `code_update` payload schema is missing required diagnostics/line-mapping fields
- Frontend store/command infrastructure is missing or incomplete
- `aw-tabs.jsx` or tab-switching infrastructure does not exist
- Implementation requires modifying Cluster 1/4/5/6/7 behavior (coordinate dependency)
- Test coverage falls below 95%
- Regression guard fails with a new failure
- Any story requires touching a forbidden file (file a new story instead)
- Static demo content in design prototype cannot be cleanly separated from production code

---

## Evidence Requirements

For cluster sign-off:

- [ ] All 10 stories updated to status `Done` in `.tasks-md/Planning/`
- [ ] Test files committed (unit, contract, component, negative, regression)
- [ ] Implementation files committed (components, store handlers, command dispatchers)
- [ ] Coverage report ≥ 95% for each story's modules
- [ ] Regression guard output (1689 passed + 12 pre-existing failures)
- [ ] Browser smoke test for Recorded/Code/Replay/Save/Load flows (Cluster 10 deliverable)
- [ ] Cluster 8 handoff summary (story count, files committed, coverage, gaps)


---

## Cluster 8 Closure (2026-05-14)

| Story | Status | File |
|-------|--------|------|
| S7-0801 Recorded tab evidence | Done | recorded/RecordedPanel.jsx |
| S7-0802 Child operation evidence | Done | recorded/RecordedStepCard.jsx |
| S7-0803 Repaired/skipped/unresolved | Done | recorded/RecordedStepCard.jsx |
| S7-0804 Replay one/all | Done | replay/ReplayControls.jsx |
| S7-0805 Replay result rendering | Done | replay/ReplayResultCard.jsx |
| S7-0806 Code tab code_update | Done | code/CodePanel.jsx |
| S7-0807 Code line→step mapping | Done | code/CodeLineMapping.jsx |
| S7-0808 Code warnings/capability | Done | code/CodeWarnings.jsx |
| S7-0809 Save/load session | Done | session/SessionPanel.jsx |
| S7-0810 Export/copy code | Done | code/CodeExport.jsx |

**Commit:** 4abbb27 — single commit, RED→GREEN.
**Tests:** tests/test_frontend_recorded_code_replay_cards.py (27 tests).
**Regression:** 2444 passed / 1 skipped / 0 failed.
**Build:** dist/autoworkbench.js 1.3mb (clean).

**Architecture invariants honored:** Recorded only from step_recorded; Code only from code_update; replay success only from replay_result; save/load result from backend events; copy/export disabled without code; skipped/failed not rendered as pass.

**Forbidden-file audit:** no backend/runtime/agent/server/LLM-prompt changes; no E2E run.
