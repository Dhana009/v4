# S7-0903 — Failure Detail Panel

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0901]

---

## Objective

Build detail panel for trace failure events. Show expected vs actual, failed layer, failed step/operation, evidence references, attempted recoveries, and next legal actions. Link to recovery card if available. Missing details show safe fallback.

After S7-0903:
- Clicking failure trace event opens detail panel
- Panel displays expected, actual, failed step/operation
- Evidence links available where provided
- Recovery context visible
- Next actions listed

---

## Source Rules

- PRD-06-TRACE-003: Failure detail context and remediation UI
- PRD-05-RECOVERY-002: Recovery context in failure events
- GOV-S7-C0-009: Negative tests required

---

## Tests First

### Component Tests

```python
test_failure_detail_panel_renders()  # PRD-06-TRACE-003
test_failure_detail_shows_expected_actual()  # PRD-06-TRACE-003
test_failure_detail_shows_failed_layer()  # PRD-06-TRACE-003
test_failure_detail_shows_recovery_context()  # PRD-05-RECOVERY-002
test_failure_detail_shows_next_actions()  # PRD-06-TRACE-003
test_failure_detail_malformed_safe()  # GOV-S7-C0-009
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/trace/FailureDetailPanel.jsx (new)
- tests/test_frontend_trace_timeline.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/
- frontend_new_design_prototype/
```

---

## Stop Conditions

Stop if:

- Failure event schema incomplete
- Coverage below 95%

