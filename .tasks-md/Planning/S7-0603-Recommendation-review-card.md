# S7-0603 — Recommendation Review Card

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Planning  
**Owner:** Frontend  
**Blocked by:** S7-0601, Cluster 2

---

## Objective

Render `recommendation_ready` backend events as an interactive card showing grouped recommendations that users can select/deselect, then accept. Recommendations are proposal/draft only — they do not execute until user confirms and backend validates.

After S7-0603: Users see available recommendations, can select/add custom assertions, and dispatch `accept_recommendations` command with selected IDs.

---

## Source Rules

1. **PRD-02-LLM-005:** Recommendations are page_validation_recommender LLM output (proposals only)
2. **PRD-04-BE-001:** recommendation_ready event includes request_id, recommendations[], timestamp
3. **PRD-03-FE-001:** Recommendation card renders backend payload structure exactly
4. **PRD-03-FE-006:** Recommendations do not auto-apply; user must select and confirm

---

## Current Known Context

### What exists

- Backend emits recommendation_ready event (from Cluster 2)
- Design prototype shows recommendation card layout
- No production recommendation component yet

### What gaps exist

- No RecommendationCard component
- No selected/unselected state tracking
- No accept_recommendations command builder
- Payload structure from backend unclear (section grouping)

### Test status

- No recommendation component tests

---

## Tests First

### Unit Tests

```
test_select_recommendation_toggles_selected_state()
test_accept_selected_recommendations_includes_ids()
test_no_selected_recommendations_disables_accept()
test_custom_assertion_addable_to_selected()
```

### Component Tests

```
test_recommendation_card_renders_section_groups()
test_recommendation_card_renders_selectable_items()
test_recommendation_card_shows_add_custom_assertion_action()
test_recommendation_card_hidden_when_no_recommendation_event()
test_accept_button_disabled_when_no_selection()
```

### Contract Tests

```
test_recommendation_ready_payload_includes_request_id_recommendations()
test_recommendation_item_has_id_label_confidence()
test_recommendations_grouped_by_section()
```

### Negative Tests

```
test_malformed_recommendations_handled_safely()
test_missing_recommendation_ids_blocked()
test_empty_recommendations_array_shows_safe_message()
```

### Integration Tests

```
test_recommendation_ready_event_shows_card()
test_select_recommendation_updates_card_state()
test_accept_recommendations_command_dispatched_with_selected_ids()
```

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/cards/RecommendationCard.jsx`
- **New:** `frontend/src/store/recommendation_reducer.js`
- **New:** `frontend/src/commands/recommendation_commands.js`
- **New:** `tests/test_frontend_recommendation_card.py`
- **Modify:** `frontend/src/aw-ide-panel.jsx` (thin wiring only)

### Forbidden Files

- No backend changes
- No LLM changes

---

## Implementation Notes

### Approach

1. Define recommendation state:
   - `{ recommendations[], selected_ids[], custom_assertions[] }`

2. Create reducer:
   - Action: `SET_RECOMMENDATIONS(event)` → store recommendations
   - Action: `TOGGLE_SELECTED(id)` → add/remove from selected_ids
   - Action: `ADD_CUSTOM_ASSERTION(assertion)` → append to custom_assertions

3. Create RecommendationCard:
   - Group recommendations by section if structure supports it
   - Render each as selectable item (checkbox + label)
   - Show confidence or risk indicator
   - "Add custom assertion" button
   - "Accept selected" button (disabled if empty selection)

4. Command dispatch:
   - `accept_recommendations { request_id, selected_ids[], custom_assertions? }`

### Key Invariants

- Recommendations shown as draft (not auto-applied)
- User must explicitly select items
- No selection → accept disabled
- Backend validates before execution

---

## Acceptance Criteria

- [ ] RecommendationCard renders recommendations from backend event
- [ ] Items grouped by section (if applicable)
- [ ] User can select/deselect items
- [ ] Accept button disabled when no selection
- [ ] accept_recommendations command sent with selected IDs
- [ ] Custom assertion option available
- [ ] No auto-execution of recommendations
- [ ] All tests pass, coverage ≥ 95%

---

## Evidence Required

- [ ] `frontend/src/components/cards/RecommendationCard.jsx` exists
- [ ] `tests/test_frontend_recommendation_card.py` passes
- [ ] All tests green, coverage ≥ 95%

---

## Stop Conditions

- Recommendations structure from backend undefined
- Card requires backend execution logic
- Selection state tracking becomes complex without clear reducer pattern
