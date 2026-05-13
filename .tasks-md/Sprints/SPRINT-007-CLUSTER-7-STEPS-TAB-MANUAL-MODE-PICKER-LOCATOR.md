# Sprint 7 — Cluster 7: Steps Tab + Manual Mode + Picker/Locator Workflows

**Sprint:** Sprint 7  
**Cluster:** 7  
**Status:** Planning  
**Date:** 2026-05-13  
**HEAD at planning:** 8bdd8def90b71fdaa24890943ec792b55397c66f

---

## Cluster 7 Goal

The Steps tab is the deterministic/manual control surface. Users should be able to:
- View and edit pending steps
- Pick elements and build locators manually
- Create manual action and assertion steps
- Run steps individually or in batch
- See live validation, execution, and recording feedback

Manual Mode sits inside Steps tab as a mode toggle (not a separate tab). It is deterministic first; LLM help is explicit and optional.

After Cluster 7, users can build and run automation workflows manually (without LLM), with support for element picking, locator validation, expected outcomes, and live status feedback.

---

## Current State Audit

### Steps Tab Existing Implementation

**In `frontend_new_design_prototype/secondary-tabs.jsx`:**
- Steps list rendering (design reference)
- Step editing UI (partial design)
- Manual action/assertion builders (partial design)
- Run controls (design only)

**In production `frontend/src/`:**
- Minimal Steps tab
- Not wired to backend pendingSteps state
- Static mock data

**Issues:**
1. Steps render from static data, not backend
2. Element picker not integrated
3. Locator candidates not displayed
4. Manual action/assertion builders not implemented
5. Run commands not wired

### Backend/Picker Status

| Component | Status | Issues |
|---|---|---|
| pendingSteps state | Exists | Not backend-driven |
| step_validating event | Exists | Not rendered in Steps tab |
| element picker | Basic UI exists | Not integrated with locator workflow |
| locator_candidates_ready | Emitted by Cluster 2 | Not rendered in Steps tab |
| run_selected/run_steps command | Defined | Not wired to Steps tab |
| step_executing/step_recorded events | Exist | Not rendered in tab |

### Design Reference

**Design prototype:** `frontend_new_design_prototype/secondary-tabs.jsx` (51KB)
- Step list with edit controls
- Action/assertion builders
- Picker integration
- Run controls
- **Note:** Reference only; production extraction must be modular

---

## Source Rules (Priority Order)

1. **PRD v2.3** — `03_FRONTEND_RUNTIME.md`, `04_BACKEND_EVENT_CONTRACT.md`
2. **Frontend UI Spec** — `autoworkbench_complete_llm_mode_frontend_ui_spec.md`
3. **Sprint 7 Governance** — `SPRINT-007-CLUSTER-0-GOVERNANCE.md`
4. **Cluster 7 strategy:** Manual Mode is deterministic first; automation builder; LLM help is optional

---

## Steps/Manual Mode State Matrix

| State | Backend event(s) | User actions | Next state |
|---|---|---|---|
| Idle/Steps | ready | Add/edit/delete step, toggle Manual Mode | Editing |
| Editing | (local draft) | Attach element, set action/params | Selecting or Editing |
| Selecting element | arm_picker | Pick element or cancel | Editing |
| Validating locator | step_validating | Choose candidate or improve | Editing or Running |
| Running | run_selected/run_all + step_executing | (wait) | Executing or Recovery |
| Executing | step_executing | (wait) | Recorded or Recovery |
| Recorded | step_recorded | View evidence, continue | Executing/Idle |

---

## Backend Command Dependency Table

| Story | Command | Must emit | Must not infer |
|---|---|---|---|
| S7-0701 — Live Steps rendering | None (consume) | None | Does not mark steps as truth without event |
| S7-0702 — Step editing | add_step/edit_step/delete_step/reorder_step | None initially (local draft) | Does not execute edits locally |
| S7-0703 — Run controls | run_selected/run_all/run_steps | None | Does not mark running until backend event |
| S7-0704 — Picker integration | arm_picker | pick_element/pick_section command | Does not assume picker success |
| S7-0705 — Element preview | (no command) | None | Does not infer element validity |
| S7-0706 — Locator candidates | (no command) | None | Does not apply candidate locally |
| S7-0707 — Locator commands | validate_locator/improve_locator/update_locator | None | Does not mark locator valid until backend |
| S7-0708 — Manual Mode toggle | (mode change) | None | Does not auto-invoke LLM in Manual Mode |
| S7-0709 — Action builder | add_step (for manual action) | None (local draft) | Does not execute manually-built steps |
| S7-0710 — Assertion builder | add_step (for manual assertion) | None (local draft) | Does not validate assertions locally |
| S7-0711 — Expected values | (metadata) | None | Does not use test data without backend validation |
| S7-0712 — Blocked states | (no command) | None | Shows reason for blocked action |

---

## Frontend Command Table

| Story | Command | Payload | Backend behavior |
|---|---|---|---|
| S7-0702 | add_step | run_id, action, locator, params, expected_outcome? | Create draft step or validate |
| S7-0702 | edit_step | run_id, step_id, action, locator, params | Update step or return validation error |
| S7-0702 | delete_step | run_id, step_id | Remove step |
| S7-0702 | reorder_step | run_id, step_id, new_position | Reorder step |
| S7-0703 | run_selected | run_id, step_ids[] | Run selected steps |
| S7-0703 | run_all | run_id | Run all pending steps |
| S7-0704 | arm_picker | run_id, mode: "element" | "section", target_section? | Start element picker |
| S7-0704 | pick_element | run_id, step_id?, locator_hint, element_selector | Select element |
| S7-0706 | choose_locator_candidate | run_id, step_id, candidate_id | Use candidate locator |
| S7-0707 | validate_locator | run_id, step_id, locator | Validate locator on live page |
| S7-0707 | improve_locator | run_id, step_id, user_hint | Request locator improvement |
| S7-0709 | add_step (manual action) | action, locator, params, expected_outcome | Create manual action step |
| S7-0710 | add_step (manual assertion) | assertion_type, expected_value, locator | Create manual assertion step |

---

## No-Frontend-Inference Rules

1. **Do NOT infer steps as correct.** Wait for backend validation.
2. **Do NOT apply locator candidate locally.** Backend validates.
3. **Do NOT auto-pick element.** User must confirm pick.
4. **Do NOT validate assertions locally.** Backend validates.
5. **Do NOT infer Manual Mode execution.** Backend Step Runner executes.
6. **Do NOT auto-focus next step.** Wait for backend step_executing event.
7. **Do NOT synthesize locator improvements.** LLM help is explicit.
8. **Do NOT fill expected_outcome fields with defaults.** User provides or backend suggests.
9. **Do NOT show element preview as evidence.** It is candidate/context only.
10. **Do NOT assume successful steps when running manually.** Backend confirms recording.

---

## Story List

### Cluster 7 Stories (12 total)

| Story | Title | Tier |
|---|---|---|
| S7-0701 | Live Steps tab wiring | 1 |
| S7-0702 | Add/edit/delete/reorder/duplicate step UI | 1 |
| S7-0703 | Run selected and run all commands | 1 |
| S7-0704 | Picker element and section integration | 1 |
| S7-0705 | Selected element preview | 2 |
| S7-0706 | Locator candidate display | 1 |
| S7-0707 | Validate and improve locator commands | 1 |
| S7-0708 | Manual Mode toggle and workspace | 1 |
| S7-0709 | Manual action builder | 1 |
| S7-0710 | Manual assertion builder | 1 |
| S7-0711 | Expected value and test data handling | 2 |
| S7-0712 | Wrong-page, missing-data, and weak-locator states | 2 |

---

## Implementation Scope

### Allowed Files

Frontend components:
- `frontend/src/components/steps/**` (new directory)
- `frontend/src/components/manual/**` (new directory)
- `frontend/src/components/locator/**` (new directory)
- `frontend/src/components/picker/**` (new directory)
- `frontend/src/store/steps_reducer.js` (new)
- `frontend/src/commands/step_commands.js` (new or extend)
- `frontend/src/commands/picker_commands.js` (new)
- `frontend/src/aw-ide-panel.jsx` (thin wiring only)
- `frontend/src/styles/steps.css` (new)

Tests:
- `tests/test_frontend_steps_*.py` (new)
- `tests/test_frontend_manual_*.py` (new)
- `tests/test_frontend_locator_*.py` (new)
- `tests/test_frontend_picker_*.py` (new)

### Forbidden Files

- No picker backend implementation (Cluster 1 scope if backend picker needed)
- No LLM locator improvement (optional in Manual Mode)
- No browser injection (Cluster 4 scope)
- No live website automation (test scope)

---

## Tests-First Requirements

Every story must include:

1. **Unit tests** — reducer, command builders, state logic
2. **Contract tests** — command payload shapes, event handling
3. **Component tests** — render, props, user interactions
4. **Integration tests** — command dispatch, state updates, event handling
5. **Negative tests** — missing fields, stale state, invalid inputs
6. **Regression tests** — existing tests stay green

### Key Test Expectations

- **No static demo steps in live mode** — test asserts empty state until backend event
- **Picker integration safe** — test mocks picker without browser
- **Locator validation safe** — test asserts no local validation
- **Manual steps not auto-executed** — test asserts backend command required
- **Blocked states clear** — test shows disabled reason
- **Expected outcomes optional** — test handles missing field

---

## Component/Browser Test Expectations

Cluster 7 focuses on **component contract tests** and **command dispatch tests**. Browser/picker tests are Cluster 4 (E2E).

For Cluster 7:
- React component unit tests
- Step reducer tests
- Command builder tests (payloads)
- Picker simulation tests (not real browser)

**No real browser, no paid LLM, no live element picking in Cluster 7.**

---

## Definition of Done

For Cluster 7:

- [ ] All 12 story files created in `.tasks-md/Planning/` with Planning status
- [ ] Each story includes source rules, objective, current context, tests-first plan
- [ ] Cluster 7 sprint doc completed (this file)
- [ ] All stories reference backend event contracts and command payloads
- [ ] No implementation code written
- [ ] No tests run
- [ ] No stories moved to In Progress or Done

---

## Stop Conditions

Stop and escalate if:

1. Picker backend integration required but not available from Cluster 1
2. Steps tab wiring requires broad refactor of aw-ide-panel.jsx
3. Manual Mode requires LLM logic conflicting with deterministic-first approach
4. Locator validation requires live browser (not Cluster 7 scope)
5. Expected outcome metadata conflicts with backend payload structure
6. Tests cannot be written without real element picking

---

## Evidence Requirements

Cluster 7 planning is complete when:

- [ ] `.tasks-md/Sprints/SPRINT-007-CLUSTER-7-STEPS-TAB-MANUAL-MODE-PICKER-LOCATOR.md` exists
- [ ] 12 story files created in `.tasks-md/Planning/` with correct names:
  - S7-0701-Live-Steps-tab-wiring.md
  - S7-0702-Add-edit-delete-reorder-duplicate-step-ui.md
  - S7-0703-Run-selected-and-run-all-commands.md
  - S7-0704-Picker-element-and-section-integration.md
  - S7-0705-Selected-element-preview.md
  - S7-0706-Locator-candidate-display.md
  - S7-0707-Validate-and-improve-locator-commands.md
  - S7-0708-Manual-Mode-toggle-and-workspace.md
  - S7-0709-Manual-action-builder.md
  - S7-0710-Manual-assertion-builder.md
  - S7-0711-Expected-value-and-test-data-handling.md
  - S7-0712-Wrong-page-missing-data-and-weak-locator-states.md
- [ ] All stories in Planning status
- [ ] No implementation code changed
- [ ] Committed to git

---

## Recommended Next Step

After Cluster 7 planning: **Create Sprint 7 Cluster 8 and Cluster 9 planning tickets** (Recorded/Code/Replay tabs, Trace tab, final E2E smoke gate).
