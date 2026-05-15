# S6-0506 Cluster 5 cheap integration proof

## Metadata

**Sprint:** Sprint 6
**Cluster:** 5
**Tier:** 2 (supporting)
**Type:** Integration test
**Status:** Pending implementation
**Owner:** Cluster 5 Integration
**Blocks:** (Cluster 5 release gate)
**Blocked by:** S6-0504, S6-0505

---

## Purpose

Prove the full Cluster 5 path end-to-end using a `FakeLLMDiffGenerator` and the in-memory plan store. No paid LLM, no paid browser E2E. Assert that discussion never mutates, explicit apply mutates only through the validator, corrected plans require fresh confirmation, old versions cannot execute, and direct edits flow through the same path.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — full discussion/correction policy
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — P0 scenarios for discussion, correction, direct edit
- Cluster 0 (S6-0007) — paid LLM / paid E2E acceptance policy

---

## Current known context

- S6-0501–0505 deliver the modules; this story integrates them with fakes.
- A `FakeLLMDiffGenerator` is the only LLM-shaped surface; it emits canned validated/invalid diffs.

---

## Desired behavior

### Flows asserted (all with fakes)

1. **Discussion does not mutate.** "what if we remove step 3?" → `plan_discussion_response`; plan unchanged.
2. **Explicit apply produces diff + corrected_plan_ready.** "remove step 3 and apply" → mutation request → validated diff → corrected plan ready (unconfirmed).
3. **Invalid diff fails closed.** FakeLLMDiffGenerator emits malformed diff twice → `plan_diff_schema_failed`; no version increment.
4. **Corrected plan executes only after fresh confirmation.** Without `plan_confirmed` for the new version → execution rejected.
5. **Old plan version rejected post-correction.** Execution against version N after correction → `stale_plan_execution_rejected`.
6. **Direct edit routes through the same validator.** Frontend `edit_text` command → REPLACE diff → validator → corrected_plan_ready.
7. **Direct delete with children without promote is rejected.** Same `silent_child_drop` error code as LLM path.

---

## Out of scope

- Paid LLM
- Paid browser E2E
- Frontend visual implementation
- Cluster 6 locator updates

---

## Allowed files

- `tests/test_cluster5_integration.py` (new)
- `tests/fakes/fake_llm_diff_generator.py` (new, under tests tree)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Real network calls
- ✗ Modifying any module under `runtime/` from this story

---

## Tests first

### Integration

- `test_discussion_only_does_not_mutate_active_plan_or_emit_corrected_plan_ready`.
- `test_explicit_apply_produces_validated_diff_and_corrected_plan_ready_unconfirmed`.
- `test_two_malformed_diffs_in_a_row_fail_closed_and_do_not_increment_version`.
- `test_corrected_plan_cannot_execute_without_fresh_plan_confirmed`.
- `test_old_plan_version_execution_attempt_emits_stale_plan_execution_rejected`.
- `test_direct_edit_text_routes_through_validator_to_corrected_plan_ready`.
- `test_direct_delete_without_promote_emits_silent_child_drop_error`.

### Regression guard (must remain green)

- Cluster 0 governance
- Cluster 1 purpose policy
- Cluster 2 enforcement (schema retry, fail-closed, tool exposure, token budget)
- Cluster 3 page intelligence + recommendation
- Cluster 4 journey planner / steps / precondition
- S5-013 convergence narrowing

### Negative

- `test_no_recording_event_in_any_flow`.
- `test_no_code_update_event_in_any_flow`.
- `test_no_browser_tool_call_from_diff_editor_purpose`.

---

## Implementation notes

1. `FakeLLMDiffGenerator` returns scripted `PlanDiff` payloads per scenario, including malformed cases.
2. Use in-memory plan store; assert reference identity for "unchanged" cases.
3. Reuse Cluster 2 fail-closed harness to count retries.
4. Each flow is one test function; no shared mutable state across tests.

### Key invariants

- All assertions deterministic.
- No real LLM, no real browser.
- Each flow ends in a typed event observable to the assertions.

---

## Coverage target

This story does not add product modules. It guards the cluster integration. Coverage on Cluster 5 modules (set by S6-0501–0505) must remain ≥ 95% with these tests included.

---

## Stop conditions

- Any flow requires a real LLM → stop and revise; the cluster contract must be fakeable.
- Any regression in Clusters 0–4 → stop, triage, do not paper over.

---

## Regression guard checklist

- [ ] Cluster 0 tests pass
- [ ] Cluster 1 tests pass
- [ ] Cluster 2 tests pass
- [ ] Cluster 3 tests pass
- [ ] Cluster 4 tests pass
- [ ] S5-013 convergence tests pass

---

## Acceptance criteria / Sign-off

- [ ] 7 integration flows asserted with fakes
- [ ] 3 negative flows asserted (no recording / no code_update / no browser tool from diff editor)
- [ ] Zero paid LLM / paid E2E
- [ ] Regression guard green
- [ ] Cluster 5 module coverage remains ≥ 95%
