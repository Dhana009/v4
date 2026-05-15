# S7-1107 — Push Readiness Gate

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Decision Gate
**Status:** Done
**Blocks:** []
**Blocked by:** [S7-1101, S7-1102, S7-1103, S7-1104, S7-1105, S7-1106]

---

## Objective

Make final decision on whether to push Sprint 7 to remote. Verify:
- Working tree clean (except allowed local noise)
- Cheap suite green (0 new failures)
- Frontend builds
- Browser E2E passes
- BUG-S6-FINAL-002 resolved or explicitly superseded
- Paid/live gate status honest

Decision options:
- **PUSH_READY:** Clean, green, no blockers. Push main branch.
- **NOT_PUSH_READY_FIX_REQUIRED:** Blockers found; must fix before push.
- **PUSH_READY_WITH_DOCUMENTED_DEFERRED_PAID/LIVE_GATE:** Local gate clean; paid/live testing deferred to Sprint 8/9 with explicit requirements.

---

## Source Rules

- GOV-S7-C0-001 through GOV-S7-C0-063: All invariants must hold
- GOV-S7-C11-001: Honest status required; no fake Done

---

## Verification Checklist

```
[ ] git status --short --branch
    Expected: only .DS_Store, AGENTS.md, frontend_new_design_prototype/ (local noise)
    No unexpected dirty product/test files

[ ] git diff --cached --name-only
    Expected: empty (nothing staged)
    Or: only .tasks-md/ planning files

[ ] python -m pytest -q --ignore=tests/e2e
    Expected: same or better than Sprint 6 baseline; 0 new failures
    Classification: all failures pre-existing or intentional deferral

[ ] cd frontend && npm run build
    Expected: success, no errors
    dist/ regenerated if code changed

[ ] tests/e2e/ smoke (8 flows)
    Expected: all pass with < 5% flakiness
    Fake LLM mode confirmed
    No live external sites accessed

[ ] Requirement matrix (S7-1101)
    Expected: all rows classified; no "Missing evidence"
    Every Done row has commit + test evidence
    BUG-S6-FINAL-002 resolved or superseded

[ ] Architecture audit (S7-1102)
    Expected: no violations of 8 core invariants
    Monoliths within budget
    Paid LLM not required in default path

[ ] Branch/remote status
    Expected: HEAD ahead of origin/main by N commits
    N = expected Sprint 7 commits
    No merge conflicts
    Ready for force-push (if needed) or regular push
```

---

## Decision Matrix

| Condition | Decision | Action |
|-----------|----------|--------|
| All green, no blockers | PUSH_READY | git push origin main |
| > 5 test failures | NOT_PUSH_READY_FIX_REQUIRED | Fix failures; S7-1103 reopen |
| Paid gate required for acceptance | PUSH_READY_WITH_DOCUMENTED_DEFERRED_PAID/LIVE_GATE | Document gate; push with status |
| Architecture violation | NOT_PUSH_READY_FIX_REQUIRED | Fix drift; S7-1102 reopen |
| Frontend build fails | NOT_PUSH_READY_FIX_REQUIRED | Fix build; S7-1104 reopen |
| > 1 E2E flow fails | NOT_PUSH_READY_FIX_REQUIRED | Fix flows; S7-1010 reopen |

---

## Acceptance Criteria

- [ ] All verification checks pass
- [ ] Decision made: PUSH_READY | NOT_PUSH_READY_FIX_REQUIRED | PUSH_READY_WITH_DOCUMENTED_DEFERRED_PAID/LIVE_GATE
- [ ] Decision documented with rationale
- [ ] If PUSH_READY: ready to git push origin main
- [ ] If NOT_PUSH_READY: blockers documented; stories reopened
- [ ] If PUSH_READY_WITH_DOCUMENTED_DEFERRED: deferred gate requirements explicit

---

## Evidence Required

- [ ] Verification checklist output
- [ ] Decision document with timestamp and rationale
- [ ] Document committed to .tasks-md/Artifacts/C11/S7-1107-push-readiness-decision.md

---

## Stop Conditions

- Cannot make decision because verification is incomplete (something missing)
- Multiple "NOT_READY" conditions (must fix before pushing)
- Paid/live gate status ambiguous (must be explicit)

---

## Template: Push Readiness Decision

```
PUSH READINESS GATE DECISION — S7-1107

Date: 2026-05-XX HH:MM UTC
Decided by: [name]

DECISION: [PUSH_READY | NOT_PUSH_READY_FIX_REQUIRED | PUSH_READY_WITH_DOCUMENTED_DEFERRED_PAID/LIVE_GATE]

VERIFICATION RESULTS:

1. Working tree: CLEAN (only .DS_Store, AGENTS.md, frontend_new_design_prototype/)
2. Cheap suite: GREEN (1689 + X passed, 0 new failures)
3. Failures classified: <summary of pre-existing vs new>
4. Frontend build: SUCCESS
5. E2E smoke: COMPLETE (8 flows, all pass, < 5% flakiness)
6. Requirement matrix: COMPLETE (0 "Missing evidence" rows)
7. Architecture audit: CLEAN (no violations)
8. BUG-S6-FINAL-002: RESOLVED (via Clusters 3–9)

DEFERRED GATES (if applicable):
- Paid E2E: NOT_RUN (can be approved for Sprint 8 or run separately)
- Real-world testing: DEFERRED_TO_SPRINT_9

NEXT STEPS:
- Push: git push origin main
- Build: npm run build in frontend/
- Verify: python -m pytest -q --ignore=tests/e2e
- Sprint 8: Controlled hardening and realistic fixtures

```


---

## Evidence Recorded

- **Handoff doc:** `.tasks-md/Sprints/SPRINT-007-HANDOFF.md`
- **Final regression:** 2481 passed / 1 skipped / 0 failed (excl. tests/e2e)
- **Frontend build:** clean (1.3mb js, 42.9kb css)
- **Browser smoke baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed (7.22s)
- **Push readiness decision:** NOT_PUSH_READY_AS_COMPLETE_UI_INTEGRATION

---

## Status Correction (2026-05-14)

The Evidence Recorded section above was based on an audit-time assumption
that the C6–C9 modular components were integrated into the live
`frontend/aw-ide-panel.jsx`. Re-audit at HEAD `f20d7f3` shows this is
**not** the case:

- `frontend/aw-ide-panel.jsx` (2135 lines) has **0 imports** from
  `frontend/src/components/{llm,steps,recorded,code,trace,agents,manual,picker,locator,replay,session}/`.
- `frontend/src/main.jsx` does not import those components either.
- The live browser path renders the monolith's internal `IDE*` functions.
- C4 (docked Shadow DOM) and C5 (store/dispatcher/runtime prop threading)
  are integrated; C6–C9 cards are dead code in the repo.

Final Sprint 7 status: **PARTIAL_INTEGRATION**.
Push readiness: **NOT_PUSH_READY_AS_COMPLETE_UI_INTEGRATION**.

Sprint 8 Integration Pass owes the actual integration + real DOM and
browser E2E gate before any Sprint 7 closure can be re-asserted as
frontend-complete. C6–C9 stories remain Done as "component built and
source-pattern tested," but the cluster-level frontend-complete claim is
retracted.
