# S6-0601 Deterministic locator candidate pipeline

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Deterministic
**Blocks:** S6-0602, S6-0604, S6-0606
**Blocked by:** Cluster 3 (S6-0307)

---

## Purpose

Produce a ranked list of deterministic locator candidates for a target element, with stability/confidence/risk scores and early-stop on `matched_count == 1`. LLM is never called when a deterministic candidate validates uniquely on the live page.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — locator strategy priority and stability scores
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — P0: prefer testid > role+name > label
- Cluster 3 page intelligence section/ancestor data feeds scoping (in S6-0602)

---

## Current known context

- Cluster 3 produces page/section intelligence (S6-0302).
- No deterministic locator pipeline exists with explicit ranking + stability scoring.
- `nth(index)` is used ad hoc today.

---

## Desired behavior

### Strategy priority (highest first) with stability scores

```
data-testid                              0.98
role + accessible name                   0.95
label (form association)                 0.90
placeholder / alt / title                0.88
aria-* (aria-label, aria-labelledby)     0.80
scoped text (within container)           0.75
stable id (non-generated)                0.70
scoped CSS (class + structural)          0.60
XPath (last resort)                      0.40
```

### Pipeline

1. Build candidates in priority order.
2. For each, compute `stability`, `confidence`, `risk`.
3. Live-validate (count occurrences) top candidates.
4. **Early stop**: first candidate with `matched_count == 1` wins; pipeline returns it.
5. If none unique → return ranked candidate list to S6-0602 (scoping) for duplicate resolution.

### Outputs

```
LocatorCandidate = {
  strategy, locator_expression,
  stability, confidence, risk,
  matched_count (after live validation, optional)
}
```

---

## Out of scope

- Scoping / chaining (S6-0602)
- Weak-DOM heuristics (S6-0603)
- Ambiguity user choice (S6-0604)
- Specialist call (S6-0605)

---

## Allowed files

- `runtime/locator_deterministic.py` (new)
- `tests/test_locator_deterministic.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM dump into prompts
- ✗ Silent `nth(index)` selection
- ✗ Unvalidated activation

---

## Tests first

### Unit

- `test_data_testid_strategy_emits_highest_stability_0_98`.
- `test_role_plus_name_strategy_emits_0_95`.
- `test_label_strategy_emits_0_90`.
- `test_placeholder_strategy_emits_0_88`.
- `test_aria_strategy_emits_0_80`.
- `test_scoped_text_strategy_emits_0_75`.
- `test_stable_id_strategy_emits_0_70`.
- `test_scoped_css_strategy_emits_0_60`.
- `test_xpath_strategy_emits_0_40_and_is_last_resort`.
- `test_ranking_orders_candidates_by_stability_descending`.

### Contract

- `test_pipeline_returns_locator_candidate_objects_with_required_fields`.
- `test_pipeline_calls_live_validation_in_priority_order`.
- `test_pipeline_early_stops_on_first_unique_candidate` (no further validation calls).
- `test_pipeline_returns_full_ranked_list_when_none_unique`.

### Integration

- `test_pipeline_does_not_invoke_llm_when_deterministic_candidate_is_unique`.
- `test_pipeline_handles_zero_match_candidates_without_crash`.

### Negative

- `test_pipeline_rejects_generated_id_as_unstable` (e.g., `id="user-123abc"`).
- `test_xpath_is_never_selected_when_higher_strategy_is_available`.
- `test_pipeline_does_not_emit_nth_index_as_a_candidate`.

### Regression

- Cluster 3 page intelligence tests pass.
- Cluster 2 token budget tests pass.

---

## Implementation notes

1. Strategies implemented as small composable functions returning `LocatorCandidate | None`.
2. Live validation is injected (so tests can stub).
3. Stability constants live in a module-level dict; tests assert exact values.
4. `risk` derives from stability and ancestor stability hints (placeholder; refined in S6-0602).

### Key invariants

- LLM never called in this module.
- `nth(index)` not emitted here.
- Ranking is total and deterministic.

---

## Coverage target

**95%** on `runtime/locator_deterministic.py`.

---

## Stop conditions

- Strategy priority disputed → freeze on the table above; deviations are bugs.
- Live validator unavailable in test env → use injectable fake.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] Cluster 0 / 1 / 2 / 3 tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] 9 strategies ranked with exact stability scores
- [ ] Early stop on first unique candidate
- [ ] Returns ranked list when none unique
- [ ] No LLM call from this module
- [ ] No `nth(index)` candidates emitted
- [ ] 95% coverage
- [ ] Regression guard green
