# S7-0402 — Dock right/left/top/bottom layout

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0402  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `03_FRONTEND_RUNTIME.md` — docked panel architecture
2. **Frontend UI Spec** — docked layout rules (right/left/bottom)
3. **Cluster 4 Goal** — real docked behavior, page not covered
4. **Design prototype** — `frontend_new_design_prototype/` — layout reference

---

## Objective

Implement dock mode controller that applies CSS classes and styles based on selected dock position. The panel should dock to right (default), left, top, or bottom. User can select dock mode, and panel layout changes immediately. Page content area compensation applied by S7-0405.

After S7-0402:
- Dock modes: `dock-right`, `dock-left`, `dock-bottom`
- Mode persists (localStorage or session)
- CSS classes applied to host element
- Default is `dock-right`
- Dock controls available in UI (buttons or menu)
- Mode changes immediately (no refresh)

---

## Current Context

- Main.jsx has hardcoded defaults
- No dock mode selection UI
- No CSS class application logic
- No localStorage persistence

---

## Tests First

### Unit Tests

**Test: Dock mode state and persistence**
- `setDockMode('dock-right')` → saved and retrievable
- `setDockMode('dock-left')` → saved and retrievable
- `setDockMode('dock-bottom')` → saved and retrievable
- `getDockMode()` returns current mode
- Invalid mode rejected safely

**Test: CSS class application**
- Set mode to `dock-right` → host element has class `aw-dock-right`
- Set mode to `dock-left` → host element has class `aw-dock-left` (and not `aw-dock-right`)
- Set mode to `dock-bottom` → host element has class `aw-dock-bottom`
- Only one dock-* class present at a time

**Test: Default mode**
- First call without prior mode → `dock-right` selected
- Subsequent calls → persisted mode returned

**Test: Mode change**
- Start with `dock-right`
- Call `setDockMode('dock-left')`
- Verify host element classes updated
- Verify new mode persisted

### Contract Tests

**Test: Dock mode options**
- Valid modes: `['dock-right', 'dock-left', 'dock-bottom']`
- Mode type: string
- Invalid modes rejected or fall back to default

**Test: CSS class contract**
- Host element receives `aw-dock-{mode}` class
- Class added by docking controller
- Class removal tested

### Integration Tests

**Test: Mode change updates layout immediately**
- Mount host, set mode to `dock-left`
- Verify `aw-dock-left` class present
- No refresh required

**Test: Mode persists across remount**
- Set mode to `dock-bottom`
- Unmount and remount host
- Verify mode still `dock-bottom`

### Negative Tests

**Test: Invalid mode**
- `setDockMode('invalid-mode')`
- Verify error logged or mode unchanged
- UI still functional

**Test: Null mode**
- `setDockMode(null)`
- Verify handled safely (not crash)

---

## Implementation Boundaries

### Allowed Changes

- **New module:** `frontend/src/layout/dock.js` or `frontend/src/dock.js`
  - Export: `setDockMode(mode)` — set dock mode
  - Export: `getDockMode()` — get current mode
  - Export: `DOCK_MODES` — valid mode list
  - Max 150 lines

- **CSS:** `frontend/src/styles/dock.css` or embedded
  - Define `.aw-dock-right`, `.aw-dock-left`, `.aw-dock-bottom` classes
  - Basic layout only (positioning deferred to component CSS)

- **Modify:** `frontend/src/main.jsx` (wiring only, ≤5 lines)

- **New tests:** `tests/test_dock_mode.py`

### Forbidden Changes

- No page compensation logic (S7-0405)
- No resize logic (S7-0404)
- No floating/collapsed mode (S7-0403)
- No broad main.jsx refactor

---

## Acceptance Criteria

✅ **Dock modes implemented:**
- `dock-right` (default)
- `dock-left`
- `dock-bottom`
- Invalid modes rejected safely

✅ **CSS classes applied:**
- `aw-dock-right`, `aw-dock-left`, `aw-dock-bottom` classes correct
- Only one dock-* class at a time

✅ **Persistence working:**
- Mode saved to localStorage or session
- Mode restored on page reload

✅ **All tests green:**
- Unit, contract, integration, negative tests passing
- Regression suite baseline maintained

✅ **Modularization:**
- Dock logic in focused module
- main.jsx wiring only
- CSS separated or scoped

✅ **Evidence:**
- Test file: `tests/test_dock_mode.py`
- Implementation: `frontend/src/dock.js` or `frontend/src/layout/dock.js`
- Commits: test + implementation

---

## Stop Conditions

- ❌ Invalid dock mode not rejected
- ❌ CSS classes not applied to host
- ❌ Mode persists incorrectly
- ❌ Mode change requires page refresh
- ❌ Dock module exceeds 150 lines
- ❌ Regression suite breaks

---

## Related

- Prerequisite: S7-0401 (host module)
- Depended on by: S7-0404 (resize), S7-0405 (compensation)

---

## Next Story

→ S7-0403: Floating, collapsed, and expanded panel modes
