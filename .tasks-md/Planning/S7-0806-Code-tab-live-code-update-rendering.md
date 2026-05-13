# S7-0806 — Code Tab Live Code Update Rendering

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-0807, S7-0808]
**Blocked by:** [S7-0500]

---

## Objective

Build Code tab to render `code_update` backend events. Display generated test code with syntax highlighting. Show empty state before first code_update. Never show frontend-generated or fabricated code. No code appears without backend code_update event.

After S7-0806:
- Code tab component exists
- `code_update` events update frontend store
- Code displays with syntax highlighting
- Empty state shows before first code_update
- Malformed code_update payload safely rejected

---

## Source Rules

- PRD-05-CODEGEN-001: Code tab shows backend-generated test code only; no frontend code generation
- PRD-04-BACKEND-009: code_update event payload with code, diagnostics, lineMapping
- PRD-03-FE-C8-002: Frontend never generates code; renders backend code_update only
- PRD-03-FE-007: No demo/draft code in live mode
- GOV-S7-C0-004: Negative tests required

---

## Current Known Context

### What exists
- `code_update` event defined in PRD
- `codegen_*.py` modules in backend generate code
- No Code tab component exists
- `frontend_new_design_prototype/` has static code mockup

### What gaps exist
- No Code tab component
- No syntax highlighting integration
- No `code_update` event handler in frontend store
- No empty state

---

## Tests First

### Unit Tests

```python
test_code_update_from_event_payload()  # PRD-04-BACKEND-009
test_code_update_with_syntax_language()  # PRD-05-CODEGEN-001
test_code_update_rejects_missing_code()  # GOV-S7-C0-004
test_code_update_timestamp_display()  # PRD-04-BACKEND-009
```

### Reducer Tests

```python
test_reducer_code_update_replaces_codePreview()  # PRD-03-FE-007
test_reducer_code_update_maintains_update_history()  # PRD-05-CODEGEN-001
test_reducer_code_update_preserves_lineMapping()  # PRD-04-BACKEND-009
```

### Component Tests

```python
test_code_tab_renders_empty_state()  # PRD-03-FE-007
test_code_tab_renders_code_with_syntax_highlight()  # PRD-05-CODEGEN-001
test_code_tab_renders_update_timestamp()  # PRD-04-BACKEND-009
test_code_tab_renders_malformed_safe()  # GOV-S7-C0-004
```

### Negative Tests

```python
test_code_update_with_null_code_rejected()  # GOV-S7-C0-004
test_code_update_with_wrong_language_type_rejected()  # GOV-S7-C0-004
test_frontend_never_generates_code()  # PRD-05-CODEGEN-001
test_code_tab_shows_empty_before_first_code_update()  # PRD-03-FE-007
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/code/CodeTab.jsx (new)
- frontend/src/components/code/CodeHighlighter.jsx (new)
- frontend/src/store/codeSlice.js (new)
- frontend/src/store/handlers/code_update_handler.js (new)
- tests/test_frontend_code_rendering.py (new)
```

### Forbidden Files

```
- agent.py
- runtime/codegen_*.py (read-only)
- frontend_new_design_prototype/
- Do NOT add code generation logic to frontend
```

---

## Implementation Notes

1. Create `CodeTab` component that consumes `codePreview` from event store
2. Use library like `react-syntax-highlighter` or similar for syntax highlighting
3. Add reducer to process `code_update` events
4. Show empty state before first event
5. Reject malformed payload with diagnostic

---

## Stop Conditions

Stop if:

- `code_update` event schema missing required fields
- Need to add code generation logic (coordinate with backend Cluster 2)
- Syntax highlighter library selection requires infrastructure change
- Coverage below 95%

