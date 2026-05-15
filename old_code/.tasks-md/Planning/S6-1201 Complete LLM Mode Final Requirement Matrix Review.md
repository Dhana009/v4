# S6-1201: Complete LLM Mode Final Requirement Matrix Review

## Objective

Review Cluster 0 requirement matrix and mark every Complete LLM Mode feature with final status and evidence.

## Acceptance Criteria

- [ ] Cluster 0 requirement matrix reviewed
- [ ] Every requirement has: Done, Partial, Blocked, or Out of Scope
- [ ] Every Done status backed by implementation and test evidence
- [ ] Every Partial status has explicit reason and scope
- [ ] Every Blocked status has evidence and owner
- [ ] No undocumented deferrals
- [ ] Final matrix document created
- [ ] Matrix includes artifact/link references

## Status Values

- **Done**: Fully implemented, tested (unit/contract/E2E)
- **Partial**: Implemented with explicit limitations
- **Blocked**: Work exists but cannot proceed without external blocker
- **Out of Scope**: Explicitly out of Complete LLM Mode v1

## Constraints

- No fake Done
- No moving requirements to Out of Scope without approval
- No Partial without documenting limitation
- No Blocked without identifying blocker

## Notes

This story is the final audit before closure. The matrix answers: "Is Complete LLM Mode actually complete?"


---

## Audit note (2026-05-13)

Evidence missing; not moved to Done. Final requirement matrix file will be created as part of SPRINT-006-HANDOFF.md closure. Frontend requirements must be marked Partial (no actual frontend source). Paid E2E not run — mark final acceptance as Pending paid E2E.

---

## Final Requirement Matrix (Sprint 6 — 2026-05-13)

| Requirement | Source doc | Implementation evidence | Test evidence | Status | Notes |
|-------------|-----------|------------------------|---------------|--------|-------|
| LLM Purpose Registry (14 purposes) | Sprint 6 Cluster 1 spec | runtime/llm_policy_registry.py, runtime/llm_purpose_policy.py | tests/test_llm_purpose_policy_registry.py | Done | 14 purposes typed and validated |
| Purpose-dispatched LLM controller | Runtime Policy Spec | runtime/llm_runtime_controller.py | tests/test_llm_controller_callsite_guard.py, tests/test_llm_runtime_controller_contract.py | Done | All calls via controller |
| Context level policy (L0–L5) | S6-0201 | runtime/context_levels.py, runtime/context_policy.py | tests/test_context_policy.py | Done | Commit 7491f35 |
| Context sufficiency gates | S6-0202 | runtime/context_gates.py | tests/test_context_gates.py | Done | Commit 7491f35 |
| Context escalation approval | S6-0203 | runtime/context_request_policy.py | tests/test_context_request_policy.py | Done | Commit 7491f35 |
| Memory selection policy | S6-0204 | runtime/memory_selection_policy.py | tests/test_memory_selection_policy.py | Done | Commit 7491f35 |
| Tool exposure enforcement | S6-0205 | runtime/tool_exposure_enforcement.py | tests/test_tool_exposure_enforcement.py | Done | Commit 7491f35 |
| Schema validation + retry-fail-closed | S6-0206 | runtime/schema_validation_policy.py | tests/test_schema_validation_policy.py | Done | Commit 7491f35 |
| Token budget enforcement + telemetry | S6-0207 | runtime/token_budget_policy.py | tests/test_token_budget_policy.py | Done | Commit 7491f35 |
| Page Intelligence live invocation | S6-0301 | runtime/page_intelligence_live.py | tests/test_page_intelligence_live.py | Done | Commit dcaec73 |
| Page extraction determinism | S6-0302 | runtime/page_extraction.py | tests/test_page_extraction.py | Done | Commit dcaec73 |
| Cheap-model page intelligence summarizer | S6-0303 | runtime/page_intelligence.py | tests/test_page_intelligence_summarizer_policy.py | Done | Commit dcaec73 |
| Page validation recommender schema | S6-0304 | runtime/page_validation_recommender.py, runtime/page_intelligence_schema.py | tests/test_page_validation_recommender.py | Done | |
| Recommendation review state + events | S6-0305 | runtime/recommendation_state.py, runtime/recommendation_events.py | tests/test_recommendation_events.py | Done | |
| Accepted recommendations → plan | S6-0306 | runtime/recommendation_to_plan.py | tests/test_recommendation_to_plan.py | Done | |
| Journey classifier + pipeline | S6-0401 | runtime/journey_classifier.py | tests/test_journey_classifier.py | Done | Commit 712bc77 |
| Journey planner policy + draft plan schema | S6-0402 | runtime/journey_plan.py | tests/test_journey_plan_schema.py | Done | |
| Steps Mode backend intake | S6-0403 | runtime/steps_mode.py | tests/test_steps_mode.py | Done | 100% coverage |
| Multi-step queue planning | S6-0404 | runtime/multi_step_queue.py | tests/test_multi_action_safety.py | Done | |
| Section action planner | S6-0405 | runtime/section_action_planner.py | tests/test_assertion_flow.py | Done | |
| Page state model | S6-0406 | runtime/page_state_model.py | tests/test_plan_model.py | Done | |
| Plan revision discussion state | S6-0501 | runtime/plan_revision.py | tests/test_plan_revision.py | Done | Commit 2e523c8 |
| Explicit apply/update mutation boundary | S6-0502 | runtime/plan_revision.py | tests/test_plan_revision.py | Done | |
| Plan diff proposal + validator | S6-0503 | runtime/correction_context.py | tests/test_correction_context.py | Done | |
| Locator candidate pipeline | S6-0601 | runtime/dom_locator.py, runtime/locator_intelligence.py | tests/test_dom_locator_contracts.py | Done | Commit d681830 |
| Locator ambiguity + chaining | S6-0602 | runtime/dom_locator_contract.py | tests/test_dom_locator_advanced_contracts.py | Done | |
| Per-operation locator context persistence | S6-0606 | runtime/locator_contract.py | tests/test_locator_intelligence.py | Done | |
| Locator update flow | S6-0607 | runtime/locator_update.py | tests/test_agent_locator_handler_contract.py | Done | |
| Permission/autonomy mode contract | S6-0701 | runtime/permission_policy.py | tests/test_permission_capability.py | Done | Commit 695755f |
| Risk classification framework | S6-0702 | runtime/permission_policy.py | tests/test_permission_capability.py | Done | |
| Capability registry | S6-0703 | runtime/capability_registry.py | tests/test_capability_gaps.py | Done | |
| Test data requirement classification | S6-0705 | runtime/test_data_policy.py | tests/test_permission_capability.py | Done | |
| Human-in-loop flow | S6-0710 | runtime/human_in_loop.py | tests/test_human_in_loop.py | Done | 100% coverage |
| Failure classification pipeline | S6-0801 | runtime/failure_classifier.py, runtime/failure_context.py | tests/test_failure_context.py | Done | Commit 695755f |
| Recovery state lifecycle | S6-0805 | runtime/recovery_manager.py | tests/test_recovery_manager.py | Done | |
| Session save/load | S6-0901 | runtime/session_store.py | tests/test_save_snapshot_ws.py | Done | Commit 546d288 |
| Replay engine | S6-0904 | runtime/replay_engine.py | tests/test_replay_one.py, tests/test_replay_all.py | Done | |
| Replay repair + versioning | S6-0908 | runtime/snapshot_archive.py, runtime/spec_snapshot.py | tests/test_replay_versioning.py | Done | |
| Frontend Shadow DOM host boundary | S6-1001 | Contract tests only in tests/test_frontend_shadow_dom_contract.py | tests/test_frontend_shadow_dom_contract.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Frontend LLM tab UI | S6-1003 | Contract tests only | tests/test_frontend_llm_mode_complete.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Frontend Steps tab UI | S6-1004 | Contract tests only | tests/test_frontend_llm_mode_complete.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Frontend Recommendation UI | S6-1005 | Contract tests only | tests/test_frontend_llm_mode_complete.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Frontend Recorded/Code/Trace tabs | S6-1006/7/8 | Contract tests only | tests/test_frontend_recorded_code_rendering.py, tests/test_frontend_trace_display.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Frontend typed event store | S6-1009 | Contract tests only | tests/test_frontend_event_command_contract.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Frontend command dispatcher | S6-1010 | Contract tests only | tests/test_frontend_event_command_contract.py | **Partial** | No actual frontend/ source. See BUG-S6-FINAL-002 |
| Trace event model | S6-1101 | runtime/trace_events.py | tests/test_trace_events.py | Done | Commit aca0949 |
| LLM call artifact completeness | S6-1103 | runtime/artifact_bundle.py | tests/test_artifact_bundle.py | Done | |
| Redaction policy | S6-1105 | runtime/redaction_policy.py | tests/test_redaction_policy.py | Done | |
| Trace export + frontend data contract | S6-1107 | runtime/trace_export.py | tests/test_trace_export.py | Done | |
| Cheap regression suite | S6-1202 | Full suite run | 1689 passed, 12 pre-existing failures (BUG-S6-FINAL-001) | **Partial** | 12 model-class mismatch failures tracked |
| Local fixture E2E | S6-1203 | tests/e2e/ | 6 passed | **Partial** | Full scenario suite not defined |
| Real LLM contract probes | S6-1204 | Not run | — | **Pending paid E2E** | Per S6-0007 policy |
| Paid browser E2E acceptance | S6-1205 | Not run | — | **Pending paid E2E** | Per S6-0007 policy |
| Architecture drift audit | S6-1207 | All invariants verified | test_runtime_no_llm_call_guard.py (69), test_llm_controller_callsite_guard.py | Done | All 8 invariants hold |
| Final Complete LLM Mode acceptance | Cluster 12 gate | — | — | **Pending paid E2E** | Cannot claim fully accepted without paid E2E gate |
