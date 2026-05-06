# AutoWorkbench Skills Library

These skills are Codex development instruction packs for AutoWorkbench.

## Usage rule

Load the smallest skill pack required for the task. Do not load all skills blindly.

Always include:
```text
00_skill_usage_policy.md
00_architecture_contract.md
01_prd_scope_validation.md
02_tdd_regression_harness.md
03_refactor_safety.md
```

Then add task-specific skills.

## Typical packs

### Backend lifecycle task
```text
backend_step_runner.md
typed_event_contract.md
observability_trace.md
```

### LLM runtime task
```text
llm_runtime_controller.md
prompt_persona_skill_loading.md
memory_human_feedback.md
observability_trace.md
typed_event_contract.md
```

### Locator task
```text
locator_strategy.md
backend_step_runner.md
typed_event_contract.md
observability_trace.md
```

### Frontend Shadow DOM task
```text
frontend_shadow_dom_ui.md
frontend_state_rendering.md
typed_event_contract.md
ux_error_blocking_states.md
```

### E2E/testing task
```text
e2e_product_harness.md
real_world_fixtures.md
contract_testing.md
observability_trace.md
```

### Capability task
```text
capability_framework.md
test_data_secrets.md
permission_safety.md
codegen.md
```

## Codex prompt pattern

```text
Read and follow these skills first:
- .autoworkbench/skills/00_skill_usage_policy.md
- .autoworkbench/skills/00_architecture_contract.md
- .autoworkbench/skills/01_prd_scope_validation.md
- .autoworkbench/skills/02_tdd_regression_harness.md
- .autoworkbench/skills/03_refactor_safety.md
- .autoworkbench/skills/<task-specific>.md

If the task conflicts with PRD/specs, stop and report evidence.
Write tests first where practical.
Do not guess architecture.
Report files changed, tests, commands, and risks.
```
