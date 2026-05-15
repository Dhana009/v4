# S6-0401 Full journey automation classifier and pipeline

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature / Classification  
**Status:** Planning  
**Owner:** Intent Classification  
**Blocks:** S6-0402, S6-0403  
**Blocked by:** S6-0307  

---

## Purpose

Classify broad user requests into `full_journey_automation` and start the correct pipeline. Intent classification for broad journey requests, no immediate execution, clarification for missing data/scope/permissions, page analysis request when needed, draft journey plan request after scope is known.

---

## Source rules

- Scenario spec: Complete LLM Mode is mainly for full user journeys, multi-step flows, multi-page automation
- Cluster 3 page intelligence is available (S6-0307 complete)
- Intent classifier purpose must be in typed registry (S6-0102)
- No execution until clarification and scope are confirmed

---

## What it contains

```
- intent classification for broad journey requests
- no immediate execution
- clarification for missing data/scope/permissions
- page analysis request when needed
- draft journey plan request after scope is known
```

---

## What it must NOT contain

```
- no actual execution
- no upload/download implementation
- no frontend card implementation
- no replay repair
```

---

## Tests first

### Unit tests

```
- "build a test for this flow" classified as full_journey_automation
- upload/submit/result-validation request identifies missing fields
- unsupported CRM/API validation is marked capability risk
```

### Contract tests

```
- broad journey request emits clarification or page_analysis_requested, not execution_started
- missing file/test data triggers test_data_required or clarification_needed
```

### Integration tests

```
- free LLM request → classified intent → clarification → draft plan request
```

Coverage: **95% for journey_classifier module**

---

## Out of scope

- Do not implement full journey planning (defer to S6-0402)
- Do not execute plans
- Do not implement frontend UI

---

## Allowed files

```
runtime/journey_classifier.py (new)
tests/test_journey_classifier.py (new)
Minor edits to:
  - runtime/llm_runtime_controller.py (thin call site)
  - agent.py (dispatch to classifier)
```

---

## Forbidden files

- No plan execution logic
- No frontend code
- No broad refactoring

---

## Implementation notes

### Classification logic (journey_classifier.py)

```
ClassifyJourneyRequest(user_request) → JourneyClassification:
  - type: enum (full_journey_automation / steps_queue / section_validation / unknown)
  - confidence: float (0-1)
  - required_fields: list (missing scope/data/permissions)
  - capability_gaps: list (unsupported features)
  - next_step: enum (clarification / page_analysis / plan_request)
```

### Approach

1. Create `runtime/journey_classifier.py` with:
   - `classify_journey_request(user_request)` → JourneyClassification
   - Pattern matching for "build a test for", "create automation for", "test flow", etc.
   - Identify missing: scope (which pages?), test data, permissions (file upload?), expected outcomes
   - Identify capability gaps (external API calls, CRM integration, etc.)
   - Return next step: ask clarification vs. proceed to page analysis vs. proceed to planning

2. Create `tests/test_journey_classifier.py`:
   - Classification accuracy for known request patterns
   - Missing field detection
   - Capability gap detection
   - Next step assignment

3. Update `agent.py` or orchestrator:
   - Detect broad journey request
   - Call `journey_classifier.classify()`
   - Emit clarification event if needed
   - Emit page_analysis_requested if scope is clear

### Key invariants

- Broad journey requests are classified before execution
- Missing scope/data is detected and user is asked
- Capability gaps are explicit (not silent failures)
- No execution until classification and clarification complete

---

## Validation commands

```bash
python -m pytest tests/test_journey_classifier.py::test_classify_full_journey -v
python -m pytest tests/test_journey_classifier.py::test_missing_fields -v
python -m pytest tests/test_journey_classifier.py::test_capability_gaps -v
python -m pytest tests/test_journey_classifier.py::test_next_step_assignment -v
coverage run -m pytest tests/test_journey_classifier.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/journey_classifier.py` created
- [ ] `tests/test_journey_classifier.py` created
- [ ] Classification logic handles known request patterns
- [ ] Missing field detection works
- [ ] Capability gap detection works
- [ ] Next step (clarification/analysis/planning) assigned correctly
- [ ] 95% coverage

---

## Stop conditions

- Request patterns unclear (enumerate in story examples)
- Required vs. optional fields ambiguous (clarify in issue)

---

## Sign-off

- [x] Story is specific (classify journey requests)
- [x] Scope is bounded (no execution, no implementation)
- [x] Tests are first
- [x] Blocks S6-0402/S6-0403 (planning pipelines)
