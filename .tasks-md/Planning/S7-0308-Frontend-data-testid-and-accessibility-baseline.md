# S7-0308 Frontend Data-TestID and Accessibility Baseline

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0308  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Define and implement stable `data-testid` attributes and ARIA labels for all interactive controls. Make components accessible and testable.

---

## Data-TestID Convention

Naming pattern: `{component}-{element}-{action | state}`

Examples:
- `plan-card-accept-button` — Accept button on plan card
- `clarification-card-input` — Input field in clarification card
- `steps-panel-add-step-button` — Add step button
- `locator-candidates-select-button` — Select button for candidate
- `recovery-card-retry-button` — Retry action
- `code-panel-copy-button` — Copy code button
- `trace-panel-filter-input` — Filter input
- `tab-bar-llm-tab` — LLM tab selector

---

## Accessibility Requirements

- All buttons have text or aria-label.
- All form inputs have associated labels.
- Focus styles visible on all interactive controls.
- Color contrast ≥ 4.5:1 for text.
- Keyboard navigation works (Tab, Enter, Escape).
- Screen reader friendly (semantic HTML, ARIA).

---

## Tests First

### Structure Tests

**Test: data-testid presence**
- Grep for all interactive elements without data-testid.
- Report: elements missing testids.
- Verify all buttons, inputs, clickable elements have testids.

**Test: data-testid uniqueness**
- Verify no duplicate testids in same component.
- Verify testids follow naming convention.

### Accessibility Tests

**Test: ARIA labels**
- Verify all buttons have text or aria-label.
- Verify no unlabeled icon-only buttons.

**Test: Label associations**
- Verify form inputs have `<label for="id">` or aria-label.
- Verify inputs have id attribute.

**Test: Focus styles**
- Verify focus pseudo-class defined for all focusable elements.
- Verify focus not hidden (outline:0 without replacement).

**Test: Color contrast**
- Verify text color contrast ≥ 4.5:1.
- Check against both light and dark backgrounds.

**Test: Keyboard navigation**
- Verify buttons respond to Enter.
- Verify inputs respond to Tab.
- Verify dialogs close on Escape.

---

## Implementation Boundaries

### Allowed Changes

- **Add data-testid** to all interactive elements in components.
- **Add aria-label** to buttons, inputs, and icons.
- **Add focus styles** to all focusable elements.
- **Add label elements** for form inputs.
- **Create tests:** `tests/test_frontend_a11y.py`

### Forbidden Changes

- No functionality changes.
- No visual overhaul.

---

## Acceptance Criteria

✅ **All testids added** — Interactive elements have stable testids.
✅ **All ARIA labels** — Buttons and inputs properly labeled.
✅ **Focus styles visible** — Tab navigation shows focus.
✅ **Keyboard navigation works** — Enter, Tab, Escape respond.
✅ **Color contrast OK** — Text readable on all backgrounds.
✅ **Tests pass** — Accessibility audit passes.
✅ **Evidence:** grep output, test results, accessibility audit report.

---

## Evidence Checklist

- [ ] data-testid added to all interactive elements
- [ ] ARIA labels added to buttons/inputs
- [ ] Focus styles defined and visible
- [ ] Keyboard navigation tested
- [ ] Color contrast verified
- [ ] Accessibility tests pass: `tests/test_frontend_a11y.py`
- [ ] Build succeeds: `npm run build`
- [ ] Story updated with evidence

