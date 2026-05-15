# Sprint 7 Cross-Layer Completion Plan (Batches E1–E8)

**Date:** 2026-05-14
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**HEAD at plan creation:** `13fbd65`
**Predecessor docs:** `docs/superpowers/specs/2026-05-14-spec-vs-build-gap.md`, `.tasks-md/Audit/FRONTEND_ACTIONS_AUDIT.md`, `.tasks-md/Audit/FRONTEND_DESIGN_AUDIT.md`, `.tasks-md/Audit/V4_TESTID_CONTRACT.md`, `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md`, `.tasks-md/Sprints/SPRINT-007-HANDOFF.md`, `.tasks-md/Planning/S7-WRAP-D106-AGENT-POPOVER.md`
**Decomposition source:** 4 parallel E0 sub-agents (backend seams / frontend control map / security & redaction / test plan).

> **Rule of engagement (sprint-finish, not sprint-handoff):**
> - Sprint 7 must finish development. Sprint 8 is testing/hardening only.
> - Do NOT push.
> - Do NOT run paid LLM tests. Do NOT run live websites.
> - Do NOT weaken tests. Do NOT fake runtime state in frontend (backend-payload-only).
> - Do NOT leave visible dead controls (wire, hide-with-reason, or delete).

References *not present* on disk and therefore replaced with closest equivalent (recorded so future readers know):
- `runtime/gent.py` → typo; canonical is `/Users/apple/personal/agent v4/agent.py`.
- `frontend_new_design_prototype/v4/` → no such dir; design ref is `yui (1)/v4/`.

---

## Batch summary table

| Batch | Scope | Backend seams | Frontend changes | Tests | Risk | Stop condition |
|---|---|---|---|---|---|---|
| **E1** | Agent settings event + real Agent popover | B1 `agent_settings.v1` event + `set_agent_enabled.v1` cmd (read-only if runtime cannot truly toggle yet) | Replace `DEFAULT_AGENTS` fallback with payload-driven rows; honest empty state; toggle disabled-or-wired | Backend contract + redaction + jsdom + static-audit + fake-stream smoke | Low — read-only path is fully safe; pure additive | Working tree clean before commit; all gate cmds green; no `DEFAULT_AGENTS` in production frontend |
| **E2** | State cards: NoBrowser / ApiKey / Otp / E2EPending | B2 `no_browser.v1`+`launch_browser.v1`, `api_key_required.v1`+`set_api_key.v1`, `otp_required.v1`+`submit_otp.v1`, `e2e_pending.v1` | Add 4 cards; render gated on payload; write-only secret inputs | Backend redaction tests (S1/S2 from Security matrix) + jsdom + fake-stream | **High** — secrets in flight; requires S8 prompt-side redaction landed first | S8 prompt-side redaction + value-classifier merged AND green BEFORE first secret-bearing UI commit; payloads excluded from `session_state` snapshot |
| **E3** | Stub card actions: highlight + view log + switch endpoint + schema edit + raw response | B3 `highlight_locator.v1`; B4 `fetch_connection_log.v1` + ring buffer; B5 `switch_endpoint.v1` + endpoint registry + allowlist; B6 `plan_edit_manual.v1`; B7 `llm_raw_response.v1` + `fetch_raw_response.v1` (TTL 30 min) | Wire 4 stubs; CardOffline "View log" = setTab("trace") + `fetch_connection_log` request when ring buffer present; **DELETE** `Switch endpoint` if B5 allowlist not complete in same commit (no partial); gate `Open raw response` behind consent | Contract tests per cmd; redaction tests for log + raw + endpoint allowlist; jsdom for each wired button | Med — connection log + raw response are leak vectors; allowlist must precede UI | All 5 stubs are exactly one of {wired with seam, hidden-with-reason, deleted}; B5 ships allowlist + cmd atomically (no half state); raw-response redaction count > 0 in fixture |
| **E4** | Execution lifecycle events | B8 `execution_started.v1` / `operation_executed.v1` / `operation_failed.v1`; B9 `precondition_failed.v1`; B10 `locator_update_request.v1` / `locator_update_applied.v1` + `improvement_available` flag on step payload | Extend `CardExecution` with per-operation rows + precondition strip + locator-update chip; add `data-status="failed"` row variant | Contract tests for triplet ordering + operation_id threading guard; jsdom for new render branches; fake-stream E2E for full run | Med — touches hot path `agent.py:_confirmed_execution_*`; must thread `operation_id` everywhere | Operation_id never None in any emitted lifecycle event; existing run-completed semantics unchanged |
| **E5** | Composer / artifact endpoints | `POST /api/upload` (B-fs: file-upload), `screenshot_capture.v1` cmd + thumbnail URL normalization, `/api/llm/providers` GET, `context_attachments` ref in `user_message` | Wire paperclip / context chips / camera / provider badge; remove disabled stubs | Upload allowlist + size cap + path-traversal tests; screenshot redaction overlay; provider-badge jsdom | Med — file upload + screenshots carry PII | Upload sandbox confirmed under workspace; screenshot redaction overlay merged; no file content fed to LLM by default |
| **E6** | Recorded / recovery / code / trace evidence | `repair_diff.v1` payload on recorded step; screenshot thumbnail URLs normalized; `download_trace.v1` cmd + GET artifact endpoint; code-diagnostic `line` field enforcement | Recorded repair-diff widget + screenshot tile; Code tab syntax highlight (Prism), top badges, per-line warnings; Trace `download` button | Recorded payload contract; export-trace redaction + idempotency; jsdom for each | Low — mostly rendering on existing payloads | Trace export passes redact-idempotent test; bundle manifest carries `RedactionReport` |
| **E7** | Policy hardening | Prompt-side redaction at `prompt_pack_builder` + `llm_runtime_controller.call_with_raw_response`; `allow_once` / `allow_for_plan` session-scope grants on `permission_policy`; manual-mode `lockout_reason` field in events; dock/resize `localStorage` persistence (frontend-only) | Persist dock + resize state; surface lockout reason in disabled tooltip | Redaction value-classifier sweep across every E1–E6 builder; permission scope tests; persistence jsdom | Med — touches every emitted event | `tests/runtime/test_redaction_policy.py` parametrised across every event type; zero unredacted secrets in fixtures |
| **E8** | Full E2E + handoff | (no new seams) | (no UI changes) | Sprint-7-completion gate command block; archive evidence | Low | Every gate cmd exits 0; no `skip`/`xfail` added; handoff doc written |

---

## Backend Seams

> Source: E0-Agent-1 (backend/event contract). All seams additive — never edit existing event payload shapes. New `*.v1` schemas, new `SUPPORTED_FRONTEND_COMMAND_TYPES` entries, new `server.py` routing branches. Each seam carries a versioned schema, declared required/optional fields, declared rejection reasons.

### B1 — `agent_settings` (includes S9 redaction denylist)
- **Current evidence:** zero refs across `runtime/`, `agent.py`, `server.py` (audit `S7-WRAP-D106-AGENT-POPOVER.md:121-130`); `chrome.jsx::AgentsPopover` currently shows honest empty state because `agent_settings` event never arrives.
- **Schema:**
  - Event `agent_settings.v1` payload `{ version: int, agents: [{ key: str, name: str, required: bool, enabled: bool, model_class: str, status: "idle"|"running"|"disabled", last_activity_at: iso8601|null }] }`. Emit on WS connect AND after every accepted `set_agent_enabled`.
  - Cmd `set_agent_enabled.v1 { agent_key: str, enabled: bool }`.
- **Rejection reasons:** `AGENT_KEY_UNKNOWN`, `REQUIRED_AGENT_CANNOT_BE_DISABLED`, `MALFORMED_COMMAND`, `STALE_AGENT_SETTINGS_VERSION` (optimistic-concurrency).
- **Security/redaction (S9 — must land in B1, not deferred):** builder applies an **explicit denylist** for keys `api_key`, `system_prompt_body`, `provider_credential`, `secret`, `token`. Reference system prompts by stable hash, never body. Test `test_agent_settings_event_omits_system_prompt_body` + `test_agent_settings_event_omits_provider_credentials` are part of E1's gate, not deferred.
- **Tests:** `tests/runtime/test_event_contracts_agent_settings.py` + `tests/runtime/test_set_agent_enabled_command_contract.py` + extend `tests/test_websocket_command_event_integration.py`.
- **Batch:** E1.

### B2 — State-card events + cmds
- **Current evidence:** only `permission_required` exists (`event_contracts.py:554-600`); 4 cards tagged ❌ in gap doc §3.3.
- **Schema:**
  - `no_browser.v1 { reason: "not_launched"|"crashed"|"detached", last_url: str|null, recoverable: bool }` + cmd `launch_browser.v1 { target_url: str|null }`.
  - `api_key_required.v1 { provider: str, purpose: str, reason: "missing"|"invalid"|"quota_exhausted" }` + cmd `set_api_key.v1 { provider: str, api_key: str (WRITE-ONLY) }`.
  - `otp_required.v1 { run_id, step_id, channel: "sms"|"email"|"totp", prompt: str, expires_at: iso8601 }` + cmd `submit_otp.v1 { run_id, step_id, otp_value }`.
  - `e2e_pending.v1 { run_id, reason: "browser_warming"|"network"|"acceptance_gate", retry_in_ms: int }` (advisory, no paired cmd).
- **Rejection reasons:** `BROWSER_LAUNCH_BLOCKED`, `PROVIDER_UNKNOWN`, `API_KEY_FORMAT_INVALID`, `OTP_EXPIRED`, `OTP_RUN_CONTEXT_MISMATCH`, `MALFORMED_COMMAND`.
- **Security/redaction:** `set_api_key.v1` + `submit_otp.v1` write-only; server logs only provider + SHA-256 fingerprint. Extend `_redact_api_keys` to mask OTP digits in trace. Exclude these 4 events from `session_state` snapshot on reconnect.
- **Tests:** `tests/runtime/test_state_card_events_contract.py` + `tests/runtime/test_set_api_key_redaction.py` + `tests/runtime/test_otp_command_contract.py` + `tests/runtime/test_no_browser_recovery_loop.py`.
- **Batch:** E2.

### B3 — `highlight_locator`
- **Current evidence:** `improve_locator`/`view_candidates` exist (`server.py:817-849`); CardLocatorAmbiguity per-candidate "Highlight" is `onClick=(e)=>e.stopPropagation()` stub.
- **Schema:** cmd `highlight_locator.v1 { ambiguity_id, candidate_id, duration_ms: int (default 1500, max 5000) }`; reply `locator_highlight_acknowledged.v1 { ambiguity_id, candidate_id, applied: bool }`.
- **Rejection reasons:** `AMBIGUITY_NOT_ACTIVE`, `CANDIDATE_NOT_IN_SET`, `NO_BROWSER_CONTEXT`, `MALFORMED_COMMAND`.
- **Security/redaction:** none — pure UX nudge.
- **Tests:** `tests/runtime/test_highlight_locator_command_contract.py` + extend `tests/test_d101_locator_commands.py`.
- **Batch:** E3.

### B4 — `fetch_connection_log` + ring buffer
- **Current evidence:** only `/api/log` POST (gap §2.3); no WS-frame ring buffer.
- **Schema:** cmd `fetch_connection_log.v1 { since_ts: iso8601|null, limit: int (default 200, max 1000) }`; response `connection_log.v1 { entries: [{ ts, direction: "in"|"out", type, summary, redacted: bool }], truncated: bool, retention_window_ms: int }`. Ring buffer in-process only — 1000 entries OR 15 min.
- **Rejection reasons:** `LOG_LIMIT_EXCEEDED`, `LOG_DISABLED_BY_POLICY`, `MALFORMED_COMMAND`.
- **Security/redaction:** every entry passes `_redact_api_keys` + `_redact_otp` before insertion. URL query-string masker. Header redaction for `Authorization`/`Cookie`/`Set-Cookie`/`X-Api-*`. Sensitive event summaries replaced with `"[sensitive]"`. Cap summary ≤200 chars.
- **Tests:** `tests/runtime/test_connection_log_ring_buffer.py` + `tests/runtime/test_fetch_connection_log_command_contract.py` + `tests/runtime/test_connection_log_redaction.py`.
- **Batch:** E3.

### B5 — `switch_endpoint` + endpoint registry
- **Current evidence:** no registry (gap §2.3 line 108). Backend URL hardcoded at startup.
- **Schema:** new `runtime/endpoint_registry.py` exposing `EndpointEntry { id, label, base_url, kind: "prod"|"staging"|"local"|"custom", auth_required: bool }`. Event `endpoint_registry.v1 { active_id, entries: [...] }` on connect + after switch. Cmd `switch_endpoint.v1 { endpoint_id }`.
- **Rejection reasons:** `ENDPOINT_UNKNOWN`, `ENDPOINT_AUTH_MISSING`, `SWITCH_BLOCKED_DURING_RUN`, `MALFORMED_COMMAND`, `ENDPOINT_NOT_IN_ALLOWLIST`.
- **Security/redaction:** **allowlist required** (S10 from Security matrix). Cmd carries `endpoint_id` not URL. Reject `file://`, non-TLS in prod, non-allowlisted host. Audit event on every switch. Strip auth subdomains from registry display.
- **Tests:** `tests/runtime/test_endpoint_registry.py` + `tests/runtime/test_switch_endpoint_command_contract.py` + `tests/runtime/test_switch_endpoint_during_run_rejection.py`.
- **Batch:** E3.

### B6 — `plan_edit_manual`
- **Current evidence:** `correction` cmd routes plan revision via LLM (`event_contracts.py:904-918`); no manual escape hatch.
- **Schema:** cmd `plan_edit_manual.v1 { plan_id, old_version: int, operations: [PlanDiffOp] }` where `PlanDiffOp` reuses existing `plan_diff_proposed` op grammar (`event_contracts.py:1247-1275`). Validate via existing `plan_diff_validated`, then emit `plan_diff_applied` with `source: "user"`.
- **Rejection reasons:** `PLAN_VERSION_STALE`, `PLAN_NOT_IN_EDITABLE_STATE`, `OPERATION_TYPE_UNKNOWN`, `MALFORMED_COMMAND`, `MUTATION_BLOCKED_DURING_RUN`.
- **Security/redaction:** user-typed values pass through redaction classifier; sensitive values stored encrypted at rest, rendered as `***`.
- **Tests:** `tests/runtime/test_plan_edit_manual_command_contract.py` + `tests/runtime/test_plan_edit_manual_diff_lifecycle.py` + extend `tests/test_event_contracts.py` for `source: "user"` round-trip.
- **Batch:** E3.

### B7 — `llm_raw_response` (gated)
- **Current evidence:** `llm_runtime_controller.call_with_raw_response` captures `result["raw_response"]` at `agent.py:3910` + `:3957`; never emitted.
- **Schema:** event `llm_raw_response.v1 { call_id, purpose, model_class, request_summary, response_text, truncated, redactions_applied: int, archived_at }`. Cmd `fetch_raw_response.v1 { call_id }`. Gated emission only for `purpose` in `{schema_error, plan_correction, recovery_repair}` OR explicit fetch.
- **Rejection reasons (fetch):** `CALL_ID_UNKNOWN`, `RAW_RESPONSE_EXPIRED`, `RAW_RESPONSE_REDACTION_BLOCKED`.
- **Security/redaction:** pipe `response_text` through redaction; truncate ≤8192 chars; TTL 30 min; evict on `run_completed`. Two-stage display: redacted by default, "show original" requires per-session consent + audit event.
- **Tests:** `tests/runtime/test_llm_raw_response_event_contract.py` + `tests/runtime/test_raw_response_redaction.py` + `tests/runtime/test_raw_response_ttl_eviction.py`.
- **Batch:** E3.

### B8 — Execution lifecycle triplet
- **Current evidence:** `_confirmed_execution_*` machinery in `agent.py:299, 1535, 2213+, 2657-2801, 4443-4514` emits only `step_executing`/`step_recorded`/`run_completed`. No operation-grain events.
- **Schema:**
  - `execution_started.v1 { run_id, plan_id, total_operations: int, started_at }`.
  - `operation_executed.v1 { run_id, step_id, operation_id, action_type, duration_ms, result_summary, artifacts: [str] }`.
  - `operation_failed.v1 { run_id, step_id, operation_id, action_type, error_class, error_summary, recoverable: bool, retry_count: int, max_retries: int }`.
- **Rejection reasons:** builders raise `ValueError` on missing `operation_id` — forces threading at every callsite (currently leaks as None around `agent.py:2755`).
- **Security/redaction:** cap `result_summary` ≤500 chars + redact; `artifacts` are paths/URLs only.
- **Tests:** `tests/runtime/test_execution_lifecycle_events_contract.py` + `tests/runtime/test_operation_id_threading.py` + extend `tests/test_event_sequence_contract.py`.
- **Batch:** E4.

### B9 — `precondition_failed`
- **Current evidence:** `runtime/page_state_model.check_page_precondition` + `runtime/locator_update.check_locator_update_precondition:46`; `trace_events.PRECONDITION_CHECK` internal only; `agent.py:809` uses free-form `"replay_precondition_failed"` string.
- **Schema:** event `precondition_failed.v1 { run_id, step_id, operation_id, precondition_type: "page_url"|"element_present"|"auth_state"|"data_ready", expected: str, actual: str, options: [{ id: "navigate"|"wait"|"override"|"skip"|"recover", label, recoverable }] }`. Option-array shape reused from `recovery_needed_structured` (`event_contracts.py:1368-1412`).
- **Rejection reasons:** add `PRECONDITION_OPTION_UNKNOWN` to existing `change_precondition`/`navigate_to_expected` rejections.
- **Security/redaction:** strip URL query-string secrets from `expected`/`actual`; cap each ≤300 chars.
- **Tests:** `tests/runtime/test_precondition_failed_event_contract.py` + `tests/runtime/test_precondition_resolution_flow.py` + extend `tests/test_d101_state_commands.py`.
- **Batch:** E4.

### B10 — `locator_update_request` / `locator_update_applied` + `improvement_available` flag
- **Current evidence:** `runtime/locator_update.process_locator_update:56`; `locator_candidates_ready` event (`event_contracts.py:1336-1365`); no request/applied lifecycle; no `improvement_available` step flag.
- **Schema:**
  - `locator_update_request.v1 { run_id, step_id, operation_id, ambiguity_id, current_locator, trigger: "user"|"weak_score"|"failure_recovery" }`.
  - `locator_update_applied.v1 { run_id, step_id, operation_id, ambiguity_id, old_locator, new_locator, strategy: "deterministic"|"llm_specialist"|"user_pick", confidence: float }`.
  - Additive field on step payload: `improvement_available: bool` + `improvement_reason: str|null` (backward-compatible).
- **Rejection reasons:** `AMBIGUITY_NOT_FOUND`, `NEW_LOCATOR_FAILED_VALIDATION`, `LOCATOR_UPDATE_BLOCKED_DURING_RUN`, `MALFORMED_COMMAND`.
- **Security/redaction:** reject locators >1024 chars (DOM-injection guard).
- **Tests:** `tests/runtime/test_locator_update_lifecycle_events.py` + `tests/runtime/test_improvement_available_flag.py` + extend `tests/test_d101_locator_commands.py`.
- **Batch:** E4.

---

## Frontend Control Map

> Source: E0-Agent-2 (frontend v4 control map). Every wired control gets a `data-testid` per `.tasks-md/Audit/V4_TESTID_CONTRACT.md`. Anything with no backend seam in current batch is **hide-until-seam** or **DELETED** — no honest-disabled-without-reason text.

### LLM-tab cards

| Control | Component file | Required data-testid | Backend seam | Action | jsdom tests |
|---|---|---|---|---|---|
| CardLocatorAmbiguity "Highlight" | `llm-cards.jsx` (CardLocatorAmbiguity foot) | `locator-highlight-${candidate_id}` | B3 | wire E3 | render-when-seam |
| CardOffline "View log" | `llm-cards.jsx:831` | `offline-view-log` | B4 `fetch_connection_log` + ring buffer (E3); UI also opens Trace tab | wire E3 (dispatch B4 + `setTab("trace")`) | 2: dispatch `fetch_connection_log`; click opens trace tab |
| CardOffline "Switch endpoint" | `llm-cards.jsx:831` | `offline-switch-endpoint` | B5 | wire E3 (or DELETE if B5 deferred) | 1: button absent without `connection.endpoints` |
| CardSchemaError "Edit plan" | `llm-cards.jsx:862` | `schema-edit-plan` | B6 | wire E3 | 1: dispatch `plan_edit_manual` |
| CardSchemaError "Open raw" | `llm-cards.jsx:862` | `schema-open-raw` | B7 | wire E3 (consent gate) | 1: toggle raw payload `<pre data-testid="schema-raw">` |
| CardNoBrowser | new export `llm-cards.jsx`, register in `LlmThread` | `card-no-browser`, `no-browser-launch` | B2 | wire E2 | 2: null when no payload; launch dispatch |
| CardApiKey | new export `llm-cards.jsx` | `card-api-key`, `api-key-input`, `api-key-submit` | B2 | wire E2 | 3: null gating; submit shape; value never logged |
| CardOtp | new export `llm-cards.jsx` | `card-otp`, `otp-input`, `otp-submit` | B2 | wire E2 | 3: null gating; submit shape; expired-state badge |
| CardE2EPending | new export `llm-cards.jsx` | `card-e2e-pending`, `e2e-pending-cancel` | B2 | wire E2 | 2: stream rows; cancel dispatch |

### Execution lifecycle inside CardExecution

| Control | Component file | Required data-testid | Seam | Action | jsdom tests |
|---|---|---|---|---|---|
| Per-operation row | `llm-cards.jsx:487` extend | `exec-operation-${operation_id}`, `exec-operation-failed-${operation_id}` | B8 | wire E4 | 2: row appears; failed `data-status="failed"` |
| Precondition strip in exec card | `llm-cards.jsx:487` | `exec-precondition-failed-${step_id}` | B9 | wire E4 | 1: render only on event |
| Locator-update inline chip | `llm-cards.jsx:487` | `exec-locator-update-${step_id}` | B10 | wire E4 | 1: chip toggles on start/resolved |
| Execution started banner | `llm-cards.jsx:495` | `exec-started-at` | B8 | wire E4 | 1: timestamp rendered |

### Composer (LLM tab)

| Control | Component file | Required data-testid | Seam | Action | jsdom tests |
|---|---|---|---|---|---|
| Paperclip | `llm-cards.jsx:922` Composer actions | `aw-composer-attach` | `/api/upload` (E5) | hide-until-seam E2; wire E5 | 2: disabled pre-seam; dispatch `attach_file` post-seam |
| Context chips | `llm-cards.jsx:922` above textarea | `aw-composer-context`, `aw-composer-context-chip-${ref_id}` | `context_attachments` ref (E5) | wire E5 | 2: chip add/remove; outgoing payload `context_refs` |
| Camera | `llm-cards.jsx:944` | `aw-composer-camera` | screenshot cmd (E5) | hide-until-seam | 1: disabled state asserted |
| Provider badge | `llm-cards.jsx:944` | `aw-composer-provider` | `/api/llm/providers` (E5) | wire E5 | 2: renders payload label; honest dash when null |

### Steps tab

| Control | Component file | data-testid | Seam | Action | jsdom |
|---|---|---|---|---|---|
| Filter icon button | `secondary-tabs.jsx:683` | `steps-filter-toggle` | none (client-only, focuses existing input) | wire E1 | 1: click focuses input |

### Recorded tab

| Control | Component file | data-testid | Seam | Action | jsdom |
|---|---|---|---|---|---|
| Repair-diff widget | `secondary-tabs.jsx:994` | `recorded-repair-diff-${id}`, `recorded-repair-diff-toggle-${id}` | E6 repair_diff payload | wire E6 | 2: toggle; null when fields absent |
| Screenshot thumbnail | `secondary-tabs.jsx:963` artifact loop | `recorded-screenshot-${id}-${artifactId}` | E5 thumbnail URL | wire E5 (after thumbnail normalization) | 1: img only when `kind==="screenshot"` |

### Code tab

| Control | Component file | data-testid | Seam | Action | jsdom |
|---|---|---|---|---|---|
| Syntax highlight | `secondary-tabs.jsx:1094` | retain `code-preview`; add `data-highlight="prism"` | client-only (Prism lib) | wire E6 | 1: highlighted tokens span present |
| Top badges (lang, line count) | `secondary-tabs.jsx:1040` | `code-lang-badge`, `code-line-count` | derived from payload | wire E6 | 1: language from `codePreview.language` |
| Per-line warnings | `secondary-tabs.jsx:1094` | `code-line-warning-${lineNo}` | `codeDiagnostics[i].line` (E6 enforcement) | wire E6 | 1: warning gutter for matching line |

### Trace tab

| Control | Component file | data-testid | Seam | Action | jsdom |
|---|---|---|---|---|---|
| Download trace button | `secondary-tabs.jsx:1356` (NEW) | `trace-download` | E6 `download_trace` | hide-until-seam; wire E6 | 1: hidden until `traceMeta.download_url`; dispatch `download_trace` |

### Agents popover

| Control | Component file | data-testid | Seam | Action | jsdom |
|---|---|---|---|---|---|
| Real agent rows | `chrome.jsx:296` | existing `aw-agent-row-${key}`, `aw-agent-toggle-${key}` | B1 | wire E1 | 3: rows from payload; empty state when none; toggle dispatch when enabled |

### Header

Settings gear **removed in commit 13fbd65** — confirmed: no `aw-settings` / `gear` testid in `chrome.jsx`. Remaining controls (status pill, mode toggle, agents toggle, page pill, run pill, dock buttons, collapse) are wired with stable testids. Manual mode button (`aw-mode-manual`) stays disabled with `data-disabled-reason="sprint-8"` per D-105.

### DELETE list (honest-UI rule)

- `Switch endpoint` button **deleted** unless E3 ships B5 in the same commit (no honest disabled-reason text possible without registry).
- Any leftover `DEFAULT_AGENTS` constant — confirm removed in E1.

---

## Security & Redaction Risk Matrix

> Source: E0-Agent-3 (security). Current redaction limits: `runtime/redaction_policy.py` is key-name scrubber only (no value-pattern classifier, no idempotency, no report integration); `event_contracts._redact_api_keys` is regex-only for `sk-` prefixes; `context_levels.L5` declares excludes but enforcement is unverified; `llm_runtime_controller` stores `raw_response` unredacted. **S8 prompt-side redaction must land before E2.**

| ID | Item | Classification | Mitigation gate | Batch |
|---|---|---|---|---|
| **S1** | CardApiKey input | needs-secure-storage + needs-redaction-policy | secret store (in-memory keyring, never persisted); value-pattern classifier (entropy + `sk-`/`xox`/`ghp_`/`AKIA`/JWT); `sensitive=true` envelope mark; idempotent `[REDACTED:api_key:<hash8>]` sentinel | E2 (blocked on S8) |
| **S2** | CardOtp input | needs-redaction-policy | in-memory only; TTL ≤5 min; explicit zeroize on consume; `{{otp}}` placeholder in codegen; never in raw_response | E2 |
| **S3** | Raw LLM response card | needs-redaction-policy + needs-consent | run upgraded redactor on raw before persistence and emission; two-stage display (redacted default, "show original" = consent + audit); strip prompt echoes via sensitive-input registry | E3 |
| **S4** | `fetch_connection_log` | needs-redaction-policy | URL query-param masker; header redaction (`Authorization`, `Cookie`, `Set-Cookie`, `X-Api-*`); frame size cap; binary frame summary (length + sha) | E3 |
| **S5** | File upload (paperclip) | needs-redaction-policy | MIME allowlist (txt/pdf/csv/json/png/jpg); size cap 5 MB; sandbox dir under workspace; reject `..`; UUID rename; file content NEVER enters prompt unless user approves | E5 |
| **S6** | Screenshot capture | needs-consent + needs-redaction-policy | permission_policy grants `screenshot`; redaction overlay blacks-out sensitive DOM rects (`input[type=password]`, `otp|cvv|ssn|card` fields) BEFORE capture; never to LLM without per-capture approval | E5 |
| **S7** | Trace export | needs-redaction-policy | run upgraded redactor over full bundle pre-write; attach `RedactionReport` to manifest; idempotency (re-redact = no-op) | E6 |
| **S8** | Prompt-side redaction | needs-redaction-policy | hook redactor into `prompt_pack_builder` + `llm_runtime_controller.call_with_raw_response`; sensitive-field registry references by hash, not value | **E2 prerequisite** |
| **S9** | `agent_settings` exposure | needs-redaction-policy | emit only name/enabled/model-class; denylist `api_key`, `system_prompt_body`, `provider_credential`; system prompts by hash | E1 |
| **S10** | `switch_endpoint` | needs-secure-storage + needs-consent | allowlist of endpoints (cmd carries id, not URL); reject `file://`, non-TLS in prod; audit event on every switch | E3 |

**Build-now (foundation, E2 must include):**
- S8 prompt-side redaction hook.
- Redaction value-classifier upgrade (entropy + prefixes + URL params + headers) covers S1, S2, S4, S7.
- S7 trace-export redaction + report attachment (lands E6 but classifier prerequisite is here).

**Build-later:** S3 raw-response UI (E3, needs S8), S5 file upload (E5), S6 screenshot overlay (E5), S10 switch_endpoint (E3 — UI only after allowlist + audit land in same commit).

**S9 (agent_settings redaction) is NOT build-later — it ships inside B1 (E1).** See B1 schema/security section.

---

## Test Plan & Validation Gates

> Source: E0-Agent-4 (test/e2e map). Constraints applied to every batch.

> Note on test paths: every `tests/...` and `frontend/tests-dom/...` path below is a **deliverable to create inside that batch**, not a pre-existing file. Batch is not complete until each declared path exists, has the listed test names, and passes.

**Environment (every batch):**
```
unset OPENAI_API_KEY
export AUTOWORKBENCH_E2E_MODE=fake_llm
export AUTOWORKBENCH_LLM_MODE=complete_llm
```

### E1 — Agent settings popover + dispatch
**Backend:** `tests/runtime/test_event_contracts_agent_settings.py` (shape, required-keys, unknown rejection, round-trip, redaction).
**Frontend jsdom:** `frontend/tests-dom/agents-popover-real-payload.test.jsx` (rows from payload, empty state, no `DEFAULT_AGENTS` bleed, toggle dispatch, capability-flag disable).
**Static guard:** extend `frontend/tests-dom/static-audit.test.jsx` `FORBIDDEN_IDENTIFIERS` with `DEFAULT_AGENTS` outside `chrome.jsx`.
**E2E (fake-backend):** `tests/e2e/test_v4_agent_popover_smoke.py`.
**Cmds:**
```
cd frontend && npm test && npm run build
python -m pytest tests/runtime/test_event_contracts_agent_settings.py tests/runtime/test_agent_settings_redaction.py -q
python -m pytest -q --ignore=tests/e2e
python -m pytest tests/e2e/test_v4_panel_smoke.py tests/e2e/test_v4_agent_popover_smoke.py -q
```

### E2 — State cards (NoBrowser / ApiKey / Otp / E2EPending)
**S8 prereq gate (MUST be green BEFORE any E2 product code commit):**
```
python -m pytest tests/runtime/test_redaction_value_classifier.py \
                 tests/runtime/test_prompt_pack_builder.py::test_prompt_assembly_redacts_secret_values \
                 tests/runtime/test_llm_runtime_controller.py::test_no_secret_in_outbound_messages -q
```
If above does not exit 0, halt E2 and finish S8 first.

**Backend (E2 contract):** `tests/runtime/test_state_card_events_contract.py` + `test_set_api_key_redaction.py` + `test_otp_command_contract.py` + `test_no_browser_recovery_loop.py`.
**Frontend jsdom:** `frontend/tests-dom/card-no-browser.test.jsx`, `card-api-key.test.jsx`, `card-otp.test.jsx`, `card-e2e-pending.test.jsx`.
**Static guard:** `static-audit.test.jsx` FORBIDDEN += `SAMPLE_API_KEY`, `MOCK_OTP`.
**E2E (fake-backend):** `tests/e2e/test_flow_state_cards.py`.
**Cmds:** S8 prereq gate above, then E1 cmds + new E2 contract files + jsdom files + E2E.

### E3 — Stub card actions (highlight / view-log / switch-endpoint / schema-edit / raw)
**Backend:** per-seam contract tests (B3/B4/B5/B6/B7 files listed in Backend Seams).
**Frontend jsdom:** wire-tests per stub above.
**Static guard:** `static-audit.test.jsx` FORBIDDEN += `MOCK_RAW_RESPONSE`, `SAMPLE_ENDPOINTS`.
**E2E:** `tests/e2e/test_flow_locator_highlight.py` + `test_flow_offline_recovery.py` + `test_flow_schema_error_edit.py`.

### E4 — Execution lifecycle
**Backend:** `tests/runtime/test_execution_lifecycle_events_contract.py` + `test_operation_id_threading.py` + `test_precondition_failed_event_contract.py` + `test_locator_update_lifecycle_events.py` + `test_improvement_available_flag.py`.
**Frontend jsdom:** `frontend/tests-dom/exec-operations.test.jsx` + `exec-precondition.test.jsx` + `exec-locator-update.test.jsx`.
**E2E:** `tests/e2e/test_flow_execution_full_run.py`.

### E5 — Composer / artifact endpoints
**Backend:** `tests/backend/test_upload_endpoint.py` (allowlist, traversal, size cap) + `tests/runtime/test_screenshot_redactor.py` (password field blacked out, screenshot-not-to-LLM-by-default) + `tests/runtime/test_providers_endpoint.py`.
**Frontend jsdom:** `composer-paperclip.test.jsx`, `composer-context-chips.test.jsx`, `composer-provider-badge.test.jsx`.
**E2E:** `tests/e2e/test_flow_composer_attach.py`.

### E6 — Recorded / recovery / code / trace evidence
**Backend:** `tests/runtime/test_recorded_repair_diff_payload.py` + `test_artifact_bundle_redaction.py::test_export_runs_redaction_and_attaches_report` + `test_redact_idempotent` + `test_exported_bundle_contains_no_sk_prefixed_tokens`.
**Frontend jsdom:** `recorded-repair-diff.test.jsx`, `recorded-screenshot-tile.test.jsx`, `code-syntax-highlight.test.jsx`, `trace-download.test.jsx`.
**E2E:** `tests/e2e/test_flow_recorded_repair.py` + `test_flow_trace_export.py`.

### E7 — Policy hardening
**Backend:** `tests/runtime/test_redaction_policy.py` parametrised across every E1–E6 event; `tests/runtime/test_permission_scope_grants.py` (allow_once/allow_for_plan/deny); `tests/runtime/test_manual_mode_lockout_reason.py`.
**Frontend jsdom:** `dock-resize-persistence.test.jsx` (localStorage round-trip).
**E2E:** `tests/e2e/test_flow_reconnect_midrun.py`.

### E8 — Sprint-7-completion gate
```
unset OPENAI_API_KEY
export AUTOWORKBENCH_E2E_MODE=fake_llm
export AUTOWORKBENCH_LLM_MODE=complete_llm

cd frontend && npm test -- --run && npm run build && cd ..

# Static / mock-gating guard (must print no matches outside tests-dom)
grep -rEn "DEFAULT_AGENTS|SAMPLE_(STEPS|PLAN|RECORDED|CODE|TRACE|PERMISSION|LOCATORS|PLAN_DIFF|RECOVERY|RUN_SUMMARY|ARTIFACTS|API_KEY|OTP|ENDPOINTS)|MOCK_(PLAN|PERMISSION|DIFF|ARTIFACTS|RAW_RESPONSE|OTP)" frontend/src/ frontend/aw-ide-panel.jsx | grep -v "tests-dom" | grep -v "// audit" ; test $? -eq 1

python -m pytest -q --ignore=tests/e2e --tb=line

python -m pytest tests/runtime/test_event_contracts_agent_settings.py \
                 tests/runtime/test_state_card_events_contract.py \
                 tests/runtime/test_highlight_locator_command_contract.py \
                 tests/runtime/test_fetch_connection_log_command_contract.py \
                 tests/runtime/test_switch_endpoint_command_contract.py \
                 tests/runtime/test_plan_edit_manual_command_contract.py \
                 tests/runtime/test_llm_raw_response_event_contract.py \
                 tests/runtime/test_execution_lifecycle_events_contract.py \
                 tests/runtime/test_precondition_failed_event_contract.py \
                 tests/runtime/test_locator_update_lifecycle_events.py \
                 tests/runtime/test_redaction_policy.py \
                 tests/runtime/test_redaction_value_classifier.py \
                 tests/backend/test_upload_endpoint.py \
                 tests/runtime/test_artifact_bundle_redaction.py -q

python -m pytest tests/e2e/test_v4_panel_smoke.py \
                 tests/e2e/test_v4_agent_popover_smoke.py \
                 tests/e2e/test_flow_state_cards.py \
                 tests/e2e/test_flow_locator_highlight.py \
                 tests/e2e/test_flow_offline_recovery.py \
                 tests/e2e/test_flow_schema_error_edit.py \
                 tests/e2e/test_flow_execution_full_run.py \
                 tests/e2e/test_flow_composer_attach.py \
                 tests/e2e/test_flow_recorded_repair.py \
                 tests/e2e/test_flow_trace_export.py \
                 tests/e2e/test_flow_reconnect_midrun.py \
                 tests/e2e/test_mvp_001_lifecycle_smoke.py -q --timeout=300

# Policy guards
! grep -rE "@pytest\.mark\.(skip|xfail)" tests/runtime tests/e2e | grep -v "BUG-S6-FINAL-001"
! grep -rE "openai\.com|live website|requests\.get\(\"http" tests/e2e | grep -v "fixtures"
```

**Completion criteria:**
1. Every command above exits 0.
2. Static-audit guard returns no matches outside `tests-dom/`.
3. Every batch closure cites: backend test commit SHA, jsdom commit SHA, fake-backend E2E commit SHA, redaction test commit SHA (per S7-0007 Rule 6).
4. No new `BUG-S7-*` Critical/High ticket unscoped in `Backlog`.

---

## PRD-to-Plan Cross-Reference

| PRD / spec section | Covered by batch |
|---|---|
| PRD_v2_3 backend modular pack — agent registry | B1 (E1) |
| Complete-LLM frontend UI spec §AgentsPopover | E1 frontend |
| Complete-LLM frontend UI spec §State Cards (NoBrowser/ApiKey/Otp/E2E) | E2 |
| Complete-LLM frontend UI spec §LocatorAmbiguity Highlight | E3 (B3) |
| Complete-LLM frontend UI spec §Offline / SchemaError | E3 (B4/B5/B6/B7) |
| P0 Scenarios §1 Plan mode test-data redaction | E2 (S8 prereq) |
| P0 Scenarios §3 Locator ambiguity scoped chain | E3+E4 (B3+B10) |
| P0 Scenarios §5 Precondition handling | E4 (B9) |
| P0 Scenarios §6 Failure recovery | E4 (B8) + E6 (repair payload) |
| P0 Scenarios §7 Permission autonomy | E7 (allow_once/for_plan) |
| Runtime policy §Redaction | S8/S1–S7/S9/S10 across all batches |
| Runtime policy §Capability gap | already ✅ (gap doc §4) |
| Runtime policy §Manual mode lockout reason | E7 |
| Runtime policy §Dock/resize persistence | E7 |
| Frontend UI spec §Composer paperclip/chips/camera/badge | E5 |
| Frontend UI spec §Recorded repair-diff/screenshot tile | E5+E6 |
| Frontend UI spec §Code syntax highlight | E6 |
| Frontend UI spec §Trace download | E6 |

---

## Build order rationale

- **E1 first** — minimal blast radius; establishes versioned-event + optimistic-concurrency pattern reused by every later seam.
- **E2 second** — only after S8 prompt-side redaction lands; secret-bearing inputs require this foundation.
- **E3 third** — clears 5 stub buttons + introduces TTL/retention/allowlist patterns reused later.
- **E4 fourth** — execution lifecycle threading must precede any per-operation evidence work.
- **E5 fifth** — composer/screenshot endpoints depend on redaction overlay + execution events for context.
- **E6 sixth** — recorded/recovery/code/trace evidence consumes E4 lifecycle + E5 thumbnails.
- **E7 seventh** — cross-cutting hardening once every event exists, so redaction matrix can be parametrised across all of them.
- **E8 final** — handoff doc + completion gate; no new product code.

---

## Stop conditions (per batch)

1. Working tree must be clean before starting a batch (untracked references like `1AutoWorkbench — print.pdf`, `yui (1)/` are excluded per user decision).
2. No paid LLM env var (`OPENAI_API_KEY` must be unset for test runs).
3. No live website fetches in tests (only `tests/e2e/fixtures/` + fake event stream).
4. No new `@pytest.mark.skip` / `@pytest.mark.xfail` outside the existing BUG-S6-FINAL-001 12-failure budget.
5. No production frontend identifier on the FORBIDDEN list.
6. `/superpowers:review` + caveman review run on the batch diff; blockers fixed.
7. No push.

---

**End of plan.** Next: review this plan (review skill + caveman review), fix any PRD-mapping gaps, commit docs-only, then start E1.
