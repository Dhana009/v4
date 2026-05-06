# PATCH-003 Batch 04 LLM Runtime Controller Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** EPIC-003 and LLM-001 through LLM-010  
**Reason:** Codex Batch 04 review found the LLM Runtime Controller planning clear enough for repo inspection, but recommended tighter contracts around side effects, skill precedence, tool matrix, retry behavior, locator confidence/escalation, telemetry, and four-developer coordination.  
**Decision:** Patch Batch 04. Do not regenerate. Do not start implementation from Batch 04 until this patch is applied.  

---

## 1. Codex review result

Codex reviewed EPIC-003 and LLM-001 through LLM-010 using only Tasks.md planning files.

Result:

```text
Confidence: Medium
All LLM-001 through LLM-010 are ready for repo inspection.
No LLM story is ready for immediate implementation.
Final decision: Patch Batch 04.
```

Reason:

```text
The LLM Runtime Controller scope is coherent,
but contract precision and coordination specificity need tightening before freezing.
```

---

## 2. Patch goal

Patch objectives:

1. Make allowed side effects explicit for every LLM purpose.
2. Define required vs optional skill loading precedence.
3. Tighten phase-to-tool exposure rules and deny reasons.
4. Define schema retry-stop behavior precisely.
5. Clarify intent vs clarification vs recovery boundaries.
6. Strengthen journey planner and correction anti-overwrite rules.
7. Make locator confidence/escalation contract reusable by EPIC-004.
8. Make recovery diagnoser advisory-only.
9. Define telemetry units and budget guard actions.
10. Add story-specific four-developer coordination notes.

---

## 3. LLM-001 purpose registry side-effect policy

Apply this to LLM-001.

### Purpose registry must include allowed side effects

Each purpose must declare:

| Field | Required | Meaning |
|---|---|---|
| purpose_id | Yes | stable purpose name |
| owner | Yes | subsystem owner |
| allowed_inputs | Yes | context/data it may receive |
| output_schema_id | Yes | schema to validate |
| allowed_tools | Yes | tool allowlist or empty |
| allowed_side_effects | Yes | usually `none` |
| backend_validator | Conditional | required for runtime-impacting output |
| retry_policy | Yes | validation retry behavior |
| telemetry_required | Yes | all calls yes |

### Allowed side-effect baseline

| Purpose | Allowed side effects | Forbidden side effects |
|---|---|---|
| intent_classifier | none | create active plan, execute, record, complete |
| clarification_generator | none; backend may emit clarification event after validation | set RunState.clarification directly |
| journey_planner | none; backend may store active plan after validation | create PlanState directly, confirm, execute |
| step_plan_normalizer | none | mutate plan/store directly |
| plan_diff_editor | none; backend may apply diff after validation | overwrite active plan directly |
| locator_specialist | none; backend/browser validates candidates | execute action, select final locator truth |
| recovery_diagnoser | none; backend may open/update recovery after validation | mark recovery resolved, skip, stop, complete |
| user_response_writer | none | mutate runtime state |
| trace_summarizer | none | mutate trace/runtime truth |

### Explicit anti-truth rule

Add this exact rule:

```text
LLM output may never directly set RunState, PlanState, StepState, OperationState, RecordingState, ReplayState, run_completed, step_recorded, or capability_gap_recorded.
All runtime-impacting LLM output must become a proposal that backend validates through the correct BE/EVENT contract.
```

### Tests to add

```markdown
| LLM001-U-004 | Unit | purpose attempts forbidden side effect | output includes run_completed | rejected |
| LLM001-U-005 | Unit | purpose missing backend_validator for runtime-impacting output | registry entry invalid | rejected |
| LLM001-U-006 | Unit | stale/unknown purpose_id | unknown purpose | rejected |
```

---

## 4. LLM-002 skill loading precedence

Apply this to LLM-002.

### Skill precedence order

When skill instructions conflict, apply this order:

| Rank | Source | Rule |
|---:|---|---|
| 1 | PRD/spec/handoff architecture | wins over skills |
| 2 | `.autoworkbench/skills/00_skill_usage_policy.md` | controls skill loading |
| 3 | `.autoworkbench/skills/00_architecture_contract.md` | mandatory architecture guard |
| 4 | task-specific skill files | only for relevant work |
| 5 | current implementation patterns | lowest priority if conflicting |

### Required skill loading groups

| Purpose/work type | Required skills |
|---|---|
| all Codex tasks | `00_skill_usage_policy.md`, `00_architecture_contract.md`, `01_prd_scope_validation.md` |
| backend runtime/event/command | backend step runner + typed event contract + TDD/refactor safety |
| LLM runtime | skill usage policy + architecture contract + LLM runtime policy + TDD/refactor safety |
| DOM/locator | locator strategy + frontend/shadow contract where relevant |
| frontend | frontend/shadow UI + typed event contract |
| E2E/harness | TDD/regression harness + typed event contract |
| refactor | refactor safety + tests-first |

### Minimal pack rule

```text
Load the smallest skill pack that protects the task.
Do not load all skills blindly.
If a required skill is missing, stop and report the missing file.
```

### Tests to add

```markdown
| LLM002-U-005 | Unit | required core skill missing | missing skill file | stop condition |
| LLM002-U-006 | Unit | conflicting skill vs architecture contract | conflict | architecture contract wins |
| LLM002-U-007 | Unit | over-loaded context | all skills selected | rejected unless explicitly approved |
```

---

## 5. LLM-003 phase-to-tool matrix and deny reasons

Apply this to LLM-003.

### Phase-to-tool exposure matrix

| Runtime phase | Allowed LLM outputs/tools | Deny reason for browser/action tools |
|---|---|---|
| idle | intent classification only | no active run/plan |
| planning | intent, clarification, journey plan proposal | plan not confirmed |
| clarification | clarification interpretation | waiting for user input |
| plan_review | explanation, correction diff proposal | confirmation required |
| executing | only backend-requested next-operation proposal if any | backend execution contract owns tool dispatch |
| recovery | diagnosis/recovery option proposal | recovery unresolved; backend decides |
| replay | replay explanation only unless backend exposes replay-specific helper | replay contract owns execution |
| completed | summary/trace explanation | terminal run |
| stopped/failed | summary or next-step suggestion | terminal or blocked state |

### Deny response shape

Tool exposure denial must include:

```json
{
  "allowed": false,
  "deny_code": "CONFIRMATION_REQUIRED",
  "phase": "plan_review",
  "purpose": "journey_planner",
  "requested_tool": "action_click",
  "message": "Browser-changing tools are not exposed before backend confirmation."
}
```

### Tests to add

```markdown
| LLM003-U-004 | Unit | hidden tool access attempt | requested tool not exposed | deny payload |
| LLM003-U-005 | Unit | phase changes during call | stale phase | deny or revalidate |
| LLM003-U-006 | Unit | replay phase browser action | live action tool | denied unless replay contract tool |
```

---

## 6. LLM-004 retry-stop behavior

Apply this to LLM-004.

### Retry policy

| Attempt | Behavior |
|---|---|
| initial invalid schema | capture validation errors and retry once with schema-only repair instruction |
| retry valid | continue to backend validator |
| retry invalid | fail closed; do not apply partial output |
| retry changes user intent materially | fail closed and ask user/raise recovery |
| parser cannot extract structured payload | count as invalid schema |
| backend validator rejects valid schema | do not retry as schema issue; return typed rejection/clarification |

### Failure output shape

```json
{
  "type": "llm_output_rejected",
  "purpose": "plan_diff_editor",
  "schema_id": "plan_correction_diff.v1",
  "retry_count": 1,
  "validation_errors": ["operations[0].reason is required"],
  "backend_applied": false,
  "required_next_action": "ask_user_or_retry_later"
}
```

### Tests to add

```markdown
| LLM004-U-005 | Unit | parse failure | prose around malformed JSON | retry once |
| LLM004-U-006 | Unit | retry changes intent | second output different target | fail closed |
| LLM004-U-007 | Unit | schema valid but backend rejects | stale plan version | no schema retry |
```

---

## 7. LLM-005 clarification threshold patch

Apply this to LLM-005.

### Planner readiness rule

`planner_ready` can be true only when:

| Requirement | Meaning |
|---|---|
| target is clear | page/element/test scope is identifiable |
| action/assertion intent is clear | click/fill/assert/navigation/etc. |
| required data exists | input values/expected text/test data present |
| risk flags are not blocking | permissions/destructive actions handled |
| confidence is high or approved medium | medium requires explicit policy/user confirmation |
| no unresolved clarification exists | backend state permits planning |

### Clarification routing

| Situation | Required output |
|---|---|
| ambiguous target | clarification question with options if possible |
| missing data | ask specific missing field |
| low confidence | ask user rather than guess |
| multiple possible workflows | present options |
| unsafe/risky action | ask permission/confirmation |
| correction intent detected | route to correction flow, not journey planner |

### Tests to add

```markdown
| LLM005-U-005 | Unit | medium confidence without policy | planner_ready false |
| LLM005-U-006 | Unit | correction disguised as new plan | route correction |
| LLM005-U-007 | Unit | risky action | clarification/permission needed |
```

---

## 8. LLM-006 planner anti-overwrite patch

Apply this to LLM-006.

### Planner output must not overwrite active plan

Rules:

```text
journey_planner is for new plan proposals only.
If an active plan exists and user is changing it, route to LLM-007 plan_diff_editor.
Journey planner output cannot replace an active plan directly.
Backend may reject planner output if active plan/correction context exists.
```

### Tests to add

```markdown
| LLM006-C-004 | Contract | planner output while active plan exists | correction intent | rejected/routed to LLM-007 |
| LLM006-C-005 | Contract | plan output contains confirmed/executing status | invalid | rejected |
| LLM006-C-006 | Contract | plan output missing child operation order | invalid | rejected |
```

---

## 9. LLM-007 correction identity patch

Apply this to LLM-007.

### Identity preservation rules

| Diff action | Identity rule |
|---|---|
| update_step | preserve step_id |
| update_operation | preserve operation_id unless explicit semantic replacement |
| reorder_step | preserve all ids; change order only |
| reorder_operation | preserve all ids; change order only |
| remove_step/remove_operation | require explicit reason |
| add_step/add_operation | backend assigns or validates new id |
| replace operation | old id removed with reason; new operation created |

### Atomicity rule

```text
Backend should reject entire diff if any required diff operation is invalid, unless a future story explicitly introduces partial-apply semantics.
```

### Tests to add

```markdown
| LLM007-C-005 | Contract | update changes id unexpectedly | rejected |
| LLM007-C-006 | Contract | partial invalid diff | whole diff rejected |
| LLM007-C-007 | Contract | reorder loses operation | rejected |
```

---

## 10. LLM-008 locator confidence and escalation thresholds

Apply this to LLM-008. This is important before EPIC-004 DOM/Locator stories.

### Locator confidence levels

| Confidence | Meaning | Required next action |
|---|---|---|
| high | one candidate, strong semantic evidence, live validation likely unique | backend validates candidate |
| medium | candidate likely but duplicates/weak scoping possible | backend validates; may ask user if ambiguous |
| low | weak evidence, multiple plausible targets, hidden/dynamic element risk | ask user or deterministic DOM pass |
| blocked | insufficient DOM/page evidence | request more DOM/element context |

### Escalation rules

| Situation | Required behavior |
|---|---|
| deterministic locator unique | do not call locator specialist |
| multiple matching elements | return ambiguity and candidate list |
| candidate needs ancestor scope | ask for scoped section/container evidence |
| hidden/detached element | do not recommend as executable |
| code block assertion | prefer text/code/pre scoped candidate |
| file/upload/popup/iframe capability | route capability gap or specialized story |
| confidence low | do not execute; ask clarification or request more context |

### Candidate ranking fields

| Field | Required |
|---|---|
| candidate_id | Yes |
| strategy | Yes |
| selector_or_locator | Yes |
| scope | Optional |
| uniqueness_evidence | Yes |
| accessibility_evidence | Optional |
| risk | low/medium/high |
| confidence | high/medium/low |
| validation_needed | Yes |

### Tests to add

```markdown
| LLM008-U-003 | Unit | deterministic unique locator | no LLM escalation |
| LLM008-U-004 | Unit | duplicate CTA | needs_user_selection true |
| LLM008-U-005 | Unit | low confidence | no execution recommendation |
| LLM008-U-006 | Unit | hidden element candidate | risk high / not executable |
```

---

## 11. LLM-009 advisory-only recovery patch

Apply this to LLM-009.

### Recovery diagnoser boundary

The recovery diagnoser may output:

```text
failure summary
likely cause
suggested options
recommended option
risk/confidence
unsupported capability hint
```

It must not output:

```text
resolved=true
step_status=recorded/skipped/completed
run_status=completed
execute_this_tool_now
final locator truth
```

### Tests to add

```markdown
| LLM009-C-004 | Contract | diagnosis says resolved=true | rejected |
| LLM009-C-005 | Contract | diagnosis marks step skipped | rejected |
| LLM009-C-006 | Contract | unsupported capability hint | routes to capability gap proposal |
```

---

## 12. LLM-010 telemetry units and guard actions

Apply this to LLM-010.

### Telemetry units

| Field | Unit/type |
|---|---|
| call_id | string |
| purpose | registered purpose id |
| model | model id |
| message_count | integer |
| estimated_input_tokens | integer |
| estimated_output_tokens | integer or null |
| total_estimated_tokens | integer |
| tools_exposed_count | integer |
| skills_loaded | string[] |
| latency_ms | integer milliseconds |
| validation_status | valid/invalid/retry_failed/backend_rejected |
| retry_count | integer |
| cost_estimate_usd | decimal optional |
| error_code | string optional |

### Budget guard actions

| Situation | Action |
|---|---|
| context above soft budget | summarize/remove irrelevant context |
| context above hard budget | stop and report required reduction |
| required source/skill would be removed | stop; do not reduce correctness |
| repeated high-cost call | log warning and require purpose review |
| telemetry logging fails | continue only if runtime-safe; record local warning |
| budget pressure during safety-critical task | preserve safety context first |

### Tests to add

```markdown
| LLM010-U-005 | Unit | hard budget exceeded | stop condition |
| LLM010-U-006 | Unit | required skill would be trimmed | reject trim |
| LLM010-U-007 | Unit | telemetry logging failure | safe warning |
| LLM010-U-008 | Unit | cost estimate missing | allowed with null + warning |
```

---

## 13. Four-developer coordination block to add to every LLM story

Add this standard section to each LLM story, customizing story-specific notes.

```markdown
## Four-developer coordination

| Developer | Relationship to this story |
|---|---|
| DEV-1 Backend | Provides validators and runtime truth boundaries. Must reject invalid LLM outputs. |
| DEV-2 LLM | Primary owner. Defines purpose/schema/context/tool/skill policy for this story. |
| DEV-3 Frontend | May display LLM explanations or request user input, but must render backend truth only. |
| DEV-4 E2E | Tests LLM-mode behavior using mocked/recorded LLM outputs and backend event evidence. |

Story-specific coordination:
- DEV-1: <validator/state boundary>
- DEV-2: <LLM runtime responsibility>
- DEV-3: <UI consumer/input behavior>
- DEV-4: <E2E/mock/assertion responsibility>
```

### Story-specific notes

#### LLM-001

```text
DEV-1 must provide backend validator hooks; DEV-4 should audit direct LLM call sites.
```

#### LLM-002

```text
DEV-3/DEV-4 should not request broad context dumps; DEV-2 owns minimal skill/context policy.
```

#### LLM-003

```text
DEV-1 validates phase/tool access even if DEV-2 filter fails; DEV-4 tests forbidden tool access.
```

#### LLM-004

```text
DEV-1 distinguishes schema-valid/backend-invalid outputs; DEV-4 tests retry exhaustion.
```

#### LLM-005

```text
DEV-3 renders clarification from backend event; DEV-4 tests ambiguous input routes to clarification.
```

#### LLM-006

```text
DEV-1 stores plan only after backend validation; DEV-3 renders plan_ready, not raw planner text.
```

#### LLM-007

```text
DEV-1 applies/rejects diff; DEV-3 shows revised plan only after backend acceptance.
```

#### LLM-008

```text
DEV-1/browser validates locator candidate; DEV-4 tests duplicate/low-confidence locator paths.
```

#### LLM-009

```text
DEV-1 owns recovery state; DEV-3 renders backend recovery options; DEV-4 asserts no LLM-owned resolution.
```

#### LLM-010

```text
DEV-4 should capture telemetry evidence for LLM-mode regression; DEV-2 owns budget rules.
```

---

## 14. Batch 04 patch acceptance criteria

Batch 04 is accepted after:

- LLM-001 includes explicit allowed side effects per purpose.
- LLM-002 includes skill precedence and minimal pack rules.
- LLM-003 includes phase-to-tool matrix and deny response.
- LLM-004 includes precise retry-stop behavior.
- LLM-005 includes planner readiness/clarification thresholds.
- LLM-006 blocks planner overwrite of active plan.
- LLM-007 defines identity preservation and atomicity.
- LLM-008 defines confidence/escalation thresholds.
- LLM-009 is advisory-only with explicit forbidden outputs.
- LLM-010 defines telemetry units and budget guard actions.
- Every LLM story has story-specific four-developer coordination.

After this patch:

```text
EPIC-003 = planning-ready.
LLM-001 through LLM-010 = ready for repo inspection.
LLM-001 through LLM-010 = not ready for immediate implementation.
```
