# INT-TOOL-002 Purpose-scoped tool schema exposure

Status: Planning
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime / Tool Policy
Priority: P0

## Problem

Tool schemas are the largest token source. Planning calls expose 6 tools and execution calls expose around 15 tools repeatedly.

## Source / architecture rule

- runtime/tool_registry.py
- runtime/telemetry.py
- runtime/skill_policy.py
- Complete LLM Mode Runtime Policy Spec
- Sprint 3 token diagnosis report

## Scope

Minimize tools exposed per call based on:
- phase
- purpose
- next expected operation
- deterministic vs model-needed path

Examples:
- plan_diff_editor: no browser/action tools
- simple planning: only send_to_overlay / ask_user if needed
- locator_specialist: locator tools only
- execution of confirmed click child: expose only action_click and required reporting tool if safe
- no-model deterministic path: expose no tools because no model call happens

## Out of scope

- Removing backend validation
- Removing recovery tools globally
- Frontend changes

## Required tests

- tool schema list is smaller for purpose-specific planning
- execution next-child tool exposure is minimized but still correct
- blocked tool is not available to wrong purpose
- telemetry shows lower tools_exposed_count/tool_schema_tokens

## Acceptance criteria

- tool_schema_tokens reduce for simple flows
- no required tool missing for valid flow
- all focused tool policy tests pass

## Cost-aware verification plan

Run unit/tool-policy tests.
Run one E2E smoke after wiring if needed.
Full E2E only at final acceptance.

## Evidence

To be filled during implementation.

## Notes

This is the main prompt-size lever after call removal.
