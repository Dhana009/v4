# INT-DOM-002B Wire page intelligence into live dom_extract result

Status: Done
Sprint: Sprint 3
Type: Story
Owner: DOM Intelligence
Priority: P1
Started: 2026-05-08 21:08 IST

## Problem

Page intelligence packet exists, but live LLM path still relies on tool-call sequence around DOM extraction.

## Source / architecture rule

- runtime/page_intelligence.py
- runtime/telemetry.py
- Complete LLM Mode Runtime Policy Spec
- PRD v2.3 DOM Strategy

## Scope

For dom_extract:
- build page intelligence packet
- return compact summary to LLM
- preserve raw data only backend-side if needed
- include headings, CTAs, forms, inputs, candidate groups, ambiguity/risk flags

## Out of scope

- Visual AI
- Full page-map persistence
- Frontend redesign

## Required tests

- dom_extract LLM-facing output is compact
- packet includes semantic page facts
- raw DOM requires explicit escalation
- locator behavior remains correct

## Acceptance criteria

- DOM/tool-result tokens reduce
- existing E2E stays green at final acceptance

## Cost-aware verification plan

Run page-intelligence tests.
E2E only at final acceptance unless a focused smoke is necessary.

## Evidence

- `python -m py_compile agent.py tests/test_page_intelligence.py tests/test_agent_dom_extract_contract.py`
- `python -m pytest tests/test_page_intelligence.py tests/test_agent_dom_extract_contract.py tests/test_context_manager.py tests/test_context_budget_gate.py -q`
  - Result: `40 passed`

## Notes

This is the live DOM compaction path for planning and locator work.

Implementation summary:
- `agent._tool_dom_extract()` now returns compact summary text plus structured `page_intelligence`
- Live `dom_extract` keeps headings, CTAs, forms, inputs, semantic quality, ambiguity, and risk flags in compact form
- Raw cleaned markup remains backend-side under `_raw_elements`
- Added direct handler contract tests for page scope and scoped extraction
