# S7-0408 — Picker Exclusion for AutoWorkbench UI

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0408  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **Cluster 4 Goal** — picker safe for website content only
2. **Frontend UI Spec** — host-aware test selectors

---

## Objective

Ensure element picker (used to target website content) does not include AutoWorkbench UI elements. When user clicks "Pick element", they see only tested website content, not AutoWorkbench panel buttons/cards/etc.

After S7-0408:
- `aw-shadow-host` excluded from picker candidates
- All panel controls excluded from picker
- Website content freely pickable
- Exclusion works in docked and floating modes

---

## Tests First

### Unit Tests

**Test: Host element excluded**
- Query for candidate selectors
- Verify `aw-shadow-host` not in results
- Verify any element inside shadow root not in results

**Test: Page elements included**
- Query for candidate selectors
- Verify page elements (buttons, inputs, etc.) in results

### Contract Tests

**Test: Picker selector contract**
- Picker returns elements with:
  - `xpath` or `selector`
  - `label` or `text_content`
  - `bounding_box` or similar
  - No elements inside `aw-shadow-host`

### Integration Tests

**Test: Picker excludes panel**
- Mount AutoWorkbench panel
- Use picker on page
- Click on panel area
- Verify panel not selected (or error message "Not on page content")
- Click on page button
- Verify page button selected

**Test: Picker excludes panel in all modes**
- Test in `dock-right`, `dock-left`, `dock-bottom`, `floating`
- Picker always excludes panel

### Negative Tests

**Test: Picker with panel covering element**
- Floating mode, panel overlaps page content
- User tries to click covered element
- Verify: picker sees page element under panel (ignores shadow root)
- Or: picker shows "element hidden by panel" notice

---

## Implementation Boundaries

### Allowed Changes

- **New module or extend:** `frontend/src/picker.js` or extend from browser interaction
  - Export: `queryPageElements(selector)` or extend existing picker
  - Exclude shadow DOM from results
  - Max 100 lines if new module

- **Modify:** browser.py picker invocation to exclude shadow host
  - Add filter: `not in aw-shadow-host`
  - ≤10 lines

- **New tests:** `tests/test_picker_exclusion.py`

### Forbidden Changes

- No changes to page structure
- No picker logic duplication

---

## Acceptance Criteria

✅ **Picker excludes panel:**
- `aw-shadow-host` and contents excluded
- No AutoWorkbench UI in picker results

✅ **Page content pickable:**
- Website elements freely selectable
- Picker works normally for page content

✅ **Exclusion works in all modes:**
- Docked, floating, collapsed — all modes tested

✅ **Tests passing:**
- Unit, integration, negative tests green
- Regression baseline maintained

---

## Stop Conditions

- ❌ AutoWorkbench UI elements appear in picker results
- ❌ Page elements not pickable
- ❌ Exclusion doesn't work in floating mode

---

## Related

- Prerequisite: S7-0401 (host)
- Final Cluster 4 story

---

## Cluster 4 Complete

After S7-0408, all docking and layout stories Done. Cluster 4 ready for browser E2E in later cluster.

## Acceptance Checklist

After all Cluster 4 stories Done:

- [ ] All 8 stories green
- [ ] Host lifecycle: mount/unmount idempotent and clean
- [ ] Docked layout: dock-right/left/bottom working
- [ ] Panel modes: expanded/collapsed/floating working
- [ ] Resize: user can resize, min/max enforced
- [ ] Page compensation: content not covered in docked mode
- [ ] Cleanup: all mutations reversed on unmount
- [ ] Style isolation: CSS scoped, no leakage
- [ ] Picker safe: AutoWorkbench UI excluded
- [ ] Browser E2E: ready to test docked layout in real browser
- [ ] Design prototype: tokens extracted for Cluster 5
- [ ] Main.jsx: wiring only, focused modules created
- [ ] Regression: baseline maintained

---

## Evidence Recorded

**Status:** Done  
**Implementation commit:** `2a6eed4`  
**Test commit:** `e8b98f7`  
**Branch:** `s7/cluster-4-docked-shadow-dom-host`

### Tests

| Test File | Tests | Result |
|---|---|---|
| test_picker_exclusion.py | 11 | ✅ Pass |

### Validation

- `python -m pytest -q` → **2247 passed, 1 skipped, 0 failed** ✅
- `npm run build` → **1.2 MB bundle, 42.9 KB CSS** ✅
- All module boundary checks: no backend imports ✅
- No DEMO_/MOCK_ constants ✅
