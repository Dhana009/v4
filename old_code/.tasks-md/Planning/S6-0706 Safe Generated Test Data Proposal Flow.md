# S6-0706 — Safe Generated Test Data Proposal Flow

## Story ID
S6-0706

## Objective
Allow generated non-sensitive test data only with user visibility and control.

## What it contains

- `generated_safe_test_data` proposal schema
- Proposal state machine (proposed → accepted | rejected | edited)
- Deterministic templates for safe data (email, name, phone, etc.)
- User edit capability before execution
- Non-secret-only constraint
- Proposal appearance in plan for visibility

## What it must NOT contain

- Secret/credential generation
- User data collection UI (that's frontend)
- Automatic acceptance without review
- Data storage (persistence handled elsewhere)

## Tests first

### Unit tests

- Safe email proposal deterministic and valid format
- Safe name proposal deterministic and realistic
- Safe phone proposal deterministic and valid
- Generated data marked with `source: generated`, not user_provided
- User can edit proposed data before execution
- Sensitive/credential data cannot be auto-generated as final truth
- Proposal state transitions valid (proposed → accepted | rejected | edited)
- Proposal includes field name and reason

### Contract tests

- Generated data appears in plan for review before execution
- Execution blocked on required generated data until user accepts/provides
- Policy can require explicit acceptance for each generated field
- Proposal event includes data value in redacted form

## Integration tests

- Test data classifier (S6-0705) triggers proposal for safe data gaps
- Proposal integrates with permission/precondition checks (S6-0708)
- Accepted proposal flows to plan as available data
- Rejected proposal triggers data_required event

## Acceptance criteria

- Proposal schema fully defined and testable
- At least 5 safe data types with deterministic templates
- Edit-before-execution flow fully testable
- 95% coverage on generated_data.py
- Integration tests cover proposal lifecycle
- No secrets in generated data
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0705 (Test Data Classification)
- Blocks: S6-0708 (Auth/Precondition), S6-0809 (Regression)

## Notes

- Proposals are non-binding suggestions; user has full control
- Deterministic templates allow reproducible runs for test data
- Design for extensibility: new safe data types added via config, not code
- Integration with S6-0705 ensures only safe data types are proposed
