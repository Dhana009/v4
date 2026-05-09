# S5-009 Page Intelligence LLM route design and contract

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 07_MULTI_MODEL_ORCHESTRATION.md section 3.2, runtime/page_intelligence.py

## Problem / Goal

**Problem:** page_intelligence.py does deterministic summarization only. For weak DOM (div/span pages), a cheap model could propose better locator candidates and page structure. Currently no contract for cheap model page intelligence.

**Goal:** Define structured output schema for page_intelligence_summarizer purpose. Schema includes: page summary, semantic quality, element candidates with confidence/risk, ambiguities, risk flags. Test with fake model (no real nano model).

## Scope

- Define PageIntelligenceSchema in `runtime/page_intelligence_schema.py`
- Output fields: page_or_section_summary, semantic_quality (good|mixed|poor), elements (list with semantic_name, element_type_guess, visible_text, signals_used, confidence, risk), ambiguities, risk_flags
- Contract tests for malformed output rejection
- Fake model tests for schema validation
- Advisory-only boundary: output is candidates/suggestions, not truth

Out of scope:
- Real nano model implementation (defer to follow-up)
- DOM intelligence execution or action
- Element validation (Step Runner does that)

## Required unit tests

- `test_page_intelligence_schema.py`:
  - Schema fields defined and documented
  - semantic_quality must be good|mixed|poor
  - Elements list must include confidence/risk
  - Ambiguities and risk_flags are optional lists
- `test_page_intelligence_schema_validation.py`:
  - Valid output passes validation
  - Missing required fields rejected
  - Invalid semantic_quality rejected
  - Confidence/risk must be numeric or string

## Required contract tests

- `test_page_intelligence_output_contract.py`:
  - Fake model output matches schema
  - Malformed output (missing semantic_quality) rejected
  - Risk flags are advisory-only (never execute)
  - Candidates are suggestions, not truth
- `test_page_intelligence_advisory_boundary.py`:
  - Output cannot trigger action or recording
  - Step Runner must validate all candidates before use

## Required integration tests

- `test_page_intelligence_with_weak_dom.py`:
  - Weak div/span page → page intelligence call
  - Output includes semantic_quality and ambiguities
  - Candidates are ranked by confidence
- `test_page_intelligence_fake_model_contract.py`:
  - Fake model receives weak DOM
  - Returns schema-valid output

## Fixture/page needs

- Weak div/span fixture page (for S5-011)

## Paid E2E requirement

None (fake model only).

## Acceptance criteria

- [ ] PageIntelligenceSchema defined and documented
- [ ] Output fields: page_summary, semantic_quality, elements (with confidence/risk), ambiguities, risk_flags
- [ ] Schema validation rejects malformed output
- [ ] Contract tests prove advisory-only boundary
- [ ] Fake model integration works
- [ ] Telemetry includes purpose="page_intelligence_summarizer"
- [ ] Documentation states output is suggestion only, Step Runner validates

## Evidence

Will include:
- PageIntelligenceSchema implementation
- Schema validation logic
- Unit test output showing schema structure
- Contract test output proving validation
- Integration test with fake model
- Documentation of advisory boundary

## Verification commands/results

```bash
pytest tests/test_page_intelligence_schema.py -v
pytest tests/test_page_intelligence_schema_validation.py -v
pytest tests/test_page_intelligence_output_contract.py -v
pytest tests/test_page_intelligence_advisory_boundary.py -v
pytest tests/test_page_intelligence_with_weak_dom.py -v
pytest tests/test_page_intelligence_fake_model_contract.py -v
```

## Risk

- **Low:** Output quality dependent on fake model; real model behavior may differ
- **Low:** Candidates may not always be valid (rejected by Step Runner during validation)

## Mitigation

- Contract tests comprehensive for schema
- Advisory-only boundary is explicit and tested
- Step Runner validation is non-negotiable
