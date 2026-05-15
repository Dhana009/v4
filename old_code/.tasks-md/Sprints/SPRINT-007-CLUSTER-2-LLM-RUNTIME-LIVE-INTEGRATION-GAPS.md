# Sprint 7 — Cluster 2: LLM/Runtime Live Integration Gaps

**Sprint:** Sprint 7  
**Cluster:** 2  
**Status:** Done  
**Date:** 2026-05-13  
**HEAD at planning:** 8bdd8de  

---

## Cluster 2 Goal

Make backend/LLM/runtime signals visible, typed, and safe for the real frontend to render and interact with. This cluster does **not** change LLM ownership of runtime truth. It does **not** execute browser actions. It does **not** add frontend UI. It makes backend signals explicit and frontend-visible.

After Cluster 2, every major LLM purpose and flow should emit frontend-visible typed events that the frontend can render without inference.

---

## Current State Audit

### LLM/Runtime Integration Status

| Purpose | Current | Blockers | Frontend-visible? | Event pipeline? |
|---------|---------|----------|-------------------|-----------------|
| page_intelligence_summarizer | Fake packet only | No live invocation boundary | No | page_summary_ready exists but is not emitted live |
| page_validation_recommender | Partial/test-only | No frontend payload shape | No | Recommendation contract exists but payload not aligned |
| locator_specialist | Implemented | Ambiguity not frontend-visible | Partial | Candidate list exists but scope/risk not explicit |
| recovery_diagnoser | Implemented | Recovery options not structured for UI | Partial | Event exists but payload gaps |
| plan_diff_editor | Implemented | Diff operations not frontend-aligned | No | No plan_diff_* events |
| capability_gap | Policy-only | Not emitted as events | No | capability_gap event missing |
| token/telemetry | Collected | Not exposed to frontend | No | Telemetry events exist but UI contract undefined |
| Error/fail-closed | Partial | Schema errors not visible to frontend | Partial | runtime_rejected exists but error payload structure unclear |

### Known Gaps

1. **Page Intelligence boundary unclear** — fake packet path mixes with live invocation.
2. **Recommendations not pipeline events** — exist in controller but not emitted as `recommendation_ready`.
3. **Locator ambiguity structure unclear** — candidates exist but frontend-facing payload lacks scope, risk, stability info.
4. **Recovery options not explicit** — recovery_diagnoser output not structured for UI card.
5. **Plan diff not visible** — corrections computed but not emitted as typed events.
6. **Capability gaps silent** — unsupported actions fail or fake success instead of emitting capability_gap event.
7. **Token/cost/telemetry hidden** — model usage exists internally but not exposed to frontend via events.
8. **Error payload unclear** — schema retry exhaustion and provider errors not consistently visible.

---

## Source Rules (Priority Order)

1. **PRD v2.3** — `PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md`, `04_BACKEND_EVENT_CONTRACT.md`
2. **Frontend UI Spec** — `autoworkbench_complete_llm_mode_frontend_ui_spec.md`
3. **Sprint 6 Handoff** — `.tasks-md/Sprints/SPRINT-006-HANDOFF.md` (Clusters 1–3 completeness)
4. **Sprint 7 Governance** — `.tasks-md/Sprints/SPRINT-007-CLUSTER-0-GOVERNANCE.md` (TDD, stop conditions, modularization)
5. **Backend Event Contract** — `.tasks-md/Sprints/SPRINT-006-CLUSTER-0-GOVERNANCE.md` (event taxonomy, payload rules)

---

## LLM/Runtime Purpose Clarity Table

| Purpose ID | LLM Model | Context Level | Output Form | Frontend needs | Sprint 7 Cluster 2 work |
|---|---|---|---|---|---|
| page_intelligence_summarizer | cheap | compact | PageIntelligenceSchema | page_summary_ready event with live/fake boundary | S7-0201 |
| page_validation_recommender | main | compact | RecommendationOutput | recommendation_ready event with user-facing payload | S7-0202 |
| — | — | — | — | page_analysis_started, page_summary_ready explicit events | S7-0203 |
| plan_diff_editor | main | compact | PlanDiffOutput | plan_diff_proposed, plan_diff_validated, plan_diff_applied events | S7-0204 |
| locator_specialist | main | compact | LocatorCandidateList | candidate_id, semantic_label, scope, risk, preview, confidence | S7-0205 |
| recovery_diagnoser | main | compact | RecoveryOption[] | recovery_needed event with options (retry/skip/stop) | S7-0206 |
| — | — | — | — | token_report, cost_summary, model_class, purpose telemetry | S7-0207 |
| — | — | — | — | capability_gap event with unsupported_action, reason, next_legal_action | S7-0208 |
| — | — | — | — | schema_error, provider_error, malformed_output fail-closed events | S7-0209 |

---

## Event/Payload Alignment Table

| Event | Payload | Frontend use | Current status | Sprint 7 action |
|---|---|---|---|---|
| page_analysis_started | request_id, page_url, section | Show "analyzing..." state | Missing | S7-0203 |
| page_summary_ready | request_id, page_summary, timestamp | Show page summary | Partial; emitted but not live | S7-0203 |
| recommendation_ready | request_id, recommendations[], timestamp | Show recommendation cards | Partial; exists as type, not event | S7-0202 |
| plan_diff_proposed | plan_id, old_version, new_version, operations[] | Show diff preview | Missing | S7-0204 |
| plan_diff_validated | plan_id, validation_result | Show diff status | Missing | S7-0204 |
| plan_diff_applied | plan_id, result | Confirm application | Missing | S7-0204 |
| locator_candidates_ready | ambiguity_id, candidates[{id, label, scope, risk, locator, confidence}] | Show candidate card | Partial; structure unclear | S7-0205 |
| recovery_needed | step_id, failure_reason, expected, actual, options[{id, label, action}] | Show recovery card | Partial; options not explicit | S7-0206 |
| token_report | purpose, model_class, input_tokens, output_tokens, estimated_cost | Show token summary | Exists internally; not exposed | S7-0207 |
| capability_gap | action, reason, next_legal_action | Show "not supported" card | Not emitted | S7-0208 |
| schema_error | error_type, message, retry_count, max_retries | Show error state | Partial | S7-0209 |
| provider_error | error_type, message, retryable | Show provider error | Partial | S7-0209 |

---

## Frontend Dependency Table

| Frontend surface | Depends on Cluster 2 | Required event(s) | Status |
|---|---|---|---|
| LLM tab — planning phase | page_intelligence_summarizer live boundary | page_analysis_started, page_summary_ready | S7-0201, S7-0203 |
| LLM tab — plan review cards | recommendation_ready pipeline | recommendation_ready event | S7-0202 |
| LLM tab — correction discussion | plan_diff events | plan_diff_proposed, plan_diff_validated | S7-0204 |
| Steps tab — element picker | locator_specialist payloads | locator_candidates_ready with structure | S7-0205 |
| Recovery card | recovery_diagnoser options | recovery_needed with options[] | S7-0206 |
| Token/cost summary | telemetry payloads | token_report event | S7-0207 |
| Error states | fail-closed events | capability_gap, schema_error, provider_error | S7-0208, S7-0209 |
| Trace tab | all telemetry, errors | All events with complete payloads | S7-0207, S7-0209 |

---

## Story List

### Cluster 2 Stories (9 total)

1. **S7-0201** — Page Intelligence live invocation boundary
2. **S7-0202** — recommendation_ready backend event pipeline  
3. **S7-0203** — page_analysis_started and page_summary_ready events
4. **S7-0204** — plan_diff event naming and payload alignment
5. **S7-0205** — locator_specialist frontend-facing payload alignment
6. **S7-0206** — recovery_diagnoser frontend-facing payload alignment
7. **S7-0207** — token/telemetry event payloads for UI
8. **S7-0208** — capability_gap frontend-facing contract
9. **S7-0209** — fail-closed schema and error events visible to frontend

---

## Implementation Scope

### Allowed Files

Runtime/backend:
- `runtime/page_intelligence_schema.py` — Page Intelligence lean schema
- `runtime/page_intelligence_live.py` (new if needed) — Live invocation boundary
- `runtime/page_intelligence.py` — Current packet builder
- `runtime/recommendation_events.py` — Event types (expand as needed)
- `runtime/recommendation_state.py` — Recommendation state management
- `runtime/recommendation_contracts.py` — Recommendation validation
- `runtime/llm_runtime_controller.py` — Event emission seams
- `runtime/event_contracts.py` — Event payload shapes
- `runtime/telemetry.py` — Telemetry collection and exposure
- `runtime/capability_registry.py` (new if needed) — Unsupported capability mapping
- `runtime/error_events.py` (new if needed) — Fail-closed error event types
- `agent.py` — Thin orchestration only; event emission seams only
- `server.py` or `ws/router.py` — Event transport
- `tests/test_page_intelligence*.py` — Page Intelligence tests
- `tests/test_llm_runtime*.py` — LLM runtime tests
- `tests/test_backend_event*.py` — Event contract tests
- `tests/test_recommendation*.py` — Recommendation event tests
- `tests/test_telemetry*.py` — Telemetry exposure tests

### Forbidden Files

- `frontend/**` — No frontend UI
- `browser.py` — No browser action
- Broad refactors of `agent.py` — Thin seams only
- Paid LLM calls by default — Fake-LLM only unless explicit gate
- `frontend_new_design_prototype/` — Reference only; do not modify

---

## Architecture Rules (Cluster 2 specific)

1. **Backend owns runtime truth** — No LLM signal overrides backend lifecycle.
2. **LLM proposes only** — Recommendations, candidates, and recovery options are advisory.
3. **Frontend-visible state is typed** — Every event payload must match a contract schema.
4. **No raw full DOM** — Page Intelligence and candidates summarize, never expose raw markup.
5. **Live invocation boundary clear** — Fake path and live path are explicit; frontend knows which is which.
6. **Fail-closed on errors** — Schema errors, provider errors, and timeouts emit visible events instead of silent failures.
7. **Telemetry exposed safely** — Token counts, model names, and purposes visible to UI but no secret/prompt dump.
8. **Token/cost/purpose visible** — Every LLM invocation's cost and purpose are trackable in the UI.

---

## Tests-First Requirements

### Test Taxonomy for Cluster 2

| Test type | Purpose | Where | Required per story |
|---|---|---|---|
| **Unit** | Single function behavior | `tests/test_*_unit.py` | Required for any new function |
| **Contract** | Event payload shape | `tests/test_*_contract.py` | Required for all event emitters |
| **Integration** | Multi-module interaction | `tests/test_*_integration.py` | Required for event pipeline tests |
| **Negative** | Invalid input behavior | `tests/test_*_negative.py` | Required for all signal handlers |
| **Regression** | No Sprint 6 breakage | `tests/test_sprint7_regression_guard.py` | Run after every commit |

### Negative Tests Required

Every story must include:
- Invalid payload rejected
- Stale/missing request_id rejected or ignored
- Null/empty field behavior
- Timeout/provider error fail-closed path
- Malformed LLM output fails closed, not silent

### Regression Guard

```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

Must stay at baseline (1689 passed, 1 skipped, 12 pre-existing failures).

---

## Local-Only Validation Policy

Cluster 2 does **not** run:
- Paid LLM calls (use fake-LLM or fixture)
- Browser E2E (local unit/contract/integration only)
- Real websites (use mock page packets)
- Live WebSocket integration with real backend (use test doubles)

Cluster 2 **does** run:
- Unit tests
- Contract tests for event payloads
- Integration tests with fake-LLM
- Regression guard suite
- Local browser fake E2E (if needed for page extraction)

---

## Definition of Done

A Cluster 2 story is **Done** when:

1. ✅ All tests from `Tests First` section exist and are green
2. ✅ Implementation code committed (separate commit from tests)
3. ✅ Event payload matches contract schema for frontend
4. ✅ Negative tests pass (invalid input, stale ID, timeout)
5. ✅ Regression guard suite still green (baseline maintained)
6. ✅ Story file updated with evidence (test file names, commit hashes)
7. ✅ No fake-demo state mixed with live state
8. ✅ Modular boundaries maintained (no monolith expansion)
9. ✅ If new module created, it has its own test file

---

## Evidence Required

Before moving story to **Done**:

1. **Test evidence** — test file names and green test output
2. **Implementation evidence** — commit hash(es) of implementation
3. **Regression evidence** — output of `python -m pytest -q` showing baseline maintained
4. **Architecture evidence** — if new module, confirm no import violations
5. **No paid LLM** — confirm no `openai.ChatCompletion` calls
6. **No browser E2E** — confirm no `playwright.sync_api` calls except in cluster 4

---

## Stop Conditions

**Stop and investigate if:**

1. **Regression breaks** — any new test failure in baseline suite
2. **Event payload changes** — any change to event schema must have frontend buy-in
3. **Monolith grows** — any file exceeding 300 lines without planned split
4. **Fake mixes with live** — any path that claims fake as live or vice versa
5. **Paid LLM invoked** — any `openai.ChatCompletion` call outside fake-LLM wrapper
6. **Browser called** — any `browser.execute_script` or `browser.click` during Cluster 2
7. **Source docs unavailable** — if referenced PRD section is missing
8. **Existing story blocked** — if earlier Cluster 2 story cannot complete
9. **Frontend blocked** — if Cluster 2 event cannot be rendered without frontend UI

If any stop condition hit, create a BUG ticket, do not continue, report to planning.

---

## Acceptance Criteria

After all Cluster 2 stories are **Done**:

1. **All 9 stories green** — All unit, contract, integration tests passing
2. **Regression suite green** — 1689+ tests passing, pre-existing 12 failures stable
3. **No paid LLM calls** — Grep confirms no paid provider calls in Cluster 2
4. **Event contracts locked** — All frontend-visible events have typed schemas
5. **Fake/live boundary clear** — Page Intelligence path explicitly marked live or fake
6. **Frontend unblocked** — All Cluster 3 frontend surface dependencies satisfied
7. **Modularization maintained** — No monolith expansion, all new modules ≤300 lines
8. **No code drift** — Implementation matches story tests-first plan

---

## Known Risks

1. **Page Intelligence performance** — Live invocation may be slow; fallback to fake needed.
2. **Event storm** — Too many granular events may flood WebSocket; payload design must be careful.
3. **Frontend type mismatch** — If Cluster 2 event schema changes during Cluster 3, integration breaks.
4. **Token tracking accuracy** — If telemetry collection incomplete, token reports will be inaccurate.
5. **Capability gap registry** — If not exhaustive, unsupported actions may fake success instead of failing closed.

---

## Next Planning Task

After Cluster 2 is **Done**:
→ Create **Cluster 3 planning tickets** (frontend architecture, design extraction, modular structure)

---

## Cluster 2 Closure

**Status:** Done  
**Implementation commit:** `0f2198b`  
**Evidence commit:** (this docs commit)  
**Branch:** `s7/cluster-2-llm-runtime-live-integration-gaps`

### Stories Completed

| Story | Test File | Tests | Status |
|---|---|---|---|
| S7-0201 Page Intelligence live invocation boundary | test_page_intelligence_live_invocation.py | 20 | Done |
| S7-0202 recommendation_ready backend event pipeline | test_recommendation_event_pipeline.py | 14 | Done |
| S7-0203 page_analysis_started and page_summary_ready events | test_page_analysis_events.py | 24 | Done |
| S7-0204 plan_diff event naming and payload alignment | test_plan_diff_events.py | 22 | Done |
| S7-0205 locator_specialist frontend-facing payload alignment | test_locator_candidates_event.py | 14 | Done |
| S7-0206 recovery_diagnoser frontend-facing payload alignment | test_recovery_needed_event.py | 16 | Done |
| S7-0207 token/telemetry event payloads for UI | test_token_report_event.py | 18 | Done |
| S7-0208 capability_gap frontend-facing contract | test_capability_gap_event.py | 21 | Done |
| S7-0209 fail-closed schema and error events visible to frontend | test_error_events.py | 25 | Done |

### Files Touched

- `runtime/event_contracts.py` — 14 new builders, `_redact_api_keys()` helper, `import re`
- `tests/test_page_intelligence_live_invocation.py` (new)
- `tests/test_page_analysis_events.py` (new)
- `tests/test_recommendation_event_pipeline.py` (new)
- `tests/test_plan_diff_events.py` (new)
- `tests/test_locator_candidates_event.py` (new)
- `tests/test_recovery_needed_event.py` (new)
- `tests/test_token_report_event.py` (new)
- `tests/test_capability_gap_event.py` (new)
- `tests/test_error_events.py` (new)

### Validation Evidence

- `python -m pytest -q` → **2078 passed, 0 failed, 1 skipped**
- `runtime/event_contracts.py` coverage: **99%**
- Audit result: **8/8 PASS** (PASS_READY_FOR_EVIDENCE_UPDATE)
- No frontend files changed
- No LLM prompt files changed
- No E2E files changed
- No secrets/raw HTML/raw DOM in any event payload

