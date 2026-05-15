# Agent Modularization Design
**Date:** 2026-05-09  
**Scope:** Full industrial-standard refactor of `agent.py` (9,302 lines) and `server.py` (433 lines) into focused, independently testable modules.  
**Approach:** Option A — big-bang full extraction in one pass, full test suite validation before commit.

---

## Problem Statement

`agent.py` is a single 9,302-line class (`AgentLoop`) with 223 methods spanning 8+ unrelated domains: LLM orchestration, tool dispatch, plan management, plan correction, recording, replay, codegen, locator resolution, step lifecycle, event emission, skill loading, and WebSocket I/O. This violates single-responsibility, makes the codebase hard to navigate, test, and extend.

`server.py` routes WebSocket commands directly into `AgentLoop` without a clear routing layer.

---

## Target Architecture

```
agent v4/
├── agent.py                         # AgentLoop — thin orchestrator (~250 lines)
├── server.py                        # Kept; imports from ws/router.py
│
├── llm/
│   ├── __init__.py
│   ├── orchestrator.py              # LLM call loop, message history management
│   ├── tool_definitions.py          # All tool JSON schemas (_build_tool_definitions)
│   └── tool_dispatcher.py           # _dispatch_tool + all _tool_* action handlers
│
├── plan/
│   ├── __init__.py
│   ├── builder.py                   # _build_plan_ready_payload, _build_planned_children, _build_plan_ready_parent_step
│   ├── correction.py                # _classify_plan_correction, _run_plan_diff_editor_correction, diff editor pipeline
│   ├── confirmation.py              # _wait_for_plan_confirmation, _send_plan_ready_after_confirmation
│   └── state.py                     # _build_active_plan_state, confirmed execution contract, plan cursor/version
│
├── recording/
│   ├── __init__.py
│   ├── recorder.py                  # _record_step_payload, _auto_record_successful_step, _mark_step_recorded
│   ├── replay.py                    # replay_one, replay_all, all _replay_* helpers
│   └── codegen.py                   # _build_generated_line, _locator_to_playwright_expression, _build_code_update_payload
│
├── locator/
│   ├── __init__.py
│   └── resolver.py                  # _build_locator_from_strategy, _build_locator_candidates, _resolve_locator, helpers
│
├── step/
│   ├── __init__.py
│   └── manager.py                   # _mark_step_executing/_failed/_recorded, _get_step_context, step state machine
│
├── event/
│   ├── __init__.py
│   └── emitter.py                   # _send, _emit_backend_event_now, _emit_recovery_needed_event, _emit_run_completed_event
│
├── skills/
│   ├── __init__.py
│   └── loader.py                    # _load_skills_for_steps, _read_skill, _load_phase_skill_expansion, _log_skill_*
│
└── ws/
    ├── __init__.py
    └── router.py                    # WebSocket command routing (extracted from server.py)
```

---

## Module Responsibilities

### `agent.py` — Thin Orchestrator
- Owns `AgentLoop.__init__`: wires all module instances together
- Owns `run()`: top-level execution entry point, delegates to domain modules
- Owns lifecycle state (`_reset_lifecycle_state`, phase, session ID)
- Owns capability gap recording (`_record_capability_gap`)
- No domain logic — only coordination

### `llm/orchestrator.py`
- LLM call loop logic currently embedded in `run()`
- Message history append helpers (`_assistant_message_entry`, `_append_tool_response`, `_append_skipped_tool_response`)
- User followup logic (`_should_request_user_followup`, `_looks_like_completion_message`, `_format_user_followup_message`)
- Correction followup detection (`_is_correction_followup`)

### `llm/tool_definitions.py`
- `_build_tool_definitions()` — returns the full list of 15 tool JSON schemas
- Pure data; no I/O, no state

### `llm/tool_dispatcher.py`
- `_dispatch_tool()` — routes tool name → handler
- All `_tool_action_click`, `_tool_action_fill`, `_tool_action_assert`, `_tool_page_*`, `_tool_scroll_into_view`, `_tool_browser_get_state`, `_tool_screenshot_take`, `_tool_dom_extract`, `_tool_locator_find`, `_tool_locator_validate`, `_tool_send_to_overlay`, `_tool_ask_user`
- `_normalize_wait_until`, `_is_browser_state_tool`, `_parse_tool_args`
- Browser action helpers (`_capture_browser_state`, `_normalize_browser_state_snapshot`, `_build_observed_outcome`, `_capture_action_context`, `_action_name_for_tool`)

### `plan/builder.py`
- `_build_plan_ready_payload`, `_build_plan_ready_parent_step`
- `_build_planned_children`, `_build_planned_child_description`
- `_build_recorded_children`, `_build_recorded_child_description`, `_is_technical_recorded_label_text`
- `_infer_operation_type`, `_infer_planned_operation_sequence`
- `_normalize_steps`, `_format_steps`, `_validate_recording_steps`

### `plan/correction.py`
- `_classify_plan_correction`, `_build_plan_correction_validation_feedback`
- `_run_plan_diff_editor_correction`, `_call_plan_diff_editor_controller`
- `_synthesize_plan_diff_editor_output`, `_validate_plan_diff_editor_output`
- `_build_plan_diff_editor_schema_message`, `_build_plan_correction_context_message`
- `_build_plan_correction_clarification_message`, `_build_plan_correction_state`
- `_build_structured_plan_correction_payload_from_diff`, `_patch_value`, `_normalize_step_patch`
- `_validate_structured_plan_correction`, `_validate_structured_plan_step`
- `allocate_operation_id`, `_build_plan_correction_added_child`
- `_remember_plan_review_context`, `_build_plan_step_context_lines`
- `_build_plan_correction_message`, `_append_plan_correction_message`
- `_build_plan_correction_child_description`, `_build_plan_correction_operation_context_lines`
- `_select_plan_correction_child_target`
- Clear state helpers: `_clear_plan_review_context`, `_clear_active_plan_correction_state`

### `plan/confirmation.py`
- `_wait_for_plan_confirmation`
- `_send_plan_ready_after_confirmation`
- `_confirmation_context`, `_confirmation_context_mismatch_reason`
- `_completed_run_confirmation_rejection_reason`

### `plan/state.py`
- `_build_active_plan_state`, `_current_active_plan_state`, `_current_plan_version`
- `_plan_steps_from_state`, `_plan_child_operations_from_step`
- `_plan_operation_text`, `_plan_operation_type`, `_plan_operation_signature`
- `_plan_operation_types_from_state`, `_plan_operation_signatures_from_state`
- `_sequence_contains_subsequence`
- Confirmed execution contract: `_build_confirmed_execution_plan`, `_store_confirmed_execution_plan`
- `_confirmed_execution_contract_for_step`, `_confirmed_execution_results_for_step`
- `_confirmed_execution_next_child_for_step`, `_confirmed_execution_step_ready_to_record`
- `_build_confirmed_execution_context_message`, `_build_confirmed_execution_tool_call`
- `_locator_matches_confirmed_execution_child`, `_assertion_matches_confirmed_execution_child`
- `_value_matches_confirmed_execution_child`, `_describe_confirmed_execution_child`
- `_describe_confirmed_execution_call`, `_record_confirmed_execution_child_result`
- `_validate_confirmed_execution_tool_call`
- `_infer_confirmed_execution_child_assertion`, `_normalize_confirmed_execution_child`
- `_current_confirmed_execution_cursor`, `_log_confirmed_execution_cursor`
- Clear state helpers: `_clear_confirmed_execution_contract_state`, `_clear_active_plan_state`

### `recording/recorder.py`
- `_record_step_payload`, `_auto_record_successful_step`
- `_mark_step_recorded`, `_advance_recording_cursor`
- `_get_successful_action_for_step`, `_get_successful_action_history_for_step`
- `_has_successful_action_to_record`, `_should_block_additional_execution_action`
- `_should_block_recording_wait_tool`
- `_build_step_record_payload`

### `recording/replay.py`
- `replay_one`, `replay_all`
- `_get_replay_recorded_step_payload`, `_get_replay_action_history`
- `_get_replay_recorded_start_state`, `_get_replay_precondition_target_locator`
- `_validate_replay_target_locator`, `_log_replay_precondition_failure`
- `_build_replay_precondition_failure_result`, `_check_replay_precondition`
- `_get_replay_archive_step_ids`, `_safe_replay_error_message`
- `_append_recorded_step_payload`, `_append_code_update_payload`

### `recording/codegen.py`
- `_build_generated_line`, `_locator_to_playwright_expression`
- `_build_code_update_payload`
- `_match_tool_locator_call`, `_match_tool_locator_text`, `_match_tool_locator_role`
- `_locator_label_hint`, `_canonical_confirmed_execution_locator`
- `_derive_element_name`, `_build_recorded_child_description` (shared with plan/builder — stays in codegen, re-exported from plan/builder)

### `locator/resolver.py`
- `_build_locator_from_strategy`, `_build_locator_candidates`, `_resolve_locator`
- `_is_stable_locator_strategy`, `_infer_role`, `_build_suggested_scope`
- `_css_escape`, `_text_escape`, `_normalize_space`, `_normalize_assertion_text`
- `_tool_string_escape`, `_tool_string_unescape`, `_xpath_literal`
- `_clean_markup`, `_summarize`

### `step/manager.py`
- `_mark_step_executing`, `_mark_step_failed`, `_clear_failed_step_success_state`
- `_mark_step_skipped`
- `_get_step_context`, `_resolve_recording_target_step`, `_get_failed_step_context`
- `_score_step_context`, `_resolve_step_context`
- `_current_pending_step`, `_find_step_for_recording`
- `_has_unresolved_steps`, `_has_unresolved_failure`, `_all_steps_done`, `_all_steps_resolved`
- `_step_state_summary`, `_derive_step_context_element_name`, `_step_context_text`
- `_coerce_step_number`, `_prepare_recording_steps`, `_derive_locator_from_step_context`
- `_normalize_steps` (re-exported)

### `event/emitter.py`
- `_send` (async WebSocket send)
- `_emit_backend_event_now`
- `_emit_recovery_needed_event`
- `_emit_run_completed_event`

### `skills/loader.py`
- `_load_skills_for_steps`, `_read_skill`, `_load_phase_skill_expansion`
- `_skill_entries_from_loaded_skills`, `_compose_skill_prompt_from_entries`, `_sync_skill_prompt_from_entries`
- `_log_skill_load`, `_log_skill_diagnostics`, `_requires_complex_codegen`

### `ws/router.py`
- WebSocket command dispatch logic extracted from `server.py`
- Maps incoming command types to `AgentLoop` method calls
- Owns reconnect grace logic (`_ws_reconnect_grace`)

---

## Interface Pattern

Each module is implemented as a **class that receives `AgentLoop` (or its relevant state) via constructor injection**. This avoids circular imports and keeps `AgentLoop` as the single owner of mutable state.

```python
# Example: event/emitter.py
class EventEmitter:
    def __init__(self, ws, loop_ref):
        self._ws = ws
        self._loop = loop_ref  # for phase/session access only

    async def send(self, msg_type: str, **kwargs) -> None: ...
    def emit_now(self, msg_type: str, **kwargs) -> None: ...
```

`AgentLoop.__init__` wires everything:
```python
self._emitter = EventEmitter(ws, self)
self._step_manager = StepManager(self._emitter, self)
self._locator_resolver = LocatorResolver()
self._plan_state = PlanState(self._emitter)
# etc.
```

---

## Dependency Graph (no cycles)

```
locator/resolver  ←── no deps on other new modules
step/manager      ←── event/emitter
skills/loader     ←── no deps on other new modules
event/emitter     ←── no deps on other new modules
recording/codegen ←── locator/resolver
recording/recorder←── step/manager, event/emitter, recording/codegen
recording/replay  ←── step/manager, event/emitter, locator/resolver
plan/state        ←── event/emitter, locator/resolver
plan/builder      ←── locator/resolver
plan/correction   ←── plan/state, plan/builder, event/emitter
plan/confirmation ←── plan/state, event/emitter
llm/tool_definitions ← no deps
llm/tool_dispatcher  ← locator/resolver, step/manager, recording/recorder, event/emitter
llm/orchestrator     ← all plan/*, llm/tool_dispatcher, skills/loader, step/manager, event/emitter
agent.py (AgentLoop)  ← all of the above
```

---

## Testing Strategy

- **Baseline:** 528 tests currently passing — must stay green after refactor
- **No new test files required** — existing tests import from `agent` module; internal refactor keeps the public interface intact
- **Import compatibility:** `AgentLoop` remains importable from `agent.py`; `replay_one`, `replay_all`, `run` remain methods on `AgentLoop`
- **Full test suite run** before committing
- **E2E tests** (`tests/e2e/`) remain unchanged — they test behavior, not internals

---

## Execution Plan

1. Extract `event/emitter.py` — zero dependencies, low risk
2. Extract `locator/resolver.py` — pure functions, zero state
3. Extract `skills/loader.py` — reads files, no mutation
4. Extract `step/manager.py` — depends on emitter
5. Extract `recording/codegen.py` — depends on locator
6. Extract `recording/recorder.py` — depends on step, emitter, codegen
7. Extract `recording/replay.py` — depends on step, emitter, locator
8. Extract `plan/state.py` — depends on emitter, locator
9. Extract `plan/builder.py` — depends on locator
10. Extract `plan/correction.py` — depends on plan/state, plan/builder, emitter
11. Extract `plan/confirmation.py` — depends on plan/state, emitter
12. Extract `llm/tool_definitions.py` — pure data
13. Extract `llm/tool_dispatcher.py` — depends on locator, step, recorder, emitter
14. Extract `llm/orchestrator.py` — depends on all plan/*, tool_dispatcher, skills, step, emitter
15. Slim `agent.py` to thin orchestrator (~250 lines)
16. Extract `ws/router.py` from `server.py`
17. Run full test suite — fix any regressions
