# Sprint 8 — Bug / Deferred Work Tickets

This file collects bugs and deferred work surfaced during Sprint 7 closeout
that require backend or cross-stack work in Sprint 8. Each entry has its own
heading; agents owning a Sprint 8 cluster append (do not rewrite) sections
here as new tickets are filed.

---

## BUG-S8-AGENT-001 — Wire Agent Control Center (backend events + frontend toggles)

**Filed by:** D-106 closeout (Sprint 7 wrap, Batch C Part 2).
**Status:** OPEN.
**PRD references:** `03 §Agent Control Center`, `07 §7 Agent Control Center`,
`04 §Multi-model event additions` (lines 92–107), `07 §8 Backend event
contract additions`, `06 §Multi-model`.
**Sprint 7 closure verdict:** `DISABLED_WITH_REASON` (see D-106 in
`.tasks-md/Audit/UI_DEFECTS.md`). Fake `DEFAULT_AGENTS` fallback removed from
production runtime; popover renders honest empty/read-only state until this
ticket lands.

### Why this is deferred to Sprint 8

The multi-model Agent Control Center UI was classified non-P0 for Sprint 7
closure (master spec §5 negative indicator: "07 Multi-model orchestration
agent control center → non-P0 for Sprint 7 closeout"). Page Intelligence
*runtime* IS P0 (Phase 2 LLM MVP depends on it) and its backend seam is
already wired (S7-0203), but the *multi-model UI surfacing* — agent registry
events, per-agent progress/result/failure events, agent enable/disable
commands, and trace view — is not. Today the backend emits **zero**
`agent_settings / agent_progress / agent_result / agent_failed / agent_trace`
events (grep evidence: no hits in `runtime/`, `agent.py`, `server.py`,
`frontend/src/`) and `server.py` has no handler for `set_agent_enabled`.

### Scope

Backend agent registry events + frontend store handling + agent control
commands + Agent Control Center popover wiring.

### Acceptance criteria

1. Backend emits `agent_settings` on WebSocket connect with
   `{ type: "agent_settings", agents: [ { key, name, required, enabled, model, status } ] }`.
2. Backend emits `agent_started / agent_progress / agent_result / agent_failed`
   events per agent run with typed payloads per `04 §agent_*`.
3. `server.py` handles `set_agent_enabled` command; validates agent key;
   rejects attempts to disable required agents; broadcasts updated
   `agent_settings`.
4. `runtime/event_contracts.py` adds `set_agent_enabled` to
   `SUPPORTED_FRONTEND_COMMAND_TYPES`; adds `agent_settings`,
   `agent_started`, `agent_progress`, `agent_result`, `agent_failed`,
   `agent_trace` to the typed backend event contract.
5. Frontend reducer processes `agent_settings` → updates `store.agents`.
6. Frontend reducer processes `agent_started / agent_progress / agent_result
   / agent_failed` → updates per-agent status in `store.agents`.
7. `AgentsPopover` continues to read `agents` from store (already wired in
   D-106); empty-state branch yields only when backend has not yet emitted
   `agent_settings`.
8. Non-required toggles dispatch typed `set_agent_enabled` on click; remain
   disabled while a request is in flight and re-enable on
   `agent_settings` broadcast.
9. Required toggles remain locked (already correct in D-106).
10. Header count strip derives from live store state (currently the
    `aw-agents-sprint8-badge` is shown in its place — replace with a live
    `N active · M off` strip backed by `store.agents`).
11. `agent_trace` event populates a trace view (design TBD; coordinate with
    Trace tab D-104 scope to avoid duplication).
12. jsdom tests cover: `agent_settings` reducer, toggle dispatch, required-
    locked behavior, empty-state branch when no `agent_settings` received.
13. Backend contract tests cover: `set_agent_enabled` accepts valid keys,
    rejects required-disable attempts and unknown keys; `agent_settings`
    emitted on connect; per-agent progress/result/failed events round-trip.

### Out of scope for this ticket

- Run Page Intelligence Now, Clear Cache, Show Agent Trace full view,
  Judge/Risk Agent — all deferred to Sprint 9 per `07 §Phase 5`.
- Any UI for editing agent model assignments (separate ticket).

### Evidence required at close

1. `grep -rn "agent_settings\|agent_progress\|agent_result\|agent_failed\|agent_trace\|set_agent_enabled" runtime/ agent.py server.py frontend/src/`
   returns non-zero hits across all four paths.
2. Backend contract tests GREEN.
3. jsdom tests GREEN; new tests cover registry, dispatch, empty-state branch.
4. `AgentsPopover` `aw-agents-empty` testid disappears once backend emits
   `agent_settings` in the smoke flow.
5. UI_DEFECTS.md D-106 row updated to point at this ticket as ENABLED.

### Architecture invariants (must hold)

- Backend owns runtime truth.
- Frontend never invents agent state.
- No dead clickable controls.
- No paid LLM calls in tests; no live website in tests.
- No test weakening.
---

## BUG-S8-MANUAL-001 — Implement Manual Mode working foundation (D-105 class A)

**Origin:** Sprint 7 wrap-up D-105 mini-spec
(`/.tasks-md/Planning/S7-WRAP-D105-MANUAL-MODE.md`) classified Manual Mode as
**B — DISABLED_WITH_REASON**. The Sprint 7 closure renders the Manual option in
the Header mode toggle as `disabled` with a Sprint 8 title; no
backend handler exists, no frontend command is dispatched. This ticket tracks
the full class-A path needed to actually enable Manual Mode.

**Status:** Open — deferred to Sprint 8.

**PRD basis:**
- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` Phase 4 ("Manual Mode using same runtime")
- v2.3 priority #4 (after LLM Mode MVP, Recording/save/replay/repair)
- v2.2 Must-have #1 (preserved)

### Current state (Sprint 7 closure)

| Surface | State |
|---|---|
| `frontend/src/v4/chrome.jsx` Header | Renders LLM/Manual toggle; Manual is `disabled` + `aria-disabled="true"` + Sprint 8 title; no `onClick` |
| `frontend/src/components/manual/ManualActionBuilder.jsx` | Component file exists; NOT imported anywhere in `frontend/src/v4/` or `frontend/src/main.jsx` |
| `frontend/src/components/manual/ManualAssertionBuilder.jsx` | Same — exists, never imported in production v4 surface |
| `frontend/src/components/manual/ManualModeToggle.jsx` | Same — exists, never imported in production v4 surface |
| `server.py` / `agent.py` | No `set_mode`, `manual_action_draft`, `manual_assertion_draft`, `mode_changed` handlers; unrecognized commands fall through to `COMMAND_NOT_SUPPORTED` |
| `runtime/event_contracts.py::SUPPORTED_FRONTEND_COMMAND_TYPES` | Does NOT list `set_mode`, `manual_action_draft`, `manual_assertion_draft` |

### Acceptance criteria

1. **Mode-state backend seam.** Add `set_mode` to
   `SUPPORTED_FRONTEND_COMMAND_TYPES`. `server.py` validates
   `mode ∈ {"llm","manual"}` and emits a typed `mode_changed`
   `{type, mode}` event back through the websocket. No active-run disruption;
   no `recorded_steps` mutation.
2. **Manual action seam.** Add `manual_action_draft` typed command:
   payload `{step_id, action, target, value?}`. `server.py` validates and
   dispatches into the same Step Runner path used for LLM-recorded steps;
   emits `step_recorded` on success and a typed rejection on validation
   failure. No fork of the Step Runner.
3. **Manual assertion seam.** Add `manual_assertion_draft` typed command:
   payload `{step_id, assertion_type, target, expected}`. Same Step Runner
   path; same `step_recorded` emission contract.
4. **Recording evidence persistence.** Manual steps land in the same
   workspace evidence store as LLM steps — same `recorded_step.json` schema,
   same artifact bundle, same redaction policy. No second store, no
   frontend-only recorded list.
5. **Frontend reducer.** `main.jsx` reducer handles `mode_changed`:
   `state.mode = payload.mode`. The Header `aw-mode-manual` button becomes
   non-disabled and `aria-pressed` flips in response to backend
   acknowledgement, never on local click alone.
6. **Frontend dispatcher.** Header Manual button (currently disabled with
   Sprint 8 title) gains an `onClick` that dispatches typed `set_mode
   {mode: "manual"}`. LLM button likewise dispatches `set_mode {mode: "llm"}`.
   Mode buttons remain disabled during `executing` / `recovery` / `saving` /
   `loading` phases.
7. **Wired Manual builders.** `ManualActionBuilder` and
   `ManualAssertionBuilder` are imported into `frontend/src/v4/secondary-tabs.jsx`
   `StepsTab`, rendered only when `mode === "manual"` (from backend, not local
   state). Submits dispatch `manual_action_draft` / `manual_assertion_draft`
   via the typed dispatcher; no local `step_recorded` fabrication.
8. **No auto-LLM in Manual Mode.** When backend mode is `manual`, the LLM
   chat pipeline does not auto-fire on user input; user explicitly switches
   mode to invoke LLM.
9. **jsdom coverage.**
   - Mode toggle dispatches `set_mode` on enabled click; disabled states
     respected during run/recovery/save/load.
   - `mode_changed` reducer flips state and re-renders Manual UI gate.
   - `ManualActionBuilder` submit dispatches typed `manual_action_draft`.
   - `ManualAssertionBuilder` submit dispatches typed `manual_assertion_draft`.
   - No LLM chat dispatch fires while mode is `manual`.
10. **Backend pytest coverage.**
    - `tests/test_manual_mode_backend.py` (new): `set_mode` validation,
      `manual_action_draft` valid/invalid payloads, `manual_assertion_draft`
      valid/invalid payloads, mode change does not corrupt active run state,
      manual steps persist into the same recorded_step evidence bundle.
11. **Local-fixture E2E smoke.** One scenario, no paid LLM, no live website:
    user switches to Manual Mode → adds one click action → `step_recorded`
    arrives → Recorded tab shows entry. No fork of Recorder / Codegen.
12. **D-105 row** in `.tasks-md/Audit/UI_DEFECTS.md` is moved from CLOSED
    (DISABLED_WITH_REASON) back to OPEN-tracked or upgraded to a new CLOSED
    (WORKING_FOUNDATION) row referencing the Sprint 8 commit SHAs.

### Out of scope for BUG-S8-MANUAL-001

- Manual Mode replay/repair beyond the existing LLM-step replay/repair path
  (handled by Sprint 7 D-102 path; manual steps inherit it for free once they
  share the recorded-step bundle).
- New element picker UI; reuse `arm_picker` typed seam.
- Codegen fork; manual steps must serialize through the existing Codegen.

### File scope (estimate)

- `runtime/event_contracts.py` — add three typed command schemas, one event
- `server.py` — three handlers + one event emitter
- `runtime/recorder.py` (if needed) — confirm shared store, no fork
- `frontend/src/v4/chrome.jsx` — wire Manual button `onClick`, gate disabled
- `frontend/src/v4/secondary-tabs.jsx` — import and gate `ManualActionBuilder`
  / `ManualAssertionBuilder`
- `frontend/src/main.jsx` — `mode_changed` reducer + `set_mode` dispatcher
- `tests/test_manual_mode_backend.py` (new)
- `frontend/tests-dom/chrome.test.jsx` — extend (live dispatch path)
- `frontend/tests-dom/secondary-tabs.test.jsx` — extend (manual builder live)
- `frontend/tests-dom/panel-integration.test.jsx` — extend (full flow)
- `tests/e2e/local_fixture/test_manual_mode_smoke.py` (new local-only smoke)

### Architecture invariants (must hold)

- Backend owns runtime truth — no frontend-only mode mutation.
- No fake Manual Mode behaviour, no dead clickable controls.
- Same Step Runner / Recorder / Codegen path as LLM steps.
- No paid LLM in tests. No live website in tests.
