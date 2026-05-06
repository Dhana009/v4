# FINAL-HANDOFF Complete LLM Mode Planning and Implementation Sequence

**Type:** Final Planning Handoff  
**Status:** Planning-ready  
**Applies To:** AutoWorkbench / Playwright Automation Co-pilot  
**Scope:** Complete LLM Mode MVP planning, repo-inspection sequencing, P1/P2 governance  
**Audience:** Next thinking agent, Codex workers, four implementation developers  
**Version:** Final Planning Handoff v1  

---

## 1. Executive status

Planning is now complete at the backlog level.

The system has been decomposed into architecture epics, story backlogs, patches, E2E proof requirements, MVP flows, recording/codegen, trace/observability, and advanced backlog governance.

Current status:

```text
Planning-ready: Yes
Repo-inspection-ready: Yes
Implementation-ready: No
Sprint-ready: Not yet
```

Important rule:

```text
Planning-ready does not mean implementation-ready.
Every story still requires repo inspection before implementation.
```

---

## 2. Source hierarchy

Use this authority order when conflicts appear:

```text
1. PRD v2.3 modular docs
2. Complete LLM Mode architecture/spec documents
3. Frontend/UI spec
4. LLM Runtime Policy spec
5. Three-part handoff lessons
6. Tasks.md planning files and patches
7. Repo skills
8. Current implementation code
```

If current implementation conflicts with source architecture, do not copy implementation behavior blindly. Report the gap during repo inspection.

---

## 3. Non-negotiable architecture invariants

These rules must survive every implementation task.

```text
LLM thinks/proposes only.
Backend validates/decides/executes/records/completes.
Frontend renders backend truth and sends typed commands.
Trace observes and explains evidence; trace is not truth.
Recording and codegen are backend-owned.
Replay is backend-owned.
DOM/locator truth is backend/browser validated.
Expected_outcome is metadata only.
No story is implemented without tests/evidence.
```

Forbidden:

```text
LLM-owned run_completed
LLM-owned step_recorded
frontend-owned lifecycle success
frontend inference from LLM prose
codegen from LLM prose
recording from last_successful_action
expected_outcome used as assertion target/value
trace used as runtime source of truth
P1/P2 silently promoted into MVP
```

---

## 4. Batch inventory

| Batch | Epic / Scope | Files |
|---|---|---|
| Batch 01 | Planning foundation + EPIC-001 seed | SOURCE-001, PLAN-001 to PLAN-005, EPIC-001, BE-001 |
| Batch 02 | Backend Runtime Truth | BE-002 to BE-012 |
| Batch 03 | Typed Event Contract | EPIC-002, EVENT-001 to EVENT-010 |
| Batch 04 | LLM Runtime Controller | EPIC-003, LLM-001 to LLM-010 |
| Batch 05 | DOM and Locator Strategy | EPIC-004, DOM-001 to DOM-010 |
| Batch 06 | Shadow DOM Frontend | EPIC-005, FE-001 to FE-010 |
| Batch 07 | E2E Harness and Real-world Fixtures | EPIC-006, E2E-001 to E2E-010 |
| Batch 08 | Complete LLM Mode MVP Flows | EPIC-007, MVP-001 to MVP-010 |
| Batch 09 | Recording and Codegen | EPIC-008, REC-001 to REC-010 |
| Batch 10 | Trace and Observability | EPIC-009, TRACE-001 to TRACE-010 |
| Batch 11 | Advanced Capabilities and Governance | EPIC-010, GOV-001 to GOV-010 |

---

## 5. Patch inventory

| Patch | Applies to | Status | Blocking before implementation? | Purpose |
|---|---|---|---:|---|
| PATCH-001 | Early backend/event planning | Apply if present | Yes | Backend/event completeness corrections |
| PATCH-002 | Event contract planning | Apply if present | Yes | Event/command dependency corrections |
| PATCH-003 | Batch 04 / EPIC-003 | Applied after Codex review | Yes | LLM side effects, skill precedence, tool phase matrix, retry rules |
| PATCH-004 | Batch 05 / EPIC-004 | Applied after Codex review | Yes | DOM source evidence, ambiguity, assertion taxonomy, fixture coverage |
| PATCH-005 | Batch 06 / EPIC-005 | Applied after Codex review | Yes | Shadow DOM lifecycle, event store, command dispatcher, UI hooks |
| PATCH-006 | Batch 07 / EPIC-006 | Applied after Codex review | Yes | E2E startup, event correlation, fixture registry, artifacts, CI/local rules |
| PATCH-007 | Batch 08 / EPIC-007 | Applied after Codex review | Yes | MVP artifacts, LLM policy, fixture mapping, command/UI dependencies |
| PATCH-008 | Batch 10 / EPIC-009 | Applied after Codex review | Yes | Trace identity, redaction, export manifest, trace-is-evidence invariant |
| PATCH-009 | Batch 11 / EPIC-010 | Applied after Codex review | Yes | Governance rubric, gap lifecycle, final handoff schema |

Before implementation starts, verify every patch file is present in `.tasks-md/Planning/`.

---

## 6. Epic dependency graph

```text
EPIC-001 Backend Runtime Truth
  ↓
EPIC-002 Typed Event Contract
  ↓
EPIC-003 LLM Runtime Controller
  ↓
EPIC-004 DOM and Locator Strategy
  ↓
EPIC-005 Shadow DOM Frontend
  ↓
EPIC-006 E2E Harness and Real-world Fixtures
  ↓
EPIC-007 Complete LLM Mode MVP Flows
  ↓
EPIC-008 Recording and Codegen
  ↓
EPIC-009 Trace and Observability
  ↓
EPIC-010 Advanced Capabilities and Backlog Governance
```

Implementation should not follow this as a strict waterfall. It should follow dependency-aware repo inspection first, then build stable foundation slices.

---

## 7. Story inventory by workstream

### Backend / Runtime

```text
BE-001 to BE-012
REC-001 to REC-010
TRACE backend-related stories
MVP backend event/evidence flows
```

Backend owns:

```text
runtime state
plan state
command validation
execution contract
recording
codegen
completion
replay
trace emission
```

### Event Contract

```text
EVENT-001 to EVENT-010
```

Events/commands are typed. UI and tests must consume canonical envelopes.

### LLM Runtime

```text
LLM-001 to LLM-010
```

LLM outputs are proposals. Runtime Controller owns purpose, schema, tools, skills, telemetry, retry/fail-closed policy.

### DOM / Locator

```text
DOM-001 to DOM-010
```

Deterministic-first. LLM locator specialist is advisory only. Backend/browser validates final locator truth.

### Frontend

```text
FE-001 to FE-010
```

Shadow DOM is primary target. Legacy overlay is transitional. Frontend renders backend truth only.

### E2E / Fixtures

```text
E2E-001 to E2E-010
```

Proves product behavior with backend event stream, Shadow DOM UI, target-page evidence, realistic local fixtures, and artifacts.

### MVP Flows

```text
MVP-001 to MVP-010
```

Defines release acceptance flows and known V1 regression coverage.

### Governance

```text
GOV-001 to GOV-010
```

Controls P1/P2 classification, advanced capabilities, replay repair, session restore, observed outcome enhancements, picker improvements, multi-model orchestration, UX polish, refactor, and final sequencing.

---

## 8. Planning readiness table

| Area | Planning-ready | Repo-inspection-ready | Implementation-ready |
|---|---:|---:|---:|
| Backend Runtime Truth | Yes | Yes | No |
| Typed Event Contract | Yes | Yes | No |
| LLM Runtime Controller | Yes | Yes | No |
| DOM and Locator Strategy | Yes | Yes | No |
| Shadow DOM Frontend | Yes | Yes | No |
| E2E Harness and Fixtures | Yes | Yes | No |
| Complete LLM Mode MVP Flows | Yes | Yes | No |
| Recording and Codegen | Yes | Yes | No |
| Trace and Observability | Yes | Yes | No |
| Advanced Governance | Yes | Yes / classification-ready | No |

---

## 9. Recommended implementation sequencing

### Phase 0: Repo-inspection only

Do this before coding.

```text
1. Inspect repo structure and current architecture.
2. Map current files to epics/stories.
3. Identify legacy overlay vs Shadow DOM paths.
4. Identify current backend runtime ownership.
5. Identify current LLM call sites and tool exposure.
6. Identify current DOM/locator code.
7. Identify current tests, fixtures, scripts, and CI.
8. Identify missing skills/source files.
9. Produce gap report.
10. Do not implement yet.
```

### Phase 1: Test harness and evidence skeleton

Start here because every future change needs proof.

```text
E2E-001 Product startup harness
E2E-002 Backend event capture
E2E-003 Shadow DOM UI harness
E2E-004 Fixture server/registry
TRACE-001 Trace identity model
TRACE-009 Artifact bundle/export format
```

Purpose:

```text
Create the ability to prove product behavior before broad implementation.
```

### Phase 2: Backend runtime and event foundation

```text
BE-001 runtime state model
BE-002 canonical event emitter/schema validation
BE-003 command validation/rejection
EVENT-001 backend event envelope
EVENT-002 frontend command envelope
EVENT-003 rejection/error payload
BE-004 active plan store
BE-005 confirmation gate
BE-006 execution contract validator
```

Purpose:

```text
Lock backend-owned truth and typed contracts before LLM/frontend expansion.
```

### Phase 3: LLM Runtime Controller

```text
LLM-001 Runtime Controller/purpose registry
LLM-002 skill/context policy
LLM-003 tool exposure by phase
LLM-004 schema validation/retry
LLM-005 intent/clarification routing
LLM-006 journey planner contract
LLM-007 correction diff contract
```

Purpose:

```text
Make LLM useful but unable to own truth.
```

### Phase 4: DOM/Locator baseline

```text
DOM-001 page snapshot
DOM-002 element candidate model
DOM-003 semantic locator ranking
DOM-004 locator validation/ambiguity
DOM-005 ancestor candidates
DOM-006 assertion target classification
DOM-010 fixture requirements
```

Purpose:

```text
Make browser target selection testable and deterministic-first.
```

### Phase 5: Shadow DOM frontend baseline

```text
FE-001 Shadow DOM host
FE-002 typed event store
FE-003 command dispatcher
FE-009 hooks/accessibility
FE-010 legacy migration audit
FE-004 plan review
FE-005 clarification/recovery
FE-006 recorded/code panel
FE-008 picker UI
```

Purpose:

```text
Frontend renders backend truth and sends typed commands.
```

### Phase 6: MVP flow implementation

```text
MVP-001 lifecycle smoke
MVP-002 simple click
MVP-003 visible assertion
MVP-004 exact text/code assertion
MVP-005 correction before confirmation
MVP-006 clarification before planning
MVP-007 locator ambiguity/recovery
MVP-008 multi-step strict cursor
MVP-010 acceptance gate
```

Purpose:

```text
Prove Complete LLM Mode works end to end.
```

### Phase 7: Recording / Codegen / Replay smoke

```text
REC-001 recorded model
REC-002 evidence-to-recording builder
REC-003 assertion recording
REC-004 deterministic codegen
REC-005 code_update
REC-006 ordering/dedup
REC-007 expected/observed outcome
REC-008 archive baseline
BE-012 replay smoke
E2E-010 recording/code/replay smoke
```

Purpose:

```text
Make output trustworthy and replay smoke possible.
```

### Phase 8: Trace and observability

```text
TRACE-002 lifecycle trace
TRACE-003 command/rejection trace
TRACE-004 LLM telemetry trace
TRACE-005 DOM locator trace
TRACE-006 recording/codegen trace
TRACE-007 replay/gap trace
TRACE-008 frontend trace panel
TRACE-010 redaction policy
```

Purpose:

```text
Make failures diagnosable without creating trace-owned truth.
```

### Phase 9: Governance / P1-P2 backlog only

```text
GOV-001 to GOV-010
```

Purpose:

```text
Classify future capabilities after MVP evidence.
```

---

## 10. Four-developer branch split

### DEV-1 Backend Runtime + Recording

Owns:

```text
BE stories
EVENT emitter/validation
REC stories
backend trace emission
replay smoke baseline
completion guard
```

First repo-inspection tasks:

```text
BE-001
BE-002
BE-003
BE-004
BE-005
BE-006
REC-001
REC-002
```

### DEV-2 LLM Runtime + DOM/Locator

Owns:

```text
LLM stories
DOM snapshot/candidate/ranking policy
locator specialist advisory boundary
LLM telemetry semantics
skill/context/tool policy
```

First repo-inspection tasks:

```text
LLM-001
LLM-002
LLM-003
LLM-004
DOM-001
DOM-002
DOM-003
DOM-004
```

### DEV-3 Shadow DOM Frontend

Owns:

```text
FE stories
Shadow DOM host
event store
command dispatcher
plan/recovery/recorded/code/picker/trace UI
legacy overlay migration audit
```

First repo-inspection tasks:

```text
FE-001
FE-002
FE-003
FE-009
FE-010
```

### DEV-4 E2E Harness + Fixtures + Evidence

Owns:

```text
E2E stories
fixture server/registry
event capture utilities
Shadow DOM harness
artifact export
MVP gate evidence
redaction regression
```

First repo-inspection tasks:

```text
E2E-001
E2E-002
E2E-003
E2E-004
TRACE-001
TRACE-009
TRACE-010
```

---

## 11. First Codex tasks

Use Codex for repo inspection first, not implementation.

### Task A: repo architecture map

```text
MODE:
Repo inspection only.
Do not edit code.

TASK:
Map current repo files/modules to Tasks.md epics:
BE/EVENT/LLM/DOM/FE/E2E/MVP/REC/TRACE/GOV.

OUTPUT:
1. Current architecture map
2. Current source-of-truth owners
3. Legacy overlay paths
4. Backend runtime/event paths
5. LLM call sites
6. DOM/locator paths
7. Test harness/fixture paths
8. Recording/codegen/replay paths
9. Trace/logging paths
10. Gaps vs Tasks.md
11. Recommended first implementation slice
12. Stop conditions encountered
```

### Task B: test harness inspection

```text
MODE:
Repo inspection only.
Do not edit code.

TASK:
Inspect current test runner, Playwright config, backend startup, frontend startup, fixture support, event capture, artifacts, and CI/local scripts.

OUTPUT:
1. Existing test commands
2. Existing E2E structure
3. Missing harness pieces
4. Fixture strategy recommendation
5. Artifact/export recommendation
6. Minimal first test to add
```

### Task C: backend runtime/event inspection

```text
MODE:
Repo inspection only.
Do not edit code.

TASK:
Inspect current backend runtime state, event emitter, command validation, plan store, confirmation gate, execution contract, recording, completion, replay.

OUTPUT:
1. Current files/functions
2. Current ownership problems
3. Where LLM/frontend currently owns truth, if any
4. Tests found
5. First safe backend slice
```

---

## 12. Stop conditions for next agent

Stop and ask/report if:

```text
source files are missing
patches are not applied
repo structure does not match expected assumptions
current code contradicts backend-owned truth
frontend is still the only runtime truth source
LLM emits lifecycle/recording/completion truth
event/command contracts are absent
tests cannot run locally
fixture strategy is missing
exact text assertion semantics are unclear
multi-step strict cursor cannot be observed
recording/code_update path is frontend/LLM-owned
trace contains sensitive data without redaction
```

---

## 13. MVP gate

MVP cannot pass unless all are proven:

```text
MVP-001 lifecycle smoke
MVP-002 simple click
MVP-003 visible assertion
MVP-004 exact text/code assertion
MVP-005 correction before confirmation
MVP-006 clarification before planning
MVP-007 locator ambiguity/recovery
MVP-008 multi-step strict cursor
MVP-010 acceptance gate
```

Replay smoke and save/load:

```text
Replay smoke required if repo supports accepted path; otherwise typed gap allowed if non-MVP blocker.
Save/load/session restore is conditional and not a blocker unless source/repo inspection promotes it.
```

---

## 14. P1/P2 governed backlog

Default P1/P2 unless explicitly promoted:

```text
robust replay repair
full replay-all stability
session restore after browser refresh
advanced observed outcome detection
advanced picker UX/highlight/ranking feedback
popup/iframe/upload/download/permission advanced capabilities
multi-model specialist orchestration
frontend polish/recovery UX improvements
broad module refactor
```

Promotion requires:

```text
source/gap evidence
MVP blocker proof
backend-owned truth preserved
deterministic local test plan
planning-brain approval
```

---

## 15. Known non-blockers unless promoted

```text
full replay repair
advanced modal/dropdown reconstruction
session restore after refresh
advanced observed outcome detection
advanced picker ancestor UX
multi-model specialist orchestration
UI polish beyond MVP usability
module extraction/refactor before MVP evidence
```

---

## 16. Open risks for repo inspection

```text
current agent.py may hold too much lifecycle logic
legacy overlay may still own too much UI state
Shadow DOM host may not be fully built
current tests may not cover product-level flows
current LLM calls may bypass Runtime Controller
current DOM/picker may still pick weak nested targets
recording/codegen may still be coupled to successful action history
replay smoke may be incomplete
save/load path may be partial
trace/redaction may not exist yet
```

---

## 17. Final instruction to next thinking agent

Do not start coding from intuition.

Start with repo inspection and evidence:

```text
Read source hierarchy.
Verify patches are applied.
Inspect repo current state.
Map repo to tasks.
Choose smallest safe implementation slice.
Write tests first.
Implement narrowly.
Run focused tests.
Capture artifacts.
Only then move next story.
```

When unsure:

```text
Stop.
Report evidence.
Ask for planning decision.
Do not guess.
```

---

## 18. Final status

```text
Planning phase: complete
Tasks.md backlog: complete
Patches: complete through PATCH-009
Next step: repo inspection
Implementation: blocked until repo inspection reports are reviewed
```
