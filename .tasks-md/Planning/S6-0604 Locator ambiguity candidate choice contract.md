# S6-0604 Locator ambiguity candidate choice contract

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Ambiguity
**Blocks:** S6-0606
**Blocked by:** S6-0602

---

## Purpose

When deterministic + scoped strategies still yield `matched_count > 1`, surface a typed `LocatorAmbiguous` event with stable candidate IDs and user-readable labels. Execution is blocked until the user picks a candidate; the backend then live-validates and activates only on unique match.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — ambiguity is a typed user-visible state
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — "the one in the dialog" / "the second row"
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — ambiguity candidate chooser

---

## Current known context

- S6-0602 emits `locator_ambiguous` signal when no scope yields unique match.
- No stable candidate ID scheme, no user-readable labels, no activation guard exists.

---

## Desired behavior

### Event

```
LocatorAmbiguous {
  operation_id,
  candidates: [{
    candidate_id (stable),
    locator_expression,
    scope_container,
    scope_priority,
    user_readable_label,   # e.g., "Save button in 'Edit Profile' dialog"
    stability,
    risk
  }]
}
```

### User round-trip

```
LocatorAmbiguous (backend → frontend)
select_candidate(operation_id, candidate_id) (frontend → backend)
backend live-validates → matched_count must be 1 → activate
```

### Rules

- Execution is blocked while ambiguous.
- Candidate IDs are stable across the round-trip (idempotent re-emission yields same IDs).
- Activation requires backend live validation, `matched_count == 1`.
- `nth(index)` candidates appear only when explicitly allowed (S6-0602 flag) and labelled accordingly.

---

## Out of scope

- Specialist call (S6-0605)
- Context persistence (S6-0606)
- Update flow (S6-0607)

---

## Allowed files

- `runtime/locator_ambiguity.py` (new)
- `tests/test_locator_ambiguity.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM dump in event payload
- ✗ Silent activation of any candidate
- ✗ Unstable / random candidate IDs

---

## Tests first

### Unit

- `test_candidate_id_is_stable_across_re_emission`.
- `test_user_readable_label_includes_scope_and_target_semantic`.
- `test_event_payload_excludes_raw_dom`.
- `test_event_payload_includes_stability_and_risk_per_candidate`.

### Contract

- `test_locator_ambiguous_event_schema_typed`.
- `test_execution_is_blocked_while_ambiguous_state_active`.
- `test_select_candidate_endpoint_requires_operation_id_and_candidate_id`.
- `test_activation_requires_live_validation_matched_count_eq_1`.

### Integration

- `test_user_selects_candidate_then_backend_validates_then_activates`.
- `test_user_selects_candidate_that_no_longer_matches_emits_revalidation_failed_no_activation`.
- `test_re_emission_after_unrelated_event_preserves_candidate_ids`.

### Negative

- `test_select_candidate_with_unknown_candidate_id_is_rejected`.
- `test_select_candidate_for_stale_operation_id_is_rejected`.
- `test_no_activation_when_matched_count_is_zero_or_greater_than_one`.
- `test_nth_index_candidate_label_explicitly_warns_user`.

### Regression

- S6-0602 scoping tests pass.
- Cluster 2 tool exposure / enforcement tests pass.

---

## Implementation notes

1. Candidate ID = hash of `(scope_container, locator_expression, scope_priority)`; deterministic.
2. Event bus carries the typed event; no DOM blobs.
3. Activation path runs backend live validation, then writes the selected candidate as the active locator.

### Key invariants

- No activation without backend-validated unique match.
- Candidate IDs deterministic across retries.

---

## Coverage target

**95%** on `runtime/locator_ambiguity.py`.

---

## Stop conditions

- Candidate ID hash collisions detected → expand hash inputs; do not lower coverage.
- User-readable label generation undecided → freeze on `<role> '<name>' in '<scope_container>'`.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0601 / S6-0602 tests pass
- [ ] Cluster 2 / 3 tests pass

---

## Acceptance criteria / Sign-off

- [ ] Typed ambiguity event with stable candidate IDs
- [ ] User-readable labels include scope + target
- [ ] Execution blocked while ambiguous
- [ ] Activation gated by live `matched_count == 1`
- [ ] No raw DOM in payload
- [ ] 95% coverage
- [ ] Regression guard green
