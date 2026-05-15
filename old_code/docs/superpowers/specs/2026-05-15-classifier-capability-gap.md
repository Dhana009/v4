# Classifier + Capability-Gap-Logging — Gap Audit

Date: 2026-05-15
Mode: read-only audit, no edits
Source rule: P0 Scenarios Spec §5 + Runtime Policy Spec §3/§12/§15/§18 + PRD 06 Phase 2 test 8

---

## 1. Five classifiers per spec (P0 Scenarios §5)

Exact enum values quoted from `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md`:

1. **User intent** (§5.1, L443–460): `single_action, single_assertion, section_validation, page_validation_recommendation, full_journey_automation, queued_multi_step_flow, plan_revision_discussion, plan_correction_apply, clarification_answer, recovery_instruction, locator_update_request, capability_request, unsupported_or_out_of_scope, stop_or_cancel`.
2. **Plan edit** (§5.2, L462–476): `discuss_only, add_operation, remove_operation, reorder_operations, replace_target, change_expected_outcome, split_step, merge_steps, skip_step, apply_revision, reject_revision`.
3. **Locator issue** (§5.3, L478–490): `locator_not_found, locator_matches_multiple, locator_matches_wrong_element, locator_unstable, locator_hidden, locator_detached, locator_scope_missing, locator_text_mismatch, locator_requires_frame_or_shadow`.
4. **Execution failure** (§5.4, L492–506): `precondition_failed, permission_required, assertion_timeout, action_timeout, navigation_timeout, element_not_interactable, page_state_mismatch, unsupported_capability, llm_schema_invalid, tool_contract_mismatch, unknown_runtime_error`.
5. **Capability / risk** (§5.5, L508–517): `safe_read_or_assert, medium_browser_action, high_risk_submit_upload_download, destructive_or_external_side_effect, unsupported_capability, requires_human_input`.

Rule (§5.6, L519–532): every input → classify → choose pipeline → minimal context → deterministic first → LLM only if needed → backend validate → typed event.

---

## 2. Code today — per-classifier status

| # | Classifier | Implemented? | Location | Schema/retry vs runtime_policy §15 |
|---|------------|--------------|----------|-------------------------------------|
| 1 | User intent | Partial — keyword heuristic, wrong enum set | `runtime/journey_classifier.py:18-23` defines `IntentType{FULL_JOURNEY_AUTOMATION, SINGLE_ACTION, RECOMMENDATION_REQUEST, STEPS_MODE, UNKNOWN}` — only 4 of 14 spec values; `classify_journey_intent` at L66 is deterministic, no LLM, no schema. **Not wired**: zero callers outside `tests/test_journey_classifier.py`. Purpose `intent_classifier` is declared in `runtime/llm_purpose_policy.py:24`, `runtime/llm_runtime_controller.py:249`, but no `controller.call(purpose="intent_classifier", ...)` exists in `agent.py` (verified: `grep purpose= agent.py` returns only `plan_diff_editor` @3871, `step_plan_normalizer` @3916, `recovery_diagnoser` @3963). |
| 2 | Plan edit | Missing as classifier | `plan_diff_editor` purpose exists (`runtime/llm_policy_registry.py:242-247`, called `agent.py:3871`) but emits a free-form plan_diff, not one of the 11 enum tags. No enum file defines `discuss_only / add_operation / …`. |
| 3 | Locator issue | Missing as enum classifier | `runtime/locator_intelligence.py`, `runtime/dom_locator_contract.py` score strength (`strong/medium/weak`) but no `LocatorIssueType` matching §5.3. `locator_specialist` purpose runs (`agent.py` controller path) without emitting one of the 9 enum tags. |
| 4 | Execution failure | Partial, narrow enum | `runtime/failure_classifier.py:16-23` defines `FailureType{ELEMENT_NOT_FOUND, TIMEOUT, NETWORK_ERROR, ASSERTION_FAILURE, NAVIGATION_ERROR, PERMISSION_DENIED, UNKNOWN}` — 7 buckets vs spec's 11. Missing: `precondition_failed, action_timeout, navigation_timeout` (only generic `timeout`), `element_not_interactable, page_state_mismatch, unsupported_capability, llm_schema_invalid, tool_contract_mismatch`. Deterministic substring matcher at L34–47; wired via `runtime/recovery_manager.py:35,105` and called from `agent.py:2288`. No schema/retry — not an LLM call. |
| 5 | Capability/risk | Missing as classifier | `runtime/capability_registry.py:15-17` only has `CapabilityStatus{SUPPORTED, CAPABILITY_GAP, WARNING}` — gap-marker, not risk classifier. None of §5.5 six values (`safe_read_or_assert / medium_browser_action / high_risk_submit_upload_download / destructive_or_external_side_effect / unsupported_capability / requires_human_input`) appear in `*.py` (`grep -r "high_risk_submit_upload_download"` empty). `journey_classifier.py:55-58` exposes a `has_capability_risks` boolean keyword check (`crm/salesforce/api/...`) which conflates risk with capability availability. |

Schema-retry compliance (§15 "retry once with schema reminder, then fail closed"): `runtime/llm_runtime_controller.py:171-175,234` sets `schema_retry_limit=1` and `fallback="fail_closed"` — compliant **when** the controller path is used. The `else: response = await self.model_router.call(...)` branch at `agent.py:1801-1808` bypasses the controller's schema-retry loop for `main_orchestrator` and recording-wait flows.

---

## 3. LLM Runtime Controller routing (runtime_policy §3)

Spec §3 (L55–93): every LLM decision flows through the controller — classify → select policy → deterministic check → build context → load skills → expose tools → call model → validate schema → backend-validate → emit event.

Code today:

- Single controller exists: `LLMRuntimeController` (`runtime/llm_runtime_controller.py:496`), instantiated at `agent.py:165`.
- Routing decision is made by `LLMPolicyGateway.decide(...)` (`runtime/llm_policy_gateway.py:28`), called at `agent.py:1622`. It is **phase-based, not enum/classifier-based** — see L66 `if normalized_phase in {"planning","awaiting_confirmation"}: → step_plan_normalizer`, L69 `if normalized_phase in {"executing","recording"}: → execution_driver`, L72 `if normalized_phase in {"recovery","recovering"}: → recovery_diagnoser`. The 14 spec purposes including `intent_classifier`, `clarification_generator`, `journey_planner`, `page_intelligence_summarizer`, `page_validation_recommender`, `custom_assertion_planner`, `user_response_writer`, `trace_summarizer` are declared (`runtime/llm_purpose_policy.py:23-38`) but never selected by the gateway.
- Ad-hoc / bypass call sites:
  - `agent.py:1801-1808` `response = await self.model_router.call(...)` invoked when controller path is not entered — uses `self.llm.client` and bypasses controller's `_validate_response` (L1480) and retry loop (L1382 `max_attempts = schema_retry_limit + 1`).
  - Direct `controller.call(purpose=...)` sites are limited to `agent.py:3871` (plan_diff_editor), `:3916` (step_plan_normalizer), `:3963` (recovery_diagnoser). No call for `intent_classifier`, `clarification_generator`, `journey_planner`, `locator_specialist`, `page_intelligence_summarizer`, `page_validation_recommender`, `custom_assertion_planner`, `execution_driver`, `replay_repair_specialist`, `user_response_writer`, `trace_summarizer`.

---

## 4. Capability gap log (P0 §13, PRD 06 phase 2)

Spec §13 (L1209–1219): gap entry must include `timestamp, url, user_intent, failed_step_id / operation_id, needed_capability, available_tools, suggested_future_work`. No secrets. Events emitted: `capability_checked, capability_gap_recorded, partial_plan_ready` (L1196–1198). PRD 06 L54: "Missing capabilities are recorded under workspace gap log".

Code today:

- Recorded in-memory list `self.capability_gaps` on the agent (`agent.py:226,300`); duplicated on recorder (`recording/recorder.py:76`).
- Producer `_record_capability_gap` (`agent.py:558-611`) writes record fields `{ordinal, timestamp, category, source, severity, message, phase, step_id, details}`. **Gap vs §13**:
  - Missing fields: `url`, `user_intent`, `operation_id`, `needed_capability` (uses generic `category`), `available_tools`, `suggested_future_work`.
  - Extra fields not in spec: `ordinal`, `source`, `severity`.
  - Field mismatch: spec says `failed_step_id / operation_id`; code only sets `step_id` from `self.active_step_id` (L578).
- Persistence: only inside the per-run spec snapshot via `build_spec_snapshot(..., capability_gaps=...)` (`agent.py:1261`, `runtime/spec_snapshot.py:78,94,112`). **No workspace gap log file** — `grep -r "gap_log\|gap_logger\|capability_gaps.json"` returns zero matches. Spec §25 (L2500) calls for `runtime/gap_logger.py` — does not exist.
- Event emission: only a single `print("[CAPABILITY_GAP] ...")` line (`agent.py:603`). The three typed events `capability_checked`, `capability_gap_recorded`, `partial_plan_ready` are **never emitted** (verified: `grep -rn "capability_gap_recorded\|capability_checked\|partial_plan_ready" --include='*.py'` returns zero non-test hits).
- Sanitiser at `agent.py:507-556` strips `dom/html/markup/prompt/tool_args/...` → secrets-redaction is in place (good).

Existing call sites: `agent.py:2641` (missing_skill), `:7878` (unknown_planned_operation), `:8930` (unknown_tool), `:9046`, plus `llm/tool_dispatcher.py:173` (via `self._loop._record_capability_gap`). None correspond to the Scenario-8 download/file-content-verification trigger.

---

## 5. Tool exposure matrix enforcement (runtime_policy §12.2)

Spec §12.2 (L590–606) defines per-purpose allowlist (e.g., `intent_classifier → no tools`, `page_intelligence_summarizer → inspection tools only`, `locator_specialist → locator + element/section context only`, etc.).

Code today:

- `runtime/tool_exposure_enforcement.py:66 PURPOSE_TOOL_EXPOSURE` exists; populated from `PURPOSE_PLANNING_TOOL_NAMES` (`runtime/tool_schema_policy.py`) plus explicit overrides at L72–75.
- `runtime/tool_schema_policy.py:15 "intent_classifier": ()` correctly enforces no tools — matches §12.2.
- Enforcement helper `get_allowed_tools(purpose_id)` at L82–90; consistency checker `validate_tool_exposure_consistency` at L111–116. Wired in `agent.py:1655 purpose_allowed_tool_names = set(policy_decision.allowed_tools)` and applied via `_filter_tools_for_phase` (`runtime/llm_runtime_controller.py:883`).
- **Gap**: `tool_call_blocked` event (§12.3 L625) not emitted on violation — `grep -rn "tool_call_blocked"` returns zero hits. Pre-call filtering exists; backend post-call rejection event missing.

---

## 6. Gap matrix

| Item | Status | Exact gap | Fix sketch |
|------|--------|-----------|------------|
| Intent classifier (§5.1) | Partial | 4-of-14 enum, deterministic-only, not routed by gateway, no `controller.call(purpose="intent_classifier")` site | Replace `IntentType` enum with full 14-value set; add LLM call wrapped by controller for ambiguous inputs; gateway dispatches to it before any phase-purpose decision |
| Plan-edit classifier (§5.2) | Missing | No 11-value enum, plan_diff_editor emits free-form diff | Add `PlanEditType` enum; require plan_diff_editor schema field `edit_type` matching enum; backend validate per §16 |
| Locator-issue classifier (§5.3) | Missing | No 9-value enum; locator_specialist returns alternatives but no issue tag | Add `LocatorIssueType` enum; locator_intelligence.py emits tag on validation failure |
| Failure classifier (§5.4) | Partial | 7-of-11 enum; missing `precondition_failed, action_timeout, navigation_timeout, element_not_interactable, page_state_mismatch, unsupported_capability, llm_schema_invalid, tool_contract_mismatch` | Extend `FailureType`; split current `TIMEOUT` into action/navigation/assertion; add precondition gate emission |
| Capability/risk classifier (§5.5) | Missing | `CapabilityStatus` is presence flag, not risk class; `has_capability_risks` is bool | Add `CapabilityRiskLevel` enum; classify each operation pre-plan; feed permission_policy |
| Controller-only routing (§3) | Partial | `model_router.call` bypass at `agent.py:1801`; gateway phase-based not classifier-based | Funnel bypass branch through controller; gateway routes on classifier output before falling back to phase |
| Capability gap-log file (PRD 06 §Phase2) | Missing | `runtime/gap_logger.py` absent; gaps live only in spec snapshot | Add `runtime/gap_logger.py` writing to `${workspace}/gap_log.jsonl` with §13 schema |
| Gap entry schema (§13) | Mismatch | Missing `url, user_intent, operation_id, needed_capability, available_tools, suggested_future_work` | Extend `_record_capability_gap` signature; pull `url` from page_state, `available_tools` from tool registry |
| Gap events (§13) | Missing | `capability_checked / capability_gap_recorded / partial_plan_ready` not emitted | Wire emissions in `_record_capability_gap` and plan finalizer |
| Tool-call-blocked event (§12.3) | Missing | No `tool_call_blocked` emission | Emit on filter rejection in `_filter_tools_for_phase` |

---

## 7. Acceptance hook — PRD 06 Phase 2 test 8

"Missing capability → gap logged under workspace" (`06_BUILD_ROADMAP_AND_ACCEPTANCE.md:175`).

Blockers today:

1. No workspace-scoped gap log file — `capability_gaps` exists only inside per-run spec snapshot (`runtime/spec_snapshot.py:78`); test cannot read a workspace path.
2. No `capability_gap_recorded` event — frontend/test harness cannot observe.
3. Capability classifier `unsupported_capability` (§5.5) absent — Scenario-8 download/PDF-verify trigger has no detector. Existing recorders fire only on `missing_skill`, `unknown_planned_operation`, `unknown_tool` (`agent.py:2641,7878,8930`).
4. Gap record missing `needed_capability` and `suggested_future_work` — even if logged, schema fails §13.

---

## 8. Conflict notes — files an implementer will touch

Hot files (likely contention with DG1/DG2 lanes — no `DG1/DG2` markers found in repo so this is best-guess by feature area):

- `agent.py` — instantiation `:165`, gap recorder `:558-611`, snapshot `:1238-1264`, classifier import `:40`, gateway `:1622`, controller call sites `:3871/3916/3963`, gap call sites `:2641/7878/8930/9046`. Single file ~9000 LOC, near-certain merge conflicts with any other lane editing planning/recovery/recording paths.
- `runtime/journey_classifier.py` — entire file rewrite (enum expansion).
- `runtime/failure_classifier.py` + `runtime/recovery_manager.py:35,105` — enum expansion changes consumers in `runtime/recovery_pipeline.py:17,41` and `agent.py:2288`.
- `runtime/capability_registry.py` — split into capability-presence vs risk-level.
- `runtime/llm_policy_gateway.py` — rewrite `decide()` to consume intent classification.
- `runtime/llm_runtime_controller.py:249` (intent_classifier purpose) — needs real call site, currently unreachable.
- `runtime/spec_snapshot.py:78,94,112,163-192` — schema additions for new gap fields; persisted snapshots load path at L163–192 must stay backward-compatible.
- New file: `runtime/gap_logger.py` (spec §25 L2500).
- `plan/correction.py:84-178` and `recording/recorder.py:76,295-318` duplicate the gap-record code — refactor target.
- `llm/tool_dispatcher.py:173` calls `_loop._record_capability_gap` — coupling that any DG lane touching tool dispatch will hit.

Likely DG-lane overlap risks:

- A lane editing recovery (DG-recovery?) will collide with failure_classifier enum expansion and `recovery_manager.classify_failure` signature changes.
- A lane editing planning (DG-planning?) will collide with `llm_policy_gateway.decide()` rewrite and `step_plan_normalizer` / `plan_diff_editor` schema additions.
- A lane editing locator (DG-locator?) will collide with `runtime/locator_intelligence.py` issue-tag emission.
- Any lane touching `agent.py` snapshot or telemetry path (`:1238-1264`, `:1735-1747`) will collide with gap-log field additions.
