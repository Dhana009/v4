# Sprint 7 — Cluster 10: Integrated Local Browser E2E Smoke Gate

**Sprint:** Sprint 7
**Cluster:** 10
**Status:** Planning
**Date:** 2026-05-13
**Expected Commits:** ~4 (harness, E2E tests, fixtures)

---

## Cluster Goal

Prove Sprint 7 Complete LLM Mode development works end-to-end through the real frontend using local, no-cost testing. Run deterministic E2E flows against the real frontend + backend + fake LLM. Produce evidence that:
- Backend event/command contracts work through the UI
- Frontend renders backend truth in real time
- Real docked Shadow DOM panel works (not static/demo content)
- Main user workflows complete without paid LLM or live websites
- Sprint 8 can focus on realistic controlled hardening, Sprint 9 on live-site validation

After Cluster 10:
- E2E harness locates and interacts with docked Shadow DOM UI
- Fake event stream proves frontend renders backend events
- 8 complete flows (intent → plan → confirm → record → code → complete) run end-to-end locally
- Clarification, correction, locator ambiguity, recovery flows work
- Steps tab, save/load/replay UI flows work
- All required artifacts captured
- No paid LLM, no live external websites

---

## Source Rules

**PRD v2.3:**
- `03_FRONTEND_RUNTIME.md`: Frontend renders typed backend events; sends typed commands only
- `04_BACKEND_EVENT_CONTRACT.md`: All event schemas and payloads
- `05_CODEGEN_REPLAY_PERSISTENCE.md`: Recording, code generation, replay, save/load contracts
- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`: Local E2E acceptance gate definition

**Sprint 7 Governance:**
- `SPRINT-007-CLUSTER-0-GOVERNANCE.md`: Non-negotiable architecture rules, test-first protocol
- Backend owns runtime truth; frontend renders events, sends commands only
- No frontend lifecycle inference
- No paid LLM by default
- Local development-complete proof required before Sprint 8

**Handoff Issues:**
- `SPRINT-006-HANDOFF.md`: No browser-level E2E tests currently verify real UI behavior
- Frontend state has historically not been fully threaded into IDEPanel
- Shadow DOM host exists partially; docked layout needs proof

---

## Current Audit Findings

### E2E Infrastructure
- **Current:** `tests/e2e/harness.py` exists with browser automation but assumes old overlay model
- **Gap:** No Shadow DOM host detection; no docked panel interaction; hard-coded for old frontend shape
- **Required:** Update harness to find `aw-shadow-host`, interact through docked layout, avoid selecting UI as target

### Fake Event Stream
- **Current:** E2E tests receive real backend events but no deterministic fake-only path
- **Gap:** Cannot run E2E without backend running; flows depend on LLM behavior or long delays
- **Required:** Deterministic fake event stream injector for reproducible, fast E2E

### Frontend State Threading
- **Current:** `frontend/src/main.jsx` has live WS transport + event store but state not fully in IDEPanel
- **Gap:** Events received but not always rendered in UI
- **Required:** Verify state flows from WebSocket → store → component props → rendered DOM

### Shadow DOM / Docked Panel
- **Current:** Shadow DOM host mount exists; docking logic partial
- **Gap:** E2E harness cannot locate or interact with docked panel; page compensation untested
- **Required:** E2E tests verify panel is docked, website area accessible, both interactive

### Data-testid Coverage
- **Current:** Sparse coverage; many components missing testids
- **Gap:** E2E selectors fragile
- **Required:** Ensure all critical UI elements have stable data-testid attributes

### Evidence Artifacts
- **Current:** E2E may take screenshots but no structured artifact bundle
- **Gap:** Cannot reproduce failures without artifacts
- **Required:** E2E captures screenshots, event/command logs, error messages

---

## Local-Only E2E Policy

This cluster must:
- ✓ Use fake/local LLM only (no OpenAI, no paid APIs)
- ✓ Use local fixture websites only (no live external sites)
- ✓ Use deterministic event streams (no random delays, no flake)
- ✓ Produce captured artifacts (logs, screenshots, event manifest)
- ✓ Run without user interaction (no manual browser steps)
- ✗ NOT call paid APIs
- ✗ NOT browse live websites
- ✗ NOT require ENV vars for real API keys
- ✗ NOT depend on LLM reasoning or generation (use fake LLM fixtures)

---

## Required Flows

| Flow | Cluster | Start Event | End Event | Assertions |
|------|---------|---|---|---|
| Intent → Clarification → Plan | C6 LLM | submit_intent | plan_ready | clarification rendered, plan rendered, no exec before confirm |
| Plan Correction | C6 LLM | submit_correction | plan_ready | plan version changes, old plan not confirmed |
| Confirm → Execute → Record → Code → Complete | C6 LLM | confirm_plan | run_completed | no exec before confirm, recorded tab updates, code tab updates |
| Locator Ambiguity → Choose | C6 LLM | locator_ambiguous | execution resumes | candidates rendered, command dispatched, no exec before choice |
| Recovery → Retry/Skip/Stop | C6 LLM | recovery_needed | run_completed | recovery card rendered, unresolved blocks summary, backend validates |
| Steps Tab: Run Selected/All | C7 Steps | submit_intent | run_completed | live steps rendered, selection dispatches commands, backend executes |
| Save/Load/Replay | C8 Recorded/Code | replay_one or save_session | replay_result or session_state | no inference before event, backend truth restored |

---

## Architecture Invariants (Hard Stops)

Must verify:
1. **Backend Truth:** No frontend mutation of step lifecycle, plan, recording, or code
2. **No Inference:** Frontend waits for backend events; does not synthesize state
3. **Typed Commands:** Every command has a schema; stale/malformed commands rejected
4. **Event-Driven UI:** Every DOM change driven by backend event or user interaction → command → event
5. **No Static/Demo Fallback:** Live mode never falls back to static UI or hardcoded content

---

## Required Artifacts

Each E2E test must produce:
- **Screenshots:** Browser state at key moments (clarification, plan, execution, completion)
- **Event Log:** Chronological list of backend events with timestamps and payloads
- **Command Log:** Chronological list of frontend commands sent
- **Errors:** Any runtime/frontend errors with stack traces
- **Manifest:** JSON describing test name, duration, pass/fail, artifacts location

---

## Shadow DOM / Docked Panel Test Requirements

- **Mount:** aw-shadow-host found and mounted within target page
- **Docking:** Panel is visible, docked right/left/top/bottom, not fullscreen overlay
- **Content:** Page content not hidden by panel (unless explicitly below fold)
- **Interaction:** Click elements in panel without clicking hidden page elements
- **Unmount:** Panel can unmount cleanly; page returns to original state
- **CSS Isolation:** Panel styles do not bleed into page; page styles do not affect panel
- **Accessibility:** Panel elements discoverable via data-testid; keyboard navigation works

---

## Event/Command Assertions

Every E2E test must assert:
1. **Event Arrival:** Backend event timestamp ≤ current time + 10s (proof it was recent)
2. **Event Payload:** All required fields present and typed correctly
3. **Command Sending:** Frontend dispatches command with correct envelope (run_id, session_id, user_id)
4. **Stale Command Blocking:** Sending command with wrong run_id is rejected or ignored
5. **Command Order:** Commands arrive at backend in order sent

---

## Story List

| ID | Title | Tier | Dependencies |
|----|-------|------|---|
| S7-1001 | E2E harness update for docked Shadow DOM | 1 | (none) |
| S7-1002 | Fake backend event stream tests | 1 | S7-1001 |
| S7-1003 | Flow: intent → clarification → plan_ready | 1 | S7-1001, S7-1002 |
| S7-1004 | Flow: plan correction → corrected plan_ready | 1 | S7-1003 |
| S7-1005 | Flow: confirm → execution → recorded → code → run_completed | 1 | S7-1003 |
| S7-1006 | Flow: locator ambiguity → choose candidate | 1 | S7-1003 |
| S7-1007 | Flow: recovery → retry/skip/stop | 1 | S7-1003 |
| S7-1008 | Flow: Steps tab run selected/run all | 2 | S7-1003 |
| S7-1009 | Flow: save/load/replay UI | 2 | S7-1005 |
| S7-1010 | Sprint 7 regression smoke suite | 1 | S7-1001 through S7-1009 |

---

## Allowed Files

For Cluster 10 implementation:
```
- tests/e2e/harness.py (update to support Shadow DOM)
- tests/e2e/ (new test files and fixtures)
- tests/fake_llm_factory.py (may need E2E-specific fixtures)
- tests/e2e/fixtures/ (new local fixture websites)
- frontend/src/ (data-testid additions only, must already be planned by Cluster 3–9)
- .tasks-md/Planning/S7-100*.md (story files)
- .tasks-md/Bugs/ (new bug tickets for failures)
```

---

## Forbidden Files

```
- agent.py (no changes)
- runtime/ (no changes except via backend cluster seams)
- llm/ (no changes to real LLM integration; use fake)
- frontend/src/main.jsx (no major refactor; state threading in Cluster 5)
- server.py (no major changes except routing in backend clusters)
- frontend/src/aw-ide-panel.jsx (state wiring in Cluster 5)
- AGENTS.md (do not stage)
- .DS_Store (do not stage)
- .tasks-md/.DS_Store (do not stage)
```

---

## Tests-First Requirements

For each story:
1. Write all test functions in proper pytest file FIRST (red)
2. Run tests — they must fail before implementation
3. Implement minimum code to pass tests
4. Verify no regression in cheap suite
5. Commit tests + implementation together

No test execution until after story implementation starts.

---

## Definition of Done (Cluster 10)

- [ ] All 10 stories completed and moved to Done
- [ ] All E2E tests pass locally with fake LLM (no paid APIs)
- [ ] All required flows run end-to-end without errors
- [ ] Artifacts captured for all flows (screenshots, event logs, command logs)
- [ ] No new failures in cheap regression suite
- [ ] Shadow DOM interaction verified (panel docked, page accessible, both interactive)
- [ ] 8 main flows complete, 2 supporting flows complete
- [ ] No static/demo UI appears in live mode
- [ ] Frontend state threaded correctly (events → store → DOM)
- [ ] Backend truth preserved throughout (no frontend mutation)
- [ ] Evidence committed: test files, fixture files, artifact examples

---

## Stop Conditions

Halt immediately if:
- E2E harness cannot locate Shadow DOM without extensive rewrites
- Fake event stream cannot be deterministic without backend changes to seams
- Frontend state not updating from events (indicates architectural issue in Clusters 1–9)
- Paid LLM or live websites required to run E2E
- More than 2 failures per flow (indicates Clusters 1–9 incomplete)
- Data-testid coverage insufficient for reliable selector matching
- Page compensation breaks interactive elements
- Tests cannot capture artifacts without external dependencies

---

## Evidence Requirements

**Cluster 10 completion evidence:**
- [ ] test_e2e_harness.py or tests/e2e/test_*.py files committed
- [ ] All E2E test functions passing
- [ ] Fake LLM factory updated with E2E-specific fixtures
- [ ] E2E fixtures directory created with local website fixtures
- [ ] Screenshot examples from each flow in `.tasks-md/Artifacts/C10/`
- [ ] Event log example showing full intent → plan → confirm → record → code → complete flow
- [ ] Command log example showing typed command envelopes
- [ ] No paid API keys in environment during E2E run
- [ ] Coverage report for E2E infrastructure
- [ ] Cluster 10 regression suite runs without failures

---

## Acceptance Philosophy

**Local development-complete means:**
- Real frontend + backend work together locally
- No paid APIs needed for proof
- No live websites needed for proof
- Fake LLM sufficient to demonstrate flows
- Trace/artifacts captured for debugging
- Flakiness < 5% on repeated runs
- Cheap regression suite green (Sprint 6 baseline or better)

**Does NOT mean:**
- Paid LLM E2E approved (deferred to Sprint 8 or explicit acceptance)
- Real-world hardening complete (deferred to Sprint 9)
- All edge cases covered (controlled hardening in Sprint 8)

If paid E2E is not run: status must be "Cluster 10 local E2E complete; paid gate pending"
If paid E2E IS run: document separately with explicit "PAID E2E COMPLETED" header
