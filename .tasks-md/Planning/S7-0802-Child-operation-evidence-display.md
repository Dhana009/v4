# S7-0802 — Child Operation Evidence Display

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-0803]
**Blocked by:** [S7-0801]

---

## Objective

Extend Recorded tab to display child operation evidence under each recorded parent step. Show action/assertion operation types, locator/target details, and expected_outcome metadata. No child operation displays as pass unless explicitly confirmed by later evidence.

After S7-0802:
- Each recorded step expands to show child operations
- Action and assertion operations render with type/locator/target/expected_outcome
- Operations render in backend event order
- Failed/unresolved operations do not show as pass

---

## Source Rules

- PRD-05-REC-002: Child operation evidence includes action/assertion type, locator/target, expected_outcome metadata
- PRD-05-REC-003: Expected outcomes are metadata; they do not imply operation success
- PRD-03-FE-C8-001: Frontend renders backend evidence only; no inferred success
- GOV-S7-C0-004: No negative tests → no merge

---

## Current Known Context

### What exists
- `step_recorded.children[]` field defined in PRD and event schema
- S7-0801 creates parent step rendering
- Frontend component architecture from S7-0801 can be extended

### What gaps exist
- No child operation display component
- No expansion/collapse mechanism for parent step
- No operation type display (action vs assertion)
- No failure/unresolved state for operations

### Current test status
- Contract tests verify `children[]` schema but no display tests

---

## Tests First

### Unit Tests

```python
test_operation_from_event_payload()  # PRD-05-REC-002
test_operation_action_vs_assertion_type()  # PRD-05-REC-002
test_operation_locator_target_rendering()  # PRD-05-REC-002
test_operation_rejects_missing_type()  # GOV-S7-C0-004
test_operation_rejects_missing_locator()  # GOV-S7-C0-004
```

### Component Tests

```python
test_recorded_step_expands_to_show_children()  # PRD-05-REC-002
test_child_operations_render_in_order()  # PRD-05-REC-002
test_operation_renders_action_type()  # PRD-05-REC-002
test_operation_renders_assertion_type()  # PRD-05-REC-002
test_operation_renders_locator_and_target()  # PRD-05-REC-002
test_operation_renders_expected_outcome_as_metadata()  # PRD-05-REC-003
test_child_operation_malformed_rejected_safely()  # GOV-S7-C0-004
```

### Negative Tests

```python
test_child_operation_with_null_type_rejected()  # GOV-S7-C0-004
test_child_operation_with_missing_locator_shows_fallback()  # GOV-S7-C0-004
test_recorded_step_empty_children_array_shows_no_operations()  # PRD-05-REC-002
test_failed_child_operation_does_not_show_pass()  # PRD-05-REC-003
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/recorded/RecordedOperation.jsx (new)
- frontend/src/components/recorded/RecordedStep.jsx (modification to expand/collapse)
- tests/test_frontend_recorded_evidence_rendering.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/*.py
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Create `RecordedOperation` component for single child operation display
2. Add expand/collapse state to `RecordedStep` component
3. Render `children[]` array from parent step payload
4. Show operation type (action/assertion) clearly
5. Display locator and target details
6. Render expected_outcome as informational metadata (not confirmation)

---

## Stop Conditions

Stop if:

- Child operation schema does not match PRD expectations
- Implementation requires new backend event/command
- Coverage falls below 95%

