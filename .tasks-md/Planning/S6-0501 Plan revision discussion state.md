# S6-0501 Plan revision discussion state

## Metadata

**Sprint:** Sprint 6
**Cluster:** 5 (Plan Discussion + Correction + Direct Plan Editing)
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Plan Discussion
**Blocks:** S6-0502, S6-0503, S6-0504, S6-0506
**Blocked by:** Cluster 4 (S6-0408)

---

## Purpose

Introduce a typed `plan_revision_discussion` state and a `discuss_only` vs `apply_revision` classifier so that exploratory user questions about a draft plan ("what if we remove this?", "can you rethink step 3?") never mutate the active plan and never trigger execution. The active plan object must remain byte-identical across the discussion turn; only a `plan_discussion_response` event is emitted.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — "Plan discussion is read-only; mutation requires explicit apply intent."
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — scenarios: "what if we remove this?", "can you rethink step 3?", "explain why you chose this order".
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — Plan tab discussion thread does not redraw the plan tree.
- PRD plan lifecycle: `draft → plan_ready → (discussion ⇄ correction) → corrected_plan_ready → confirmed → executing`.

---

## Current known context

### What exists in the repo

- Cluster 4 produces a draft plan with `plan_id` and `plan_version` (S6-0402, S6-0404).
- `runtime/llm_runtime_controller.py` dispatches per-purpose calls; no `plan_revision_discussion` purpose exists yet.
- No classifier distinguishes discussion from mutation.

### What gaps exist

- No `plan_revision_discussion` state in the runtime state machine.
- No `discuss_only` vs `apply_revision` classifier.
- No `plan_discussion_response` event type.

### Test status

- None.

---

## Desired behavior

### High-level expectation

- A new runtime state `plan_revision_discussion` is enterable only from `plan_ready` or `corrected_plan_ready`.
- A classifier maps each user utterance to one of: `discuss_only`, `apply_revision`, `clarification_needed`.
- `discuss_only` emits a `plan_discussion_response` event referencing `(plan_id, plan_version)` and leaves the plan unchanged.
- `apply_revision` exits this story's scope and hands off to S6-0502 (mutation boundary).
- No `corrected_plan_ready`, no `plan_diff`, no execution, no recording in discussion state.

### Interface (sketch)

```
classify_plan_utterance(utterance, active_plan) -> DiscussionIntent
DiscussionIntent = discuss_only | apply_revision | clarification_needed
emit_plan_discussion_response(plan_id, plan_version, answer_text)
```

### New files

- `runtime/plan_discussion.py`
- `tests/test_plan_discussion.py`

---

## Out of scope

- Mutation boundary (S6-0502)
- Diff schema (S6-0503)
- Corrected plan lifecycle (S6-0504)
- Direct edits (S6-0505)

---

## Allowed files

- `runtime/plan_discussion.py` (new)
- `tests/test_plan_discussion.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit from this story
- ✗ `.DS_Store` commit
- ✗ Paid LLM call in tests
- ✗ Paid browser E2E
- ✗ Active plan in-place mutation
- ✗ Recording / code_update during discussion

---

## Tests first

### Unit

- `test_classifier_what_if_we_remove_this_is_discuss_only` — asserts intent.
- `test_classifier_can_you_rethink_step_3_is_discuss_only`.
- `test_classifier_explain_why_you_chose_this_order_is_discuss_only`.
- `test_classifier_apply_this_change_is_apply_revision`.
- `test_classifier_ambiguous_utterance_is_clarification_needed`.
- `test_classifier_handles_empty_utterance_as_clarification_needed`.

### Contract

- `test_plan_discussion_response_event_carries_plan_id_and_plan_version`.
- `test_plan_discussion_response_event_has_typed_schema`.
- `test_active_plan_object_is_byte_identical_pre_and_post_discussion_turn`.
- `test_no_corrected_plan_ready_event_emitted_in_discussion_state`.
- `test_no_plan_diff_event_emitted_in_discussion_state`.

### Integration

- `test_enter_discussion_only_from_plan_ready_or_corrected_plan_ready`.
- `test_discussion_state_blocks_execution_event`.

### Negative

- `test_discussion_state_cannot_be_entered_from_executing_state`.
- `test_classifier_does_not_misroute_speculative_phrase_as_apply` (e.g., "maybe remove X" stays `discuss_only`).
- `test_discussion_turn_does_not_emit_recording_or_code_update_events`.

### Regression

- Cluster 4 `plan_ready` event tests still pass.
- S5-013 convergence tests still pass.

---

## Implementation notes

### Approach

1. Add `PlanDiscussionState` enum entry and `classify_plan_utterance()` in `runtime/plan_discussion.py`.
2. Use a deterministic phrase-pattern + verb-intent map first; LLM-assisted classification is out of scope here.
3. Emit `plan_discussion_response` via the existing event bus; reuse `(plan_id, plan_version)` from active plan.
4. Provide a `assert_plan_unchanged(active_plan)` helper used in tests and runtime guard.

### Key invariants

- Active plan reference equality and structural equality preserved across the discussion turn.
- No state transition to `correction` from this module.

---

## Coverage target

**95% line + branch coverage** on `runtime/plan_discussion.py`.

```
python -m pytest tests/test_plan_discussion.py --cov=runtime.plan_discussion --cov-fail-under=95
```

---

## Stop conditions

- Cannot decide intent with confidence → emit `clarification_needed`, do not mutate.
- Active plan not present → reject discussion entry.
- Coverage < 95% → diagnose; do not lower the bar.

---

## Regression guard checklist

- [ ] Cluster 0 governance tests pass
- [ ] Cluster 1 purpose policy tests pass
- [ ] Cluster 2 enforcement tests pass
- [ ] Cluster 4 plan lifecycle tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] `plan_revision_discussion` state added and gated
- [ ] Classifier returns one of 3 typed outcomes
- [ ] `plan_discussion_response` event has typed schema and carries `(plan_id, plan_version)`
- [ ] Active plan is provably unchanged across a discussion turn
- [ ] No mutation / execution / recording side effects
- [ ] 95% coverage
- [ ] Regression guard green
