# S6-0304 Page validation recommender schema and policy

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 1 (core)  
**Type:** Feature / Schema  
**Status:** Planning  
**Owner:** Recommender Schema  
**Blocks:** S6-0305, S6-0306  
**Blocked by:** S6-0303  

---

## Purpose

Complete `page_validation_recommender`. This is the purpose that turns page intelligence into recommended assertions/actions for user review. Grouped validation recommendation schema, priority classification, section mapping, assertion type mapping, capability support validation, and unsupported recommendation filtering.

---

## Source rules

- Page Intelligence summary is input (from S6-0303)
- Scenario spec: page/section validation recommendations are strongest LLM Mode use case
- Recommendations must be grouped by section, not flat list
- User must be able to accept/remove/reorder before execution

---

## What it contains

```
- grouped validation recommendation schema
- priority classification: critical / useful / optional
- section mapping (which section each recommendation applies to)
- assertion type mapping (what assertion types are recommended)
- capability support validation (only recommend supported assertions/actions)
- unsupported recommendation filtering
```

---

## What it must NOT contain

```
- no execution
- no direct recording
- no code_update
- no browser-changing tools
```

---

## Tests first

### Unit tests

```
- recommendations grouped by section
- priorities assigned correctly
- unsupported assertions become capability gaps or warnings
- duplicate locator ambiguity remains unresolved until backend/user choice
```

### Contract tests

```
- recommender gets no browser-changing tools
- output must map to supported assertion/action capabilities
- invalid recommendation schema retries/fails closed
```

### Integration tests

```
- fake page intelligence summary → fake recommender output → recommendation_ready event payload
```

Coverage: **95% for page_validation_recommender module**

---

## Out of scope

- Do not implement frontend visual UI for recommendations (Cluster 5+)
- Do not execute recommendations
- Do not auto-accept recommendations

---

## Allowed files

```
runtime/page_validation_recommender.py (new)
runtime/recommendation_contracts.py (new)
tests/test_page_validation_recommender.py (new)
tests/test_recommendation_contracts.py (new)
```

---

## Forbidden files

- No frontend code
- No execution logic
- No auto-acceptance

---

## Implementation notes

### Schema definition (recommendation_contracts.py)

```
ValidationRecommendation:
  - id: string (stable across accept/reorder/remove)
  - recommendation_type: enum (assertion / action / check)
  - assertion_type: enum (text / visibility / attribute / etc.)
  - action_type: enum (click / fill / submit / etc.)
  - section_id: string (which section this applies to)
  - description: string (human-readable)
  - locator_hint: string (not final, just hint)
  - expected_value: optional (for assertion)
  - priority: enum (critical / useful / optional)
  - confidence: float (0-1)
  - capability_status: enum (supported / capability_gap / warning)

ValidationRecommendationGroup:
  - section_id: string
  - section_name: string
  - recommendations: list[ValidationRecommendation]
  - ambiguities: list (if multiple targets match)

PageValidationRecommenderOutput:
  - groups: list[ValidationRecommendationGroup]
  - total_recommendations: int
  - critical_count: int
  - capability_gaps: list
  - warnings: list
```

### Approach

1. Create `runtime/recommendation_contracts.py` with schema definitions
2. Create `runtime/page_validation_recommender.py` with:
   - `recommend_page_validations(page_intelligence_summary)` → PageValidationRecommenderOutput
   - Group recommendations by section
   - Classify priority (critical: e.g., form fields; useful: e.g., headings; optional: e.g., footer)
   - Filter by supported capabilities (check agent.py for available assertion/action types)
   - Mark capability gaps (e.g., "custom JS validation not supported")
   - Handle duplicate/ambiguous locators (mark as ambiguity, require user clarification)

3. Create `tests/test_page_validation_recommender.py`:
   - Output schema compliance
   - Grouping by section
   - Priority classification
   - Capability filtering
   - Ambiguity detection

### Key invariants

- Recommendations are grouped, not flat
- User can accept/remove/reorder (IDs are stable)
- Unsupported capabilities are explicit (not silent)
- Ambiguities are marked, not resolved

---

## Validation commands

```bash
python -m pytest tests/test_page_validation_recommender.py::test_grouping_by_section -v
python -m pytest tests/test_page_validation_recommender.py::test_priority_classification -v
python -m pytest tests/test_page_validation_recommender.py::test_capability_filtering -v
python -m pytest tests/test_recommendation_contracts.py::test_schema_compliance -v
coverage run -m pytest tests/test_page_validation_recommender.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/recommendation_contracts.py` with schema
- [ ] `runtime/page_validation_recommender.py` with logic
- [ ] `tests/test_page_validation_recommender.py` with unit tests
- [ ] `tests/test_recommendation_contracts.py` with contract tests
- [ ] Recommendations are grouped by section
- [ ] Priorities assigned correctly
- [ ] Capability gaps marked (not silent)
- [ ] Ambiguities flagged
- [ ] 95% coverage

---

## Stop conditions

- Agent.py capabilities unclear (enumerate in story)
- Section extraction not available (defer to S6-0302)

---

## Sign-off

- [x] Story is specific (create recommender schema/policy)
- [x] Scope is bounded (no execution, no frontend)
- [x] Tests are first
- [x] Blocks S6-0305 (recommendation events)
