# S6-0803 — Recovery Context Packet

## Story ID
S6-0803

## Objective
Build a compact L4 recovery packet for `recovery_diagnoser` LLM call.

## Packet includes

```
failed_operation
original_user_intent
failure_classification
expected vs actual
current_page_state (high level, not raw DOM)
candidate_locators
what_deterministic_recovery_tried
allowed_repair_schema
artifact_refs
```

## What it must NOT include

```
raw_full_dom (by default)
full_chat_history
secrets
unbounded_trace_logs
```

## What it contains

- Packet builder function
- Selective DOM extraction (relevant elements only)
- Secret redaction (S6-0707)
- Artifact reference builder
- Packet validation (required fields present)
- Token usage estimation

## Tests first

### Unit tests

- Recovery packet includes failure classification
- Recovery packet includes tried deterministic attempts
- Recovery packet excludes secrets/raw DOM
- Recovery packet includes artifact refs where available
- Packet size stays under context budget (L4 ~20K tokens)
- Secret redaction applied to all fields
- Packet is serializable (JSON)
- Unknown failure type packet still valid

### Contract tests

- Recovery packet includes failed_operation and original_intent
- Recovery packet passes sufficiency gate (S6-0202)
- Selective DOM limited to ~10 elements + context
- Artifact refs resolvable by recovery_diagnoser

## Integration tests

- Packet builder integrates with failure classifier (S6-0801)
- Packet builder integrates with redaction policy (S6-0707)
- Packet fed to recovery_diagnoser (S6-0804)
- Token usage within LLM context budget

## Acceptance criteria

- Packet schema fully specified and documented
- Selective DOM extraction deterministic
- Token budget monitoring included
- 95% coverage on recovery_packet.py
- Integration tests verify packet → recovery_diagnoser flow
- No secrets in any packet field
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0801 (Failure Classification), S6-0802 (Deterministic Recovery), S6-0707 (Redaction)
- Blocks: S6-0804 (Recovery Proposal), S6-0805 (Lifecycle)

## Notes

- L4 context level defined in runtime policy (S6-0202)
- Token budget critical: ~20K per recovery packet fits in typical LLM context
- Selective DOM extraction balances context size with debuggability
- Design for auditability: packet logged before recovery_diagnoser call
