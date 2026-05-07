# FE-010 Legacy overlay migration and compatibility audit

**Type:** Story  
**Status:** Testing  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Branch:** `dev3/frontend-test-harness-mapping`  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** MR-4E narrow implementation complete; Shadow DOM React mount and shadow-first harness lookup added  
**Dependencies:** EVENT-010, TEST-FE-001, TEST-MATRIX-FE-001, TEST-MATRIX-EVENT-001, TEST-MATRIX-E2E-001  
**Blocks:** MR-4B test-only slice selection, safe migration sequencing  
**Version:** MR-4E v1  

---

## Product contribution

This story prevents the new Shadow DOM frontend from being mixed with legacy overlay assumptions.

## Architecture decision

Fixed:

- audit current overlay/state/event dependencies before implementation
- new work targets Shadow DOM
- adapters are temporary and explicit
- legacy overlay-only behavior is marked transitional/deprecated

## MR-4A mapping subtasks

- [x] frontend matrix row mapping
- [x] existing frontend/E2E coverage inventory
- [x] missing frontend harness analysis
- [x] Shadow DOM host testability mapping
- [x] command dispatcher mapping
- [x] event store/read-model mapping
- [x] plan/clarification/recovery UI mapping
- [x] recorded/code/trace tab mapping
- [x] blocked rows and dependency list
- [x] first safe MR-4B test-only slice proposal

## MR-4A mapping evidence

MR-4A mapping completed.

### Current frontend architecture found

- `frontend/package.json` has `clean` and `build` only.
- `frontend/src/main.jsx` mounts a React root to `#autoworkbench-root`.
- UI delegates rendering to `window.IDEPanel`.
- Current tabs are legacy: `workbench`, `steps`, `code`, `debug`.
- `tests/e2e/harness.py` targets `#autoworkbench-root .ide-panel`.

### Shadow DOM status

- No `attachShadow` or `shadowRoot` was found in `frontend`.

### Dedicated frontend harness status

- No dedicated frontend component harness exists yet.
- Current coverage is pytest/E2E plus backend contract tests only.

### Existing coverage inventory

- `tests/test_browser_injection.py`
- `tests/test_ws_reconnect_grace.py`
- `tests/test_command_contract.py`
- `tests/test_event_contract.py`
- `tests/test_plan_correction.py`
- `tests/test_recording_codegen_truth_contract.py`
- `tests/test_recorded_step_model.py`
- `tests/test_replay_one.py`
- `tests/test_replay_all.py`
- `tests/test_assertion_flow.py`
- `tests/test_multi_action_safety.py`
- `tests/test_e2e_harness.py`
- `tests/e2e/test_basic_click_flow.py`
- `tests/e2e/test_visible_assertion_flow.py`
- `tests/e2e/test_exact_text_assertion_flow.py`
- `tests/e2e/test_correction_assert_then_click_flow.py`

### Missing coverage

- Shadow DOM mount/isolation
- frontend command dispatcher
- no-deadlock/safe-action UI
- picker candidate display
- trace display-only/redaction
- accessibility hooks
- legacy coexistence/truth ownership

### Blocked rows and dependency list

- FE-001 / FE-009 / FE-010 are blocked by the Shadow DOM host and harness decision.
- FE-002 / FE-003 depend on stable `EVENT-002` and `EVENT-003`.
- FE-004 / FE-005 depend on `EVENT-004` and `EVENT-007`.
- FE-006 depends on recording/code truth.
- FE-007 depends on TRACE rows, especially `TRACE-001`, `TRACE-008`, and `TRACE-010`.
- FE-008 depends on DOM rows, especially `DOM-002`, `DOM-005`, and `DOM-009`.

### MR-4B proposed test-only scope

1. FE-001 host mount/lifecycle
2. FE-009 root hook/accessibility
3. then FE-002 / FE-003 event store and command-envelope tests

## Audit table

| Current UI/path | Current role | Canonical replacement | Decision | Blocker |
|---|---|---|---|---|
| legacy overlay panel | old UI state | Shadow DOM panel | adapt/deprecate | TBD |
| old event handler | event consume | typed event store | keep/adapt/block | TBD |
| old command sender | command | command dispatcher | keep/adapt/block | TBD |
| picker path | target selection | candidate UI | adapt/block | TBD |

## Selected mapping rows

| Mapping area | Related board rows | Main dependency / blocker |
|---|---|---|
| frontend shell + host | FE-001, FE-009, FE-010 | EVENT-001, EVENT-002, EVENT-010 |
| event store + dispatcher | FE-002, FE-003 | EVENT-002, EVENT-003 |
| plan review | FE-004 | EVENT-004, BE-004, BE-005 |
| clarification + recovery | FE-005 | EVENT-007, BE-008 |
| recorded + code | FE-006 | EVENT-006, BE-009, BE-010 |
| trace + diagnostics | FE-007, TRACE-001..TRACE-010 | EVENT-003, EVENT-010, FE-009 |
| picker + test hooks | FE-008, FE-009 | DOM-002, DOM-005, DOM-009, stable Shadow DOM hooks |

## Blocked rows and dependency list

| Blocked row group | Why it stays blocked in MR-4A | Dependency / note |
|---|---|---|
| FE-001 / FE-009 host + hooks | needs host/testability mapping first | frontend harness decision not yet fixed |
| FE-002 / FE-003 store + dispatcher | needs canonical command/event shape | EVENT-002 and EVENT-003 must stay stable |
| FE-004 / FE-005 plan + recovery | needs typed plan/recovery events | EVENT-004 and EVENT-007 gate the UI shape |
| FE-006 recorded + code | needs recording/code_update truth | EVENT-006 and backend ownership remain canonical |
| FE-007 trace | needs diagnostics and redaction model | TRACE-001, TRACE-008, TRACE-010 remain linked |
| FE-008 picker | needs candidate/testability mapping | DOM-002, DOM-005, DOM-009 are the active blockers |

## First safe MR-4B test-only slice proposal

Start with the narrowest test-only slice that proves the harness path without changing product logic:

1. FE-001 host mount and lifecycle test mapping
2. FE-009 root hook and accessibility test mapping
3. then FE-002 / FE-003 read-model and command-envelope test mapping once the event contract is confirmed stable

Do not expand MR-4B into implementation until the mapping report is reviewed.

## MR-4B test-only slice evidence

- `tests/test_frontend_shadow_dom_contract.py` added
- `python -m py_compile tests/test_frontend_shadow_dom_contract.py` passed
- `python -m pytest tests/test_frontend_shadow_dom_contract.py -q` returned `1 passed, 2 xfailed`
- `python -m pytest tests/test_browser_injection.py tests/test_e2e_harness.py -q` returned `31 passed`
- xfails are expected for the missing Shadow DOM host and planned root/hook contract
- no frontend/runtime/backend/source changes

## MR-4C implementation evidence

- implemented a thin Shadow DOM host adapter in `frontend/src/main.jsx`
- preserved the existing `#autoworkbench-root` light-DOM render path
- preserved `window.IDEPanel`
- added a stable `aw-root` hook
- added stable hooks / aria labels for LLM, Recorded, Code, Trace, plan review, clarification, and recovery
- `python -m pytest tests/test_frontend_shadow_dom_contract.py -q` returned `3 passed`
- `python -m pytest tests/test_browser_injection.py tests/test_e2e_harness.py -q` returned `31 passed`
- combined verification returned `34 passed`
- `cd frontend && npm run build` succeeded
- the previous 2 xfails now pass
- no backend/runtime/test changes

## MR-4D test-only slice evidence

- added a contract test for the actual React mount targeting a Shadow DOM root
- added a passing legacy fallback harness test
- added an xfailed shadow-root-aware lookup helper contract
- `python -m pytest tests/test_frontend_shadow_dom_contract.py tests/test_browser_injection.py tests/test_e2e_harness.py -q` returned `35 passed, 2 xfailed`
- no frontend/source changes

## MR-4E implementation evidence

- mounted the actual React/product UI inside the Shadow DOM root in `frontend/src/main.jsx`
- preserved the existing `#autoworkbench-root` light-DOM host for compatibility
- preserved `window.IDEPanel`
- added shadow-root style cloning so the UI remains styled inside the shadow tree
- updated `tests/e2e/harness.py` with `find_autoworkbench_panel` and `wait_for_autoworkbench_ready` helpers that prefer Shadow DOM lookup and fall back to `#autoworkbench-root .ide-panel`
- `cd frontend && npm run build` succeeded
- `python -m pytest tests/test_frontend_shadow_dom_contract.py tests/test_browser_injection.py tests/test_e2e_harness.py -q` returned `37 passed`
- the previous 2 xfails are now green
- no backend/runtime/LLM/DOM changes

## FE-010 final regression note

- focused DEV-3 verification passed: `37 passed`
- final broad E2E regression attempted
- result: `37 passed, 4 failed`
- failure class: environment/browser startup
- root cause: `PermissionError: [Errno 1] Operation not permitted` during local static server socket bind in `tests/e2e/harness.py`
- classification: blocked by DEV-4/E2E harness environment, not a DEV-3 implementation regression
- status remains `Testing`, not `Done`
- `AGENTS.md` not committed

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE010-A-001 | Audit | list overlay entry points | complete |
| FE010-A-002 | Audit | list frontend event consumers | complete |
| FE010-A-003 | Audit | map legacy to canonical | decision per item |
| FE010-I-001 | Integration | canonical event not legacy-only | Shadow UI consumes |

## Edge cases

- both UIs mounted
- old event names only
- tests depend on legacy overlay
- hidden overlay side effects

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current frontend entry points and overlay injection path
- current Shadow DOM host/components if any
- current WebSocket/event consumer code
- current command sending code
- current plan/recorded/code/trace UI state ownership
- current picker/element-info UI behavior
- current tests and frontend test hooks
- current legacy overlay dependencies
- proposed narrow implementation path
- current FE / EVENT / MVP / TRACE board coverage inventory
- current frontend harness gaps and test-only slice candidates

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

## Stop conditions

Stop if:

- frontend would infer lifecycle truth locally
- implementation targets legacy overlay as the new product architecture
- event/command contracts are missing or incompatible
- backend truth fields are not enough to render safely
- UI command would mutate runtime state directly
- current code requires broad rewrite before tests
- frontend test hooks cannot be defined
- Shadow DOM isolation conflicts with product page behavior

---

## Codex execution summary

First Codex task for FE-010 should be read-only:

```text
Read FE-010, SOURCE-001, DEVELOPER-EXECUTION-PLAN-001, FINAL-HANDOFF-v2, TEST-DOCTRINE-001, TEST-FE-001, TEST-MATRIX-FE-001, TEST-MATRIX-EVENT-001, TEST-MATRIX-E2E-001, and required skills.
Do not edit code.
Inspect current frontend/runtime UI ownership and report a narrow MR-4A mapping path.
Do not implement until repo-inspection report is reviewed.
```
