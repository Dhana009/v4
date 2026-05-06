# EPIC-005 Shadow DOM Frontend

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Primary Consumers:** DEV-1 Backend Runtime, DEV-2 LLM/DOM, DEV-4 E2E Harness  
**Capability:** Shadow DOM product UI, typed rendering, user commands, plan/recovery/recorded/code/trace surfaces  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, EPIC-003, EPIC-004, EVENT-001, EVENT-002, EVENT-003, DOM-002, DOM-005  
**Version:** Batch 06 v1  

---

## 1. Product contribution

This epic defines the real frontend target for Complete LLM Mode.

Final user value:

```text
User sees a stable Shadow DOM UI
→ backend events render current truth
→ user reviews/corrects/confirms plans
→ user answers clarification/recovery questions
→ user sees recorded steps, generated code, and trace evidence
→ user commands are sent through typed backend command envelopes
```

Without EPIC-005:

- frontend may keep relying on legacy overlay state
- lifecycle may be inferred from LLM prose or local flags
- users may confirm/correct against stale plan data
- E2E cannot reliably assert UI state
- picker/locator UI may keep selecting weak targets without backend validation

---

## 2. Final product workflow supported

| Workflow stage | Frontend contribution |
|---|---|
| ready/session | Shadow host mounts safely without polluting page |
| user input | captures natural-language intent/commands |
| plan review | renders backend `plan_ready`; user confirms/corrects |
| clarification/recovery | renders backend questions/options |
| execution | shows backend progress events |
| recording/code | renders backend `step_recorded` and `code_update` |
| trace | displays structured diagnostic evidence |
| picker | displays element/ancestor candidates without deciding truth |

---

## 3. Source evidence table

| Source | Extracted rule | Planning interpretation | EPIC-005 impact |
|---|---|---|---|
| SOURCE-001 | Frontend renders backend state and collects user input; it must not infer lifecycle from LLM prose. | UI is consumer/command source only. | Build typed event store and command dispatcher. |
| Frontend/UI Spec | Shadow DOM host is primary frontend target; injected overlay is legacy/transitional. | New work targets Shadow DOM. | Build Shadow DOM host and migration audit. |
| EPIC-002 | Event/command contracts are typed. | UI consumes events and sends commands. | FE stories depend on EVENT envelopes. |
| EPIC-004 | Picker/candidate UI must expose ancestors and candidate levels. | UI displays choices; backend validates. | FE-008 is required. |
| PLAN-005 | E2E needs stable hooks and evidence. | UI needs deterministic selectors/test hooks. | FE-009 is required. |

---

## 4. Architecture decision

Fixed decisions:

- Shadow DOM is the primary frontend architecture.
- Legacy injected overlay is transitional and must not receive new product ownership.
- Frontend renders typed backend truth only.
- Frontend sends commands through canonical command envelope.
- Frontend state store mirrors backend events; it does not become runtime truth.
- UI must expose stable test hooks and accessibility labels.
- Picker UI displays backend/DOM candidates but does not validate final locator truth.

Forbidden interpretations:

- frontend marks run_completed/step_recorded locally
- frontend infers execution state from LLM message text
- frontend silently mutates plan on correction without backend acceptance
- frontend directly executes browser actions
- broad UI rewrite without repo inspection/tests
- new work targets legacy overlay instead of Shadow DOM

---

## 5. Story map

| Story | Purpose | Direct consumers |
|---|---|---|
| FE-001 | Shadow DOM host/mount lifecycle | all frontend UI |
| FE-002 | typed event store | rendering |
| FE-003 | command dispatcher | all user actions |
| FE-004 | LLM Mode plan review UI | confirm/correction |
| FE-005 | clarification/recovery UI | user decision flows |
| FE-006 | recorded/code panel | recording/codegen |
| FE-007 | trace/diagnostic panel | debugging/E2E |
| FE-008 | picker/element candidate UI | DOM/locator |
| FE-009 | frontend test hooks/accessibility | DEV-4 E2E |
| FE-010 | legacy overlay migration audit | safe transition |

---

## 6. Direct vs indirect dependency note

Direct blockers:

```text
FE-001 Shadow DOM host
FE-002 typed event store
FE-003 command dispatcher
FE-009 test hooks/accessibility
FE-010 legacy migration audit
```

Indirect consumers:

```text
E2E harness
LLM Mode user journeys
Plan correction flow
Locator/picker workflows
Recorded/code/trace panels
```

Parallel safe work:

```text
DEV-1 can provide mock event payloads.
DEV-2 can provide mock LLM/DOM candidate payloads.
DEV-4 can build UI E2E tests using fixture events and stable test hooks.
```

---

## 7. Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Provides typed events and validates commands |
| DEV-2 LLM/DOM | Provides proposals/candidates only; frontend displays them as non-truth until backend accepts |
| DEV-3 Frontend | Primary owner; renders typed state and sends commands |
| DEV-4 E2E | Uses stable hooks/events to verify UI state and command flows |

---

## 8. Epic acceptance criteria

EPIC-005 is accepted when:

- Shadow DOM host mounts safely and consistently
- frontend typed event store consumes canonical backend events
- frontend command dispatcher sends canonical commands only
- plan review UI renders backend active plan
- confirmation/correction commands include run/plan/version identity
- clarification/recovery UI renders backend options
- recorded/code panel renders backend-owned payloads
- trace panel shows structured diagnostic events
- picker UI displays target/ancestor candidates without deciding truth
- stable test hooks/accessibility labels exist
- legacy overlay dependencies are audited and migration path is clear

---

## 9. Stop conditions

Stop if:

- current UI architecture cannot support Shadow DOM without broad rewrite
- event/command contracts are missing fields needed to render
- frontend would need to infer lifecycle truth
- legacy overlay is still the only viable target and migration path is unclear
- test hooks cannot be added without breaking product page
