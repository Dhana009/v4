# S5-001B Controller raw-response tool-call preserving planning path

Status: Done
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/llm_runtime_controller.py, agent.py

## Evidence

Status: Done

Problem:
- S5-001 added planning-call telemetry attribution but did not close the live controller-routing gap.
- `step_plan_normalizer` still called `model_router.call(...)` directly in `agent.py`.
- `LLMRuntimeController.call()` returns validated content-only results and drops raw provider `message.tool_calls`, which the planning loop needs for `send_to_overlay`, `ask_user`, and similar tool-driven planning behavior.

Implemented:
- Added `LLMRuntimeController.call_with_raw_response(...)` in `runtime/llm_runtime_controller.py`.
- The new controller path applies the same purpose policy resolution, context preparation, skill analysis, tool filtering, token-budget guard, and controller telemetry emission as the content-only path.
- The raw-preserving result now returns:
  - `raw_response`
  - `raw_message`
  - `content`
  - `tool_calls`
- Kept existing `LLMRuntimeController.call()` behavior unchanged for content-only callers such as `plan_diff_editor`.
- Added `AgentLoop._call_step_plan_normalizer_controller(...)` and routed the live `step_plan_normalizer` planning turn through the controller boundary in `agent.py`.
- Kept the direct `model_router.call(...)` fallback only when controller state is absent on lightweight test stubs built with `AgentLoop.__new__`.

Controller interface decision:
- Chose the smallest safe option close to Option B.
- Added a new controller entrypoint `call_with_raw_response(...)` instead of changing `call(...)` return semantics.
- This preserves backward compatibility for existing content-only controller callers while making the live planning path controller-owned.

Tests added/updated:
- `tests/test_llm_runtime_controller_contract.py`
  - Added controller contract proof that `call_with_raw_response(...)` preserves `tool_calls` for `step_plan_normalizer`.
- `tests/test_planning_through_controller_fake_model.py`
  - Added proof that the live planning path uses controller for `step_plan_normalizer` and does not call `model_router.call(...)` for that purpose.
  - Added malformed controller-response test proving no `plan_ready`, `step_recorded`, `code_update`, or `run_completed` is emitted from malformed content-only output on the controller planning path.

Commands run:
- `python -m py_compile agent.py runtime/llm_runtime_controller.py tests/test_planning_through_controller_fake_model.py tests/test_llm_runtime_controller_contract.py tests/fake_llm_factory.py`
- `python -m pytest tests/test_llm_runtime_controller_contract.py -q`
- `python -m pytest tests/test_planning_through_controller_fake_model.py -q`
- `python -m pytest tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_fake_llm_factory.py -q`
- `python -m pytest tests/test_telemetry_breakdown.py tests/test_token_report.py -q`
- `python -m pytest tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py -q`

Results:
- `py_compile`: OK
- `tests/test_llm_runtime_controller_contract.py`: 8 passed
- `tests/test_planning_through_controller_fake_model.py`: 20 passed
- `tests/test_backend_event_sequences.py tests/test_deterministic_fast_path.py tests/test_fake_llm_factory.py -q`: 53 passed
- `tests/test_telemetry_breakdown.py tests/test_token_report.py -q`: 46 passed
- `tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py -q`: 13 passed

Interpretation:
- `step_plan_normalizer` now routes through controller policy handling in the live planning path.
- Raw provider `tool_calls` are preserved through the controller boundary.
- `plan_diff_editor` remains on the existing content-only controller path and did not require behavior changes.
- Cluster 3 work can now target real controller-owned planning traffic instead of dead policy plumbing.

Changed files:
- `runtime/llm_runtime_controller.py`
- `agent.py`
- `tests/test_llm_runtime_controller_contract.py`
- `tests/test_planning_through_controller_fake_model.py`
- `.tasks-md/Done/S5-001B Controller raw-response tool-call preserving planning path.md`

Commit:
- pending
