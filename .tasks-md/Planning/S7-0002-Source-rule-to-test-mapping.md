# S7-0002 — Source-Rule-to-Test Mapping

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Define the Sprint 7 rule that every test must trace back to a named source rule. No source rule → no test. No test → no implementation. This document establishes the traceability standard and provides a mapping template for all Cluster 1–4 stories.

---

## Source Rules

- PRD `00_MASTER_INDEX.md`: "All implementation decisions preserve the non-negotiable decisions above."
- PRD `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`: Tests that must exist before calling LLM Mode MVP complete
- Sprint 7 Cluster 0 Governance: "No source rule → no test. No test → no implementation."
- Sprint 6 story template (S6-0005): Source rules section required in every story

---

## Current Known Context

Sprint 6 stories included source rules sections but the mapping was not always enforced as a hard gate — some stories had implementation before tests. Sprint 7 enforces this as a hard requirement: test file must exist with failing tests before any implementation commit is accepted.

The `runtime/event_contracts.py` module already has a schema version system and builder functions. New event builders must be tested before being wired.

The `SUPPORTED_FRONTEND_COMMAND_TYPES` set in `event_contracts.py` currently only contains `{"confirmed", "correction", "option_selected"}`. Adding new command types requires a source rule citation.

---

## Tests First

This is a documentation/policy story. No implementation tests required.

### Verification
- Mapping table covers all Sprint 7 Must-Have requirements from S7-0001
- Each row has a source document, rule ID, test file, and test name pattern
- No test is listed without a source rule
- Mapping is used by Cluster 1–4 stories as their test-design starting point

---

## Source Rule ID Convention

Sprint 7 source rule IDs follow this format:

```
PRD-<doc>-<area>-<NNN>
```

Examples:
- `PRD-04-BE-001` = PRD document 04 (Backend Event Contract), Backend Events, rule 001
- `PRD-03-FE-001` = PRD document 03 (Frontend Runtime), Frontend, rule 001
- `PRD-02-LLM-001` = PRD document 02 (LLM Runtime), LLM, rule 001
- `GOV-S7-C0-001` = Sprint 7 Cluster 0 Governance, rule 001
- `S6-HANDOFF-001` = Sprint 6 HANDOFF, finding 001

The full `GOV-S7-C0-NNN` range (001–063) is anchored in `SPRINT-007-CLUSTER-0-GOVERNANCE.md` § "Anchored Rule ID Index". Any story citing a `GOV-S7-C0-NNN` ID must resolve to a row in that index.

---

## Synthetic ID Index — Source Document Anchors

This index resolves every `PRD-<doc>-<area>-<NNN>` ID cited across Sprint 7 stories to a real source-document section and rule summary. Stories cite the synthetic ID; reviewers verify the row exists here.

### PRD-02 (LLM Runtime, Workflows)

| Synthetic ID | Source document | Section / rule | Rule summary |
|--------------|-----------------|----------------|--------------|
| PRD-02-WORKFLOWS-001 | `01_PRODUCT_WORKFLOWS.md` | LLM Mode primary flow | Intent → clarification → plan → confirm → execute → record → code → complete |
| PRD-02-WORKFLOWS-002 | `01_PRODUCT_WORKFLOWS.md` | Plan correction | User correction triggers re-plan; old plan invalid until new plan_ready |
| PRD-02-WORKFLOWS-003 | `01_PRODUCT_WORKFLOWS.md` | Confirmation gate | No execution before user confirm of plan |
| PRD-02-WORKFLOWS-004 | `01_PRODUCT_WORKFLOWS.md` | Recording flow | Each step produces backend-emitted step_recorded evidence |
| PRD-02-WORKFLOWS-005 | `01_PRODUCT_WORKFLOWS.md` | Locator ambiguity flow | Backend emits locator_ambiguous with candidates; UI awaits user choice |
| PRD-02-WORKFLOWS-006 | `01_PRODUCT_WORKFLOWS.md` | Recovery flow | Backend emits recovery_needed; user chooses retry/skip/stop |
| PRD-02-WORKFLOWS-007 | `01_PRODUCT_WORKFLOWS.md` | Completion summary | run_completed payload includes recorded/skipped counts |
| PRD-02-LLM-001 | `02_LLM_RUNTIME.md` | LLM proposer/reasoner only | LLM never decides finality, recording, or failure resolution |
| PRD-02-LLM-005 | `02_LLM_RUNTIME.md` | Fail-closed schema | Malformed/missing LLM output rejected; no silent fallback |

### PRD-03 (Frontend Runtime)

| Synthetic ID | Source document | Section / rule | Rule summary |
|--------------|-----------------|----------------|--------------|
| PRD-03-FE-001 | `03_FRONTEND_RUNTIME.md` | Live WS transport | Frontend connects via typed WS transport; IDEPanel receives live state |
| PRD-03-FE-002 | `03_FRONTEND_RUNTIME.md` | Manual Mode is deterministic first | Manual Mode is deterministic/manual-control-first; LLM help is explicit and optional |
| PRD-03-FE-003 | `03_FRONTEND_RUNTIME.md` | Same Recorder/Code/Trace systems serve both modes | LLM Mode and Manual Mode share backend recording/code/replay infrastructure |
| PRD-03-FE-004 | `03_FRONTEND_RUNTIME.md` | plan_review interaction mode | Triggered by plan_ready event only |
| PRD-03-FE-005 | `03_FRONTEND_RUNTIME.md` | clarification interaction mode | Triggered by clarification_needed event only |
| PRD-03-FE-006 | `03_FRONTEND_RUNTIME.md` | executing interaction mode | Triggered by step lifecycle events only |
| PRD-03-FE-007 | `03_FRONTEND_RUNTIME.md` | Typed commands only | Frontend sends only typed, schema-validated commands |
| PRD-03-FE-008 | `03_FRONTEND_RUNTIME.md` | completed interaction mode | Triggered by run_completed event only |
| PRD-03-FE-009 | `03_FRONTEND_RUNTIME.md` | No inference from LLM text | UI never derives lifecycle state from LLM prose |
| PRD-03-FE-010 | `03_FRONTEND_RUNTIME.md` | session_state reconnect restore | UI restores from session_state snapshot on reconnect |
| PRD-03-FE-011 | `03_FRONTEND_RUNTIME.md` | No static/demo fallback in live mode | Live mode never renders demo/static content |
| PRD-03-FE-012 | `03_FRONTEND_RUNTIME.md` | Shadow DOM host wiring | Frontend mounts inside `aw-shadow-host` with isolated styles |
| PRD-03-FE-013 | `03_FRONTEND_RUNTIME.md` | Design tokens externalized | Tokens extracted from prototype; no inline magic values |
| PRD-03-FE-014 | `03_FRONTEND_RUNTIME.md` | Docked panel layout | Panel docks right/left/top/bottom; non-overlay |
| PRD-03-FE-015 | `03_FRONTEND_RUNTIME.md` | Page compensation | Host page content shifts; not hidden behind panel |
| PRD-03-FE-016 | `03_FRONTEND_RUNTIME.md` | data-testid baseline | Critical UI elements expose stable data-testid attributes |

### PRD-04 (Backend Event and Command Contract)

`PRD-04-BE-000` through `PRD-04-BE-017` map to `04_BACKEND_EVENT_CONTRACT.md` event sections (run_started, plan_ready, step_validating, step_executing, step_failed, step_skipped, step_recorded, permission_required, ready, run_completed, session_state, code_update, recommendation_ready, page_analysis_started, page_summary_ready, plan_diff_ready, locator_ambiguous, recovery_needed). `PRD-04-BACKEND-001..010` are legacy aliases retained for stories that pre-date the `BE` rename; reviewers may treat `BACKEND-NNN` as identical to `BE-NNN`.

`PRD-04-CMD-000` through `PRD-04-CMD-012` map to `04_BACKEND_EVENT_CONTRACT.md` command-envelope section (confirmed, correction, option_selected, stop_run, skip_step, save_session, load_session, permission_decision, replay_one, replay_all, choose_candidate, validate_locator, improve_locator).

### PRD-05 (Codegen / Replay / Persistence)

| Synthetic ID | Source document | Rule summary |
|--------------|-----------------|--------------|
| PRD-05-REC-001..005 | `05_CODEGEN_REPLAY_PERSISTENCE.md` | step_recorded payload, evidence fields, repaired/skipped/unresolved states |
| PRD-05-CODEGEN-001..004 | `05_CODEGEN_REPLAY_PERSISTENCE.md` | code_update payload, line-to-step mapping, warnings, capability placeholders |
| PRD-05-REPLAY-001 | `05_CODEGEN_REPLAY_PERSISTENCE.md` | replay_one and replay_all command payloads |
| PRD-05-RECOVERY-001..002 | `05_CODEGEN_REPLAY_PERSISTENCE.md` | recovery_needed payload, retry/skip/stop options |
| PRD-05-SESSION-001 | `05_CODEGEN_REPLAY_PERSISTENCE.md` | save_session / load_session payload and version field |
| PRD-05-CAPGAP-001..002 | `05_CODEGEN_REPLAY_PERSISTENCE.md` | capability_gap notice payload and UI handling |

### PRD-06 (Build Roadmap / Acceptance / Trace)

| Synthetic ID | Source document | Rule summary |
|--------------|-----------------|--------------|
| PRD-06-ACC-001 | `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Local E2E smoke acceptance gate |
| PRD-06-ACC-002 | `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Cheap regression suite must stay green |
| PRD-06-ACC-003 | `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Frontend build/test must pass before push readiness |
| PRD-06-TRACE-001..004 | `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Trace timeline, filters, failure detail, artifact link contracts |
| PRD-06-REDACTION-001 | `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Artifacts must redact secrets before display |

### PRD-07 (Multi-Model Orchestration)

| Synthetic ID | Source document | Rule summary |
|--------------|-----------------|--------------|
| PRD-07-AGENT-001 | `07_MULTI_MODEL_ORCHESTRATION.md` | Agent Control Center limited visibility in Sprint 7 |
| PRD-07-AGENT-004 | `07_MULTI_MODEL_ORCHESTRATION.md` | Specialist agents (Page Intelligence) emit context only, not decisions |

### GOV-S7-C0 (Sprint 7 Cluster 0 Governance)

`GOV-S7-C0-001` … `GOV-S7-C0-063` are anchored in `SPRINT-007-CLUSTER-0-GOVERNANCE.md` § "Anchored Rule ID Index". See that document for the canonical list.

### Unresolvable IDs

If any story cites an ID not in this index or in the C0 anchored rule index, the story must be corrected before merge. No `_UNRESOLVED` IDs remain.

---

## Source-Rule-to-Test Mapping

### Cluster 1: Backend Event and Command Seams

| Source Rule | Rule Text (Summary) | Story | Test File | Test Name Pattern |
|-------------|---------------------|-------|-----------|-------------------|
| PRD-04-BE-001 | run_started event with run_id, steps[] | S7-0101 | tests/test_run_started_event_contract.py | test_build_run_started_payload_* |
| PRD-04-BE-002 | step_validating with step_id, operation_id, locator | S7-0102 | tests/test_step_progress_events_contract.py | test_step_validating_payload_* |
| PRD-04-BE-003 | step_executing with step_id, operation_id, action | S7-0102 | tests/test_step_progress_events_contract.py | test_step_executing_payload_* |
| PRD-04-BE-004 | step_failed with step_id, operation_id, error, status | S7-0103 | tests/test_step_terminal_events_contract.py | test_step_failed_payload_* |
| PRD-04-BE-005 | step_skipped with step_id, reason | S7-0103 | tests/test_step_terminal_events_contract.py | test_step_skipped_payload_* |
| PRD-04-BE-006 | permission_required when policy blocks | S7-0104 | tests/test_permission_required_event_contract.py | test_permission_required_* |
| PRD-04-BE-007 | typed ready/browser_ready envelope fields | S7-0105 | tests/test_ready_envelope_contract.py | test_typed_ready_envelope_* |
| PRD-04-BE-008 | run_completed with run_id, summary, recorded_count, skipped_count | S7-0106 | tests/test_run_completed_contract.py | test_run_completed_payload_* |
| PRD-04-BE-009 | session_state on connect/reconnect with full snapshot | S7-0110 | tests/test_session_state_reconnect.py | test_session_state_* |
| PRD-04-CMD-001 | stop_run accepted only when active run exists | S7-0107 | tests/test_stop_run_command_contract.py | test_stop_run_* |
| PRD-04-CMD-002 | skip_step requires run_id and step_id | S7-0108 | tests/test_skip_step_command_contract.py | test_skip_step_* |
| PRD-04-CMD-003 | save_session WS command → save_result event | S7-0109 | tests/test_session_persistence_contract.py | test_save_session_* |
| PRD-04-CMD-004 | load_session WS command → load_result event | S7-0109 | tests/test_session_persistence_contract.py | test_load_session_* |
| PRD-04-CMD-005 | permission_decision accepted only for matching run/operation | S7-0104 | tests/test_permission_required_event_contract.py | test_permission_decision_* |

### Cluster 2: Frontend Transport, State, and Interaction Mode (planned)

| Source Rule | Rule Text (Summary) | Story | Test File | Test Name Pattern |
|-------------|---------------------|-------|-----------|-------------------|
| PRD-03-FE-001 | Live WS transport connected to IDEPanel | S7-0201 | tests/test_frontend_transport_contract.py | test_ws_transport_* |
| PRD-03-FE-002 | idle mode from backend ready event | S7-0202 | tests/test_frontend_interaction_modes.py | test_idle_mode_* |
| PRD-03-FE-003 | planning mode from run_started event | S7-0202 | tests/test_frontend_interaction_modes.py | test_planning_mode_* |
| PRD-03-FE-004 | plan_review mode from plan_ready event | S7-0202 | tests/test_frontend_interaction_modes.py | test_plan_review_mode_* |
| PRD-03-FE-005 | clarification mode from clarification_needed | S7-0202 | tests/test_frontend_interaction_modes.py | test_clarification_mode_* |
| PRD-03-FE-006 | executing mode from step execution events | S7-0202 | tests/test_frontend_interaction_modes.py | test_executing_mode_* |
| PRD-03-FE-007 | recovery mode from recovery_needed event | S7-0202 | tests/test_frontend_interaction_modes.py | test_recovery_mode_* |
| PRD-03-FE-008 | completed mode from run_completed event | S7-0202 | tests/test_frontend_interaction_modes.py | test_completed_mode_* |
| PRD-03-FE-009 | no mode inferred from LLM prose text | S7-0203 | tests/test_frontend_no_inference.py | test_no_llm_text_inference_* |
| PRD-03-FE-010 | session_state reconnect restores UI | S7-0204 | tests/test_frontend_reconnect_restore.py | test_reconnect_restore_* |
| PRD-03-FE-011 | static/demo content fallback removed | S7-0205 | tests/test_frontend_no_demo_state.py | test_no_demo_state_* |

### Cluster 3: Frontend Component Wiring (planned)

| Source Rule | Rule Text (Summary) | Story | Test File | Test Name Pattern |
|-------------|---------------------|-------|-----------|-------------------|
| PRD-03-FE-012 | Shadow DOM host wired to live state | S7-0301 | tests/test_shadow_dom_wiring.py | test_shadow_dom_* |
| PRD-03-FE-013 | Design tokens from prototype extracted | S7-0302 | component tests | test_design_tokens_* |
| PRD-04-BE-001..009 | All event types render correctly in components | S7-0303 | component test suite | test_event_renders_* |

### Cluster 4: Local Browser E2E (planned)

| Source Rule | Rule Text (Summary) | Story | Test File | Test Name Pattern |
|-------------|---------------------|-------|-----------|-------------------|
| PRD-06-ACC-001 | Local E2E smoke: fake-LLM run through real UI | S7-0401 | tests/e2e/test_llm_mode_smoke.py | test_e2e_smoke_* |

---

## Negative Test Requirements

Every story must include negative tests. Negative tests require their own source rule citations:

| Negative Scenario | Source Rule | Required in Story |
|-------------------|-------------|------------------|
| Malformed event payload rejected | GOV-S7-C0-004 | All Cluster 1 stories |
| Stale command rejected with typed error | GOV-S7-C0-005 | S7-0107, S7-0108 |
| Missing required field rejected | PRD-04-BE-000 (validation rules) | All event builder stories |
| Unknown event type logged not silently ignored | PRD-04-BE-000 | S7-0105 |
| Invalid command type rejected | PRD-04-CMD-000 | S7-0107, S7-0108, S7-0109 |
| Frontend mode transition from unknown event blocked | PRD-03-FE-009 | Cluster 2 stories |
| Load session with malformed payload rejected | PRD-04-CMD-004 | S7-0109 |
| Permission decision for wrong run rejected | PRD-04-CMD-005 | S7-0104 |

---

## Enforcement Protocol

When a developer submits implementation for any Sprint 7 story:

1. Reviewer checks that every test in the story's test files has a source rule cited in a comment.
2. Reviewer checks that no test exists without a matching row in this mapping table or the story's own source rules section.
3. If a test cannot be traced to a source rule, the test is removed or the source rule is added and this mapping updated before merge.
4. If an implementation file is modified but no corresponding test exists, implementation is rejected.

---

## Implementation Boundaries

This is a documentation/policy story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0002-Source-rule-to-test-mapping.md` (this file)

---

## Forbidden Files

- No product code changes
- No test file changes
- No runtime/ changes
- No frontend/ changes

---

## Acceptance Criteria

- [ ] Every Sprint 7 Must-Have requirement from S7-0001 is covered in the mapping table
- [ ] Every row has: source rule ID, rule summary, story reference, test file, test name pattern
- [ ] Negative test requirements are documented for each story category
- [ ] Enforcement protocol is clear and actionable
- [ ] Cluster 1–4 story files reference this mapping when listing tests

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`
- [ ] All rows populated — no empty test file or pattern cells

---

## Stop Conditions

- A Sprint 7 story is implemented without a corresponding row in this mapping — stop and add the mapping first
- A test in a story does not trace to any source rule — stop and resolve before merging
