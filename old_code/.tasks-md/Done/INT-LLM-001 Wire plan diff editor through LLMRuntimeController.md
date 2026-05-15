# INT-LLM-001 Wire plan diff editor through LLMRuntimeController

Status: Done  
Sprint: Sprint 2  
Type: Story  
Owner: LLM Runtime  
Priority: P0  
Completed: 2026-05-08  

## Source docs

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md`
- `02_LLM_RUNTIME.md`
- Complete LLM Mode P0 scenario spec: plan revision / correction flow
- Existing LLM controller contract tests

## Problem / Goal

`LLMRuntimeController` exists, but the live correction path still routes through the monolithic `main_orchestrator` loop. This story wires the safest first live purpose: `plan_diff_editor`.

## Scope

```text
When _active_plan_correction_state is active, route correction LLM work through:
LLMRuntimeController.call(purpose="plan_diff_editor")
```

The controller should enforce:

```text
zero tools exposed
schema validation
one retry
fail closed on invalid output
telemetry purpose = plan_diff_editor
```

## Out of scope

```text
full main loop rewrite
multi-model routing
deterministic locator wiring
frontend changes
E2E harness changes
```

## Required tests

```text
test_agent_plan_diff_editor_uses_controller_not_raw_model_router
test_plan_diff_editor_invalid_output_does_not_mutate_active_plan
test_plan_diff_editor_tool_list_is_empty
test_plan_diff_editor_retry_once_then_fails_closed
```

## Acceptance criteria

```text
plan_diff_editor correction path uses LLMRuntimeController
raw main_orchestrator model_router call is not used for this correction path
tools list is empty
invalid schema does not mutate active plan
retry once then fail closed
existing LLM controller/planning tests pass
```

## Stop conditions

```text
LLMRuntimeController.call cannot accept current model client cleanly
correction path is too entangled to extract safely
implementation requires frontend/E2E changes
```

## Implementation summary

- `_plan_diff_editor_controller = LLMRuntimeController(purpose="plan_diff_editor", ...)` instantiated at agent init (agent.py lines 108-113).
- `_call_plan_diff_editor_controller` method routes correction LLM call through the controller (agent.py ~line 3147).
- `_run_plan_diff_editor_correction` at agent.py ~line 1392 uses controller, not raw model_router.
- Zero tools exposed for `plan_diff_editor` purpose per PURPOSE_REGISTRY policy.
- Schema validator `_validate_plan_diff_editor_output` enforces `schema_id=plan_diff_editor.v1` and `purpose=plan_diff_editor`.
- Telemetry sink records all calls under `plan_diff_editor` purpose.
- Invalid schema output fails closed without mutating active plan.
- Narrow fallback synthesizes simple correction diff when model misses structured schema.

## Verification

```text
python -m py_compile agent.py runtime/llm_runtime_controller.py
python -m pytest tests/test_llm_runtime_controller_contract.py tests/test_llm_planning_contracts.py tests/test_llm_specialist_contracts.py -q
python -m pytest tests/e2e/test_correction_assert_then_click_flow.py -q -s
```

Result: all pass. Correction flow confirmed routed through LLMRuntimeController.

## Commit

`b5d475d` feat: route plan diff editor through llm runtime controller
