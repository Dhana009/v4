# TEST-FE-001 Shadow DOM Frontend Test Strategy

**Type:** Test Strategy  
**Status:** Planning  
**Priority:** P0  
**Owner:** DEV-3 Shadow DOM Frontend + DEV-4 E2E  

## 1. Purpose

Frontend is display and command-sender only.

Tests must prove:
```text
frontend renders backend truth clearly
frontend sends valid typed commands
frontend never creates fake lifecycle truth
frontend always gives user a next safe action when something fails
```

## 2. Truth boundary tests

```text
backend emits plan_ready → plan review UI appears
backend emits step_executing → execution status appears
backend emits recovery_needed → recovery UI appears
backend emits step_recorded → recorded step appears
backend emits code_update → code panel updates
backend emits run_completed → final status appears
```

Negative:
```text
LLM prose says done → frontend must not show completed
trace row says success → frontend must not update lifecycle
confirm click → frontend must not show executing until backend accepts
correction submitted → frontend must not replace plan locally
recovery option clicked → frontend must not close recovery locally
```

## 3. Command dispatcher tests

Actions:
```text
start run
confirm plan
submit correction
answer clarification
select recovery option
skip step
stop run
update locator
replay step
export trace
save/load if supported
```

Assert:
```text
command_id present
schema_version present
source present
run_id/plan_id/plan_version where needed
step_id/operation_id where needed
payload valid
duplicate click handled safely
backend rejection shown
```

## 4. Plan/recovery/recorded UI tests

Plan:
```text
plan steps render in order
child operations render under parent step
expected_outcome appears as metadata only
confirm visible only when plan confirmable
correction input available before confirmation
revised plan appears only after backend emits new plan_ready
backend rejects correction → error shown and no local mutation
```

Recovery:
```text
recovery_needed renders clear reason
recovery options render
retry sends typed command
skip requires reason
stop is always available
update_locator opens picker/candidate UI
backend rejection keeps recovery open
successful backend recovery event clears recovery
```

Recorded/code:
```text
step_recorded adds recorded parent row
child operations display in backend order
assertion children display assertion type/value correctly
expected_outcome displayed separately from assertion value
code_update appears only after backend event
diagnostic_only code_update shows warning, not fake code
```

## 5. No-deadlock rule

Every pending/error state must show at least one safe next action:
```text
retry
stop
edit
answer clarification
choose candidate
skip with reason
view diagnostic
export trace
```

Forbidden:
```text
blank panel
spinner forever
all buttons disabled
error with no action
unknown state with no explanation
```

## 6. Picker and trace panel tests

Picker:
```text
exact node candidate shown
ancestor candidates shown
section/card/form/dialog/code-block levels shown
hidden/disabled/stale candidates show warning
candidate selection sends update_locator/selection command
candidate selection does not mark locator final locally
backend rejection shown
```

Trace:
```text
trace rows render by type
filters are display-only
row expansion shows redacted payload
trace click does not mutate runtime
export includes filter metadata
missing evidence_ref shows warning
raw sensitive data not displayed
```

## 7. Accessibility/test hooks

```text
Shadow DOM root hook exists
plan panel hook exists
recovery panel hook exists
recorded/code panel hooks exist
picker candidate row hooks exist
trace panel hooks exist
buttons have accessible names
inputs have labels
dialogs/regions are labelled
keyboard access for critical actions
```

## 8. Mandatory regressions

```text
1. Frontend locally marks run completed.
2. Frontend locally replaces corrected plan.
3. Confirm button sends stale plan_version.
4. Duplicate confirm sends duplicate unsafe command.
5. Recovery UI closes before backend resolves.
6. Picker selection becomes locator truth locally.
7. code_update appears as if recorded when no step_recorded exists.
8. Trace panel changes runtime state.
9. Disconnected state leaves no action.
10. Error state shows no next step.
```
