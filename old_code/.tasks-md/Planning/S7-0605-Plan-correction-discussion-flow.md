# S7-0605 — Plan Correction Discussion Flow

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0601, S7-0604, Cluster 2

---

## Objective

Allow users to send correction/discussion messages during plan_ready without mutating the active plan. Backend responds with either plan_diff (for structural changes) or corrected plan_ready (for acceptance). Frontend must not locally reorder/remove/modify steps.

After S7-0605: Users can type corrections in plan review, dispatch correction command, see backend response (plan_diff or new plan_ready).

---

## Source Rules

1. **PRD-03-FE-001:** Frontend does not locally modify plan structure
2. **PRD-03-FE-002:** Corrections are proposals sent to backend for re-planning
3. **PRD-04-BE-001:** Backend responds with plan_diff_proposed or new plan_ready

---

## Current Known Context

### What exists

- design prototype shows correction input in plan card
- Backend handles correction logic
- No correction command builder

### What gaps exist

- No correction message input in PlanReadyCard
- No send_correction command implementation
- No distinction between discussion vs. structural change responses

---

## Tests First

### Unit Tests

```
test_correction_command_includes_message_and_context()
test_empty_correction_rejected()
```

### Component Tests

```
test_plan_card_has_correction_input_field()
test_send_correction_button_enabled_with_text()
test_correction_input_cleared_after_send()
```

### Contract Tests

```
test_correction_command_payload_shape()
```

### Negative Tests

```
test_empty_correction_blocked()
test_stale_correction_with_old_plan_version_handled()
```

### Integration Tests

```
test_correction_command_dispatched_with_message()
test_plan_diff_response_shows_diff_card()
test_corrected_plan_ready_replaces_current_plan()
```

---

## Implementation Boundaries

### Allowed Files

- **Modify:** `frontend/src/components/cards/PlanReadyCard.jsx` (add correction input)
- **New:** `frontend/src/commands/correction_commands.js`
- **New:** `tests/test_frontend_correction_flow.py`

### Forbidden Files

- No plan mutation logic
- No local reordering

---

## Implementation Notes

### Approach

1. Add correction input to PlanReadyCard:
   - Text input field below plan details
   - "Send Correction" button (enabled when text provided)
   - Clear input after submission

2. Create correction command:
   - `send_correction { run_id, plan_id, message, context? }`

3. Handle responses:
   - If `plan_diff_proposed` → show diff card (S7-0606 handles)
   - If new `plan_ready` → replace current plan, re-show confirmation

### Key Invariants

- No local plan changes
- Backend decides structural changes
- Correction message from user input (not inferred)

---

## Acceptance Criteria

- [ ] Correction input visible in PlanReadyCard
- [ ] Send button enabled with message, disabled when empty
- [ ] correction command dispatched with all fields
- [ ] No local plan mutation
- [ ] Backend response (diff or new plan) handled correctly
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] PlanReadyCard updated with correction input
- [ ] `frontend/src/commands/correction_commands.js` created
- [ ] `tests/test_frontend_correction_flow.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Backend correction response structure undefined
- Card logic becomes too large for single component

---

## Evidence Recorded

- **Commit:** a84bf22 — Cluster 6 LLM card extraction
- **File:** `frontend/src/components/llm/` — CorrectionCard.jsx — correction typed; no setPlan() locally
- **Test:** tests/test_frontend_llm_cards.py (36 tests verify typed commands, empty states, no demo, no local lifecycle mutation)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2383 passed / 1 skipped / 0 failed
