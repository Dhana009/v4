# S7-0808 — Code Warnings, Placeholder, and Capability States

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0806]

---

## Objective

Display code warnings and diagnostic states from `code_update.diagnostics[]`. Show warnings for fragile locators, repaired assertions, skipped steps, unsupported capabilities, placeholder test data, codegen failure, unresolved recovery. Warning severity visible (not color-only). Unsupported capability does not show fake code success.

After S7-0808:
- Warning list renders from code_update diagnostics
- Each warning shows severity (error/warning/info) and actionable message
- Placeholder data warning visible before code export
- Unsupported capability warning prevents success claim

---

## Source Rules

- PRD-05-CODEGEN-003: Diagnostics and warnings in code_update payload
- PRD-05-CAPGAP-001: Capability gap warning and next actions
- PRD-03-FE-011: No fake success for unsupported capabilities

---

## Current Known Context

### What exists
- S7-0806 renders code
- `diagnostics[]` field may be in `code_update` payload
- Capability gap events defined in PRD (Cluster 2)

### What gaps exist
- No diagnostics display component
- No severity indicator
- No actionable messaging
- No capability gap display integration

---

## Tests First

### Unit Tests

```python
test_diagnostic_from_code_update_payload()  # PRD-05-CODEGEN-003
test_diagnostic_severity_level()  # PRD-05-CODEGEN-003
test_placeholder_data_warning()  # PRD-05-CODEGEN-003
test_unsupported_capability_warning()  # PRD-05-CAPGAP-001
```

### Component Tests

```python
test_code_warnings_panel_renders()  # PRD-05-CODEGEN-003
test_warning_severity_displayed()  # PRD-05-CODEGEN-003
test_placeholder_warning_before_export()  # PRD-05-CODEGEN-003
test_unsupported_capability_prevents_pass()  # PRD-05-CAPGAP-001
```

### Negative Tests

```python
test_malformed_diagnostic_rejected()  # GOV-S7-C0-009
test_empty_diagnostics_array_renders()  # PRD-05-CODEGEN-003
test_severity_not_color_only()  # PRD-05-CODEGEN-003
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/code/CodeWarningsPanel.jsx (new)
- frontend/src/components/code/CodeDiagnostic.jsx (new)
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

1. Parse `diagnostics[]` from code_update event
2. Create component to display each diagnostic with severity badge
3. Ensure severity visible via text/icon (not color-only)
4. Show actionable message, not just type
5. Link to capability gap or recovery docs where applicable

---

## Stop Conditions

Stop if:

- `diagnostics[]` field not in `code_update` payload (file Cluster 2 ticket)
- Capability gap event schema incomplete
- Implementation requires backend changes

