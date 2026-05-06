# PLAN-004 Workstream Ownership Model

**Type:** Planning Control  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain  
**Applies To:** Four-developer split  

---

## 1. Purpose

This file defines ownership boundaries so four developers can work in parallel without architecture drift.

---

## 2. DEV-1 Backend Runtime + Event Truth

Owns:

- runtime state model
- active plan
- command validation
- event emission backend side
- confirmation gate
- execution contract
- correction diff validation/application
- recovery/failure truth
- recording builder
- completion guard
- replay smoke backend path
- capability gap backend event

Provides contracts to:

- DEV-2 LLM: what LLM outputs backend will accept
- DEV-3 Frontend: event/state payloads to render
- DEV-4 E2E: lifecycle assertions and event logs

Must not own:

- LLM prompt strategy
- frontend rendering logic
- fixture server internals
- robust replay repair specialist

---

## 3. DEV-2 LLM Runtime Controller + DOM/Page Policy

Owns:

- LLM purpose routing
- context policy
- skill loading policy
- tool exposure policy
- schema validation
- retry/fail-closed
- model routing
- LLM telemetry
- locator/page intelligence policy
- recovery diagnosis policy

Depends on DEV-1 for:

- accepted schemas
- backend validator boundaries
- state/plan/execution truth rules

Must not:

- mark runtime truth
- emit recorded/completed truth
- bypass backend execution contract

---

## 4. DEV-3 Shadow DOM Frontend + Typed Rendering

Owns:

- Shadow DOM host
- frontend state store
- LLM/Steps/Recorded/Code/Trace tabs
- plan review UI
- clarification/recovery UI
- blocking states
- stable frontend test hooks

Depends on DEV-1/EPIC-002 for:

- typed event payloads
- command payloads
- lifecycle status model

Can work in parallel using:

- mock canonical events
- mock state store
- fake backend event fixtures

Must not:

- infer lifecycle truth
- create frontend-only state authority
- build new product UI on legacy overlay assumptions

---

## 5. DEV-4 E2E Harness + Fixtures + Evidence

Owns:

- fixture server
- realistic fixture pages
- E2E runner
- backend/browser/frontend startup
- event log capture
- screenshot/trace artifacts
- stage-aware failure summary

Depends on all teams for:

- stable events
- stable test IDs/hooks
- backend lifecycle events
- mock/real server commands

Can work in parallel using:

- mock event fixtures
- local page fixtures
- skeleton runner

Must not:

- make live external sites mandatory for CI
- replace unit/contract tests with only E2E tests

---

## 6. Coordination matrix

| Story type | Primary owner | Reviewers |
|---|---|---|
| Backend state/contract | DEV-1 | DEV-2, DEV-3, DEV-4 |
| LLM schema/policy | DEV-2 | DEV-1 |
| Frontend event rendering | DEV-3 | DEV-1, DEV-4 |
| Harness/fixtures | DEV-4 | DEV-1, DEV-3 |
| Cross-flow E2E | DEV-4 | all |

---

## 7. Conflict rule

If a story touches another workstream’s owned boundary:

```text
stop
document dependency
ask for contract decision
do not silently implement cross-stream behavior
```
