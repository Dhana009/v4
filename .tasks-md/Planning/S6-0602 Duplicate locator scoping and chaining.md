# S6-0602 Duplicate locator scoping and chaining

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Scoping
**Blocks:** S6-0604, S6-0606
**Blocked by:** S6-0601

---

## Purpose

When the deterministic pipeline yields multiple matches, resolve duplicates with container scoping and Playwright chaining (`filter`, `has`, `hasText`, role+name within container) **before** calling the locator specialist. `nth(index)` is explicitly fragile (stability 0.15) and requires explicit user approval.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — scoping priority, chaining patterns, nth fragility
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — "the one in the dialog", "in the second row"

---

## Current known context

- S6-0601 returns a ranked candidate list when no candidate is unique.
- No standardized container priority or chaining policy exists today.

---

## Desired behavior

### Container priority (highest first)

```
dialog > form > table-row > card > section > fieldset > list-item
```

### Chaining patterns

- `container.filter({ hasText })`
- `container.locator(...).filter({ has: ... })`
- `container.getByRole(...).filter({ hasText })`
- Combine with the highest-priority deterministic strategy inside the container.

### Rules

- Try scopes in priority order; first scope that yields `matched_count == 1` wins.
- If no scope yields a unique match → emit `locator_ambiguous` (handled by S6-0604).
- `nth(index)` candidates have stability `0.15` and **require explicit user approval**; never auto-selected.

### Output

`ScopedLocatorCandidate = LocatorCandidate + {scope_container, scope_priority}`.

---

## Out of scope

- Specialist invocation (S6-0605)
- Ambiguity user choice surface (S6-0604)
- Weak-DOM (S6-0603)

---

## Allowed files

- `runtime/locator_scoping.py` (new)
- `tests/test_locator_scoping.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM dump
- ✗ Silent `nth(index)` activation
- ✗ Unvalidated activation

---

## Tests first

### Unit

- `test_scope_priority_dialog_first_then_form_then_table_row_then_card_then_section_then_fieldset_then_list_item`.
- `test_filter_hasText_pattern_produces_scoped_candidate`.
- `test_has_pattern_produces_scoped_candidate`.
- `test_role_plus_name_within_container_produces_scoped_candidate`.
- `test_nth_index_candidate_has_stability_0_15`.
- `test_nth_index_candidate_is_marked_requires_user_approval`.

### Contract

- `test_scoping_returns_first_unique_match_across_scopes_in_priority_order`.
- `test_scoping_emits_locator_ambiguous_event_when_no_scope_unique`.
- `test_scoping_skips_llm_when_scoped_candidate_is_unique`.
- `test_scoped_candidate_includes_scope_container_and_scope_priority_fields`.

### Integration

- `test_two_buttons_named_save_resolve_via_dialog_scope`.
- `test_three_rows_with_edit_resolve_via_table_row_scope_with_hasText`.

### Negative

- `test_nth_index_is_never_auto_selected_even_when_uniquely_matched`.
- `test_no_silent_activation_of_ambiguous_candidate`.
- `test_scope_outside_priority_list_is_ignored`.

### Regression

- S6-0601 tests pass.
- Cluster 3 section / ancestor headings tests pass.

---

## Implementation notes

1. Container detection consumes Cluster 3 section/ancestor heading data.
2. Chaining helpers produce a typed `ScopedLocatorCandidate`.
3. `nth` support exists but produces a candidate flagged `requires_user_approval=True`.
4. Live validation is injected for testability.

### Key invariants

- Specialist not called from this module.
- Ambiguity is surfaced, never silently resolved by `nth(index)`.

---

## Coverage target

**95%** on `runtime/locator_scoping.py`.

---

## Stop conditions

- Container priority disputed → freeze on the 7 listed.
- Ambiguity persists after all scopes → emit `locator_ambiguous`, defer to S6-0604.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0601 tests pass
- [ ] Cluster 3 tests pass
- [ ] Cluster 2 enforcement tests pass

---

## Acceptance criteria / Sign-off

- [ ] 7-tier scope priority enforced
- [ ] 4 chaining patterns supported
- [ ] First-unique-wins across scopes
- [ ] `nth` stability `0.15`, requires user approval, never auto-selected
- [ ] No specialist call from this module
- [ ] 95% coverage
- [ ] Regression guard green
