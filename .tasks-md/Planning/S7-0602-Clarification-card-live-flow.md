# S7-0602 — Clarification Card Live Flow

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2  

---

## Objective

Render `clarification_needed` backend events as an interactive card that lets users answer questions and dispatch `answer_clarification` commands. Frontend must never auto-fill or assume default answers.

Today: Clarification partially shown; no full interactive flow.
After S7-0602: User sees exact backend question, required/optional fields, options if provided, submits typed answer, frontend blocks stale answers.

---

## Source Rules

1. **PRD-04-BE-001:** clarification_needed event includes run_id, question, options[], step_id
2. **PRD-03-FE-001:** Clarification card renders exact backend question; no inference
3. **PRD-03-FE-002:** Frontend dispatches answer_clarification command with run_id, question_id, value
4. **PRD-03-FE-003:** Empty/missing options fallback to text input field safely
5. **GOV-S7-C0-006:** Frontend must not infer lifecycle truth; wait for backend answer confirmation

---

## Current Known Context

### What exists

- `frontend_new_design_prototype/llm-tab.jsx` — Clarification card UI (reference)
- Backend emits `clarification_needed` event (Cluster 2)
- Question and options structure defined in PRD
- No clarification component in production frontend yet

### What gaps exist

- No Clarification Card component
- No answer_clarification command builder
- No question_id tracking for stale answer rejection
- No form validation (required vs. optional fields)
- Fallback text input not implemented if no options provided

### Test status

- No tests for clarification card
- Answer command validation not tested

---

## Tests First

### Unit Tests

```
test_answer_clarification_command_includes_run_id_question_id_value()
test_empty_answer_rejected_for_required_field()
test_optional_answer_field_accepts_empty_string()
test_stale_question_id_answer_blocked()
test_fallback_text_input_when_no_options()
```

File: `tests/test_frontend_clarification_card.py`

### Contract Tests

```
test_clarification_needed_event_payload_shape()
test_question_field_not_empty()
test_options_array_serializable()
test_answer_command_payload_shape()
```

### Component Tests

```
test_clarification_card_renders_question()
test_clarification_card_renders_options_as_buttons()
test_clarification_card_shows_fallback_text_input()
test_clarification_card_disables_submit_until_answer_filled()
test_clarification_card_hidden_when_no_clarification_event()
```

### Negative Tests

```
test_malformed_options_handled_safely()
test_missing_question_id_rejected()
test_null_options_array_falls_back_to_text()
test_submit_with_stale_question_id_blocked()
test_double_submit_ignored()
```

### Integration Tests

```
test_clarification_needed_event_shows_card()
test_answer_dispatches_answer_clarification_command()
test_new_clarification_event_replaces_old_card()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/ClarificationCard.jsx`
- **New:** `frontend/src/store/clarification_reducer.js`
- **New:** `frontend/src/commands/clarification_commands.js`
- **New:** `tests/test_frontend_clarification_card.py`
- **Modify:** `frontend/src/aw-ide-panel.jsx` (thin wiring only)
- **Modify:** `frontend/src/store/` reducer hooks

### Forbidden Files

- No backend changes
- No runtime changes
- No monolith expansion

---

## Implementation Notes

### Approach

1. Define clarification state:
   - `{ question, options[], question_id, run_id, answered: false }`

2. Create reducer:
   - Action: `SET_CLARIFICATION(event)` → store question+options+ids
   - Action: `SUBMIT_ANSWER(value)` → dispatch command, mark answered

3. Create ClarificationCard component:
   - If options exist: radio/checkbox buttons
   - If no options: text input field
   - Submit button disabled until answer provided
   - Show current question_id in disabled state

4. Answer validation:
   - question_id must match current question (block stale answers)
   - value must not be empty for required fields
   - Dispatch `answer_clarification { run_id, question_id, value }`

5. State management:
   - New clarification event replaces previous
   - Card hidden when answered or new plan_ready event received

### Key Invariants

- Question text from backend, not inferred
- Options rendered exactly as received
- Submit blocked until user provides answer
- Stale question_id answers rejected

---

## Acceptance Criteria

- [ ] ClarificationCard renders exact backend question
- [ ] Options (if provided) render as interactive buttons
- [ ] No options → fallback text input appears
- [ ] Submit button disabled until answer filled
- [ ] answer_clarification command includes all required fields
- [ ] Stale answers blocked (question_id mismatch)
- [ ] New clarification event replaces old card
- [ ] No frontend inference of answer correctness
- [ ] All tests pass

---

## Evidence Required

- [ ] `frontend/src/components/cards/ClarificationCard.jsx` exists
- [ ] `tests/test_frontend_clarification_card.py` passes
- [ ] All unit/contract/component/negative/integration tests green
- [ ] Coverage ≥ 95%
- [ ] Story updated with commit hash

---

## Stop Conditions

- Backend clarification_needed event missing question or question_id
- Card requires inferring whether answer is correct
- Options structure conflicts with PRD definition
- Stale answer blocking requires complex session tracking
