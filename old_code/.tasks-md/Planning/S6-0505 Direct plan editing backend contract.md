# S6-0505 Direct plan editing backend contract

## Metadata

**Sprint:** Sprint 6
**Cluster:** 5
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Direct Plan Edit
**Blocks:** S6-0506
**Blocked by:** S6-0503

---

## Purpose

Frontend direct-edit commands on the Plan tab (change text, drag/reorder, delete, duplicate, edit expected outcome) must translate into typed `plan_diff` requests and flow through the same validator as LLM-proposed corrections. The frontend cannot directly replace the active plan object. Edits that risk dependent steps emit a `dependency_warning` event.

---

## Source rules

- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — Plan tab direct edits: change text, reorder via drag, delete, duplicate, edit expected outcome.
- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — "Direct edits flow through the same validator; backend is the single source of truth."
- PRD: dependency warning surfaces when edit threatens dependents.

---

## Current known context

- S6-0503 supplies the diff schema and validator.
- S6-0504 supplies the apply lifecycle.
- Frontend currently has no typed direct-edit contract; this story defines the backend half only.

---

## Desired behavior

### Edit-command → DiffOperation mapping

```
edit_text(step_id, new_text)                  -> REPLACE
reorder(parent_step_id?, new_order)           -> REORDER
delete(step_id, promote_children?)            -> REMOVE
duplicate(step_id)                            -> ADD (cloned step at position+1)
edit_expected_outcome(step_id, new_outcome)   -> CHANGE_EXPECTED_OUTCOME
```

### Rules

- Each command requires `(plan_id, plan_version)` from the frontend.
- The backend translates to a `PlanDiff` and submits to the S6-0503 validator.
- On validator success → S6-0504 lifecycle (corrected_plan_ready, fresh confirmation).
- Delete on a step with children without `promote_children` → reject `silent_child_drop` (same validator rule).
- Reorder that would break `depends_on_step_ids` → emit `dependency_warning` and reject the diff; user must resolve.
- Frontend cannot replace the active plan object directly.

---

## Out of scope

- Frontend visual implementation
- Integration proof (S6-0506)

---

## Allowed files

- `runtime/direct_plan_edit.py` (new)
- `tests/test_direct_plan_edit.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Frontend code in this story
- ✗ Direct active-plan replacement endpoint
- ✗ Bypassing the S6-0503 validator

---

## Tests first

### Unit

- `test_edit_text_translates_to_replace_operation`.
- `test_reorder_translates_to_reorder_operation`.
- `test_delete_with_promote_translates_to_remove_with_children_promoted_to`.
- `test_duplicate_translates_to_add_with_cloned_step_at_position_plus_1`.
- `test_edit_expected_outcome_translates_to_change_expected_outcome_operation`.

### Contract

- `test_each_command_requires_plan_id_and_plan_version`.
- `test_direct_edit_flows_through_s6_0503_validator` (asserts call site).
- `test_validator_failure_propagates_with_typed_error_to_caller`.
- `test_no_direct_active_plan_replacement_endpoint_exists`.

### Integration

- `test_successful_direct_edit_results_in_corrected_plan_ready` (with S6-0504 lifecycle).
- `test_dependency_warning_emitted_when_reorder_breaks_dependent_step`.

### Negative

- `test_delete_step_with_children_without_promote_is_rejected_as_silent_child_drop`.
- `test_reorder_violating_dependency_graph_is_rejected_with_dependency_warning`.
- `test_edit_against_stale_plan_version_is_rejected`.
- `test_duplicate_does_not_collide_step_ids`.
- `test_direct_edit_does_not_execute_or_record`.

### Regression

- S6-0503 validator tests pass.
- S6-0504 lifecycle tests pass.
- Cluster 4 dependency model tests pass.

---

## Implementation notes

1. `runtime/direct_plan_edit.py` exposes one entry point per edit command, each returning the validator result.
2. ID minting for duplicate uses a deterministic scheme `{step_id}-copy-{n}`.
3. Dependency-warning detection reuses the Cluster 4 dependency graph.
4. No code path may construct a new active plan object directly; all changes go through S6-0504's `apply_diff`.

### Key invariants

- Single validator path.
- Single apply path.
- No direct active-plan replacement.

---

## Coverage target

**95%** on `runtime/direct_plan_edit.py`.

---

## Stop conditions

- Frontend command set disputed → freeze on the 5 listed; add later via follow-up.
- Dependency graph source unclear → use Cluster 4 source.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0503 / S6-0504 tests pass
- [ ] Cluster 4 dependency tests pass
- [ ] Cluster 2 enforcement tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] 5 edit commands translate to typed DiffOperations
- [ ] Each command routes through S6-0503 validator
- [ ] Successful edits route through S6-0504 lifecycle
- [ ] Dependency-warning emitted where applicable
- [ ] No direct active-plan replacement endpoint
- [ ] 95% coverage
- [ ] Regression guard green
