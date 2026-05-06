# Skill: Skill Usage Policy

## Purpose
Keep Codex on the smallest safe skill pack and stop drift from broad or speculative loading.

## When to use
Use at the start of every AutoWorkbench task that may load repo-local skills.

## Policy
1. Load the smallest skill pack that protects the task.
2. Mandatory core skills:
   - 00_skill_usage_policy.md
   - 00_architecture_contract.md
   - 01_prd_scope_validation.md
   - 02_tdd_regression_harness.md
   - 03_refactor_safety.md
3. Add only task-specific skills that match the requested change.
4. Do not load all skills blindly.
5. PRD + Architecture Contract wins on conflicts.
6. If evidence is missing, unclear, or contradictory, do not guess; stop and report the exact files, logs, traces, or tests needed.
7. Prefer the smallest skill pack that still protects the task.
8. Do not widen scope because a broader skill exists.

## Expected skill-loading header
```text
Read and follow these skills first:
- .autoworkbench/skills/00_skill_usage_policy.md
- .autoworkbench/skills/00_architecture_contract.md
- .autoworkbench/skills/01_prd_scope_validation.md
- .autoworkbench/skills/02_tdd_regression_harness.md
- .autoworkbench/skills/03_refactor_safety.md
- .autoworkbench/skills/<task-specific>.md
```

## Task-specific loading
- Backend lifecycle tasks: add backend_step_runner.md, typed_event_contract.md, observability_trace.md
- LLM runtime tasks: add llm_runtime_controller.md, prompt_persona_skill_loading.md, memory_human_feedback.md, observability_trace.md, typed_event_contract.md
- Locator tasks: add locator_strategy.md, backend_step_runner.md, typed_event_contract.md, observability_trace.md
- Frontend Shadow DOM tasks: add frontend_shadow_dom_ui.md, frontend_state_rendering.md, typed_event_contract.md, ux_error_blocking_states.md
- E2E/testing tasks: add e2e_product_harness.md, real_world_fixtures.md, contract_testing.md, observability_trace.md
- Capability tasks: add capability_framework.md, test_data_secrets.md, permission_safety.md, codegen.md

## Stop conditions
Stop and report if:
- required evidence is missing, unclear, or contradictory
- the task conflicts with PRD or Architecture Contract
- the task needs a broader skill pack without a clear reason
