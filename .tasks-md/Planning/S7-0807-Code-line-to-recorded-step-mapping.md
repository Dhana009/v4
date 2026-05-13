# S7-0807 — Code Line to Recorded Step Mapping

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0806]

---

## Objective

Display code line or section mapping to recorded step/operation in PRD-defined format. Clicking mapping highlights both code and recorded step locally. Links code to trace/evidence where available. Frontend rendering only; no mutation.

After S7-0807:
- Code line numbers or sections correlate to recorded step IDs
- Hovering/clicking highlights both code and step
- Links to trace/artifact if available
- Missing mapping shows fallback gracefully

---

## Source Rules

- PRD-05-CODEGEN-002: Code-to-step mapping via lineMapping metadata in code_update event
- PRD-05-REC-005: Recorded step references to code generation evidence

---

## Current Known Context

### What exists
- S7-0806 renders code
- `lineMapping` field may be in `code_update` payload
- Recorded step component exists from S7-0801

### What gaps exist
- No lineMapping schema verification
- No mapping display UI
- No highlight/click interaction
- No trace/evidence linking

---

## Tests First

### Unit Tests

```python
test_line_mapping_from_code_update_payload()  # PRD-05-CODEGEN-002
test_line_mapping_correlates_to_step_id()  # PRD-05-CODEGEN-002
test_missing_line_mapping_safe_fallback()  # GOV-S7-C0-009
```

### Component Tests

```python
test_code_line_renders_mapping_indicator()  # PRD-05-CODEGEN-002
test_recorded_step_renders_code_link()  # PRD-05-CODEGEN-002
test_click_mapping_highlights_code_and_step()  # PRD-05-CODEGEN-002
test_missing_mapping_shows_no_link()  # GOV-S7-C0-009
```

### Negative Tests

```python
test_malformed_line_mapping_rejected()  # GOV-S7-C0-009
test_stale_step_id_in_mapping_safe()  # GOV-S7-C0-009
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/code/CodeLineMapping.jsx (new)
- frontend/src/components/recorded/RecordedStepCodeLink.jsx (new)
- frontend/src/store/handlers/line_mapping_handler.js (new)
- tests/test_frontend_code_rendering.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Add optional `lineMapping` to code reducer state
2. Create component to render mapping indicators in code (gutter or inline)
3. Add code link to recorded step component
4. Implement local click/hover highlight only
5. Link to trace if artifact reference available

---

## Stop Conditions

Stop if:

- `lineMapping` field not in `code_update` payload (file Cluster 2 ticket)
- Implementation requires backend changes
- Coverage below 95%

