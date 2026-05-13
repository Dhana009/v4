# S7-0407 — Shadow DOM Style Isolation and Host-Page Safety

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0407  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — CSS isolation via Shadow DOM
2. **Cluster 4 Goal** — host-page safety rules
3. **Frontend UI Spec** — style isolation requirements

---

## Objective

Ensure CSS isolation works correctly. Product CSS does not leak into page. Page CSS does not break panel controls. CSS variable conflicts handled safely.

After S7-0407:
- Product CSS scoped to Shadow DOM
- No `<style>` tags in Shadow DOM leak to page
- Page CSS does not break panel buttons/inputs
- CSS variables namespaced (e.g., `--aw-primary-color` not `--primary-color`)
- z-index and fixed elements controlled

---

## Tests First

### Unit Tests

**Test: Shadow DOM CSS scoping**
- Add CSS rule to Shadow DOM `<style>` element
- Verify rule does not apply to page (outside shadow root)
- Verify rule applies to shadow content

**Test: Page CSS does not affect panel inputs**
- Page has `input { background: red; }`
- Panel has input with expected background
- Input in panel has correct background (not red from page)

**Test: Panel CSS does not leak to page**
- Panel CSS sets button styling
- Page button has different styling (page CSS respected)

**Test: CSS variable namespacing**
- Use `--aw-primary-color` not `--primary-color`
- No conflict with page CSS variables
- Verify variable values scoped correctly

### Contract Tests

**Test: CSS isolation contract**
- Product CSS file contains only namespaced variables
- No color names that conflict with common variables
- CSS is valid and scoped

### Integration Tests

**Test: Panel visible in common page CSS scenarios**
- Page has `* { color: white; background: black; }`
- Panel still visible and readable (CSS isolation works)

**Test: Page buttons/links unaffected by panel CSS**
- Page has styled buttons
- Button styling unchanged by panel mount
- Panel CSS doesn't override page CSS

### Negative Tests

**Test: High z-index page elements**
- Page has z-index: 99999 element
- Panel z-index: 10000
- Panel behind page element (expected)
- Page element visible and interactive

**Test: Fixed position page elements**
- Page has fixed sidebar or header
- Panel doesn't break fixed positioning
- Fixed element still works correctly

---

## Implementation Boundaries

### Allowed Changes

- **Audit and document:** `frontend/src/styles/` or main CSS file
  - Verify all variables namespaced with `--aw-` prefix
  - Document color/spacing variable naming scheme

- **New module or extend:** `frontend/src/styles/isolation.css` or similar
  - Shadow DOM-specific CSS rules
  - Z-index management
  - Max 100 lines

- **New tests:** `tests/test_style_isolation.py`

### Forbidden Changes

- No changes to page CSS
- No overriding page CSS

---

## Acceptance Criteria

✅ **CSS properly scoped:**
- Product CSS in Shadow DOM only
- Page CSS not affected

✅ **Variable naming:**
- All custom properties prefixed with `--aw-`
- No conflicts with common variables

✅ **Panel controls work:**
- Buttons, inputs, etc. look and behave correctly
- Page CSS doesn't break them

✅ **Tests passing:**
- Unit, integration, negative tests green
- Regression baseline maintained

---

## Stop Conditions

- ❌ Product CSS affects page elements
- ❌ Page CSS breaks panel controls
- ❌ CSS variables not namespaced
- ❌ Z-index conflicts with page elements

---

## Related

- Prerequisite: S7-0401 (host)
- Related to: S7-0408 (picker exclusion)

---

## Next Story

→ S7-0408: Picker exclusion for AutoWorkbench UI
