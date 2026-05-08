# TEST-BE-001 Backend Runtime Truth Test Strategy

**Type:** Test Strategy  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-1 Backend Runtime + DEV-4 Evidence  
**Applies To:** EPIC-001, EPIC-002, EPIC-008, backend portions of EPIC-009, MVP flows  

## 1. Purpose

Backend is the runtime truth layer. Backend tests must prove:
```text
backend owns state
backend validates every command
backend controls lifecycle transitions
backend records only from execution evidence
backend emits typed events that frontend/E2E can trust
```

## 2. State-machine model

States to test:
```text
idle
planning
plan_ready
correcting
confirmed
executing
recovery
recording
completed
stopped
failed
```

Every valid and invalid transition must be covered.

## 3. Required test groups

| Group | Purpose |
|---|---|
| Runtime reducer | State transitions and immutability |
| Phase-command matrix | Which commands are allowed in each phase |
| Event contract | Envelope/schema/causality |
| Command contract | Command shape, IDs, validation |
| Rejection contract | Typed failure behavior |
| Plan store/versioning | active plan, correction, stale plan rejection |
| Confirmation gate | no execution before confirm |
| Execution cursor | strict step/operation order |
| Recovery | retry/skip/stop/update_locator lifecycle |
| Recording builder | evidence-backed recorded parent/children |
| Codegen | deterministic code from recorded children |
| Completion guard | run_completed only at valid terminal state |
| Replay smoke | replay precondition/result |
| Capability gaps | unsupported behavior becomes typed gap |
| Snapshot/persistence boundary | save/load support vs typed gap |
| Trace/redaction | evidence without truth mutation |
| Idempotency/race | duplicate/concurrent command safety |
| Backward compatibility | legacy + canonical event migration |

## 4. Positive cases

```text
valid run starts
valid plan_ready stored
valid confirm accepted
valid execution follows confirmed cursor
valid recovery resolves
valid recording created from evidence
valid code_update follows recording
valid run_completed emitted after all required work terminal
valid replay smoke emits replay_result
valid capability gap recorded for unsupported behavior
```

## 5. Negative cases

```text
execute before confirm rejected
frontend fake completion ignored
LLM step_recorded ignored/rejected
LLM run_completed ignored/rejected
stale plan_version rejected
wrong step_id rejected
wrong operation_id rejected
recording without evidence rejected
code_update before step_recorded blocked
run_completed while recovery open blocked
unsupported capability not executed blindly
```

## 6. Boundary cases

```text
duplicate confirm
duplicate correction
duplicate step_recorded
duplicate code_update
duplicate run_completed
same command_id repeated
plan_ready emitted twice
correction arrives during execution
stop_run during execution
reconnect during recovery
replay while run is active
old event from previous run arrives
```

Expected: idempotent no-op or typed rejection; never state corruption.

## 7. Edge cases

```text
partial child success
optional step skipped with reason
navigation happens after click
wrong page before replay
unsupported iframe/upload/popup
capability gap during execution
backend crash/restart during run
large multi-step plan
recording/codegen diagnostic-only path
```

## 8. Mandatory regressions

```text
1. No execution before confirmation.
2. Old plan_version rejected after correction.
3. Correction diff cannot silently drop children.
4. Wrong step_id / operation_id rejected by strict cursor.
5. LLM step_recorded ignored/rejected.
6. LLM run_completed impossible.
7. expected_outcome never becomes assertion target/value.
8. exact_text assertion stays exact_text.
9. visible assertion does not become click.
10. code_update never before step_recorded.
11. run_completed never while recovery open.
12. recording not built only from last_successful_action.
13. replay wrong page gives precondition failure.
14. frontend command missing command_id gives typed rejection.
15. duplicate terminal event handled safely.
```

## 9. Coverage

```text
95% line coverage for new/changed backend/runtime modules
branch coverage for validators/reducers/state machines
100% command rejection paths covered
100% event envelope paths covered
100% known backend regressions covered
```
