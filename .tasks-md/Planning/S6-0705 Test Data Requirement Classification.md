# S6-0705 — Test Data Requirement Classification

## Story ID
S6-0705

## Objective
Detect required test data before planning/execution and classify by sensitivity/source.

## Test data classifications

```
text_value
email
phone
name
number
salary_range
file_reference
resume_file
credentials
otp_or_manual_code
dropdown_option
table_expected_value
api_or_crm_expected_value
generated_safe_test_data
sensitive_secret
```

## What it contains

- Test data requirement classifier
- Data type to classification mapping
- Required data detector (from LLM plan, from capability preconditions)
- Data sensitivity level
- Prompt for user to provide data
- Integration with S6-0706 (generated safe data proposal)

## What it must NOT contain

- Data generation (that's S6-0706)
- Secret/credential storage (that's infrastructure)
- User data collection UI (that's frontend)
- Redaction policy (that's S6-0707)

## Tests first

### Unit tests

- Resume upload requires `file_reference`
- Form fill with email requires `email` or `generated_safe_test_data` proposal
- OTP requires `otp_or_manual_code` → `requires_human_input`
- Credentials classified as `sensitive_secret`
- Table assertion requires `table_expected_value`
- API expected value requires `api_or_crm_expected_value`
- Classifier deterministic per input
- Unknown data type → `text_value` with sensitivity default

### Contract tests

- Missing required data emits `test_data_required` or `clarification_needed` event
- LLM cannot invent missing data as final truth
- Sensitive data classified and marked for redaction
- Data requirement trace survives full run lifecycle

## Integration tests

- Test data classifier integrates with capability registry (S6-0703)
- Missing data prevents execution (blocks S6-0708 permission/precondition)
- Data requirement flows to plan for visibility

## Acceptance criteria

- 15 data classifications fully defined
- Clear sensitivity level for each type
- Detector works on capability preconditions and LLM outputs
- 95% coverage on data_classifier.py
- Integration with required-data event contract
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0702, S6-0703, S6-0704
- Blocks: S6-0706, S6-0707, S6-0708

## Notes

- Scenario spec treats test data as first-class: must be collected before execution
- Do not generate credentials/secrets; ask user or fail-safe
- Design for auditability: trace includes all data classifications
- Integration with S6-0706 allows safe data proposals without blocking high-risk data
