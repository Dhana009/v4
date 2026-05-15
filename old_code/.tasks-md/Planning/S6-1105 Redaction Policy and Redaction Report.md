# S6-1105: Redaction Policy and Redaction Report

## Objective

Prevent sensitive data leakage across prompts, traces, logs, artifacts, and generated code.

## Acceptance Criteria

- [ ] Redaction policy module implemented
- [ ] API keys and tokens redacted from all artifacts
- [ ] Credentials redacted before artifact write
- [ ] OTP/manual codes redacted
- [ ] File content redacted by default (unless user-approved)
- [ ] Resume/test data references handled safely
- [ ] URL query params masked where needed
- [ ] Idempotent: already-redacted placeholders stay idempotent
- [ ] Redaction report lists redacted categories and counts

## Redaction Categories

secrets/api_keys, credentials, otp/codes, file_content, resume/pii, urls, auth_tokens, database_urls, private_keys

## Constraints

- No raw credentials in prompts
- No raw credentials in logs
- No raw credentials in artifacts
- No raw resume/file content by default
- No generated code with secrets unless user-approved

## Integration Points

- Works with S6-1104 (artifact bundle)
- Works with S6-1103 (LLM calls)
- Works with S6-1106 (failure context)
- Feeds S6-1107 (trace export)
- Required before S6-1205 (paid E2E)
