# Skill: Permission and Safety

## Purpose
Prevent unsafe browser actions and external side effects without user approval.

## When to use
Use for submit/upload/download/delete/navigation-to-external/auth/OTP/payment/CRM/API-side-effect operations, permission UI, autonomy modes.

## Source of truth
- Complete LLM Mode permission/autonomy model
- Capability framework
- Frontend permission UI spec

## Non-negotiable rules
1. Risky actions require permission according to mode.
2. LLM cannot override permission policy.
3. Backend decides risk and permission status.
4. UI must show clear permission prompt.
5. Denied permission must be remembered for the run/session.
6. Destructive/external side effects must not run silently.

## Risk levels
```text
safe_read_or_assert
medium_browser_action
high_risk_submit_upload_download
destructive_or_external_side_effect
unsupported_capability
requires_human_input
```

## Permission modes
```text
strict
balanced
auto
```

## Required implementation behavior
- Classify action risk before execution.
- Emit permission_required with operation, reason, risk_level, choices.
- Accept permission_response.
- Store permission_state.
- Respect denied actions.
- Include permission events in Trace.

## Required tests
- permission_required emission
- allow once/allow for run/deny handling
- risky action blocked without permission
- denied action not retried
- permission trace tests

## Verification commands
```bash
python -m pytest tests/test_*permission* tests/test_*safety* -q
```

## Stop conditions
Stop if:
- action risk is unknown
- risky action can execute without permission
- permission UI/event is missing
- LLM can call tool despite denied permission
- external side effect is not classified

## Reporting format
Report:
1. Risk classification changed
2. Permission events/commands
3. Tests/results
4. Remaining safety gaps
