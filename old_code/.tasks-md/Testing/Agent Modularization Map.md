# Agent Modularization Map

Status: Testing
Sprint: Sprint 3.5
Type: Refactor Readiness
Owner: Runtime Architecture
Priority: P0

## Scope

Static modularization audit for `agent.py` and adjacent backend/runtime boundaries. No production behavior changes.

## Current size and boundary

- `agent.py`: 9,517 lines
- `server.py`: 433 lines
- `agent.py` still owns the orchestration spine, confirmation gate, correction flow, confirmed execution contract, recording/codegen handoff, replay, and a large share of tool handlers.
- `server.py` is relatively thin and should stay thin. Sprint 3.5 should prefer extracting logic out of `agent.py`, not inflating `server.py`.

## Map

| Responsibility | Current functions/classes | Existing tests | Missing characterization tests | Risk | Suggested module | Extraction order |
|---|---|---|---|---|---|---:|
| Lifecycle orchestration | `run` (`agent.py:1353`), `_send_plan_ready_after_confirmation` (`8653`), `_wait_for_plan_confirmation` (`9004`), `_emit_run_completed_event` (`322`), `_emit_recovery_needed_event` (`279`) | `tests/test_event_contract.py`, `tests/test_event_sequence_contract.py`, `tests/test_late_event_contract.py`, `tests/test_completion_guard.py`, E2E lifecycle smoke | Cheap live websocket sequence harness for full command -> confirm -> execute -> complete flow | High | `runtime/agent_loop.py` | 7 |
| Deterministic fast path gateway | `_try_deterministic_fast_path` (`2292`), `_execute_deterministic_fast_path_confirmed_plan` (`2410`) | `tests/test_deterministic_fast_path.py`, `tests/test_plan_model.py`, `tests/test_code_update.py`, deterministic E2E acceptance | Shared integration harness proving websocket lifecycle, confirmation gate, and parity with fake-LLM path | Medium | `runtime/fast_path_gateway.py` | 3 |
| Confirmed execution contract | `_build_confirmed_execution_plan` (`4016`), `_validate_confirmed_execution_tool_call` (`4574`), confirmed cursor/result helpers nearby | `tests/test_recorded_step_model.py`, `tests/test_recording_codegen_truth_contract.py`, `tests/test_plan_correction.py`, `tests/test_event_sequence_contract.py` | Focused integration coverage proving confirmed plan storage and live execution gating through server boundary | High | `runtime/confirmed_execution.py` | 5 |
| Plan-ready payload building | `_build_plan_ready_payload` (`7935`), `_build_plan_ready_parent_step` (`7546`), planned/recorded child shaping nearby | `tests/test_event_contract.py`, `tests/test_plan_model.py`, `tests/test_plan_correction.py`, frontend rendering contract tests | Golden sequence test proving `plan_ready` semantics in a live backend flow | Medium-High | `runtime/plan_ready_builder.py` | 4 |
| Structured correction flow | `_run_plan_diff_editor_correction` (`3589`), `_build_plan_correction_state` (`5165`), `_validate_structured_plan_correction` (`5800`), correction message/context helpers | `tests/test_plan_correction.py`, `tests/test_recovery_scope_guard.py`, `tests/test_late_event_contract.py` | Websocket-routed correction command harness and one golden correction sequence | High | `runtime/correction_flow.py` | 6 |
| Recording and code generation | `_build_step_record_payload` (`7130`), `_build_code_update_payload` (`7898`), `_append_code_update_payload` (`510`), recorded child shaping | `tests/test_recorded_step_model.py`, `tests/test_recording_codegen_truth_contract.py`, `tests/test_code_update.py`, `tests/test_event_contract.py` | Cheap integration sequence proving execution evidence -> `step_recorded` -> `code_update` -> `run_completed` | High | `runtime/recording_codegen.py` | 5 |
| Replay and snapshot state | `replay_one` (`811`), `replay_all` (`965`), `_build_spec_snapshot` (`1103`), `_build_session_state_payload` (`1149`) plus `runtime/spec_snapshot.py` | `tests/test_replay_one.py`, `tests/test_replay_all.py`, `tests/test_snapshot_archive_contract.py`, `tests/test_save_snapshot_ws.py` | Live snapshot round-trip harness and characterization of server boundary around save/replay routes | Medium | `runtime/replay_contract.py` plus keep `runtime/spec_snapshot.py` | 2 |
| DOM intelligence and locator tools | `_dispatch_tool` (`8291`), `_tool_dom_extract` (`8320`), `_tool_locator_find` (`8372`), `_tool_locator_validate` (`8433`) | `tests/test_agent_dom_extract_contract.py`, `tests/test_agent_locator_handler_contract.py`, DOM contract suites | Minimal characterization test for dispatch table ownership and one fake execution integration around handler outputs | Medium-Low | `runtime/dom_tool_handlers.py` | 4 |
| WebSocket command boundary | `server.py` `ws_endpoint` (`226`), `_current_command_state` (`102`), `_build_session_state_event` (`133`), `_legacy_control_message` (`145`), `_attach_or_create_run_session` (`70`) | `tests/test_event_contracts.py`, `tests/test_command_contract.py`, `tests/test_process_boundary_contract.py`, `tests/test_ws_reconnect_grace.py`, `tests/test_save_snapshot_ws.py` | Reusable websocket integration harness that covers valid commands, stale/late rejection, and correlation metadata | Medium | `runtime/websocket_commands.py` or keep thin in `server.py` | 1 |
| LLM policy and tool gating | `runtime/llm_runtime_controller.py`, `runtime/llm_policy_gateway.py`, `runtime/tool_registry.py` | `tests/test_llm_runtime_controller_contract.py`, `tests/test_llm_planning_contracts.py`, `tests/test_llm_specialist_contracts.py`, `tests/test_llm_policy_gateway.py`, `tests/test_tool_registry.py` | Cheap integration comparison between deterministic and fake-LLM ambiguous planning paths | Low | Keep split as-is | Stable |
| Backend event contracts | `runtime/event_contracts.py`, event/session/rejection builders and normalization | `tests/test_event_contracts.py`, `tests/test_event_contract.py`, `tests/test_command_contract.py` | Clarify `run_started` / `execution_started` contract and bridge into golden sequence suite | Low | Keep split as-is | Stable |

## Safest extraction order

1. WebSocket command boundary harness and event contract clarification first. This is test-first infrastructure, not a large refactor.
2. Replay/snapshot helpers are relatively isolated and already have dedicated tests.
3. Deterministic fast path gateway is a practical early extraction once the cheap lifecycle harness exists.
4. DOM intelligence / locator handlers and plan-ready builder are reasonable mid-risk splits after characterization tests are green.
5. Confirmed execution and recording/codegen should move only after integrated sequence tests exist.
6. Structured correction flow should move only after websocket correction routing and golden correction tests exist.
7. Lifecycle orchestration should be last. It is the highest-risk extraction because it coordinates nearly every other subsystem.

## Blocking conditions before extraction

- Do not extract lifecycle orchestration until the cheap websocket integration harness from `TEST-ARCH-003` exists.
- Do not extract any area that participates in event order until `TEST-ARCH-002` golden backend sequences exist.
- Do not extract confirmed execution or recording/codegen until `TEST-ARCH-004` proves the backend-owned evidence path in integration.
- Do not extract fast-path or LLM routing behavior until `TEST-ARCH-005` proves both paths preserve the same backend truth rules.
- Do not treat `run_started` and `execution_started` as stable extraction seams until `TEST-ARCH-006` clarifies the contract.
