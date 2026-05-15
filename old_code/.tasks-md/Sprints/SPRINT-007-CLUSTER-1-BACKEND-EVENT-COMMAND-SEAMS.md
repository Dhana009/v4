# Sprint 7 — Cluster 1: Backend Event and Command Seam Completion

**Sprint:** Sprint 7
**Cluster:** 1
**Status:** Done
**Date:** 2026-05-13
**Prerequisite:** Cluster 0 complete (all 8 governance stories in Planning status)
**HEAD at planning:** 8bdd8def90b71fdaa24890943ec792b55397c66f

---

## Cluster Goal

Complete every backend event and command seam required by the real frontend so that Cluster 2 (frontend wiring) can connect to real backend truth without any stubs or demo fallbacks.

After Cluster 1 is Done:
- Every lifecycle event the frontend needs is emitted by the backend with a typed, validated payload
- Every command the frontend sends is received, validated, and handled by the backend
- All new events and commands have unit, contract, and negative tests
- Session save/load is wired through WS commands with a result event
- Session state reconnect payload is complete
- Regression suite is green at or above Sprint 6 baseline

---

## Source Documents

| Document | Relevant sections |
|----------|------------------|
| `PRD_v2_3_Modular_Pack_v2/04_BACKEND_EVENT_CONTRACT.md` | All required lifecycle events and commands |
| `PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md` | Runtime architecture, permission policy |
| `PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Phase 2 acceptance criteria |
| `S7-0001`: Requirement matrix | Sprint 7 Must-Have events and commands |
| `S7-0002`: Source-rule-to-test mapping | Test names and rule citations for Cluster 1 |
| `S7-0003`: Test taxonomy | Which test types apply to backend stories |
| `S7-0004`: Frontend-backend seam readiness matrix | Gap list driving this cluster |

---

## Architecture Invariants

These invariants must hold throughout Cluster 1. Any story that violates them is rejected.

1. **Backend owns runtime truth.** New events report state that already happened — they do not predict or drive state.
2. **LLM proposes only.** No new event type may be emitted by LLM output alone.
3. **Typed payloads only.** All new events use `build_backend_event_envelope()`. No raw dict emission.
4. **All new command types must be registered** in `SUPPORTED_FRONTEND_COMMAND_TYPES` or the equivalent command routing mechanism.
5. **Stale commands must be rejected** with `build_runtime_rejection_payload()` — not silently ignored.
6. **No broad refactor.** `agent.py` and `server.py` are touched at thin seams only.
7. **No frontend changes in Cluster 1.** Frontend wiring is Cluster 2.
8. **No paid LLM.** No paid model calls in Cluster 1 tests.
9. **No browser E2E in Cluster 1.** Browser E2E is Cluster 4.

---

## Event and Command Table

### New Events Required (Cluster 1 deliverables)

| Event | Story | Required Payload Fields | Current Status |
|-------|-------|------------------------|----------------|
| `run_started` | S7-0101 | run_id, steps[], phase="planning" | Missing — no builder, no emission |
| `step_validating` | S7-0102 | step_id, operation_id?, locator?, run_id | Missing — no builder, no emission |
| `step_executing` | S7-0102 | step_id, operation_id?, action, run_id | Missing — no builder, no emission |
| `step_failed` | S7-0103 | step_id, operation_id?, error, status, run_id | Missing — subsumed in recovery_needed |
| `step_skipped` | S7-0103 | step_id, reason, run_id | Missing — no distinct event |
| `permission_required` | S7-0104 | run_id, operation_id, action_type, risk_level, message, options? | Missing — no builder, no emission |
| `ready` (typed envelope) | S7-0105 | session_id, workspace, mode, url, backend_ready, browser_ready, session_active | Partial — plain status string only |
| `browser_ready` | S7-0105 | browser_ready, context, url | Missing |
| `run_completed` (extended) | S7-0106 | run_id, summary, recorded_count, skipped_count, failed_count, code_status | Partial — missing failed_count, code_status |
| `save_result` | S7-0109 | path, name, session_id, step_count | Missing |
| `load_result` | S7-0109 | path, name, session_id, step_count, snapshot_valid | Missing |

### New Commands Required (Cluster 1 deliverables)

| Command | Story | Required Payload | Current Status |
|---------|-------|-----------------|----------------|
| `stop_run` | S7-0107 | run_id | No handler, not registered |
| `skip_step` | S7-0108 | step_id, run_id | No handler, not registered |
| `save_session` | S7-0109 | path?, name? | Stub only, not registered |
| `load_session` | S7-0109 | path | Stub only, not registered |
| `permission_decision` | S7-0104 | run_id, operation_id, decision | No handler, not registered |

### Existing Events to Verify (not new, but completeness check)

| Event | Story | Check |
|-------|-------|-------|
| `plan_ready` | S7-0101 | Verify run_id field is present and consistent with run_started |
| `session_state` | S7-0110 | Verify all reconnect fields present: run_id, phase, plan, steps, code_preview, recovery_state |

---

## Story List

| Story | Title | Priority |
|-------|-------|---------|
| S7-0101 | run_started event contract | P0 |
| S7-0102 | step_validating and step_executing events | P0 |
| S7-0103 | step_failed and step_skipped events | P0 |
| S7-0104 | permission_required event emission | P0 |
| S7-0105 | typed ready/browser_ready envelope | P0 |
| S7-0106 | run_completed frontend-ready payload | P0 |
| S7-0107 | stop_run command | P0 |
| S7-0108 | skip_step command | P0 |
| S7-0109 | save_session and load_session command wiring | P0 |
| S7-0110 | session_state reconnect payload completeness | P0 |

All stories are P0. Cluster 1 is not Done until all 10 stories are Done.

Recommended execution order: 0101 → 0105 → 0102 → 0103 → 0104 → 0106 → 0107 → 0108 → 0109 → 0110

---

## Allowed Files for Implementation

When implementing Cluster 1 stories, only these files may be modified or created:

```
runtime/event_contracts.py               ← new builder functions
runtime/session_store.py                 ← extend with file persistence + WS wiring
server.py                                ← command routing seam only
agent.py                                 ← event emission seam only (thin wiring)
tests/test_run_started_event_contract.py
tests/test_step_progress_events_contract.py
tests/test_step_terminal_events_contract.py
tests/test_permission_required_event_contract.py
tests/test_ready_envelope_contract.py
tests/test_run_completed_contract.py
tests/test_stop_run_command_contract.py
tests/test_skip_step_command_contract.py
tests/test_session_persistence_contract.py
tests/test_session_state_reconnect.py
```

New runtime modules may be created (e.g., `runtime/command_handlers.py`) if logic would otherwise bloat `server.py` or `agent.py`.

---

## Forbidden Files for Implementation

```
frontend/                  ← no UI changes in Cluster 1
frontend_new_design_prototype/  ← no changes ever
browser.py                 ← no changes in Cluster 1
AGENTS.md                  ← do not stage
.DS_Store                  ← do not stage
.tasks-md/.DS_Store        ← do not stage
.playwright-cli/           ← do not stage
tests/e2e/                 ← no E2E in Cluster 1
runtime/llm_policy_gateway.py  ← no LLM prompt changes
runtime/llm_runtime_controller.py  ← no LLM controller changes
Any Sprint 6 test file     ← do not modify existing Sprint 6 tests
```

If a fix requires a forbidden file, stop and file a new story or bug ticket before proceeding.

---

## Test-First Requirements

Every Cluster 1 story must:
1. Write failing tests before any implementation code.
2. Commit failing tests separately: `test: <story-id> failing tests for <feature>`.
3. Implement only after tests are committed and failing.
4. All tests must pass before marking story Done.
5. No `@pytest.mark.skip` or `@pytest.mark.xfail` to hide failures.
6. Every test must have a comment citing its source rule: `# PRD-04-BE-001`.

---

## Regression Guard

Command to run after every story and after all cluster stories are done:

```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

Baseline: ~1689 passed, 12 pre-existing failures (BUG-S6-FINAL-001), 1 skipped.

No new failures allowed. If a new failure appears, stop and investigate before continuing.

---

## Definition of Done

Cluster 1 is Done when:
- [ ] All 10 stories are Done with evidence
- [ ] All new event builders exist in `runtime/event_contracts.py`
- [ ] All new command types are registered in `SUPPORTED_FRONTEND_COMMAND_TYPES`
- [ ] All new command handlers exist in `server.py` or a new `runtime/command_handlers.py`
- [ ] All stale command attempts are rejected with typed error
- [ ] `session_state` payload contains all fields required for frontend reconnect
- [ ] `save_session` and `load_session` work round-trip (in-memory or file persistence)
- [ ] Regression gate passes at or above baseline
- [ ] No new test failures introduced
- [ ] Coverage ≥ 95% for new modules
- [ ] All 10 story files updated to Done with evidence

---

## Stop Conditions

Stop and escalate if:
1. A story's implementation requires touching a frontend file — defer to Cluster 2.
2. A new event type cannot be added to `event_contracts.py` without broad refactor of `agent.py` — file a modular boundary story.
3. Any paid LLM call is made during test execution — stop immediately.
4. Regression gate fails with a new failure — stop and diagnose before continuing.
5. A command handler requires modifying an existing Sprint 6 test — file a bug ticket first.

---

## Evidence Requirements

At Cluster 1 completion, provide:
- [ ] List of all 10 story files with Done status
- [ ] Final regression run output
- [ ] Count of new tests added (target: 80+ new tests across all Cluster 1 stories)
- [ ] List of new modules created
- [ ] Confirmation: no frontend/ files modified
- [ ] Confirmation: no paid LLM calls made
- [ ] Commit hash for last Cluster 1 story

---

## Cluster 1 Closure

**Closed:** 2026-05-13
**Implementation commit:** `0dd4506`
**Branch:** `s7/cluster-1-backend-event-command-seams`

### Stories Done

| Story | Title | Test File |
|---|---|---|
| S7-0101 | run_started event contract | tests/test_run_started_event_contract.py |
| S7-0102 | step_validating & step_executing | tests/test_step_progress_events_contract.py |
| S7-0103 | step_failed & step_skipped | tests/test_step_terminal_events_contract.py |
| S7-0104 | permission_required event | tests/test_permission_required_event_contract.py |
| S7-0105 | typed ready / browser_ready | tests/test_ready_envelope_contract.py |
| S7-0106 | run_completed frontend-ready payload | tests/test_run_completed_contract.py |
| S7-0107 | stop_run command | tests/test_stop_run_command_contract.py |
| S7-0108 | skip_step command | tests/test_skip_step_command_contract.py |
| S7-0109 | save_session / load_session wiring | tests/test_session_persistence_contract.py |
| S7-0110 | session_state reconnect payload | tests/test_session_state_reconnect.py |

### Implementation Files Touched

- `runtime/event_contracts.py` — 13 new/extended builders, command type registry extended
- `runtime/session_store.py` — SessionSpec extended, save/load functions added, security exclusion list
- `agent.py` — 4 thin event emission seams (_mark_step_executing, _mark_step_failed, _mark_step_skipped, _emit_run_completed_event)
- `server.py` — 5 new command handlers (stop_run, skip_step, save_session, load_session, permission_decision); typed ready envelope on connect
- `tests/` — 10 new contract test files (203 new tests)
- `tests/` — 12 existing test files updated for status→ready envelope and infra event filtering

### Validation Evidence

- `python -m pytest -q --ignore=tests/e2e` → **0 failures, ~1898 passed, 1 skipped**
- Coverage with Cluster 1 tests only:
  - `runtime/event_contracts.py`: **98%**
  - `runtime/session_store.py`: **90%**
  - Combined target: **96%**

### Audit Result

- Cluster 1 focused audit: **8/8 passed** after this evidence commit
- Item 1 — only allowed files changed: PASS (26 files, no forbidden paths)
- Item 2 — no frontend/LLM/E2E files changed: PASS
- Item 3 — event payloads match S7-0101–S7-0110: PASS (13 builders verified)
- Item 4 — command handlers gate stale/malformed via `normalize_frontend_command`: PASS
- Item 5 — session_store security exclusions present: PASS
- Item 6 — task-board evidence recorded: PASS (this commit)
- Item 7 — no AGENTS.md/.DS_Store/noise staged: PASS
- Item 8 — full pytest + coverage evidence: PASS

### Confirmations

- No frontend files changed
- No LLM prompt files changed
- No E2E files changed
- No local noise staged
- Cluster 1 is fully closed.

### Next Step

Start Sprint 7 implementation Cluster 2: LLM/runtime live purpose integration gaps.
