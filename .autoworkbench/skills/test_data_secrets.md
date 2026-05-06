# Skill: Test Data and Secrets

## Purpose
Handle user-provided/generated test data, file uploads, credentials, OTPs, and sensitive data safely.

## When to use
Use for forms, upload flows, credentials/auth, OTP/manual input, test data registry, generated data, logs, traces, codegen placeholders.

## Source of truth
- Complete LLM Mode test data management
- LLM Runtime Policy memory/safety rules
- Permission/Safety skill

## Non-negotiable rules
1. Do not let LLM invent required real data.
2. Ask user or generate safe test data only with permission.
3. Store file references and secret references, not raw sensitive content where possible.
4. Redact secrets in logs, trace, screenshots where applicable.
5. Do not send raw credentials/OTP/files to LLM by default.
6. Generated data should be visible/editable before execution when relevant.
7. Codegen should use placeholders/fixtures unless user permits inline values.
8. Do not invent missing sensitive data.

## Test data classifications
```text
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
generated_safe_test_data
sensitive_secret
```

## Required implementation behavior
- Emit test_data_required when missing.
- Track requirement status: missing/proposed/provided/validated/rejected.
- Use value_ref for sensitive/file data.
- Respect redaction_policy.
- Show data requirements in UI.
- Validate file exists before upload.

## Required tests
- missing data prompts
- generated data proposal
- secret redaction tests
- file reference validation
- LLM context excludes secrets
- codegen placeholder tests

## Verification commands
```bash
python -m pytest tests/test_*data* tests/test_*secret* tests/test_*upload* -q
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- sensitive data would be logged
- LLM receives raw secret without explicit need/approval
- upload lacks file reference
- required data is guessed
- codegen would leak credentials

## Reporting format
Report:
1. Data types handled
2. Redaction behavior
3. UI/backend events
4. Tests/results
5. Security risks
