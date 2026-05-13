# S7-0705 — Selected Element Preview

**Sprint:** Sprint 7  
**Cluster:** 7  
**Tier:** 2  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0704

---

## Objective

Display selected element context safely: accessible name, role/tag, text summary, section hierarchy. Element preview is candidate/context only, not evidence.

---

## Tests First

### Component Tests

```
test_element_preview_shows_accessible_name()
test_element_preview_shows_role_tag()
test_element_preview_truncates_long_text()
test_sensitive_values_redacted()
test_preview_hidden_when_no_element_selected()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/steps/ElementPreview.jsx`
- **New:** `tests/test_frontend_element_preview.py`

### Forbidden Files

- No raw sensitive value exposure
- No screenshot/highlight (E2E scope)

---

## Acceptance Criteria

- [ ] Element preview renders selected element info
- [ ] Sensitive values redacted
- [ ] Long text truncated
- [ ] Preview not treated as evidence
- [ ] All tests pass

---

## Stop Conditions

- Screenshot/highlight required (E2E scope)
- Sensitive value redaction rules undefined
