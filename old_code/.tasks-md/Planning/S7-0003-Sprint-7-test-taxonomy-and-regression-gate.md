# S7-0003 — Sprint 7 Test Taxonomy and Regression Gate

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Define the complete Sprint 7 test taxonomy: what types of tests exist, what each type covers, where they live, and how they contribute to the regression gate. Establish the regression gate command that must pass after every cluster.

---

## Source Rules

- PRD `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`: Tests that must exist before calling LLM Mode MVP complete
- Sprint 7 Cluster 0 Governance: Test taxonomy and regression gate requirements
- Sprint 6 story S6-0002 (test strategy): Prior taxonomy as baseline

---

## Current Known Context

Sprint 6 ended with 1689 passing tests, 12 pre-existing tracked failures (BUG-S6-FINAL-001), and 1 skipped. The cheap regression suite uses:

```bash
python -m pytest -q
```

The 12 pre-existing failures are in:
- `tests/test_llm_planning_contracts.py` (4 failures)
- `tests/test_llm_specialist_contracts.py` (6 failures)
- `tests/test_llm_policy_gateway.py` (2 failures)

These are tracked but not fixed in Sprint 7 unless BUG-S6-FINAL-001 is explicitly scheduled. Sprint 7 must not introduce NEW failures.

No frontend test suite exists yet. Sprint 7 Cluster 2–3 will create frontend component and integration tests.

---

## Tests First

This is a documentation/policy story. No implementation tests required.

### Verification
- Taxonomy covers all test types needed for Cluster 1–4 stories
- Regression gate command is unambiguous
- Gate baseline is recorded before Cluster 1 implementation begins

---

## Test Taxonomy

### 1. Unit Tests

**Definition:** Test a single function or class method in isolation, pure inputs/outputs, no real I/O, no WS, no browser.

**Scope in Sprint 7:**
- Event builder functions in `runtime/event_contracts.py`
- Command validator functions
- Session store read/write logic
- Frontend reducer/state functions (pure JS functions)

**Naming convention:** `test_<function>_<scenario>()`

**Location:**
- Backend: `tests/test_<module_name>.py`
- Frontend: `frontend/tests/unit/test_<module>.js` or `*.test.js`

**Minimum count per story:** 3+ unit tests for each new builder/validator function.

---

### 2. Contract Tests

**Definition:** Test the interface boundary between two modules or between backend and frontend. Verify payload shapes, field presence, field types, and rejection behavior for invalid inputs.

**Scope in Sprint 7:**
- Event envelope contracts: `run_started`, `step_validating`, `step_executing`, `step_failed`, `step_skipped`, `permission_required`, `ready/browser_ready`, `run_completed`, `session_state`
- Command contracts: `stop_run`, `skip_step`, `save_session`, `load_session`
- Frontend receives event → state transition contract
- Frontend sends command → backend receives contract

**Naming convention:** `test_<event_or_command>_contract_<scenario>()`

**Location:** `tests/test_*_contract*.py`

**Required for all Cluster 1 stories.**

---

### 3. Reducer / Store Tests

**Definition:** Test frontend state reducer logic as pure functions. Input = current state + incoming event. Output = new state. No DOM, no WS.

**Scope in Sprint 7:**
- `run_started` → `planning` state
- `plan_ready` → `plan_review` state
- `step_executing` → `executing` state
- `recovery_needed` → `recovery` state
- `run_completed` → `completed` state
- `session_state` → full state restore

**Naming convention:** `test_reducer_<event>_<scenario>()`

**Location:** `frontend/tests/reducer/` or `tests/test_frontend_reducer*.py`

**Required for all Cluster 2 stories.**

---

### 4. Command Dispatcher Tests

**Definition:** Test frontend command dispatching: given a UI action, the correct typed command is sent with correct payload. No real WS.

**Scope in Sprint 7:**
- Stop Run button → `stop_run` command
- Skip Step button → `skip_step` with step_id
- Save Session → `save_session` with path/name
- Load Session → `load_session` with path
- Confirm Plan → `confirmed` with run_id
- Send Correction → `correction` with message, run_id

**Naming convention:** `test_dispatch_<command>_<scenario>()`

**Location:** `tests/test_command_dispatcher*.py` or frontend test files

**Required for all Cluster 2–3 stories.**

---

### 5. Integration Tests

**Definition:** Multi-module interaction test without real browser or real LLM. Covers event emission through the event seam into a mock WS sink, or command receipt through the command router to the target handler.

**Scope in Sprint 7:**
- Event emission sequence: `run_started` → `step_validating` → `step_executing` → `step_recorded` → `run_completed`
- Command routing: `stop_run` → active run cancelled → typed event emitted
- Session save/load round-trip through `session_store.py`

**Naming convention:** `test_integration_<flow>_<scenario>()`

**Location:** `tests/test_*_integration*.py`

**Required for at least one story per cluster.**

---

### 6. Frontend Component Tests

**Definition:** Test that a frontend component renders correctly given typed backend event data. No real WS or backend. Uses fixture event payloads.

**Scope in Sprint 7:**
- LLM tab renders plan from `plan_ready` payload
- Steps tab renders executing steps from `step_executing` payload
- Recovery card renders from `recovery_needed` payload
- Completed summary from `run_completed` payload
- Session state restore renders from `session_state` payload

**Naming convention:** `test_<component>_renders_<event>_<scenario>()`

**Location:** `frontend/tests/components/` or inline component test files

**Required for all Cluster 3 stories.**

---

### 7. Shadow DOM / Browser Tests

**Definition:** Test that components behave correctly inside the Shadow DOM container. Requires a headless browser environment.

**Scope in Sprint 7:**
- Shadow DOM host mounts correctly
- CSS isolation does not break component layout
- Event listeners work inside Shadow DOM boundary

**Location:** `frontend/tests/browser/` or `tests/e2e/test_shadow_dom*.py`

**Required only in Cluster 4. Not required in Clusters 0–3.**

---

### 8. Local Fake-LLM E2E Tests

**Definition:** Full backend + real frontend + local browser, but with fixture/fake LLM responses. Proves the end-to-end flow without paid model calls.

**Scope in Sprint 7:**
- LLM Mode smoke: submit steps → `run_started` → `plan_ready` → confirm → `step_executing` → `step_recorded` → `run_completed`
- Recovery smoke: step fails → `recovery_needed` → correction → recovery resolves
- Stop run smoke: run active → `stop_run` command → run halted

**Naming convention:** `test_e2e_smoke_<flow>()`

**Location:** `tests/e2e/test_llm_mode_smoke.py`

**Required only in Cluster 4. Not required in Clusters 0–3.**

---

### 9. Regression Guard

**Definition:** The subset of tests that must pass after every Sprint 7 cluster commit. Includes all Sprint 6 tests that were passing, plus all new Sprint 7 tests.

**Command:**
```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -10
```

**Baseline:** 1689 passing, 12 pre-existing failures (BUG-S6-FINAL-001), 1 skipped.

**Gate rule:** Any new test failure introduced by Sprint 7 work is a blocker. Do not merge a cluster until the gate passes at or above baseline.

**Regression guard file:** `.tasks-md/Testing/S7-REGRESSION-GUARD.md` (to be created in Cluster 1 implementation phase)

---

### 10. Paid E2E Gate

**Definition:** Real LLM model + real browser + real or staging site. Only after Sprint 7 local proof is complete.

**Scope:** Sprint 8 only.

**Sprint 7 policy:** Zero paid E2E calls. If a paid call is triggered accidentally, stop and investigate before continuing.

---

## Pre-Cluster Baseline Capture

Before Cluster 1 implementation begins, run and record this baseline:

```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

Expected output (approximate):
```
1689 passed, 1 skipped, 12 failed
```

Record the exact output in `.tasks-md/Testing/S7-REGRESSION-GUARD.md`.

---

## Test File Naming Conventions

| Story cluster | File pattern |
|---------------|-------------|
| Backend events | `tests/test_<event_name>_event_contract.py` |
| Backend commands | `tests/test_<command_name>_command_contract.py` |
| Session/state | `tests/test_session_*.py` |
| Frontend reducers | `tests/test_frontend_reducer*.py` or `frontend/tests/` |
| Frontend components | `frontend/tests/components/` |
| Integration | `tests/test_*_integration*.py` |
| E2E | `tests/e2e/test_*.py` |

---

## Implementation Boundaries

This is a documentation/policy story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0003-Sprint-7-test-taxonomy-and-regression-gate.md` (this file)

---

## Forbidden Files

- No product code changes
- No test file changes (the `.tasks-md/Testing/S7-REGRESSION-GUARD.md` is created at Cluster 1 start, not here)
- No runtime/ changes
- No frontend/ changes

---

## Acceptance Criteria

- [ ] All 10 test types are defined with scope, naming, and location
- [ ] Regression gate command is unambiguous
- [ ] Baseline capture protocol is documented
- [ ] Paid E2E gate is clearly deferred to Sprint 8
- [ ] Test taxonomy is referenced by all Cluster 1–4 story files

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`

---

## Stop Conditions

- Regression gate baseline cannot be captured (pytest broken) — fix before starting Cluster 1
- New test type is needed that is not in this taxonomy — update this file first
