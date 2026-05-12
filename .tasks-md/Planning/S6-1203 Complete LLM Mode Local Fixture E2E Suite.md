# S6-1203: Complete LLM Mode Local Fixture E2E Suite

## Objective

Run local deterministic fixture E2E flows to verify Complete LLM Mode works end-to-end.

## Acceptance Criteria

- [ ] All 15 required local flows execute and pass
- [ ] Every flow produces artifacts
- [ ] Every failure produces failure-context.json
- [ ] No external websites fetched
- [ ] No paid LLM unless separately approved
- [ ] Trace/artifact bundle correct for each flow

## Required Test Flows

1. Free LLM page recommendation
2. Full journey with clarification
3. Steps queue
4. Selected section multi-action
5. Duplicate/weak DOM locator ambiguity
6. Plan discussion (no mutation)
7. Explicit plan correction
8. Permission required (submit/upload/download)
9. Recovery failure → repair/skip/stop
10. Save/load/replay one
11. Replay all
12. Replay broken locator → repair
13. Unsupported capability → gap logged
14. Reconnect/session state restore
15. Frontend five-tab state rendering

## Constraints

- No real websites
- No paid LLM
- Deterministic (same input = same output)
- Fixtures redacted (no PII)

## Notes

This is the local gating story. All 15 flows must pass before Cluster 12 paid work can proceed.
