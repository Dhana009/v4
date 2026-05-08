# INT-DOM-002B Wire page intelligence into live dom_extract result

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: DOM Intelligence
Priority: P1

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

To be filled during implementation.

## Notes

This is the live DOM compaction path for planning and locator work.
