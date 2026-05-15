# TEST-MATRIX-FE-001 Shadow DOM Frontend Test Cases

**Type:** Detailed Test Matrix  
**Priority:** P0  
**Owner:** DEV-3 Shadow DOM Frontend  
**References:** EPIC-005, TEST-FE-001  

---

## 1. Truth rendering tests

| Test ID | Type | Priority | Scenario | Steps | Expected Result |
|---|---|---:|---|---|---|
| FE-P-001 | Positive | P0 | plan_ready renders plan UI | emit plan_ready | plan panel visible with steps |
| FE-P-002 | Positive | P0 | step_executing renders status | emit step_executing | execution status visible |
| FE-P-003 | Positive | P0 | recovery_needed renders recovery UI | emit recovery_needed | recovery reason/options visible |
| FE-P-004 | Positive | P0 | step_recorded renders recorded row | emit step_recorded | recorded panel updated |
| FE-P-005 | Positive | P0 | code_update renders code | emit code_update | code panel updated |
| FE-P-006 | Positive | P0 | run_completed renders final state | emit run_completed | final status visible |
| FE-N-001 | Negative | P0 | LLM prose says done | render LLM text | UI does not mark completed |
| FE-N-002 | Negative | P0 | Trace row says success | click/view trace row | lifecycle state unchanged |
| FE-N-003 | Negative | P0 | Local confirm click | click confirm before backend event | UI pending only, not executing truth |
| FE-N-004 | Negative | P0 | Local correction submit | submit correction | old plan remains until backend plan_ready |
| FE-N-005 | Negative | P0 | Recovery option clicked | select option | recovery remains pending until backend event |

---

## 2. Command dispatcher tests

| Test ID | Type | Priority | Scenario | Steps | Expected Result |
|---|---|---:|---|---|---|
| FE-C-001 | Contract | P0 | Confirm command shape | click confirm | command_id/schema/source/plan_id/version |
| FE-C-002 | Contract | P0 | Correction command shape | submit correction | command includes plan_id/version/text |
| FE-C-003 | Contract | P0 | Clarification option_selected | choose option | target.kind=clarification |
| FE-C-004 | Contract | P0 | Recovery option_selected | choose recovery | target.kind=recovery |
| FE-C-005 | Contract | P0 | update_locator command | choose candidate | step_id/operation_id/candidate/ref |
| FE-C-006 | Contract | P0 | skip_step requires reason | click skip | reason required before command |
| FE-B-001 | Boundary | P0 | Double confirm | double click | one command or safe dedupe |
| FE-B-002 | Boundary | P0 | Backend rejection after command | command rejected | UI shows rejection; state unchanged |
| FE-B-003 | Boundary | P1 | WebSocket disconnected | click command | blocked/queued safely with diagnostic |

---

## 3. No-deadlock / failure-state tests

| Test ID | Type | Priority | Scenario | Expected Result |
|---|---|---:|---|---|
| FE-E-001 | Edge | P0 | Command pending timeout | visible status + retry/stop/diagnostic |
| FE-E-002 | Edge | P0 | Recovery has no options | stop/edit/export diagnostic available |
| FE-E-003 | Edge | P0 | Backend disconnected | reconnect/stop guidance visible |
| FE-E-004 | Edge | P0 | LLM schema failure | user sees error + retry/edit/stop |
| FE-E-005 | Edge | P0 | Unknown backend event | diagnostic only; no fake state |
| FE-E-006 | Edge | P0 | All buttons disabled regression | at least one safe action remains unless terminal |
| FE-R-001 | Regression | P0 | Spinner forever | timeout test prevents indefinite spinner |
| FE-R-002 | Regression | P0 | Error with no next step | test fails if no action |

---

## 4. Picker / recorded / trace tests

| Test ID | Type | Priority | Scenario | Expected Result |
|---|---|---:|---|---|
| FE-PICK-P-001 | Positive | P0 | Ancestor candidates shown | exact node + ancestor/container candidates |
| FE-PICK-N-001 | Negative | P0 | Candidate selected locally | no locator truth until backend accepts |
| FE-PICK-E-001 | Edge | P0 | Hidden/stale candidate | warning shown |
| FE-REC-P-001 | Positive | P0 | Assertion child display | assertion type/value correct |
| FE-REC-R-001 | Regression | P0 | expected_outcome leakage | metadata separate from assertion value |
| FE-CODE-N-001 | Negative | P0 | code_update before step_recorded | diagnostic/no fake recorded state |
| FE-TRACE-P-001 | Positive | P0 | Trace filter | display-only filter |
| FE-TRACE-N-001 | Negative | P0 | Trace click mutates state | forbidden |
| FE-TRACE-N-002 | Negative | P0 | Raw sensitive payload | redacted display |
| FE-A11Y-001 | Contract | P0 | Critical hooks present | aw-root/plan/recovery/recorded/code/picker/trace hooks |
| FE-A11Y-002 | Contract | P0 | Accessible action names | buttons/inputs labelled |
