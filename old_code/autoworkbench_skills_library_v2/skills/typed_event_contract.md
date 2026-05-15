# Skill: Typed Event Contract

## Purpose
Keep backend, frontend, LLM, trace, and tests synchronized through explicit typed events and commands.

## When to use
Use for WebSocket commands/events, frontend handlers, backend emitters, UI state, trace, LLM status, replay, code_update, locator events, permission/test data events.

## Source of truth
- PRD backend event contract
- Frontend/UI spec event mapping
- Backend/UI state contract

## Non-negotiable rules
1. No lifecycle state from prose.
2. No frontend inference of backend truth.
3. Events must have stable type names and payload shape.
4. Commands must be typed and validated.
5. Blocking states must include next allowed actions.
6. Errors must include reason/classification and evidence where possible.
7. UI-visible state should be represented in backend state objects.
8. Unknown events must go to Trace, not silently disappear.

## Required implementation behavior
Define/maintain events for:
```text
status/phase_update
conversation_state_updated
plan_ready
plan_diff_proposed/applied/failed
steps_updated
dependency_warning
locator_update_result
precondition_failed_for_locator_update
clarification_needed
permission_required
execution_started
operation_started/failed
recovery_needed
step_recorded
code_update
replay_started/result
trace_summary_updated
llm_call_started/completed/failed
```

Define/maintain commands for:
```text
chat_message_submitted
run_steps
confirmed
correction
step_edit_request
locator_update_request
option_selected
permission_response
arm_picker
replay_one
replay_all
save_snapshot
```

## Required tests
- Backend event payload tests
- Frontend handler tests/build where possible
- Contract tests for command validation
- E2E asserts for critical events
- Unknown/malformed command tests

## Verification commands
```bash
python -m pytest tests/test_*ws* tests/test_*event* tests/test_*contract* -q
npm run build
```

## Stop conditions
Stop if:
- event payload shape is unclear
- frontend needs to parse LLM prose to infer state
- command is accepted without backend validation
- important errors have no typed reason
- UI blocking state lacks next action

## Reporting format
Report:
1. Events/commands added/changed
2. Payload fields
3. UI destinations
4. Tests/results
5. Compatibility risks
