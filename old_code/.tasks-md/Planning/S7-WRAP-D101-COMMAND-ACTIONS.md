# D-101 Command Actions — Mini-Spec
# improve_locator / blocked-action resolve / change_precondition / navigate_to_expected

**Status:** PLANNING — Sprint 7 closeout  
**Branch:** `s7/clusters-6-11-complete-llm-mode`  
**Spec authored at HEAD:** `6c34187`  
**Date:** 2026-05-14  
**Parent spec:** `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md`

---

## Decision Summary

All four sub-areas are BUILD_P0_SEAM. None has a backend command handler wired in
`server.py`. Grep across `agent.py`, `server.py`, and `runtime/` confirms:

- `improve_locator` — frontend dispatches the command object; `server.py` routes it to
  `COMMAND_NOT_SUPPORTED`. No server-side handler block exists.
- `change_locator_scope` — same situation. Frontend wraps it; server drops it.
- `choose_locator_candidate` — **already wired** through CardLocatorAmbiguity; NOT part
  of this mini-spec scope.
- `change_precondition` / `navigate_to_expected` — command names appear only in the
  master spec; no backend Python handler exists anywhere.
- `resolve_blocked` (any variant) — no Python handler. The blocked-action button in
  `StepBlockedStrip` is disabled with `title="Resolve command not yet wired"`.

PRD-P0 basis is solid for all four. Phase 3 ("locator replacement flow") and Phase 2
recovery/precondition flows are explicitly listed in `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`
acceptance matrix. P0-scenarios §21 names the full inline locator update contract.

**Recommended implementation order:**

| Order | Sub-area | Fate | Rationale |
|---|---|---|---|
| 1 | A — improve_locator / view_candidates | BUILD_P0_SEAM | Builds the new backend handler that B and C partially reuse for page-state checks. |
| 2 | C — change_precondition / navigate_to_expected | BUILD_P0_SEAM | Shares the page-state requirement concept with A; minimal new seam. |
| 3 | B — blocked-action resolve | BUILD_P0_SEAM | Depends on knowing which resolve command routes to which recovery path; builds on the precondition pattern from C. |
| 4 | D — close-out remaining D-101 items | WIRE_EXISTING_SEAM | Final audit pass; verifies nothing was missed. |

---

## Sub-area A — improve_locator / view_candidates

### Objective

Wire the "Ask LLM" and inline locator improve buttons on the Steps tab and the
CardLocatorAmbiguity card so they dispatch a validated `improve_locator` command to the
backend and surface the returned candidate list for user selection — without any
frontend-only fake behavior.

### Current state

- `llm-cards.jsx:636` — `CardLocatorAmbiguity` "Ask LLM" button calls
  `onAskLLM({ type: "improve_locator", step_id })`.
- `aw-ide-panel.jsx:198` — `buildDispatchers` maps `onAskLocatorLLM` through
  `loggedDispatcher("ask_locator_llm", runtime?.onAskLocatorLLM)`.
- `frontend/src/main.jsx` — `runtime.onAskLocatorLLM` is **not bound** to a WebSocket
  send; the dispatcher logs and drops the call.
- `server.py:631-636` — all unrecognised `msg_type` values fall to
  `COMMAND_NOT_SUPPORTED`. No `if msg_type == "improve_locator"` block exists.
- `runtime/locator_update.py` — `process_locator_update` and
  `check_locator_update_precondition` exist but are not called from any server route.
- `runtime/agent_locator_handlers.py` — `tool_locator_find` / `tool_locator_validate`
  exist as LLM tool helpers, not as user-command handlers.
- Step tab inline locator improve action is not yet rendered (referenced in pass 4b-1.1
  deferral in `UI_DEFECTS.md` D-101 row).

### Source / PRD-P0 basis

- `PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md` §"Phase 3 — Recording,
  save, replay, repair, versioning" — "locator replacement flow" is Phase-3 acceptance.
- `06 §Acceptance matrix` — "Locator update: alternatives generated/scored/validated;
  chosen locator updates code/replay" — explicit P0 acceptance criterion.
- `06 §Tests that must exist` #7 — "User requests better locator → alternatives
  validated → code/replay updated."
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` §21 — full inline locator
  update contract including `improve_locator`, `view_candidates`, `change_scope`,
  page-state precondition check, and focused LLM locator packet.
- `PRD_v2_3_Modular_Pack_v2/05_CODEGEN_REPLAY_PERSISTENCE.md` §"Locator update /
  replacement flow" — end-to-end contract.

### Control inventory rows affected (master §6)

| Row | Control | Current status |
|---|---|---|
| `locator-ask-llm` (`llm-cards.jsx:635`) | Locator ask-LLM | DISPATCH_PRESENT / BACKEND_OPEN |
| `locator-change-scope` (`llm-cards.jsx:641`) | Locator change-scope | DISPATCH_PRESENT / BACKEND_TBD |
| Step inline improve (not yet rendered, pass 4b-1.1) | Step locator improve inline | MISSING |

### Seam fate per master §5

`BUILD_P0_SEAM` — no server handler exists; PRD explicitly names locator replacement as
Phase-3 acceptance.

### Backend events/commands needed

| Command/event | Status | Notes |
|---|---|---|
| `improve_locator` (frontend → backend) | **NEW SEAM REQUIRED** | Add `if msg_type == "improve_locator"` block in `server.py`. Payload: `{ step_id, operation_id?, user_hint? }`. Backend runs deterministic candidate pipeline, validates each live, returns ranked list. |
| `change_locator_scope` (frontend → backend) | **NEW SEAM REQUIRED** | Add `if msg_type == "change_locator_scope"` in `server.py`. Payload: `{ step_id, scope_hint }`. Backend narrows candidate search to scope. Returns updated candidate list. |
| `locator_candidates_ready` (backend → frontend) | **NEW SEAM REQUIRED** | New backend event emitted after `improve_locator` or `change_locator_scope` resolves. Payload mirrors `locator_ambiguous` / `candidate_choice_needed` shape so CardLocatorAmbiguity re-renders without code change. |
| `precondition_failed_for_locator_update` (backend → frontend) | **NEW SEAM REQUIRED** | Emitted when browser is on wrong page to run live validation. Payload: `{ step_id, required_page_state, current_url, available_resolution_options[] }`. Frontend must show this error state. |
| `choose_locator_candidate` (frontend → backend) | **EXISTING / ALREADY WIRED** | Used in CardLocatorAmbiguity confirm path. Reuse same command for post-improve candidate selection. No new handler needed. |
| `update_locator` (frontend → backend) | **EXISTING IN CONTRACT** — `04_BACKEND_EVENT_CONTRACT.md` v2.2 table; not yet in `server.py` dispatch. Candidate for improvement-accept path. |

Note: do NOT invent `view_candidates` as a new WS command. P0-scenarios §21.1 lists
it as a UI action that triggers the same backend flow as `improve_locator`. Map it to
the same handler.

### Frontend files likely touched

- `frontend/src/v4/secondary-tabs.jsx` — add inline locator improve button on step
  locator chip row (deferred pass 4b-1.1); bind `onImproveLocator` prop.
- `frontend/src/v4/llm-cards.jsx` — `CardLocatorAmbiguity` already has the button;
  verify `onAskLLM` prop is threaded from panel.
- `frontend/aw-ide-panel.jsx` — bind `runtime.onAskLocatorLLM` → WS send
  `{ type: "improve_locator", ... }`; add `onChangeScope` → WS send
  `{ type: "change_locator_scope", ... }`.
- `frontend/src/main.jsx` — add `onAskLocatorLLM` and `onChangeLocatorScope` to
  runtime object pointing to `sendWs`.
- Frontend store reducer — handle `locator_candidates_ready` event; update
  `locatorAmbiguity` store slice with new candidates so CardLocatorAmbiguity re-renders.
- Frontend store reducer — handle `precondition_failed_for_locator_update`; surface
  error in step row or LLM thread.

### Tests required

**jsdom:**
1. `CardLocatorAmbiguity` "Ask LLM" click → `onAskLLM` called with
   `{ type: "improve_locator", step_id }`.
2. `CardLocatorAmbiguity` "Change scope" click → `onChangeScope` called with
   `{ type: "change_locator_scope", step_id }`.
3. Reducer: `locator_candidates_ready` event updates ambiguity store slice; card
   re-renders new candidate list.
4. Reducer: `precondition_failed_for_locator_update` stores error; error visible in
   render.
5. Step inline improve button (once rendered) → `onImproveLocator` called.

**Backend contract:**
1. `server.py` `improve_locator` handler: valid payload → calls locator pipeline → emits
   `locator_candidates_ready` with ranked list.
2. `server.py` `improve_locator` handler: missing `step_id` → emits typed rejection.
3. `server.py` `improve_locator` handler: browser on wrong page → emits
   `precondition_failed_for_locator_update`.
4. `server.py` `change_locator_scope` handler: valid scope → returns narrowed candidates.
5. `runtime/locator_update.py` `check_locator_update_precondition` already has unit
   tests (`tests/` — verify or add).

### E2E required?

YES — use `tests/e2e/test_llm_required_ambiguous_action_flow.py`. After locator
ambiguity card appears, click "Ask LLM" and assert the card refreshes with new
candidates. Local-fixture only; no paid LLM call (deterministic candidate pipeline
must be exercised).

### Acceptance criteria

- "Ask LLM" click on CardLocatorAmbiguity sends `improve_locator` over WS; no
  `COMMAND_NOT_SUPPORTED` error is returned.
- Backend runs deterministic candidate pipeline and emits `locator_candidates_ready`;
  card updates candidate list in UI.
- "Change scope" click sends `change_locator_scope`; backend narrows candidates;
  card updates.
- If browser is on wrong page, backend emits `precondition_failed_for_locator_update`;
  UI shows error row, not silent failure.
- Step inline improve button (when rendered) behaves identically to card path.
- `choose_locator_candidate` confirm after improve → same flow as before improve; no
  duplicate dispatch.
- All new jsdom and backend contract tests pass; no existing test weakened.

### Stop conditions

- Backend `improve_locator` handler would require LLM call in test path → STOP, ask
  user. Use deterministic-only path for local tests.
- Handler touches more than `server.py` + one new `runtime/` module + existing
  `runtime/locator_update.py` + `runtime/agent_locator_handlers.py` → STOP, scope too
  broad.
- Frontend changes touch `llm_runtime_controller.py` or `agent.py` main loop → STOP,
  wrong layer.

### Final handoff evidence required (§13)

- `server.py` line numbers for new `improve_locator` and `change_locator_scope` blocks.
- New backend event shape for `locator_candidates_ready` (JSON schema excerpt).
- jsdom test run excerpt showing 5+ passing tests covering the above.
- Grep confirming `onAskLocatorLLM` is bound in `main.jsx` and not a no-op.
- E2E fate code for `test_llm_required_ambiguous_action_flow.py` after this pass.

---

## Sub-area B — blocked-action resolve

### Objective

Wire the `step-blocked-action` button in `StepBlockedStrip` so it dispatches a typed
resolve command to the backend based on `blocked.reason`, covering all four canonical
reason codes: `missing_data`, `wrong_page`, `locator_unstable`, and
`permission_required`.

### Current state

- `secondary-tabs.jsx:279` — `StepBlockedStrip` renders the action button as disabled
  with `title="Resolve command not yet wired (Pass 4b-4.1)"`.
- `secondary-tabs.jsx:276` — `data-testid="step-blocked-action-${stepId}"` present.
  `V4_TESTID_CONTRACT.md` §6 marks it `ACTIVE (DISABLED)`.
- `server.py` — no `if msg_type` block for any blocked-step resolve command variant.
  The master spec §6 row for `step-blocked-action` lists backend command as "TBD per
  blocked.reason".
- No `resolve_blocked_step` handler exists anywhere in `agent.py`, `server.py`, or
  `runtime/`.
- `UI_DEFECTS.md` D-101 — remaining pass 4b-4.1 scope.

### Source / PRD-P0 basis

- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` §"Phase 2 — Complete LLM Mode MVP" — "recovery
  correction" is Phase-2 acceptance. Blocked steps that cannot proceed are part of
  recovery correction path.
- `06 §Acceptance matrix` — "LLM Mode: single step, multi-action section, queued steps,
  correction, recovery, recording, code_update pass."
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` §5.4 — execution failure
  classifications include `precondition_failed`, `permission_required`. §3.7 —
  `locator_unstable` is a first-class locator issue classification.
- `PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md` §"Recovery decision tree" — wrong-page,
  locator-not-found, permission failure all have explicit recovery guidance.
- `PRD_v2_3_Modular_Pack_v2/04_BACKEND_EVENT_CONTRACT.md` — `skip_step` and
  `correction` commands exist and are wired; the blocked-action button needs to route to
  one of these or a new typed variant depending on `blocked.reason`.

### Control inventory rows affected (master §6)

| Row | Control | Current status |
|---|---|---|
| `step-blocked-action-${stepId}` (`secondary-tabs.jsx:276`) | Step blocked-action | DISABLED_PENDING_SEAM → BUILD_P0_SEAM |

### Seam fate per master §5

`BUILD_P0_SEAM` — no backend handler; PRD names recovery for Phase-2 acceptance.

### Backend events/commands needed

The blocked-step action must route differently per `blocked.reason`. Map:

| `blocked.reason` | Frontend action label | Backend command to send | Handler status |
|---|---|---|---|
| `missing_data` | "Provide data" or "Edit step" | `correction` with `{ type: "correction", message: "User is providing missing data", step_id }` | **EXISTING** (`server.py:410`). Wire existing. |
| `wrong_page` | "Navigate there" | **NEW COMMAND REQUIRED** — `navigate_to_required_page` or re-use `navigate_to_expected` (see Sub-area C below) with step context. | NEW SEAM REQUIRED. |
| `locator_unstable` | "Improve locator" | `improve_locator` from Sub-area A. | BUILD in Sub-area A first. |
| `permission_required` | "Grant permission" | `permission_decision` with `{ type: "permission_decision", decision: "allow_once", step_id }` | **EXISTING** (`server.py:580`). Wire existing. |
| `unknown` / fallback | "Skip step" | `skip_step` with `{ type: "skip_step", step_id }` | **EXISTING** (`server.py:468`). Wire existing. |

New command needed: for `wrong_page`, either reuse the `navigate_to_expected` seam
from Sub-area C, or add `navigate_to_required_page` with `{ step_id }` payload. Do
not invent a name — see Sub-area C for the canonical name decision; implement after C
lands.

### Frontend files likely touched

- `frontend/src/v4/secondary-tabs.jsx` — `StepBlockedStrip`: enable the action button
  conditional on `blocked.reason`; bind per-reason dispatch callback; remove disabled
  state and placeholder title.
- `frontend/aw-ide-panel.jsx` — thread `onResolveBlockedStep(stepId, reason)` dispatcher
  into StepsTab → StepRow → StepBlockedStrip.
- `frontend/src/main.jsx` — add `onResolveBlockedStep` that inspects `reason` and calls
  the appropriate `sendWs` payload.

### Tests required

**jsdom:**
1. `StepBlockedStrip` with `reason="missing_data"` → action button enabled → click →
   `onResolveBlocked` called with `{ type: "correction", step_id }`.
2. `reason="wrong_page"` → click → `onResolveBlocked` called with navigate command.
3. `reason="locator_unstable"` → click → `onResolveBlocked` called with
   `{ type: "improve_locator", step_id }`.
4. `reason="permission_required"` → click → `onResolveBlocked` called with
   `{ type: "permission_decision", decision: "allow_once", step_id }`.
5. `reason="unknown"` → click → `onResolveBlocked` called with
   `{ type: "skip_step", step_id }`.
6. Button has no `disabled` attribute after wiring; `title` is updated to explain the
   action (not the old placeholder).

**Backend contract:**
1. `missing_data` path routes to existing `correction` handler without new handler code.
2. `permission_required` path routes to existing `permission_decision` handler.
3. `skip_step` routes to existing `skip_step` handler.
4. `wrong_page` / `navigate_to_required_page` new handler (after Sub-area C lands):
   valid `step_id` → emits navigation intent or `navigate_to_expected` response.

### E2E required?

YES — use `tests/e2e/test_llm_required_ambiguous_action_flow.py` or
`tests/e2e/test_correction_assert_then_click_flow.py` where a step can be forced into
blocked state. Verify button click sends correct WS message. Local fixture only.

### Acceptance criteria

- `step-blocked-action` button is enabled (no `disabled` attribute) after this pass.
- Each `blocked.reason` dispatches the correct typed command; no `COMMAND_NOT_SUPPORTED`
  returned.
- `missing_data` → `correction`; `permission_required` → `permission_decision`;
  `locator_unstable` → `improve_locator`; `wrong_page` → `navigate_to_required_page`
  (or `navigate_to_expected`); `unknown` → `skip_step`.
- Button label / `title` text is reason-specific, not generic placeholder.
- All five jsdom tests pass; no existing blocked-strip render tests regress.
- `V4_TESTID_CONTRACT.md` §6 row updated from `ACTIVE (DISABLED)` to `ACTIVE`.

### Stop conditions

- `wrong_page` resolve command would require backend navigation logic touching
  `agent.py` main agent loop — STOP, too broad; use Sub-area C's simpler seam first
  and link.
- The reason-routing logic would require reading live browser state from frontend —
  STOP, PRD forbids frontend lifecycle inference.
- Any path would use LLM call in local test — STOP, ask user.

### Final handoff evidence required (§13)

- `secondary-tabs.jsx` line number where disabled is removed and per-reason dispatch
  is wired.
- `aw-ide-panel.jsx` line number of `onResolveBlockedStep` dispatcher.
- Table mapping each `blocked.reason` to the WS command sent (verified by jsdom test
  assertion).
- jsdom test run excerpt showing 5+ passing tests.

---

## Sub-area C — change_precondition / navigate_to_expected

### Objective

Wire the disabled "Change precondition" button in `StepPreconditionStrip` so it
dispatches a typed command to the backend. Cover both sub-cases: user wants to update
the expected precondition URL/state (`change_precondition`) and user wants the backend
to navigate the browser to the expected state (`navigate_to_expected`).

### Current state

- `secondary-tabs.jsx:148` — `StepPreconditionStrip` renders action button disabled:
  `title="Change precondition command not yet wired (Pass 4b-5.1)"`.
- `data-testid="step-precondition-action-${stepId}"` present; contract marks it
  `ACTIVE (DISABLED)`.
- `server.py` — no `if msg_type` block for `change_precondition` or
  `navigate_to_expected`. Grep across all Python files confirms neither command name
  appears anywhere in the codebase.
- `PRD_v2_3_Modular_Pack_v2/05_CODEGEN_REPLAY_PERSISTENCE.md` — "Replay Precondition
  Guard v1" addendum defines `replay_precondition_failed` as the backend event and
  `navigate_to_required_page` as a resolution option.
- `agent.py:702-877` — `_check_replay_precondition`,
  `_build_replay_precondition_failure_result` exist for the replay path. They emit
  structured `replay_precondition_failed` results but do not handle user-initiated
  navigation or precondition change commands.

### Source / PRD-P0 basis

- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` §"Phase 3" — "replay one/all" and "LLM repair
  during replay" are Phase-3 acceptance. Precondition guard is prerequisite.
- `05_CODEGEN_REPLAY_PERSISTENCE.md` §"Replay Precondition Guard v1" — "Replay One
  blocks if current URL/title does not match recorded before state" is v1 acceptance
  criterion #1. User-facing resolution options listed: `navigate_to_required_page`,
  `cancel_locator_update`, etc.
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` §21.3 — "precondition
  resolution options" include `navigate_to_required_page` explicitly. §3.8 — "Page-state
  and dependency awareness" — every step carries `precondition`.
- Master spec §6 row — "Step precondition-action" has `change_precondition /
  navigate_to_expected` as backend commands, `BUILD_P0_SEAM` fate, ticket D-101.

### Control inventory rows affected (master §6)

| Row | Control | Current status |
|---|---|---|
| `step-precondition-action-${stepId}` (`secondary-tabs.jsx:145`) | Step precondition-action | DISABLED_PENDING_SEAM → BUILD_P0_SEAM |

### Seam fate per master §5

`BUILD_P0_SEAM` — no backend handler; PRD names Replay Precondition Guard v1 as Phase-3
acceptance criteria explicitly.

### Backend events/commands needed

| Command/event | Status | Notes |
|---|---|---|
| `change_precondition` (frontend → backend) | **NEW SEAM REQUIRED** | User edits the expected URL/state stored with a step. Payload: `{ step_id, expected_url?, expected_title?, message? }`. Backend updates the step's precondition metadata; emits `step_precondition_updated` or absorbs into existing step update path. Does not trigger navigation. |
| `navigate_to_expected` (frontend → backend) | **NEW SEAM REQUIRED** | User asks backend to navigate the browser to the step's recorded `before_url`. Payload: `{ step_id }`. Backend reads step's precondition/before-url, calls `page.goto(before_url)`, confirms navigation, emits `navigation_complete` or uses existing `step_validating` event path. |
| `step_precondition_updated` (backend → frontend) | NEW event recommended | Payload: `{ step_id, new_precondition }`. Frontend reducer updates step precondition strip. |

Note on naming: P0-scenarios §21 uses `navigate_to_required_page` as the resolution
option label. Master spec uses `navigate_to_expected`. Use `navigate_to_expected` (as
per master spec §6 row and commit discipline §16) to stay internally consistent. Do not
introduce a third name.

### Frontend files likely touched

- `frontend/src/v4/secondary-tabs.jsx` — `StepPreconditionStrip`: enable action button;
  split into two actions if the precondition strip exposes both options, or combine into
  a single "Fix precondition" button that calls the appropriate command based on whether
  the user wants to edit vs navigate.
- `frontend/aw-ide-panel.jsx` — add `onChangePrecondition` and `onNavigateToExpected`
  dispatchers.
- `frontend/src/main.jsx` — bind dispatchers to `sendWs`.
- Frontend store reducer — handle `step_precondition_updated` event; refresh strip state.

### Tests required

**jsdom:**
1. `StepPreconditionStrip` action button is enabled (no `disabled`) after wiring.
2. Click "Change precondition" → callback called with
   `{ type: "change_precondition", step_id }`.
3. Click "Navigate to expected" → callback called with
   `{ type: "navigate_to_expected", step_id }`.
4. Reducer: `step_precondition_updated` event → strip re-renders with updated
   `expected_url`.
5. Button `title` is explanatory (not the old placeholder string).

**Backend contract:**
1. `server.py` `change_precondition` block: valid `step_id` + `expected_url` → updates
   stored precondition; emits `step_precondition_updated`.
2. `server.py` `change_precondition` block: missing `step_id` → typed rejection.
3. `server.py` `navigate_to_expected` block: valid `step_id` → backend reads
   step before_url → `page.goto(before_url)` → emits confirmation event.
4. `server.py` `navigate_to_expected` block: `step_id` has no stored `before_url` →
   typed error response, not crash.

### E2E required?

YES — use `tests/e2e/test_mvp_001_lifecycle_smoke.py` or a new fixture. After a
`replay_precondition_failed` event is emitted, verify the "Navigate to expected" button
appears and clicking it triggers a page navigation. Local-fixture only.

### Acceptance criteria

- `step-precondition-action` button is enabled after this pass; `disabled` attribute
  absent.
- `change_precondition` command is accepted by `server.py` without
  `COMMAND_NOT_SUPPORTED`; step's precondition metadata updates; `step_precondition_updated`
  event emitted.
- `navigate_to_expected` command navigates browser to the step's `before_url`; backend
  confirms navigation.
- Missing `before_url` case returns typed error, not unhandled exception.
- All jsdom tests pass; `V4_TESTID_CONTRACT.md` §6 row updated to `ACTIVE`.
- `agent.py` replay precondition guard (`_build_replay_precondition_failure_result`)
  payload includes `navigate_to_expected` as a named resolution option in its
  `available_resolution_options` list so the frontend can surface it from the
  `replay_precondition_failed` event payload.

### Stop conditions

- `navigate_to_expected` handler requires calling into the LLM agent loop rather than
  a direct `page.goto` — STOP, wrong layer.
- `change_precondition` handler must mutate recorded step artifacts already saved to
  disk — STOP, that's replay repair (Phase 3 separate sub-task, Sprint 8+).
- Handler touches more than `server.py` + one small runtime helper → STOP.

### Final handoff evidence required (§13)

- `server.py` line numbers for `change_precondition` and `navigate_to_expected` handler
  blocks.
- Shape of `step_precondition_updated` event (JSON schema excerpt).
- `agent.py` grep showing `navigate_to_expected` in `available_resolution_options` list.
- jsdom test run excerpt showing 4+ passing tests.

---

## Sub-area D — Close-out remaining D-101 command-only items

### Objective

Verify, after Sub-areas A/B/C complete, that no D-101 command gap remains open. Audit
the control inventory, the test suite, and `server.py` to confirm all previously
disabled-pending-seam controls are either wired or formally classified per §5.

### Current state

At spec-authoring time the following D-101 gaps were open:

| Gap | Status at authoring |
|---|---|
| `improve_locator` / `view_candidates` | Sub-area A |
| `change_locator_scope` | Sub-area A |
| Blocked-action resolve (4 reasons) | Sub-area B |
| `change_precondition` | Sub-area C |
| `navigate_to_expected` | Sub-area C |
| Step inline locator improve button (pass 4b-1.1) | Sub-area A (add button) |

No additional D-101 command items are known. This sub-area is a final audit pass, not
new build work.

### Source / PRD-P0 basis

Master spec §4 — "D-101 command-only gaps: OPEN" is the checkpoint marker. Sprint 7
acceptance gate §12 criterion #6 — "All v4 controls audited per §6; every row resolved."

### Control inventory rows affected (master §6)

All rows with `D-101` ticket and `BUILD_P0_SEAM` fate. After Sub-areas A/B/C:

| Row | Expected final fate |
|---|---|
| `locator-ask-llm` | WIRE_EXISTING_SEAM (handler built in A) |
| `locator-change-scope` | WIRE_EXISTING_SEAM (handler built in A) |
| `step-blocked-action-${stepId}` | WIRE_EXISTING_SEAM (handlers wired in B) |
| `step-precondition-action-${stepId}` | WIRE_EXISTING_SEAM (handlers wired in C) |
| Step inline improve (new button) | KEEP_ACTIVE (new button added in A) |

### Seam fate per master §5

`WIRE_EXISTING_SEAM` — after A/B/C this is verification only. If grep reveals a new
unresolved gap, fate reverts to `BUILD_P0_SEAM` and a new sub-area is required.

### Backend events/commands needed

None new. Only verification that all new handlers added in A/B/C are covered by tests
and that `server.py` has no remaining D-101 `COMMAND_NOT_SUPPORTED` fallback for
these types.

### Frontend files likely touched

- `V4_TESTID_CONTRACT.md` — update status column for affected rows from
  `ACTIVE (DISABLED)` to `ACTIVE`.
- `UI_DEFECTS.md` D-101 — update pass 4b-1.1, 4b-4.1, 4b-5.1 sub-pass markers to
  DONE.
- Master spec §6 — update `Current status` and `Fate` columns for all D-101 rows.
- Master spec §4 — update checkpoint: "D-101 command-only gaps: DONE".

### Tests required

**Audit-only:**
1. `grep -r "COMMAND_NOT_SUPPORTED"` — confirm `improve_locator`, `change_locator_scope`,
   `change_precondition`, `navigate_to_expected` do NOT appear in server rejection logs
   in any test fixture.
2. `grep -r "not yet wired"` across `secondary-tabs.jsx` — confirm no remaining
   placeholder `title` strings referencing D-101.
3. Run `cd frontend && npm test` — confirm all previously passing tests still pass and
   new tests from A/B/C also pass.
4. Run `python -m pytest --tb=short -q --ignore=tests/e2e` — confirm no new failures.

### E2E required?

NO — Sub-areas A/B/C each carry their own E2E fate. This close-out is doc and audit
only.

### Acceptance criteria

- `grep "COMMAND_NOT_SUPPORTED"` in any server log for `improve_locator`,
  `change_locator_scope`, `change_precondition`, `navigate_to_expected` returns zero
  hits after the test suite runs.
- `secondary-tabs.jsx` has no `disabled` button with a "not yet wired" title for any
  D-101 control.
- `V4_TESTID_CONTRACT.md` §6 rows for all four affected controls show `ACTIVE` (not
  `ACTIVE (DISABLED)`).
- Master spec §4 checkpoint updated: "D-101 command-only gaps: DONE".
- `UI_DEFECTS.md` D-101 row notes all pass 4b-* sub-passes as DONE.
- Sprint 7 master §12 acceptance gate criterion #6 passes for D-101 scope.

### Stop conditions

- Audit finds a new unresolved command gap not covered by A/B/C — STOP, open new
  sub-area, do not silently disable.
- Any newly discovered `COMMAND_NOT_SUPPORTED` hit in test suite log means a test is
  incorrectly passing — STOP, fix the test not the gate.

### Final handoff evidence required (§13)

- Grep output (command run + stdout) confirming zero "not yet wired" strings in
  `secondary-tabs.jsx`.
- `V4_TESTID_CONTRACT.md` §6 screenshot or diff showing updated rows.
- Master spec §4 diff showing checkpoint updated.
- `npm test` summary (pass count) and `pytest` summary confirming no regression.

---

## Cross-cutting notes

**No frontend-only fake behavior.** If a backend seam is not ready, the button stays
disabled with an accurate `title` per §8 requirements. Do not render fake candidate
lists or fake navigation confirmations.

**Commit discipline.** Each sub-area lands as a separate commit per master §16:
- Sub-area A: `feat(v4): wire improve_locator inline action`
- Sub-area B: `feat(v4): wire blocked-action resolve commands`
- Sub-area C: `feat(v4): wire change_precondition / navigate_to_expected`
- Sub-area D: `docs: D-101 command-actions close-out audit`

**Test-id contract.** Every new interactive control wired in A/B/C must have a stable
`data-testid` and must update `V4_TESTID_CONTRACT.md` in the same commit per §13
maintenance rules.

**PRD conflict sentinel.** If the backend handler for `navigate_to_expected` would
require the agent loop to issue a `page.goto` that mutates the current browser session
state in a way that loses the in-progress run — STOP and ask user. The Replay
Precondition Guard v1 addendum explicitly says "Replay All may auto-navigate only for
simple same-tab URL restoration."
