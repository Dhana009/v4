# Sprint 7 — Cluster 9: Trace + Artifacts + Agent Visibility

**Sprint:** Sprint 7
**Cluster:** 9
**Status:** Planning
**Date:** 2026-05-13
**Expected Commits:** ~6 (test files + implementation per story)

---

## Cluster Goal

Wire the Trace, Artifacts, and Agent Visibility UI features to live backend telemetry and events. Replace static/demo trace with real event timeline. Show artifacts, redaction status, failure details, LLM telemetry, and capability gap notices. Provide limited agent activity visibility without overclaiming missing backend support.

After Cluster 9:
- Trace tab renders real `trace_event` timeline
- Filters and search work on backend events
- Failure detail panel shows context for failures
- Artifact links and redaction status visible
- LLM call telemetry (model, tokens, cost) displayed
- Capability gap notices visible
- Agent Activity shows available telemetry only; placeholders for missing
- Agent Control Center shows unsupported controls as disabled with reason

---

## Source Rules

**PRD v2.3:**
- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`: Trace and observability architecture
- `04_BACKEND_EVENT_CONTRACT.md`: trace_event payload and semantics
- `07_MULTI_MODEL_ORCHESTRATION.md`: Agent visibility and control surface

**Sprint 7 Governance:**
- `SPRINT-007-CLUSTER-0-GOVERNANCE.md`: Test-first, modularization, no inference rules
- Trace is evidence/debugging only; not runtime truth
- Frontend does not mark run complete, record step, or mutate code based on trace

**Handoff Issues:**
- `SPRINT-006-HANDOFF.md`: Trace tab is contract-only; zero real implementation

---

## Current Audit Findings

### Trace Tab
- **Current:** Zero real frontend implementation (contract tests only)
- **Backend:** `trace_events.py` creates trace events; `trace_export.py` exports bundles
- **Gap:** No Trace tab component, no timeline renderer, no filters, no failure detail panel

### Artifacts & Redaction
- **Current:** Zero real frontend display
- **Backend:** `artifact_bundle.py` creates bundles; `redaction_policy.py` redacts secrets
- **Gap:** No artifact link display, no redaction status indicator

### LLM Telemetry
- **Current:** Token/cost/LLM call data exists in backend but not wired to UI
- **Backend:** `telemetry.py` or trace records track LLM calls, tokens, cost
- **Gap:** No telemetry display in frontend

### Agent Visibility
- **Current:** No Agent Activity view, no Agent Control Center
- **Backend:** `main_orchestrator`, `page_intelligence`, `step_runner` exist but agent lifecycle events may be incomplete
- **Gap:** No agent activity display, no agent control surface

---

## Design Prototype Role

`frontend_new_design_prototype/` contains static mockups of Trace and Agent Control. These are **design reference only**. Do not:
- Copy static content into production live mode
- Show fake agent activity in live mode
- Assume backend wired multi-agent commands unless explicitly implemented

---

## Trace/Artifacts/Agent State Matrix

| Feature | Backend Event | Frontend Command | Frontend State | Display |
|---------|---|---|---|---|
| Trace timeline | `trace_event` (list) | (none) | traceEntries[] | event rows |
| Trace filters | — | (none) | filters | filter UI |
| Failure detail | `trace_event` (failure type) | (none) | selectedFailure | detail panel |
| Artifact link | `artifact_bundle` or `trace_event` ref | (none) | artifacts | link display |
| Redaction status | `redaction_report` | (none) | redactionStatus | status badge |
| LLM telemetry | `llm_call` or trace records | (none) | llmTelemetry[] | summary + details |
| Context/tool policy | `trace_event.context_level` | (none) | contextLevel | info display |
| Capability gap | `capability_gap_recorded` event | (none) | capabilityGaps | notice + action |
| Agent activity | agent lifecycle events | (none) | agentActivity | activity view |
| Agent control | — | `agent_*` commands (if backend wired) | (none) | control toggles |

---

## Backend Event Dependency Table

| Story | Requires Backend Event | Requires Backend Command | Status |
|-------|---|---|---|
| S7-0901: Trace timeline | `trace_event` | — | Events exist; frontend UI missing |
| S7-0902: Trace filters | — | — | UI-only; backend event stream assumed working |
| S7-0903: Failure detail | `trace_event` (type=failure/rejection) | — | Event schema exists; frontend panel missing |
| S7-0904: Artifact links | `artifact_bundle` ref or trace.artifact_ref | — | Events exist; frontend display missing |
| S7-0905: LLM telemetry | `llm_call` or telemetry in trace | — | Data may be in backend trace; wiring needed |
| S7-0906: Context/tool policy | `trace_event.context_level` | — | Event field may need expansion |
| S7-0907: Capability gap | `capability_gap_recorded` event | — | Event may be missing; file Cluster 2 ticket if so |
| S7-0908: Agent activity | agent lifecycle events (incomplete) | — | Events may be missing from backend |
| S7-0909: Agent Control Center | — | `agent_*` commands (if any) | Commands likely missing; placeholder expected |

---

## Frontend Command Table

| Command | Payload | Backend Handler Status | Story |
|---------|---------|---|---|
| (none required) | — | — | Cluster 9 has no required commands |

---

## No-Trace-As-Truth Rules

### Rule C9-1: Trace Cannot Drive Runtime State
Frontend must not:
- Mark a run complete based on trace
- Record a step based on trace evidence
- Mutate code/replay state based on trace

Frontend must:
- Use trace for debugging/evidence only
- Wait for backend events for state truth

### Rule C9-2: Agent Visibility Limited to Available Telemetry
Frontend must not:
- Show fake agent activity in live mode
- Show unsupported agent controls as active
- Claim multi-agent orchestration without backend support

Frontend must:
- Show available telemetry from backend events
- Mark missing/unsupported features clearly
- Provide placeholder/documentation for future features

### Rule C9-3: Secrets Never Displayed
Frontend must not:
- Show raw API keys, prompts, or secret values
- Dump full tool schemas by default
- Display unredacted PII/secrets from artifacts

Frontend must:
- Respect redaction_policy from backend
- Show redaction status clearly

---

## Story List (Tier 1 and 2)

1. **S7-0901** Trace tab live timeline
2. **S7-0902** Trace filters and search
3. **S7-0903** Failure detail panel
4. **S7-0904** Artifact links and redaction status
5. **S7-0905** LLM call, token, and cost display
6. **S7-0906** Context level and tool policy display
7. **S7-0907** Capability gap notices
8. **S7-0908** Compact agent activity view
9. **S7-0909** Agent Control Center placeholder / limited live view

---

## Allowed Files (Cluster 9 Implementation)

### Frontend Components (new)
- `frontend/src/components/trace/**` (new — all Trace tab subcomponents)
- `frontend/src/components/agents/**` (new — agent activity and control surfaces)

### Frontend State & Commands
- `frontend/src/store/**` (new or extend — event store handlers for trace/agent events)

### Frontend Wiring
- `frontend/src/aw-ide-panel.jsx` (modification at prop/callback boundaries only)
- `frontend/src/main.jsx` (modification for thin state threading only)

### Tests
- `tests/test_frontend_trace_*.py` (new)
- `tests/test_frontend_agents_*.py` (new)
- `tests/test_trace_export_*.py` (new — if trace export rendering needed)

### Backend (if handlers missing)
- `server.py` (only thin event routing seam if needed)
- `ws/router.py` or similar (only thin event routing seam if needed)

---

## Forbidden Files (Cluster 9)

- `agent.py` (no changes)
- `runtime/trace_events.py` (read-only; backend owned)
- `runtime/artifact_bundle.py` (read-only; backend owned)
- `runtime/redaction_policy.py` (read-only; backend owned)
- `frontend_new_design_prototype/` (read-only design reference)
- Any `.DS_Store`, `AGENTS.md` files

---

## Tests-First Requirements

### Before Implementation

For each story (S7-0901 through S7-0909):

1. Write unit tests for data transforms (pure functions only)
2. Write contract tests for event payloads
3. Write reducer/store tests for event handlers
4. Write component render tests
5. Write negative tests (malformed/stale/missing data)
6. Run tests — all must fail (red) before implementation
7. Write implementation
8. All tests pass (green)
9. Run regression guard
10. Commit tests + implementation together

### Test File Locations

- `tests/test_frontend_trace_timeline.py` — unit + contract + component tests for S7-0901/0902/0903
- `tests/test_frontend_artifacts.py` — unit + contract + component tests for S7-0904/0905/0906
- `tests/test_frontend_agents.py` — unit + contract + component tests for S7-0908/0909
- `tests/test_capability_gap_notices.py` — unit + component tests for S7-0907

---

## Definition of Done (Cluster 9)

- [ ] All 9 stories complete (status = Done)
- [ ] All story tests pass (unit, contract, integration, negative, regression)
- [ ] Coverage ≥ 95% for new modules
- [ ] No new failures in cheap regression suite
- [ ] No forbidden files modified
- [ ] Trace tab shows real event timeline only (no static demo trace)
- [ ] Filters and search UI work on backend event data
- [ ] Failure detail panel shows context for failures
- [ ] Artifact links and redaction status visible
- [ ] LLM telemetry displayed (model, tokens, cost) if available
- [ ] Capability gap notices visible with next actions
- [ ] Agent Activity shows available telemetry only
- [ ] Agent Control Center shows unsupported controls as disabled
- [ ] Browser smoke test passes for Trace/Agent flows (Cluster 10, S7-1009)
- [ ] All evidence committed and linked

---

## Stop Conditions

Stop and ask for clarification if:

- `trace_event` event schema is incomplete
- Agent lifecycle events are not wired from backend
- `artifact_bundle` or `redaction_policy` cannot be integrated
- LLM telemetry data is not available in backend events
- `capability_gap_recorded` event missing (file Cluster 2 ticket)
- Frontend store/command infrastructure incomplete
- Implementation requires modifying `trace_events.py`, `artifact_bundle.py`, or `redaction_policy.py`
- Test coverage falls below 95%
- Regression guard fails with a new failure
- Any story requires touching a forbidden file (file a new story instead)
- Static demo trace content cannot be cleanly separated from real event rendering

---

## Evidence Requirements

For cluster sign-off:

- [ ] All 9 stories updated to status `Done` in `.tasks-md/Planning/`
- [ ] Test files committed (unit, contract, component, negative, regression)
- [ ] Implementation files committed (components, store handlers, trace/agent displays)
- [ ] Coverage report ≥ 95% for each story's modules
- [ ] Regression guard output (1689 passed + 12 pre-existing failures)
- [ ] Browser smoke test for Trace/Agent flows (Cluster 10 deliverable)
- [ ] Cluster 9 handoff summary (story count, files committed, coverage, gaps)

