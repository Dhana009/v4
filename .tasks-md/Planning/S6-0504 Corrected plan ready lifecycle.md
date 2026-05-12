# S6-0504 Corrected plan_ready lifecycle

## Metadata

**Sprint:** Sprint 6
**Cluster:** 5
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Plan Correction Lifecycle
**Blocks:** S6-0506
**Blocked by:** S6-0503

---

## Purpose

Define the deterministic lifecycle from a validated `plan_diff` to a `corrected_plan_ready` event with fresh user confirmation gating. The old plan version becomes non-executable the moment a corrected version is emitted.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — "Corrected plans require fresh user confirmation; old plan versions cannot execute."
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — scenarios: "apply this revision then run", "I changed my mind on the corrected plan".
- PRD plan lifecycle.

---

## Current known context

- S6-0503 provides a validated `PlanDiff`.
- Cluster 4 produces `plan_ready` events at version N.
- No atomic version increment or non-executable marker exists.

---

## Desired behavior

### Event sequence

```
plan_diff_validated         (from S6-0503)
plan_diff_applied           (atomic: active_plan = apply(old_plan, diff); version = N+1)
corrected_plan_ready        (carries new plan, new plan_version, awaiting fresh confirmation)
[user confirms]             -> plan_confirmed
[user does not confirm]     -> stays in awaiting state; cannot execute
```

### Rules

- `apply_diff` is atomic; partial-apply is not allowed.
- After `plan_diff_applied`, version becomes `N+1`; old version `N` is marked `non_executable`.
- `corrected_plan_ready` requires a fresh `plan_confirmed` to enter `executing`.
- Any execution attempt against version `N` after correction → `stale_plan_execution_rejected`.

---

## Out of scope

- Direct frontend edits (S6-0505)
- Integration proof (S6-0506)

---

## Allowed files

- `runtime/plan_correction_lifecycle.py` (new)
- `tests/test_plan_correction_lifecycle.py` (new)
- Narrow edits to existing event bus only if needed to register new event types

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Reusing old `plan_confirmed` for the corrected plan
- ✗ Auto-execution of corrected plan

---

## Tests first

### Unit

- `test_apply_diff_is_atomic_no_partial_state_on_failure`.
- `test_version_increments_to_n_plus_1_after_apply`.
- `test_old_plan_version_is_marked_non_executable_after_apply`.
- `test_corrected_plan_ready_event_carries_new_plan_and_version`.

### Contract

- `test_event_order_plan_diff_validated_then_applied_then_corrected_plan_ready`.
- `test_corrected_plan_ready_does_not_imply_confirmation`.
- `test_fresh_plan_confirmed_required_to_enter_executing`.

### Integration

- `test_cannot_execute_corrected_plan_without_fresh_confirmation`.
- `test_cannot_execute_old_plan_version_after_correction` (emits `stale_plan_execution_rejected`).
- `test_two_consecutive_corrections_chain_versions_correctly` (N → N+1 → N+2).

### Negative

- `test_apply_diff_with_validator_failure_does_not_increment_version`.
- `test_execution_attempt_against_version_n_after_correction_is_rejected_with_typed_error`.
- `test_user_rejection_of_corrected_plan_keeps_state_blocked_not_reverted`.

### Regression

- S6-0503 validator tests pass.
- Cluster 4 `plan_ready` lifecycle tests pass.
- Cluster 2 enforcement tests pass.

---

## Implementation notes

1. `apply_diff(old_plan, diff) -> new_plan` is a pure function; lifecycle wrapper handles atomic store update.
2. Old plan version retained in history but flagged `non_executable=True`.
3. `corrected_plan_ready` carries `{plan_id, plan_version, prior_version, diff_summary}`.
4. Executor entry point checks `plan.non_executable` and `plan.confirmed_version == requested_version`.

### Key invariants

- Atomic version transition.
- Confirmation is per-version; never reused across versions.
- Old versions never executable.

---

## Coverage target

**95%** on `runtime/plan_correction_lifecycle.py`.

---

## Stop conditions

- Atomic apply requires a transaction layer not yet available → simulate with copy-on-write store; document.
- Event order disputed → freeze on the order above; deviations are bugs.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0501 / S6-0502 / S6-0503 tests pass
- [ ] Cluster 4 lifecycle tests pass
- [ ] Cluster 2 fail-closed tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] Atomic apply with version increment
- [ ] Old version flagged non-executable
- [ ] `corrected_plan_ready` requires fresh confirmation
- [ ] Stale execution rejected with typed error
- [ ] 95% coverage
- [ ] Regression guard green
