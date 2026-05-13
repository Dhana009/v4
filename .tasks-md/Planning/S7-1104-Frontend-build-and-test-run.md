# S7-1104 — Frontend Build and Test Run

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Test
**Status:** Done
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [Clusters 3–9]

---

## Source Rules

- `PRD-06-ACC-003`: Frontend build/test must pass before push readiness (`06_BUILD_ROADMAP_AND_ACCEPTANCE.md`)
- `PRD-03-FE-011`: No static/demo content in live mode (`03_FRONTEND_RUNTIME.md`)
- `PRD-03-FE-020`: data-testid baseline on critical UI elements (`03_FRONTEND_RUNTIME.md`)
- `GOV-S7-C0-022`: Cheap regression suite must remain stable
- `GOV-S7-C0-036` … `GOV-S7-C0-040`: Evidence requirements for Done state
- C11 acceptance: build log + test log committed as evidence

---

## Objective

Build frontend and run all frontend-specific tests. Verify no build errors, no static/demo production path, no stale artifacts.

---

## Tests First

```bash
cd frontend
npm run build 2>&1 | tee frontend-build.log
npm run test 2>&1 | tee frontend-test.log  # if tests exist
npm run lint 2>&1 | tee frontend-lint.log  # if linter exists
```

---

## Acceptance Criteria

- [ ] npm run build succeeds
- [ ] No build errors or warnings related to missing data-testid
- [ ] Frontend tests pass (if they exist)
- [ ] No static/demo UI referenced in production build
- [ ] dist/ regenerated if build process modified code

---

## Evidence Required

- [ ] frontend-build.log
- [ ] frontend-test.log (if tests exist)
- [ ] Build summary committed to .tasks-md/Artifacts/C11/

---

## Stop Conditions

- npm run build fails (must fix)
- Build includes static/demo runtime truth (architecture issue)
- Missing data-testids on critical UI elements (Cluster 3 issue)

---

## Evidence Recorded

- **Handoff doc:** `.tasks-md/Sprints/SPRINT-007-HANDOFF.md`
- **Final regression:** 2481 passed / 1 skipped / 0 failed (excl. tests/e2e)
- **Frontend build:** clean (1.3mb js, 42.9kb css)
- **Browser smoke baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed (7.22s)
- **Push readiness decision:** PUSH_READY_WITH_DOCUMENTED_DEFERRED_BROWSER_GATE
