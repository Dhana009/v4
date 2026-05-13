# S7-1001 — E2E Harness Update for Docked Shadow DOM

**Sprint:** Sprint 7
**Cluster:** 10
**Tier:** 1 (core)
**Type:** Feature
**Status:** Planning
**Blocks:** [S7-1002, S7-1003, S7-1004, S7-1005, S7-1006, S7-1007, S7-1008, S7-1009, S7-1010]
**Blocked by:** []

---

## Objective

Update the E2E test harness to locate, mount, and interact with the real docked Shadow DOM panel. The current harness assumes overlay behavior and old frontend shape. After S7-1001, the harness can:
- Find `aw-shadow-host` element in the target page
- Interact with UI inside the Shadow DOM
- Apply data-testid selectors through Shadow DOM boundary
- Assert panel docking, visibility, and page accessibility
- Capture screenshots and artifacts
- Safely exclude AutoWorkbench UI from target element selection

---

## Source Rules

- PRD-03-FE-C4-001: Shadow DOM host exists and is docked, not fullscreen overlay
- PRD-03-FE-C4-002: Page content remains accessible; panel docking compensates page area
- PRD-03-FE-C4-003: CSS isolation prevents style bleed
- GOV-S7-C0-007: No source rule → no test; no test → no implementation
- GOV-S7-C10-001 (Cluster 10): E2E harness must support docked Shadow DOM before any flow tests run
- GOV-S7-C10-002: Local-only E2E; no paid APIs; fake LLM only

---

## Current Known Context

### What exists
- `tests/e2e/harness.py` (current: ~2000 lines, assumes overlay model)
- Browser automation via Playwright or similar (inspect existing harness imports)
- Page fixture loading (current harness has fixture file support)
- Screenshot capture capability
- Old event stream polling for test synchronization

### What gaps exist
- No Shadow DOM host detection (`aw-shadow-host`, `aw-shadow-mount` not searched)
- No docked panel bounds calculation (assumes full-screen overlay)
- No page compensation interaction (assumes page unchanged)
- No data-testid piercing through Shadow DOM boundary
- No validation of panel docking (right/left/top/bottom layout)
- No artifact capture structure (event logs, command logs, manifest)

### Current test status
- E2E tests exist (`tests/e2e/*.py`) but assume old frontend shape
- No Shadow DOM-specific tests
- Fixture loading works but no docked-panel-specific fixtures

---

## Tests First

### Unit Tests

```python
# tests/e2e/test_harness_shadow_dom.py

test_harness_finds_shadow_host()  # GOV-S7-C10-001
  # Harness locates aw-shadow-host element; assert not None
  # Must work on fixture page with Shadow DOM

test_harness_gets_shadow_root()  # GOV-S7-C10-001
  # From shadow-host, retrieve shadow root
  # Assert shadow root accessible and queryable

test_harness_finds_element_in_shadow_dom_by_testid()  # PRD-03-FE-C4-001
  # Use data-testid="llm-tab-button" to find element inside Shadow DOM
  # Assert element found and clickable

test_harness_excludes_shadow_dom_from_page_selectors()  # GOV-S7-C10-001
  # Selector for page content must not match AutoWorkbench UI elements
  # Verify: clicking page element does not click panel UI

test_harness_calculates_docked_panel_bounds()  # PRD-03-FE-C4-002
  # Panel width, height, position (docked-right example: x=page_width-panel_width, y=0)
  # Assert bounds are within page viewport

test_harness_verifies_page_remains_interactive()  # PRD-03-FE-C4-002
  # After panel docking, page content below panel is still clickable
  # Assert clicking page element does not hit panel

test_harness_captures_screenshot()  # GOV-S7-C10-002
  # Screenshot saved to artifact directory with timestamp
  # Assert file created and is valid image format
```

### Contract Tests

```python
# tests/e2e/test_harness_artifact_contract.py

test_artifact_manifest_schema()  # GOV-S7-C10-002
  # Manifest.json has: test_name, duration_ms, passed, artifacts_dir, flow_name
  # Assert schema valid

test_artifact_event_log_schema()  # GOV-S7-C10-002
  # Event log has: timestamp, event_type, payload, event_id
  # Assert all backend events are logged

test_artifact_command_log_schema()  # GOV-S7-C10-002
  # Command log has: timestamp, command_type, payload, command_id
  # Assert all frontend commands logged
```

### Integration Tests

```python
# tests/e2e/test_harness_e2e_setup.py

test_harness_full_setup_and_teardown()  # GOV-S7-C10-001
  # Start browser → load fixture → inject Shadow DOM host → ready for test
  # Assert no errors; panel ready

test_harness_event_stream_with_shadow_dom()  # GOV-S7-C10-002
  # Harness can receive and log backend events while Shadow DOM is active
  # Assert event logging works correctly
```

### Negative Tests

```python
test_harness_rejects_missing_shadow_host()  # GOV-S7-C0-004
  # If aw-shadow-host not found, raise clear error (not timeout, not silent fail)
  # Error message includes: "Shadow DOM host not found"

test_harness_rejects_inaccessible_shadow_root()  # GOV-S7-C0-004
  # If shadow root blocked by browser, raise clear error
  # Error message includes: "Cannot access shadow root"

test_harness_rejects_malformed_docked_bounds()  # GOV-S7-C0-004
  # If panel bounds calc fails (panel outside viewport), raise diagnostic error
  # Do not silently fall back to full-screen assumptions

test_harness_rejects_selector_without_testid()  # GOV-S7-C0-004
  # If data-testid missing on critical element, raise clear error during test setup
  # Error message includes: "Element <name> missing data-testid"

test_harness_handles_shadow_dom_reattach()  # GOV-S7-C0-004
  # If Shadow DOM unmounts/remounts during test, harness recognizes it (not flake)
  # Can re-establish root reference and continue
```

### Regression Tests

Run after implementation:
```bash
python -m pytest tests/e2e/test_harness_*.py -v
python -m pytest tests/test_e2e_*.py -v  # Existing E2E tests
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5  # Cheap suite must stay green
```

---

## Implementation Boundaries

### Allowed Files

```
- tests/e2e/harness.py (update existing harness with Shadow DOM support)
- tests/e2e/test_harness_shadow_dom.py (new — unit/contract tests)
- tests/e2e/test_harness_e2e_setup.py (new — integration tests)
- tests/e2e/test_harness_artifact_contract.py (new — artifact schema tests)
- tests/e2e/fixtures/ (may need Shadow-DOM-specific fixture if creating one)
```

### Forbidden Files

```
- agent.py (no changes)
- frontend/ (no changes; harness only reads DOM, does not modify)
- runtime/ (no changes)
- server.py (no changes)
- tests/test_*.py except test_harness_*.py (do not modify existing tests)
```

---

## Implementation Notes

### Approach

1. **Shadow DOM host detection:** Add `find_shadow_host()` method that uses Playwright/browser API to locate `aw-shadow-host` element
2. **Root access:** Implement `get_shadow_root()` to access shadow-root and return queryable interface
3. **Data-testid selectors:** Add `select_in_shadow_dom(testid)` method that works through Shadow DOM boundary
4. **Docking bounds:** Add `calculate_panel_bounds(docking_position)` to compute panel coordinates from page dimensions
5. **Page interaction:** Add `click_page_element()` that ensures clicks occur outside panel bounds
6. **Artifact capture:** Add `capture_artifact(type, name, data)` to save screenshots, event logs, manifests to timestamped directory
7. **Clear errors:** Wrap all operations in try-catch; raise descriptive errors (not timeouts) when Shadow DOM missing

### Key Invariants

- Shadow DOM host is always located before any test attempts panel interaction
- Docked panel bounds are always calculated and verified within viewport
- Data-testid selectors work through Shadow DOM without wrapper divs
- Event/command logs are written to artifact directory with ISO timestamps
- No hardcoded assumptions about page size or panel position (calculate from real page)

### Known Risks

- **Browser version:** Shadow DOM access APIs differ between Chromium versions; may need feature detection
- **Fixture page:** Fixture may not have Shadow DOM injected automatically; harness must handle injection or test setup must do it
- **Timing:** Shadow DOM host may take time to mount; harness needs retry logic with timeout
- **Selector brittleness:** If data-testids change, tests break; mitigation: enforce data-testid policy in Clusters 3–9

---

## Coverage Requirement

Minimum 90% line coverage for new harness methods.

```bash
python -m pytest tests/e2e/test_harness_shadow_dom.py --cov=tests/e2e/harness --cov-fail-under=90
```

---

## Validation Commands

```bash
# Unit + contract tests
python -m pytest tests/e2e/test_harness_*.py -v

# Full E2E setup
python -m pytest tests/e2e/test_harness_e2e_setup.py::test_harness_full_setup_and_teardown -v -s

# Regression
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5

# Coverage
python -m pytest tests/e2e/test_harness_shadow_dom.py --cov=tests/e2e/harness --cov-fail-under=90
```

---

## Acceptance Criteria

- [ ] Harness finds Shadow DOM host on fixture page
- [ ] Harness can query elements by data-testid through Shadow DOM
- [ ] Docking bounds calculated correctly for right/left/top/bottom positions
- [ ] Page elements remain clickable outside panel area
- [ ] Screenshots captured to artifact directory with timestamps
- [ ] Event/command logs written to manifest with ISO timestamps
- [ ] All 7 unit tests pass (red → green → refactor)
- [ ] All 2 contract tests pass
- [ ] All 2 integration tests pass
- [ ] All 5 negative tests pass (errors clear and actionable)
- [ ] No regression in existing cheap suite
- [ ] Coverage ≥ 90% for new harness methods

---

## Evidence Required

- [ ] tests/e2e/harness.py updated with Shadow DOM methods
- [ ] tests/e2e/test_harness_shadow_dom.py committed with 7 unit tests passing
- [ ] tests/e2e/test_harness_artifact_contract.py committed with 2 contract tests passing
- [ ] tests/e2e/test_harness_e2e_setup.py committed with 2 integration tests passing
- [ ] All 5 negative tests passing
- [ ] Coverage report showing ≥ 90% for harness methods
- [ ] Example artifact directory structure and manifest.json
- [ ] Story status updated to Done

---

## Stop Conditions

- Cannot locate Shadow DOM host without modifying frontend source
- Browser API for Shadow DOM access not available in test environment
- Fixture page does not have Shadow DOM injected and cannot be modified
- Data-testid selectors require wrapper HTML changes (indicates Cluster 3 issue)
- Artifact capture requires external service or manual file I/O that is fragile
