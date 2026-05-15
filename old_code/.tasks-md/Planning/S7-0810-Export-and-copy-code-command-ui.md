# S7-0810 — Export and Copy Code Command UI

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Done
**Blocks:** []
**Blocked by:** [S7-0806]

---

## Objective

Expose copy-to-clipboard and export code controls. Copy uses current `codePreview` from backend. Export disabled if no code_update exists. Warn before export if code contains placeholders. Frontend does not fabricate file path; uses backend-provided path if available.

After S7-0810:
- Copy button copies current code to clipboard
- Export button disabled if no code_update
- Placeholder warning shown before export if applicable
- Frontend does not generate file path
- Backend command handlers optional (graceful degradation)

---

## Source Rules

- PRD-05-CODEGEN-004: Copy/export code commands and UX
- PRD-05-CODEGEN-003: Placeholder warning on export
- PRD-03-FE-009: Frontend does not infer or fabricate state (no inference from LLM text or missing events)
- PRD-03-FE-019: Frontend sends only typed, schema-validated commands

---

## Current Known Context

### What exists
- S7-0806 renders code
- Browser clipboard API available
- Diagnostics include placeholder warning (S7-0808)

### What gaps exist
- No Copy/Export buttons
- No clipboard integration
- No placeholder warning integration
- No file path handling

---

## Tests First

### Unit Tests

```python
test_copy_code_uses_current_codePreview()  # PRD-05-CODEGEN-004
test_export_button_disabled_without_code()  # PRD-05-CODEGEN-004
test_placeholder_warning_before_export()  # PRD-05-CODEGEN-003
```

### Component Tests

```python
test_copy_button_renders()  # PRD-05-CODEGEN-004
test_copy_button_triggers_clipboard()  # PRD-05-CODEGEN-004
test_export_button_disabled_when_no_code()  # PRD-05-CODEGEN-004
test_export_warning_shows_if_placeholders()  # PRD-05-CODEGEN-003
```

### Negative Tests

```python
test_copy_button_graceful_if_clipboard_unavailable()  # GOV-S7-C0-009
test_export_without_code_disabled()  # PRD-05-CODEGEN-004
test_export_does_not_fabricate_file_path()  # PRD-03-FE-009
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/code/CodeActionsBar.jsx (new)
- frontend/src/commands/codeCommands.js (new)
- tests/test_frontend_code_rendering.py (extend)
```

### Backend Seam (optional; graceful degradation if missing)
```
- No required backend changes; export can be client-only or call optional backend handler
```

### Forbidden Files

```
- agent.py
- runtime/codegen_*.py
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Create Copy button using browser Clipboard API
2. Create Export button — either client-only download or backend command (optional)
3. Disable Export if `codePreview` is null/empty
4. Check diagnostics for placeholder warning
5. Show warning dialog before export if placeholder detected
6. Do NOT generate file path on frontend; use backend-provided path or fallback

---

## Stop Conditions

Stop if:

- Browser clipboard API not available
- Need backend export command (coordinate with Cluster 2 if needed)
- Coverage below 95%


---

## Evidence Recorded

- **Commit:** 4abbb27 — Cluster 8 components
- **Tests:** tests/test_frontend_recorded_code_replay_cards.py (27 tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2444 passed / 1 skipped / 0 failed
