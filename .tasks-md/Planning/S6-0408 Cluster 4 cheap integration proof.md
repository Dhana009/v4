# S6-0408 Cluster 4 cheap integration proof

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 2 (integration proof)  
**Type:** Integration / E2E  
**Status:** Planning  
**Owner:** Integration  
**Blocks:** (Cluster 4 release gate)  
**Blocked by:** S6-0407  

---

## Purpose

Prove journey/steps planning without paid LLM or browser-changing E2E. Fixture-based integration tests, fake LLM planner, no paid LLM, no execution until confirmation.

---

## Source rules

- S6-0401 through S6-0407 stories are complete and tested
- Cheap/fake models are available for testing
- S5 DOM-heavy fixtures available
- No paid LLM or browser E2E required

---

## What it contains

```
- fixture-based integration tests
- fake LLM planner
- no paid LLM
- no execution until confirmation
```

### Required flows

```
1. full journey request → clarification → draft plan
2. steps queue → plan_ready
3. selected section → multi-action parent/children
4. wrong current page → precondition_failed
```

---

## What it must NOT contain

```
- no paid LLM
- no browser-changing execution
- no replay repair
- no frontend UI build
```

---

## Tests first

### Integration tests

```
- fake journey planner produces valid plan
- fake step planner preserves step IDs
- page-state model appears in planned operations
- no runtime event marks execution/recording before confirmation
```

### Regression tests

```
- S5 convergence
- backend event contract
- recording/code_update truth
- Page Intelligence schema/fake integration (Cluster 3)
```

Coverage: **95% for Cluster 4 code under test**

---

## Out of scope

- Do not implement frontend UI
- Do not run paid E2E
- Do not execute plans
- Do not implement replay repair

---

## Allowed files

```
tests/test_cluster4_cheap_e2e.py (new)
tests/fixtures/cluster4_e2e_scenarios.py (new, test data)
No changes to production code (S6-0401 through S6-0407 complete)
```

---

## Forbidden files

- No frontend code
- No execution logic
- No changes to runtime/ (completed in S6-0401 through S6-0407)

---

## Implementation notes

### Scenario 1: Full journey request

```
Given: user request "build a test for login → dashboard → user profile update"
When: request classified as full_journey_automation
And:   clarification asks for test data (username, password, new profile data)
Then:
  - clarification_needed event emitted
  - user provides data
  - journey planner creates draft plan
  - plan includes 3 steps with dependencies
  - no execution happens
```

### Scenario 2: Steps queue

```
Given: user provides queue of 5 pending steps (with stable step IDs)
When: steps are queued and submitted for planning
Then:
  - steps_planner receives queue
  - step order is preserved
  - plan_ready includes all 5 operations
  - step_ids are stable in plan
  - page-state model tracks dependencies
```

### Scenario 3: Selected section

```
Given: user selects section and requests "validate form fields and submit"
When: section intent is decomposed
Then:
  - one parent step created
  - child operations: assert email/password/submit button visible, fill fields, click submit
  - children preserve order (assertions before action)
  - plan_ready includes parent + children
  - no execution before confirmation
```

### Scenario 4: Wrong current page

```
Given: plan expects browser on /dashboard
And:   current browser is on /login
When: precondition is checked before execution
Then:
  - precondition_failed event emitted
  - expected/current URLs shown
  - resolution options: navigate to /dashboard, stop, skip
  - user must choose before continuing
  - no silent navigation in default mode
```

### Approach

1. Create `tests/fixtures/cluster4_e2e_scenarios.py`:
   - Fixture page contexts (login page, dashboard, profile page)
   - Expected journey plans
   - Expected step queues
   - Expected section intents
   - Expected precondition mismatches

2. Create `tests/test_cluster4_cheap_e2e.py`:
   - For each scenario:
     - Set up fixture context
     - Request journey/steps/section planning
     - Verify no execution event before confirmation
     - Verify plan structure
     - Capture artifacts (classification, clarification, plan, events)

3. Run full regression:
   - All S6-0401 through S6-0407 tests
   - Cluster 3 tests
   - S5-013 convergence tests
   - Page intelligence schema/fake tests

### Key invariants

- No paid LLM calls
- No execution before confirmation
- All flows produce plan_ready (not execution_started)
- Artifacts capture full flow (request → classification/clarification → planning → plan_ready)

---

## Validation commands

```bash
# Run scenario tests
python -m pytest tests/test_cluster4_cheap_e2e.py::test_full_journey_scenario -v
python -m pytest tests/test_cluster4_cheap_e2e.py::test_steps_queue_scenario -v
python -m pytest tests/test_cluster4_cheap_e2e.py::test_selected_section_scenario -v
python -m pytest tests/test_cluster4_cheap_e2e.py::test_wrong_page_scenario -v

# Run full regression
python -m pytest tests/test_journey_*.py tests/test_steps_*.py tests/test_page_state_*.py tests/test_precondition_*.py -v

# Verify Cluster 3 still passes
python -m pytest tests/test_cluster3_cheap_e2e.py -v

# Verify S5 convergence still passes
python -m pytest tests/test_planning_convergence_contract.py -v

# Coverage for Cluster 4
coverage run -m pytest tests/test_cluster4_cheap_e2e.py
coverage report --include=runtime/journey_*.py,runtime/steps_*.py,runtime/page_state_*.py,runtime/precondition_*.py
```

---

## Artifact/evidence requirement

- [ ] Scenario 1: full journey → clarification → draft plan
- [ ] Scenario 2: steps queue → plan_ready with stable IDs
- [ ] Scenario 3: section intent → parent + children with order preserved
- [ ] Scenario 4: wrong page → precondition_failed with resolution options
- [ ] All scenarios: no execution_started event (only plan_ready)
- [ ] Artifacts captured for each scenario
- [ ] Full regression passed (S6-0401 through S6-0407 + Cluster 3 + S5 convergence)
- [ ] 95% coverage for Cluster 4 code

---

## Stop conditions

- Fixture pages not available (create minimal fixtures in story)
- Fake models not working (coordinate with S6-0303)
- Convergence regression fails (debug upstream stories)
- Cluster 3 tests fail (debug Cluster 3)

---

## Sign-off

- [x] Story is specific (prove Cluster 4 with cheap E2E)
- [x] Scope is bounded (no paid LLM, no frontend, no execution)
- [x] Tests are first (scenario-based)
- [x] Releases Cluster 4 gate (all tests + regression pass)
