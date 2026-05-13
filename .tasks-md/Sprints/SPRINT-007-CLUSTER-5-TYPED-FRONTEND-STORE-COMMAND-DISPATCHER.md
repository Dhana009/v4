# Sprint 7 — Cluster 5: Typed Frontend Event Store + Command Dispatcher

**Sprint:** Sprint 7  
**Cluster:** 5  
**Status:** Planning  
**Date:** 2026-05-13  
**HEAD at planning:** 8bdd8de  

---

## Cluster 5 Goal

Make frontend state real and backend-event driven. Move from partial/inline state management to a typed event store and command dispatcher that consume backend events and send typed commands back. After Cluster 5, the frontend renders backend truth (not inferred state, not demo content), and all user actions become typed backend commands.

This cluster **closes BUG-S6-FINAL-002** by threading live backend state into IDEPanel components.

---

## Current State Audit

### Frontend State Today

- WebSocket transport exists in `frontend/src/main.jsx` (1000+ lines)
- `IDEPanel` component receives some props (plan, steps, etc.)
- No typed event model definition
- No frontend-owned reducer or event store
- State partially inline, partially as props
- No command dispatcher; commands likely sent as loose strings
- Static demo/fallback content may appear in live mode
- No session_state consumer (reconnect logic missing)
- Run completion logic not wired to backend events
- Step lifecycle rendering decoupled from backend events

### Known Gaps

1. **No typed event model** — events from backend not typed in frontend
2. **No reducer pattern** — state transitions not explicit
3. **No command dispatcher** — commands not validated before sending
4. **State not event-driven** — props set directly instead of through reducer
5. **Demo fallback in live** — static content may appear when backend event expected
6. **Stale command risk** — no validation that command matches current run_id/plan_id
7. **Session reconnect missing** — frontend has no way to consume session_state
8. **No negative state** — invalid/unknown events may cause UI crash
9. **Permission/recovery/recommendation not wired** — events exist but UI doesn't consume them

### Known Issues

- BUG-S6-FINAL-002: Frontend is contract-only; no real state management
- main.jsx monolith makes testing difficult
- Transport layer mixed with state layer mixed with rendering

---

## Source Rules (Priority Order)

1. **PRD v2.3** — `04_BACKEND_EVENT_CONTRACT.md` — backend event taxonomy
2. **Frontend UI Spec** — `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — interaction modes
3. **Sprint 7 Cluster 0** — architecture rules: backend owns truth, frontend renders events
4. **Sprint 6 Handoff** — BUG-S6-FINAL-002, state gaps
5. **Event taxonomy** — `.tasks-md/Sprints/SPRINT-007-CLUSTER-2-LLM-RUNTIME-LIVE-INTEGRATION-GAPS.md`

---

## Frontend Event Model

Events expected from backend (Cluster 2/3 will emit):

| Event | Payload | Frontend use |
|-------|---------|---|
| `session_state` | complete run/plan/steps/recorded/code state | restore UI on reconnect |
| `run_started` | run_id, timestamp | set mode to "planning" |
| `plan_ready` | plan_id, plan dict, timestamp | show plan for review |
| `clarification_needed` | question_id, question text, options[], target_step | show clarification card |
| `recommendation_ready` | recommendations[] with labels | show recommendation cards |
| `permission_required` | operation, risk_level, reason | show permission card |
| `step_validating` | step_id, operation_id | update step UI state |
| `step_executing` | step_id, operation_id | update step UI state |
| `step_failed` | step_id, failure_reason, failure_context | show failure state |
| `step_skipped` | step_id, reason | show skipped state |
| `step_recorded` | step_id, recorded_step dict | add to recorded steps |
| `recovery_needed` | step_id, failure_reason, options[] | show recovery card |
| `recovery_resolved` | step_id, action_taken | clear recovery state |
| `code_update` | code_dict, timestamp | update code preview |
| `replay_started` | operation_id, timestamp | show replay progress |
| `replay_result` | step_id, outcome, diff | show replay result |
| `run_completed` | summary, duration, success | show completion state |
| `runtime_rejected` | error_type, error_message | show error state |
| `trace_export` | trace_dict | populate trace tab |
| `plan_diff_proposed` | diff_operations[] | show diff preview |
| `plan_diff_validated` | validation_result | show validation state |
| `plan_diff_applied` | result | confirm application |

---

## Frontend Command Model

Commands sent to backend (Cluster 2/3 must validate):

| Command | Payload | Backend validation |
|---------|---------|---|
| `user_message` | run_id, message_text | require active run |
| `answer_clarification` | run_id, question_id, answer | require pending clarification |
| `accept_recommendations` | run_id, selected_recs[] | require pending recommendations |
| `confirm_plan` | run_id, plan_id, plan_version | require plan_ready state |
| `correction` | run_id, plan_id, correction_text | require planning state |
| `apply_plan_diff` | run_id, plan_id, diff_id, operations[] | require diff pending |
| `reject_plan_diff` | run_id, plan_id, diff_id | require diff pending |
| `permission_decision` | run_id, operation, decision (allow/deny) | require permission pending |
| `choose_locator_candidate` | step_id, candidate_id | require locator_ambiguous state |
| `retry_recovery` | step_id, recovery_action | require recovery_needed |
| `skip_step` | run_id, step_id | require executing state |
| `stop_run` | run_id | require active run |
| `run_steps` | step_ids[], mode | require steps available |
| `replay_one` | run_id, step_id | require completed state |
| `replay_all` | run_id | require completed state |
| `save_session` | run_id, session_name, metadata | require completed state |
| `load_session` | session_id | require idle state |
| `arm_picker` | run_id, step_id, target_type | require steps mode |
| `request_trace_export` | run_id, filter_options | require active run |

---

## Frontend State Shape

```typescript
interface FrontendState {
  // Connection
  connected: boolean;
  transport_url: string;
  
  // Run/session
  run_id: string | null;
  session_id: string | null;
  phase: string; // idle | planning | executing | recovery | completed
  
  // Plan/steps
  plan_id: string | null;
  plan_version: number;
  plan: object | null;
  pending_steps: object[];
  recorded_steps: object[];
  
  // Live execution state
  executing_step_id: string | null;
  executing_operation_id: string | null;
  
  // Decision states
  pending_clarification: object | null;
  pending_recommendations: object[];
  pending_permission: object | null;
  pending_recovery: object | null;
  pending_diff: object | null;
  
  // Results
  code_preview: string | null;
  trace_entries: object[];
  errors: object[];
  
  // UI mode
  interaction_mode: string; // idle | planning | plan_review | clarification | executing | recovery | completed
  
  // Non-inference rules
  // Frontend must NOT infer: completion status, recording confirmation, code generation success
  // These come from backend events ONLY
}
```

---

## Store Architecture

### Reducer Pattern

```
event → reducer → new_state

Example:
{
  type: 'plan_ready',
  payload: { plan_id, plan, timestamp }
} → { ...state, plan_id, plan, interaction_mode: 'plan_review' }
```

### Event Consumer

- Receive typed backend events
- Validate against event schema
- Pass to reducer
- Emit new state to components

### Command Dispatcher

- Receive command from component
- Validate: required IDs present, state allows command
- Serialize to JSON
- Send via WebSocket
- Do NOT wait for response (backend will emit event)

---

## Story List

| Story | Title |
|-------|-------|
| S7-0501 | Typed frontend event model |
| S7-0502 | Frontend reducer and event store |
| S7-0503 | Session_state consumer and reconnect restore |
| S7-0504 | Run_completed, runtime_rejected, and error handlers |
| S7-0505 | Step lifecycle event handlers |
| S7-0506 | Permission, recommendation, and recovery event handlers |
| S7-0507 | Typed command dispatcher |
| S7-0508 | Stale, missing ID, and disabled command blocking |
| S7-0509 | Live prop threading into IDEPanel |

---

## Implementation Scope

### Allowed Files for Future Implementation

- `frontend/src/store/**` — Event store module
- `frontend/src/transport/**` — WebSocket transport wrapper
- `frontend/src/commands/**` — Command dispatcher module
- `frontend/src/hooks/**` — React hooks for store access
- `frontend/src/components/**` — Component directory (placeholder)
- `frontend/src/main.jsx` — **thin wiring only; no state logic**
- `frontend/src/aw-ide-panel.jsx` — **prop threading only; no state logic**
- `tests/test_frontend_event_store*.py` — Event store tests
- `tests/test_frontend_command_dispatcher*.py` — Command dispatcher tests
- `tests/test_frontend_event_command_contract.py` — Contract tests
- `tests/test_frontend_recorded_code_rendering.py` — Component render tests

### Forbidden Files

- No backend/ or runtime/ implementation in Cluster 5
- No LLM purpose implementation
- No product code copied directly from `frontend_new_design_prototype/`
- No broad refactor of `aw-ide-panel.jsx` — prop threading only
- No monolith growth in main.jsx

---

## Architecture Rules

1. **Event sourcing pattern** — all state changes caused by backend events
2. **Reducer pure** — state transitions are pure functions
3. **No inference** — frontend does not guess completion/recording/code success
4. **Typed commands** — all commands validated before sending
5. **Stale ID blocking** — commands with old/wrong run_id rejected
6. **Demo fallback removed** — no static content in live mode
7. **Modular structure** — store, transport, dispatcher in separate modules
8. **No main.jsx bloat** — wiring only, logic in focused modules

---

## Tests-First Requirements

### Test Taxonomy for Cluster 5

| Test type | Purpose | Where | Required per story |
|---|---|---|---|
| **Unit** | Single reducer function behavior | `tests/test_store_*.py` | Required for all reducers |
| **Contract** | Event/command payload shapes | `tests/test_*_contract.py` | Required for all events/commands |
| **Integration** | Event → reducer → state → component | `tests/test_store_integration.py` | Required for event sequences |
| **Negative** | Unknown event, stale ID, missing payload | `tests/test_store_negative.py` | Required for all handlers |
| **Component** | Component render against typed state | frontend test suite | Required for prop threading |
| **Regression** | No Sprint 6 breakage | `tests/test_sprint7_regression_guard.py` | Run after every commit |

### Negative Tests Required

Every story must include:
- Unknown event type (safe handling)
- Stale/missing run_id in command
- Missing required payload field
- Conflicting state transition (e.g., step failed but code shows success)
- Command sent in wrong state (e.g., confirm without plan)
- Session state overwrite protocol
- Empty/null field handling

### Regression Guard

```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

Must stay at baseline (1689 passed, 1 skipped, 12 pre-existing failures).

---

## Definition of Done

A Cluster 5 story is **Done** when:

1. ✅ All tests from `Tests First` section exist and are green
2. ✅ Implementation code committed (separate commit from tests)
3. ✅ Event/command types exported and typed
4. ✅ Reducer functions pure and testable
5. ✅ Negative tests pass (unknown event, stale ID, etc.)
6. ✅ Regression guard suite still green (baseline maintained)
7. ✅ Story file updated with evidence (test file names, commit hashes)
8. ✅ IDEPanel props correctly threaded from store
9. ✅ No static demo content in live mode
10. ✅ Command validation prevents invalid commands sending

---

## Evidence Required

Before moving story to **Done**:

1. **Test evidence** — test file names and green test output
2. **Implementation evidence** — commit hash(es) of implementation
3. **Regression evidence** — output of `python -m pytest -q` showing baseline maintained
4. **Type exports** — confirm types available to other modules
5. **No inference** — grep confirms no frontend completion guessing
6. **No monolith** — confirm main.jsx and aw-ide-panel.jsx changes are wiring only

---

## Stop Conditions

**Stop and escalate if:**

1. ❌ Regression suite breaks (any new test failure in baseline)
2. ❌ Event contract differs from Cluster 2 event spec
3. ❌ Command sent without required run_id validation
4. ❌ Frontend infers completion/recording/code success without backend event
5. ❌ Unknown event type causes UI crash (not safe handling)
6. ❌ Static demo content appears in live mode
7. ❌ main.jsx grows beyond thin wiring
8. ❌ Type system not enforced at module boundaries

---

## Acceptance Criteria

After all Cluster 5 stories are **Done**:

1. **All 9 stories green** — All unit, integration, component tests passing
2. **Regression suite green** — 1689+ tests passing, pre-existing 12 failures stable
3. **Event types exported** — all event types importable by components
4. **Command types exported** — all command types importable by dispatcher
5. **Reducer correct** — state transitions match backend event sequence
6. **Store testable** — all reducer functions pure, decoupled from React
7. **No inference** — frontend does not guess lifecycle state
8. **Commands validated** — dispatcher blocks invalid commands before send
9. **IDEPanel wired** — all required props threaded from store
10. **Demo removed** — no static fallback in live mode

---

## Known Risks

1. **State explosion** — too many state fields makes reducer complex; modular substores may help.
2. **Event storm** — fast event sequence may cause render thrashing; debounce/batch events.
3. **Type mismatch** — if Cluster 2 event changes signature, Cluster 5 breaks.
4. **Frontend race** — command sent, but backend hasn't emitted corresponding event yet; UI may show stale state.
5. **Session restore complexity** — session_state must merge with current state correctly; must not duplicate records.

---

## Next Planning Task

After Cluster 5 is **Done**:
→ Move to **Cluster 6 and Cluster 7** implementation planning (LLM tab and Steps tab UI)

---

## Related Files and References

- `.tasks-md/Planning/S7-0501-Typed-frontend-event-model.md`
- `.tasks-md/Planning/S7-0502-Frontend-reducer-and-event-store.md`
- `.tasks-md/Planning/S7-0503-Session-state-consumer-and-reconnect-restore.md`
- `.tasks-md/Planning/S7-0504-Run-completed-runtime-rejected-and-error-handlers.md`
- `.tasks-md/Planning/S7-0505-Step-lifecycle-event-handlers.md`
- `.tasks-md/Planning/S7-0506-Permission-recommendation-and-recovery-event-handlers.md`
- `.tasks-md/Planning/S7-0507-Typed-command-dispatcher.md`
- `.tasks-md/Planning/S7-0508-Stale-missing-id-and-disabled-command-blocking.md`
- `.tasks-md/Planning/S7-0509-Live-prop-threading-into-IDEPanel.md`
- `PRD_v2_3_Modular_Pack_v2/04_BACKEND_EVENT_CONTRACT.md` — event taxonomy
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — UI spec
- `.tasks-md/Bugs/Backlog/BUG-S6-FINAL-002-frontend-complete-llm-ui-contract-only.md` — context
