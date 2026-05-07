# FE-006 Recorded steps and code panel rendering

**Type:** Story  
**Status:** Inprogress  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Repo inspection complete; test-first implementation in progress  
**Dependencies:** FE-002, EVENT-006, BE-009  
**Blocks:** recorded/code UI, E2E recording assertions  
**Version:** Batch 06 v1  

---

## Product contribution

This story renders backend-owned recorded steps and generated Playwright code.

## Architecture decision

Fixed:

- recorded steps come only from `step_recorded`
- code comes only from `code_update`
- UI preserves parent/child order from backend
- expected_outcome metadata is displayed as metadata only

## Subtasks

- [x] source-rule mapping
- [x] existing recorded/code backend tests inventory
- [x] step_recorded rendering expectations
- [x] code_update rendering expectations
- [x] parent/child recorded-step display expectations
- [x] negative cases: code_update without step_recorded must not fake recorded truth
- [x] boundary cases: duplicate step_recorded, failed child, unresolved child, missing operation_id
- [x] read-model rule: backend events only, no frontend-generated recorded/code truth
- [x] test-only slice
- [x] narrow implementation slice
- [x] verification commands
- [x] stop conditions

## Rendering contract

| Panel | Data source |
|---|---|
| Recorded steps | step_recorded.recorded_step |
| Child operations | recorded_step.children |
| Code | code_update.lines |
| Diagnostics | code_update.diagnostics |
| Metadata | expected_outcome_metadata |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE006-U-001 | Unit | step_recorded event | recorded row appears |
| FE006-U-002 | Unit | children order | order preserved |
| FE006-U-003 | Unit | code_update | code panel updates |
| FE006-U-004 | Unit | diagnostic_only | diagnostics shown |
| FE006-I-001 | Integration | recording→code | panels match backend events |

## Edge cases

- duplicate recorded step
- code_update before recording
- failed recording
- long code output

---

## Testing evidence

- tests added: `tests/test_frontend_recorded_code_rendering.py`
- implementation summary: `step_recorded` now drives the recorded-step read model, `code_update` now drives code preview plus preserved diagnostics, and recorded child structures continue to flow through the Shadow DOM panel bridge without inventing lifecycle truth
- commands/results: `python -m py_compile tests/test_frontend_recorded_code_rendering.py`; `python -m pytest tests/test_frontend_recorded_code_rendering.py tests/test_recorded_step_model.py tests/test_code_update.py tests/test_recording_codegen_truth_contract.py tests/test_frontend_plan_recovery_rendering.py tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` → `113 passed`; `cd frontend && npm run build` passed
- remaining known gaps: code panel diagnostics are preserved in runtime state for now, but the visible panel still renders the backend code preview text only
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
