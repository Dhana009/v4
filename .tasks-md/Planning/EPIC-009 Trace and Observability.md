# EPIC-009 Trace and Observability

**Type:** Epic  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence/Observability  
**Primary Consumers:** DEV-1 Backend, DEV-2 LLM/DOM, DEV-3 Frontend, DEV-4 E2E Harness  
**Capability:** Correlated trace, telemetry, diagnostics, artifact export, and redaction  
**Readiness:** Planning-ready; stories require repo inspection before implementation  
**Depends On:** SOURCE-001, PLAN-002, PLAN-005, EPIC-001, EPIC-002, EPIC-003, EPIC-004, EPIC-005, EPIC-006, EPIC-008  
**Version:** Batch 10 v1  

---

## Product contribution

This epic makes AutoWorkbench debuggable without creating another source of runtime truth.

Final user/developer value:

```text
run starts
→ backend events, commands, LLM calls, DOM validation, recording, code_update, replay, and gaps are correlated
→ frontend can show diagnostics
→ E2E exports artifact bundles
→ developers can debug failures from evidence
→ trace never mutates runtime truth
```

Without EPIC-009:

- failures are hard to reproduce
- Codex cannot diagnose regressions safely
- event/command/LLM/DOM/recording evidence is fragmented
- artifact bundles may miss required proof
- sensitive data could leak into logs

---

## Source evidence table

| Source | Extracted rule | Planning interpretation | Epic impact |
|---|---|---|---|
| SOURCE-001 | Backend owns runtime truth; frontend renders typed truth. | Trace observes truth, never owns it. | All trace records are evidence/read-model only. |
| EPIC-002 | Events/commands are typed and correlated. | Trace must capture canonical event/command IDs. | Trace schema includes run_id/plan_id/step_id/operation_id/command_id. |
| EPIC-003 | LLM telemetry includes purpose/model/tokens/latency/validation. | LLM trace must include schema and retry status. | TRACE-004 consumes LLM telemetry. |
| EPIC-004 | DOM/locator validation produces evidence. | Locator trace captures candidate/validation decisions. | TRACE-005 captures DOM evidence. |
| EPIC-008 | recording/code_update produce artifacts. | Trace links recorded_step_id, codegen_version, diagnostics. | TRACE-006 consumes recording/codegen evidence. |
| EPIC-006 | E2E artifacts must prove behavior. | Trace exports bundle and redaction policy. | TRACE-009/010 define export and redaction. |

---

## Architecture decision

Fixed:

- Trace is read-only evidence.
- Trace must never mutate RunState, PlanState, StepState, OperationState, RecordingState, ReplayState, or UI truth.
- Trace records must be structured enough for tests.
- Every trace record should be correlated by run_id and specialized IDs where available.
- Trace should cover event, command, LLM, DOM, recording/codegen, replay, capability gap, and frontend diagnostic evidence.
- Artifact export should be deterministic and safe.
- Sensitive values require redaction policy.

Forbidden:

- using trace logs as lifecycle truth
- frontend inferring state from trace panel
- free-form-only logs as the only evidence
- storing raw secrets, tokens, OTPs, resumes, personal data, or user inputs without policy
- broad observability platform work before local artifact evidence

---

## Story map

| Story | Purpose | Direct consumers |
|---|---|---|
| TRACE-001 | trace identity/correlation model | all trace stories |
| TRACE-002 | backend lifecycle event trace | backend/debug/E2E |
| TRACE-003 | command/rejection trace | command failures |
| TRACE-004 | LLM telemetry/schema trace | LLM runtime debugging |
| TRACE-005 | DOM locator validation trace | locator/recovery debugging |
| TRACE-006 | recording/codegen trace | REC/E2E/debug |
| TRACE-007 | replay/capability-gap trace | replay/gap audit |
| TRACE-008 | frontend diagnostic trace panel | Shadow DOM UI |
| TRACE-009 | artifact bundle/export format | E2E and handoff |
| TRACE-010 | regression/redaction policy | safety/release gate |

---

## Direct vs indirect dependency note

Direct blockers:

```text
TRACE-001
TRACE-002
TRACE-003
TRACE-009
TRACE-010
```

Supporting/specialized:

```text
TRACE-004
TRACE-005
TRACE-006
TRACE-007
TRACE-008
```

Parallel safe work:

```text
DEV-1 can inspect backend logging/event correlation.
DEV-2 can inspect LLM telemetry and schema validation trace.
DEV-3 can inspect diagnostic panel rendering.
DEV-4 can inspect artifact export and E2E evidence.
```

---

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | Owns backend event/command/recording/replay trace emission |
| DEV-2 LLM/DOM | Owns LLM telemetry and DOM evidence semantics, not runtime truth |
| DEV-3 Frontend | Renders diagnostic trace panel as read-only evidence |
| DEV-4 E2E | Captures/export artifacts and asserts observability regressions |

---

## Epic acceptance criteria

EPIC-009 is accepted when:

- trace identity/correlation model exists
- backend lifecycle events can be traced
- commands and rejections can be traced
- LLM telemetry/schema validation trace exists
- DOM locator validation trace exists
- recording/codegen trace evidence exists
- replay/capability-gap trace evidence exists
- frontend trace panel reads trace without mutating state
- artifact bundle/export format exists
- redaction policy and regression tests exist

---

## Artifact bundle standard

Trace/export flows should produce:

```text
trace.ndjson
events.ndjson
commands.json
rejections.json
llm-telemetry.json
locator-validation.json
recording-codegen.json
replay-gap.json
frontend-diagnostics.json
redaction-report.json
summary.md
```

---

## Stop conditions

Stop if trace becomes a second source of truth, correlation IDs are missing, redaction is unclear, or artifact export cannot be tested locally.
