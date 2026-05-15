# Frontend ⇄ Backend integration map

Date: 2026-05-15
Branch: `s7/clusters-6-11-complete-llm-mode`
Frontend baseline: commit `2789936` — `frontend/` is byte-identical to the
`AutoWorkbench.html` design bundle. Zero outbound network traffic from the
page today; backend boots fine but is not consulted.

This document is the **source of truth for the next phase**. We will not
ship integration work in one go — each section below is a discrete task to
be picked off the list. No fixes are proposed here; this is inventory +
gap map only.

---

## 1. What the frontend is today

7 jsx files transpiled in the browser by Babel-standalone. State lives in
`useTweaks(...)` (tweaks-panel.jsx:162) — a single value bag persisted via
`__edit_mode_set_keys` postMessage to a parent harness, plus a same-window
`tweakchange` event for in-page listeners. There is no `fetch`, no
`WebSocket`, no `XMLHttpRequest`, no `EventSource` anywhere in the seven
jsx files.

### 1.1 Surfaces the user can touch

* **Mode switch** (chrome.jsx:60, 63) — `LLM` ⇄ `Manual` (writes `mode`)
* **Tabs** (chrome.jsx:134-156) — `llm` / `steps` / `rec` / `code` /
  `trace` with mock badge counts `{steps:5, rec:4, code:1, trace:25}`
  (app.jsx:80, hardcoded)
* **Agents button** (chrome.jsx:66) — toggles `agentsOpen`; popover lists
  Main Orchestrator / Page Intelligence / Step Runner / Debug Agent /
  Risk Judge with hardcoded `on|off|run` dots (app.jsx:82-93)
* **Dock menu** (chrome.jsx:101) — right / left / top / float
* **Collapse toggle** (chrome.jsx:111, 120)
* **Settings / Tweaks gear** (chrome.jsx:122-126) — `postMessage __activate_edit_mode`
* **Composer** (llm-tab.jsx:723) — textarea, three context chips
  (`/pricing` / `2 selected` / `users.csv`, all hardcoded), `Add` button
  (no onClick), three icon buttons (no onClick), Send button. Submit
  cycles `sending → sent` UI states locally; **never posts**.
* **15 decision cards** in llm-tab.jsx (lines 52-700) — one per lifecycle
  state. Roughly **60 onClick handlers are missing entirely** — every
  "Confirm & run" / "Allow once" / "Pause" / "Replay all" / "Reconnect
  now" / "Add key" / "Submit code" / etc. is dead.
* **Steps tab** (secondary-tabs.jsx:6, 256) — `ManualBuilder` form
  (action select + assertion select + expected input, all local state),
  filter search, "Add step" appends to local array only, "Pick element"
  toggles local picking flag only.
* **Recorded tab** (secondary-tabs.jsx:477) — 4 hardcoded recorded step
  rows with `More` menu (all menu items no-op).
* **Code tab** (secondary-tabs.jsx) — hardcoded Playwright snippet,
  `Copy` / `More` menu (all no-op).
* **Trace tab** (secondary-tabs.jsx:745) — 26 hardcoded event rows; scope
  + filter + reset are local state only.

### 1.2 State machine

`STATE_META` (app.jsx:19-54) defines 17 lifecycle states:

`idle, planning, clarify, recommend, plan, diff, permit, exec, locator,
recover, done, offline, schema, nobrowser, apikey, otp, e2e`

Each state pins six fields used by chrome / now-strip / footer:
`phase, event, next, conn, busy, blocker, now.{kind, state, task,
refLabel, primaryLabel}`.

Today, the only way to enter a state is through the dev Tweaks panel
(activated via `__activate_edit_mode`). There is no event-driven path.

### 1.3 Hardcoded mock data inventory

| Where | What | Replace with |
|---|---|---|
| app.jsx:78 | `runId = "run_a91b"` (or `"—"` when idle) | live `run_id` from `run_started` |
| app.jsx:79 | `tokenInfo = { tok: "8.4k", cost: "0.12" }` | `token_report` event |
| app.jsx:80 | `counts = { steps:5, rec:4, code:1, trace:25 }` | derive from `session_state.steps / recorded_steps / code_preview / trace` |
| app.jsx:82-93 | `agentsSummary` 5-dot array | derive from `agent_settings` |
| llm-tab.jsx:104-110 | 6 hardcoded assertion candidates | `recommendation_ready` event |
| llm-tab.jsx:380-393 | 3 hardcoded locator candidates | `locator_update_request` event |
| secondary-tabs.jsx:9-18 | `ManualBuilder` `picked` mock | `arm_picker` round-trip |
| secondary-tabs.jsx:312-423 | 5 hardcoded plan step rows | `session_state.steps` |
| secondary-tabs.jsx:745-770 | 26 hardcoded trace events | derive from agent event stream |
| llm-tab.jsx:744 | Composer chips `/pricing`, `2 selected`, `users.csv` | live page url + selection + attachment list |

---

## 2. What the backend has today

### 2.1 WS inbound — frontend → server (23 message types)

Implemented & validated (`server.py`):

| msg_type | line | required fields | effect |
|---|---|---|---|
| `run_steps` / `llm_run` | 425 | `steps` | starts `agent.run(steps)` |
| `export_code` | 445 | `code`, `path?` | writes spec into `AUTOWORKBENCH_WORKSPACE` |
| `save_snapshot` | 505 | — | `agent._build_spec_snapshot()` |
| `replay_one` | 532 | `step_id` | `agent.replay_one(step_id)` |
| `replay_all` | 547 | `stop_on_error?` | `agent.replay_all(...)` |
| `confirmed` | 597 | normalised | queued to `control_queue` |
| `correction` | 597 | normalised | queued to `control_queue` |
| `option_selected` | 597 | normalised | queued to `control_queue` |
| `stop_run` | 624 | normalised | cancels `run_task` + emits `stop_run_result` |
| `skip_step` | 655 | `step_id` | queued to `control_queue` |
| `save_session` | 679 | normalised | `save_session_to_file` + `save_result` event |
| `load_session` | 723 | `path` | `load_session_from_file` + `load_result` event |
| `permission_decision` | 767 | normalised | queued to `control_queue` |
| `change_precondition` | 791 | `step_id, run_id, expected_url \| new_precondition` | routed to correction pipeline |
| `navigate_to_expected` | 861 | `step_id, run_id` | ack + nav intent queued |
| `arm_picker` | 930 | `step_id` | `arm_picker(step_id, picker_send)` |
| `reset` | 939 | — | `agent.llm.reset()` |

Stubs (server.py acks only, agent never acts on them):

| msg_type | line | event sent back |
|---|---|---|
| `improve_locator` | 946 | `improve_locator_acknowledged {status: "queued"}` |
| `view_candidates` | 946 | alias of `improve_locator` |
| `change_locator_scope` | 984 | `change_locator_scope_acknowledged {status: "queued"}` |
| `highlight_locator` | 1039 | `locator_highlight_acknowledged {applied: false, status: "queued"}` |
| `switch_endpoint` | 1078 | rejects unknown ids; for the active id replies `{status: "already_active"}` |

Unknown message types fall through to `COMMAND_NOT_SUPPORTED`
(server.py:1130).

### 2.2 WS outbound — server → frontend (38 builders defined)

**Used today (≥1 emission site):**

`build_backend_event_envelope` (generic wrapper, 57 uses across the runtime),
`build_runtime_rejection_payload`, `build_run_completed_payload`,
`build_recovery_needed_payload`, `build_session_state_event`,
`build_run_started_payload`, `build_step_validating_payload`,
`build_step_executing_payload`, `build_step_failed_payload`,
`build_step_skipped_payload`, `build_no_browser_event`,
`build_api_key_required_event`, `build_endpoint_registry_event`,
`build_agent_settings_event`, `build_typed_ready_envelope`,
`build_stop_run_result_event`, `build_save_result_event`,
`build_load_result_event`.

**Defined but never emitted (`runtime/event_contracts.py`, lines listed):**

`build_permission_required_payload` (586), `build_human_input_required_event`
(744), `build_e2e_pending_event` (797), `build_execution_started_event`
(869), `build_operation_executed_event` (919), `build_operation_failed_event`
(977), `build_precondition_failed_event` (1045),
`build_locator_update_request_event` (1106),
`build_locator_update_applied_event` (1159), `build_browser_ready_event`
(1347), `build_page_analysis_started_event` (1695),
`build_page_summary_ready_event` (1725), `build_page_analysis_failed_event`
(1754), `build_recommendation_ready_event` (1784),
`build_capability_gap_event` (1816), `build_schema_error_event` (1851),
`build_provider_error_event` (1889), `build_malformed_output_error_event`
(1923), `build_plan_diff_proposed_event` (1955),
`build_plan_diff_validated_event` (1986), `build_plan_diff_applied_event`
(2016), `build_locator_candidates_ready_event` (2044),
`build_recovery_needed_structured_event` (2076), `build_token_report_event`
(2123).

24 builders are dead code waiting for the agent to start calling them.
Each one corresponds to a card the frontend already renders.

### 2.3 Agent / capability surface

* `agent.py:1471 AgentLoop.run(steps)` — async planning/execution loop.
* `agent.py:929 .replay_one(step_id)`
* `agent.py:1083 .replay_all(stop_on_error=True)`
* `agent.py:1221 ._build_spec_snapshot()`
* `agent.py:1267 ._build_session_state_payload()`
* `agent.py:484/496` — current phase / run-id getters.
* `agent.py:154 .llm: LLMClient`, `.176 .phase_tracker`.

* `browser.py:193 launch_browser()`
* `browser.py:187 get_page()`
* `browser.py:239 inject_panel(page)`
* `browser.py:804 arm_picker(step_id, send)`
* `locator.py:16 find_best_locator(...)`

* `llm.py:23 LLMClient.chat(msg)` / `.35 .reset()`
* `llm/orchestrator.py` — higher-level plan / repair / recovery flows
  (not directly called from the WS handler today).

* `runtime/session_store.py:23 SessionSpec`
* `runtime/session_store.py:89 save_session_to_file`
* `runtime/session_store.py:134 load_session_from_file`

### 2.4 Boot-time degraded modes (server.py:223 `_BOOT_STATE`)

`api_key_ok`, `api_key_reason`, `browser_ok`, `browser_error`, `stub_mode`.
On WS connect:
* `api_key_ok=False` → `api_key_required` event
* `browser_ok=False and not stub_mode` → `no_browser` event

---

## 3. Gap map — state by state

For every frontend lifecycle state, list (a) what must arrive over the
wire to enter it, (b) what buttons must wire back out, (c) what backend
work is needed.

### 3.1 `idle`

* Enter: WS open → `ready{backend_ready, browser_ready}` already emitted.
* Buttons: Composer Send.
* Backend ready: `run_steps` / `llm_run` ✅.
* Gap: Composer onSubmit not implemented. No transport layer yet.

### 3.2 `planning`

* Enter event needed: `page_analysis_started` builder (1695) — never emitted.
* Buttons: none (display only).
* Backend gap: agent must call the builder when it starts a DOM scan.

### 3.3 `clarify`

* Enter event needed: there is **no `build_clarification_requested_*`
  builder**. Closest existing: `build_human_input_required_event` (744,
  unused). Either repurpose or add a new builder.
* Buttons: Submit answer, Let LLM decide.
* Backend cmd ready: `option_selected` ✅ (via `control_queue`).
* Gap: agent must emit the event; FE buttons unwired.

### 3.4 `recommend`

* Enter event needed: `recommendation_ready` (1784) — defined, unused.
* Buttons: Use selected, Add my own assertion, Group differently.
* Backend cmd ready: `option_selected` ✅; `Add my own` may need a
  `correction` payload schema.
* Gap: agent emit + FE wiring.

### 3.5 `plan`

* Enter event needed: a `plan_ready` envelope — closest builder
  `build_run_started_payload` plus a new event. None of the existing
  `plan_diff_*` builders cover "first plan ready" cleanly.
* Buttons: Confirm & run, Edit plan, Run first 3 only.
* Backend cmd ready: `confirmed` ✅, `correction` ✅. "Run first 3"
  needs either `correction` with a slice spec or a new command.
* Gap: agent emit a typed plan envelope; FE wiring; possibly a new cmd
  for partial-run.

### 3.6 `diff`

* Enter event needed: `plan_diff_proposed` (1955) — defined, unused.
* Buttons: Apply changes, Keep editing, Revert.
* Backend cmd ready: `confirmed` ✅, `correction` ✅. Revert probably
  needs a typed `revert_plan` cmd or `correction` with a `reset` flag.
* Gap: agent emit + FE wiring + possibly new cmd.

### 3.7 `permit`

* Enter event needed: `permission_required` (586) — defined, unused.
* Buttons: Allow once, Allow for this plan, Deny.
* Backend cmd ready: `permission_decision` ✅ (queued to
  `control_queue`).
* Gap: agent emit + FE wiring of three discrete answers.

### 3.8 `exec`

* Enter event ready: `step_executing` ✅ in use.
* Buttons: Pause, Stop run.
* Backend cmd ready: `stop_run` ✅. **`pause` does not exist** as a WS
  message type.
* Gap: add `pause`/`resume` commands or fold into `stop_run` semantics;
  FE wiring; possibly distinct lifecycle state for `paused`.

### 3.9 `locator`

* Enter event needed: `locator_update_request` (1106) or
  `locator_candidates_ready` (2044) — both defined, unused.
* Buttons: Select candidate, Highlight, Ask LLM for better locator,
  Change scope, Stop, Use candidate N.
* Backend cmds: `option_selected` ✅; `improve_locator` ✅ (stub);
  `change_locator_scope` ✅ (stub); `highlight_locator` ✅ (stub);
  `stop_run` ✅.
* Gap: agent emit candidates; de-stub three locator handlers (server.py
  946 / 984 / 1039); FE wiring.

### 3.10 `recover`

* Enter event ready: `recovery_needed` ✅ in use. Structured variant
  `recovery_needed_structured` (2076) — defined, unused.
* Buttons: Apply LLM repair, Retry as-is, Choose another locator, Stop.
* Backend cmds: `correction` ✅ (LLM repair / Choose another can both
  ride this). **No `retry_as_is` command** today.
* Gap: add `retry_as_is` cmd (or route via `correction` with a
  `retry: true` flag); FE wiring.

### 3.11 `done`

* Enter event ready: `run_completed` ✅ in use.
* Buttons: Replay all, Save as suite, Open code, Download trace.
* Backend cmds: `replay_all` ✅; `save_session` ✅; `export_code` ✅
  (covers "Open code" if it returns a path the FE can open). **No
  command for "Download trace"** (trace bundling not exposed).
* Gap: FE wiring; new cmd or REST endpoint for trace download.

### 3.12 `offline`

* Enter trigger: client-side detection of WS close.
* Buttons: Reconnect now, View connection log, Switch endpoint.
* Backend cmds: `switch_endpoint` ✅ stub (only `local` in registry).
  Reconnect is a client-side WS retry. Connection log is local.
* Gap: transport layer must own reconnect; FE wiring of two side
  buttons; registry needs more entries before switch is useful.

### 3.13 `schema`

* Enter event needed: `schema_error` (1851) — defined, unused.
* Buttons: Ask LLM to repair plan, Edit plan manually, Open raw response.
* Backend cmd: `correction` ✅; "Open raw response" is local.
* Gap: agent emit; FE wiring.

### 3.14 `nobrowser`

* Enter event ready: `no_browser` ✅ in use.
* Buttons: Launch chromium, Attach existing tab, Keep plan as draft.
* Backend cmds: **none**. `launch_browser` is a Python function but not
  exposed as a WS command. "Attach existing tab" / "Keep as draft" have
  no backend hooks.
* Gap: add three commands; expose `launch_browser` over WS.

### 3.15 `apikey`

* Enter event ready: `api_key_required` ✅ in use.
* Buttons: Add key, Use shared workspace key.
* Backend cmds: **none**. Adding a key from the UI requires either a
  new WS command (writes to `.env` / process env) or a config endpoint.
* Gap: add a key-store command; FE wiring.

### 3.16 `otp`

* Enter event needed: `human_input_required` (744) — defined, unused.
* Buttons: Submit code, Skip step, Pause run.
* Backend cmds: `correction` ✅; `skip_step` ✅. **No `pause`.**
* Gap: agent emit; add `pause` cmd; FE wiring.

### 3.17 `e2e`

* Enter event needed: `e2e_pending` (797) — defined, unused.
* Buttons: Trigger E2E now, Notify on E2E complete.
* Backend cmds: **none**. E2E pipeline not exposed.
* Gap: add `trigger_e2e` + `notify_on_e2e` commands; backend pipeline.

---

## 4. Cross-cutting items

### 4.1 Transport layer (does not exist yet)

A single new frontend file (e.g. `frontend/transport.jsx`) needs to:

* open `ws://<host>/ws` on page load
* parse every incoming envelope and translate it into `setTweak` calls
  on the same `useTweaks` bag the Tweaks panel mutates (so the state
  machine reuses the existing rendering path)
* expose `window.AW.send(cmd)` and `window.AW.on(type, fn)` for cards
  and Composer to use
* own reconnect / backoff for the `offline` state

This is a prerequisite for every other slice. It is the same shape as
the file we built in commit `dfa8351` and reverted in `2789936` — we
can lift it back when we are ready.

### 4.2 Mock-data replacement

App-level mocks (counts, token info, agent dots, run id) should be
fully driven by `session_state` + `agent_settings` + `token_report` +
`run_started`. Card-level mocks (assertion lists, locator candidates,
plan steps, trace events) follow the per-state events from §3.

### 4.3 Picker

`secondary-tabs.jsx:45` and `:449` toggle a local `picking` flag.
Backend `arm_picker` (server.py:930 + browser.py:804) exists. Wiring
these together needs the transport layer plus a click-listener on the
real page that arm_picker injects.

### 4.4 Manual builder

`secondary-tabs.jsx:6` collects `{ action, assertion, expected }`
locally. Submission should call `run_steps` with a one-element list
(maybe new `step.kind = "manual"`) once a Composer-equivalent button is
added. Not blocking the LLM path; can be a separate sub-feature.

### 4.5 Unused event builders to either emit or delete

We have 24 builders that no agent code calls (full list in §2.2).
Each one is a contract waiting for a producer. The decision per
builder is:

* keep + wire an emit point in agent / executor / orchestrator, or
* delete the builder (and update the spec) if the corresponding state
  isn't actually planned.

A short backend-only sweep through `runtime/event_contracts.py` cross-
referenced against `agent.py` flows would close this gap without any
frontend change.

### 4.6 Commands we will probably need to add

`pause`, `resume`, `retry_as_is`, `launch_chromium`,
`attach_existing_tab`, `keep_plan_as_draft`, `add_api_key`,
`use_workspace_key`, `trigger_e2e`, `notify_on_e2e`, `download_trace`,
`open_raw_response`, `view_redaction_policy`, `view_connection_log`,
`apply_recommendation_set`.

Some of these are pure client-side (view raw response = open a modal
with whatever we already store), others are real RPCs (`launch_chromium`,
`add_api_key`, `trigger_e2e`). We will tag each at the point we wire
it.

---

## 5. Suggested slicing (task list)

These are intentionally small. Pick them off one at a time; don't bundle.

1. **T-1 — Transport read path only.** Re-introduce a minimal
   `transport.jsx` that opens `/ws`, maps the events we already emit
   (`ready`, `api_key_required`, `no_browser`, `agent_settings`,
   `endpoint_registry`, `session_state`, `run_started`,
   `step_executing`, `step_failed`, `step_skipped`, `run_completed`,
   `recovery_needed`, `runtime_rejected`) onto `useTweaks` and writes
   `connection` + `state`. No buttons. No commands. Verifies the pipe
   end-to-end.

2. **T-2 — `idle → planning → exec → done` golden path.** Wire
   Composer Send → `llm_run`, CardPlanReady Confirm & run → `confirmed`,
   CardExecution Stop run → `stop_run`, CardCompleted Replay all →
   `replay_all`. No other cards yet.

3. **T-3 — Permission card.** Emit `permission_required` from agent at
   the right point. Wire CardPermission Allow/Deny → `permission_decision`.

4. **T-4 — Locator card.** Emit `locator_update_request`. Wire
   CardLocatorAmbiguity Select / Highlight / Ask LLM / Change scope to
   the existing four typed commands; de-stub three handlers in
   server.py.

5. **T-5 — Clarification + Recommendation cards.** Emit
   `human_input_required` (rename or repurpose) and `recommendation_ready`.
   Wire the buttons.

6. **T-6 — Plan-diff card.** Emit `plan_diff_proposed`. Wire CardPlanDiff
   Apply / Keep / Revert.

7. **T-7 — Recovery + Schema cards.** Emit `schema_error`. Add
   `retry_as_is` cmd. Wire CardRecovery + CardSchemaError.

8. **T-8 — Offline + reconnect.** Client-side reconnect with backoff in
   transport. Wire `switch_endpoint` button (already a stub).

9. **T-9 — Apikey + No-browser cards.** Add `add_api_key`,
   `launch_chromium`, `attach_existing_tab` commands. Wire the buttons.

10. **T-10 — OTP + E2E cards.** Add `pause`, `trigger_e2e`. Wire those
    two cards.

11. **T-11 — Tab counts + agent dots + token info.** Replace
    `app.jsx:78-93` mocks with derived values from `session_state` /
    `agent_settings` / `token_report`.

12. **T-12 — Steps tab.** Replace the 5 hardcoded step rows with
    `session_state.steps`. Wire the step "More" menu items to
    `change_precondition` / `navigate_to_expected` / `skip_step`.

13. **T-13 — Recorded + Code tabs.** Live `session_state.recorded_steps`
    and `code_preview`. Wire Code tab `Copy` / "Open in editor".

14. **T-14 — Trace tab.** Decide whether trace is its own builder or is
    derived from existing events. Replace 26 hardcoded rows.

15. **T-15 — Picker.** Wire `arm_picker` to the Steps tab "Pick element"
    toggle and the `ManualBuilder` "Re-pick" button. Round-trip the
    selection back via injected listener.

16. **T-16 — Manual builder submission.** Wire `ManualBuilder` "Add step"
    + form to `run_steps` with a manual step kind.

17. **T-17 — Backend emission sweep.** For every still-unused builder
    in §2.2, either wire an emit point in agent / executor / orchestrator
    or delete the builder.

---

## 6. Out of scope of this document

* No proposed code is in this map.
* No commits are made by writing this doc; the task list above is the
  next set of work items.
* The original `AutoWorkbench.html` design bundle continues to be the
  visual reference; any change that drifts from it is a regression.

This document supersedes the spec at
`docs/superpowers/specs/2026-05-15-frontend-rebuild-from-v4-mock-design.md`
for everything after the rebuild. That spec remains valid for the
Phase-1 rebuild it described.
