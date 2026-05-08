# INT-CALL-001 Deterministic fast path for simple picked-element actions

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: Backend / LLM Runtime / DOM
Priority: P0

## Source docs

- Complete LLM Mode P0 Scenario Spec
- Backend Event Contract
- Complete LLM Mode Runtime Policy Spec
- PRD v2.3 LLM Runtime
- Sprint 3 cost optimization plan

## Problem / Goal

Current simple flows may still make too many LLM calls.

For simple picked-element actions, the backend often has enough information to create a plan deterministically:

- user picked an element
- user intent is simple
- locator candidate validates uniquely
- action/assertion is obvious

Goal:

Avoid LLM calls for high-confidence simple picked-element flows while preserving backend confirmation and execution safety.

Examples:

- click this button
- assert this heading is visible
- fill this input with test@example.com

## Scope

Add deterministic fast path for simple picked-element actions.

Expected flow:

1. classify simple picked-element intent deterministically
2. build deterministic plan proposal
3. validate locator programmatically
4. emit plan_ready
5. wait for user confirmation
6. execute through backend runtime only after confirmation

LLM should be used only if:

- intent is ambiguous
- locator confidence is low
- locator validates to 0 or multiple elements
- requested action/assertion is unsupported by deterministic parser
- user asks for broader reasoning

## Out of scope

- Full intent classifier LLM routing
- Multi-step journey planning
- Page/section recommendation mode
- Multi-model routing
- Removing confirmation gate

## Required tests

- Test simple picked click reaches plan_ready with zero LLM calls when deterministic confidence is high.
- Test simple visible assertion reaches plan_ready with zero LLM calls when target is clear.
- Test ambiguous picked action still asks clarification or uses LLM path.
- Test deterministic fast path still requires user confirmation before execution.
- Test telemetry records model_called=false or llm_calls=0 for the fast path.

## Acceptance criteria

- At least one current simple E2E flow reduces LLM call count.
- No browser-changing action occurs before confirmation.
- Backend remains runtime truth.
- Existing 5 E2E tests still pass.
- Token report shows reduced call count for simple flows.

## Deterministic confidence definition

A simple picked-element flow qualifies for the deterministic fast path only when all three conditions are true:

1. Locator validates to exactly one visible/compatible element.
2. Action verb is in the deterministic action set:
   - click
   - fill
   - assert_visible
   - assert_text
3. User message has no compound/multi-step pattern.

Compound/multi-step examples that must not use the zero-LLM fast path:

- "click this and validate the next page"
- "fill this form and submit"
- "test this whole section"
- "check everything on this page"
- "click this, then verify the result"

If any condition fails, use the normal LLM/planning path or ask clarification.

## Evidence

To be filled during implementation.

## Notes

This ticket addresses call count reduction, not only prompt size.
