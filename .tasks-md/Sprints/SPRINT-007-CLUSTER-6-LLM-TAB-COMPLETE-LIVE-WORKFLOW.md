# Sprint 7 — Cluster 6: LLM Tab Complete Live Workflow

**Sprint:** Sprint 7  
**Cluster:** 6  
**Status:** Planning  
**Date:** 2026-05-13  
**HEAD at planning:** 8bdd8def90b71fdaa24890943ec792b55397c66f

---

## Cluster 6 Goal

The LLM tab is the primary user-facing interface for Complete LLM Mode. It must feel like a continuous conversation/workflow, but every state must come directly from backend events. No static demo content. No frontend inference of lifecycle truth.

After Cluster 6, users can:
- Have a continuous chat-like conversation with the LLM about test intent
- See clarifications, recommendations, and permission requests as interactive cards
- Review and confirm plans before execution
- Discuss/correct plans when needed
- See plan diffs and apply/reject them
- Handle recovery workflows and locator ambiguity within the chat flow
- See execution progress, recording status, code generation, and completion

All without the frontend inventing state or hiding behind demo placeholders.

---

## Current State Audit

### LLM Tab Existing Implementation

**In `frontend_new_design_prototype/llm-tab.jsx`:**
- Chat/conversation message display (partially designed)
- Plan review card UI
- Clarification question display (partial)
- Recovery card placeholder
- Recommendation card missing

**In `frontend/src/` (production):**
- Minimal LLM Mode integration
- Static demo message stream
- Not wired to live backend events

**Issues:**
1. Frontend renders static demo content in production
2. Backend events (run_started, plan_ready, etc.) exist but not rendered
3. Cards (permission, locator ambiguity, recovery) do not exist in production
4. Conversation is not a sequence of typed events
5. Frontend state store not connected to IDEPanel props

### Backend Event Completeness (from Cluster 2 audit)

| Event | Emitted? | Frontend-visible? | Used by LLM tab? |
|---|---|---|---|
| run_started | Yes | Yes | Partial |
| plan_ready | Yes | Yes | Partial |
| clarification_needed | Yes | Yes | Partial |
| recovery_needed | Yes | Yes | No |
| recommendation_ready | Partial | No | No |
| permission_required | Yes | Yes | No |
| locator_ambiguous | Yes | Yes | No |
| plan_diff_proposed | Partial | No | No |
| code_update | Yes | Yes | No |
| run_completed | Yes | Yes | No |

### Frontend/Backend Seam Status

- **Transport:** WebSocket exists; events reach frontend
- **Store:** Frontend has initial context but not live event reducer
- **IDEPanel props:** Initial; not updated on new events
- **Card components:** Design exists; not wired to backend data
- **Command dispatch:** Typed commands framework exists; not all used

### Design Reference

**Design prototype:** `frontend_new_design_prototype/llm-tab.jsx` (47KB, detailed)
- Message rendering
- Card layouts (clarification, plan, recovery)
- UX states
- **Note:** This is reference only; production extraction must be modular and testable

---

## Source Rules (Priority Order)

1. **PRD v2.3** — `PRD_v2_3_Modular_Pack_v2/03_FRONTEND_RUNTIME.md`, `04_BACKEND_EVENT_CONTRACT.md`
2. **Frontend UI Spec** — `autoworkbench_complete_llm_mode_frontend_ui_spec.md`
3. **Sprint 7 Governance** — `SPRINT-007-CLUSTER-0-GOVERNANCE.md`
4. **Sprint 7 Cluster 2** — `SPRINT-007-CLUSTER-2-LLM-RUNTIME-LIVE-INTEGRATION-GAPS.md`
5. **PRD v2.3 Workflows** — `PRD_v2_3_Modular_Pack_v2/01_PRODUCT_WORKFLOWS.md`

---

## LLM Tab State Matrix

| State | Backend event(s) | Frontend card(s) | User actions | Next state |
|---|---|---|---|---|
| Idle | ready | — | start LLM run | Running |
| Running | run_started | — | (wait for plan or clarification) | Clarifying or Planning |
| Clarifying | clarification_needed | Clarification Card | answer question | Running |
| Planning | plan_ready | Plan Review Card | confirm or send correction | Confirming or Correcting |
| Correcting | plan_diff_proposed → plan_diff_validated | Plan Diff Card | apply or reject | Planning or Confirming |
| Confirming (wait permission) | permission_required | Permission Card | allow or deny | Executing or Recovering |
| Confirming (wait locator) | locator_ambiguous | Locator Ambiguity Card | choose candidate | Executing or Recovering |
| Executing | step_executing → step_recorded | — | (wait) | Executing/Recording or Recovering |
| Recovering | recovery_needed | Recovery Card | retry/skip/stop | Executing or Stopped |
| Stopped | run_completed or run_failed | Completion Card | replay/save/export | Idle |

---

## Backend Event Dependency Table

| Story | Event dependency | Must emit | Must not infer |
|---|---|---|---|
| S7-0601 — Live chat rendering | run_started, user_intent, assistant_summary, runtime_rejected | None (consume only) | Does not mark plan_ready by itself |
| S7-0602 — Clarification card | clarification_needed | answer command | Does not mark answered until backend event |
| S7-0603 — Recommendation card | recommendation_ready | accept_recommendations | Does not auto-confirm recommendations |
| S7-0604 — Plan ready card | plan_ready | confirm_plan | Does not execute before backend accept |
| S7-0605 — Plan correction | correction_needed (internal) or plan_diff_proposed | correction command | Does not apply correction locally |
| S7-0606 — Plan diff card | plan_diff_proposed, plan_diff_validated | apply_diff/reject_diff | Does not mark applied until backend event |
| S7-0607 — Permission card | permission_required | permission_decision | Does not mark allowed/denied until backend event |
| S7-0608 — Locator ambiguity card | locator_ambiguous | choose_candidate | Does not continue until backend validation |
| S7-0609 — Recovery card | recovery_needed | recovery_action | Does not mark recovered until backend event |
| S7-0610 — Completion card | run_completed, run_failed, runtime_rejected | None (consume only) | Does not mark complete before event |

---

## Frontend Command Table

| Story | Command | Payload | Backend behavior |
|---|---|---|---|
| S7-0602 | answer_clarification | run_id, question_id, value | Update planning state |
| S7-0603 | accept_recommendations | run_id, selected_ids[] | Mark recommendations accepted |
| S7-0604 | confirm_plan | run_id, plan_id, plan_version | Start execution or permission gate |
| S7-0605 | send_correction | run_id, message, context | Backend re-plans with user guidance |
| S7-0606 | apply_diff | run_id, plan_id, diff_id | Apply correction, emit new plan_ready |
| S7-0606 | reject_diff | run_id, plan_id, diff_id | Discard correction, stay in plan_ready |
| S7-0607 | permission_decision | run_id, permission_id, decision (allow/deny) | Allow execution or recover |
| S7-0608 | choose_locator_candidate | run_id, step_id, operation_id, candidate_id | Update locator, continue execution |
| S7-0609 | recovery_action | run_id, step_id, action (retry/skip/stop) | Execute action or stop |
| S7-0610 | save_session | run_id, path, name | Save recorded session |
| S7-0610 | load_session | path | Restore recorded session |

---

## No-Frontend-Inference Rules

1. **Do NOT infer execution state.** If `step_executing` not received, do not mark executing.
2. **Do NOT infer recording.** If `step_recorded` not received, do not mark recorded.
3. **Do NOT infer plan confirmation.** If `plan_ready` not received, do not show confirmation button.
4. **Do NOT infer permission granted.** If `permission_required` received and user clicks allow, do not auto-execute. Backend decides if safe.
5. **Do NOT infer locator choice.** If locator_ambiguous received, do not auto-choose candidate.
6. **Do NOT infer recovery completion.** If recovery_needed received, mark state until recovery_* event.
7. **Do NOT infer code generation.** If code_update not received, do not synthesize code.
8. **Do NOT show demo messages in live mode.** If no user/assistant messages from events, show empty state or "waiting" message.
9. **Do NOT fill clarification form with defaults.** Show exact backend question; empty fields until user provides answer.
10. **Do NOT auto-collapse cards.** Keep cards visible until next state event arrives.

---

## Story List

### Cluster 6 Stories (10 total)

| Story | Title | Tier |
|---|---|---|
| S7-0601 | Live chat and conversation rendering | 1 |
| S7-0602 | Clarification card live flow | 1 |
| S7-0603 | Recommendation review card | 1 |
| S7-0604 | Plan ready review card | 1 |
| S7-0605 | Plan correction discussion flow | 1 |
| S7-0606 | Plan diff apply/reject card | 1 |
| S7-0607 | Permission required card | 1 |
| S7-0608 | Locator ambiguity card | 1 |
| S7-0609 | Recovery needed card | 1 |
| S7-0610 | Completed/failed run summary card | 1 |

All Tier 1 (core); interdependent on Cluster 2 events.

---

## Implementation Scope

### Allowed Files

Frontend components:
- `frontend/src/components/llm/**` (new directory for LLM tab components)
- `frontend/src/components/cards/**` (new directory for card components)
- `frontend/src/store/llm_reducer.js` (new if needed)
- `frontend/src/transport/event_handlers.js` (new if needed)
- `frontend/src/commands/llm_commands.js` (new or extend)
- `frontend/src/aw-ide-panel.jsx` (thin wiring only — thread live state into props)
- `frontend/src/main.jsx` (thin wiring only — mount store + transport)

Tests:
- `tests/test_frontend_llm_tab_*.py` (new)
- `tests/test_frontend_event_handlers_*.py` (new)
- `tests/test_frontend_llm_commands.py` (new)

Styling:
- `frontend/src/styles/llm.css` (new)
- `frontend/src/styles/cards.css` (new)

### Forbidden Files

- `runtime/**` — No backend event implementation
- `agent.py` — No LLM runtime changes
- `llm.py` — No model implementation
- `browser.py` — No legacy overlay wiring
- `server.py` or `ws/router.py` — No message routing changes
- Sprint 6 test files — Do not modify
- `.tasks-md/` local noise files
- `AGENTS.md` — No memory changes

---

## Tests-First Requirements

Every story must include:

1. **Unit tests** — reducer logic, event handler functions, command builders
2. **Contract tests** — event payload shapes from backend match expected types
3. **Component render tests** — component accepts typed event data and renders correctly
4. **Command dispatch tests** — user actions dispatch correct typed commands with required fields
5. **Integration tests** — event flow + reducer + component render work together
6. **Negative tests** — malformed events, missing fields, stale commands, unknown events handled safely
7. **Regression tests** — existing tests still pass

### Test File Structure

```
tests/test_frontend_llm_tab_rendering.py       # S7-0601
tests/test_frontend_clarification_card.py      # S7-0602
tests/test_frontend_recommendation_card.py     # S7-0603
tests/test_frontend_plan_ready_card.py         # S7-0604
tests/test_frontend_plan_correction.py         # S7-0605
tests/test_frontend_plan_diff_card.py          # S7-0606
tests/test_frontend_permission_card.py         # S7-0607
tests/test_frontend_locator_ambiguity_card.py  # S7-0608
tests/test_frontend_recovery_card.py           # S7-0609
tests/test_frontend_completion_summary.py      # S7-0610
```

### Key Test Expectations

- **No static demo content in production live mode** — test asserts empty message state before events
- **Render from backend event data only** — test passes typed event object, asserts correct render
- **Unknown events handled safely** — test passes malformed event, asserts no crash + logged warning
- **Stale commands blocked** — test submits command with wrong run_id, asserts rejected or logged
- **Empty/null fields safe** — test passes event with missing optional field, asserts fallback or safe render
- **Card state accurate** — test asserts correct card shown for each backend event type

---

## Component/Browser Test Expectations

Cluster 6 focuses on **component contract tests** and **unit tests**. Browser/Shadow DOM tests are Cluster 4 (E2E).

For Cluster 6:
- React component unit tests (render, props, state)
- Event reducer tests (pure function)
- Command builder tests (output shape, validation)
- Integration tests (event → reducer → component)

**No paid LLM, no real browser E2E in Cluster 6.**

---

## Definition of Done

For Cluster 6:

- [ ] All 10 story files created in `.tasks-md/Planning/` with Planning status
- [ ] Each story includes: source rules, objective, current context, tests-first plan, allowed/forbidden files, acceptance criteria
- [ ] Cluster 6 sprint doc completed (this file)
- [ ] All stories reference Cluster 2 event contracts
- [ ] No implementation code written
- [ ] No tests run
- [ ] No stories moved to In Progress or Done

---

## Stop Conditions

Stop and escalate if:

1. Backend event contract from Cluster 2 is missing or conflicts with LLM tab requirements
2. Frontend state store architecture requires broad refactor of main.jsx or aw-ide-panel.jsx
3. Card component needs backend logic that violates modularization rule
4. Transport layer requires changes to agent.py beyond thin seams
5. Tests cannot be written without accessing live WebSocket or backend state
6. Design prototype reveals inconsistent state model or missing event types

---

## Evidence Requirements

Cluster 6 planning is complete when:

- [ ] `.tasks-md/Sprints/SPRINT-007-CLUSTER-6-LLM-TAB-COMPLETE-LIVE-WORKFLOW.md` exists
- [ ] 10 story files created in `.tasks-md/Planning/` with correct names:
  - S7-0601-Live-chat-and-conversation-rendering.md
  - S7-0602-Clarification-card-live-flow.md
  - S7-0603-Recommendation-review-card.md
  - S7-0604-Plan-ready-review-card.md
  - S7-0605-Plan-correction-discussion-flow.md
  - S7-0606-Plan-diff-apply-reject-card.md
  - S7-0607-Permission-required-card.md
  - S7-0608-Locator-ambiguity-card.md
  - S7-0609-Recovery-needed-card.md
  - S7-0610-Completed-failed-run-summary-card.md
- [ ] All stories in Planning status
- [ ] No implementation code changed
- [ ] Committed to git

---

## Recommended Next Step

After Cluster 6 planning: **Create Sprint 7 Cluster 7 and Cluster 8 planning tickets** (Steps tab, Manual Mode, Recorded/Code/Replay tabs).
