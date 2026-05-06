# Skill: UX Error and Blocking States

## Purpose
Ensure every blocked/failure state is understandable and actionable in the UI.

## When to use
Use for frontend error cards, clarification, permission, recovery, precondition failures, API/backend/LLM errors, locator ambiguity, plan invalidation, replay failures.

## Source of truth
- Frontend/UI negative and edge-case requirements
- Typed Event Contract
- Observability/Trace skill

## Non-negotiable rules
1. Every blocking state must show what happened, why, where, and next actions.
2. Do not show generic failure when typed reason exists.
3. UI should link to Trace evidence.
4. User must know where to respond.
5. Blocking UI must be driven by backend typed events.
6. Do not hide setup/API/backend failures in terminal only.

## Required UI handling
Show clear UI for:
```text
api_key_missing/api_key_invalid
backend_down
llm_timeout
clarification_needed
permission_required
test_data_missing
locator_ambiguous
precondition_failed
dependency_warning
plan_invalidated
recovery_needed
code_generation_failed
websocket_reconnecting
replay_failed
capability_gap
```

## Required actions examples
```text
Retry
Edit instruction
Provide data
Choose candidate
Navigate to required page
Replay dependencies
Allow once
Deny
View trace
Cancel
```

## Required tests
- UI rendering for blocking events
- action command emission
- Trace link/rendering
- no silent failure tests
- E2E for at least key blocking states

## Verification commands
```bash
npm run build
python -m pytest tests/e2e/<blocking_state_flow>.py -q -s
```

## Stop conditions
Stop if:
- backend event lacks needed UI fields
- UI must guess next action
- user cannot recover/cancel
- error exists only in logs
- same event renders inconsistently across tabs

## Reporting format
Report:
1. Blocking states handled
2. Events required
3. UI actions
4. Tests/results
5. Missing backend fields
