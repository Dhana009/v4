# REC-002 Execution evidence to recorded step builder

**Type:** Story  
**Status:** Done  
**Priority:** P0  
**Epic:** EPIC-008 Recording and Codegen  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Done; implementation and verification complete  
**Dependencies:** REC-001, BE-006, BE-008, BE-009  
**Blocks:** step_recorded, REC-004, REC-006, E2E-010  
**Version:** Batch 09 v1  

---

## Product contribution

Builds recorded steps from validated execution evidence.

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-006 | cursor advances only with backend evidence | recording consumes evidence | validate evidence refs |
| BE-009 | backend-owned recording builder | builder owns step_recorded creation | implement builder path |
| BE-008 | unresolved recovery blocks recording | failed/unresolved child cannot record parent | check recovery state |
| SOURCE-001 | no LLM-owned truth | ignore model-emitted step_recorded | backend-only builder |

---

## Architecture boundary

Builder consumes confirmed contract plus execution evidence and produces RecordedStep. It must not inspect LLM prose as truth.

---

## Contract / schema

```text
confirmed child results
→ verify all required children terminal
→ verify evidence_refs exist
→ build RecordedChild list in confirmed order
→ build RecordedStep parent
→ validate model
→ emit/queue step_recorded
→ mark codegen eligible
```

| Child state | Parent result |
|---|---|
| all required succeeded | recordable |
| required failed unresolved | not recordable; recovery |
| optional skipped with reason | recordable if policy allows |
| missing evidence | not recordable |
| order mismatch | reject/recovery |

---

## Dependency map

| Dependency | Type | Reason |
|---|---|---|
| REC-001 | upstream | output model |
| BE-006 | upstream | evidence source |
| BE-008 | upstream | recovery blocker |
| REC-004 | downstream | codegen after recording |

---

## Four-developer coordination

| Developer | Responsibility |
|---|---|
| DEV-1 | owns builder and validation |
| DEV-2 | no recording truth |
| DEV-3 | waits for step_recorded event |
| DEV-4 | tests evidence-to-recording path |

---

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| REC002-U-001 | Unit | all children success | RecordedStep built |
| REC002-U-002 | Unit | child failed | no recording |
| REC002-U-003 | Unit | missing evidence | rejected |
| REC002-U-004 | Unit | LLM step_recorded | ignored |
| REC002-I-001 | Integration | execution to step_recorded | event-ready payload |

---

## Edge cases

- partial success
- retry after recovery
- navigation after click
- same operation emitted twice

---

## Standard artifact/evidence expectation

| Artifact/evidence | Required | Notes |
|---|---|---|
| execution evidence ref | Yes where applicable | source action/assertion result |
| recorded step payload | Conditional | required for recording stories |
| code_update payload | Conditional | required for codegen stories |
| event stream excerpt | Conditional | required when event behavior changes |
| test output | Yes | unit/integration/E2E where applicable |
| diagnostics | Yes | structured errors/warnings |

---

## Required skills

Codex must load the smallest required skill pack only:

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/backend_step_runner.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current recording path and owner
- current `step_recorded` handling
- current successful action/assertion evidence model
- current expected_outcome and observed_outcome handling
- current code_update/codegen implementation
- current recorded step ordering/deduplication behavior
- current replay archive/persistence behavior
- existing tests covering recording/codegen
- source alignment gaps
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- recording would be built from LLM prose or `last_successful_action`
- codegen would run before backend recording is finalized
- expected_outcome would become assertion target/value
- recorded child order cannot be tied to confirmed execution contract
- frontend would own recorded/code truth
- replay archive semantics are unclear
- persistence path would require broad architecture changes
- tests cannot be written before implementation

---

## Codex execution summary

First Codex task for REC-002 should be read-only:

```text
Read REC-002, SOURCE-001, PLAN-002, PLAN-005, EPIC-008, EPIC-001, EPIC-002, BE-006, BE-009, EVENT-006, and required skills.
Do not edit code.
Inspect current recording/codegen ownership for Execution evidence to recorded step builder.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
