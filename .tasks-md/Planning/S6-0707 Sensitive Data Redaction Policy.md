# S6-0707 — Sensitive Data Redaction Policy

## Story ID
S6-0707

## Objective
Protect secrets and test data across prompts, logs, traces, code, and artifacts.

## What it contains

- Sensitive value classifier
- Prompt redaction policy (before LLM calls)
- Trace/log redaction policy (during execution)
- Artifact redaction (in output recordings)
- Generated-code placeholder policy (codegen uses references, not inline secrets)
- Redaction summary/report

## What it must NOT contain

- Secret storage (that's infrastructure/vault)
- Credential collection UI (that's frontend)
- Encryption (handled by infrastructure)
- Broad log filtering (only redaction in user-facing layers)

## Tests first

### Unit tests

- Credentials redacted from LLM prompt context
- OTP/manual code redacted from trace output
- File content not sent in prompts by default
- Secret values not printed in logs
- Generated code uses `{{placeholder}}` or reference, not inline credential
- Redaction deterministic: same secret → same redaction always
- Whitespace/formatting preserved in redacted values
- Redaction report generated with count/classification

### Contract tests

- Redaction event includes field, classification, redaction_type
- Redacted secrets cannot be recovered from trace
- Prompt redaction happens before LLM call (not after response)
- Generated code placeholders match promised values
- Artifact redaction report queryable

## Integration tests

- Credentials classified by S6-0705 trigger redaction
- Prompt redaction integrates with LLM runtime controller (S5)
- Generated code references are validated before execution
- Trace includes redaction report with summary

## Acceptance criteria

- Sensitive value classifier covers credentials, OTP, file content, secrets
- Prompt redaction 100% before LLM calls
- Trace/log redaction for secrets 100% on user-facing output
- Generated code uses placeholders for all secrets
- Redaction report included in all artifacts
- 95% coverage on redaction_policy.py
- Integration tests cover all redaction layers
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0705 (Test Data Classification), S6-0707 (Redaction)
- Blocks: S6-0802, S6-0809

## Notes

- Scenario spec requires redaction across prompts/logs/traces/artifacts/code
- Design for auditability: redaction report allows audit of what was protected
- Prompt redaction prevents LLM from learning secrets
- Generated code placeholders allow safe replay without exposing secrets
