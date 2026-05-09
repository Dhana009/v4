# S5-010 Page Intelligence first fake-model integration

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P1
Source docs: PRD v2.3 07_MULTI_MODEL_ORCHESTRATION.md, S5-009 Page Intelligence contract

## Problem / Goal

**Problem:** Page intelligence is currently deterministic HTML only. For weak div/span pages, we need to prove a fake cheap model can propose better candidates before main planner sees the page.

**Goal:** Build fake-model integration where weak div/span page → page intelligence call (fake model) → compact summary → main planner receives summary instead of raw DOM. Verify Step Runner still validates locator.

## Scope

- Integrate page_intelligence_summarizer through LLMRuntimeController
- Weak div/span page flow: DOM → fake page intelligence model → struct summary → main planner
- Main planner receives PageIntelligencePacket summary, not raw DOM
- Verify Step Runner validates proposed locator before action
- Fake model returns schema-valid output

Out of scope:
- Real nano model (fake only for this story)
- Full DOM page intelligence (S5-011 fixture work)
- UI changes for page intelligence display

## Required unit tests

- `test_page_intelligence_summarizer_call.py`:
  - page_intelligence_summarizer purpose call through controller
  - Fake model receives weak DOM
  - Returns PageIntelligencePacket schema
- `test_page_intelligence_flow.py`:
  - Weak page → page intelligence call → compact summary
  - Summary is smaller than raw DOM

## Required contract tests

- `test_page_intelligence_to_main_planner_contract.py`:
  - Main planner receives PageIntelligencePacket summary
  - Summary includes candidates with confidence
  - Telemetry links page_intelligence call to main planner call

## Required integration tests

- `test_weak_dom_page_intelligence_flow.py`:
  - Weak div/span page triggers page intelligence call
  - Fake model processes page
  - Main planner receives summary
  - Step Runner validates proposed locator (no action without validation)
- `test_page_intelligence_backend_validation.py`:
  - Backend validates page intelligence candidate before action
  - Locator is re-validated live against page state

## Fixture/page needs

- Weak div/span fixture page (or use existing fixture from S5-011 planning)

## Paid E2E requirement

None (fake model only).

## Acceptance criteria

- [ ] page_intelligence_summarizer call routed through LLMRuntimeController
- [ ] Weak page flow: DOM → fake model → PageIntelligencePacket → main planner
- [ ] Main planner receives summary, not raw DOM
- [ ] Telemetry links both calls (page intelligence + planning)
- [ ] Step Runner validates all candidates before action
- [ ] No action without live validation
- [ ] Fake model integration works end-to-end

## Evidence

Will include:
- LLMRuntimeController wiring for page_intelligence_summarizer
- Fake model integration code
- Unit and integration test output
- Telemetry showing both calls
- Step Runner validation logs

## Verification commands/results

```bash
pytest tests/test_page_intelligence_summarizer_call.py -v
pytest tests/test_page_intelligence_flow.py -v
pytest tests/test_page_intelligence_to_main_planner_contract.py -v
pytest tests/test_weak_dom_page_intelligence_flow.py -v
pytest tests/test_page_intelligence_backend_validation.py -v

# Trace: weak DOM → page intelligence → summary → main planner → validation
grep -E "page_intelligence_summarizer|PageIntelligencePacket|backend.*validate" test_output.log
```

## Risk

- **Medium:** Fake model output may not reflect real model behavior
- **Low:** Main planner may need adjustment if it expects raw DOM context

## Mitigation

- Contract tests explicit about summary format
- Controlled E2E (S5-013) validates quality with real LLM
- Main planner can fall back to raw DOM if summary missing (logged)
