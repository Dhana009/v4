# S7-0303 Design Token Extraction and Style System

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0303  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Extract visual design tokens from prototype (colors, typography, spacing, radius, shadows) and create production style system (`frontend/styles/tokens.css`). No component implementation; tokens only.

---

## Design Token Scope

- **Colors** — Primary, secondary, danger, success, etc.
- **Typography** — Font families, sizes, weights, line heights
- **Spacing** — Margin, padding scale (4px, 8px, 12px, 16px, 24px, etc.)
- **Radius** — Border radius values
- **Shadows** — Box shadow definitions
- **States** — Hover, active, disabled, error states

---

## Tests First

### Unit Tests

**Test: CSS custom properties defined**
- Verify `frontend/styles/tokens.css` has all token definitions.
- Verify tokens use `--` prefix.
- Verify no hard-coded values in components.

**Test: Token values consistent**
- Verify colors are valid hex/rgb.
- Verify spacing uses 4px base unit.
- Verify font sizes are reasonable.

### Integration Tests

**Test: Shadow DOM style isolation**
- Verify tokens imported in Shadow DOM do not leak to page.
- Verify page styles do not override Shadow DOM tokens.

---

## Implementation Boundaries

### Allowed Changes

- **New file:** `frontend/styles/tokens.css`
  - Define all design tokens as CSS custom properties.
  - Include color palette, typography scale, spacing scale, shadows.
  
- **Modify:** `frontend/src/main.jsx` (if needed)
  - Import tokens.css in Shadow DOM style setup.

- **Modify:** `frontend/src/aw-ide-panel.jsx` (if needed)
  - Replace hard-coded colors/spacing with token vars.

- **New tests:** `tests/test_frontend_tokens.py`, `tests/test_frontend_styles.py`

### Forbidden Changes

- No component implementation.
- No logic changes.

---

## Acceptance Criteria

✅ **tokens.css complete** with all design tokens.
✅ **No hard-coded values** in production code.
✅ **Tests green** — token import, isolation, consistency.
✅ **Evidence:** test output, build success.

---

## Evidence Checklist

- [ ] `frontend/styles/tokens.css` created
- [ ] All tokens extracted and defined
- [ ] Build succeeds: `npm run build`
- [ ] Tests pass: `tests/test_frontend_styles.py`
- [ ] No hard-coded colors/spacing in code
- [ ] Story updated with evidence

