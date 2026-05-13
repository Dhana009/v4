# S7-0406 — Unmount, Restore, and Host-Page Cleanup

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0406  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **Cluster 4 Goal** — host-page safety, cleanup guarantee
2. **Architecture rule** — no page state mutations left behind

---

## Objective

Ensure complete cleanup on unmount. All added DOM nodes removed, all page style mutations reversed, all event listeners removed. After unmount, page is exactly as it was before mount.

After S7-0406:
- All host DOM elements removed
- All style mutations (compensation, etc.) reversed
- All event listeners (resize, etc.) removed
- No orphaned styles, nodes, or listeners
- Cleanup tested and verified

---

## Tests First

### Unit Tests

**Test: Full cleanup sequence**
- Mount host, apply compensation, attach listeners
- Call cleanup
- Verify: no `aw-shadow-host` in DOM
- Verify: no resize listeners attached
- Verify: page width/height restored
- Verify: no pending promises/timers

**Test: Cleanup removes all host nodes**
- Mount, add test content to host
- Cleanup
- Verify: host element removed
- Verify: no orphaned child nodes

**Test: Cleanup reverses compensation**
- Apply compensation (body width reduced)
- Cleanup
- Verify: body width restored to original

**Test: Cleanup removes listeners**
- Attach resize listener
- Cleanup
- Verify: listener not called on window resize

**Test: Cleanup removes styles**
- Add `aw-shadow-style` marker or style elements
- Cleanup
- Verify: all marker styles removed

### Contract Tests

**Test: Cleanup completeness**
- Cleanup function ensures:
  - DOM nodes removed
  - Styles restored
  - Listeners removed
  - No memory leaks
- Verification function available for testing

### Integration Tests

**Test: Page usable after cleanup**
- Mount AutoWorkbench
- Interact with page
- Unmount
- Verify: page fully interactive again
- Can click, scroll, input normally

**Test: Remount after cleanup**
- Mount, unmount, mount again
- Second mount succeeds
- No conflicts with first unmount

### Negative Tests

**Test: Cleanup without prior mount**
- Call cleanup without mounting
- Handled safely (noop)

**Test: Cleanup with partial state**
- Mount but don't apply compensation
- Cleanup
- Handled safely

---

## Implementation Boundaries

### Allowed Changes

- **New module or extend:** `frontend/src/host/cleanup.js`
  - Export: `cleanupHost()`, `verifyCleanup()`
  - Coordinates cleanup from all submodules (host, compensation, listeners)
  - Max 150 lines

- **Modify:** host, compensation, and resize modules to export cleanup functions

- **Modify:** main.jsx (wiring only)

- **New tests:** `tests/test_cleanup_verification.py`

### Forbidden Changes

- No broad refactor

---

## Acceptance Criteria

✅ **Cleanup complete:**
- All host nodes removed
- All compensation reversed
- All listeners removed
- Page state restored

✅ **Verification available:**
- Test-friendly function to verify cleanup
- Can be called from test suite

✅ **Tests passing:**
- Unit, integration, negative tests green
- Regression baseline maintained

✅ **Evidence:**
- Test output shows cleanup verification passing
- Page state identical before/after unmount

---

## Stop Conditions

- ❌ Orphaned DOM nodes after cleanup
- ❌ Compensation not reversed
- ❌ Listeners not removed
- ❌ Cleanup function not exported for testing

---

## Related

- Prerequisite: S7-0401, S7-0405 (compensation)
- Depended on by: S7-0407 (style isolation)

---

## Next Story

→ S7-0407: Shadow DOM style isolation and host-page safety

---

## Evidence Recorded

**Status:** Done  
**Implementation commit:** `2a6eed4`  
**Test commit:** `e8b98f7`  
**Branch:** `s7/cluster-4-docked-shadow-dom-host`

### Tests

| Test File | Tests | Result |
|---|---|---|
| test_host_cleanup.py | 9 | ✅ Pass |

### Validation

- `python -m pytest -q` → **2247 passed, 1 skipped, 0 failed** ✅
- `npm run build` → **1.2 MB bundle, 42.9 KB CSS** ✅
- All module boundary checks: no backend imports ✅
- No DEMO_/MOCK_ constants ✅
