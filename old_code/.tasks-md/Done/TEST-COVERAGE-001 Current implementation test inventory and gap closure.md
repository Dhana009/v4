# TEST-COVERAGE-001: Current Implementation Test Inventory and Gap Closure

**Status:** Done
**Branch:** main (ahead 60 of origin)
**Baseline:** 522 tests passing before this task
**Final:** 531 tests passing (9 new tests added)
**Product code changed:** No

---

## Current Implementation Summary

AutoWorkbench / Playwright Automation Co-pilot — backend runtime with:

- `agent.py` / `AgentLoop` (modularized across `plan/`, `llm/`, `recording/`, `step/`, `event/`, `locator/`, `ws/`, `recording/`)
- `server.py` — FastAPI WebSocket server
- `ws/router.py` — `WSRouter` dispatching WS commands
- `runtime/` — event_contracts, deterministic_fast_path, llm_runtime_controller, llm_policy_gateway, snapshot_archive, recovery_manager, phase_tracker, context_manager, skill_manager, tool_registry, model_router, page_intelligence, dom_locator, agent_locator_handlers, spec_snapshot, telemetry, token_report
- Frontend: `frontend/src/main.jsx`, `frontend/aw-ide-panel.jsx`

Architecture invariants enforced:
- Backend owns runtime truth; LLM proposes only
- Frontend renders typed backend events, sends typed commands
- DOM/locator output is advisory (validation does not recover)
- No browser action before plan confirmation
- Deterministic fast path skips LLM for simple single-element intents
- step_recorded / code_update / run_completed require backend evidence

---

## Test Inventory by Category

### Unit (pure helpers, no WS/browser/model orchestration)

| File | What it covers |
|---|---|
| test_assertion_flow.py | has_text normalization, retry, missing expected_value |
| test_capability_gaps.py | gap list append/reset, unknown tool gap recording |
| test_context_budget_gate.py | token cap, DOM summarization, non-tool message pass-through |
| test_context_manager.py | phase instruction insertion, history compaction |
| test_deterministic_fast_path.py (classify_fast_path) | qualify/disqualify logic, compound intent, multi-match, zero-match |
| test_dom_locator_contracts.py | candidate resolution, page snapshot shape, locator ranking |
| test_dom_locator_advanced_contracts.py | assertion target baseline, dynamic UI snapshot, escalation baseline |
| test_llm_policy_gateway.py | gateway decisions: deterministic, planning, tool restriction, confirmation |
| test_model_router.py | accepts/rejects explicit runtime purpose |
| test_page_intelligence.py | packet fields: headings, CTAs, inputs, forms, text blocks |
| test_plan_model.py | click/assert/fill intent creates correct child operation types |
| test_process_boundary_contract.py | normalize_frontend_command: missing type, bad envelope, unknown type, bad version, stale run_id |
| test_recorded_step_model.py | step_recorded payload structure, expected_outcome parent-only metadata, child ordering |
| test_recovery_manager.py | classify_failure: recover/purge flags; locator_validate advisory-only |
| test_skill_loading.py | core always loads, intent-specific skill sets, simple click no codegen |
| test_skill_loading_policy.py | skill tier policies (core_compact, skill_summary, full_skill, debug_skill) |
| test_telemetry_breakdown.py | model call telemetry fields, system tokens, DOM tool tokens, skill tokens |
| test_token_report.py | parse_telemetry_line, build_token_report fields |
| test_tool_registry.py | phase-scoped tool filtering: planning-safe, runtime-all, recording-wait, unknown phase |

### Integration (multiple backend components, AgentLoop + fake model/browser)

| File | What it covers |
|---|---|
| test_agent_dom_extract_contract.py | _tool_dom_extract backend wiring: compact summary + structured page intelligence |
| test_agent_locator_handler_contract.py | _tool_locator_find/_tool_locator_validate wiring, LLM skip for unique deterministic candidate |
| test_backend_event_sequences.py | golden sequences: deterministic click blocks until confirmation then records; assertion golden; runtime rejection; fake-LLM ambiguous path emits plan_ready before execution |
| test_backend_isolation_contract.py | reset_lifecycle_state discards previous run state; stale confirmation/completion/recovery do not bleed into new run |
| test_browser_injection.py | autoworkbench injection script includes backend WebSocket config |
| test_code_update.py | simple click recording emits code_update; multi-action recording flattens lines in order |
| test_completion_guard.py | _all_steps_resolved requires awaiting_step_record clear; pending_recovery blocks; guard stops before second model call |
| test_deterministic_fast_path.py (fast path execution) | _try_deterministic_fast_path executes confirmed plan without LLM; correction falls back; derives expected text; run uses fast path before model loop |
| test_late_event_contract.py | run_completed emitted only once; completed run rejects late confirmation; stale correction cannot mutate current run |
| test_llm_planning_contracts.py | intent_classifier, clarification_generator, journey_planner, plan_diff_editor via LLMRuntimeController with fake model |
| test_llm_runtime_controller_contract.py | purpose registry shape: required fields, runtime-impacting validators, tool exposure, skill loading |
| test_llm_specialist_contracts.py | locator_specialist advisory-only boundary; recovery_diagnoser contract; trace_summarizer skips model; budget guard |
| test_multi_action_safety.py | assert-then-click sequence; confirmed execution contract blocks wrong step; cursor strict rejection; auto-record ends batch |
| test_plan_correction.py | correction re-emits plan_ready; validation preserves reordered children; diff applies assert-before-click |
| test_recovery_scope_guard.py | plan_ready blocked during unresolved recovery; plan_ready outside recovery works; context instruction locks completed steps |
| test_replay_all.py | replay_all uses backend archive order, calls replay_one per step; stops after WS disconnect; auto-recorded archive order; restores before_url |
| test_replay_one.py | resolves step by step_id; blocks URL mismatch; allows matching URL; fill operations; WS dispatch path |
| test_save_snapshot_ws.py | save_snapshot WS command returns snapshot envelope; error case returns safe failure |
| test_save_spec.py | build_spec_snapshot includes plan/recorded/code_update; falls back to child code lines |
| test_ws_reconnect_grace.py | transient WS disconnect preserves active run; rebinds ws to same agent |
| test_ws_router_gap_coverage.py **(NEW)** | run_steps routes to agent.run(); llm_run alias works; empty/missing steps; already-in-progress guard; reset calls llm.reset(); arm_picker missing/empty step_id returns error |

### Contract (typed envelopes, frontend/backend boundary, LLM/DOM advisory boundary)

| File | What it covers |
|---|---|
| test_command_contract.py | replay_all stop_on_error default; supported commands require context before forward; unsupported commands return runtime_rejected with command_id |
| test_event_contract.py | plan_ready emits step tree + child operation ids; step_recorded emits explicit ids + code_update; clarification_needed; plan_ready blocked during recovery; runtime_rejected shape; run_completed shape; session_state shape on reconnect |
| test_event_contracts.py | backend event envelope canonical metadata + legacy fields; frontend command envelope required fields; runtime rejection payload fields |
| test_event_sequence_contract.py | step_recorded blocked before plan confirmation; step_recorded followed by code_update in backend-owned order; failed step sets recovery before terminal resolution; stale confirmation does not execute until matching run context |
| test_frontend_accessibility_focus.py | shadow DOM root hooks stable; critical actions have accessible names; clarification/recovery cards expose focus targets; focus hooks backend-driven |
| test_frontend_event_command_contract.py | frontend event store is source-anchored; command surface routes through transport; pending command metadata modeled; command dispatcher emits typed envelopes |
| test_frontend_picker_candidate_ui.py | picker surface shadow-DOM ready; candidate metadata display-only; picker selection is proposal-only; picker does not call backend locator directly |
| test_frontend_plan_recovery_rendering.py | plan_ready drives plan review read model; plan review command paths are typed-and-pending-only; clarification_needed drives clarification read model; recovery_needed drives recovery read model |
| test_frontend_recorded_code_rendering.py | step_recorded drives recorded read model; code_update drives code read model without faking recorded truth; diagnostics are display-only; child structure preserved |
| test_frontend_shadow_dom_contract.py | frontend inventory matches legacy bootstrap path; shadow DOM host mount contract; planned root/core region hooks stable |
| test_frontend_trace_display.py | trace surface is backend-read-model driven; trace entry normalizer is display-only; backend messages feed trace without becoming lifecycle truth |
| test_lifecycle_checkpoint_contract.py | run_started is backend phase checkpoint not a typed event; execution_started mapped to executing phase after confirmation; lifecycle bridge sequence; session_state lifecycle mapping is backend-owned |
| test_llm_runtime_controller_contract.py | purpose registry accepts only known purposes; each purpose has required contract fields; runtime-impacting purposes require validator + single schema retry |
| test_process_boundary_contract.py | (also contract) normalize_frontend_command: missing type, incomplete envelope, unknown type, bad version, stale run_id — all typed rejections; current_state not mutated |
| test_recording_codegen_truth_contract.py | recording requires backend action evidence before truth; expected_outcome is parent-only metadata; child operation order matches confirmed execution; assert child preserves value alias and expected_value only in code_update |
| test_snapshot_archive_contract.py | archive preserves recorded steps verbatim; expected_outcome kept as step metadata; observed_outcome preserved; loading does not mark unresolved steps complete; corrupted input rejected safely |
| test_websocket_command_event_integration.py | malformed command returns runtime_rejected; unknown command rejected; stale run_id rejected; completed run correction rejected by backend consumer; valid canonical command preserves command correlation |
| test_dom_locator_contracts.py | (also contract) locator_validate invalid remains advisory; element candidate contract distinguishes target_text from expected_value |
| test_llm_planning_contracts.py | (also contract) LLM proposals are proposal-only output; backend validates before accepting |
| test_llm_specialist_contracts.py | (also contract) locator_specialist advisory-only boundary; recovery_diagnoser does not take browser action |

### Regression (prevents known bugs)

| File | What it covers |
|---|---|
| test_backend_isolation_contract.py | stale confirmation/completion/recovery do not bleed into new run session |
| test_completion_guard.py | guard stops before second model call (no infinite LLM loop) |
| test_late_event_contract.py | run_completed emitted only once; stale correction cannot mutate current run |
| test_multi_action_safety.py | confirmed execution contract blocks wrong assertion; strict cursor rejects step-1 click leak |
| test_process_boundary_contract.py | stale run_id payload does not mutate current_state (immutability regression) |
| test_event_sequence_contract.py | stale confirmation does not execute until matching run context |
| test_llm_specialist_contracts.py | budget guard rejects over-budget calls without model call |
| test_recovery_manager.py | locator_validate invalid does not trigger recovery (advisory-only regression) |

### E2E (browser/product-flow — inspect only, not modified)

| File | What it covers |
|---|---|
| tests/e2e/test_basic_click_flow.py | Full click flow via live Playwright |
| tests/e2e/test_correction_assert_then_click_flow.py | Correction then assert-click lifecycle |
| tests/e2e/test_exact_text_assertion_flow.py | has_text assertion E2E |
| tests/e2e/test_llm_required_ambiguous_action_flow.py | LLM-required path E2E |
| tests/e2e/test_mvp_001_lifecycle_smoke.py | MVP lifecycle smoke |
| tests/e2e/test_visible_assertion_flow.py | visible assertion E2E |
| test_e2e_harness.py | Harness helper contracts (no live browser — unit-level harness tests) |

---

## Gap Analysis

| Area | Status | Evidence |
|---|---|---|
| Backend event/command contract | Covered | test_event_contracts, test_event_contract, test_process_boundary_contract |
| WebSocket command routing/rejection | Covered + **gaps closed** | test_command_contract, test_websocket_command_event_integration, **test_ws_router_gap_coverage (NEW)** |
| session_state handshake on connect | Covered | test_event_contract::test_session_state_shape_is_explicit |
| session_state re-sent on reconnect | Partially covered | test_ws_reconnect_grace verifies agent rebind; session_state emission on reconnect is server.py logic tested indirectly via test_event_contract |
| run_completed / recovery_needed | Covered | test_late_event_contract, test_event_contract, test_backend_event_sequences |
| plan_ready and confirmation gate | Covered | test_event_contract, test_event_sequence_contract, test_backend_event_sequences |
| plan correction | Covered | test_plan_correction (37 tests) |
| Deterministic fast path | Covered | test_deterministic_fast_path (31 tests) |
| LLM-required ambiguous path | Covered | test_backend_event_sequences, test_llm_planning_contracts, test_llm_specialist_contracts |
| DOM/locator candidate/validation contract | Covered | test_dom_locator_contracts, test_dom_locator_advanced_contracts, test_agent_locator_handler_contract |
| Frontend/backend contract | Covered | test_frontend_event_command_contract, test_frontend_plan_recovery_rendering, test_frontend_recorded_code_rendering |
| Recording/code_update evidence | Covered | test_recording_codegen_truth_contract, test_code_update |
| Snapshot/archive/replay smoke | Covered | test_snapshot_archive_contract, test_replay_all, test_replay_one, test_save_snapshot_ws |
| run_steps → agent.run() routing | **Gap — closed** | test_ws_router_gap_coverage (NEW) |
| run_steps already-in-progress guard | **Gap — closed** | test_ws_router_gap_coverage (NEW) |
| llm_run alias routing | **Gap — closed** | test_ws_router_gap_coverage (NEW) |
| reset → llm.reset() + status response | **Gap — closed** | test_ws_router_gap_coverage (NEW) |
| arm_picker missing/empty step_id error | **Gap — closed** | test_ws_router_gap_coverage (NEW) |
| arm_picker with valid step_id | Blocked/future | Requires live browser / arm_picker implementation to return data |
| E2E: LLM-required full lifecycle | Future | test_e2e/* — requires live browser + backend server |

---

## Tests Added

**File:** `tests/test_ws_router_gap_coverage.py` (new file, 9 tests)

| Test | Category | What it proves |
|---|---|---|
| test_run_steps_routes_to_agent_run_with_forwarded_steps | Integration | run_steps calls agent.run() with the exact steps |
| test_llm_run_routes_to_agent_run_with_forwarded_steps | Integration | llm_run alias also calls agent.run() |
| test_run_steps_with_empty_steps_list_still_calls_agent_run | Integration | empty steps list → agent.run([]) not crash |
| test_run_steps_with_missing_steps_key_defaults_to_empty_list | Integration | missing steps key → agent.run([]) not crash |
| test_run_steps_while_run_already_active_returns_status_and_does_not_start_second_run | Regression | already-in-progress guard: status message, run() called only once |
| test_reset_calls_llm_reset_and_returns_status_message | Contract | reset calls llm.reset() and returns "status" typed message |
| test_reset_does_not_start_a_run | Regression | reset must not call agent.run() |
| test_arm_picker_missing_step_id_returns_error_without_queue_mutation | Contract | arm_picker without step_id returns typed error, no queue mutation |
| test_arm_picker_empty_step_id_returns_error | Contract | arm_picker with empty step_id treated same as missing |

---

## Tests Verified as Existing (not duplicated)

- session_state shape on connect: `test_event_contract.py::test_session_state_shape_is_explicit`
- save_snapshot WS path: `test_save_snapshot_ws.py` (2 tests)
- replay_one WS path: `test_replay_one.py` (WS dispatch path tested at lines 679–770)
- confirmed/correction/option_selected routing: `test_websocket_command_event_integration.py`
- stale command rejection: `test_process_boundary_contract.py`, `test_websocket_command_event_integration.py`
- plan_ready blocked during recovery: `test_event_contract.py::test_plan_ready_blocked_during_recovery_returns_a_user_friendly_rejection`
- deterministic fast path skips LLM: `test_deterministic_fast_path.py::test_plan_has_zero_llm_calls`

---

## Blocked / Future Tests

| Gap | Reason blocked |
|---|---|
| arm_picker with valid step_id → returns picker_ready event | Requires live browser and arm_picker to return real data |
| session_state re-sent on second WS connect with active run | server.py line 231–233 runs only when `_build_session_state_payload` returns non-None; full path needs a running agent with state |
| E2E: ambiguous path + correction + re-plan | Requires live LLM + Playwright browser |
| E2E: replay_all with failure recovery | Requires live browser |

---

## Commands Run and Results

```
# Baseline
python -m pytest tests/ --ignore=tests/e2e -q
→ 522 passed

# New file
python -m pytest tests/test_ws_router_gap_coverage.py -v
→ 9 passed

# Specified verification suite
python -m pytest \
  tests/test_event_contract.py tests/test_event_contracts.py \
  tests/test_command_contract.py tests/test_event_sequence_contract.py \
  tests/test_backend_event_sequences.py tests/test_websocket_command_event_integration.py \
  tests/test_lifecycle_checkpoint_contract.py tests/test_recording_codegen_truth_contract.py \
  tests/test_deterministic_fast_path.py tests/test_snapshot_archive_contract.py \
  tests/test_ws_router_gap_coverage.py -q
→ 102 passed

# Full suite after adding tests
python -m pytest tests/ --ignore=tests/e2e -q
→ 531 passed
```

---

## Remaining Risks

1. `arm_picker` with a valid `step_id` is not tested at the WS level — the route calls `arm_picker()` from `browser.py` which requires a live browser page.
2. The `session_state` re-emission path on WS reconnect (server.py:231–233) is covered only partially by the reconnect grace test — the full flow requires an agent with an active `_build_session_state_payload`.
3. No test covers the `replay_all` WS route's disconnect-during-replay error path in isolation (it is covered inside `test_replay_all.py` at the AgentLoop level, but not through the WS router).

---

## Next Recommended Task

**TEST-COVERAGE-002: WS reconnect session_state emission integration test**
Write a single integration test that starts a run, disconnects, reconnects, and asserts that `session_state` is sent as the first non-status message on reconnect — covering server.py lines 231–233. This requires a fake AgentLoop that implements `_build_session_state_payload()` and stays alive across the reconnect.
