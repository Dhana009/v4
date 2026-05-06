# TEST-MATRIX-BE-001 Backend Runtime Truth Test Cases

**Type:** Detailed Test Matrix  
**Priority:** P0  
**Owner:** DEV-1 Backend Runtime  
**References:** TEST-BE-001, EPIC-001, EPIC-002, EPIC-008, EPIC-009  

---

## 1. Backend state-machine tests

| Test ID | Type | Priority | Scenario | Preconditions | Steps | Expected Result | Evidence |
|---|---|---:|---|---|---|---|---|
| BE-P-001 | Positive | P0 | Start run enters planning state | backend idle | send valid run request | run state created; `run_started` emitted | event payload |
| BE-P-002 | Positive | P0 | plan_ready stores active plan | run planning | backend receives valid plan proposal | active plan has plan_id/version/steps | state snapshot |
| BE-P-003 | Positive | P0 | Confirm current plan | plan_ready | send confirm with current plan_id/version | run moves to confirmed/executable | event sequence |
| BE-P-004 | Positive | P0 | Execute confirmed child | confirmed plan with next child | execute next operation | step_validating → step_executing | event sequence |
| BE-P-005 | Positive | P0 | Complete run after all required steps | all required steps recorded | completion guard evaluates | run_completed emitted once | event payload |
| BE-N-001 | Negative | P0 | Execution before confirmation blocked | plan_ready but not confirmed | attempt execution | runtime_rejected; no browser execution | rejection payload |
| BE-N-002 | Negative | P0 | Frontend fake completion ignored | executing/recovery | frontend sends completed-like command/payload | backend state unchanged; rejection/diagnostic | state snapshot |
| BE-N-003 | Negative | P0 | LLM step_recorded ignored | executing | model emits step_recorded-like output | no recording truth created | trace/rejection |
| BE-N-004 | Negative | P0 | LLM run_completed ignored | executing | model emits done/completed output | no run_completed | event absence |
| BE-N-005 | Negative | P0 | Stale plan_version rejected | plan version N+1 active | confirm plan version N | runtime_rejected STALE_PLAN_VERSION | rejection payload |
| BE-N-006 | Negative | P0 | Wrong step_id rejected | confirmed step A expected | execute step B | runtime_rejected WRONG_STEP | rejection payload |
| BE-N-007 | Negative | P0 | Wrong operation_id rejected | operation A expected | execute operation B | runtime_rejected WRONG_OPERATION | rejection payload |
| BE-N-008 | Negative | P0 | run_completed blocked during recovery | recovery open | evaluate completion | no run_completed | event absence |
| BE-B-001 | Boundary | P0 | Duplicate confirm | plan_ready | send same confirm twice | idempotent no-op or typed rejection; no duplicate execution | command log |
| BE-B-002 | Boundary | P0 | Duplicate run_completed | completed | completion guard called twice | one terminal event only | event count |
| BE-B-003 | Boundary | P0 | Correction and confirm race | plan_ready | send correction and confirm close together | deterministic winner; stale command rejected | event order |
| BE-B-004 | Boundary | P0 | Stop during execution | executing | send stop_run | execution stops safely; terminal stopped event | event sequence |
| BE-B-005 | Boundary | P1 | Reconnect during recovery | recovery open | simulate disconnect/reconnect | session state restored/read-only; no fake completion | reconnect event |
| BE-E-001 | Edge | P0 | Partial child success | multi-child step | one child succeeds, next fails | parent not recorded until policy satisfied | recorded absence |
| BE-E-002 | Edge | P0 | Optional skipped step with reason | step optional | skip with valid reason | terminal skipped child allowed by policy | recorded payload |
| BE-E-003 | Edge | P1 | Capability gap during execution | unsupported iframe/upload | attempt unsupported action | capability_gap_recorded; no blind execution | gap payload |
| BE-R-001 | Regression | P0 | plan_ready cannot overwrite execution | executing | receive plan_ready-like proposal | rejected/ignored; execution contract preserved | state snapshot |
| BE-R-002 | Regression | P0 | recording not from last_successful_action only | prior successful action exists | record new failed/missing-evidence step | no incorrect recording from fallback | recorded payload absence |
| BE-R-003 | Regression | P0 | expected_outcome not assertion target/value | assertion step with expected_outcome | build recording/codegen | metadata separate; assertion fields unchanged | recorded/code payload |
| BE-R-004 | Regression | P0 | exact_text remains exact_text | exact text assertion executed | record/codegen | assertion_type exact_text; toHaveText/equivalent | code_update |
| BE-R-005 | Regression | P0 | visible assertion not click | visible assertion intent | execute/record | no click child; assertion child only | recorded payload |

---

## 2. Backend command validation tests

| Test ID | Type | Priority | Scenario | Preconditions | Steps | Expected Result | Evidence |
|---|---|---:|---|---|---|---|---|
| BE-C-001 | Contract | P0 | Valid command envelope accepted | any commandable state | send command with command_id/schema/source/payload | command reaches validator | command log |
| BE-C-002 | Contract | P0 | Missing command_id rejected | any | send command without command_id | typed runtime_rejected | rejection payload |
| BE-C-003 | Contract | P0 | Unknown command rejected | any | send unknown command type | typed rejection UNKNOWN_COMMAND | rejection payload |
| BE-C-004 | Contract | P0 | Command not allowed in phase rejected | executing | send correction if not allowed | typed rejection INVALID_PHASE | rejection payload |
| BE-C-005 | Contract | P0 | skip_step requires reason | recovery | send skip without reason | typed rejection MISSING_REASON | rejection payload |
| BE-C-006 | Contract | P0 | update_locator validates IDs | recovery | send update_locator missing operation_id | typed rejection | rejection payload |
| BE-C-007 | Contract | P1 | replay command blocked during active execution | executing | send replay_step | typed rejection or queued policy | rejection payload |
| BE-B-006 | Boundary | P0 | Same command_id repeated | command processed | resend same command_id | idempotent/rejected; no duplicate mutation | command log |

---

## 3. Recording / codegen / replay tests

| Test ID | Type | Priority | Scenario | Preconditions | Steps | Expected Result | Evidence |
|---|---|---:|---|---|---|---|---|
| BE-P-006 | Positive | P0 | Recording from execution evidence | operation succeeded | build recording | RecordedStep + ordered children + evidence_ref | recorded-step.json |
| BE-N-009 | Negative | P0 | Recording without evidence rejected | no evidence_ref | build recording | no step_recorded | rejection/diagnostic |
| BE-P-007 | Positive | P0 | code_update after step_recorded | recorded step exists | generate code | code_update emitted after step_recorded | event order |
| BE-N-010 | Negative | P0 | code_update before step_recorded blocked | no recording | call codegen event path | no normal code_update | diagnostic |
| BE-P-008 | Positive | P1 | Replay smoke correct page | replay archive exists; correct page | replay step | replay_started → replay_result pass | replay-result.json |
| BE-N-011 | Negative | P0 | Replay wrong page precondition failure | replay archive exists; wrong page | replay step | replay_result precondition failed | replay-result.json |
| BE-E-004 | Edge | P1 | Unsupported replay capability | archive has unsupported op | replay | capability gap / typed replay failure | gap payload |

---

## 4. Backend trace/redaction tests

| Test ID | Type | Priority | Scenario | Preconditions | Steps | Expected Result | Evidence |
|---|---|---:|---|---|---|---|---|
| BE-C-008 | Contract | P0 | Trace does not mutate runtime state | trace enabled | emit trace record | no RunState mutation | state snapshot |
| BE-C-009 | Contract | P0 | Event trace has correlation IDs | event emitted | write trace | run_id/event type/trace_id present | trace row |
| BE-N-012 | Negative | P0 | Sensitive data redacted | fake token/email in command | trace/export | raw sensitive value absent | redaction report |
