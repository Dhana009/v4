# FE-004 LLM Mode plan review UI

**Type:** Story  
**Status:** Testing  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Focused frontend contract tests and build passed; ready for acceptance  
**Dependencies:** FE-002, FE-003, EVENT-004, BE-004, BE-005  
**Blocks:** confirmation/correction user workflow, E2E plan review  
**Version:** Batch 06 v1  

---

## Product contribution

This story builds the plan review UI where the user can inspect, confirm, or correct the backend-owned plan.

## Architecture decision

Fixed:

- renders `plan_ready` from backend active plan
- confirm command includes run_id/plan_id/plan_version
- correction command does not mutate local plan directly
- revised plan renders only after backend accepts correction

## Subtasks

- [ ] source-rule mapping
- [ ] existing frontend/backend event coverage inventory
- [ ] plan_ready rendering expectations
- [ ] runtime_rejected display expectations
- [ ] command actions available from this UI state
- [ ] negative cases: unknown/malformed/missing payloads must not fake lifecycle truth
- [ ] boundary cases: stale run_id, duplicate events, correction races
- [ ] test-only slice
- [ ] narrow implementation slice
- [ ] verification commands
- [ ] stop conditions

## UI states

| State | Source |
|---|---|
| no plan | backend state |
| plan ready | plan_ready |
| correction pending | command in flight |
| stale/rejected | runtime_rejected |
| confirmed/executing | backend event/store |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE004-U-001 | Unit | render plan_ready | steps visible |
| FE004-U-002 | Unit | confirm plan | confirmed command with version |
| FE004-U-003 | Unit | correction submit | correction command |
| FE004-U-004 | Unit | stale rejection | shown to user |
| FE004-I-001 | Integration | correction then revised plan | old plan not rendered as active |

## Edge cases

- plan with many steps
- duplicate confirm
- correction while executing
- stale plan_version

---

## Testing evidence

- tests added: `tests/test_frontend_plan_recovery_rendering.py`
- implementation summary: plan review is already backend-driven through `plan_ready`; confirm/correction remain typed command paths with pending metadata only, and the Shadow DOM runtime bridge still forwards plan/clarification/recovery state into the panel
- commands/results: `python -m py_compile tests/test_frontend_plan_recovery_rendering.py`; `python -m pytest tests/test_frontend_plan_recovery_rendering.py tests/test_frontend_event_command_contract.py tests/test_command_contract.py tests/test_plan_correction.py tests/test_late_event_contract.py -q` → `88 passed`; `cd frontend && npm run build` passed
- remaining known gaps: recovery-side option/skip/stop/update_locator actions are still backend-contract work and are not part of this slice
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
