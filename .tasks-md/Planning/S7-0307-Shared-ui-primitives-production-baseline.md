# S7-0307 Shared UI Primitives Production Baseline

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0307  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Create reusable UI primitives (Button, Card, Badge, etc.) from prototype patterns. No decorative icon overload. Focused, accessible, reusable.

---

## Primitive Inventory

- **Button** — Primary, secondary, danger, disabled states. No icons-only (icons + text).
- **Card** — Container with optional header/footer, padding, shadow.
- **Badge** — Small status indicator (success, warning, error, info colors).
- **StatusPill** — Status label with icon (completed, running, failed).
- **EmptyState** — Empty data message with icon and text.
- **InlineAlert** — Error/warning/info message inline.
- **ActionRow** — Horizontal row of buttons.
- **CodeBlock** — Code display, optional syntax highlighting.
- **TimelineRow** — Single event in timeline.
- **CandidateCard** — Locator candidate with preview.

---

## Tests First

### Component Tests

**Test: Button renders**
- Verify Button renders with text and onClick.
- Verify variants (primary, secondary, danger).
- Verify disabled state.

**Test: Card renders**
- Verify Card renders with children.
- Verify header/footer optional.

**Test: Badge renders**
- Verify Badge renders with label and color variant.

**Test: Accessibility**
- Verify Button has aria-label if icon-only.
- Verify all inputs have associated labels.
- Verify focus styles work.

### Negative Tests

**Test: Icon without text (rejected)**
- Icon-only buttons should have aria-label.
- Verify Button requires either text or aria-label.

---

## Implementation Boundaries

### Allowed Changes

- **Create primitive components** in `frontend/src/components/primitives/`:
  - `Button.jsx`
  - `Card.jsx`
  - `Badge.jsx`
  - `StatusPill.jsx`
  - `EmptyState.jsx`
  - `InlineAlert.jsx`
  - `ActionRow.jsx`
  - `CodeBlock.jsx`
  - `TimelineRow.jsx`
  - `CandidateCard.jsx`

- **Create tests** for each primitive.
- **Use design tokens** for colors, spacing, fonts.

### Forbidden Changes

- No heavy icon decorations.
- No complex animation (focus on clarity).
- No logic beyond rendering.

---

## Acceptance Criteria

✅ **All primitives created** — Button, Card, Badge, etc. rendered.
✅ **Tests pass** — Render, variants, accessibility tests green.
✅ **Tokens used** — Colors, spacing from tokens.css.
✅ **Build succeeds** — `npm run build`.
✅ **Evidence:** component files, test output, build success.

---

## Evidence Checklist

- [ ] Primitive component files created
- [ ] Tests created for each primitive
- [ ] All tests pass
- [ ] Accessibility checks pass
- [ ] Design tokens used
- [ ] Build succeeds: `npm run build`
- [ ] Story updated with evidence

