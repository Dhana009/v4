# EPIC-002 Typed Event Contract

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-1 Backend Runtime + Event Truth  
**Primary Consumers:** DEV-3 Shadow DOM Frontend, DEV-4 E2E Harness, DEV-2 LLM Runtime Controller  
**Capability:** Typed Event / Command Contract  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, BE-001, BE-002, BE-003  
**Version:** Batch 03 v1  

---

## 1. Product contribution

This epic defines the typed communication contract between backend, frontend, E2E harness, and LLM boundaries.

It contributes to the final product by making this possible:

```text
backend state changes
→ typed event payload
→ Shadow DOM frontend renders truth
→ E2E harness captures/asserts event stream
→ LLM receives only allowed context/commands
```

Without EPIC-002:

- frontend may infer lifecycle from LLM prose or CSS
- E2E cannot reliably assert state transitions
- command validation may vary by handler
- recovery/completion/recording state becomes ambiguous
- future developers may invent inconsistent event names

---

## 2. Final product workflow supported

| Workflow stage | Typed contract contribution |
|---|---|
| user starts run | command envelope validates `llm_run`/`run_steps` |
| plan review | `plan_ready` payload shows backend active plan |
| correction/confirmation | commands carry run/plan/version identity |
| execution | `step_validating` / `step_executing` events show exact operation |
| failure | `step_failed` / `recovery_needed` payloads carry failed target |
| recording/codegen | `step_recorded` / `code_update` payloads carry parent/child evidence |
| replay | replay commands/events are backend-owned |
| unsupported capability | `capability_gap_recorded` gives traceable gap |

---

## 3. Source evidence table

| Source | Extracted rule | Planning interpretation | EPIC-002 impact |
|---|---|---|---|
| SOURCE-001 | Every important lifecycle change must become a typed backend event. | No hidden lifecycle transitions in logs/prose. | Define canonical event envelope and event families. |
| SOURCE-001 | Frontend sends explicit commands such as run_steps, confirmed, correction, option_selected, replay_step, replay_operation, replay_all, skip_step, stop_run, save_session, load_session, update_locator. | Commands must be validated requests, not state mutation authority. | Define command envelope and command families. |
| EPIC-001 | Backend owns runtime truth. | Events serialize backend truth; they do not create it. | Event contract depends on BE state ownership. |
| Frontend/UI Spec | Frontend renders backend state and collects user input. | Frontend needs typed events and commands. | DEV-3 consumes this epic directly. |
| E2E strategy | Harness must capture event/log evidence. | E2E needs stable payloads. | DEV-4 consumes this epic directly. |

---

## 4. Architecture decision

Fixed decisions:

- Backend event envelope is canonical.
- Frontend command envelope is canonical.
- Rejections/errors are structured.
- Events serialize backend truth; commands request backend decisions.
- LLM cannot emit runtime truth events.
- Frontend cannot mutate truth by sending status fields.

Flexible implementation choices:

- exact Python/TypeScript schema mechanism
- exact adapter layer for legacy event names
- exact WebSocket bridge file/module names after repo inspection

Forbidden interpretations:

- free-form strings as contract
- frontend-only lifecycle state
- LLM-owned `step_recorded` / `run_completed`
- silent migration from old event names without adapter/audit

---

## 5. Story map

| Story | Purpose | Depends on | Direct consumers |
|---|---|---|---|
| EVENT-001 | canonical backend event envelope | BE-001/BE-002 | all events, DEV-3, DEV-4 |
| EVENT-002 | frontend command envelope | BE-003 | command validation, DEV-3 |
| EVENT-003 | rejection/error payload | EVENT-001/002 | command/state failures |
| EVENT-004 | plan review event contract | EVENT-001, BE-004/005 | plan UI |
| EVENT-005 | step execution event contract | EVENT-001, BE-006 | execution UI/E2E |
| EVENT-006 | recording/code_update event contract | EVENT-001, BE-009 | recorded/code UI |
| EVENT-007 | recovery/clarification contract | EVENT-001/002, BE-008 | recovery UI |
| EVENT-008 | replay event/command contract | EVENT-001/002, BE-012 | replay UI/E2E |
| EVENT-009 | capability gap contract | EVENT-001, BE-011 | trace/gap backlog |
| EVENT-010 | compatibility adapter/audit | existing repo events | safe migration |

---

## 6. Direct vs indirect dependency note

Direct blockers:

```text
EVENT-001, EVENT-002, EVENT-003
```

These establish the generic envelope and rejection contract.

Indirect consumers:

```text
Frontend typed store
E2E event capture
LLM runtime schemas
Recording/code_update UI
Replay smoke
Capability backlog
```

Parallel safe work:

```text
DEV-3 may create mock event fixtures from these stories.
DEV-4 may build event capture using fixture payloads.
DEV-2 may design LLM outputs that avoid runtime truth events.
```

---

## 7. Epic acceptance criteria

EPIC-002 is accepted when:

- event envelope is defined and tested
- command envelope is defined and tested
- runtime rejection payload is defined and tested
- plan/execution/recording/recovery/replay/gap event families are covered
- frontend consumers do not need to infer lifecycle truth
- E2E can capture and assert event stream
- legacy/current event names are audited with adapter plan
- tests cover malformed/unknown/stale payloads

---

## 8. Stop conditions

Stop if:

- current WebSocket/event bridge conflicts with source and migration path is unclear
- event names differ from source and adapter decision is unclear
- frontend needs fields not present in backend event
- command payload would mutate runtime truth directly
- LLM output would bypass backend event/command validation
