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

---

## BUG-S8-E2E-001 — Migrate legacy flow E2E tests to v4 testid contract

**Filed by:** Sprint 7 Wrap-Up Batch D (final E2E run at HEAD `45071df`).
**Status:** OPEN (scope reduced 2026-05-14 — see addendum below).
**Supersedes:** BUG-S7-V4-001 (same scope; widened to all 5 legacy flow tests).

### 2026-05-14 update — post-routing-fix state

The Sprint 7 final routing fix (harness alias `workbench → aw-tab-steps`,
auto-switch to LLM on `plan_ready`, NowStrip onPrimary state guard widened,
dead `run_steps` inline envelope removed) unblocked the first half of the
chain. As of the final E2E run on this branch:

- `basic_click_flow` reaches `execution_started` (was failing at
  `run_clicked`). It now fails on the recorded-step locator inside the
  panel body — needs a `click_autoworkbench_tab(page, "recorded")` call
  before reading `.ide-recorded-step`, then a `recorded-row-*` testid
  switch.
- `visible_assertion_flow` reaches `execution_started` (was failing at
  `pending_step_added`).
- `exact_text_assertion_flow` still fails at the pending-step ready-badge
  selector (`.ide-step-topline .ide-badge.b-ready`) — selector-only fix.
- `correction_assert_then_click_flow` still fails at the plan-child
  count assertion — selector-only fix.
- `llm_required_ambiguous_action_flow` reaches LLM (2 calls fired,
  `llm_triggered=true`); fails on the `.ide-clarification-question`
  legacy class — selector-only fix.

All five failures are now pure selector drift; no remaining routing or
product bugs in scope for Sprint 7.
**PRD/contract references:** `.tasks-md/Audit/V4_TESTID_CONTRACT.md`,
`SPRINT-007-WRAP-UP-MASTER-SPEC.md §10`.

### Failing tests at Sprint 7 close

All 5 tests below time out on legacy selectors that no longer exist in the v4
panel. Backend, websocket, picker, and element-pick stages all succeed —
this is **pure selector drift**, not a product regression. The smoke gate
(`test_v4_panel_smoke.py`, `test_mvp_001_lifecycle_smoke.py`) which already
uses v4 testids is green.

| Test | Last green stage | First failing selector | Classification |
|---|---|---|---|
| `tests/e2e/test_basic_click_flow.py` | `pending_step_added` | `get_by_role("button", name="Run Pending Steps")` | SELECTOR_DRIFT |
| `tests/e2e/test_exact_text_assertion_flow.py` | `exact_text_element_picked` | `.ide-step-topline .ide-badge.b-ready` | SELECTOR_DRIFT |
| `tests/e2e/test_visible_assertion_flow.py` | `visible_assertion_pending_step_added` | `get_by_role("button", name="Run Pending Steps")` | SELECTOR_DRIFT |
| `tests/e2e/test_correction_assert_then_click_flow.py` | `pending_step_added` | `get_by_role("button", name="Run Pending Steps")` | SELECTOR_DRIFT |
| `tests/e2e/test_llm_required_ambiguous_action_flow.py` | `pending_step_added` | `get_by_role("button", name="Run Pending Steps")` | SELECTOR_DRIFT |

### Legacy → v4 selector mapping (use `V4_TESTID_CONTRACT.md`)

| Legacy selector | v4 replacement |
|---|---|
| `get_by_role("button", name="Run Pending Steps")` | `[data-testid="steps-run-all"]` |
| `.ide-step-topline .ide-badge.b-ready` | `[data-testid^="aw-step-row-"] [data-testid^="step-kind-"]` (or status-ready signal) |
| `.ide-step-input` | `[data-testid^="step-input-"]` |
| `.ide-step-outcome` | `[data-testid^="step-outcome-chip-"]` |
| `.ide-step-target-summary` | per-row target summary inside `aw-step-row-${id}` |
| `get_by_role("button", name="Attach Element")` | `[data-testid^="step-attach-"]` |
| `get_by_role("button", name="Click page element…")` | picker armed indicator (verify against `chrome.jsx`) |
| `get_by_role("button", name="Confirm Plan")` | `[data-testid="plan-confirm"]` |
| `get_by_role("button", name="Send Correction")` | `[data-testid="plan-edit"]` → correction composer |
| `.ide-card` filter "// plan review" | `[data-testid="card-plan-ready"]` / `[data-testid="card-plan-diff"]` |
| `.ide-clarification-question` | `[data-testid="clarification-question"]` (verify in `llm-cards.jsx`) |
| `.ide-recorded-step` | `[data-testid^="recorded-row-"]` |
| `.ide-recorded-step-title` | per-row title inside `recorded-row-${id}` |
| `.ide-plan-child-desc` | `[data-testid^="step-child-label-"]` / `[data-testid^="recorded-child-"]` |
| `.ide-stat-num` | footer/count badge — verify in `chrome.jsx` |

### Acceptance criteria

1. Each of the 5 tests passes locally at the Sprint 8 baseline HEAD against
   the v4 panel using local fixtures + fake LLM (no paid LLM, no live web).
2. No assertion is weakened. Replays, recordings, child-op counts, and
   clarification flows are still asserted in full.
3. Selectors must target `data-testid` per V4_TESTID_CONTRACT.md. Class
   selectors `ide-*` may not be reintroduced.
4. If a legacy test asserts behavior that the v4 + backend pipeline does
   not yet produce (real product gap), that gap is split off as a separate
   product ticket — do **not** weaken the assertion or skip the test.
5. Update `.tasks-md/Audit/V4_TESTID_CONTRACT.md §10` mapping table with
   any new aliases added during migration.

### Out of scope

- Adding new product behavior to make a test green. Any real product gap
  becomes a separate ticket.
- Changing the v4 panel testid contract. The contract is frozen; tests
  migrate to it.

### Architecture invariants (must hold)

- No assertion weakening.
- No selector based on incidental CSS class.
- No live website / no paid LLM in tests.
- Tests fail closed on missing payload, not by waiting for legacy markup.
