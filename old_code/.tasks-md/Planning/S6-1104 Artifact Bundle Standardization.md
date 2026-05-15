# S6-1104: Artifact Bundle Standardization

## Objective

Standardize the artifact bundle for local, CI, and paid runs.

## Acceptance Criteria

- [ ] Artifact manifest.json specifies required and optional files
- [ ] All required files created or absence documented
- [ ] Optional artifacts have clear absence reasons
- [ ] File hashes recorded in manifest
- [ ] Artifact writer is idempotent
- [ ] Failed E2E creates failure-context.json
- [ ] Successful E2E creates test-result.json
- [ ] Paid E2E blocked if artifact writer unavailable

## Required Artifact Bundle

manifest.json, test-result.json, events.ndjson, commands.json, rejections.json, trace.ndjson, llm-calls.json, token-report.json, backend.log, frontend.log, browser-console.log, screenshots/, payloads/, failure-context.json, redaction-report.json, summary.md

## Constraints

- No required artifact silently missing on failure
- No secret-bearing artifact without redaction annotation
- Paid test blocked if artifact writer unavailable

## Integration Points

- Works with S6-1101 (trace events)
- Works with S6-1102 (lifecycle trace)
- Works with S6-1103 (LLM calls)
- Works with S6-1105 (redaction)
- Works with S6-1106 (failure context)
- Feeds S6-1107 (trace export)
