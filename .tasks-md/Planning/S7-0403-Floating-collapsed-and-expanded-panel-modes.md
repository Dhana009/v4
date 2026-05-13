# S7-0403 — Floating, Collapsed, and Expanded Panel Modes

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0403  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — docked panel architecture, floating mode optional
2. **Frontend UI Spec** — layout modes, switching between modes
3. **Cluster 4 Goal** — safe mode switching, no content loss

---

## Objective

Implement panel mode switching: collapsed (minimal rail), expanded (normal), and floating (overlay). User can toggle between modes, and panel state is preserved. Floating mode clearly indicates it may overlap content.

After S7-0403:
- Collapsed mode shows minimal UI (buttons only, no content)
- Expanded mode shows full panel
- Floating mode allows panel to float over page
- Mode preserved when switching (content not lost)
- Visual indicator when in floating mode (user knows content may be covered)
- Floating mode does NOT apply page compensation (S7-0405)

---

## Tests First

### Unit Tests

**Test: Mode state**
- `setMode('expanded')` → mode set and retrieved
- `setMode('collapsed')` → mode set and retrieved
- `setMode('floating')` → mode set and retrieved
- `getMode()` returns current mode

**Test: CSS classes for modes**
- Expanded → `aw-mode-expanded` class
- Collapsed → `aw-mode-collapsed` class
- Floating → `aw-mode-floating` class

**Test: Mode restoration**
- Save mode, close/reopen panel
- Mode persists

**Test: Floating mode compensation disabled**
- Set mode to `floating`
- Verify `aw-no-compensation` class present
- Verify compensation logic skipped

### Contract Tests

**Test: Mode options**
- Valid modes: `['expanded', 'collapsed', 'floating']`
- Invalid modes rejected

**Test: Mode metadata**
- Mode includes: name, label, compensates_page (boolean)
- `floating` has `compensates_page: false`
- `expanded` has `compensates_page: true` (when docked)
- `collapsed` has `compensates_page: true` (minimal)

### Integration Tests

**Test: Mode toggle preserves state**
- Enter expanded mode with plan visible
- Switch to collapsed mode
- Switch back to expanded
- Plan still visible (not lost)

**Test: Floating mode indication**
- Set mode to floating
- Verify visual indicator present (class or attribute)
- User sees "Panel may overlap content" notice or similar

### Negative Tests

**Test: Invalid mode**
- `setMode('invalid')`
- Verify handled safely

**Test: Floating without docking**
- In floating mode, verify compensation disabled
- Page content not pushed aside

---

## Implementation Boundaries

### Allowed Changes

- **New module or extend:** `frontend/src/layout/mode.js`
  - Export: `setMode(mode)`, `getMode()`, `MODE_LIST`
  - Max 150 lines

- **CSS:** classes for modes
  - `.aw-mode-expanded`, `.aw-mode-collapsed`, `.aw-mode-floating`

- **Modify:** main.jsx (wiring only)

- **New tests:** `tests/test_panel_modes.py`

### Forbidden Changes

- No compensation logic (S7-0405)
- No content hiding (modes preserve UI, just layout changes)

---

## Acceptance Criteria

✅ **Modes working:**
- Expanded, collapsed, floating all functional
- Mode changes without page refresh

✅ **Floating mode safe:**
- No compensation applied in floating mode
- User sees clear indication
- Content may overlap without automatic adjustment

✅ **State preservation:**
- Mode persists across panel close/open
- Content visible after mode switch

✅ **Tests passing:**
- Unit, contract, integration, negative tests green
- Regression baseline maintained

---

## Stop Conditions

- ❌ Mode switch causes content loss
- ❌ Floating mode applies compensation (incorrect)
- ❌ Mode not persisted
- ❌ Invalid mode not rejected

---

## Related

- Prerequisite: S7-0402 (dock modes)
- Depended on by: S7-0405 (compensation logic)

---

## Next Story

→ S7-0404: Resize controller and panel size persistence
