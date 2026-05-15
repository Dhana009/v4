# S6-0502 Explicit apply update mutation boundary

## Metadata

**Sprint:** Sprint 6
**Cluster:** 5
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Plan Mutation Boundary
**Blocks:** S6-0503, S6-0504, S6-0506
**Blocked by:** S6-0501

---

## Purpose

Define the single, explicit boundary that crosses from `plan_revision_discussion` into a plan-mutation flow. Only utterances classified as `apply_revision`, `update`, `make_this_change`, or `confirm_this_version` may emit a mutation request, and only when paired with a valid `(plan_id, plan_version)` matching the active plan.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — "Mutation requires explicit apply intent and current plan version."
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — scenarios: "remove step 3 and apply", "apply this revision", "confirm this version".
- PRD plan lifecycle: stale-plan rejection.

---

## Current known context

- S6-0501 emits `apply_revision` intent but does not act on it.
- No mutation-request schema exists; no stale-plan rejection exists.

---

## Desired behavior

### High-level expectation

- A `MutationRequest` is produced only on explicit apply/update language.
- Each `MutationRequest` carries `(plan_id, plan_version, intent_phrase, utterance)`.
- Requests with missing or mismatched version → reject with `stale_plan`.
- Ambiguous mutation language (e.g., "maybe remove X") → emit `clarification_needed`, no request created.
- Mutation requests are handed to S6-0503 (diff generator), never executed directly.

### Interface (sketch)

```
detect_mutation_request(utterance, active_plan) -> MutationRequest | None | ClarificationNeeded
MutationRequest = {plan_id, plan_version, intent_phrase, utterance}
```

---

## Out of scope

- Diff schema (S6-0503)
- Diff validation (S6-0503)
- Lifecycle / corrected_plan_ready (S6-0504)
- Direct frontend edits (S6-0505)

---

## Allowed files

- `runtime/plan_mutation_boundary.py` (new)
- `tests/test_plan_mutation_boundary.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Direct mutation of active plan
- ✗ Recording / code_update during boundary check

---

## Tests first

### Unit

- `test_apply_phrase_emits_mutation_request` (apply, update, make this change, confirm this version).
- `test_speculative_phrase_emits_nothing` ("maybe remove X", "what if we drop step 2").
- `test_pure_question_emits_nothing` ("why is step 4 here?").
- `test_request_carries_active_plan_id_and_version`.
- `test_ambiguous_mutation_emits_clarification_needed` ("change it" without target).

### Contract

- `test_mutation_request_schema_has_required_fields`.
- `test_stale_plan_version_is_rejected_with_typed_error`.
- `test_missing_plan_id_is_rejected`.
- `test_boundary_does_not_mutate_active_plan`.

### Integration

- `test_discussion_to_mutation_transition_only_on_apply_intent` (with S6-0501 classifier).
- `test_concurrent_plan_advance_invalidates_in_flight_request` (active plan moved to v=N+1; request at v=N rejected).

### Negative

- `test_request_with_future_plan_version_is_rejected`.
- `test_request_with_unknown_plan_id_is_rejected`.
- `test_intent_phrase_in_quoted_string_is_not_treated_as_apply` ("the user said 'apply this'" stays `discuss_only`).

### Regression

- S6-0501 discussion tests still pass.
- Cluster 4 plan lifecycle tests still pass.

---

## Implementation notes

1. Phrase set lives in a typed constant; classifier returns `MutationRequest | None | ClarificationNeeded`.
2. Stale-plan check compares `(plan_id, plan_version)` against active plan store.
3. The boundary is the *only* path that produces a `MutationRequest`; later stories assert this.

### Key invariants

- No `MutationRequest` is ever created without explicit apply intent.
- Stale `(plan_id, plan_version)` always rejected before any downstream call.

---

## Coverage target

**95%** on `runtime/plan_mutation_boundary.py`.

---

## Stop conditions

- Apply phrase set incomplete or ambiguous → expand carefully and re-run classifier negatives.
- Active plan store contract unclear → defer to a tiny in-memory adapter for tests.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0501 tests pass
- [ ] Cluster 4 lifecycle tests pass
- [ ] Cluster 2 enforcement tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] Mutation requests created only on explicit apply intent
- [ ] All requests carry valid `(plan_id, plan_version)`
- [ ] Stale plans rejected
- [ ] Speculative phrases never cross the boundary
- [ ] 95% coverage
- [ ] Regression guard green
