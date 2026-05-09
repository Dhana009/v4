# SPRINT-004 Agent module extraction map

Status: In Progress
Sprint: Sprint 4
Owner: Runtime Architecture

## Current responsibility clusters

| Cluster | Current area in `agent.py` | Target module | Risk | Tests protecting it | Extraction order | Final status |
|---|---|---|---|---|---:|---|
| Deterministic fast path gateway | `_try_deterministic_fast_path` | `runtime/deterministic_fast_path_gateway.py` | Medium | `tests/test_deterministic_fast_path.py`, `tests/test_backend_event_sequences.py`, `tests/test_lifecycle_checkpoint_contract.py` | 1 | Extracted |
| Snapshot/archive seam | `_build_spec_snapshot` import boundary | `runtime/snapshot_archive.py` facade over `runtime/spec_snapshot.py` | Low | `tests/test_snapshot_archive_contract.py`, `tests/test_replay_one.py`, `tests/test_save_spec.py` | 2 | Extracted |
| DOM/locator handlers | `_tool_dom_extract`, `_tool_locator_find`, `_tool_locator_validate` | `runtime/agent_locator_handlers.py` | Medium | `tests/test_agent_locator_handler_contract.py`, `tests/test_agent_dom_extract_contract.py`, `tests/test_dom_locator_contracts.py`, `tests/test_dom_locator_advanced_contracts.py` | 3 | Extracted |
| Extracted boundary cleanup | extracted module seams only | n/a | Low | focused helper suites plus non-E2E regression | 4 | Completed |
| Action/assert handlers | `_tool_action_click`, `_tool_action_fill`, `_tool_action_assert` | possible `runtime/agent_action_handlers.py` | Medium-High | `tests/test_recorded_step_model.py`, `tests/test_code_update.py`, `tests/test_recording_codegen_truth_contract.py`, `tests/test_replay_one.py` | 5 | Blocked in this batch |
| Page/navigation handlers | `_tool_page_navigate`, `_tool_page_go_back`, `_tool_page_go_forward`, `_tool_page_reload`, `_tool_scroll_into_view`, `_tool_browser_get_state`, `_tool_screenshot_take` | possible `runtime/agent_page_handlers.py` | Medium-High | partial focused coverage only; broad regression covers some fallout | 6 | Blocked in this batch |
| Replay handlers and preconditions | replay helpers plus `replay_one` / `replay_all` | possible `runtime/agent_replay_handlers.py` | High | `tests/test_replay_one.py`, `tests/test_snapshot_archive_contract.py`, websocket replay tests | 7 | Blocked in this batch |
| Command/event bridge glue | overlay dispatch and confirmation glue | possible `runtime/agent_command_dispatch.py`, `runtime/agent_event_bridge.py` | High | websocket integration and event contract suites | 8 | Blocked in this batch |
| LLM planning/runtime glue | model-call orchestration, prompt/context glue | possible `runtime/agent_llm_planning.py`, `runtime/agent_plan_review.py` | High | `tests/test_llm_runtime_controller_contract.py`, `tests/test_llm_planning_contracts.py`, `tests/test_plan_correction.py` | 9 | Blocked in this batch |
| Recovery/session helpers | recovery formatting, session payload helpers | possible `runtime/agent_recovery_helpers.py`, `runtime/agent_session_state.py` | High | lifecycle/event/replay suites | 10 | Blocked in this batch |
| Lifecycle orchestration | `run`, completion/recovery gating | future high-risk slice | Highest | broad contract and sequence suites only | 11 | Explicitly blocked |
| Correction flow | plan diff editor and structured correction | future high-risk slice | Highest | `tests/test_plan_correction.py`, lifecycle/late-event suites | 12 | Explicitly blocked |
| Confirmed execution contract | confirmed plan/cursor/result logic | future high-risk slice | Highest | `tests/test_recorded_step_model.py`, `tests/test_recording_codegen_truth_contract.py` | 13 | Explicitly blocked |
| Recording/codegen truth | step record and code update builders | future high-risk slice | Highest | recording/code update suites | 14 | Explicitly blocked |
| Main run loop | orchestration spine | future high-risk slice | Highest | broad regression only | 15 | Explicitly blocked |

## Blocked areas

- Lifecycle orchestration
- Correction flow
- Confirmed execution
- Recording/code_update
- Main run loop
- Replay handler extraction beyond current snapshot/archive seam
- Action/assert handler extraction without dedicated review gate

## Notes

- The safe Sprint 4 progress in this batch came from already-characterized seams only.
- Remaining candidates are more entangled with execution semantics, replay semantics, or orchestration ownership and should not move without dedicated characterization and review gates.
