# S6-0607 User requested locator update flow

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Update
**Blocks:** S6-0608
**Blocked by:** S6-0606

---

## Purpose

Support `improve_locator(operation_id, user_hint)` so the user can request a better locator for a prior operation. Reuses the deterministic pipeline first, only invokes the specialist if necessary, validates live, and preserves the old locator in `update_history` plus the code/replay archive.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — user-requested update preserves history; deterministic-first
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — "use a more stable locator for step N"
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — update affordance, status surface

---

## Current known context

- S6-0606 stores `LocatorContext`.
- No `improve_locator` entry point exists.

---

## Desired behavior

### Flow

1. Load `LocatorContext` by `operation_id`. If missing → return `LocatorContextMissing`.
2. Regenerate deterministic candidates (S6-0601), incorporating `user_hint` (e.g., "prefer testid", "scope to dialog").
3. Live-validate.
4. If a deterministic candidate yields `matched_count == 1` → use it; **no LLM call**.
5. Else invoke `locator_specialist` (S6-0605) with focused packet + `user_hint`.
6. Validate each specialist suggestion live.
7. If ambiguity persists → present `LocatorAmbiguous` candidate chooser (S6-0604).
8. On user selection or unique deterministic match, activate only on `matched_count == 1`.
9. Append `{prev_locator, reason, replaced_at}` to `update_history`.
10. Update the code/replay archive entry.

### Rules

- Old locator never erased; always retained in `update_history`.
- Code/replay archive update is part of the flow's success path.
- No silent activation; live validation gates each step.

---

## Out of scope

- Wrong-page precondition (S6-0608)
- Replay repair flow (future)

---

## Allowed files

- `runtime/locator_update_flow.py` (new)
- `tests/test_locator_update_flow.py` (new)
- Narrow edits to a replay-archive adapter (not a broad refactor) only if required to write update records

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM dump
- ✗ Unvalidated activation
- ✗ Erasing old locator from history

---

## Tests first

### Unit

- `test_load_context_missing_returns_locator_context_missing`.
- `test_user_hint_prefer_testid_biases_pipeline`.
- `test_user_hint_scope_dialog_biases_scoping`.
- `test_update_history_appended_with_prev_locator_reason_and_timestamp`.

### Contract

- `test_deterministic_unique_match_branch_does_not_invoke_specialist`.
- `test_specialist_branch_invoked_only_when_deterministic_fails`.
- `test_activation_requires_live_matched_count_eq_1`.
- `test_code_replay_archive_updated_on_success`.

### Integration

- `test_deterministic_unique_match_branch_end_to_end`.
- `test_specialist_branch_with_unique_suggestion_end_to_end`.
- `test_specialist_branch_with_ambiguity_routes_to_user_chooser`.

### Negative

- `test_no_activation_when_live_validation_returns_zero_matches`.
- `test_no_activation_when_live_validation_returns_multiple_matches_without_user_pick`.
- `test_old_locator_retained_in_history_even_after_multiple_updates`.
- `test_specialist_branch_obeys_one_retry_then_fail_closed`.
- `test_user_hint_with_action_phrase_does_not_trigger_action_tools` (specialist still tool-restricted).

### Regression

- S6-0601 / S6-0602 / S6-0604 / S6-0605 / S6-0606 tests pass.
- Cluster 2 enforcement tests pass.

---

## Implementation notes

1. `improve_locator` is the single entry point; it composes existing modules.
2. The replay archive write is idempotent per `(operation_id, replaced_at)`.
3. Deterministic regeneration consumes `user_hint` to reweight (e.g., bias testid; restrict scope to "dialog").

### Key invariants

- Deterministic-first branch never calls LLM.
- Old locator preserved.
- Activation gated by live unique match.

---

## Coverage target

**95%** on `runtime/locator_update_flow.py`.

---

## Stop conditions

- `user_hint` grammar undefined → freeze on a small whitelist (`prefer_testid`, `prefer_role_name`, `scope:<container>`, `avoid_xpath`).
- Replay archive write contract unclear → use a thin adapter; do not refactor archive subsystem.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0601 / S6-0602 / S6-0604 / S6-0605 / S6-0606 tests pass
- [ ] Cluster 2 / 3 tests pass

---

## Acceptance criteria / Sign-off

- [ ] `improve_locator` composes the pipeline + specialist correctly
- [ ] Deterministic branch never invokes LLM
- [ ] Live validation gates activation
- [ ] Old locator retained in `update_history`
- [ ] Code/replay archive updated
- [ ] 95% coverage
- [ ] Regression guard green
