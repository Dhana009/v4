# S6-0801 — Failure Classification Pipeline

## Story ID
S6-0801

## Objective
Classify operation failures into typed categories before recovery.

## Error classifications

```
locator_not_found
locator_matches_multiple
locator_wrong_target
assertion_timeout
assertion_text_mismatch
action_timeout
element_not_interactable
element_hidden
element_detached
navigation_timeout
page_state_mismatch
permission_required
test_data_missing
unsupported_capability
llm_schema_invalid
tool_contract_mismatch
websocket_disconnect
unknown_runtime_error
```

## What it contains

- Failure classifier with 18 distinct error types
- Classification logic per error stage (locator, action, assertion, navigation, page)
- Evidence attachment (expected vs actual, screenshot, locators tried)
- Failure event contract with classification reason
- Classifier integration with recovery decision logic

## What it must NOT contain

- Recovery execution (that's S6-0802)
- Browser automation
- Permission enforcement (that's S6-0701)

## Tests first

### Unit tests

- Locator count 0 → `locator_not_found`
- Locator count >1 → `locator_matches_multiple`
- Hidden element → `element_hidden`
- Assertion timeout → `assertion_timeout`
- Text mismatch → `assertion_text_mismatch`
- Detached element → `element_detached`
- Wrong page → `page_state_mismatch`
- Missing test data → `test_data_missing`
- Classifier deterministic per input
- Unknown errors categorized as `unknown_runtime_error` (not swallowed)

### Contract tests

- `operation_failed` event includes error_type, failed_stage, expected, actual, evidence
- `operation_failed` includes next_allowed_actions based on classification
- Evidence compact: locator candidate list, screenshot, text diff, not full DOM
- Classification immutable after event emission
- Stale failure classification rejected

## Integration tests

- Failure classifier runs before deterministic recovery (S6-0802)
- Classification event flows to recovery diagnoser (S6-0804)
- Unknown errors do not crash runtime

## Acceptance criteria

- All 18 error types classified and documented
- Evidence capture complete without raw DOM default
- Classifier 100% deterministic
- 95% coverage on failure_classifier.py
- Contract tests cover integration with recovery
- Sprint 6 regression guard passes

## Dependencies

- Requires: None (foundational)
- Blocks: S6-0802 (Deterministic Recovery), S6-0804 (Recovery Proposal)

## Notes

- Classification is critical gating function for recovery decision
- Evidence format must be compact to fit recovery context (L4) budget
- Design for extensibility: new error types added without architecture change
- Scenario spec requires classification before recovery
