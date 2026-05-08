# EPIC-008 Recording and Codegen

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-1 Backend Runtime + Recording/Codegen  
**Primary Consumers:** DEV-3 Shadow DOM Frontend, DEV-4 E2E Harness, Replay stories  
**Capability:** Backend-owned recording and deterministic Playwright code generation  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, EPIC-006, EPIC-007, BE-006, BE-009, BE-010, EVENT-006, FE-006, E2E-010  
**Version:** Batch 09 v1  

---

## Product contribution

This epic turns validated browser execution evidence into trustworthy recorded steps and deterministic Playwright code.

```text
confirmed plan
→ backend validates and executes child operations
→ backend records parent step + ordered child operations/checks
→ backend generates deterministic Playwright code
→ backend emits step_recorded and code_update
→ frontend renders backend-owned output
→ replay smoke consumes recorded archive
```

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Epic impact |
|---|---|---|---|
| SOURCE-001 | Backend owns recording and codegen first. | LLM/frontend cannot create recording truth. | Recording builder and codegen are backend-owned. |
| BE-006 | Confirmed plan children become execution contract. | Recording must preserve confirmed step/child identity and order. | Recorded data model links to plan_id/version/step_id/operation_id. |
| BE-009 | Recording model is parent recorded step with child operations/checks. | Recording must be structured and evidence-backed. | REC-001/REC-002 define parent-child model and builder. |
| EVENT-006 | `step_recorded` and `code_update` are typed backend events. | UI consumes backend payloads only. | REC-005 defines event/UI integration. |
| DOM-006 | expected_outcome is metadata only, not assertion target/value. | Assertion recording must separate target/value/metadata. | REC-003/REC-007 protect assertion semantics. |
| EPIC-006 / MVP | E2E must prove recording/code_update and replay smoke. | Regression matrix must include action/assertion/correction/multi-step cases. | REC-010 defines tests. |

---

## Architecture decision

Fixed:

- Recording is backend-owned.
- Recorded step is a parent containing ordered child operations/checks.
- Recording is built from backend execution/assertion evidence only.
- LLM cannot emit `step_recorded` as truth.
- Frontend cannot create or reorder recorded/code truth.
- `code_update` must not emit before recording is finalized.
- Codegen is deterministic and backend-owned first.
- expected_outcome remains parent metadata only.
- observed_outcome is evidence/summary, not assertion source unless explicitly validated.
- Replay archive baseline uses recorded children, not regenerated LLM plan.

Forbidden:

- record from `last_successful_action`
- codegen from LLM prose
- code_update before step_recorded
- expected_outcome-as-target/value
- silently dropping/reordering child operations
- replay archive built from frontend state

---

## Story map

| Story | Purpose | Direct consumers |
|---|---|---|
| REC-001 | parent-child recorded step model | all recording/codegen/replay |
| REC-002 | evidence-to-recording builder | step_recorded |
| REC-003 | assertion recording semantics | assertion codegen |
| REC-004 | deterministic Playwright codegen | code_update |
| REC-005 | code_update event/UI integration | FE-006/E2E |
| REC-006 | ordering/deduplication | multi-step stability |
| REC-007 | expected/observed outcome handling | recording/trace |
| REC-008 | persistence/replay archive baseline | replay smoke |
| REC-009 | codegen diagnostics/reviewer | quality guard |
| REC-010 | regression matrix | acceptance evidence |

---

## Direct vs indirect dependency note

Direct blockers:

```text
REC-001
REC-002
REC-003
REC-004
REC-005
REC-006
REC-010
```

Supporting/conditional:

```text
REC-007
REC-008
REC-009
```

Parallel safe work:

```text
DEV-1 can inspect backend recording/codegen modules.
DEV-2 can inspect LLM/code-review boundaries but cannot generate truth.
DEV-3 can inspect recorded/code panel rendering using mock backend events.
DEV-4 can map recording/codegen E2E scenarios and fixtures.
```

---

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Primary owner of recording builder, codegen, code_update payloads |
| DEV-2 LLM/DOM | May suggest diagnostics/review comments, not recording/code truth |
| DEV-3 Frontend | Renders `step_recorded` and `code_update` payloads only |
| DEV-4 E2E | Proves recording/codegen via event/UI/code artifacts |

---

## Epic acceptance criteria

- recorded parent-child model is defined
- recording builder consumes execution evidence, not LLM prose
- assertion recording separates target, expected value, and metadata
- deterministic codegen exists for click/fill/assert/navigate baseline
- `code_update` payload follows `step_recorded`
- child ordering/deduplication is enforced
- expected_outcome/observed_outcome handling is source-aligned
- persistence/replay archive baseline is defined or typed gap documented
- diagnostics/reviewer path is advisory-only
- regression matrix covers click, visible assert, exact text, correction, multi-step, code_update, replay smoke

---

## Artifact bundle standard

```text
events.ndjson
recorded-step.json
recorded-children.json
code-update.json
execution-evidence.json
trace-summary.txt
screenshots where relevant
test-result.json
```

---

## Stop conditions

Stop if current implementation cannot identify execution evidence source, code_update path is frontend/LLM-owned, recording conflicts with BE-006, assertion semantics are unclear, or replay archive scope expands beyond P0 baseline.
