# S7-1104 — Frontend Build and Test Run

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Test
**Status:** Planning
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [Clusters 3–9]

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
