# S6-0608 Wrong page locator update precondition flow

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Wrong-Page Flow
**Blocks:** (Cluster 6 release gate)
**Blocked by:** S6-0607

---

## Purpose

Handle the case where a user requests a locator update while the browser is on the wrong page. Compare `required_page_state` (from operation context) against `current_page_state`; on mismatch emit `precondition_failed_for_locator_update` with typed options. Strict mode requires explicit user choice; relaxed mode auto-selects a safe option. No silent navigation. No live validation on wrong page. Snapshot-only path is never marked final.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — wrong-page precondition handling, strict vs relaxed modes, no silent navigation
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — "update locator but I'm on a different page now"
- Cluster 4 (S6-0407) page-state mismatch flow (reused contract)

---

## Current known context

- S6-0607 implements the update flow assuming the right page.
- S6-0606 stores `required_page_state` via `LocatorContext` + Cluster 4 page-state model.
- No locator-update-specific precondition flow exists.

---

## Desired behavior

### Precheck

```
if current_page_state != required_page_state:
    emit precondition_failed_for_locator_update {
      operation_id,
      required_page_state, current_page_state,
      options: [
        navigate_to_required,
        replay_dependency_steps,
        user_manual_then_recheck,
        use_stored_snapshot (marked non-final, pending_live_validation),
        cancel
      ],
      mode: "strict" | "relaxed"
    }
```

### Mode behavior

- **Strict (default)**: wait for explicit user choice; no auto action.
- **Relaxed**: auto-select the safest option in order: `replay_dependency_steps` → `navigate_to_required` → `user_manual_then_recheck`. Never auto-select `use_stored_snapshot` as a final activation path.

### Rules

- No silent navigation, even in relaxed mode (any navigation emits an event).
- Live validation never runs on the wrong page.
- `use_stored_snapshot` path produces a non-final result tagged `pending_live_validation`; activation deferred until live validation passes.
- After resolution → re-enter S6-0607 update flow.

---

## Out of scope

- Replay-repair product flow (future)
- New page-state inference logic (reuse Cluster 4)

---

## Allowed files

- `runtime/locator_wrong_page_flow.py` (new)
- `tests/test_locator_wrong_page_flow.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Silent navigation
- ✗ Live validation while on wrong page
- ✗ Marking snapshot-only path as final
- ✗ Auto-selecting `use_stored_snapshot` for activation

---

## Tests first

### Unit

- `test_precheck_returns_satisfied_when_states_match`.
- `test_precheck_returns_failed_with_typed_options_when_states_differ`.
- `test_strict_mode_does_not_auto_select_any_option`.
- `test_relaxed_mode_auto_selects_replay_dependency_steps_when_available`.
- `test_relaxed_mode_falls_back_to_navigate_to_required_when_no_dependencies`.
- `test_relaxed_mode_falls_back_to_user_manual_when_navigation_unavailable`.
- `test_relaxed_mode_never_auto_selects_use_stored_snapshot`.

### Contract

- `test_precondition_failed_for_locator_update_event_schema_typed`.
- `test_event_includes_required_and_current_page_state`.
- `test_event_includes_full_options_list`.
- `test_event_includes_mode_field`.

### Integration

- `test_strict_mode_blocks_until_user_choice_then_re_enters_s6_0607_flow`.
- `test_navigate_option_emits_navigation_event_before_re_entering_update`.
- `test_replay_dependency_steps_option_routes_to_cluster_4_precondition_flow`.
- `test_use_stored_snapshot_option_returns_non_final_result_pending_live_validation`.

### Negative

- `test_no_silent_navigation_event_in_strict_mode`.
- `test_no_silent_navigation_event_in_relaxed_mode_navigation_path` (event is emitted, not silent).
- `test_no_live_validation_call_while_on_wrong_page`.
- `test_snapshot_only_result_is_never_marked_final`.
- `test_cancel_option_aborts_update_without_side_effects`.

### Regression

- S6-0607 update flow tests pass.
- S6-0606 context tests pass.
- Cluster 4 S6-0407 precondition tests pass.
- S5-013 convergence tests pass.

---

## Implementation notes

1. Precheck reuses Cluster 4 page-state model; no new inference.
2. Event payload is typed; no DOM blobs.
3. Mode is a parameter to the flow; default `strict`.
4. Snapshot-only path returns `LocatorUpdateResult(status="pending_live_validation", final=False)`.
5. Re-entry into S6-0607 is explicit; never implicit from this flow.

### Key invariants

- No silent navigation.
- No live validation on wrong page.
- Snapshot-only never final.
- Strict mode requires user choice.

---

## Coverage target

**95%** on `runtime/locator_wrong_page_flow.py`.

---

## Stop conditions

- Page-state comparison logic disputed → defer to Cluster 4 implementation.
- Relaxed-mode auto-selection rules disputed → freeze on the ordering above.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0606 / S6-0607 tests pass
- [ ] Cluster 4 S6-0407 tests pass
- [ ] Cluster 2 / 3 tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] Precondition check vs Cluster 4 page-state model
- [ ] Typed `precondition_failed_for_locator_update` event with 5 options
- [ ] Strict mode blocks; relaxed auto-selects in defined order
- [ ] No silent navigation; no live validation on wrong page
- [ ] Snapshot-only path never marked final
- [ ] 95% coverage
- [ ] Regression guard green
