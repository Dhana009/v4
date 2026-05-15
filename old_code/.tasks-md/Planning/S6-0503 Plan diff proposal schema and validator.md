# S6-0503 Plan diff proposal schema and validator

## Metadata

**Sprint:** Sprint 6
**Cluster:** 5
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Plan Diff Schema
**Blocks:** S6-0504, S6-0505, S6-0506
**Blocked by:** S6-0502

---

## Purpose

Define the typed `plan_diff` schema and its validator. Every plan mutation (LLM-proposed or frontend-direct) flows through this schema. Validator enforces fail-closed semantics: one schema retry, then reject; no silent drop, no silent reorder, no implicit split/merge.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — `plan_diff` schema, retry budget = 1, fail-closed.
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — correction scenarios: remove step, reorder, change expected outcome, split a step into two, merge two steps.
- Cluster 2 (S6-0206) — schema retry + fail-closed policy.

---

## Current known context

- No `plan_diff` schema exists.
- Cluster 2 has a generic schema retry mechanism; this story uses it.
- Diff editor purpose has **no browser tools** (read-only over plan tree).

---

## Desired behavior

### Diff schema

```
PlanDiff = {
  plan_id, base_plan_version, operations: [DiffOperation]
}

DiffOperation = one of:
  ADD                  {parent_step_id?, position, step}
  REMOVE               {step_id, children_promoted_to?}
  REPLACE              {step_id, new_step}
  REORDER              {parent_step_id?, new_order: [step_id]}
  CHANGE_EXPECTED_OUTCOME {step_id, new_expected_outcome}
  SPLIT                {step_id, into: [step, step], children_assignment}
  MERGE                {step_ids: [...], merged_step, children_assignment}
```

### Validator rules

- Schema retry budget = 1; second failure → reject with `plan_diff_schema_failed`.
- REMOVE without `children_promoted_to` when the step has children → reject `silent_child_drop`.
- REORDER that violates dependency graph → reject `dependency_violation`.
- SPLIT / MERGE without explicit operation type → reject (no implicit split/merge inside REPLACE).
- Diff editor purpose receives **no browser/action tools**.
- `base_plan_version` must equal active plan version; else `stale_plan`.

---

## Out of scope

- Applying validated diffs (S6-0504)
- Direct edit translation (S6-0505)
- Integration proof (S6-0506)

---

## Allowed files

- `runtime/plan_diff_schema.py` (new)
- `runtime/plan_diff_validator.py` (new)
- `tests/test_plan_diff_schema.py` (new)
- `tests/test_plan_diff_validator.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM injection into diff prompts
- ✗ Tool exposure beyond plan-read tools for diff editor purpose

---

## Tests first

### Unit

- `test_add_operation_round_trips_through_schema`.
- `test_remove_operation_with_children_promoted_to_validates`.
- `test_replace_operation_validates`.
- `test_reorder_operation_validates_when_dependency_graph_respected`.
- `test_change_expected_outcome_validates`.
- `test_split_operation_requires_children_assignment`.
- `test_merge_operation_requires_children_assignment`.
- `test_schema_rejects_unknown_operation_type`.
- `test_schema_rejects_missing_base_plan_version`.

### Contract

- `test_validator_rejects_remove_without_children_promoted_to_as_silent_child_drop`.
- `test_validator_rejects_reorder_that_violates_dependency_graph`.
- `test_validator_rejects_implicit_split_inside_replace`.
- `test_validator_rejects_implicit_merge_inside_replace`.
- `test_validator_rejects_stale_base_plan_version`.
- `test_validator_emits_typed_error_codes` (silent_child_drop, dependency_violation, stale_plan, plan_diff_schema_failed).

### Integration

- `test_one_schema_retry_then_fail_closed` (first malformed diff → retry; second malformed → reject).
- `test_diff_editor_purpose_has_no_browser_tools_exposed`.

### Negative

- `test_validator_rejects_empty_operations_list`.
- `test_validator_rejects_duplicate_step_ids_in_reorder`.
- `test_validator_rejects_split_with_single_target` (must be ≥2).
- `test_validator_rejects_merge_with_single_source` (must be ≥2).
- `test_validator_rejects_operation_referencing_nonexistent_step_id`.

### Regression

- Cluster 2 schema retry / fail-closed tests pass.
- S6-0502 mutation boundary tests pass.

---

## Implementation notes

1. `runtime/plan_diff_schema.py`: dataclasses or pydantic models for `PlanDiff` and `DiffOperation` variants.
2. `runtime/plan_diff_validator.py`: pure functions; reuse Cluster 2 retry harness.
3. Tool-exposure filter: register diff editor purpose with read-only plan tools only.
4. Dependency-graph check: build adjacency from `depends_on_step_ids` (S6-0406); REORDER must produce a topological sort consistent with the graph.

### Key invariants

- Every emitted diff is typed.
- No silent transformations.
- One retry; then closed.

---

## Coverage target

**95%** on both `plan_diff_schema.py` and `plan_diff_validator.py`.

---

## Stop conditions

- Operation type set disputed → freeze on the 7 listed; add new types in a follow-up story.
- Dependency graph source unclear → consume the same `depends_on_step_ids` as S6-0406.
- Coverage < 95% → diagnose; do not lower.

---

## Regression guard checklist

- [ ] Cluster 2 schema-retry / fail-closed tests pass
- [ ] S6-0501 / S6-0502 tests pass
- [ ] Cluster 4 lifecycle / dependency tests pass

---

## Acceptance criteria / Sign-off

- [ ] `PlanDiff` and 7 `DiffOperation` variants defined
- [ ] Validator rejects each negative case with typed error code
- [ ] One retry, then fail-closed
- [ ] Diff editor purpose has no browser tools
- [ ] 95% coverage on both modules
- [ ] Regression guard green
