# PATCH-009 Batch 11 Advanced Capabilities and Governance Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0 Planning / Governance  
**Applies To:** EPIC-010 and GOV-001 through GOV-010  
**Reason:** Codex Batch 11 review found governance structurally strong and ready for classification/repo inspection, but identified cleanup required before final handoff: GOV-010 self-reference, missing global P0/P1/P2/not-planned rubric, broad roadmap boundaries, gap lifecycle rules, and final handoff output schema.  
**Decision:** Patch Batch 11. Do not regenerate. Do not start final implementation sequencing until this patch is applied.

---

## 1. Codex review result

Codex reviewed EPIC-010 and GOV-001 through GOV-010 using only Tasks.md planning files.

Result:

```text
Confidence: High
All GOV-001 through GOV-010 are ready for repo inspection or backlog classification.
No GOV story is ready for immediate implementation.
Final decision: Patch Batch 11.
```

Reason:

```text
The governance batch is clearly separated from MVP implementation and strong enough to prevent P1/P2 scope creep,
but it needs a few final cleanup patches before handoff.
```

---

## 2. Patch goal

Patch objectives:

1. Fix the self-referential dependency in GOV-010.
2. Add a single global P0/P1/P2/not-planned classification rubric to EPIC-010 and GOV-001.
3. Add gap lifecycle rules: open, duplicate, merged, deferred, accepted, closed, not planned.
4. Clarify advanced browser capability escalation from P1 to P2/research.
5. Clarify replay repair phase acceptance criteria.
6. Clarify session persistence/restore target separation.
7. Clarify advanced observed outcome data model and advisory-only boundary.
8. Clarify picker enhancement feedback/ranking boundary.
9. Clarify multi-model controller/specialist/failure boundaries.
10. Clarify frontend UX action-to-command mapping and accessibility expectations.
11. Clarify refactor extraction sequence.
12. Add explicit final handoff output schema and patch list requirements.
13. Tighten four-developer coordination expectations.

---

## 3. EPIC-010 global classification rubric

Apply this to EPIC-010 and GOV-001.

### Global classification rule

Every advanced capability, gap, roadmap item, refactor, or UX enhancement must be classified using this rubric before implementation.

| Classification | Meaning | Allowed before MVP gate? | Implementation allowed? |
|---|---|---:|---:|
| P0 | Required to prove MVP acceptance or protect non-negotiable architecture truth | Yes | Yes, only with source evidence and tests |
| P1 | Important after MVP; improves reliability/usability/coverage but not required to prove MVP | No, unless explicitly promoted | After MVP gate and repo inspection |
| P2 | Future enhancement, polish, broader coverage, or lower-frequency capability | No | After P1 priorities or explicit approval |
| Research | Unknown feasibility/cost/risk; needs spike before story | No | No implementation until research accepted |
| Not planned | Out of scope, unsafe, too costly, or unsupported by product goal | No | No |

### P0 promotion rule

A P1/P2 item may be promoted to P0 only when all are true:

```text
1. There is source evidence or trace/capability-gap evidence.
2. The item blocks an MVP acceptance story.
3. The item protects backend-owned truth, typed event contracts, or deterministic safety.
4. The implementation can be tested locally/deterministically.
5. The planning brain explicitly approves promotion.
```

### P1/P2 default rule

If an item is useful but not required for MVP acceptance, default to P1/P2.

```text
Do not promote because it is “nice to have,” because a model suggested it, or because it exists in a future roadmap.
```

### Not-planned rule

Classify as not planned when:

```text
- it conflicts with backend-owned truth
- it requires unsafe/private data handling
- it cannot be tested deterministically
- it is unrelated to the product goal
- it creates large scope without clear user value
- it belongs to a different product/system
```

---

## 4. GOV-001 gap lifecycle patch

Apply this to GOV-001.

### Gap lifecycle states

| State | Meaning |
|---|---|
| open | new gap captured and awaiting classification |
| duplicate | same as another gap; linked to canonical gap |
| merged | combined into broader accepted gap |
| accepted | approved for future P1/P2 implementation planning |
| deferred | valid but not scheduled |
| blocked | cannot proceed until dependency/evidence exists |
| not_planned | explicitly out of scope |
| closed | resolved, invalid, or superseded |

### Required lifecycle fields

| Field | Required | Meaning |
|---|---|---|
| gap_id | Yes | unique gap id |
| canonical_gap_id | Conditional | used for duplicate/merged |
| lifecycle_state | Yes | open/duplicate/merged/accepted/deferred/blocked/not_planned/closed |
| classification | Yes | P0/P1/P2/Research/Not planned |
| decision_reason | Yes | why this state/classification |
| source_evidence_refs | Yes | trace, artifact, source, or test evidence |
| owner_stream | Yes | DEV-1/DEV-2/DEV-3/DEV-4 |
| next_review_condition | Optional | what would reopen/promote it |

### Tests to add

```markdown
| GOV001-C-004 | Contract | duplicate gap | linked canonical_gap_id |
| GOV001-C-005 | Contract | close gap | decision_reason required |
| GOV001-C-006 | Contract | not_planned gap | reason and evidence required |
| GOV001-A-002 | Audit | P1/P2 promoted to P0 | promotion rule satisfied |
```

---

## 5. GOV-002 advanced browser capability policy patch

Apply this to GOV-002.

### P1 vs P2/research escalation rules

| Condition | Classification |
|---|---|
| Needed for common user-visible automation and locally testable | P1 |
| Needed only for less common/specialized flows | P2 |
| Cross-origin, security-sensitive, or browser-permission constrained | P2 or Research |
| Requires external/live site dependency | Research unless local fixture possible |
| Requires unsafe/private data handling | Not planned or blocked pending safety review |
| Blocks MVP acceptance | Candidate P0 only if promotion rule passes |

### Security-sensitive examples

| Capability | Default treatment |
|---|---|
| cross-origin iframe control | P2/Research |
| browser permission prompt handling | P1/P2 with safety constraints |
| file upload/download | P1/P2 with local fixture only |
| clipboard/camera/mic permissions | P2/Research unless explicit product need |
| authentication/OTP flows | P2/Research with strict redaction |
| payment/financial flows | Not planned unless explicitly approved |

### Tests/evidence to add

```markdown
| GOV002-A-003 | Audit | cross-origin iframe request | P2/Research |
| GOV002-A-004 | Audit | local file upload fixture exists | P1 candidate |
| GOV002-A-005 | Audit | security-sensitive permission | safety review required |
```

---

## 6. GOV-003 replay repair phase acceptance patch

Apply this to GOV-003.

### Replay roadmap phase acceptance

| Phase | Acceptance criteria |
|---|---|
| P0 replay smoke | replay starts, validates precondition, emits replay_result, fails safely on wrong page |
| P1 locator refresh | replay can request/update locator through backend-validated update_locator path |
| P1 wrong-page guided recovery | wrong-page precondition creates recovery guidance without simulating frontend state |
| P2 modal/dropdown reconstruction | dynamic state fixtures prove state restoration or clear typed failure |
| P2 replay-all stability | ordered recorded steps replay with stop_on_error and artifact evidence |
| Research self-healing | suggestions only until backend validator accepts deterministic repair path |

### Graduation rule

A replay issue graduates from evidence-only to repairable only when:

```text
- replay failure is reproducible with artifact evidence
- recorded archive contains required source data
- backend can validate the proposed repair
- E2E fixture exists
- frontend/LLM does not own repair truth
```

### Tests/evidence to add

```markdown
| GOV003-A-003 | Audit | replay failure lacks archive | remains blocked |
| GOV003-A-004 | Audit | repair suggestion without backend validator | not implementation-ready |
| GOV003-A-005 | Audit | replay-all requested before smoke stable | deferred |
```

---

## 7. GOV-004 session persistence target separation patch

Apply this to GOV-004.

### Persistence vs restore target matrix

| Target | Meaning | Default priority |
|---|---|---|
| run metadata | run/session identifiers, timestamps, status | P1 |
| active plan | plan_id/version/steps before confirmation | P1 |
| recorded steps | recorded parent/children | P1 |
| code updates | generated code_update payloads | P1 |
| trace/artifacts | exported evidence bundle refs | P1 |
| browser URL/title | basic page location | P1/P2 |
| browser DOM/state | page-specific UI state | P2 |
| modal/dropdown state | dynamic UI state | P2 |
| auth/session cookies | security-sensitive browser state | P2/Research |
| cross-workspace portability | sharing sessions between workspaces | P2/Research |

### Restore rule

```text
Restored state must come from backend/session storage.
Frontend must not reconstruct runtime truth from local UI cache.
Browser/page-state restore is separate from backend run-state restore.
```

### Tests/evidence to add

```markdown
| GOV004-A-003 | Audit | save recorded steps only | P1 target |
| GOV004-A-004 | Audit | restore browser modal state | P2 target |
| GOV004-C-002 | Contract | frontend reconstructs runtime truth | rejected |
```

---

## 8. GOV-005 advanced observed outcome data model patch

Apply this to GOV-005.

### Advanced observed outcome record

| Field | Required | Meaning |
|---|---|---|
| observed_outcome_id | Yes | identity |
| run_id/step_id/operation_id | Yes where scoped | correlation |
| detection_type | Yes | url_change/content_change/modal/dropdown/toast/download/network/etc. |
| confidence | Yes | high/medium/low |
| evidence_ref | Yes | trace/DOM/screenshot/network evidence |
| matched_expected | Optional | nullable summary |
| advisory_only | Yes | must be true unless future approved validator path exists |
| used_for_completion | Yes | must be false for roadmap stage |
| diagnostics | Optional | warnings/errors |

### Advisory-only rule

```text
Advanced observed outcome may support explanation, recovery, trace, or user display.
It must not mark step/run complete by itself.
It must not become assertion expected_value.
It must not bypass backend completion guard.
```

### Tests/evidence to add

```markdown
| GOV005-C-002 | Contract | observed outcome used for completion | rejected |
| GOV005-C-003 | Contract | observed outcome used as assertion value | rejected |
| GOV005-A-002 | Audit | toast detection requested | P1 candidate with fixture |
```

---

## 9. GOV-006 picker feedback and ranking boundary patch

Apply this to GOV-006.

### Picker feedback loop

Allowed:

```text
user selects preferred candidate
backend validates selected candidate
trace records selection and validation result
future ranking may use aggregated evidence after explicit approval
```

Forbidden:

```text
UI-selected candidate becomes final truth without backend validation
LLM updates ranking policy silently
ranking learns from private/sensitive page content without redaction policy
candidate feedback mutates current execution contract
```

### Enhancement contract

| Feature | Boundary |
|---|---|
| visual hover highlight | UI-only preview |
| confidence badge | advisory display |
| candidate compare | display evidence only |
| locator preview | preview only until backend validates |
| user preference | future ranking input, not immediate truth |
| candidate feedback | trace evidence, not runtime state |

### Tests/evidence to add

```markdown
| GOV006-C-002 | Contract | UI preference used as final locator | rejected |
| GOV006-C-003 | Contract | ranking feedback lacks redaction | blocked |
| GOV006-A-002 | Audit | repeated weak-DOM ambiguity | P1 enhancement candidate |
```

---

## 10. GOV-007 multi-model orchestration boundary patch

Apply this to GOV-007.

### Controller boundary

All specialists must run behind LLM Runtime Controller.

| Specialist | Required controller fields |
|---|---|
| locator specialist | purpose, schema, allowed context, validator |
| debug agent | purpose, schema, no mutation side effects |
| codegen reviewer | advisory diagnostics only |
| judge/risk agent | risk output only |
| trace summarizer | summary output only |

### Specialist selection rule

Specialist can be called only when:

```text
- deterministic/backend path needs advisory help
- purpose is registered
- schema is defined
- allowed context is minimal and safe
- output has backend or policy validator
- telemetry is captured
```

### Failure handling

| Failure | Required behavior |
|---|---|
| specialist unavailable | continue deterministic path or ask user |
| specialist schema invalid | retry once then fail closed |
| specialists disagree | backend/policy decides; no automatic truth |
| high token/cost | stop or require purpose review |
| hallucinated selector/code | reject through backend validator |

### Tests/evidence to add

```markdown
| GOV007-C-002 | Contract | specialist outside controller | rejected |
| GOV007-C-003 | Contract | specialist output mutates state | rejected |
| GOV007-A-002 | Audit | specialist high-cost repeated call | purpose review |
```

---

## 11. GOV-008 UX action-to-command patch

Apply this to GOV-008.

### UX action mapping

| UX action | Backend command / route |
|---|---|
| retry correction again | correction command |
| use original plan | select plan version / cancel correction route if supported |
| edit pending step | structured correction or future edit_step command |
| cancel correction | cancel/reject correction route if supported |
| retry failed operation | recovery option_selected |
| skip step | skip_step command with reason |
| stop run | stop_run command |
| update locator | update_locator command |
| choose picker candidate | update_locator or option_selected depending context |
| export trace | trace export action, no runtime mutation |

### Accessibility expectation

Every UX action must have:

```text
stable hook
role/name
keyboard-accessible behavior where applicable
typed command mapping
rejection rendering
no optimistic truth mutation
```

### Tests/evidence to add

```markdown
| GOV008-C-002 | Contract | UX action lacks command mapping | blocked |
| GOV008-C-003 | Contract | action has no accessible name | blocked |
| GOV008-E-002 | E2E | rejected recovery action | UI shows rejection, state unchanged |
```

---

## 12. GOV-009 refactor extraction sequence patch

Apply this to GOV-009.

### Refactor sequencing

Recommended extraction order after MVP gate:

```text
1. runtime/plan_correction.py
2. runtime/execution_contract.py
3. runtime/recording.py
4. runtime/outcomes.py
5. runtime/replay.py
6. runtime/picker_contract.py
7. runtime/llm_runtime_controller.py if not already separated
8. agent.py reduced to orchestration
```

### Refactor gate per module

Each extraction must have:

```text
before tests passing
target module boundary
no behavior change statement
files allowed/forbidden
rollback plan
after tests passing
manual smoke if applicable
```

### Tests/evidence to add

```markdown
| GOV009-A-002 | Audit | extraction before MVP gate | blocked |
| GOV009-A-003 | Audit | extraction lacks before/after tests | blocked |
| GOV009-C-002 | Contract | behavior change hidden inside refactor | rejected |
```

---

## 13. GOV-010 self-reference fix and final handoff schema

Apply this to GOV-010.

### Dependency map correction

Replace any self-referential dependency:

```text
EPIC-001 through EPIC-010
```

with:

```text
EPIC-001 through EPIC-009 plus EPIC-010 planning status
```

Reason:

```text
GOV-010 summarizes EPIC-010 but must not depend on itself as an upstream prerequisite.
```

### Final handoff output schema

Final handoff must include:

| Section | Required content |
|---|---|
| Executive status | planning-ready/not-ready by batch |
| Source hierarchy | exact order of authority |
| Batch inventory | Batch 01 through Batch 11 file list |
| Patch inventory | PATCH-001 through PATCH-009 status/applied/not applied |
| Epic dependency graph | EPIC-001 through EPIC-010 |
| Story inventory | all BE/EVENT/LLM/DOM/FE/E2E/MVP/REC/TRACE/GOV stories |
| Planning readiness table | repo-inspection-ready / not implementation-ready |
| Implementation sequencing | recommended order by dependency |
| Four-developer split | DEV-1/2/3/4 ownership lanes |
| First Codex tasks | repo-inspection tasks only |
| Stop conditions | architecture and process stop rules |
| MVP gate | required flows and artifacts |
| P1/P2 backlog | governed future work |
| Known non-blockers | replay repair/session restore/etc. |
| Open risks | unresolved policy or repo-inspection items |
| Handoff instructions | how next thinking agent should proceed |

### Patch inventory rule

Patch list must show:

```text
patch id
batch affected
file name
status applied/not applied
reason
blocking before implementation yes/no
```

### Implementation readiness rule

Final handoff must state:

```text
Planning-ready does not mean implementation-ready.
Every story still requires repo inspection before implementation.
```

### Tests/evidence to add

```markdown
| GOV010-A-003 | Audit | no self-reference | dependency map corrected |
| GOV010-A-004 | Audit | patch inventory complete | PATCH-001..PATCH-009 listed |
| GOV010-A-005 | Audit | implementation sequencing present | dependency-ordered |
| GOV010-G-002 | Gate | planning-ready confused with implementation-ready | fail handoff |
```

---

## 14. Four-developer coordination tightening

Apply to all GOV stories.

### Required per-story coordination rule

Each GOV story must explicitly answer:

```text
What can each developer classify?
What evidence must each developer provide?
What must each developer not own?
What decision requires planning-brain approval?
```

### Standard coordination matrix

| Developer | Can classify | Must provide | Must not own |
|---|---|---|---|
| DEV-1 Backend | runtime/event/replay/persistence/refactor impacts | backend evidence, event traces, tests | frontend/LLM truth |
| DEV-2 LLM/DOM | LLM/DOM/locator/multi-model impacts | schema/context/tool evidence, DOM traces | runtime finality |
| DEV-3 Frontend | UX/picker/recovery/action impacts | UI hooks, command mapping, accessibility evidence | backend runtime truth |
| DEV-4 E2E | testability/fixture/artifact impacts | regression plan, fixture evidence, artifacts | product behavior truth |

Planning-brain approval required for:

```text
P0 promotion
scope expansion
MVP blocker classification
refactor before MVP gate
new advanced capability implementation
```

---

## 15. Batch 11 patch acceptance criteria

Batch 11 is accepted after:

- EPIC-010 includes global P0/P1/P2/Research/Not planned rubric.
- GOV-001 includes lifecycle states and dedupe/merge/close/not-planned rules.
- GOV-002 includes P1 vs P2/research escalation and security-sensitive examples.
- GOV-003 includes replay repair phase acceptance and graduation criteria.
- GOV-004 separates persistence targets from restore targets.
- GOV-005 defines advanced observed outcome advisory-only data model.
- GOV-006 defines picker feedback/ranking boundary.
- GOV-007 defines Runtime Controller/specialist/failure boundaries.
- GOV-008 maps UX actions to backend commands and accessibility expectations.
- GOV-009 defines behavior-preserving refactor extraction sequence.
- GOV-010 removes self-reference and defines final handoff schema.
- Four-developer coordination is tightened for all GOV stories.

After this patch:

```text
EPIC-010 = planning-ready.
GOV-001 through GOV-010 = ready for repo inspection or backlog classification.
GOV-001 through GOV-010 = not ready for immediate implementation.
Final planning handoff can be generated next.
```
