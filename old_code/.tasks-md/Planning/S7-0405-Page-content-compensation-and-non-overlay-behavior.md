# S7-0405 — Page Content Compensation and Non-Overlay Behavior

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0405  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — page compensation rules
2. **Cluster 4 Goal** — website content never covered in docked mode
3. **Frontend UI Spec** — docked layout rules

---

## Objective

Implement page compensation logic. When panel is docked (not floating), page body/html is resized to prevent content being covered. For dock-right: reduce width. For dock-bottom: reduce height. Compensation updates when panel is resized. Floating mode skips compensation (user accepts overlap).

After S7-0405:
- Dock-right: body width reduced by panel width
- Dock-left: body width reduced by panel width
- Dock-bottom: body height reduced by panel height
- Floating: no compensation
- Compensation updates when resize happens
- Original styles restored on unmount

---

## Current Context

- Page compensation logic missing
- Website content currently covered by panel
- No style restoration mechanism

---

## Tests First

### Unit Tests

**Test: Apply compensation (dock-right)**
- Apply compensation with width 400px for dock-right
- Body width reduced by 400px
- Original width stored for restoration

**Test: Apply compensation (dock-left)**
- Apply compensation with width 400px for dock-left
- Body width reduced by 400px (left side)

**Test: Apply compensation (dock-bottom)**
- Apply compensation with height 300px for dock-bottom
- Body height reduced by 300px
- Original height stored

**Test: Skip compensation (floating)**
- Mode is floating
- Call apply compensation (noop)
- Body width/height unchanged

**Test: Remove compensation**
- Apply compensation
- Remove compensation
- Body width/height restored to original
- Original style attribute restored (if was null, remove attribute)

**Test: Compensation update on resize**
- Apply compensation with 400px
- Update to 500px
- Body width updated (new reduction)

### Contract Tests

**Test: Compensation storage**
- Stores: original width, original height, mode
- Can restore accurately

**Test: CSS property handling**
- If element has inline width style, modifies it
- If element has width in CSS, doesn't break cascade
- Restores to original state

### Integration Tests

**Test: Compensation with real page**
- Load real HTML page with body width 1000px
- Apply compensation with 400px dock-right
- Body width becomes 600px
- Page still scrollable
- Interactive elements still accessible

**Test: Mode change (dock-right to dock-left)**
- Apply compensation dock-right 400px
- Change mode to dock-left
- Compensation recomputed for dock-left
- Result correct

**Test: Mode change (docked to floating)**
- Apply compensation dock-right 400px
- Switch to floating mode
- Compensation removed
- Body width restored to original

**Test: Compensation across resize**
- Start dock-right 400px (body width 600px)
- Resize panel to 500px
- Body width becomes 500px
- Resize back to 400px
- Body width becomes 600px

### Negative Tests

**Test: Page with fixed/sticky elements**
- Page has fixed position divs
- Apply compensation
- Verify fixed elements still visible
- Compensation doesn't break fixed positioning

**Test: Page with max-width constraint**
- Body has `max-width: 900px` in CSS
- Apply compensation 400px
- Compensation respects max-width
- Result is min(600px, 900px) = 600px or similar

**Test: Rapid compensation changes**
- Apply, remove, apply, remove (5 cycles)
- Final state correct (body restored to original)

**Test: Null values**
- Apply compensation with null width
- Handled safely

---

## Implementation Boundaries

### Allowed Changes

- **New module or extend:** `frontend/src/layout/compensation.js`
  - Export: `applyCompensation(mode, width, height)`, `removeCompensation()`, `updateCompensation(width, height)`
  - Max 250 lines

- **CSS:** minimal (no CSS changes needed, mostly JS)

- **Modify:** main.jsx (wiring + integration ≤10 lines)

- **New tests:** `tests/test_page_compensation.py`

### Forbidden Changes

- No page CSS overrides (only inline style changes)
- No breaking page CSS cascade

---

## Acceptance Criteria

✅ **Compensation applied correctly:**
- Dock-right reduces width
- Dock-left reduces width
- Dock-bottom reduces height
- Floating skips compensation

✅ **Compensation removed correctly:**
- Original width/height restored
- Original attributes restored (remove if was null)

✅ **Compensation updates on resize:**
- Panel resizes → compensation updated live
- Page adjusts with new panel size

✅ **Page still functional:**
- Content visible (not covered)
- Page scrollable
- Interactive elements accessible

✅ **Tests passing:**
- Unit, contract, integration, negative tests green
- Regression baseline maintained

---

## Stop Conditions

- ❌ Page content still covered in docked mode
- ❌ Original width/height not restored
- ❌ Fixed/sticky elements broken by compensation
- ❌ Compensation not updated on resize
- ❌ Floating mode applies compensation (should not)
- ❌ Module exceeds 250 lines

---

## Related

- Prerequisite: S7-0402 (dock modes), S7-0404 (resize)
- Depended on by: S7-0406 (cleanup must handle compensation)

---

## Next Story

→ S7-0406: Unmount, restore, and host-page cleanup

---

## Evidence Recorded

**Status:** Done  
**Implementation commit:** `2a6eed4`  
**Test commit:** `e8b98f7`  
**Branch:** `s7/cluster-4-docked-shadow-dom-host`

### Tests

| Test File | Tests | Result |
|---|---|---|
| test_page_compensation.py | 17 | ✅ Pass |

### Validation

- `python -m pytest -q` → **2247 passed, 1 skipped, 0 failed** ✅
- `npm run build` → **1.2 MB bundle, 42.9 KB CSS** ✅
- All module boundary checks: no backend imports ✅
- No DEMO_/MOCK_ constants ✅
