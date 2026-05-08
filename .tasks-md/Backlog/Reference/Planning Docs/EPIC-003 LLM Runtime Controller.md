# EPIC-003 LLM Runtime Controller

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-2 LLM Runtime Controller + DOM/Page Policy  
**Primary Consumers:** DEV-1 Backend Runtime, DEV-3 Frontend, DEV-4 E2E Harness  
**Capability:** Controlled LLM calls, schemas, skills, tools, telemetry  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, BE-001, BE-002, BE-003, EVENT-001, EVENT-002, EVENT-003  
**Version:** Batch 04 v1  

---

## 1. Product contribution

This epic controls how AutoWorkbench uses LLMs.

It contributes to the final product by ensuring:

```text
LLM helps interpret, plan, clarify, repair, and explain
but never owns runtime truth, execution truth, recording truth, or completion truth.
```

Without EPIC-003:

- one broad orchestrator may load too much context
- LLM may call unsafe tools in the wrong phase
- invalid schema may mutate runtime indirectly
- prompt drift may bypass backend contracts
- token/cost optimization may reduce correctness
- multi-model agents may conflict with backend truth

---

## 2. Final product workflow supported

| Workflow stage | LLM Runtime Controller contribution |
|---|---|
| user intent | classifies intent and missing info |
| page/DOM context | controls page/locator specialist calls |
| plan proposal | emits structured journey plan only |
| correction | emits structured diff only |
| confirmation/execution | cannot bypass backend gate |
| failure/recovery | diagnoses and suggests, backend decides |
| trace/explanation | summarizes evidence without changing truth |

---

## 3. Source evidence table

| Source | Extracted rule | Planning interpretation | EPIC-003 impact |
|---|---|---|---|
| SOURCE-001 | LLM thinks/proposes only. | LLM output is proposal, not runtime mutation. | Runtime Controller enforces purpose/schema/tool boundaries. |
| LLM Runtime Policy Spec | Every LLM call declares purpose, context, tools, model, schema, retry/fail policy, and validator. | LLM access must be routed through a controller. | Implement purpose registry and policy checks. |
| Skills hardening | Mandatory core skills + task-specific skills only; do not load all skills blindly. | Skills must be selected minimally. | Add skill loading policy. |
| EPIC-001 | Backend owns runtime truth. | LLM output must be validated by backend. | Backend validator boundary is mandatory. |
| EPIC-002 | Event/command contracts are typed. | LLM must not invent event/command truth. | LLM schemas align with event/command contracts. |

---

## 4. Architecture decision

Fixed decisions:

- All LLM calls go through an LLM Runtime Controller.
- Every LLM call has a registered `purpose`.
- Each purpose declares allowed context, tools, output schema, model route, retry policy, and backend validator.
- LLM cannot emit `step_recorded`, `run_completed`, or other runtime truth events.
- Invalid schema retries once, then fails closed or asks user.
- Tool exposure depends on runtime phase and purpose.
- Skills are loaded minimally.

Flexible implementation choices:

- exact class/module names
- exact schema library
- exact model names/routes
- whether specialist agents are separate classes or purpose handlers

Forbidden interpretations:

- direct ad hoc `chat.completions.create` from feature code
- all-skills context stuffing
- tool access independent of phase
- LLM output directly mutating active plan/runtime state
- reducing context so much that correctness suffers

---

## 5. Story map

| Story | Purpose | Direct consumers |
|---|---|---|
| LLM-001 | Controller and purpose registry | all LLM calls |
| LLM-002 | Skill loading and context policy | every purpose |
| LLM-003 | Tool exposure by phase | safety/tool routing |
| LLM-004 | Schema validation and retry | all structured outputs |
| LLM-005 | Intent classification and clarification routing | planning/clarification |
| LLM-006 | Journey planner output contract | BE-004/plan_ready |
| LLM-007 | Plan correction diff output contract | BE-007 |
| LLM-008 | Locator specialist boundary | DOM/locator stories |
| LLM-009 | Recovery diagnoser output contract | BE-008 |
| LLM-010 | Telemetry/token/cost guard | observability/cost control |

---

## 6. Direct vs indirect dependency note

Direct blockers:

```text
LLM-001
LLM-002
LLM-003
LLM-004
```

These establish the controller, skills, tools, and schema foundation.

Indirect downstream consumers:

```text
DOM/locator specialist
frontend clarification/recovery rendering
E2E LLM-mode flows
recording/codegen explanation
future multi-model orchestration
```

Parallel safe work:

```text
DEV-1 can build backend validators.
DEV-3 can build UI using mock LLM outputs.
DEV-4 can build no-LLM deterministic harness paths.
```

---

## 7. Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Provides validators and rejects invalid LLM outputs |
| DEV-2 LLM | Primary owner of controller/policies/schemas |
| DEV-3 Frontend | Displays LLM explanations but renders backend truth |
| DEV-4 E2E | Tests LLM-mode flows with mocked/recorded LLM outputs where possible |

---

## 8. Epic acceptance criteria

EPIC-003 is accepted when:

- all LLM calls are routed through Runtime Controller
- purpose registry exists and is tested
- skill loading policy is minimal and source-aligned
- tool exposure is phase/purpose constrained
- structured output validation exists
- invalid schema retries once then fails closed
- journey plan/correction/recovery outputs are structured
- locator specialist cannot bypass backend validation
- telemetry logs purpose/model/tokens/latency/failure
- tests prove LLM cannot own runtime truth

---

## 9. Stop conditions

Stop if:

- current code has uncontrolled LLM call sites and migration plan is unclear
- model/tool routing is too coupled for a narrow change
- backend validator boundary is missing
- schema validation cannot be added test-first
- prompt/context changes risk behavior without regression evidence
