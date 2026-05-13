# S7-0907 — Capability Gap Notices

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0500 (event store)]

---

## Objective

Render `capability_gap_recorded` events as user-visible notices. Show unsupported action/assertion and reason. Display next legal action. Dismissing notice is local UI only; does not mutate backend. No fake success for unsupported capability.

After S7-0907:
- Capability gap notice appears in-context (Recorded tab or alert)
- Gap includes unsupported action/assertion and reason
- Next legal action visible
- Notice dismissal is local UI only
- No fake success badge

---

## Source Rules

- PRD-05-CAPGAP-002: Capability gap recording and user notices
- PRD-03-FE-011: No fake state / static-demo fallback; frontend renders backend truth only
- GOV-S7-C0-009: Negative tests required

---

## Current Known Context

### What exists
- `capability_gap_recorded` event defined in PRD
- May be in Cluster 2 (event emission) or missing entirely

### What gaps exist
- Event may not be implemented in backend
- No Capability Gap notice UI
- No notice dismissal state (local)

---

## Tests First

### Unit Tests

```python
test_capability_gap_from_event_payload()  # PRD-05-CAPGAP-002
test_capability_gap_rejects_missing_action_type()  # GOV-S7-C0-009
```

### Component Tests

```python
test_capability_gap_notice_renders()  # PRD-05-CAPGAP-002
test_capability_gap_notice_shows_reason()  # PRD-05-CAPGAP-002
test_capability_gap_notice_shows_next_action()  # PRD-05-CAPGAP-002
test_notice_dismissal_local_only()  # PRD-03-FE-019
test_no_fake_success_with_capability_gap()  # PRD-05-CAPGAP-002
```

### Negative Tests

```python
test_malformed_capability_gap_safe()  # GOV-S7-C0-009
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/recorded/CapabilityGapNotice.jsx (new)
- frontend/src/store/handlers/capability_gap_handler.js (new)
- tests/test_capability_gap_notices.py (new)
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

- `capability_gap_recorded` event not implemented in backend (file Cluster 2 ticket)
- Coverage below 95%

