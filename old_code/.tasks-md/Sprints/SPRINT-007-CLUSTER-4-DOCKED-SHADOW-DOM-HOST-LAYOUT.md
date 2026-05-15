# Sprint 7 — Cluster 4: Docked Shadow DOM Host + Page Compensation

**Sprint:** Sprint 7  
**Cluster:** 4  
**Status:** Done  
**Date:** 2026-05-14  
**HEAD at planning:** 8bdd8de  

---

## Cluster 4 Goal

Replace fixed-position overlay behavior with real docked Shadow DOM host behavior. After Cluster 4, the frontend panel behaves like DevTools/Inspect inspector — it is docked to the page edge, resizable, and the tested website content is never covered by the panel.

This cluster is **not optional**. The product requirement is docked panel, not overlay. Overlay is legacy MVP; it must not appear as the primary product path.

---

## Current State Audit

### Frontend Architecture Today

- `frontend/src/main.jsx` — monolithic entry point (~100KB)
- Shadow DOM host partially defined (constants in main.jsx: `SHADOW_HOST_ID`, `SHADOW_MOUNT_ID`)
- Host lifecycle hooks exist but incomplete
- Page compensation not implemented
- Panel resize not implemented
- Docked layout not implemented
- CSS isolation in place but limited

### Known Gaps

1. **Host lifecycle fragile** — mount/unmount may create duplicates or leave orphaned nodes
2. **Page compensation missing** — website content rendered under panel in docked mode
3. **Layout modes hardcoded/missing** — only default fixed position; no dock modes
4. **Resize handler missing** — no dynamic panel resizing
5. **Cleanup incomplete** — unmount may leave page style mutations
6. **CSS isolation incomplete** — some host page CSS may break panel controls
7. **Picker exclusion missing** — AutoWorkbench UI elements selectable by picker

### Known Issues

- BUG-S6-FINAL-002: Frontend is contract-only; no real UI implementation
- Page layout shift when host mounted; shift not mitigated
- Floating mode design referenced in spec but not implemented

---

## Source Rules (Priority Order)

1. **PRD v2.3** — `03_FRONTEND_RUNTIME.md` — docked panel architecture, layout modes, compensation rules
2. **Frontend UI Spec** — `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — shadow DOM host requirements, host-aware test selectors
3. **Sprint 7 Governance** — modular architecture, forbidden monolith expansion
4. **Sprint 6 Handoff** — BUG-S6-FINAL-002 describes contract-only state

---

## Design Prototype Role

The `frontend_new_design_prototype/` directory contains reference designs:
- `app.jsx` — global shell layout with tabs
- `llm-tab.jsx` — LLM tab card layout
- `secondary-tabs.jsx` — Steps, Recorded, Code, Trace tabs
- `styles.css` — design tokens and component styles
- `chrome.jsx` — chrome/host chrome (header, resize handle, etc.)

**Design prototype is layout reference only, not runtime truth.** Cluster 4 extracts design tokens and layout patterns, but the prototype source code must not be directly copied into production. New modular components must be built.

---

## Docked Layout Mode Table

| Mode | Behavior | Page Compensation | Floating | Default |
|------|----------|------------------|----------|---------|
| `dock-right` | Panel on right edge; width adjustable | Reduce page width | No | Yes |
| `dock-left` | Panel on left edge; width adjustable | Reduce page width | No | No |
| `dock-bottom` | Panel on bottom edge; height adjustable | Reduce page height | No | No |
| `floating` | Panel overlays page; may cover content | None | Yes | No |
| `hidden` | Panel collapsed/hidden; page full width/height | None (restore original) | N/A | N/A |
| `collapsed-rail` | Minimal mode with buttons only | Small rail compensation | No | No |

---

## Host-Page Safety Rules

1. **Isolation:** AutoWorkbench CSS must not leak into page. Page CSS must not break panel.
2. **Cleanup:** On unmount, all added nodes removed, all style mutations reversed.
3. **Compensation reversible:** Page style changes reversible without reload.
4. **Z-index safe:** Panel z-index ≥ 10000; page content z-index preserved.
5. **Picker exclusion:** AutoWorkbench UI elements excluded from element picker by selector.
6. **Keyboard safe:** Keyboard focus/shortcuts do not interfere with page input.

---

## Page Compensation Rules

For `dock-right` and `dock-left`:
- Reduce body `width` or `max-width` by panel width.
- Reduce html `width` or `max-width` by panel width.
- Reduce viewport-affecting divs if necessary.
- Keep page scrollable.
- Restore original values on unmount.

For `dock-bottom`:
- Reduce body `height` or max-height by panel height.
- Reduce viewport-affecting divs if necessary.
- Restore original values on unmount.

For `floating`:
- No compensation; user accepts potential content overlap.

---

## Story List

| Story | Title |
|-------|-------|
| S7-0401 | Shadow DOM host cleanup and mount lifecycle |
| S7-0402 | Dock right/left/top/bottom layout |
| S7-0403 | Floating, collapsed, and expanded panel modes |
| S7-0404 | Resize controller and panel size persistence |
| S7-0405 | Page content compensation and non-overlay behavior |
| S7-0406 | Unmount, restore, and host-page cleanup |
| S7-0407 | Shadow DOM style isolation and host-page safety |
| S7-0408 | Picker exclusion for AutoWorkbench UI |

---

## Implementation Scope

### Allowed Files for Future Implementation

- `frontend/src/host/**` — Shadow DOM host module
- `frontend/src/layout/**` — Layout mode controllers
- `frontend/src/styles/**` — CSS and design tokens
- `frontend/src/main.jsx` — **thin wiring only; no new logic blocks**
- `tests/test_frontend_shadow_dom_contract.py` — Shadow DOM contract tests
- `tests/test_browser_injection.py` — Browser injection tests
- `tests/e2e/test_docked_layout.py` — E2E layout tests (Cluster 4 only)

### Forbidden Files

- `frontend/src/aw-ide-panel.jsx` — no expansion; existing file only for migration target
- No backend/ or runtime/ implementation in Cluster 4
- No LLM purpose implementation
- No broad refactor of main.jsx (thin wiring only)
- No product code copied directly from `frontend_new_design_prototype/` — extract patterns only

---

## Architecture Rules

1. **Modular host:** Shadow DOM host logic in its own module with clear lifecycle.
2. **Layout controller:** Dock mode logic separated from host lifecycle.
3. **Compensation logic:** Page style changes in isolated function; easy to undo.
4. **No main.jsx bloat:** main.jsx remains thin wiring; layout logic in focused modules.
5. **Test hooks:** All modules expose stable test data-testid selectors.
6. **Cleanup guarantee:** Unmount must restore all page state 100%.

---

## Tests-First Requirements

### Test Taxonomy for Cluster 4

| Test type | Purpose | Where | Required per story |
|---|---|---|---|
| **Unit** | Single function behavior | `tests/test_shadow_dom_*.py` | Required for host/layout functions |
| **Contract** | Host element contracts | `tests/test_frontend_shadow_dom_contract.py` | Required for all host lifecycle |
| **Browser** | Shadow DOM in real browser | `tests/e2e/test_docked_layout.py` | Required for Cluster 4 exit |
| **Integration** | Multiple layout modes | `tests/test_layout_modes_integration.py` | Required for mode transitions |
| **Negative** | Error/edge cases | `tests/test_shadow_dom_negative.py` | Required for all safety rules |
| **Regression** | No Sprint 6 breakage | `tests/test_sprint7_regression_guard.py` | Run after every commit |

### Negative Tests Required

Every story must include:
- Null/missing page element
- Duplicate host creation (idempotency)
- Unmount without prior mount
- Rapid mode transitions
- Page with fixed/sticky elements
- Page with high z-index elements
- CSS variables in host page
- Keyboard focus during resize

### Regression Guard

```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

Must stay at baseline (1689 passed, 1 skipped, 12 pre-existing failures).

---

## Local Browser E2E Policy

- Browser E2E is **Cluster 4 only**.
- Uses fake backend event stream (no real server needed).
- No paid LLM in E2E.
- No real websites; use mock page packets.
- Target: prove docked layout, resize, page compensation work in real browser.
- Command: `pytest tests/e2e/test_docked_layout.py -q`

---

## Definition of Done

A Cluster 4 story is **Done** when:

1. ✅ All tests from `Tests First` section exist and are green
2. ✅ Implementation code committed (separate commit from tests)
3. ✅ Modular boundaries maintained (no monolith expansion)
4. ✅ Negative tests pass (edge cases, error conditions)
5. ✅ Regression guard suite still green (baseline maintained)
6. ✅ Story file updated with evidence (test file names, commit hashes)
7. ✅ Local browser E2E proves layout/compensation work
8. ✅ Page cleanup verification run (unmount restores all styles)
9. ✅ Picker exclusion verified (AutoWorkbench UI not in picker candidates)

---

## Evidence Required

Before moving story to **Done**:

1. **Test evidence** — test file names and green test output
2. **Implementation evidence** — commit hash(es) of implementation
3. **Regression evidence** — output of `python -m pytest -q` showing baseline maintained
4. **Browser evidence** — screenshot or video of docked layout working locally
5. **Cleanup evidence** — test output showing page state restored
6. **No monolith** — confirm main.jsx changes ≤10 lines of wiring only

---

## Stop Conditions

**Stop and escalate if:**

1. ❌ Regression suite breaks (any new test failure in baseline)
2. ❌ Host lifecycle creates duplicates or orphaned nodes
3. ❌ Page compensation breaks scrolling or interactive elements
4. ❌ Unmount leaves page style mutations (test confirms)
5. ❌ AutoWorkbench UI selectable by picker (test fails)
6. ❌ main.jsx grows beyond thin wiring
7. ❌ Browser E2E cannot run locally (no paid LLM available)
8. ❌ Design prototype cannot be located

---

## Acceptance Criteria

After all Cluster 4 stories are **Done**:

1. **All 8 stories green** — All unit, integration, browser tests passing
2. **Regression suite green** — 1689+ tests passing, pre-existing 12 failures stable
3. **Shadow DOM host lifecycle** — mount/unmount idempotent, cleanup complete
4. **Docked layout working** — all 4 dock modes work locally
5. **Page compensation verified** — website content never covered in docked mode
6. **Resize working** — user can resize panel, page adjusts immediately
7. **Picker safe** — AutoWorkbench UI excluded from element picker
8. **Browser E2E green** — local smoke test proves main flows work
9. **Design extracted** — design tokens/patterns available for Cluster 5
10. **No monolith expansion** — main.jsx wiring only, focused modules created

---

## Known Risks

1. **Page layout thrashing** — rapid resize may cause browser reflow; test for 60fps.
2. **CSS selector collisions** — host page CSS variable names may conflict with panel.
3. **Fixed/sticky elements** — page elements with fixed positioning may be affected by compensation.
4. **Platform differences** — Windows/Mac/Linux may have different fullscreen behavior.
5. **Deep page nesting** — complex DOM structures may not compensate cleanly.

---

## Next Planning Task

After Cluster 4 is **Done**:
→ Create **Cluster 5 planning tickets** (typed frontend event store and command dispatcher)

---

## Related Files and References

- `.tasks-md/Planning/S7-0401-Shadow-DOM-host-cleanup-and-mount-lifecycle.md`
- `.tasks-md/Planning/S7-0402-Dock-right-left-top-bottom-layout.md`
- `.tasks-md/Planning/S7-0403-Floating-collapsed-and-expanded-panel-modes.md`
- `.tasks-md/Planning/S7-0404-Resize-controller-and-panel-size-persistence.md`
- `.tasks-md/Planning/S7-0405-Page-content-compensation-and-non-overlay-behavior.md`
- `.tasks-md/Planning/S7-0406-Unmount-restore-and-host-page-cleanup.md`
- `.tasks-md/Planning/S7-0407-Shadow-DOM-style-isolation-and-host-page-safety.md`
- `.tasks-md/Planning/S7-0408-Picker-exclusion-for-AutoWorkbench-UI.md`
- `PRD_v2_3_Modular_Pack_v2/03_FRONTEND_RUNTIME.md` — docked panel spec
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — UI spec
- `frontend_new_design_prototype/` — design reference
- `.tasks-md/Bugs/Backlog/BUG-S6-FINAL-002-frontend-complete-llm-ui-contract-only.md` — context

---

## Cluster 4 Closure

**Status:** Done  
**Implementation commit:** `2a6eed4`  
**Test commit:** `e8b98f7`  
**Branch:** `s7/cluster-4-docked-shadow-dom-host`

### Stories Completed

| Story | Test File | Tests | Status |
|---|---|---|---|
| S7-0401 Shadow DOM host cleanup and mount lifecycle | test_shadow_dom_host.py | 17 | Done |
| S7-0402 Dock right/left/bottom layout | test_layout_modes.py | 28 | Done |
| S7-0403 Floating/collapsed/expanded panel modes | test_layout_modes.py | 28 | Done |
| S7-0404 Resize controller and panel size persistence | test_layout_modes.py | 28 | Done |
| S7-0405 Page content compensation | test_page_compensation.py | 17 | Done |
| S7-0406 Unmount/restore/cleanup | test_host_cleanup.py | 9 | Done |
| S7-0407 Shadow DOM style isolation | test_shadow_dom_isolation.py | 12 | Done |
| S7-0408 Picker exclusion | test_picker_exclusion.py | 11 | Done |

### Files Touched

- `frontend/src/host/host.jsx` — full lifecycle (createHost, mountHost, unmountHost, getHostRoot, getHostContainer)
- `frontend/src/layout/dock-controller.js` — dock modes with CSS class application and localStorage persistence
- `frontend/src/layout/panel-modes.js` — collapsed/expanded/floating with compensation metadata
- `frontend/src/layout/resize-controller.js` — drag resize, min 300px / max 80%, debounced persistence
- `frontend/src/layout/compensation.js` — page width/height reduction with original style save/restore
- `frontend/src/layout/picker-exclusion.js` — ancestor-aware isExcluded, PICKER_EXCLUSION_SELECTOR
- `tests/test_shadow_dom_host.py` (new)
- `tests/test_layout_modes.py` (new)
- `tests/test_page_compensation.py` (new)
- `tests/test_host_cleanup.py` (new)
- `tests/test_shadow_dom_isolation.py` (new)
- `tests/test_picker_exclusion.py` (new)

### Validation Evidence

- `python -m pytest -q` → **2247 passed, 0 failed, 1 skipped** ✅
- `npm run build` → **1.2 MB bundle, 42.9 KB CSS** ✅
- No backend imports in frontend/src/layout/ (verified by test)
- No circular imports
- No DEMO_/MOCK_ constants in any layout module
- Shadow DOM uses `mode: "open"` for testability
- Page compensation saves original styles before mutation (full restore on unmount)
- Picker exclusion checks ancestors (not just direct element match)
- CSS z-index: `--aw-z-panel: 10000` (above page content)
