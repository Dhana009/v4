# TEST-MATRIX-EVENT-001 Typed Event Command Contract Test Cases

**Type:** Detailed Test Matrix  
**Priority:** P0  
**Owner:** DEV-1 Backend + DEV-3 Frontend + DEV-4 E2E  
**References:** EPIC-002, EVENT-001 through EVENT-010, TEST-DOCTRINE-001  

---

## 1. Backend event envelope tests

| Test ID | Type | Priority | Scenario | Steps | Expected Result |
|---|---|---:|---|---|---|
| EVENT-C-001 | Contract | P0 | Valid backend event envelope | build event with type/schema_version/payload | accepted |
| EVENT-C-002 | Contract | P0 | Missing type | build event without type | rejected |
| EVENT-C-003 | Contract | P0 | Missing schema_version | build event without schema_version | rejected or normalized by compatibility path |
| EVENT-C-004 | Contract | P0 | Missing run_id for run-scoped event | build run_started without run_id | rejected |
| EVENT-C-005 | Contract | P0 | Unknown event type | emit unknown type | typed diagnostic/rejection; frontend does not mutate |
| EVENT-C-006 | Contract | P0 | runtime_rejected payload shape | emit rejection | rejection_code/message/current_state/command_id where available |
| EVENT-B-001 | Boundary | P0 | Duplicate terminal event | emit run_completed twice | one terminal truth; duplicate flagged/rejected |
| EVENT-B-002 | Boundary | P0 | Out-of-order event | emit code_update before step_recorded | test fails/diagnostic |
| EVENT-R-001 | Regression | P0 | LLM-originated lifecycle event not truth | LLM emits lifecycle-like payload | backend ignores/rejects |

---

## 2. Frontend command envelope tests

| Test ID | Type | Priority | Scenario | Steps | Expected Result |
|---|---|---:|---|---|---|
| EVENT-CMD-C-001 | Contract | P0 | Valid confirm command | frontend sends confirm | command_id/source/schema/payload present |
| EVENT-CMD-C-002 | Contract | P0 | Missing command_id | send malformed command | runtime_rejected |
| EVENT-CMD-C-003 | Contract | P0 | Missing plan_version on confirm | send confirm without version | runtime_rejected |
| EVENT-CMD-C-004 | Contract | P0 | Unknown command | send invalid command type | runtime_rejected |
| EVENT-CMD-C-005 | Contract | P0 | option_selected target kind | send clarification/recovery option | target.kind correct |
| EVENT-CMD-C-006 | Contract | P0 | update_locator shape | send update locator | step_id/operation_id/candidate/ref present |
| EVENT-CMD-B-001 | Boundary | P0 | Double-click confirm | click confirm twice | one command or idempotent behavior |
| EVENT-CMD-B-002 | Boundary | P0 | Command while disconnected | send command disconnected | blocked/queued safely with UI diagnostic |

---

## 3. Event causality sequence tests

| Test ID | Type | Priority | Scenario | Expected Order |
|---|---|---:|---|---|
| EVENT-SEQ-001 | Integration | P0 | Happy planning flow | run_started → plan_ready |
| EVENT-SEQ-002 | Integration | P0 | Confirmed execution | plan_ready → confirmed/accepted → step_validating → step_executing |
| EVENT-SEQ-003 | Integration | P0 | Recording/code | step_executing → step_recorded → code_update |
| EVENT-SEQ-004 | Integration | P0 | Completion | all required terminal → run_completed |
| EVENT-SEQ-005 | Integration | P0 | Failure recovery | step_failed → recovery_needed |
| EVENT-SEQ-006 | Integration | P1 | Replay | replay_started → replay_result |
| EVENT-SEQ-007 | Negative | P0 | Recovery open completion | recovery_needed must not be followed by run_completed until resolved |
