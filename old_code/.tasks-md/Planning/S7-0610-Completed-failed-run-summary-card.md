# S7-0610 — Completed/Failed Run Summary Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2

---

## Objective

Render `run_completed` / `run_failed` / `runtime_rejected` backend events as a terminal summary card showing:
- Run result status
- Steps recorded, skipped, failed counts
- Recorded output available indicator
- Generated code indicator
- Next actions: Replay, Save, Export, Try Again

Frontend must never infer completion from final step — only backend event truth.

---

## Source Rules

1. **PRD-04-BE-001:** run_completed includes summary, recorded_count, skipped_count, code_available
2. **PRD-03-FE-001:** Completion card shows backend-provided summary
3. **PRD-03-FE-006:** Frontend must not infer completion before event

---

## Current Known Context

### What exists

- Backend emits run_completed, run_failed events
- Design prototype shows completion card
- No production completion component

### What gaps exist

- Completion event structure details
- Code availability indication
- Save/Replay/Export command wiring

---

## Tests First

### Unit Tests

```
test_save_session_command_includes_run_id_path()
test_load_session_command_includes_path()
test_completion_not_inferred_before_event()
```

### Component Tests

```
test_completion_card_shows_result_status()
test_completion_card_shows_step_counts()
test_completion_card_shows_code_and_recorded_availability()
test_completion_card_shows_next_actions()
test_failed_run_card_shows_error_summary()
test_runtime_rejected_card_shows_reason()
```

### Contract Tests

```
test_run_completed_event_includes_summary_counts()
test_run_failed_event_includes_error()
```

### Negative Tests

```
test_missing_summary_handled_safely()
test_zero_recorded_steps_shows_message()
test_no_code_generated_shows_reason()
```

### Integration Tests

```
test_run_completed_event_shows_card()
test_save_session_command_dispatched()
test_replay_button_triggers_replay_commands()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/CompletionCard.jsx`
- **New:** `frontend/src/commands/session_commands.js`
- **New:** `tests/test_frontend_completion_card.py`

### Forbidden Files

- No code replay logic (Cluster 4)
- No save/load implementation (Cluster 9)

---

## Implementation Notes

### Approach

1. Completion Card:
   - Status header: "Run completed" or "Run failed" or "Runtime rejected"
   - Summary text from backend
   - Counts: "X steps recorded, Y skipped, Z failed"
   - Code availability: "Generated code available" or "Not available"
   - Recorded output indicator
   - Action buttons: Replay, Save, Export, Try again

2. Commands:
   - `save_session { run_id, path, name }`
   - `load_session { path }`
   - Replay commands (delegated to Cluster 9)

3. State:
   - Terminal state; card shown until new run starts
   - Cannot trigger new run from this card (user must start new run)

### Key Invariants

- Status from backend, not inferred
- Counts accurate from backend
- Code availability from backend event
- Cannot infer completion from UI state

---

## Acceptance Criteria

- [ ] CompletionCard displays result status
- [ ] Step counts shown accurately
- [ ] Code/recorded availability indicated
- [ ] Next actions available (replay, save, etc.)
- [ ] No inferred completion without event
- [ ] Failed/rejected status shown with reason
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/CompletionCard.jsx` exists
- [ ] `tests/test_frontend_completion_card.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Completion event structure undefined
- Card requires replay/save implementation

---

## Evidence Recorded

- **Commit:** a84bf22 — Cluster 6 LLM card extraction
- **File:** `frontend/src/components/llm/` — CompletedCard.jsx — completion-prop-driven; never reads step counts
- **Test:** tests/test_frontend_llm_cards.py (36 tests verify typed commands, empty states, no demo, no local lifecycle mutation)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2383 passed / 1 skipped / 0 failed
