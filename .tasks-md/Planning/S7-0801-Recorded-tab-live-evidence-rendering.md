# S7-0801 — Recorded Tab Live Evidence Rendering

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-0802, S7-0803]
**Blocked by:** [S7-0500 (frontend event store), S7-0504 (step lifecycle handlers)]

---

## Objective

Build the Recorded tab frontend component to render backend-recorded steps in real time. Display parent recorded steps, metadata (validation count, observed/expected outcome), and evidence references. Show empty state before recording starts. No draft/pending/inferred steps appear as recorded evidence.

After S7-0801:
- Recorded tab component exists and renders `recordedSteps` from frontend event store
- `step_recorded` backend events update frontend store
- Empty state shows before any steps are recorded
- Malformed recorded payloads are safely rejected

---

## Source Rules

- PRD-05-REC-001: Recorded evidence shows validated steps with locator used, validation count, observed/expected outcomes
- PRD-05-REC-002: Child operation evidence includes action/assertion type, locator/target, expected_outcome metadata (not execution truth)
- PRD-03-FE-C8-001 (Cluster 8 Rule C8-1): Frontend renders only `step_recorded` events; never infers recording from local state
- PRD-03-FE-011: Frontend renders backend truth only; no demo/draft content in live mode
- GOV-S7-C0-007: No source rule → no test; no test → no implementation
- GOV-S7-C8-001 (Cluster 8): Backend owns runtime truth; frontend renders, never simulates

---

## Current Known Context

### What exists
- `step_recorded` event builder exists in `runtime/event_contracts.py`
- `step_recorded` payload schema defined in PRD `04_BACKEND_EVENT_CONTRACT.md`
- Frontend event store infrastructure exists (S7-0500) but handlers for `step_recorded` not yet implemented
- No Recorded tab component exists in `frontend/src/`
- `frontend_new_design_prototype/` has static HTML mockups of Recorded tab (design reference only)

### What gaps exist
- No Recorded tab component
- No `step_recorded` event handler in frontend store
- No reducer logic to accumulate recordedSteps[]
- No display of parent step metadata (step_id, locator_used, validation_count, observed_outcome, expected_outcome)
- No display of evidence references (trace link, artifact link)
- No empty state placeholder
- No malformed payload rejection with diagnostics

### Current test status
- `tests/test_frontend_llm_mode_complete.py` has contract tests for `step_recorded` payload shape but no component or store tests
- No frontend reducer/component tests for Recorded tab rendering

---

## Tests First

### Unit Tests

```python
# tests/test_frontend_recorded_evidence_rendering.py

test_recorded_step_from_event_payload()  # PRD-05-REC-001
  # Transform step_recorded backend event to RecordedStep frontend type
  # Verify: step_id, locator_used, validation_count, observed_outcome, expected_outcome, timestamp present

test_recorded_step_rejects_missing_step_id()  # GOV-S7-C0-009
  # Malformed payload without step_id must not crash renderer

test_recorded_step_rejects_missing_locator()  # GOV-S7-C0-009
  # Recorded step without locator_used should be rejected or show "unknown locator" safely

test_recorded_step_timestamp_formatting()  # PRD-05-REC-001
  # Timestamp rendered as human-readable string with timezone

test_recorded_step_outcome_rendering()  # PRD-05-REC-002
  # observed_outcome and expected_outcome both rendered
  # expected_outcome is metadata (does not imply step passed)
```

### Contract Tests

```python
test_step_recorded_event_contract_minimal()  # PRD-04-BACKEND-001
  # step_recorded event with required fields only (no children, no evidence refs)

test_step_recorded_event_contract_full()  # PRD-04-BACKEND-001
  # step_recorded event with all optional fields (children, evidence_refs, diagnostics)

test_step_recorded_event_contract_malformed_rejects()  # PRD-04-BACKEND-003
  # Invalid step_recorded payload (null step_id, wrong type for validation_count, etc.)
  # Frontend must not render; must show diagnostic
```

### Reducer Tests

```python
test_reducer_step_recorded_event_appends_to_recordedsteps()  # PRD-03-FE-011
  # reducer(state, {type: 'step_recorded', payload: {...}}) appends to state.recordedSteps

test_reducer_step_recorded_event_maintains_order()  # PRD-05-REC-001
  # Multiple step_recorded events → recordedSteps maintains backend order

test_reducer_step_recorded_event_rejects_stale_step_id()  # GOV-S7-C0-009
  # If step_id already in recordedSteps, new event with same id is rejected with diagnostic

test_reducer_ignores_non_recorded_events()  # PRD-03-FE-011
  # Other event types (planning_started, step_executing, etc.) do not affect recordedSteps
```

### Component Tests

```python
test_recorded_tab_renders_empty_state()  # PRD-03-FE-011
  # No recorded steps → show "No steps recorded yet" or placeholder

test_recorded_tab_renders_recorded_steps()  # PRD-05-REC-001
  # recordedSteps[] with 1+ items → each renders as row with step_id, locator, validation_count

test_recorded_tab_renders_step_metadata()  # PRD-05-REC-001
  # Visible fields: step_id, locator_used, validation_count, observed_outcome, expected_outcome

test_recorded_tab_renders_evidence_link()  # PRD-05-REC-001
  # If evidence_refs provided, show link to trace/artifact

test_recorded_tab_renders_timestamp()  # PRD-05-REC-001
  # step timestamp rendered as human-readable string

test_recorded_tab_renders_malformed_safe()  # GOV-S7-C0-009
  # Malformed recorded step → show [!] error badge, do not crash
```

### Command Dispatcher Tests

```python
# No new commands in this story; skip
```

### Integration Tests

```python
test_recorded_tab_integration_event_to_display()  # PRD-05-REC-001 + PRD-03-FE-011
  # End-to-end: dispatch step_recorded event → reducer updates state → component re-renders
  # Verify displayed step_id matches event payload
```

### Negative Tests

```python
test_recorded_step_with_null_step_id_rejected()  # GOV-S7-C0-009
  # step_recorded event with step_id=null → no render, diagnostic shown

test_recorded_step_with_missing_locator_shows_fallback()  # GOV-S7-C0-009
  # step_recorded without locator_used → show "unknown" or skip field, do not crash

test_recorded_step_with_wrong_validation_count_type_rejected()  # GOV-S7-C0-009
  # validation_count not a number → reject with diagnostic

test_recorded_step_validation_count_zero_renders()  # GOV-S7-C8-001
  # validation_count can be 0 (step never validated); must render correctly

test_recorded_tab_ignores_draft_step_state()  # GOV-S7-C8-001
  # If frontend has draft step in store, it must not appear in Recorded tab
  # Only step_recorded events should appear in Recorded tab
```

### Regression Tests

Run after implementation:
```bash
python -m pytest tests/test_frontend_recorded_evidence_rendering.py tests/test_step_recorded_event_contract.py -v
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5  # Full cheap suite must stay green
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/recorded/RecordedTab.jsx (new — main component)
- frontend/src/components/recorded/RecordedStep.jsx (new — step row component)
- frontend/src/components/recorded/RecordedEvidence.jsx (new — evidence display)
- frontend/src/store/recordedSlice.js (new — reducer for recordedSteps state)
- frontend/src/store/handlers/step_recorded_handler.js (new — event handler)
- frontend/src/aw-ide-panel.jsx (modification at prop/callback boundaries only)
- frontend/src/main.jsx (modification for state threading only)
- tests/test_frontend_recorded_evidence_rendering.py (new)
```

### Forbidden Files

```
- agent.py (no changes)
- runtime/*.py (no changes)
- frontend_new_design_prototype/ (read-only)
- frontend/src/aw-workbench.jsx
- frontend/src/aw-tabs.jsx (infrastructure assumed existing)
```

---

## Implementation Notes

### Approach

1. Create `RecordedTab` component that consumes `recordedSteps` from frontend event store
2. Create `RecordedStep` subcomponent to render single step row with metadata
3. Create reducer/handler in event store to process `step_recorded` events into state
4. Wire `RecordedTab` into `aw-ide-panel.jsx` tab layout (if tabs already exist)
5. Add safe guards: reject malformed payload, show empty state, show diagnostics for errors

### Key Invariants

- `recordedSteps` is append-only; old steps never removed until new run starts
- Frontend renders only events from event store; never infers recording state
- Empty state shows before first `step_recorded` event
- Malformed payload never crashes renderer; shows diagnostic
- Backend event order preserved in frontend display

### Known Risks

- If frontend event store is not yet wired (S7-0500 incomplete), this story cannot start
- If `step_recorded` event handler is missing, backend events will not reach frontend state
- If tab layout does not exist, need to create thin tab wiring in `aw-ide-panel.jsx`

---

## Coverage Requirement

Minimum 95% line coverage for new modules:

```bash
python -m pytest tests/test_frontend_recorded_evidence_rendering.py --cov=frontend/src/components/recorded --cov=frontend/src/store/recordedSlice --cov-fail-under=95
```

---

## Validation Commands

```bash
# Unit + contract + component tests
python -m pytest tests/test_frontend_recorded_evidence_rendering.py -v

# Regression guard
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5

# Coverage check
python -m pytest tests/test_frontend_recorded_evidence_rendering.py --cov=frontend/src/components/recorded --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] RecordedTab component renders recordedSteps from event store
- [ ] Recorded step shows step_id, locator_used, validation_count, observed/expected outcomes
- [ ] Empty state shows before any steps recorded
- [ ] Malformed payload rejected with diagnostic; no crash
- [ ] All unit/contract/reducer/component tests pass
- [ ] No new failures in regression guard
- [ ] Coverage ≥ 95% for new modules
- [ ] No forbidden files modified
- [ ] Evidence committed and linked

---

## Evidence Required

- [ ] `frontend/src/components/recorded/RecordedTab.jsx` committed
- [ ] `frontend/src/components/recorded/RecordedStep.jsx` committed
- [ ] `frontend/src/store/recordedSlice.js` committed
- [ ] `tests/test_frontend_recorded_evidence_rendering.py` committed
- [ ] All tests passing — output pasted or file attached
- [ ] Regression guard passing — output pasted
- [ ] Coverage ≥ 95% — output pasted
- [ ] Story status updated to Done

---

## Stop Conditions

Stop if:

- Frontend event store (S7-0500) is not complete or does not have reducer pattern
- `step_recorded` event schema changes in a way that breaks this story's assumptions
- Tab layout infrastructure does not exist (ask for S7-04xx frontend architecture pre-work)
- Implementation requires modifying `agent.py` or `runtime/` files
- Test coverage cannot reach 95% without significant refactor
- Regression guard fails with a new failure (investigate before continuing)
- A bug is found in the `step_recorded` event builder (file BUG ticket; do not fix in this story)

