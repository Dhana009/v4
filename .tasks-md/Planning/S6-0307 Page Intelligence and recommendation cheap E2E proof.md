# S6-0307 Page Intelligence and recommendation cheap E2E proof

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 2 (integration proof)  
**Type:** Integration / E2E  
**Status:** Planning  
**Owner:** Integration  
**Blocks:** (Cluster 3 release gate)  
**Blocked by:** S6-0306  

---

## Purpose

Prove Page Intelligence + recommendation mode through local fixtures. Local fixture-based cheap E2E, no paid LLM, no external website, artifact/evidence capture. Candidate flows: weak-divs page, duplicate-profiles page, data-table page, modal-recovery page.

---

## Source rules

- S5 DOM-heavy fixtures exist (test/fixtures/dom_heavy_pages.py)
- S6-0301 through S6-0306 stories are complete and tested
- Cheap/fake models are available for testing
- No paid LLM or browser E2E required

---

## What it contains

```
- local fixture-based cheap E2E
- no paid LLM
- no external website
- artifact/evidence capture
```

### Candidate flows

```
1. weak-divs page → recommendation mode → ambiguity shown
2. duplicate-profiles page → candidate ambiguity → ask user/recommendation review
3. data-table page → table/list recommendations grouped by row/section
4. modal-recovery page → dynamic UI risk identified
```

---

## What it must NOT contain

```
- no paid browser E2E
- no real LLM call unless later acceptance explicitly approved
- no replay repair
- no frontend full UI build
```

---

## Tests first

### Cheap E2E / Integration tests

```
- page recommendation request does not execute
- recommendations are grouped by section
- accepted recommendations become plan_ready
- unaccepted recommendations do not execute
- artifacts include page intelligence summary and recommendation payload
```

### Regression tests

```
- S5-013 convergence behavior still passes
- page intelligence schema/fake integration tests
- recommendation event/state machine tests
- all Cluster 3 unit/contract tests still pass
```

Coverage: **95% for Cluster 3 code under test**

---

## Out of scope

- Do not implement frontend visual UI
- Do not run paid E2E
- Do not execute plans
- Do not implement replay repair

---

## Allowed files

```
tests/test_cluster3_cheap_e2e.py (new)
tests/fixtures/cluster3_e2e_scenarios.py (new, test data)
No changes to production code (S6-0301 through S6-0306 complete)
```

---

## Forbidden files

- No frontend code
- No execution logic
- No changes to runtime/ (completed in S6-0301 through S6-0306)

---

## Implementation notes

### Scenario 1: Weak DIVs page

```
Given: fixture page with weak divs (no semantic elements)
When: user requests "validate and find buttons on this page"
Then:
  - page_summary_ready event includes low semantic quality score
  - recommendations include ambiguity flags
  - user is asked to clarify which button
  - no execution happens
```

### Scenario 2: Duplicate profiles page

```
Given: fixture page with 3 identical profile cards
When: user requests "click the profile for user X"
Then:
  - recommendations show all 3 matching profiles
  - ambiguity_flag is true
  - user must select which profile (accept specific recommendation)
  - unselected recommendations are not executed
```

### Scenario 3: Data table page

```
Given: fixture page with large data table (50 rows, 10 columns)
When: user requests "validate table structure and find specific cell"
Then:
  - table is identified and grouped by row
  - recommendations include row-level assertions
  - recommendations grouped by "table" section
  - recommendations prioritized (critical: headers; useful: specific rows)
```

### Scenario 4: Modal recovery page

```
Given: fixture page with modal/overlay
When: user requests "close modal and continue"
Then:
  - page intelligence summary includes modal detection
  - recommendations include close button with risk flag
  - precondition for next action includes "modal must be closed"
  - user can accept/remove/reorder
```

### Approach

1. Create `tests/fixtures/cluster3_e2e_scenarios.py`:
   - Fixture pages (weak divs, duplicate profiles, data table, modal)
   - Expected page intelligence summaries
   - Expected recommendations
   - Expected user interactions

2. Create `tests/test_cluster3_cheap_e2e.py`:
   - For each scenario:
     - Load fixture page
     - Request page intelligence
     - Request recommendations
     - Accept subset of recommendations
     - Verify no execution
     - Verify plan_ready includes accepted only
     - Capture artifacts (page summary, recommendations, plan)

3. Run full regression:
   - All S6-0301 through S6-0306 tests
   - S5-013 convergence tests
   - Page intelligence schema/fake tests

### Key invariants

- No paid LLM calls
- No browser-changing actions
- No execution before confirmation
- Artifacts capture full flow (summary → recommendations → plan)

---

## Validation commands

```bash
# Run scenario tests
python -m pytest tests/test_cluster3_cheap_e2e.py::test_weak_divs_scenario -v
python -m pytest tests/test_cluster3_cheap_e2e.py::test_duplicate_profiles_scenario -v
python -m pytest tests/test_cluster3_cheap_e2e.py::test_data_table_scenario -v
python -m pytest tests/test_cluster3_cheap_e2e.py::test_modal_scenario -v

# Run full regression
python -m pytest tests/test_page_intelligence_live.py tests/test_page_extraction.py tests/test_page_validation_recommender.py tests/test_recommendation_*.py -v

# Verify convergence still passes
python -m pytest tests/test_planning_convergence_contract.py -v

# Coverage for Cluster 3
coverage run -m pytest tests/test_cluster3_cheap_e2e.py
coverage report --include=runtime/page_*.py
```

---

## Artifact/evidence requirement

- [ ] Scenario 1: weak divs → low quality score + ambiguity
- [ ] Scenario 2: duplicate profiles → ambiguity flags + user choice required
- [ ] Scenario 3: data table → grouped recommendations + priorities
- [ ] Scenario 4: modal → risk flags + precondition
- [ ] All scenarios: no execution, plan_ready only after acceptance
- [ ] Artifacts captured (page summary, recommendations, plan for each scenario)
- [ ] Full regression passed (S6-0301 through S6-0306 + S5 convergence)
- [ ] 95% coverage for Cluster 3 code

---

## Stop conditions

- Fixture pages not available (create minimal fixtures in story)
- Fake/cheap models not working (coordinate with S6-0303)
- Convergence regression fails (debug S6-0301 through S6-0306)

---

## Sign-off

- [x] Story is specific (prove Cluster 3 with cheap E2E)
- [x] Scope is bounded (no paid LLM, no frontend, no execution)
- [x] Tests are first (scenario-based)
- [x] Releases Cluster 3 gate (all tests + regression pass)
