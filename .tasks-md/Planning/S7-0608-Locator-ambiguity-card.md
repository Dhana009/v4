# S7-0608 — Locator Ambiguity Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2

---

## Objective

Render `locator_ambiguous` backend events as an interactive card showing:
- Multiple candidate locators with IDs
- Semantic labels and scopes
- Confidence/fragility warnings
- Preview/highlight option
- Choose candidate button

Selection dispatches `choose_locator_candidate` command; backend validates before execution.

---

## Source Rules

1. **PRD-04-BE-001:** locator_ambiguous includes candidates[{id, label, scope, confidence, risk}]
2. **PRD-03-FE-001:** Candidate list rendered exactly as backend provides
3. **PRD-03-FE-006:** Backend validates candidate before execution

---

## Current Known Context

### What exists

- Backend emits locator_ambiguous event
- Locator candidate structure defined in Cluster 2
- No LocatorAmbiguityCard component

### What gaps exist

- Candidate preview/highlight not implemented
- Risk display (fragility warnings)
- choose_locator_candidate command structure

---

## Tests First

### Unit Tests

```
test_choose_candidate_command_includes_candidate_id()
test_empty_candidates_shows_safe_message()
```

### Component Tests

```
test_locator_card_renders_candidate_list()
test_locator_card_shows_confidence_and_risk()
test_locator_card_has_inspect_highlight_action()
test_use_candidate_button_requires_selection()
test_locator_card_hidden_when_no_ambiguity_event()
```

### Contract Tests

```
test_locator_ambiguous_event_includes_candidates()
test_candidate_has_id_label_scope()
```

### Negative Tests

```
test_missing_candidate_ids_rejected()
test_malformed_candidate_data_handled()
test_empty_candidates_array_shows_message()
```

### Integration Tests

```
test_locator_ambiguous_event_shows_card()
test_candidate_selection_updates_card_state()
test_choose_candidate_command_dispatched()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/LocatorAmbiguityCard.jsx`
- **New:** `frontend/src/commands/locator_commands.js`
- **New:** `tests/test_frontend_locator_ambiguity_card.py`

### Forbidden Files

- No picker integration (Cluster 7 scope)
- No locator validation logic
- No browser highlight (Cluster 4 scope)

---

## Implementation Notes

### Approach

1. Candidate list rendering:
   - Each candidate: ID, semantic label, scope, confidence
   - Risk/fragility indicator
   - Radio/button for selection

2. Actions:
   - Inspect/Highlight button (action only; preview in future)
   - Use Candidate button (enabled when selected)

3. Command:
   - `choose_locator_candidate { run_id, step_id, operation_id, candidate_id }`

### Key Invariants

- Candidates from backend, not inferred
- User must choose explicitly
- Backend validates before execution

---

## Acceptance Criteria

- [ ] LocatorAmbiguityCard renders candidate list
- [ ] Confidence and risk displayed
- [ ] User can select one candidate
- [ ] Use Candidate button disabled until selection
- [ ] choose_locator_candidate command sent with all IDs
- [ ] Backend validation required before continuation
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/LocatorAmbiguityCard.jsx` exists
- [ ] `tests/test_frontend_locator_ambiguity_card.py` passes
- [ ] Coverage ≥ 95%

---

## Stop Conditions

- Candidate structure from backend undefined
- Card requires browser highlight/inspect
- Picker integration needed

---

## Evidence Recorded

- **Commit:** a84bf22 — Cluster 6 LLM card extraction
- **File:** `frontend/src/components/llm/` — LocatorAmbiguityCard.jsx — choose_locator_candidate typed; no local activation
- **Test:** tests/test_frontend_llm_cards.py (36 tests verify typed commands, empty states, no demo, no local lifecycle mutation)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2383 passed / 1 skipped / 0 failed
