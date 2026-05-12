# Sprint 6 Cluster 4 — Journey Planner + Steps Mode + Multi-step Flows

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Depends on:** Cluster 1 (Purpose Coverage), Cluster 2 (Policy Enforcement), Cluster 3 (Page Intelligence + Recommendations)  
**Release gate:** Completion + 95% module coverage + regression pass  

---

## Cluster goal

Complete the **broad journey planning and scoped Steps Mode planning layer**.

This cluster lets the user ask for a full user journey or build a structured step queue, then get a validated plan with data, preconditions, postconditions, page-state dependencies, and confirmation gating.

The scenario spec says Complete LLM Mode is mainly for full user journeys, multi-step flows, multi-page automation, and recording complete usable automation. 

The frontend spec says the Steps tab supports focused steps, picked element/section, expected outcome/postcondition, test data, locator status, reordering, deleting, duplicating, and running selected/all steps through LLM planning.

---

## Stories (8 total)

| ID | Title | Tier | Depends on | Blocks |
|----|-------|------|-----------|--------|
| S6-0401 | Full journey automation classifier and pipeline | 1 | S6-0307 | S6-0402, S6-0403 |
| S6-0402 | Journey planner policy and draft plan schema | 1 | S6-0401 | S6-0404, S6-0405 |
| S6-0403 | Scoped Steps Mode backend intake | 1 | S6-0401 | S6-0404 |
| S6-0404 | Queued multi-step planning flow | 1 | S6-0402, S6-0403 | S6-0405, S6-0406 |
| S6-0405 | Selected section multi-action planning | 1 | S6-0404 | S6-0406 |
| S6-0406 | Multi-page dependency and page-state model | 1 | S6-0405 | S6-0407 |
| S6-0407 | Wrong-current-page precondition flow | 1 | S6-0406 | S6-0408 |
| S6-0408 | Cluster 4 cheap integration proof | 2 | S6-0407 | (release gate) |

---

## Cluster Definition of Done

Cluster 4 is Done only when:

```
1. Broad journey requests classify correctly.
2. Journey planner draft schema exists and is validated.
3. Structured Steps Mode backend intake exists.
4. Queued multi-step planning preserves IDs/order.
5. Selected section multi-action planning works.
6. Page-state/dependency metadata exists.
7. Wrong-current-page precondition flow works.
8. No execution happens before confirmation.
9. Fake/local integration proof exists.
10. 95% coverage exists for new/changed modules.
11. Regression guard passes (Cluster 3 + S5 convergence).
```

---

## Cluster boundaries

### Allowed future implementation files

```
runtime/journey_classifier.py
runtime/journey_planner_contracts.py
runtime/steps_intake.py
runtime/steps_planner.py
runtime/page_state_model.py
runtime/precondition_checks.py
runtime/plan_schema.py
tests/test_journey_classifier.py
tests/test_journey_planner_contracts.py
tests/test_steps_intake.py
tests/test_steps_planner.py
tests/test_page_state_model.py
tests/test_precondition_checks.py
tests/test_cluster4_integration.py
```

### Forbidden in Cluster 4

```
No broad agent.py refactor.
No frontend visual implementation.
No replay repair product flow.
No locator update implementation.
No permission framework implementation beyond risk metadata needed for planning.
No paid browser E2E.
No paid LLM unless explicitly approved as acceptance probe.
No execution before confirmation.
```

---

## Integration with Cluster 3

**Cluster 3 dependencies:**
- Page Intelligence schema/contract (S6-0301, S6-0302, S6-0303)
- Recommendation contracts (S6-0304, S6-0305)
- Page-state model shared (S6-0406)

Cluster 4 journey/steps planning depends on Cluster 3 page/section intelligence and recommendation contracts for context preparation.

---

## Test-first strategy

- **Unit tests:** classification, schema validation, state transitions, ordering, dependency detection
- **Contract tests:** schema compliance, tool filtering, precondition validation
- **Integration tests:** end-to-end flow using fake/local fixtures, no paid LLM
- **Regression tests:** existing Cluster 3 tests, S5-013 convergence, page intelligence tests

Coverage target: **95% for new/changed modules**.

---

## Cheap E2E proof (S6-0408)

Candidate flows using local fixtures (no paid LLM, no external website):

```
1. full journey request → clarification → draft plan
2. steps queue → plan_ready
3. selected section → multi-action parent/children
4. wrong current page → precondition_failed
```

---

## Milestones

| Phase | Gate | Condition |
|-------|------|-----------|
| Unit/Contract | Story-level | Each story tests pass, 95% coverage |
| Integration | Cluster gate | All 8 stories integrated, convergence passes |
| Regression | Release gate | Full regression suite + Cluster 3 + S5 tests pass |

---

## Risk and mitigation

| Risk | Mitigation |
|------|-----------|
| Multi-step plans become too complex | Structured steps with IDs, user can reorder/remove |
| Page-state assumptions fail | Precondition checks before execution, explicit mismatch handling |
| Journey planner misses test data | Clarification request if data missing, marked as required |
| Wrong page navigation | Precondition_failed event, user choice (navigate/skip/stop) |

