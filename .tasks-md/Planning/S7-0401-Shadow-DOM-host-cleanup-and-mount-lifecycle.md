# S7-0401 — Shadow DOM Host Cleanup and Mount Lifecycle

**Sprint:** Sprint 7  
**Cluster:** 4  
**Story:** S7-0401  
**Status:** Done  
**Date:** 2026-05-13  

---

## Source Rules

1. **PRD v2.3** — `03_FRONTEND_RUNTIME.md` — Shadow DOM host architecture
2. **Frontend UI Spec** — Section 4.3–4.5 — Shadow DOM host requirements and testability
3. **Sprint 7 Governance** — modular architecture, test-first, no monolith expansion
4. **Cluster 4 Goal** — reliable, testable, isolated host lifecycle

---

## Objective

Create a focused Shadow DOM host module that manages mount/unmount lifecycle reliably. The host should be idempotent (repeated mount is safe), cleanly unmount without leaving orphaned nodes, and expose stable test data-testid selectors.

After S7-0401:
- Shadow DOM host created as separate module (`frontend/src/host/`)
- Mount creates `aw-shadow-host` and `aw-shadow-mount` elements safely
- Repeated mount is idempotent (no duplicates)
- Unmount removes all added nodes and restores original state
- Test hooks available for all important elements
- Lifecycle tested without browser execution

---

## Current Context

- `frontend/src/main.jsx` has constant definitions for host IDs
- Host lifecycle exists but incomplete and monolithic
- No separate host module
- No idempotency guarantee
- No cleanup contract

---

## Tests First

### Unit Tests

**Test: Host module imports and exports correctly**
- Verify `frontend/src/host/` module exists
- Verify exports: `createHost()`, `mountHost()`, `unmountHost()`, `getHostRoot()`
- All functions are named functions, not arrow functions (for better debugging)

**Test: Mount creates correct DOM structure**
- Call `mountHost(document.body)` with clean document
- Verify `aw-shadow-host` div created as child of body
- Verify `aw-shadow-host` has Shadow DOM root
- Verify `aw-shadow-mount` div created inside Shadow DOM
- Verify `aw-shadow-mount` has data-testid="aw-shadow-mount"

**Test: Mount is idempotent**
- Call `mountHost(document.body)` twice
- Verify second call returns same host root (no duplicate created)
- Verify only one `aw-shadow-host` in document
- Verify no error thrown

**Test: Unmount removes host and restores DOM**
- Call `mountHost(document.body)`
- Verify host created
- Call `unmountHost()`
- Verify `aw-shadow-host` element removed from DOM
- Verify document.body reverted to initial state

**Test: Get host root after mount**
- Call `mountHost(document.body)`
- Call `getHostRoot()`
- Verify returns Shadow DOM root, not null
- Verify root is DOM element

**Test: Get host root before mount**
- Call `getHostRoot()` without mount
- Verify returns null (not error)

**Test: Unmount without prior mount**
- Call `unmountHost()` with no prior mount
- Verify no error thrown (safe)

**Test: Host styles not in global scope**
- Mount host
- Verify host element has `data-autoworkbench-shadow-style` marker
- Verify Shadow DOM root has isolated style scope (no style leakage)

### Contract Tests

**Test: Host container contract**
- Mount returns object with:
  - `shadowRoot` (DOM ShadowRoot)
  - `mountPoint` (DOM HTMLElement for aw-shadow-mount)
  - `hostElement` (DOM HTMLElement for aw-shadow-host)
- All properties exist and are correct DOM types

**Test: Mount options contract**
- `mountHost(target, options)` accepts optional options:
  - `zIndex` (default 10000)
  - `containerId` (default 'aw-shadow-host')
  - `mountId` (default 'aw-shadow-mount')
- Options stored in host metadata for testing

### Integration Tests

**Test: Host lifecycle in real DOM**
- Start with clean document
- Mount host
- Add content to mount point
- Verify content visible in Shadow DOM
- Unmount host
- Verify content removed
- Verify document clean

**Test: Repeated mount/unmount cycle**
- Mount, unmount, mount, unmount (4 cycles)
- Verify no memory leaks or orphaned nodes
- Verify each cycle succeeds

### Negative Tests

**Test: Null target**
- Call `mountHost(null)`
- Verify error logged or null returned (not crash)

**Test: Target element removed**
- Mount host to element
- Remove target element from DOM
- Verify host unmount safe (no error)

**Test: Shadow DOM already exists**
- Create Shadow DOM on body manually
- Call `mountHost(document.body)`
- Verify either: reuses existing shadow root OR creates new element with separate shadow
- Verify contract clear

**Test: Mount point already has content**
- Add DOM content to body
- Mount host
- Verify existing content not affected
- Verify host mounted as separate subtree

### Regression Tests

**Test: Sprint 6 tests still pass**
- Run `pytest tests/test_frontend*.py -q` on relevant existing tests
- Verify no new failures in frontend contract tests

---

## Implementation Boundaries

### Allowed Changes

- **New module:** `frontend/src/host/index.js` or `frontend/src/host/host.js`
  - Export: `createHost(target, options)` — create but don't mount
  - Export: `mountHost(target, options)` — create and mount
  - Export: `unmountHost()` — remove host from DOM
  - Export: `getHostRoot()` — get current Shadow DOM root
  - Export: `getHostContainer()` — get host element
  - Max 200 lines

- **Modify:** `frontend/src/main.jsx` (thin wiring only, ≤5 lines)
  - Remove inline host logic
  - Import and call `mountHost()` from new module
  - Call `unmountHost()` on cleanup

- **New tests:** `tests/test_frontend_shadow_dom_contract.py`
  - All tests listed above
  - No browser execution in unit/contract tests
  - Jest/vitest for JS unit tests if preferred

### Forbidden Changes

- No backend/ or runtime/ implementation
- No layout logic in host module (defer to S7-0402)
- No page compensation in host module (defer to S7-0405)
- No broad refactor of main.jsx
- No product UI components in host module

---

## Acceptance Criteria

✅ **Host module created:**
- File: `frontend/src/host/` (or `frontend/src/host.js`)
- Exports: `createHost`, `mountHost`, `unmountHost`, `getHostRoot`, `getHostContainer`

✅ **All tests green:**
- Unit tests: mount, unmount, idempotency, test hooks
- Contract tests: return value shapes correct
- Integration tests: lifecycle works in real DOM
- Negative tests: null/missing input handled safely
- Regression: Sprint 6 tests still pass

✅ **Idempotency verified:**
- Repeated mount does not create duplicate hosts
- Test confirms this behavior

✅ **Cleanup complete:**
- Unmount removes all added nodes
- No orphaned elements left in DOM
- Original page state restored

✅ **Modularization:**
- Host logic separated from main.jsx
- main.jsx ≤5 lines of wiring
- Host module ≤200 lines

✅ **Evidence:**
- Test file name: `tests/test_frontend_shadow_dom_contract.py`
- Implementation file: `frontend/src/host/index.js` or similar
- Commit messages: test commit + implementation commit
- Regression output: `pytest tests/test_frontend*.py -q` green

---

## Evidence Checklist

- [ ] `frontend/src/host/` module created or `frontend/src/host.js` file added
- [ ] `tests/test_frontend_shadow_dom_contract.py` created with all unit/contract/integration/negative tests
- [ ] All tests passing (green)
- [ ] Host exports: `createHost`, `mountHost`, `unmountHost`, `getHostRoot`, `getHostContainer`
- [ ] `frontend/src/main.jsx` modified to import and use host module (≤5 lines added/changed)
- [ ] Idempotency test passes (repeated mount safe)
- [ ] Cleanup test passes (unmount restores DOM)
- [ ] Regression guard green: `python -m pytest -q --ignore=tests/e2e` baseline maintained
- [ ] Story updated with commit hashes and test evidence

---

## Stop Conditions

- ❌ Repeated mount creates duplicate `aw-shadow-host` elements
- ❌ Unmount leaves orphaned nodes in DOM
- ❌ Calling unmount without prior mount throws error
- ❌ Host lifecycle logic remains in main.jsx (not extracted to module)
- ❌ Host module exceeds 200 lines
- ❌ New test failures in regression suite

---

## Related Issues

- BUG-S6-FINAL-002: Frontend contract-only; S7-0401 starts real implementation
- Cluster 4 prerequisite for all other layout/compensation stories

---

## Next Story

→ S7-0402: Dock right/left/top/bottom layout modes

---

## Evidence Recorded

**Status:** Done  
**Implementation commit:** `2a6eed4`  
**Test commit:** `e8b98f7`  
**Branch:** `s7/cluster-4-docked-shadow-dom-host`

### Tests

| Test File | Tests | Result |
|---|---|---|
| test_shadow_dom_host.py | 17 | ✅ Pass |

### Validation

- `python -m pytest -q` → **2247 passed, 1 skipped, 0 failed** ✅
- `npm run build` → **1.2 MB bundle, 42.9 KB CSS** ✅
- All module boundary checks: no backend imports ✅
- No DEMO_/MOCK_ constants ✅
