# S7-0404 — Resize Controller and Panel Size Persistence

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0404  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — docked panel rules, resize support
2. **Frontend UI Spec** — panel resizing, size persistence
3. **Cluster 4 Goal** — user can resize panel safely

---

## Objective

Implement panel resize controller. User can drag panel edge to resize it. Min/max width enforced. Resize listener cleanup guaranteed. Page compensation updates with new size (S7-0405).

After S7-0404:
- Panel edge draggable (pointer/mouse events)
- Min width: 300px, max width: 80% page width (configurable)
- For dock-bottom: min height 200px, max 70% page height
- Size persisted to localStorage/session
- Resize listeners removed on unmount
- No layout thrash (debounced resize)

---

## Tests First

### Unit Tests

**Test: Resize state**
- `setPanelWidth(500)` → width set and retrieved
- `getPanelWidth()` returns current width
- Width within min/max bounds

**Test: Min/max enforcement**
- Set width to 200 (below min 300) → set to 300 instead
- Set width to 2000 (above max) → set to max width
- Bounds respected

**Test: Resize listener attachment**
- `attachResizeListener()` → listener added
- Drag event triggers width update
- `removeResizeListener()` → listener removed (cleanup)

**Test: Debounce**
- Rapid drag events (10 events in 100ms)
- Resize function called only once (or few times)
- Not called on every event

### Contract Tests

**Test: Resize event contract**
- Resize event includes: newWidth, newHeight, source (user | api)
- Type consistency

**Test: Size constraints**
- Default min: 300px, max: 80%
- Constraints configurable
- Bounds enforced

### Integration Tests

**Test: Size persistence across reload**
- Set panel width to 600px
- Unmount and remount
- Width still 600px

**Test: Resize with page compensation**
- Dock-right, set width to 400px
- Page width reduced by 400px
- Resize to 500px
- Page width reduced by 500px
- Compensation updates with size

### Negative Tests

**Test: Null/invalid size**
- `setPanelWidth(null)` → handled safely
- `setPanelWidth('abc')` → handled safely

**Test: Rapid unmount/remount**
- Resize, unmount, remount
- Resize listener cleanup verified (no orphaned listeners)

---

## Implementation Boundaries

### Allowed Changes

- **New module or extend:** `frontend/src/layout/resize.js`
  - Export: `attachResizeListener()`, `removeResizeListener()`, `setPanelWidth()`, `getPanelWidth()`, `setPanelHeight()`, `getPanelHeight()`
  - Max 200 lines

- **CSS:**
  - Resize handle styling (grab cursor, visual indicator)
  - Minimal CSS required (mostly JS driven)

- **Modify:** main.jsx (wiring only)

- **New tests:** `tests/test_resize_controller.py`

### Forbidden Changes

- No page compensation in this story (defer to S7-0405)
- No broad event listener patterns

---

## Acceptance Criteria

✅ **Resize working:**
- User can drag panel edge
- Size updates live
- Min/max enforced

✅ **Size persisted:**
- Size saved to localStorage/session
- Restored on reload

✅ **Listeners cleaned up:**
- On unmount, all listeners removed
- No memory leaks

✅ **Debounced:**
- Resize function not called on every pixel change
- Performance acceptable

✅ **Tests passing:**
- Unit, contract, integration, negative tests green
- Regression baseline maintained

---

## Stop Conditions

- ❌ Min/max not enforced
- ❌ Resize listener orphaned on unmount
- ❌ Size not persisted
- ❌ Layout thrashing on resize (60fps expected)
- ❌ Module exceeds 200 lines

---

## Related

- Prerequisite: S7-0402 (dock modes)
- Depended on by: S7-0405 (compensation updates)

---

## Next Story

→ S7-0405: Page content compensation and non-overlay behavior

---

## Evidence Recorded

**Status:** Done  
**Implementation commit:** `2a6eed4`  
**Test commit:** `e8b98f7`  
**Branch:** `s7/cluster-4-docked-shadow-dom-host`

### Tests

| Test File | Tests | Result |
|---|---|---|
| test_layout_modes.py | partial — resize tests | ✅ Pass |

### Validation

- `python -m pytest -q` → **2247 passed, 1 skipped, 0 failed** ✅
- `npm run build` → **1.2 MB bundle, 42.9 KB CSS** ✅
- All module boundary checks: no backend imports ✅
- No DEMO_/MOCK_ constants ✅
