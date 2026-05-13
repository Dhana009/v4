# S7-0001 — Complete LLM Mode Requirement Matrix

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Map every Complete LLM Mode requirement from PRD v2.3 and runtime/frontend specs to its Sprint 7, Sprint 8, Sprint 9, or out-of-scope ownership. This matrix is the authoritative reference for deciding what is and is not in scope for Sprint 7 development.

---

## Source Rules

- PRD `00_MASTER_INDEX.md`: Non-negotiable decisions — backend owns runtime truth; LLM proposes only; frontend renders typed events
- PRD `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`: Phase 2 (Complete LLM Mode MVP) acceptance criteria
- PRD `04_BACKEND_EVENT_CONTRACT.md`: Required lifecycle events and commands
- PRD `03_FRONTEND_RUNTIME.md`: Frontend interaction modes, docked panel architecture
- `autoworkbench_complete_llm_mode_runtime_policy_spec.md`: Runtime policy rules
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md`: Frontend UI specification
- `SPRINT-006-HANDOFF.md`: Sprint 6 partial/done status per cluster

---

## Current Known Context

### What Sprint 6 completed
- 37 runtime policy modules compile and are tested
- LLM purpose registry (14 purposes)
- Context policy (L0–L5 tiers)
- Memory, token, tool, schema policy
- Page Intelligence and recommendation
- Journey planner and steps mode
- Plan revision and direct editing
- Locator intelligence and update
- Permission and capability control
- Recovery and failure handling
- Replay, repair, save/load/versioning (session_store in-memory only)
- Trace observability and redaction
- Contract-only frontend tests (no real UI source implemented)

### What Sprint 6 did NOT complete
- Real frontend source implementation (Cluster 10 is contract-only — BUG-S6-FINAL-002)
- run_started event emission
- step_validating / step_executing events
- distinct step_failed / step_skipped events
- permission_required event emission
- typed ready/browser_ready envelope
- run_completed frontend-ready payload completeness
- session_state reconnect payload completeness
- stop_run command wiring
- skip_step command wiring
- save_session / load_session WS command wiring
- Local browser E2E smoke through real UI

### Known pre-existing bugs
- BUG-S6-FINAL-001: 12 model-class contract mismatch failures in cheap suite
- BUG-S6-FINAL-002: Frontend Complete LLM UI is contract-only

---

## Tests First

This is a documentation/matrix story. No implementation tests required. Acceptance is verified by completeness and accuracy of the matrix below.

### Verification
- Matrix covers all PRD v2.3 Phase 2 acceptance criteria
- Each requirement has a clear Sprint ownership
- No requirement is in two sprint columns simultaneously
- Matrix is referenced by S7-0002 (source-rule-to-test mapping)

---

## Requirement Matrix

### Column definitions
- **Sprint 7 Must-Have:** Required for Complete LLM Mode to work end-to-end through the real frontend in Sprint 7.
- **Sprint 8 Controlled Testing:** Working backend/frontend seam exists from Sprint 7; Sprint 8 hardens with paid LLM, real-site scenarios, and edge cases.
- **Sprint 9 Real-World/Live:** Live-site testing, production hardening, real-user flows.
- **Out of Scope (Current):** Not in Complete LLM Mode MVP; deferred to Phase 4 / Phase 5 / v2+.

---

### Backend Event Seams

| Requirement | Source | Sprint 7 | Sprint 8 | Sprint 9 | OOS |
|-------------|--------|----------|----------|----------|-----|
| `run_started` event emitted on new run | PRD-04-BE-001 | Must-Have | | | |
| `step_validating` event during validation | PRD-04-BE-002 | Must-Have | | | |
| `step_executing` event during execution | PRD-04-BE-003 | Must-Have | | | |
| `step_failed` distinct event on failure | PRD-04-BE-004 | Must-Have | | | |
| `step_skipped` distinct event on skip | PRD-04-BE-005 | Must-Have | | | |
| `permission_required` event when policy blocks | PRD-04-BE-006 | Must-Have | | | |
| Typed `ready`/`browser_ready` envelope | PRD-04-BE-007 | Must-Have | | | |
| `run_completed` with frontend-ready payload | PRD-04-BE-008 | Must-Have | | | |
| `session_state` reconnect payload completeness | PRD-04-BE-009 | Must-Have | | | |
| `plan_ready` event (already exists) | PRD-04-BE-010 | Verify | | | |
| `clarification_needed` event (already exists) | PRD-04-BE-011 | Verify | | | |
| `recovery_needed` event (already exists) | PRD-04-BE-012 | Verify | | | |
| `step_recorded` event (already exists) | PRD-04-BE-013 | Verify | | | |
| `code_update` event (already exists) | PRD-04-BE-014 | Verify | | | |
| `capability_gap_recorded` event | PRD-04-BE-015 | | Sprint 8 | | |
| `replay_started` event | PRD-04-BE-016 | | Sprint 8 | | |
| `replay_result` event per step | PRD-04-BE-017 | | Sprint 8 | | |

### Backend Command Seams

| Requirement | Source | Sprint 7 | Sprint 8 | Sprint 9 | OOS |
|-------------|--------|----------|----------|----------|-----|
| `stop_run` command with stale-rejection | PRD-04-CMD-001 | Must-Have | | | |
| `skip_step` command with step_id validation | PRD-04-CMD-002 | Must-Have | | | |
| `save_session` WS command wiring | PRD-04-CMD-003 | Must-Have | | | |
| `load_session` WS command wiring | PRD-04-CMD-004 | Must-Have | | | |
| `permission_decision` command | PRD-04-CMD-005 | Must-Have | | | |
| `confirmed` command (already wired) | PRD-04-CMD-006 | Verify | | | |
| `correction` command (already wired) | PRD-04-CMD-007 | Verify | | | |
| `option_selected` command (already wired) | PRD-04-CMD-008 | Verify | | | |
| `run_steps` / `llm_run` command | PRD-04-CMD-009 | Verify | | | |
| `replay_one` / `replay_step` command | PRD-04-CMD-010 | | Sprint 8 | | |
| `replay_all` command | PRD-04-CMD-011 | | Sprint 8 | | |
| `update_locator` command | PRD-04-CMD-012 | | Sprint 8 | | |

### Frontend State and Interaction Modes

| Requirement | Source | Sprint 7 | Sprint 8 | Sprint 9 | OOS |
|-------------|--------|----------|----------|----------|-----|
| Live WS transport connected to IDEPanel | PRD-03-FE-001 | Must-Have | | | |
| `idle` mode renders correctly from backend event | PRD-03-FE-002 | Must-Have | | | |
| `planning` mode from `run_started` event | PRD-03-FE-003 | Must-Have | | | |
| `plan_review` mode from `plan_ready` event | PRD-03-FE-004 | Must-Have | | | |
| `clarification` mode from `clarification_needed` | PRD-03-FE-005 | Must-Have | | | |
| `executing` mode from step execution events | PRD-03-FE-006 | Must-Have | | | |
| `recovery` mode from `recovery_needed` event | PRD-03-FE-007 | Must-Have | | | |
| `completed` mode from `run_completed` event | PRD-03-FE-008 | Must-Have | | | |
| No mode inferred from LLM text | PRD-03-FE-009 | Must-Have | | | |
| Session state reconnect restores UI from backend | PRD-03-FE-010 | Must-Have | | | |
| Static/demo content fallback removed | PRD-03-FE-011 | Must-Have | | | |
| Shadow DOM host wired to live state | PRD-03-FE-012 | Must-Have | | | |
| Design tokens from `frontend_new_design_prototype` extracted | PRD-03-FE-013 | Must-Have | | | |
| Docked/resizable layout host | PRD-03-FE-014 | | Sprint 8 | | |
| Fullscreen-safe rendering | PRD-03-FE-015 | | Sprint 8 | | |
| Agent Control Center UI toggles | PRD-03-FE-016 | | | | OOS (Phase 5) |

### LLM Runtime (Verified Sprint 6)

| Requirement | Source | Sprint 7 | Sprint 8 | Sprint 9 | OOS |
|-------------|--------|----------|----------|----------|-----|
| 14-purpose LLM policy registry | Sprint 6 Done | Maintain | | | |
| Context policy L0–L5 | Sprint 6 Done | Maintain | | | |
| Token budget policy | Sprint 6 Done | Maintain | | | |
| Tool exposure enforcement | Sprint 6 Done | Maintain | | | |
| Schema validation policy | Sprint 6 Done | Maintain | | | |
| Page Intelligence recommendation | Sprint 6 Done | Maintain | | | |
| Journey planner and steps mode | Sprint 6 Done | Maintain | | | |
| Plan revision and correction | Sprint 6 Done | Maintain | | | |
| Locator intelligence and update | Sprint 6 Done | Maintain | | | |
| Permission and capability control | Sprint 6 Done | Maintain | | | |
| Recovery and failure handling | Sprint 6 Done | Maintain | | | |
| Replay, save/load/versioning (in-memory) | Sprint 6 Done | Extend with WS | | | |
| Trace observability and redaction | Sprint 6 Done | Maintain | | | |

### E2E and Acceptance

| Requirement | Source | Sprint 7 | Sprint 8 | Sprint 9 | OOS |
|-------------|--------|----------|----------|----------|-----|
| Local browser E2E smoke (fake-LLM) | PRD-06-ACC-001 | Must-Have | | | |
| Paid LLM E2E acceptance gate | PRD-06-ACC-002 | | Sprint 8 | | |
| Real-world/live-site E2E | PRD-06-ACC-003 | | | Sprint 9 | |

---

## Implementation Boundaries

This is a documentation story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0001-Complete-LLM-Mode-requirement-matrix.md` (this file)

---

## Forbidden Files

- No product code changes
- No test file changes
- No runtime/ changes
- No frontend/ changes

---

## Acceptance Criteria

- [ ] Matrix covers all PRD v2.3 Phase 2 requirements
- [ ] Every requirement has exactly one sprint column marked
- [ ] Sprint 7 Must-Have requirements are traceable to Cluster 1–4 story files
- [ ] Sprint 8 / Sprint 9 requirements are clearly deferred with no Sprint 7 work started
- [ ] Matrix is referenced by S7-0002 source-rule-to-test mapping

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`
- [ ] Matrix complete with no empty rows

---

## Stop Conditions

- A Sprint 7 requirement cannot be mapped to a specific cluster story — file a planning gap ticket
- A requirement appears in both Sprint 7 and Sprint 8 columns — resolve before proceeding
