# S7-0305 Static Demo Fallback Removal Strategy

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0305  
**Status:** Planning  
**Date:** 2026-05-13  

---

## Objective

Plan how to remove static/demo fallbacks and render from backend events only. Define empty states for missing data. Prevent static demo content from becoming runtime truth.

---

## Current Issue

Today, `aw-ide-panel.jsx` and other components render static demo data when backend state is missing. This can become runtime truth if not disciplined. S7-0305 plans the removal strategy.

---

## Tests First

### Audit Tests

**Test: Demo content inventory**
- Grep for static plan, steps, code, trace mock data.
- Report: files and lines with demo content.

**Test: Current fallback logic**
- Identify code that renders demo when state is missing.
- Report: fallback patterns (conditional renders, default values).

### Production Tests

**Test: No demo in live mode**
- Verify production code does NOT render demo content.
- Empty states show "No data yet" instead.

**Test: Empty state rendering**
- Components without data show explicit empty states.
- Empty states are readable, not error pages.

---

## Implementation Boundaries

### Allowed Changes

- **Define empty state components** — EmptyState primitive with message.
- **Update components** to check for data before rendering:
  - If data exists → render data
  - If data missing → render empty state
  - No demo fallback to static content

- **Tests:** `tests/test_frontend_live_state.py`
  - Verify components render empty states when data is null.
  - Verify no static demo content in production mode.

### Forbidden Changes

- No backend integration (Cluster 5+).
- No static content in production paths.

---

## Acceptance Criteria

✅ **Demo content removed** — No static plan/steps/code in production paths.
✅ **Empty states defined** — Components show "No data yet" when missing.
✅ **Tests pass** — No demo content detected in live mode.
✅ **Evidence:** grep output, empty state examples, test results.

---

## Evidence Checklist

- [ ] Demo content inventory created
- [ ] Fallback patterns identified
- [ ] Empty state strategy defined
- [ ] Components updated to use empty states
- [ ] Tests verify no demo content
- [ ] Build succeeds
- [ ] Story updated with evidence

