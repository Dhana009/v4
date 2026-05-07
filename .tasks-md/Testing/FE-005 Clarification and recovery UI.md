# FE-005 Clarification and recovery UI

**Type:** Story  
**Status:** Testing  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Focused frontend contract tests and build passed; ready for acceptance  
**Dependencies:** FE-002, FE-003, EVENT-007, BE-008  
**Blocks:** clarification/recovery flows, E2E negative paths  
**Version:** Batch 06 v1  

---

## Product contribution

This story lets frontend ask the user for missing info or recovery decisions without guessing.

## Architecture decision

Fixed:

- clarification/recovery options come from backend event
- option_selected uses canonical target.kind/id
- UI cannot mark recovery resolved
- skip/stop require typed commands

## Subtasks

- [ ] source-rule mapping
- [ ] existing frontend/backend event coverage inventory
- [ ] clarification_needed rendering expectations
- [ ] recovery_needed rendering expectations
- [ ] runtime_rejected display expectations
- [ ] command actions available from each UI state
- [ ] negative cases: unknown/malformed/missing payloads must not fake lifecycle truth
- [ ] boundary cases: stale run_id, duplicate events, recovery open blocks completed UI
- [ ] test-only slice
- [ ] narrow implementation slice
- [ ] verification commands
- [ ] stop conditions

## UI contract

| UI surface | Source event | Commands |
|---|---|---|
| clarification question | clarification_needed | option_selected |
| recovery card | recovery_needed | option_selected/skip_step/stop_run/update_locator |
| failure summary | step_failed/recovery_needed | none directly |
| rejection banner | runtime_rejected | contextual retry/user action |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE005-U-001 | Unit | clarification event | question/options render |
| FE005-U-002 | Unit | select option | option_selected command |
| FE005-U-003 | Unit | recovery event | options render |
| FE005-U-004 | Unit | skip without reason UI | blocked or reason required |
| FE005-I-001 | Integration | recovery rejection | typed rejection shown |

## Edge cases

- stale option id
- free-form answer
- repeated failure
- stop from recovery

---

## Testing evidence

- tests added: `tests/test_frontend_plan_recovery_rendering.py`
- implementation summary: `recovery_needed` now drives the backend-owned recovery read-model in `frontend/src/main.jsx`; recovery instruction sending stays typed/pending-only and does not locally close lifecycle truth
- commands/results: `python -m py_compile tests/test_frontend_plan_recovery_rendering.py`; `python -m pytest tests/test_frontend_plan_recovery_rendering.py tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` → `88 passed`; `cd frontend && npm run build` passed
- remaining known gaps: recovery option variants like `skip_step`, `stop_run`, and `update_locator` remain backend-contract work and are not part of this slice
- no backend/runtime/LLM/DOM changes

---

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
