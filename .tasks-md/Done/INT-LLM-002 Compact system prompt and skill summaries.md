# INT-LLM-002 Compact system prompt and skill summaries

Status: Done
Sprint: Sprint 3
Type: Story
Owner: LLM Runtime
Priority: P0

## Source docs

- Complete LLM Mode Runtime Policy Spec
- PRD v2.3 LLM Runtime
- autoworkbench_skills_library_v2
- Sprint 3 cost optimization plan

## Problem / Goal

Current LLM calls can include large repeated system/skill prompt content.

Observed example:

- system prompt contains full core/actions skill material
- a single request can reach around 4,000+ input tokens before meaningful user/tool context
- repeated E2E runs multiply this cost

Goal:

Replace broad full-skill prompt loading with purpose-specific compact prompt blocks.

## Scope

Implement compact skill-loading policy:

- core_compact: always loaded, very short
- skill_summary: loaded only for relevant purpose/capability
- full_skill: loaded only on explicit escalation
- debug_skill: loaded only in recovery/debug

Expected behavior examples:

- plan_diff_editor loads no action/browser skill
- simple click/assert flow does not load full actions + assertions + locator skills
- locator flow loads compact locator summary only
- recovery flow may load debug/recovery skill
- telemetry records skills_loaded and skill_tokens

## Out of scope

- Full multi-model routing
- New skill authoring
- Skill content rewrite beyond compact summaries/adapters
- Frontend UI changes

## Required tests

- Test that plan_diff_editor does not load action/browser full skills.
- Test that simple click/assert loads compact core + minimal relevant summaries only.
- Test that full_skill is loaded only when escalation is explicitly requested.
- Test that telemetry reports skill_tokens and loaded skill names.
- Regression test that existing LLM controller/planning tests still pass.

## Acceptance criteria

- System+skill tokens are reduced for simple flows.
- Full skill text is not loaded by default for every LLM call.
- Purpose-specific skill policy is enforced.
- Existing 5 E2E tests still pass.
- Telemetry report shows reduced skill token contribution.

## Skill level mapping

Initial Sprint 3 skill-level mapping:

| Level | Skills |
|---|---|
| core_compact always | llm_runtime_controller, prompt_persona_skill_loading |
| skill_summary by purpose | locator_strategy, backend_step_runner, codegen, contract_testing |
| full_skill on escalation | capability_framework, replay_repair, real_world_fixtures |
| debug_skill on recovery | observability_trace, memory_human_feedback |

Implementation must not load full skill files by default for every call.

If a skill is not listed here, default it to `skill_summary` only after the implementation justifies the purpose/capability that needs it.

## Evidence

To be filled during implementation.

## Notes

Target: reduce system+skill tokens per simple call by at least 50%.
