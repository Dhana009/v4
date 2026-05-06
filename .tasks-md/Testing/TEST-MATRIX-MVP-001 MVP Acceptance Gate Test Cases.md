# TEST-MATRIX-MVP-001 MVP Acceptance Gate Test Cases

**Type:** Acceptance Gate Matrix  
**Priority:** P0  
**Owner:** Planning Brain + DEV-4 Evidence Governance  
**References:** EPIC-007, MVP-010, TEST-DOCTRINE-001  

---

## 1. MVP gate tests

| Test ID | Type | Priority | Gate Item | Required Evidence | Pass Criteria |
|---|---|---:|---|---|---|
| MVP-GATE-001 | Gate | P0 | Lifecycle smoke | E2E-P-001 artifacts | run_started/plan_ready/UI visible |
| MVP-GATE-002 | Gate | P0 | Simple click | E2E-P-002 artifacts | backend event + page effect + recording/code |
| MVP-GATE-003 | Gate | P0 | Visible assertion | E2E-P-003 artifacts | assertion only; no click |
| MVP-GATE-004 | Gate | P0 | Exact text/code assertion | E2E-P-004 artifacts | exact_text expected_value preserved |
| MVP-GATE-005 | Gate | P0 | Correction before confirmation | E2E-P-005 artifacts | revised plan only executes |
| MVP-GATE-006 | Gate | P0 | Clarification before planning | E2E-P-006 artifacts | no plan/execution before answer |
| MVP-GATE-007 | Gate | P0 | Locator ambiguity/recovery | E2E-P-007 artifacts | no blind execution; recovery shown |
| MVP-GATE-008 | Gate | P0 | Multi-step strict cursor | E2E-P-008 artifacts | order/cursor/recording/code correct |
| MVP-GATE-009 | Gate | P1/P0 conditional | Replay smoke or typed gap | replay artifacts/gap | pass or typed non-blocking gap |
| MVP-GATE-010 | Gate | P1/P0 conditional | Save/load smoke or typed gap | session artifacts/gap | pass or typed non-blocking gap |
| MVP-GATE-011 | Gate | P0 | Architecture invariant audit | test report | no backend/LLM/frontend/trace truth violation |
| MVP-GATE-012 | Gate | P0 | Artifact completeness | artifact manifest | required files present |
| MVP-GATE-013 | Gate | P0 | Redaction | redaction report | fake secrets absent |
| MVP-GATE-014 | Gate | P0 | Coverage threshold | coverage report | 95% for changed deterministic modules |
| MVP-GATE-015 | Gate | P0 | Known regression suite | regression results | all P0 regressions pass |

---

## 2. MVP fail conditions

Fail MVP gate if:

```text
execution occurs before confirmation
LLM owns runtime truth
frontend owns lifecycle truth
trace owns runtime truth
stale plan executes
exact_text becomes visible assertion
visible assertion becomes click
recording lacks execution evidence
code_update appears before step_recorded
recovery open but run_completed emitted
failed E2E lacks artifacts
redaction fails
```
