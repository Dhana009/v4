# Sprint 6 Cluster 5 — Plan Discussion, Correction, Direct Editing

**Sprint:** Sprint 6
**Cluster:** 5 (Plan Discussion + Correction + Direct Plan Editing)
**Depends on:** Cluster 1 (Purpose Coverage), Cluster 2 (Policy Enforcement), Cluster 4 (Journey Planner + Steps)
**Release gate:** All stories Done + 95% module coverage + regression pass (Clusters 0–4)

---

## Cluster goal

Implement the **plan revision discussion layer**, the **explicit apply/update mutation boundary**, and the **structured plan_diff path** that lets the user revise, correct, or directly edit a draft plan **without** silently mutating the active plan or executing on a stale version.

This cluster makes plan discussion safe (read-only), plan correction explicit (typed `plan_diff`), and direct frontend edits subject to the same validator. Old plan versions become non-executable the moment a corrected `plan_ready` is generated; execution remains gated on fresh user confirmation.

---

## Source docs

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — plan revision / correction policies, explicit-apply boundary, plan_diff schema, fail-closed retry
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — scenarios: "what if we remove this?", "rethink step 3", direct frontend edit, apply-revision
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — Plan tab direct edit commands, dependency warnings, corrected plan UI states
- PRD modular docs: plan lifecycle, mutation boundary, confirmation gating

---

## Architecture invariants

1. **Discussion ≠ mutation.** While in `plan_revision_discussion`, the active plan object is byte-identical pre/post.
2. **Explicit apply boundary.** Only classifier outcomes `apply_revision`, `update`, `make_this_change`, `confirm_this_version` cross from discuss → mutate.
3. **Structured diff only.** Every mutation is a typed `plan_diff` proposal — no in-place edit of the active plan tree.
4. **Backend validates every diff.** Schema retry budget = 1, then fail-closed.
5. **No silent drop / reorder / split / merge.** REMOVE without `children_promoted_to`, REORDER violating dependency graph, SPLIT/MERGE without explicit operation type → reject.
6. **Corrected plan_ready requires fresh user confirmation** before execution.
7. **Old plan versions cannot execute** once a corrected version is emitted.
8. **Direct frontend edits flow through the same validator** as LLM-proposed diffs.
9. **No recording, no code_update, no execution during discussion or correction.**
10. **Stale-plan rejection.** Mutation requests must carry `(plan_id, plan_version)`; mismatch → reject.

---

## Stories

| ID | Title | Tier | Depends on | Blocks |
|----|-------|------|------------|--------|
| S6-0501 | Plan revision discussion state | 1 | Cluster 4 | S6-0502 |
| S6-0502 | Explicit apply/update mutation boundary | 1 | S6-0501 | S6-0503 |
| S6-0503 | Plan diff proposal schema and validator | 1 | S6-0502 | S6-0504, S6-0505 |
| S6-0504 | Corrected plan_ready lifecycle | 1 | S6-0503 | S6-0506 |
| S6-0505 | Direct plan editing backend contract | 1 | S6-0503 | S6-0506 |
| S6-0506 | Cluster 5 cheap integration proof | 2 | S6-0504, S6-0505 | (release gate) |

---

## Dependency / sequence notes

- S6-0501 establishes the discussion state machine; nothing else can rely on a discuss→mutate transition before it.
- S6-0502 layers the apply/update classifier on top of 0501; it consumes 0501's state.
- S6-0503 defines the `plan_diff` schema + validator — required by both 0504 (LLM-proposed correction) and 0505 (direct edit).
- S6-0504 is the lifecycle: `plan_diff_validated → plan_diff_applied → corrected_plan_ready` (with fresh confirmation gate).
- S6-0505 wires frontend direct-edit commands through the same validator.
- S6-0506 is the integration proof using `FakeLLMDiffGenerator` (no paid LLM, no paid E2E).

---

## Allowed future implementation files

```
runtime/plan_discussion.py          # discuss_only vs apply classifier, discussion state
runtime/plan_mutation_boundary.py   # explicit-apply detection, stale-plan rejection
runtime/plan_diff_schema.py         # PlanDiff, DiffOperation, validators
runtime/plan_diff_validator.py      # no-silent-drop / no-silent-reorder rules, retry budget
runtime/plan_correction_lifecycle.py# version increment, corrected_plan_ready, confirmation gate
runtime/direct_plan_edit.py         # frontend edit → plan_diff translator
tests/test_plan_discussion.py
tests/test_plan_mutation_boundary.py
tests/test_plan_diff_schema.py
tests/test_plan_diff_validator.py
tests/test_plan_correction_lifecycle.py
tests/test_direct_plan_edit.py
tests/test_cluster5_integration.py
```

---

## Forbidden files / actions

- Broad `agent.py` refactor (only narrow dispatch hooks allowed in 0504/0505)
- Broad `server.py` refactor
- Committing `AGENTS.md` changes from this cluster
- Committing `.DS_Store`
- Paid LLM calls in tests
- Paid browser E2E
- Raw full-DOM injection into discussion/correction prompts
- Unvalidated locator/plan activation
- Recording or code_update during discussion or correction
- In-place mutation of the active plan tree

---

## Tests-first policy

Every story lists Unit / Contract / Integration / Regression / Negative test cases **before** any implementation checkbox. The integration story (S6-0506) is the only place a multi-module flow is asserted, and it uses fakes only.

---

## Coverage requirement

**95% line + branch coverage** on every new/changed module:

```
runtime/plan_discussion.py
runtime/plan_mutation_boundary.py
runtime/plan_diff_schema.py
runtime/plan_diff_validator.py
runtime/plan_correction_lifecycle.py
runtime/direct_plan_edit.py
```

---

## Regression guard

Each story must keep these green:

- Cluster 0 governance tests
- Cluster 1 purpose policy tests
- Cluster 2 enforcement tests (schema retry, fail-closed, tool exposure, token budget)
- Cluster 3 page intelligence + recommendation tests
- Cluster 4 journey planner / steps / precondition tests
- S5-013 convergence narrowing tests

---

## Definition of Done

- [ ] Discussion state never mutates the active plan
- [ ] Only explicit apply/update language crosses the mutation boundary
- [ ] Every mutation is a typed `plan_diff` proposal
- [ ] Validator rejects silent drop / reorder / split / merge
- [ ] Corrected `plan_ready` requires fresh user confirmation
- [ ] Old plan versions are non-executable after correction
- [ ] Frontend direct edits use the same validator path
- [ ] Stale `(plan_id, plan_version)` mutation requests are rejected
- [ ] FakeLLMDiffGenerator integration proof passes
- [ ] 95% coverage on each new module
- [ ] Regression guard passes (Clusters 0–4)

---

## Stop conditions

- Cannot decide whether a phrase is `discuss_only` vs `apply_revision` → emit `clarification_needed`, do not mutate
- `plan_diff` schema retry exhausted → fail closed, surface validator error
- Active plan has been concurrently advanced past the mutation request's `plan_version` → reject with `stale_plan`
- Direct edit lacks `plan_id`/`plan_version` → reject
- Any test in the regression guard regresses → stop and triage

---

## Evidence requirements

- [ ] All 6 stories filed under `.tasks-md/Planning/` with `S6-050N` filenames
- [ ] Each story passes the template checklist (Source rules, Tests first, Forbidden, Coverage, Stop conditions, Sign-off)
- [ ] Cluster integration proof story (S6-0506) lists fake-only flows
- [ ] Update to `.tasks-md/Testing/S6-REGRESSION-GUARD.md` planned (not executed) listing new test files
