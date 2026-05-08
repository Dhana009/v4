# INT-DOM-002 Compact page and section intelligence packet

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: DOM Intelligence / LLM Runtime
Priority: P1

## Source docs

- Complete LLM Mode P0 Scenario Spec
- PRD v2.3 DOM Strategy
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 cost optimization plan

## Problem / Goal

For page/section-level requests, the main LLM should not receive raw full DOM by default.

Goal:

Create a compact page/section intelligence packet that summarizes useful page structure for planning and recommendation.

## Scope

Pipeline:

dom/page extract
→ deterministic page summary
→ candidate locator groups
→ ambiguity/risk flags
→ compact page intelligence payload
→ main LLM receives summary, not raw DOM

Packet should include:

- page_id
- url/title
- sections
- headings
- CTAs
- forms/inputs
- important text blocks
- candidate locator groups
- semantic quality
- ambiguities
- risk flags
- token estimate
- source: deterministic | model | mixed

## Out of scope

- Cheap/nano model production split
- Full page-map persistence
- Full visual AI / screenshot reasoning
- Frontend redesign

## Required tests

- Test page intelligence packet includes sections/headings/CTAs/forms.
- Test weak DOM produces semantic quality/risk flags.
- Test main planner receives page intelligence summary instead of raw DOM for page/section request.
- Test raw DOM requires explicit escalation.
- Test token estimate is attached.

## Acceptance criteria

- Page/section requests use compact structured summary.
- Raw DOM is excluded by default.
- Token report shows reduced DOM/context token contribution.
- Existing 5 E2E tests still pass.

## Evidence

To be filled during implementation.

## Notes

This supports future page validation/recommendation mode while reducing token cost now.
