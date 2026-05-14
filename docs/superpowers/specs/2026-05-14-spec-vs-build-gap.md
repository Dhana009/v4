# Spec vs Build — Gap Analysis (Full Diff)

**Date:** 2026-05-14
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**HEAD:** `13fbd65`
**Method:** systematic-debugging Phase 1 / 4 parallel Explore agents
**Scope:** every requirement in PRD_v2_3 + complete-llm frontend / scenarios / runtime-policy specs + yui (1) design ref + 1AutoWorkbench print PDF, diffed against current code.

References (already in repo, NOT rewritten here):
- `PRD_v2_3_Modular_Pack_v2/` — backend modular pack
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md`
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md`
- `autoworkbench_complete_llm_mode_runtime_policy_spec.md`
- `yui (1)/v4/` — design reference (jsx mockups)
- `1AutoWorkbench — print.pdf` — visual reference
- Companion: `.tasks-md/Audit/FRONTEND_ACTIONS_AUDIT.md` (Phase 1 actions audit)

Legend: ✅ built · ⚠️ partial · ❌ missing · 🚫 disabled-with-reason

---

## 1. LLM-Mode Capabilities (P0 scenarios)

| P0 Scenario / Capability | Spec requires | Status | Evidence | Gap |
|---|---|---|---|---|
| **Scenario 1: Full journey automation** | Plan mode: clarify scope, multi-step plan, test-data handling, permission pre-check | ⚠️ | `runtime/llm_policy_registry.py:journey_planner`, `plan/builder.py`, `runtime/permission_policy.py` | Test-data collection loop + sensitive-value redaction during planning incomplete |
| **Scenario 2: Page-validation recommendations** | LLM recommends assertions grouped by section, non-blocking | ⚠️ | `runtime/page_validation_recommender.py` + `build_recommendation_ready_event` | Recommendation review state not exposed in backend events |
| **Scenario 3: Locator ambiguity** | Deterministic-first; scoped/chained before LLM | ⚠️ | `runtime/dom_locator_contract.py`, `runtime/locator_intelligence.py` | Scoped/ancestor chain resolution incomplete; LLM locator specialist not fully integrated |
| **Scenario 4: Plan revision (ChatGPT-style)** | Discussion vs mutation separated; plan_diff validated before apply | ✅ | `plan/correction.py:plan_diff_editor`, `event_contracts.build_plan_diff_*_event` | Brainstorm vs mutation intent classification weak in clarification path |
| **Scenario 5: Precondition handling** | Check page state, deterministic resolve or ask | ⚠️ | `runtime/page_state_model.check_page_precondition`, `runtime/locator_update.check_locator_update_precondition`, `trace_events.PRECONDITION_CHECK` | `precondition_failed` event + resolution-option payload not in event_contracts |
| **Scenario 6: Failure recovery / repair** | Classify → deterministic → LLM repair → bounded retries | ⚠️ | `runtime/recovery_context.py`, `recovery_pipeline.py`, `build_recovery_needed_structured_event`, `replay_repair_specialist` policy | Retry-limit policy not exposed; `repair_diff` event builder missing |
| **Scenario 7: Permission / autonomy modes** | Risk classes (safe/medium/high/destructive); ask before risky | ⚠️ | `runtime/permission_policy.check_permission` + RiskLevel enum, `human_in_loop.py`, `build_permission_required_payload` | Autonomy mode (strict/balanced/auto) not in state contract; decision storage incomplete |
| **Scenario 8: Capability-gap logging** | Log unsupported, no fake success | ⚠️ | `build_capability_gap_event`, `runtime/capability_registry.py`, gap-logging in recommendations | Event payload minimal; not linked to execution phase |
| **Planning + Clarification** | Intent classify → clarify → page analysis → draft → review | ⚠️ | `intent_classifier`, `journey_classifier.JourneyClassification`, `clarification_generator`, `page_analysis_started/ready` events | `clarification_needed` event builder thin; classification-result event missing |
| **Plan Confirmation** | `plan_review` state; confirm/correct | ⚠️ | `plan/confirmation.wait_for_plan_confirmation`, `session_state` includes plan, `confirmed` cmd | Distinct `plan_review` event missing; `plan_ready` payload incomplete |
| **Plan Diff lifecycle** | proposed → validated → applied → new_plan_ready | ✅ | `plan/correction.py`, `event_contracts` builders | `plan_diff.v1` schema incomplete; mutation enums not enforced |
| **Locator Update Flow** | Per-step improve; deterministic candidates first; validate LLM | ⚠️ | `runtime/locator_update.process_locator_update` | `locator_candidates_ready` exists but `locator_update_request/applied` missing; `improvement_available` flag absent |
| **Execution Start** | `execution_started`; precondition; `operation_executed`/`operation_failed` | ⚠️ | `_confirmed_execution_*` in `agent.py`, `build_run_completed_payload` | `execution_started` + `operation_executed`/`operation_failed` events missing; operation_id lifecycle incomplete |
| **Offline Mode** | Detect offline; queue ops; sync on reconnect | ❌ | none | No state machine, queue, or sync protocol |
| **agent_settings event** | Stream agents enabled/disabled/model | ❌ | none | Not implemented (D-106 blocker) |
| **Raw LLM Response Retention** | Preserve raw for debugging | ⚠️ | `llm_runtime_controller.call_with_raw_response` sets `result["raw_response"]` | Not exposed in events; no archive/cleanup lifecycle |
| **Schema Error Handling** | Invalid schema → retry once → clarify/fail-safe | ⚠️ | `build_schema_error_event`, `_validate_response` retry-once | Retry policy not enforced at controller boundary in all purposes; fallback routing partial |
| **Execution Redaction** | Mask creds in logs/traces; visibility control | ⚠️ | `context_levels.py L5` mentions secrets redaction; `redaction_policy.py` shell | Policy logic empty; LLM-input redaction not systematic; test-data visibility rules in codegen not enforced |
| **Completion** | `run_completed` with summary/counts/code_status | ✅ | `build_run_completed_payload` | Completion state transition not clear in `session_state`; code_update link to completion missing |

---

## 2. Backend (events / commands / endpoints / persistence)

### 2.1 Events

| Event | Spec | Status | Evidence / Gap |
|---|---|---|---|
| `ready` | session_id, workspace, mode, url | ✅ | `build_browser_ready_event` |
| `run_started` | run_id, steps[] | ✅ | `agent.py` emits |
| `plan_ready` | plan_id, steps[], summary | ✅ | `server.py:318+` |
| `clarification_needed` | question, options, step_id | ⚠️ | builder exists; rarely triggered |
| `recovery_needed` | error_summary, tried[], options | ✅ | `_emit_recovery_needed_event` |
| `step_validating` | step_id, op_id, action | ⚠️ | only `step_executing` mostly |
| `step_executing` | step_id, op_id, action | ✅ | wired |
| `step_recorded` | step + parent/children | ✅ | `llm/tool_dispatcher.py` |
| `step_failed` | step_id, error, status | ⚠️ | mostly implicit in recovery |
| `step_skipped` | step_id, reason | ⚠️ | cmd exists, event weak |
| `code_update` | step_id, lines[], diagnostics[] | ⚠️ | `_append_code_update_payload`; diagnostics unclear |
| `replay_result` | step_id, op_id, passed, error | ✅ | replay_one/all payloads |
| `run_completed` | summary, counts | ✅ | `build_run_completed_payload` |
| `session_state` | full snapshot for reconnect | ✅ | `_build_session_state_event` |
| `agent_settings` | agents[], enabled/disabled, model | ❌ | zero refs (D-106) |
| `agent_started/progress/result/failed/trace` | multi-agent activity | ❌ | placeholder schema only |
| `no_browser` / `api_key_required` / `otp_required` / `e2e_pending` | state-card triggers | ❌ | only `permission_required` exists |
| `precondition_failed` | step + resolution options | ❌ | not in event_contracts |
| `execution_started` / `operation_executed` / `operation_failed` | execution lifecycle | ❌ | not defined |
| `locator_update_request` / `locator_update_applied` | locator improvement flow | ❌ | not defined |
| `plan_review` (distinct from session_state) | review-state signal | ❌ | not defined |

### 2.2 Commands

| Command | Status | Gap |
|---|---|---|
| `run_steps` / `llm_run` | ✅ | — |
| `confirmed` | ✅ | — |
| `correction` | ✅ | — |
| `option_selected` | ✅ | — |
| `replay_step` | ⚠️ | precondition logic weak |
| `replay_operation` | ⚠️ | execution path unverified |
| `replay_all` | ✅ | — |
| `skip_step` | ✅ | — |
| `stop_run` | ✅ | — |
| `save_session` / `load_session` | ✅ | — |
| `update_locator` / `change_locator_scope` | ⚠️ | full replacement flow incomplete |
| `set_agent_enabled` | ❌ | multi-agent control not in MVP |
| `run_page_intelligence` / `clear_page_intelligence_cache` / `get_agent_trace` / `set_model_for_agent` | ❌ | not implemented |
| `highlight_locator` (per-candidate) | ❌ | new cmd needed for Card Highlight stub |
| `plan_edit_manual` | ❌ | new cmd for SchemaError "Edit plan manually" stub |
| `switch_endpoint` | ❌ | requires endpoint registry |
| `fetch_connection_log` | ❌ | new for Offline "View log" stub |

### 2.3 Endpoints (HTTP / non-WS)

| Endpoint | Status | Gap |
|---|---|---|
| File-upload for paperclip | ❌ | only `/api/log` + `/ws` exist |
| Screenshot capture cmd | ⚠️ | `screenshot` in `capability_registry`; tool seam weak |
| Replay REST | ❌ | WS-only |
| Export-code download | ⚠️ | WS cmd writes file; no GET |
| Export-trace download | ❌ | trace_summarizer purpose only |
| Connection-log fetch | ❌ | `/api/log` POST-only |
| Endpoint registry / switch_endpoint | ❌ | not implemented |

### 2.4 Persistence

| Item | Status | Gap |
|---|---|---|
| repair-diff in recorded rows | ⚠️ | passed to LLM, not serialized in step payload (`repaired_from`/`repaired_to` fields render but no diff button) |
| screenshot thumbnail URLs | ❌ | paths not normalized to URLs |
| raw LLM response retention | ⚠️ | stored, not exposed in events |
| dock position | ❌ | not in session model |
| panel resize | ❌ | not tracked |

---

## 3. Frontend (panel-by-panel)

### 3.1 Header (chrome.jsx::Header)

| Control | Status | Note |
|---|---|---|
| Logo / brand divider | ✅ | — |
| Connection status pill | ✅ | — |
| LLM mode toggle | ✅ | D-105 lock |
| Manual mode toggle | 🚫 | D-105 — disabled with reason |
| Agents toggle | ✅ | — |
| Page URL pill | ✅ | — |
| Tokens pill | ✅ | — |
| Dock-right/left/top/float (H9–H12) | ✅ recent-fix (13fbd65) | now calls `applyDock` + `setDockMode` |
| Collapse | ✅ | — |
| Settings gear (H14) | ✅ recent-fix (13fbd65) | removed; defer to S8 |

### 3.2 TabStrip / NowStrip / Footer / CollapsedRail / Resize

| Control | Status | Note |
|---|---|---|
| TabStrip (5 tabs + badges) | ✅ | auto-switch on plan_ready |
| NowStrip primary action | ✅ | RC3 widened guard |
| Footer | ✅ | — |
| CollapsedRail (expand + 5 icons) | ✅ | — |
| Resize handle | ✅ recent-fix (13fbd65) | `createResizeController` instantiated in mount |

### 3.3 LLM tab — Cards

| Card | Status | Gap |
|---|---|---|
| Clarification | ✅ | — |
| Recommendation | ✅ | — |
| PlanDiff | ✅ | — |
| PlanReady (confirm/correction/partial-run) | ✅ | — |
| Permission (Allow Once/For-plan/Deny) | ✅ | — |
| Execution (pause/stop) | ✅ | — |
| LocatorAmbiguity | ⚠️ | Highlight per-candidate = stub (`onClick=(e)=>e.stopPropagation()`); other actions wired |
| Recovery | ✅ | — |
| Completed | ✅ | — |
| Offline | ⚠️ | Reconnect ✅; "View connection log" + "Switch endpoint" stub |
| SchemaError | ⚠️ | Ask LLM repair ✅; "Edit plan manually" + "Open raw response" stub |
| NoBrowser | ❌ | BUG-S8-NO-BROWSER-CARD-001 |
| ApiKey | ❌ | BUG-S8-API-KEY-CARD-001 |
| Otp | ❌ | BUG-S8-OTP-CARD-001 |
| E2EPending | ❌ | BUG-S8-E2E-PENDING-CARD-001 |

### 3.4 LLM tab — Composer

| Control | Status | Gap |
|---|---|---|
| Textarea + Send + Pick element | ✅ | — |
| 4 empty-state suggestion chips | ✅ | — |
| Paperclip attach | ❌ | BUG-S8-COMPOSER-ATTACH-001 (needs upload endpoint) |
| Context chips row (URL · selected · file) | ❌ | BUG-S8-COMPOSER-CONTEXT-CHIPS-001 |
| Camera / screenshot | 🚫 | D-107 hidden; needs backend seam |
| Provider badge | ❌ | P2 |

### 3.5 Steps tab

| Control | Status | Gap |
|---|---|---|
| Toolbar: Add / Pick / Filter input | ✅ | — |
| Filter icon button | ❌ | P2 |
| Run Pending / Run Selected | ✅ | — |
| Per-step intent / status / target / kind / blocked / precondition / outcome / attach / duplicate / delete | ✅ | all D-101 wired |
| Locator chip + improve + view candidates | ✅ | — |

### 3.6 Recorded tab

| Control | Status | Gap |
|---|---|---|
| Replay all / per-row replay | ✅ | — |
| Status badge / locator / outcome / observed / child ops / artifacts | ✅ | — |
| Repair-diff visual | ⚠️ | text rows render; no diff widget / button |
| Screenshot thumbnail tile | ❌ | BUG-S8-RECORDED-SCREENSHOT-TILE-001 |

### 3.7 Code tab

| Control | Status | Gap |
|---|---|---|
| Copy / Save / save-result chip | ✅ | — |
| Diagnostics list | ✅ | not per-line widget |
| Syntax highlighting | ❌ | BUG-S8-CODE-SYNTAX-HIGHLIGHT-001 |
| Top badges row / per-line warnings | ❌ | P2 |

### 3.8 Trace tab

| Control | Status | Gap |
|---|---|---|
| Search + filter chips (7) | ✅ | D-104 |
| Failure detail / LLM telemetry / artifacts / capability-gap / redaction badge | ✅ | — |
| Download trace button | ❌ | needs export-trace endpoint |

### 3.9 Misc

| Item | Status | Note |
|---|---|---|
| AgentsPopover (close + per-agent toggles) | ⚠️ | rows empty until `agent_settings` event lands |
| Dark mode | ❌ | not in v4 design — no action |
| TweaksPanel | 🚫 | prototype-only — correctly omitted |

---

## 4. Runtime Policy / Cross-Cutting

| Domain | Spec | Status | Gap |
|---|---|---|---|
| Permission routing | `allow_once` / `allow_for_plan` / `deny` scope | ⚠️ | only AutonomyMode binary gates; no session-scope grants |
| Redaction | secrets/creds across trace + recorded + code + LLM input | ⚠️ | event-boundary only; LLM prompt not systematically redacted |
| Capability-gap event | detect → emit → record lifecycle | ✅ | fully wired |
| agent_settings stream | hot-update agent/skill/tool policy | ❌ | not implemented (D-106) |
| Manual-mode lockout reason | record reason text | ❌ | tests exist, no reason field |
| Dock / resize persistence | localStorage layout | ❌ | no persistence layer in frontend |
| Replay determinism | step_id stability + replay_repair_specialist | ✅ | step_id passes through all paths |
| Screenshot retention TTL | retention policy | ❌ | no policy |
| Raw LLM response lifecycle | retention vs archive | ⚠️ | stored, no cleanup policy |
| Schema-error recovery | retry-once → fail-closed | ✅ | wired |
| Recording → step-list mapping | step_id keying | ✅ | wired |
| Skill registry → UI | only available skills shown | ❌ | no manifest sent to frontend |
| Test gates | e2e + jsdom + pytest coverage thresholds | ⚠️ | suites exist; no enforced threshold or pre-commit gate |
| Telemetry events | typed events for LLM, skills, ctx, tokens | ⚠️ | 11 trace types; ctx_request_denied / skill_escalation not wired |
| Error budget per purpose | track + enforce | ❌ | not tracked |
| Context sufficiency gates | L0–L5 enforced gates | ⚠️ | levels defined; gates not all enforced |
| Tool-call validation | purpose / phase / precondition / permission | ⚠️ | `tool_schema_policy` + `tool_exposure_enforcement` exist; not all checks emit `tool_call_blocked` |

---

## 5. Master Missing-List (build order)

### P0 — Sprint 7 backend blockers (frontend stub clears once shipped)

1. `agent_settings` event + `set_agent_enabled` command → unblocks AgentsPopover (D-106)
2. `highlight_locator` typed command → clears CardLocatorAmbiguity Highlight stub
3. `fetch_connection_log` cmd + raw connection-log retention → clears CardOffline "View log" stub
4. Endpoint registry + `switch_endpoint` cmd → clears CardOffline "Switch endpoint" stub
5. `plan_edit_manual` cmd + raw LLM response exposure in event → clears CardSchemaError "Edit plan manually" + "Open raw response" stubs

### P0 — State cards (4) requiring new backend events

6. `no_browser` event + launch-browser cmd → CardNoBrowser
7. `api_key_required` event + `set_api_key` cmd → CardApiKey
8. `otp_required` event + `submit_otp` cmd → CardOtp
9. `e2e_pending` event stream → CardE2EPending

### P0 — Execution lifecycle events (LLM scenarios)

10. `execution_started` / `operation_executed` / `operation_failed` events
11. `precondition_failed` event + resolution-option payload
12. `locator_update_request` / `locator_update_applied` events + `improvement_available` flag
13. `clarification_needed` integration (builder exists, wire to all paths)
14. `step_failed` explicit event (currently implicit)
15. `step_skipped` event payload completion

### P1 — Composer + recorded

16. File-upload endpoint (`POST /api/upload`) → composer paperclip
17. Context-state event for composer chips
18. Screenshot capture cmd + thumbnail URL normalization → camera + recorded screenshot tile
19. Repair-diff payload serialization in recorded steps + diff widget

### P1 — Code + trace + recovery

20. Export-code GET endpoint
21. Export-trace GET endpoint → Trace download button
22. `repair_diff` event builder → Recovery card diff render
23. Code syntax highlighting (frontend-only)
24. Schema-retry policy enforcement at all controller boundaries

### P1 — Policy / governance

25. Permission `allow_once` / `allow_for_plan` session-scope grants
26. LLM-input redaction (prompt-side) + redaction_policy logic
27. Manual-mode lockout reason text in events
28. Dock + resize localStorage persistence (frontend-only)
29. Skill availability manifest to frontend
30. Autonomy mode (strict/balanced/auto) in state contract

### P2 — Polish

31. Provider badge in composer
32. Steps filter icon button
33. Code top-badges row + per-line warnings
34. Screenshot retention TTL
35. Raw LLM response cleanup lifecycle
36. Error-budget tracking per purpose
37. Context sufficiency gates enforcement
38. Test-coverage thresholds + pre-commit gate
39. Multi-agent events (`agent_started/progress/result/failed/trace`) — post-MVP
40. Page-intelligence commands (`run_page_intelligence`, etc.) — post-MVP

### Out of scope

- Dark mode (not in v4 design)
- TweaksPanel (prototype-only)

---

## 6. Aggregate Counts

| Layer | Built ✅ | Partial ⚠️ | Missing ❌ | Total tracked |
|---|---|---|---|---|
| LLM-mode capabilities | 4 | 13 | 2 | 19 |
| Backend events | 12 | 6 | 11 | 29 |
| Backend commands | 9 | 3 | 8 | 20 |
| Backend endpoints | 0 | 2 | 5 | 7 |
| Persistence | 0 | 2 | 3 | 5 |
| Frontend controls | ~60 | 5 stub | 11 missing + 4 cards | ~80 |
| Policy domains | 7 | 7 | 5 | 19 |

Roughly **74 % of cross-layer requirements built**; the remaining 26 % is mostly **backend events + endpoints** that unblock 9 frontend stubs/missing cards and the agent control center.

---

**End of gap analysis.** Next: pick a sub-batch (e.g. items 1–5 or 6–9) and feed into writing-plans for an implementation plan.
