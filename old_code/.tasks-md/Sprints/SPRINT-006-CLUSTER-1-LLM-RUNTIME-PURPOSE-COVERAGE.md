# Sprint 6 Cluster 1 — LLM Runtime Purpose Coverage

**Sprint:** Sprint 6  
**Cluster:** 1  
**Status:** Planning  
**Type:** Control Plane Foundation  
**Owner:** Runtime Policy  

---

## Cluster Goal

Make the LLM Runtime Controller the single source of policy for every Complete LLM Mode LLM purpose. Every LLM call must be purpose-specific, route through the controller, and have complete metadata: model class, context policy, skill policy, tool policy, output schema, validator, fallback, retry policy, and telemetry fields.

---

## Why Cluster 1 First

Runtime Policy Spec requires:
- Every LLM call must go through the LLMRuntimeController
- Every call must declare a purpose_id
- Unknown purpose must fail closed (no fallback LLM call)
- Every purpose must have complete policy metadata

Cluster 1 establishes this foundation. Cluster 2 will enforce the policies at runtime. Without Cluster 1, Cluster 2 has nothing to enforce.

---

## Source Documents

### Required

- `autoworkbench_complete_llm_mode_runtime_policy_spec*.md` (source of truth for purposes, policies, constraints)
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec*.md` (user scenarios requiring LLM)
- PRD v2.3 modular docs:
  - `02_LLM_RUNTIME.md` (LLM layer architecture)
  - `07_MULTI_MODEL_ORCHESTRATION.md` (model routing)

### Governance

- `.tasks-md/Sprints/SPRINT-006-CLUSTER-0-GOVERNANCE.md` (overall framework)
- `.tasks-md/Planning/S6-0001*` (requirement-to-test matrix)
- `.tasks-md/Planning/S6-0002*` (test taxonomy)
- `.tasks-md/Planning/S6-0004*` (modularization rules)
- `.tasks-md/Planning/S6-0005*` (story template)
- `.tasks-md/Testing/S6-0003*` (coverage gates)
- `.tasks-md/Testing/S6-0006*` (regression guard)

---

## Architecture Invariants

1. **Backend owns runtime truth**: LLM proposes only. Backend validates, finalizes, records.
2. **Purpose-specific policies**: Every LLM call declares purpose_id. Unknown purpose fails immediately.
3. **Policy is metadata**: All 14 purposes have complete metadata in one typed registry. Runtime queries registry.
4. **Modular policy logic**: Policy code goes in focused runtime/ modules, not agent.py.
5. **Tests enforce policy**: No policy implemented without tests that verify enforcement.
6. **No silent failures**: Schema invalid? Retry once, then fail closed. Budget exceeded? Compact or ask user. Unknown purpose? Fail with clear error.
7. **Tooling is constrained by purpose**: Only tools in purpose.tool_policy are exposed to LLM.
8. **Context is constrained by purpose**: Only context level in purpose.context_policy is used.

---

## Cluster 1 Stories

### Story List

| Story ID | Title | Type | Objective |
|----------|-------|------|-----------|
| S6-0101 | Purpose registry completeness audit | Discovery | Audit: which purposes exist, which are missing, which have policy, which need migration |
| S6-0102 | Typed purpose policy registry | Core | Create single typed registry with all 14 purposes and complete metadata |
| S6-0103 | Low-risk purpose policies | Core | Complete policies for 4 no-tool purposes: intent_classifier, clarification_generator, user_response_writer, trace_summarizer |
| S6-0104 | Planning and recommendation purpose policies | Core | Complete policies for 3 planning purposes: page_validation_recommender, journey_planner, step_plan_normalizer |
| S6-0105 | Plan edit and custom assertion purpose policies | Core | Complete policies for 2 modifying purposes: plan_diff_editor, custom_assertion_planner |
| S6-0106 | Locator, execution, recovery, replay purpose policies | Core | Complete policies for 4 operational purposes: locator_specialist, execution_driver, recovery_diagnoser, replay_repair_specialist |
| S6-0107 | Controller call-site inventory and migration guard | Discovery | Audit: where LLM is called, which sites bypass controller, which need migration |

### Required 14 LLM Purposes

Cluster 1 must ensure all 14 are declared in policy registry:

```
intent_classifier
clarification_generator
page_intelligence_summarizer
page_validation_recommender
journey_planner
step_plan_normalizer
plan_diff_editor
locator_specialist
custom_assertion_planner
execution_driver
recovery_diagnoser
replay_repair_specialist
user_response_writer
trace_summarizer
```

Each must have:

```
purpose_id: str
model_class: str (cheap/main/debug)
context_policy: str (L0-L5 default)
skill_policy: List[str]
tool_policy: List[str]
schema_id: str
validator_id: str
fallback_policy: str (ask_user/fail_closed/retry)
retry_policy: str
telemetry_fields: List[str]
```

---

## Allowed Files (for future implementation)

- `runtime/llm_purpose_policy.py` (new, TypedDict/dataclass for purpose metadata)
- `runtime/llm_purpose_registry.py` (new, single registry with all 14 purposes)
- `runtime/llm_controller_callsite_inventory.py` (new, if documenting call sites)
- `tests/test_llm_purpose_policy_registry.py` (new, registry tests)
- `tests/test_*_purpose_policies.py` (new, policy tests per story)

Minimal changes to:
- `runtime/llm_runtime_controller.py` (call registry.get() only, thin)

---

## Forbidden Files and Actions

- ✗ `agent.py` (no broad changes; thin orchestration only if absolutely needed)
- ✗ `server.py` (no changes)
- ✗ `runtime/` (no changes to existing files except llm_runtime_controller.py minimal)
- ✗ `frontend/` (no changes)
- ✗ `tests/` (no changes to existing tests except minimal controller fix if needed)
- ✗ `browser.py` (no changes)
- ✗ Paid LLM tests (Cluster 1/2 are control plane only, no paid calls)
- ✗ Browser E2E tests (Cluster 1/2 are control plane only, no browser)
- ✗ Page Intelligence live invocation (that's Cluster 3)
- ✗ Journey planner implementation (that's Cluster 4)
- ✗ Replay repair implementation (that's Cluster 8)

---

## Tests-First Policy

Every Cluster 1 story must:

1. **Design tests BEFORE implementation** (tests pass == story done)
2. **Unit tests**: Test policy metadata, validators, registry lookup
3. **Contract tests**: Test purpose → policy resolution, registry integration
4. **No implementation without tests**
5. **No shortcuts**: If coverage <95%, investigate. Don't lower requirement.
6. **No paid LLM**: Use fake/mock. Real LLM testing deferred to Cluster 3+ acceptance tests.

---

## 95% Coverage Rule

Every new module must reach 95% coverage minimum:

```bash
python -m pytest tests/ --cov=runtime.llm_purpose_policy --cov=runtime.llm_purpose_registry --cov-fail-under=95 -q
```

If below 95%:
- Investigate root cause (missing tests, untestable code)
- Do not lower requirement
- Add tests or refactor
- Stop if cannot reach 95%

---

## Required Regression Guard

After Cluster 1 complete, run:

```bash
REGRESSION_GUARD_SUITE=(
  "tests/test_backend_event_sequences.py"
  "tests/test_event_contract.py"
  "tests/test_recording_codegen_truth_contract.py"
  "tests/test_llm_runtime_controller_contract.py"
  "tests/test_prompt_pack_builder.py"
  "tests/test_prompt_pack_safety_rules.py"
  "tests/test_skill_escalation_contract.py"
  "tests/test_tool_schema_filter.py"
  "tests/test_planning_convergence_contract.py"
  "tests/test_page_intelligence_schema.py"
  "tests/test_page_intelligence_fake_integration.py"
  "tests/test_replay_one.py"
  "tests/test_deterministic_fast_path.py"
  "tests/test_dom_locator_contracts.py"
  "tests/test_frontend_plan_recovery_rendering.py"
  "tests/test_frontend_recorded_code_rendering.py"
)

python -m pytest "${REGRESSION_GUARD_SUITE[@]}" -q
```

Expected: 365+ tests passing in <2.5 minutes. All must pass before moving to Cluster 2.

---

## Definition of Done

Cluster 1 is complete and ready for Cluster 2 only when:

- [ ] All 7 stories marked Done
- [ ] All 14 LLM purposes in registry
- [ ] Unknown purpose fails closed (test verifies)
- [ ] Every purpose has complete metadata (model, context, skills, tools, schema, validator, fallback)
- [ ] No browser-changing tools exposed to planning/recommendation purposes
- [ ] No LLM purpose can claim to mutate runtime truth
- [ ] Controller call-site inventory complete (audit finished)
- [ ] 95% coverage for all new/modified modules
- [ ] Regression guard passes (all 365+ tests)
- [ ] No paid LLM/E2E run
- [ ] All story commits approved in code review
- [ ] No product behavior changes (implementation will come in Cluster 2)

---

## Stop Conditions

Stop and ask for clarification if:

- A purpose's metadata is ambiguous (cannot determine model class, context level, etc.)
- Cannot design tests for a purpose (likely indicates scope unclear)
- Coverage requirement cannot be met (investigate why, don't lower requirement)
- Regression guard fails (stop, fix root cause before proceeding)
- New purpose discovered not in the 14 (add to list or defer to Cluster 3+)
- Call site inventory reveals deep architectural issue (stop, report)
- Registry conflicts with existing code (clarify authority/precedence)

---

## Execution Notes

### One Story at a Time

Give Claude Code one story at a time:

```
Story: S6-0101 Purpose registry completeness audit
File: .tasks-md/Planning/S6-0101-Purpose-registry-completeness-audit.md
Expected: Read-only audit output (discovery)
Hand off when: S6-0101 report created
```

Do NOT give all 7 stories at once. Reason: earlier stories inform later ones.

### Commit After Each Story

After each story (test design + implementation + verification):

```bash
git commit -m "feat: s6-0101 purpose registry audit

Audit report: [count] purposes found, [count] ready, [count] missing.
Call sites: [count] controller-owned, [count] pending migration.
Next: S6-0102 typed registry."
```

### Review Between Stories

After each story done:
1. Review story output (test count, coverage, audit findings)
2. If regressions, fix before next story
3. If coverage below 95%, stop
4. If tests pass + coverage ≥95% + regression guard passes → approve → next story

---

## Multi-Story Dependencies

```
S6-0101 (audit) 
  → S6-0102 (registry)
    → S6-0103 (low-risk)
      → S6-0104 (planning)
        → S6-0105 (edit/assert)
          → S6-0106 (operational)
            → S6-0107 (call-site inventory)
```

S6-0101 output feeds into S6-0102. S6-0102 defines shape for S6-0103+. S6-0107 inventory informs Cluster 2 migrations.

---

## What Cluster 1 Does NOT Include

- ✗ Context level enforcement (that's Cluster 2)
- ✗ Tool exposure at runtime (that's Cluster 2)
- ✗ Schema validation enforcement (that's Cluster 2)
- ✗ Token budget enforcement (that's Cluster 2)
- ✗ Page Intelligence live invocation (that's Cluster 3)
- ✗ Journey planner implementation (that's Cluster 4)
- ✗ Any LLM call behavior changes (just declare policies)

Cluster 1 is metadata + registry only. Enforcement comes in Cluster 2.

---

## Next: Cluster 2

After Cluster 1 approval, Cluster 2 takes the purpose policies and implements:

```
Cluster 2 = Converting Cluster 1 policies into runtime enforcement

S6-0201: Context levels L0-L5 enforced
S6-0202: Sufficiency gates (user goal clear? page state known?)
S6-0203: Escalation requests (backend approval)
S6-0204: Memory selection (no full history by default)
S6-0205: Tool exposure (only tools in purpose.tool_policy)
S6-0206: Schema validation + retry/fail-closed
S6-0207: Token budgets + telemetry
S6-0208: Integration regression (everything together)
```

---

## Open Questions

- Are all 14 purposes in the list above correct? (Verify against Runtime Policy Spec)
- Are there additional purposes not yet documented? (S6-0101 will discover)
- Should model_class be enum (cheap/main/debug) or literal model name? (Define in S6-0102)
- Should fallback_policy be enum (ask_user/fail_closed/retry) or more granular? (Define in S6-0102)

---

## Validation Checklist

Before approving Cluster 1, verify:

- [ ] All 7 story files exist and are readable
- [ ] Each story follows S6-0005 template
- [ ] Each story has explicit tests-first section
- [ ] Each story forbids paid LLM/E2E
- [ ] Each story forbids broad agent.py changes
- [ ] Regression guard command is documented
- [ ] Definition of Done is specific (not vague)
- [ ] Stop conditions are clear
- [ ] No product code changes in planning files

---

## Notes

- Cluster 1 is control plane establishment. No behavior changes yet.
- Cluster 1 is read-heavy (discovery + audit + policy definition).
- Cluster 1 is low-risk (new modules, no behavioral changes).
- Cluster 1 unblocks Cluster 2, which unblocks Cluster 3+.
