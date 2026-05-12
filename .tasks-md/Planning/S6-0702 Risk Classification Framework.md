# S6-0702 — Risk Classification Framework

## Story ID
S6-0702

## Objective
Classify actions and capabilities before execution into risk tiers.

## Risk levels

```
safe_read_or_assert
medium_browser_action
high_risk_submit_upload_download
destructive_or_external_side_effect
unsupported_capability
requires_human_input
```

## What it contains

- Risk classifier function with clear mapping
- Capability category to risk mapping (actions, assertions, navigation, auth, files, tables, external)
- Operation risk metadata schema
- Risk trace event with classification reason
- Safe/medium/high/destructive decision boundary definitions

## What it must NOT contain

- Browser execution
- Frontend implementation
- Destructive action execution
- Permission enforcement (that's S6-0701)

## Tests first

### Unit tests

- Assert/read actions classified as `safe_read_or_assert`
- Click/fill/navigation classified as `medium_browser_action`
- Submit/upload/download classified as `high_risk_submit_upload_download`
- Delete/payment/send-email classified as `destructive_or_external_side_effect`
- Unsupported behavior classified as `unsupported_capability`
- OTP/captcha/manual-login classified as `requires_human_input`
- Classifier deterministic: same action → same risk always
- Custom action risk can be overridden by policy

### Contract tests

- Risky operation cannot bypass permission gate (integration with S6-0701)
- Unsupported capability cannot become executable operation
- Risk classification event includes operation, reason, assigned_level
- Risk trace survives full run lifecycle

## Integration tests

- Risk classifier wired to permission decision in runtime
- Failed risk classification defaults to highest risk tier
- Unknown operation type → destructive tier by default

## Acceptance criteria

- All six risk tiers fully specified with clear boundaries
- Classifier 100% deterministic per input
- Mapping document included (action → risk matrix)
- 95% unit coverage on risk_classifier.py
- Contract tests cover integration with S6-0701
- Sprint 6 regression guard passes

## Dependencies

- Requires: None (foundational)
- Blocks: S6-0701, S6-0703, S6-0704, S6-0705

## Notes

- Risk classification is input to permission decision, not decision itself
- Classifier output is immutable; recorded in trace for audit
- Design for extensibility: custom capability risk should be configurable per org/user
