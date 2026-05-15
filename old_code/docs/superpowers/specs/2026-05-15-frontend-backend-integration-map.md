# AutoWorkbench — Frontend ⇄ Backend integration map (master)

Date: 2026-05-15
Branch: `s7/clusters-6-11-complete-llm-mode`
Frontend baseline: commit `2789936` — byte-identical to the original
`AutoWorkbench.html` design bundle.

This is the single source of truth for everything that needs to be
built before Complete-LLM-Mode can run end-to-end. It is the
*read-only* product of a four-pass systematic review:

1. Frontend interaction surface (every onClick, every state, every
   mock value).
2. Backend protocol surface (every WS handler, every event builder,
   every public agent method).
3. Spec mining — the three "complete LLM mode" docs in repo root
   plus the seven-document `PRD_v2_3_Modular_Pack_v2/` set.
4. Cross-reference + gap table per spec contract.

No code changes were made while writing this doc. Each item below is
a discrete task you can pick off the list and verify with the
included test plan.

---

## 0. Authoritative documents

Every claim below cites at least one of these. If two specs disagree,
both are cited and the disagreement is logged under §10.

* `autoworkbench_complete_llm_mode_frontend_ui_spec.md` (887 lines) —
  **FE UI spec**. Visual surfaces, cards, keyboard behaviour.
* `autoworkbench_complete_llm_mode_runtime_policy_spec.md` (1391 lines)
  — **runtime policy**. LLM purposes, deterministic-first rules,
  model routing, context policy, tool exposure, token budgets.
* `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` (2624
  lines) — **P0 scenarios**. 8 end-to-end product scenarios with
  acceptance hooks.
* `PRD_v2_3_Modular_Pack_v2/00_MASTER_INDEX.md` — entry point.
* `PRD_v2_3_Modular_Pack_v2/01_PRODUCT_WORKFLOWS.md` (517) — 10 named
  workflows with expected step sequences.
* `PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md` (2069) — LLM runtime
  acceptance criteria.
* `PRD_v2_3_Modular_Pack_v2/03_FRONTEND_RUNTIME.md` (319) — FE PRD.
  Mode list, picker flow, dock layout.
* `PRD_v2_3_Modular_Pack_v2/04_BACKEND_EVENT_CONTRACT.md` (193) —
  authoritative WS event + command list.
* `PRD_v2_3_Modular_Pack_v2/05_CODEGEN_REPLAY_PERSISTENCE.md` (1080) —
  save/load, replay, locator update, expected outcome, precondition
  guard v1.
* `PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md` (394)
  — 5-phase build plan + 12 required tests.
* `PRD_v2_3_Modular_Pack_v2/07_MULTI_MODEL_ORCHESTRATION.md` (663) —
  Page Intelligence / Locator / Debug / Codegen-Reviewer / Risk
  Judge.

---

## 1. Frontend as built today

7 jsx files, transpiled in the browser by Babel-standalone, mounted
from `frontend/index.html`. State lives in `useTweaks` value bag
(`frontend/tweaks-panel.jsx:162`).

### 1.1 Surfaces present today

| Surface | File:line | Spec coverage |
|---|---|---|
| 5 tabs (LLM/Steps/Recorded/Code/Trace) | `frontend/chrome.jsx:134-156` | FE UI spec §3 ✅ |
| LLM tab decision cards (15 cards) | `frontend/llm-tab.jsx:52-700` | FE UI spec §5.1–5.8, §10 ✅ |
| Steps tab + ManualBuilder | `frontend/secondary-tabs.jsx:6, 256` | FE UI spec §6, §10.2 |
| Recorded tab | `frontend/secondary-tabs.jsx:477` | FE UI spec §7 |
| Code tab | `frontend/secondary-tabs.jsx` | FE UI spec §8 |
| Trace tab (8 filters) | `frontend/secondary-tabs.jsx:745` | FE UI spec §9 |
| Global header (conn, run, tokens, agents, dock) | `frontend/chrome.jsx:57-130` | FE UI spec §4.1 + §4.3 |
| Now-strip / activity strip | `frontend/llm-tab.jsx` (NowStrip) | FE UI spec §4.2 |
| Element picker hooks | `frontend/secondary-tabs.jsx:45, 449` | FE UI spec §6.6 + FE PRD §"Element picker" |
| Dock modes (right/left/top/float) | `frontend/app.jsx:88, 117` | FE PRD §"Docked layout" |
| Agents popover (Agent Control Center) | `frontend/chrome.jsx:281` | PRD 04 §86–107 (multi-agent), **not in FE UI spec** |

### 1.2 Lifecycle states present today

`STATE_META` (`frontend/app.jsx:19-54`) — 17 keys: `idle, planning,
clarify, recommend, plan, diff, permit, exec, locator, recover, done,
offline, schema, nobrowser, apikey, otp, e2e`.

The FE PRD (`03_FRONTEND_RUNTIME.md` §"mode behavior", line 76-83)
defines a smaller **mode** vocabulary: `idle, drafting, plan_review,
clarification, executing, recovery, completed`. The current 17-state
list is the larger "rendering destination" set that also covers
backend-degraded states (`offline, schema, nobrowser, apikey, otp,
e2e`) plus implementation-specific intermediates (`planning,
recommend, diff, permit, locator`).

### 1.3 Outbound network surface

`grep -rn "fetch\|WebSocket\|XMLHttpRequest\|EventSource"
frontend/*.jsx` — **0 hits**. The FE does not talk to the backend
today. Every onClick that should send a command is dead.

### 1.4 Hardcoded mock data

| Field | File:line | Replace with |
|---|---|---|
| `runId = "run_a91b"` | `frontend/app.jsx:78` | `run_started.run_id` |
| `tokenInfo = { tok: "8.4k", cost: "0.12" }` | `frontend/app.jsx:79` | `token_report` event |
| Tab `counts = { steps:5, rec:4, code:1, trace:25 }` | `frontend/app.jsx:80` | derived from `session_state` |
| `agentsSummary` (5 dots) | `frontend/app.jsx:82-93` | `agent_settings` event |
| 6 assertion candidates | `frontend/llm-tab.jsx:104-110` | `recommendation_ready` |
| 3 locator candidates | `frontend/llm-tab.jsx:380-393` | `locator_update_request` / `locator_candidates_ready` |
| ManualBuilder mock pick | `frontend/secondary-tabs.jsx:9-18` | `arm_picker` round-trip |
| 5 hardcoded plan steps | `frontend/secondary-tabs.jsx:312-423` | `session_state.steps` |
| 26 hardcoded trace events | `frontend/secondary-tabs.jsx:745-770` | derived event stream |
| Composer chips `/pricing`, `2 selected`, `users.csv` | `frontend/llm-tab.jsx:744` | live url + selection + attachments |

---

## 2. Backend as built today

### 2.1 WS inbound (`server.py`)

| msg_type | server.py:line | required fields | spec id | normalised? | status |
|---|---|---|---|---|---|
| `run_steps` / `llm_run` | 425 | `steps` | PRD 04 §46 | no | ✅ |
| `export_code` | 445 | `code, path?` | PRD 05 §44-72 | no | ✅ |
| `save_snapshot` | 505 | — | PRD 05 §258-332 | no | ✅ |
| `replay_one` | 532 | `step_id` | PRD 04 §50 | no | ✅ |
| `replay_all` | 547 | `stop_on_error?` | PRD 04 §52 | no | ✅ |
| `confirmed` | 597 | normalised | PRD 04 §47 | yes | ✅ |
| `correction` | 597 | normalised | PRD 04 §47 | yes | ✅ |
| `option_selected` | 597 | normalised | PRD 04 §47 | yes | ✅ |
| `stop_run` | 624 | normalised | PRD 04 §54 | yes | ✅ |
| `skip_step` | 655 | `step_id` | PRD 04 §53 | yes | ✅ |
| `save_session` | 679 | normalised | PRD 04 §55 | yes | ✅ |
| `load_session` | 723 | `path` | PRD 04 §55 | yes | ✅ |
| `permission_decision` | 767 | normalised | runtime policy §permission_policy | yes | ✅ |
| `change_precondition` | 791 | `step_id, run_id, expected_url \| new_precondition` | PRD 05 Replay Precondition Guard v1 | yes | ✅ |
| `navigate_to_expected` | 861 | `step_id, run_id` | PRD 05 Replay Precondition Guard v1 | yes | ✅ |
| `arm_picker` | 930 | `step_id` | FE UI spec §6.6 | no | ✅ |
| `reset` | 939 | — | — | no | ✅ |
| `improve_locator` / `view_candidates` | 946 | `step_id` | FE UI spec §6.6 | yes | ⚠ **stub** |
| `change_locator_scope` | 984 | `step_id, scope` | FE UI spec §6.6 | yes | ⚠ **stub** |
| `highlight_locator` | 1039 | `candidate_id, duration_ms?` | FE UI spec §6.6 | no | ⚠ **stub** |
| `switch_endpoint` | 1078 | `endpoint_id` | FE UI spec §10.6 | no | ⚠ **stub** |
| (fall-through) | 1130 | — | — | — | rejects with `COMMAND_NOT_SUPPORTED` |

### 2.2 WS outbound (`runtime/event_contracts.py`)

**Builders that have ≥ 1 emit site:** 18.
`build_backend_event_envelope`, `build_runtime_rejection_payload`,
`build_run_completed_payload`, `build_recovery_needed_payload`,
`build_session_state_event`, `build_run_started_payload`,
`build_step_validating_payload`, `build_step_executing_payload`,
`build_step_failed_payload`, `build_step_skipped_payload`,
`build_no_browser_event`, `build_api_key_required_event`,
`build_endpoint_registry_event`, `build_agent_settings_event`,
`build_typed_ready_envelope`, `build_stop_run_result_event`,
`build_save_result_event`, `build_load_result_event`.

**Builders defined but never emitted:** 24.
`build_permission_required_payload` (586),
`build_human_input_required_event` (744),
`build_e2e_pending_event` (797),
`build_execution_started_event` (869),
`build_operation_executed_event` (919),
`build_operation_failed_event` (977),
`build_precondition_failed_event` (1045),
`build_locator_update_request_event` (1106),
`build_locator_update_applied_event` (1159),
`build_browser_ready_event` (1347),
`build_page_analysis_started_event` (1695),
`build_page_summary_ready_event` (1725),
`build_page_analysis_failed_event` (1754),
`build_recommendation_ready_event` (1784),
`build_capability_gap_event` (1816),
`build_schema_error_event` (1851),
`build_provider_error_event` (1889),
`build_malformed_output_error_event` (1923),
`build_plan_diff_proposed_event` (1955),
`build_plan_diff_validated_event` (1986),
`build_plan_diff_applied_event` (2016),
`build_locator_candidates_ready_event` (2044),
`build_recovery_needed_structured_event` (2076),
`build_token_report_event` (2123).

**Builders MISSING entirely** (named by `04_BACKEND_EVENT_CONTRACT.md`
but never declared):

| Spec event | PRD 04 line | Status |
|---|---|---|
| `plan_ready` | §27 | no `build_plan_ready_*` exists |
| `clarification_needed` | §28 | only `build_human_input_required_event` (744) — semantically equivalent? |
| `code_update` | §35 | no builder exists |
| `agent_started` / `agent_progress` / `agent_result` / `agent_failed` / `agent_trace` | §100-107 | no builders (multi-agent track not yet emitted) |

### 2.3 AgentLoop / capability surface

* `agent.py:1471 AgentLoop.run(steps)` — async planning/exec loop.
* `agent.py:929 replay_one`, `:1083 replay_all`.
* `agent.py:1221 _build_spec_snapshot`, `:1267 _build_session_state_payload`.
* `agent.py:484 _current_phase`, `:496 _current_run_session_id`.
* `agent.py:154 .llm: LLMClient`, `:176 .phase_tracker`.
* `browser.py:193 launch_browser`, `:187 get_page`, `:239 inject_panel`,
  `:804 arm_picker`.
* `locator.py:16 find_best_locator`.
* `llm.py:23 LLMClient.chat`, `:35 .reset`. Orchestrator lives in
  `llm/` but is not called directly from the WS handler.
* `runtime/session_store.py:23 SessionSpec`, `:89 save_session_to_file`,
  `:134 load_session_from_file`.

### 2.4 Runtime policy enforcement (where the rules already live)

* Deterministic-first gateway — `runtime/deterministic_fast_path_gateway.py`
  (no LLM call when locator validates count==1).
* Model routing — `runtime/model_router.py` (cheap vs main per
  purpose).
* Skill loading — `runtime/skill_manager.py`.
* Context policy — `runtime/context_policy.py:67` `_redact_secrets`.
* Tool exposure — `runtime/tool_exposure_enforcement.py`.
* Token budget — `runtime/token_budget_policy.py`.
* Schema validation — `runtime/schema_validation_policy.py:888-913`.
* Permission gating — `runtime/permission_policy.py:75+`.
* Run-id match — `runtime/event_contracts.py:204`.
* Workspace containment — `server.py:472-481` (export_code path
  resolve).

These exist and gate the LLM today. The integration tasks below
need to be careful **not to short-circuit any of them** when wiring
new buttons.

### 2.5 Boot degraded modes

`server.py:223 _BOOT_STATE` — `api_key_ok, api_key_reason, browser_ok,
browser_error, stub_mode`. On WS connect: emits
`api_key_required` / `no_browser` accordingly (server.py:368, 382).
Spec basis: PRD 06 phase 1 §"degraded boot" + runtime policy spec
§"degraded modes".

---

## 3. Mode model — spec vs. implementation

The FE PRD canonical mode list (`03_FRONTEND_RUNTIME.md` §"mode
behavior", lines 76-83) is **7 user-facing modes**:

```
idle → drafting → plan_review → (clarification | executing) → recovery → completed
```

The current implementation `frontend/app.jsx:19-54` ships 17 states.
The deltas:

| State (current) | Spec mode | Role | Keep? |
|---|---|---|---|
| `idle` | `idle` | session ready | ✅ |
| `planning` | (sub-phase of plan_review) | analyzing page | render-only; collapse into plan_review status field |
| `clarify` | `clarification` | clarification | ✅ rename to match spec |
| `recommend` | (variant of plan_review) | recommendation review | P0 scenario 2 — keep as distinct render |
| `plan` | `plan_review` | confirm-to-run | ✅ rename |
| `diff` | `plan_review` | plan diff | keep as variant of plan_review |
| `permit` | (orthogonal) | permission required | keep — can interrupt any mode |
| `exec` | `executing` | step running | ✅ rename |
| `locator` | (variant of executing) | ambiguous locator | keep — P0 scenario 3 |
| `recover` | `recovery` | recovery needed | ✅ rename |
| `done` | `completed` | run finished | ✅ rename |
| `offline` | (degraded) | ws closed | keep — FE UI spec §10.6 |
| `schema` | (degraded) | invalid LLM output | keep — FE UI spec §10.5 |
| `nobrowser` | (degraded) | no playwright context | keep — runtime policy §degraded |
| `apikey` | (degraded) | missing model key | keep |
| `otp` | (variant of clarification) | human input required | keep — P0 scenario 1 (auth) |
| `e2e` | (extension) | acceptance run pending | not in v1 specs — defer? |

Naming alignment is a separate task — see T-11.

---

## 4. Spec contracts not yet honoured

### 4.1 Events the FE must listen for (PRD 04 §22-40 + §84-107)

Required by spec; today the FE listens to *nothing* (no transport
layer). Status per builder is from §2.2.

| Spec event | Builder exists? | Builder emitted? | FE handles? |
|---|---|---|---|
| `ready` | yes (`build_typed_ready_envelope`) | yes | no |
| `run_started` | yes | yes | no |
| `plan_ready` | **MISSING** | n/a | no |
| `clarification_needed` | partial (`build_human_input_required_event`) | no | no |
| `recovery_needed` | yes | yes | no |
| `step_validating` | yes | yes | no |
| `step_executing` | yes | yes | no |
| `step_recorded` | yes (`build_operation_executed_event` ~) | no | no |
| `step_failed` | yes | yes | no |
| `step_skipped` | yes | yes | no |
| `code_update` | **MISSING** | n/a | no |
| `replay_started` | (via envelope) | partial | no |
| `replay_result` | (via envelope) | partial | no |
| `run_completed` | yes | yes | no |
| `session_state` | yes | yes | no |
| `capability_gap_recorded` | yes (`build_capability_gap_event`) | no | no |
| `agent_started/progress/result/failed/trace` | **MISSING (5)** | n/a | no |
| `agent_settings` | yes | yes | no |

### 4.2 Commands the FE must send (PRD 04 §42-57 + §88-96)

| Spec command | Backend handler exists? | FE sends today? |
|---|---|---|
| `run_steps / llm_run` | ✅ `server.py:425` | no |
| `confirmed` | ✅ `:597` | no |
| `correction` | ✅ `:597` | no |
| `option_selected` | ✅ `:597` | no |
| `replay_step` | ✅ `replay_one :532` | no |
| `replay_operation` | partial (`replay_one` covers parent only) | no |
| `replay_all` | ✅ `:547` | no |
| `skip_step` | ✅ `:655` | no |
| `stop_run` | ✅ `:624` | no |
| `save_session` | ✅ `:679` | no |
| `load_session` | ✅ `:723` | no |
| `update_locator` | partial (`improve_locator` stub) | no |
| `set_agent_enabled` | **MISSING** | no |
| `run_page_intelligence` | **MISSING** | no |
| `clear_page_intelligence_cache` | **MISSING** | no |
| `get_agent_trace` | **MISSING** | no |
| `set_model_for_agent` | **MISSING** | no |

### 4.3 P0 scenarios coverage

| Scenario | What it exercises | Lifecycle path | Backend ready? |
|---|---|---|---|
| 1 — Full journey + upload (P0 §562-673) | clarification → plan_review → permit → exec → recover → done | needs `clarification_needed` + `plan_ready` + `permission_required` + recovery events | ⚠ events partly missing |
| 2 — Recommendations only (P0 §676-756) | analysis → recommendation_review → plan_ready | needs `recommendation_ready` emission | ⚠ builder unused |
| 3 — Duplicate locator (P0 §759-915) | analysis → locator ambiguity → plan_ready | needs `locator_candidates_ready` or `locator_update_request` | ⚠ builders unused |
| 4 — Plan revision (P0 §918-988) | plan_review → plan_revision → diff → confirmed | needs `plan_diff_proposed` + `plan_diff_validated` + `plan_diff_applied` | ⚠ all unused |
| 5 — Wrong page precondition (P0 §991-1054) | execution → precondition_failed → resolution options | needs `precondition_failed` emission + UI `navigate_to_expected` already wired | ⚠ event unused |
| 6 — Mid-exec failure + recovery (P0 §1057-1131) | operation_failed → recovery_needed → repair → resumed/skip | `operation_failed` + `recovery_needed_structured` unused; `correction` + `skip_step` wired | ⚠ events partly missing |
| 7 — Permission gate (P0 §1134-1180) | risk_classified → permission_required → continue/pause | `permission_required` event unused; `permission_decision` handler ready | ⚠ event missing |
| 8 — Capability gap (P0 §1183-1231) | capability_check → capability_gap_recorded → partial plan | `capability_gap_event` unused | ⚠ event unused |

### 4.4 Codegen / replay / persistence (PRD 05)

| Contract | Backend code path | FE handles? |
|---|---|---|
| Recording model: parent + child ops | `agent.py` step lifecycle | no — FE has flat step cards |
| Workspace storage `<workspace>/autoworkbench-output/` | `server.py:469` | not surfaced to FE |
| Replay one / all + revalidate + recovery | `agent.py:929, 1083` | no |
| Locator update flow (score, validate, history) | not implemented (only stub handlers) | no |
| Codegen Reviewer (optional, deterministic-first) | not implemented (PRD 07) | no |
| L1 run memory | `agent.py` (internal) | partly via `session_state` |
| L2 session memory | `agent.py` (internal) | partly via `session_state` |
| L3 persistent (`.hermes/locators/...`) | **MISSING** | no |
| Save/load UX + naming `.hermes/output/[date]-[name].spec.ts` | `runtime/session_store.py:89/134` (basic) | no |
| Test data: env vars / faker / never hardcoded | **MISSING** | no |
| Auth via `storageState` | **MISSING** | no |
| Generated code structure (LOCATORS section, env var fallbacks) | partial in `agent.py` codegen | no |
| **Expected outcome capture v1** (P0 §498-887) | **MISSING** | no |
| **Replay Precondition Guard v1** (P0 §889-1069) | `server.py:791 change_precondition`, `:861 navigate_to_expected` | no FE buttons |

### 4.5 Multi-model orchestration (PRD 07 + multi-agent §84-107)

* Main Orchestrator (always on).
* Page Intelligence (optional, cheap model).
* Step Runner (always on, deterministic-first).
* Debug Agent (recovery only).
* Codegen Reviewer (optional, deterministic-first).
* Risk Judge (optional, permission-aware).

Agents are *named* in `build_agent_settings_event` payload, but
none of `agent_started`, `agent_progress`, `agent_result`,
`agent_failed`, `agent_trace` are emitted, and the FE Agent Control
Center popover today shows hardcoded `on/off/run` dots.

---

## 5. Gap summary — at a glance

| Layer | Items present | Items missing | Items stubbed |
|---|---|---|---|
| FE outbound (wired buttons / Composer) | 0 | ~60 | — |
| FE inbound (events handled) | 0 | 23 spec'd + 5 multi-agent | — |
| BE inbound handlers | 18 | 5 (multi-agent cmds) | 4 (`improve_locator`, `view_candidates`, `change_locator_scope`, `highlight_locator`) |
| BE outbound builders | 18 emitted | 24 unused, 8 missing entirely | — |
| Codegen / persistence contracts | 4 partial | 9 | — |
| Multi-model agent events | 0 emitted | 5 builders missing | — |
| P0 scenario backend readiness | 0 fully ready | 8 partial | — |

---

## 6. Task list (T-1 … T-25)

Every task is one PR. Each task carries:

* **Scope** — what to touch.
* **Files** — explicit paths.
* **Spec basis** — citations.
* **FE today / BE today** — current state.
* **Gap** — what's missing.
* **How to verify** — manual smoke + automated test where possible.

Pick them off in order unless a dependency note says otherwise.

---

### T-1. Transport read path (FE)

* **Scope.** Re-introduce `frontend/transport.jsx`. Open `ws://<host>/ws`
  on page load. Parse every typed envelope. Translate the events
  listed below into `aw:set` custom-events that the existing
  `useTweaks` listener (already in `frontend/tweaks-panel.jsx`)
  consumes. No buttons wired yet. Pure read path.
* **Files to touch.** `frontend/transport.jsx` (new),
  `frontend/index.html` (add one `<script type="text/babel">` after
  `secondary-tabs.jsx`), `frontend/tweaks-panel.jsx` (reintroduce the
  `aw:set` listener we had at commit `dfa8351`).
* **Spec basis.** PRD 04 §22-40 (every event the FE must handle);
  FE UI spec §2 (FE renders backend state, does not infer).
* **FE today.** Zero network. 17 states only switchable via
  Tweaks panel.
* **BE today.** Already emits `ready, agent_settings,
  endpoint_registry, api_key_required, no_browser, session_state,
  run_started, step_validating, step_executing, step_failed,
  step_skipped, recovery_needed, run_completed, runtime_rejected,
  save_result, load_result, stop_run_result`.
* **Gap.** Frontend doesn't connect.
* **Events to map (subset that already emits):**
  * `ready` → `state: idle` (or `apikey` / `nobrowser` based on payload).
  * `api_key_required` → `state: apikey`.
  * `no_browser` → `state: nobrowser`.
  * `run_started` → `state: exec` (placeholder until plan_ready).
  * `step_executing` → `state: exec`.
  * `step_failed` / `recovery_needed` → `state: recover`.
  * `run_completed` → `state: done`.
  * `runtime_rejected` → toast / schema state if applicable.
  * WS close → `state: offline`, attempt reconnect with exponential
    backoff.
* **Verify.**
  * Boot `python server.py` in stub mode, open browser, confirm
    `state` flips to `apikey` automatically when no `OPENAI_API_KEY`.
  * Headless Playwright test: connect → expect at least one `state`
    transition driven by an inbound event.
  * Disconnect server, confirm UI shows `offline` card within 5s.

### T-2. Composer Send → `llm_run`

* **Scope.** Wire the Composer (`frontend/llm-tab.jsx:723-774`) to
  call `window.AW.send({ type: "llm_run", steps: [...] })` on Enter
  (not Shift+Enter) and on Send-button click. Clear the textarea on
  send. Disable Send while a run is active.
* **Files.** `frontend/llm-tab.jsx` Composer + LlmThread (read
  active state to gate the button).
* **Spec basis.** PRD 04 §46 (`run_steps / llm_run`); FE UI spec
  §5.2 (chat input); P0 scenario 1 §562 (entry point).
* **Gap.** Composer is UI-only; `onSend` (`llm-tab.jsx:727-736`)
  fakes a sending → sent toggle and never posts.
* **Verify.** Type a prompt, hit Enter, confirm `[WS_RECV]
  type=run_steps` in server log. Confirm state moves from `idle` to
  `planning` (or `exec`) as backend emits its first event. Headless
  Playwright: fill, Enter, assert outgoing WS message.

### T-3. CardPlanReady Confirm & run

* **Scope.** Wire the three buttons in `CardPlanReady`
  (`frontend/llm-tab.jsx:188-282`): Confirm & run →
  `{ type: "confirmed", run_id, plan_id }`; Edit plan → switch to
  `correction` flow with the plan text editable; Run first 3 →
  `{ type: "correction", run_id, plan_id, slice: { first_n: 3 } }`
  (new field — see T-23).
* **Files.** `frontend/llm-tab.jsx` CardPlanReady; `agent.py`
  correction handler if slice is added.
* **Spec basis.** PRD 04 §47 (`confirmed`, `correction`); P0
  scenario 1 §606; P0 scenario 4 §922-987 (plan revision).
* **BE today.** `confirmed`, `correction` handlers wired (server.py
  :597); no `plan_ready` event yet emitted (depends on T-15).
* **Gap.** FE buttons unwired. `Run first 3 only` needs a spec'd
  slice payload — flagged AMBIGUOUS in FE UI spec, OPEN in PRD.
* **Verify.** Send a plan request, wait for `plan_ready`, click
  Confirm, confirm server transitions to `exec`. For Edit plan: type
  correction, send, confirm `correction` arrives. For slice: skip
  until T-23.

### T-4. CardExecution Stop run + Pause (Pause = new cmd)

* **Scope.** Wire `CardExecution` (`frontend/llm-tab.jsx:313-374`)
  buttons. Stop run → `{ type: "stop_run", run_id }`. Pause: needs
  new backend command (`pause` / `resume`).
* **Files.** `frontend/llm-tab.jsx` CardExecution; `server.py` to add
  `pause` / `resume` handlers; `agent.py` to honour pause flag in
  step loop.
* **Spec basis.** PRD 04 §54 (`stop_run`); FE UI spec §5.7 / §10.4
  ("Pause for manual login"); P0 scenario 6 §1057-1131.
* **Gap.** `pause` and `resume` are not in the existing 23 WS types.
* **Verify.** Start a run, click Stop → confirm `stop_run_result`
  envelope on FE. Click Pause → expect a new
  `run_paused_result` envelope. Resume → run continues from the next
  pending step.

### T-5. CardCompleted Replay all + Save as suite + Open code + Download trace

* **Scope.** Wire the four buttons of `CardCompleted`
  (`frontend/llm-tab.jsx:503-536`).
  * Replay all → `replay_all`.
  * Save as suite → open save modal, then `save_session`.
  * Open code → switch FE tab to `code`, no backend call needed
    (preview is already on `session_state.code_preview`).
  * Download trace → **new endpoint required**; either a new WS
    command `download_trace` returning a workspace path, or a REST
    `GET /api/trace/<run_id>.zip`.
* **Files.** `frontend/llm-tab.jsx` CardCompleted; `server.py` add
  `download_trace` handler or REST route; `agent.py` to expose a
  trace-bundler.
* **Spec basis.** PRD 04 §50-55; FE UI spec §5.10 (completed card);
  P0 scenario 1 §660 ("user can replay").
* **Verify.** After a successful run, click Replay all → `replay_all`
  message sent → server emits replay_started / replay_result per
  step. Click Save → confirm `save_result` event + file on disk under
  `.hermes/output/`. Click Open code → tab switches. Click Download
  trace → file lands.

### T-6. CardOffline Reconnect / View log / Switch endpoint

* **Scope.** Reconnect = client-side WS reconnect (already in T-1).
  View log = show the local browser-side log buffer in a modal (no
  backend). Switch endpoint = `{ type: "switch_endpoint", endpoint_id }`.
* **Files.** `frontend/llm-tab.jsx` CardOffline; `frontend/transport.jsx`
  log buffer; `server.py` already has the handler (`:1078`, stub) and
  emits `endpoint_registry` on connect.
* **Spec basis.** FE UI spec §10.6; PRD 04 §"endpoint_registry".
* **Gap.** `switch_endpoint` only supports the active id today
  (`server.py:1092`); needs a real registry source.
* **Verify.** Kill server, confirm FE shows offline card. Click
  Reconnect, restart server, confirm transport reattaches. Click
  Switch endpoint with a non-existent id, confirm `ENDPOINT_UNKNOWN`
  rejection.

### T-7. CardSchemaError Ask LLM to repair / Edit manually / Open raw

* **Scope.** Backend must emit `schema_error` when an LLM response
  fails validation (today the builder exists at
  `runtime/event_contracts.py:1851` but no agent path calls it).
  Then FE wires Ask LLM to repair → `correction` with a `repair:
  schema` flag; Edit plan manually → switch UI to correction mode;
  Open raw response → show the cached last raw payload locally.
* **Files.** `agent.py` / `llm/orchestrator.py` to emit the event;
  `frontend/llm-tab.jsx` CardSchemaError.
* **Spec basis.** FE UI spec §10.5 (LLM schema failure UI).
* **Verify.** Inject a malformed LLM response via a stub model
  adapter, confirm `schema_error` arrives, confirm FE card renders
  with the three buttons and Ask-LLM-to-repair sends a correction.

### T-8. CardClarification + CardRecommendation

* **Scope.** Two cards, one task.
  1. Emit `clarification_needed` (today only
     `build_human_input_required_event` exists; either rename or
     also add a dedicated builder) when the planner needs an answer.
  2. Emit `recommendation_ready` (builder exists,
     `event_contracts.py:1784`, unused) when the recommender returns.
  3. Wire `CardClarification` Submit answer → `option_selected` or
     `correction`; Let LLM decide → `correction` with `auto:true`.
  4. Wire `CardRecommendation` Use selected → `option_selected` with
     selected set; Add my own assertion → `correction`; Group
     differently → `correction`.
* **Files.** `agent.py` / `llm/orchestrator.py` emit points;
  `frontend/llm-tab.jsx` CardClarification + CardRecommendation.
* **Spec basis.** FE UI spec §5.6, §5.4; PRD 04 §28, §31;
  P0 scenario 1 (clarification) + P0 scenario 2 (recommendations).
* **Verify.** Send a deliberately ambiguous prompt; confirm
  `clarification_needed` arrives + card renders. Answer it; confirm
  flow resumes. For recommendations: send a "validate this page"
  prompt; confirm `recommendation_ready` + card. Select assertions;
  confirm `option_selected` carries the chosen set.

### T-9. CardPermission Allow once / Allow run / Deny

* **Scope.** Emit `permission_required` from the agent before any
  high-risk operation. Wire the three buttons →
  `permission_decision`. Allow once → `{ scope: "once" }`; Allow run
  → `{ scope: "run" }`; Deny → `{ scope: "deny" }`.
* **Files.** `agent.py` / `runtime/permission_policy.py` emit point;
  `frontend/llm-tab.jsx` CardPermission.
* **Spec basis.** FE UI spec §5.7; PRD 04 §"permission_required";
  P0 scenario 7 §1134-1180.
* **Verify.** Drive a flow that hits a destructive action (e.g.,
  form submit). Confirm `permission_required` envelope. Click Allow
  once → permission_decision carries the scope. Click Deny → run
  pauses. Audit log records the decision.

### T-10. CardLocator + de-stub four locator handlers

* **Scope.** Real locator-flow integration.
  1. Emit `locator_update_request` (`event_contracts.py:1106`) or
     `locator_candidates_ready` (`:2044`) when count > 1.
  2. De-stub `improve_locator` (`server.py:946`),
     `view_candidates` (alias), `change_locator_scope` (`:984`),
     `highlight_locator` (`:1039`) — implement them against the
     locator agent.
  3. Wire `CardLocatorAmbiguity` (`llm-tab.jsx:377-458`) Select →
     `option_selected`; Highlight → `highlight_locator`; Ask LLM →
     `improve_locator`; Change scope → `change_locator_scope`;
     Stop → `stop_run`; Use candidate N → `option_selected`.
* **Files.** `agent.py` / `locator.py` emit + handler logic;
  `frontend/llm-tab.jsx` CardLocatorAmbiguity; `server.py` four
  handlers.
* **Spec basis.** FE UI spec §6.6; PRD 05 §99-120 (locator update
  flow); P0 scenario 3 §759-915.
* **Verify.** Drive scenario 3 (duplicate "Get started" buttons).
  Confirm candidate event. Click Highlight → backend overlay (when
  the browser is real). Click Select → `option_selected` lands and
  the run proceeds. De-stubbed handlers respond with real applied
  events, not `applied: false`.

### T-11. CardRecovery wiring + retry_as_is command

* **Scope.** Wire `CardRecovery` (`llm-tab.jsx:461-500`). Apply LLM
  repair → `correction` with `repair: llm`. Retry as-is → **new
  command** `retry_as_is` (or `correction` with `retry:true`).
  Choose another locator → switch to locator-update flow. Stop run →
  `stop_run`.
* **Files.** `agent.py` to honour the retry payload; `server.py` add
  handler if new cmd; `frontend/llm-tab.jsx` CardRecovery.
* **Spec basis.** FE UI spec §5.8; PRD 04 §"recovery_needed";
  P0 scenario 6 §1057-1131.
* **Verify.** Inject a failure (e.g., locator timeout) → recovery
  card → Apply LLM repair → confirm `correction` sent →
  `step_recorded`/repair event emitted.

### T-12. CardNoBrowser Launch chromium / Attach existing / Keep as draft

* **Scope.** Three new commands.
  * `launch_chromium` → `browser.launch_browser()` called over the
    WS.
  * `attach_existing_tab` → user-supplied URL; new flow.
  * `keep_plan_as_draft` → state moves to `idle` without browser.
* **Files.** `server.py` three handlers; `browser.py` (no change for
  launch); `frontend/llm-tab.jsx` CardNoBrowser.
* **Spec basis.** FE UI spec §"CardNoBrowser"; PRD 03 §
  "browser_ready"; PRD 04 §"no_browser".
* **Verify.** Boot in `STUB_MODE=0` with no browser installed →
  `no_browser` event → card renders. Click Launch chromium → expect
  `browser_ready` event (builder exists at `:1347`).

### T-13. CardApiKey Add key / Use workspace key

* **Scope.** Add a new command (`add_api_key`) that writes to
  `<workspace>/.env` (or in-process env). Treat as sensitive — never
  echoed in events.
* **Files.** `server.py` `add_api_key` handler; `runtime/redaction_policy.py`
  to ensure key never leaves the server.
* **Spec basis.** FE UI spec §"CardApiKey"; runtime policy §13.
* **Verify.** Boot without an `OPENAI_API_KEY` → card renders.
  Submit key → confirm `api_key_required` no longer fires on next
  WS connect.

### T-14. CardOtp + CardE2E

* **Scope.** OTP card: Submit code → `correction`; Skip step →
  `skip_step`; Pause run → T-4 `pause`.
  E2E card: Trigger E2E → new `trigger_e2e` command (backend pipeline
  may not exist in v1 — flag as Phase 5 per PRD 06).
* **Files.** `frontend/llm-tab.jsx` CardOtp + CardE2E;
  `server.py` if E2E is added; defer if E2E is out of scope.
* **Spec basis.** P0 scenario 1 §580 (auth/OTP); FE UI spec
  §"CardOtp", §"CardE2E"; PRD 06 phase 5.
* **Verify.** Drive a flow that hits an OTP prompt → card → submit
  code → run resumes.

### T-15. Backend emit `plan_ready` + missing builders

* **Scope.** Add `build_plan_ready_event` (PRD 04 §27 wants
  `{run_id, plan, steps, summary}`). Add `build_code_update_event`
  (§35 wants `{step_id?, operation_id?, lines, full_spec_preview,
  diagnostics}`). Decide whether `clarification_needed` ≡
  `human_input_required` or add a dedicated builder.
* **Files.** `runtime/event_contracts.py` add three builders;
  `agent.py` / `llm/orchestrator.py` emit at the right phases.
* **Spec basis.** PRD 04 §27, §28, §35.
* **Verify.** Snapshot test: run the golden path scenario, capture
  every event sent over WS, assert the three new event types appear
  in the expected order: `clarification_needed` →
  `plan_ready` → `code_update`.

### T-16. Mode-name alignment (FE)

* **Scope.** Rename FE state keys to match the FE PRD canonical
  names where they differ: `clarify → clarification`, `plan →
  plan_review`, `exec → executing`, `recover → recovery`, `done →
  completed`. Keep the degraded states (`offline, schema, nobrowser,
  apikey`) and the variants (`planning, recommend, diff, permit,
  locator, otp, e2e`). Update `STATE_META` keys + every consumer.
* **Files.** `frontend/app.jsx` STATE_META + all `t.state === "x"`
  branches; `frontend/llm-tab.jsx` LlmThread state selector;
  `frontend/secondary-tabs.jsx`.
* **Spec basis.** PRD 03 §"mode behavior" (lines 76-83).
* **Verify.** Re-run the headless 17-state cycler from the previous
  test pass — every state must still render correctly under its new
  key. Pixel-diff against the previous baseline must remain 0.

### T-17. Tab counts + agent dots + token info from events

* **Scope.** Replace the three mock blocks at `frontend/app.jsx
  :78-93` with values derived from `session_state` (counts),
  `agent_settings` (dots), and a new `token_report` event (token
  info; builder exists at `event_contracts.py:2123`, unused).
* **Files.** `frontend/app.jsx` consumers + a small
  `useSessionState` selector pattern; `agent.py` emit
  `token_report` after each LLM call.
* **Spec basis.** PRD 04 §"session_state"; multi-agent §"agent_settings";
  PRD 07 §"telemetry" (token costs).
* **Verify.** Headless test: send a prompt, watch the tab badge
  counts update from 0 → real numbers; the token counter rises;
  agent dots reflect `agent_settings` updates.

### T-18. Steps tab from `session_state.steps` + step-row commands

* **Scope.** Replace the 5 hardcoded step rows at
  `frontend/secondary-tabs.jsx:312-423` with `session_state.steps`.
  Wire the per-row "More" menu to typed commands:
  Edit intent → `correction` (T-3); Re-pick locator → `arm_picker`
  (T-15 picker); Change precondition → `change_precondition` (already
  in server.py:791); Navigate to expected → `navigate_to_expected`
  (server.py:861); Skip → `skip_step`.
* **Files.** `frontend/secondary-tabs.jsx` step list + More menu;
  no backend changes (handlers exist).
* **Spec basis.** PRD 05 §99-120 + §889-1069 (Replay Precondition
  Guard v1); FE UI spec §6.
* **Verify.** Drive scenario 5 (wrong page) → confirm
  Navigate-to-expected button fires the right command.

### T-19. Recorded tab live + Code tab live

* **Scope.** Replace recorded-step mocks at `secondary-tabs.jsx:477`
  with `session_state.recorded_steps`. Replace code mock with
  `session_state.code_preview`. Wire the Code tab Copy → local
  clipboard; Export → `export_code` (`server.py:445`); Regenerate →
  new `code_regenerate` command (T-23).
* **Files.** `frontend/secondary-tabs.jsx` Recorded + Code.
* **Spec basis.** PRD 05 §44-72 (workspace), §122-141 (codegen),
  §426-458 (generated code structure).
* **Verify.** Run scenario 1 → confirm both tabs populate from the
  same `session_state` payload the LLM tab uses. Click Export →
  inspect `<workspace>/autoworkbench-output/generated.spec.ts`.

### T-20. Trace tab from event stream

* **Scope.** Replace the 26 hardcoded rows at
  `secondary-tabs.jsx:745-770` with a live event log derived from
  the same WS stream `transport.jsx` consumes. Filters (8 of them in
  FE UI spec §9) drive client-side categorisation.
* **Files.** `frontend/secondary-tabs.jsx` TraceTab + a buffer in
  `transport.jsx`.
* **Spec basis.** FE UI spec §9 (timeline + filters).
* **Verify.** Headless test: capture WS frames for 30s, count rows
  in Trace tab = number of frames. Each filter button hides/shows
  the right subset.

### T-21. Picker round-trip

* **Scope.** Wire `frontend/secondary-tabs.jsx:45, 449` "Pick
  element" toggle to `arm_picker(step_id)`. Backend already injects
  a click listener (`browser.py:804`). Listener posts back the
  selection via `picker_send` (server.py:415). Render that into
  ManualBuilder.
* **Files.** `frontend/secondary-tabs.jsx` ManualBuilder + step row
  "Re-pick"; `browser.py` listener may need to emit a typed event
  (today it's an ad-hoc dict).
* **Spec basis.** FE UI spec §6.6 (element picker); PRD 03 §"Element
  picker technical flow".
* **Verify.** Open a real page (not stub mode). Click Pick element.
  Click any DOM element. Confirm the picked descriptor (name, role,
  text, candidates) flows into the form.

### T-22. ManualBuilder submission → `run_steps`

* **Scope.** Wire `secondary-tabs.jsx:6` ManualBuilder form. On
  "Add step" send `{ type: "run_steps", steps: [{ kind: "manual",
  action, assertion, expected, picked }] }`. Backend can wrap manual
  steps in the same Step Runner pipeline (PRD 06 phase 4).
* **Files.** `frontend/secondary-tabs.jsx` ManualBuilder; `agent.py`
  to accept `kind: "manual"`.
* **Spec basis.** PRD 06 phase 4 ("Manual Mode using same runtime");
  PRD 01 §scenarios 3-4.
* **Verify.** Pick an element, choose action=click, assertion=text,
  expected="Get started" → Add step. Confirm a new step row appears
  driven by `session_state.steps`. Click Run all → it executes.

### T-23. New commands batch

* **Scope.** Add the commands accumulated above:
  * `pause`, `resume` (T-4)
  * `retry_as_is` (T-11)
  * `launch_chromium`, `attach_existing_tab`, `keep_plan_as_draft`
    (T-12)
  * `add_api_key`, `use_workspace_key` (T-13)
  * `trigger_e2e`, `notify_on_e2e` (T-14)
  * `download_trace` (T-5)
  * `code_regenerate` (T-19)
  * Optionally: `set_agent_enabled`, `run_page_intelligence`,
    `clear_page_intelligence_cache`, `get_agent_trace`,
    `set_model_for_agent` (multi-agent, PRD 04 §88-96).
* **Files.** `server.py` handlers; `runtime/event_contracts.py`
  SUPPORTED_FRONTEND_COMMAND_TYPES list; new typed envelopes.
* **Spec basis.** Aggregated; per-cmd citations above.
* **Verify.** Schema test: every new command goes through
  `normalize_frontend_command` and is in the supported list. WS
  fuzz: send `{type: "<new_cmd>"}` with required fields, confirm
  it is *not* rejected as `COMMAND_NOT_SUPPORTED`.

### T-24. Multi-agent emission sweep (PRD 07)

* **Scope.** Wire `agent_started, agent_progress, agent_result,
  agent_failed, agent_trace` events from the orchestrator and the
  optional agents (Page Intelligence, Locator, Debug, Codegen
  Reviewer, Risk Judge). Replace hardcoded
  `agentsSummary` dots with live derived dots.
* **Files.** `agent.py`, `llm/orchestrator.py` + sub-agents in
  `llm/`; `runtime/event_contracts.py` add five builders.
* **Spec basis.** PRD 04 §84-107; PRD 07 entire.
* **Verify.** Drive any scenario → assert at least one
  `agent_started` for Main Orchestrator + one `agent_result` per
  agent that ran. Agent Control Center popover reflects live
  on/off/run states.

### T-25. Backend emit-sweep for the remaining 16 unused builders

* **Scope.** For each builder in §2.2 that's still unused after T-1
  … T-24, decide: emit it from the agent at the right phase, or
  delete it. Don't ship unused contract surface.
* **Files.** `agent.py` emit points; possibly delete unused builders
  in `runtime/event_contracts.py` if the corresponding behavior is
  v2+ and out of scope.
* **Spec basis.** PRD 04 entire; "no silent drops" runtime policy
  §16.
* **Verify.** Schema test: every builder has at least one emit site
  (or is removed). PR description must justify each deletion.

---

## 7. Verification matrix

For every task above we should add at least one of:

* **Headless Playwright test** (run from `tests/`) — spawns the
  server in stub mode, drives the FE, and asserts WS frames /
  rendered DOM. Tag with the task id (e.g., `test_t1_transport.py`).
* **WS schema test** — feed a stub WS frame and assert the FE state
  transition.
* **Pixel-diff regression test** — keep the byte-identity guarantee
  with `AutoWorkbench.html`. Any change that diverges from the
  canonical screenshot for a state we didn't intentionally redesign
  fails the test.
* **Manual smoke** — explicit reproduction steps in the PR description.

Until we have those, the existing test corpus under `tests/` and
`tests-dom/` (deleted in commit `3eaae8c`) is not trusted — see
the rationale in commit `a3267a3` and §1 of this doc.

---

## 8. Build phasing vs. PRD 06

The PRD 06 build roadmap defines five phases; mapping our tasks:

| PRD 06 phase | Scope | Tasks |
|---|---|---|
| Phase 1 — Core runtime + FE/BE contract | browser, WS events, Step Runner, docked layout | T-1, T-15 (events), T-16 (mode names) |
| Phase 2 — Complete LLM Mode MVP | single/multi-action, plan correction, recovery, capability gaps, code_update | T-2 … T-11, T-15, T-25 (partial) |
| Phase 3 — Recording / save / replay / repair / version | save, load, replay, repair, version | T-5, T-18, T-19, T-20 |
| Phase 4 — Manual Mode using same runtime | pick / action / assert, same Step Runner | T-21, T-22 |
| Phase 5 — Advanced actions + persistence + polish | upload/download/popup/iframe, page maps, persistent locator library, Shadow DOM, polish | T-12, T-13, T-14, deferred items |
| Multi-model track | telemetry, Page Intelligence nano, Agent Control Center, Debug, Codegen Reviewer | T-17, T-24 |

---

## 9. Acceptance tests pulled from the specs

Listing the spec-mandated tests so we have a verification anchor per
PR.

* PRD 06 §166-180 — 12 MVP tests:
  1. button → code line
  2. heading `&nbsp;` assertion preserves normalised text
  3. section → parent + children
  4. wrong order → correction
  5. failure → recovery
  6. replay → repair
  7. locator update
  8. capability gap
  9. WebSocket reconnect
  10. docked UI (no occlusion, resize live)
  11. Page Intelligence disabled toggle
  12. div/span page → candidates
* P0 §662-672, §747-755, §907-914, §979-987, §1046-1053,
  §1122-1130, §1172-1179, §1223-1230 — eight scenario acceptance
  blocks.
* PRD 02 §345-359 — 10 LLM acceptance items
  (correction: click-only → assert+click; reorder preserves all ops;
  ambiguous → asks clarification; no silent drop; no silent split/merge;
  reuses validated locators; avoids full DOM; bounded retry; UI only
  shows plan after validation).
* PRD 04 §76-82 — four FE/BE invariants (render from events only,
  replay from event history, reconnect restores UI, every UI action
  is one explicit command).
* PRD 04 §428-432 — capability gap acceptance (no silent ignore, no
  fake success, never stores secrets).

These are the "test names" each task should claim coverage of.

---

## 10. Open spec ambiguities to resolve before implementation

Pulled from the FE UI spec ↔ FE PRD ↔ runtime policy comparison.

1. **Plan diff in Steps tab vs. LLM tab.** FE UI spec §5.3 says
   Plan Mode lives in LLM tab; §6.8 implies Steps tab can also send
   pending steps. Decide whether plan editing happens in one place
   or both.
2. **Slash commands.** FE UI spec §5.5 says they "help
   classification only" and "do not bypass" validation, but doesn't
   say what backend cmd they map to (`correction` with a hint? a new
   `intent_hint` envelope?). Open.
3. **Save / Load placement.** FE UI spec §4.3 (global footer) vs.
   §8.2 (Code tab Export). Decide.
4. **Agent Control Center.** PRD 04 §86-107 + multi-agent track
   require it. FE UI spec does not describe it. Decide whether it's
   a v2.3-only PRD addition and what panel it lives in.
5. **WebSocket reconnect semantics.** FE UI spec §10.6 wants
   "preserved / lost" badges; PRD 04 has no `run_preserved` /
   `run_lost` event yet. Decide.
6. **Postcondition vs. expected outcome.** FE UI spec §6.1 lists
   both as step-card fields; PRD 05 §498-887 defines "Expected
   Outcome Capture v1". Decide whether they are synonymous or
   separate.
7. **`clarification_needed` vs. `human_input_required`.** Two names
   for the same payload? Or different?
8. **Plan-slice command for "Run first 3 only"** (T-3) — needs a
   spec'd payload shape.
9. **`retry_as_is` vs. `correction { retry: true }`** (T-11).
10. **E2E pipeline** (T-14, scenario covered by PRD 06 phase 5) —
    confirm in scope before building.

Each is a one-line decision the product owner can make. The tasks
above name an assumption per ambiguity but flag the choice.

---

## 11. Provenance

This document supersedes the earlier
`docs/superpowers/specs/2026-05-15-frontend-backend-integration-map.md`
(commit `a3267a3`). The earlier rebuild spec
(`2026-05-15-frontend-rebuild-from-v4-mock-design.md`, commit
`dfa8351`) remains valid for the Phase-1 rebuild it describes.
Frontend baseline for all work below: commit `2789936`.
