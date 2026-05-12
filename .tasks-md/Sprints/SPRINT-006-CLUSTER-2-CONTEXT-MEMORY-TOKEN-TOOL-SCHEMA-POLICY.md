# Sprint 6 Cluster 2 — Context, Memory, Token, Tool, Schema Policy Enforcement

**Sprint:** Sprint 6  
**Cluster:** 2  
**Status:** Planning  
**Type:** Control Plane Enforcement  
**Owner:** Runtime Policy  

---

## Cluster Goal

Implement runtime enforcement of all LLM Runtime Controller policies. Convert Cluster 1 purpose metadata into enforced constraints:

- Context levels (L0–L5) applied per purpose
- Sufficiency gates checked before every LLM call
- Context escalation requests backend-approved
- Memory selection prevents full-history prompting
- Tool exposure strictly matched to purpose policy
- Schema validation enforced with retry/fail-closed behavior
- Token budgets enforced with compaction/clarification
- All calls observable via telemetry

Result: Backend controls all LLM I/O. Frontend/DOM/LLM cannot violate policy.

---

## Why Cluster 2 After Cluster 1

Cluster 1 defines what policies exist. Cluster 2 enforces them at runtime. Cannot enforce without definitions.

---

## Source Documents

### Required

- `autoworkbench_complete_llm_mode_runtime_policy_spec*.md` (source of truth for context levels, policies, constraints)
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec*.md` (scenarios requiring policy enforcement)
- PRD v2.3 modular docs:
  - `02_LLM_RUNTIME.md` (LLM layer architecture)
  - `04_BACKEND_EVENT_CONTRACT.md` (backend truth owner)

### Governance

- `.tasks-md/Sprints/SPRINT-006-CLUSTER-0-GOVERNANCE.md`
- `.tasks-md/Sprints/SPRINT-006-CLUSTER-1-LLM-RUNTIME-PURPOSE-COVERAGE.md` (Cluster 1 must be complete)
- `.tasks-md/Planning/S6-0001*` through `S6-0008*`
- `.tasks-md/Testing/S6-0003*` and `S6-0006*`

---

## Architecture Invariants

1. **Backend owns runtime truth**: All context-building, policy checks, validators, fallbacks run on backend only.
2. **LLM I/O is constrained**: Every LLM input and output passes through policy enforcement.
3. **No silent failures**: Invalid schema? Retry once. Budget exceeded? Compact. Gate fails? Ask user. Unknown purpose? Error.
4. **Context is selective**: L0–L5 defaults per purpose. Escalation requires approval. Full DOM never by default.
5. **No full history**: Old plans/traces stored but not auto-sent. Memory selection is per-purpose.
6. **Tools match purpose**: Only tools in purpose.tool_policy reach LLM. Unknown tools rejected.
7. **Observability is mandatory**: Every call logged with purpose/model/context_level/tokens/latency/result.
8. **Secrets excluded**: Credentials, raw auth tokens, internal IDs never in prompts.

---

## Cluster 2 Stories

### Story List

| Story ID | Title | Type | Objective |
|----------|-------|------|-----------|
| S6-0201 | Context level policy enforcement | Core | Implement L0–L5 context level builders and defaults per purpose |
| S6-0202 | Context sufficiency gates | Core | Implement gates: user goal clear? page state known? required data available? |
| S6-0203 | Structured context request and escalation | Core | Implement context_request tool approval logic; deny unscoped/broad requests |
| S6-0204 | Memory selection policy | Core | Implement memory selection (no full history by default, selective relevant subset) |
| S6-0205 | Tool exposure enforcement | Core | Implement tool exposure matrix per purpose; only allowed tools exposed |
| S6-0206 | Schema validation and retry/fail-closed policy | Core | Implement schema validation + one retry on failure + fallback |
| S6-0207 | Token budget enforcement and telemetry | Core | Implement per-purpose token budgets; compact or ask on exceeded |
| S6-0208 | Cluster 2 integration regression | Integration | Prove all policies work together; all 14 purposes resolve; unknown purpose fails; S5 tests pass |

---

## Context Levels (L0–L5)

Cluster 2 must enforce:

```
L0: user message + minimal UI state (phase, modal open/closed)
L1: selected element descriptor (tag, class, text, position)
L2: section summary (nearby elements, visual context, heading hierarchy)
L3: page intelligence summary (page structure, DOM strength marker, recommendation)
L4: focused debug packet (failure evidence, locator candidates, recent trace, specific error)
L5: capped raw DOM (with secrets redacted, max 50KB, fallback only)
```

### Purpose Context Defaults

```
intent_classifier           → L0
clarification_generator     → L0
page_intelligence_summarizer → L1
page_validation_recommender → L3
journey_planner             → L1
step_plan_normalizer        → L1
plan_diff_editor            → L2
locator_specialist          → L2
custom_assertion_planner    → L1
execution_driver            → L0
recovery_diagnoser          → L4
replay_repair_specialist    → L4
user_response_writer        → L0
trace_summarizer            → L2
```

---

## Context Sufficiency Gates

Cluster 2 must implement gates per purpose family:

```
intent_classifier:          user goal clear (one sentence or less)?
clarification_generator:    missing field known?
page_validation_recommender: page state + page intelligence available?
journey_planner:            required pages + data types specified?
step_plan_normalizer:       stable step IDs + page snapshot available?
locator_specialist:         target element validation result available?
recovery_diagnoser:         failed operation evidence available?
custom_assertion_planner:   original step + execution result available?
```

If gate fails → ask_user clarification, never auto-escalate to L5.

---

## Context Escalation (structured request)

Cluster 2 must implement context_request tool:

```
Tool: context_request
Parameters:
  - requested_context_type: enum[L1|L2|L3|L4|L5]
  - reason: string (max 100 chars)
  - scope: string (optional, e.g., "failing_element", "error_trace")

Backend approval:
  - If requested type > purpose max level → deny + log
  - If scope is empty/unscoped for L5 → deny + log
  - If request contains "send me more context" prose → deny + log
  - Else → approve + escalate + log reason
```

---

## Memory Selection Policy

Cluster 2 must implement:

```
Default:
  - Current user message
  - Current page state (if applicable)
  - Current plan (if in planning/correction phase)
  - Current error/recovery context (if in recovery)

Excluded by default:
  - Full chat history
  - Old plans/traces (unless explicitly relevant)
  - Secrets/credentials
  - Raw full DOM

Optional (per purpose):
  - Previous accepted plans (if comparing to similar)
  - Previous rejected plans (if learning from mistakes)
  - Previous locator decisions (if same target)
  - Execution traces (if debugging similar step)
```

Size ceiling: max 20KB of memory per call (compaction if exceeded).

---

## Tool Exposure Matrix

Cluster 2 must enforce purpose → tool_policy mapping:

```
intent_classifier                → [ask_user] (no tools)
clarification_generator           → [ask_user]
page_intelligence_summarizer      → [no tools]
page_validation_recommender       → [ask_user, needs_more_context]
journey_planner                   → [ask_user, needs_more_context]
step_plan_normalizer              → [ask_user, needs_more_context] + S5-013 convergence narrowing
plan_diff_editor                  → [no tools] (LLM inspection only)
locator_specialist                → [locator_tools, inspection, ask_user]
custom_assertion_planner          → [inspection, ask_user]
execution_driver                  → [next_operation] (only confirmed operation)
recovery_diagnoser                → [diagnostic_tools, ask_user]
replay_repair_specialist          → [inspection, ask_user]
user_response_writer              → [ask_user]
trace_summarizer                  → [no tools]
```

Unknown purpose → zero tools, fail immediately.

---

## Schema Validation + Retry/Fail-Closed

Cluster 2 must implement:

```
1. LLM returns output
2. Validate against schema
3. If valid → use output
4. If invalid → log, call LLM again with "please follow schema" hint
5. If second attempt valid → use output
6. If second attempt invalid → log, apply fallback:
   - ask_user (if purpose allows)
   - fail_closed (return empty/default result)
   - escalate (move to next handler)
7. Never accept prose as structured output
```

---

## Token Budget Enforcement

Cluster 2 must enforce per-purpose budgets:

```
intent_classifier           → 500 input tokens max
clarification_generator     → 500 input
page_intelligence_summarizer → 800 input
page_validation_recommender → 1500 input
journey_planner             → 2000 input
step_plan_normalizer        → 2000 input
plan_diff_editor            → 800 input
locator_specialist          → 1500 input
custom_assertion_planner    → 1000 input
execution_driver            → 500 input
recovery_diagnoser          → 1500 input (no L5 escalation by default)
replay_repair_specialist    → 1500 input
user_response_writer        → 500 input
trace_summarizer            → 1000 input
```

If context tokens exceed budget:
1. Try compaction (remove old traces, summarize history)
2. If compaction insufficient → ask_user for clarification
3. If still over → fail_closed (no LLM call)

Never silently truncate.

---

## Telemetry

Cluster 2 must log every LLM call:

```json
{
  "purpose": "step_plan_normalizer",
  "model": "gpt-4o-mini",
  "context_level": "L1",
  "context_tokens": 1200,
  "skills_tokens": 300,
  "tools_tokens": 200,
  "total_input_tokens": 1700,
  "output_tokens": 45,
  "latency_ms": 2340,
  "finish_reason": "stop",
  "schema_validation": "passed|retry|failed",
  "result": "success|schema_failure|budget_exceeded|gate_failure"
}
```

---

## Allowed Files (for future implementation)

- `runtime/context_policy.py` (new, context level builders)
- `runtime/context_levels.py` (new, L0–L5 definitions)
- `runtime/context_gates.py` (new, sufficiency gates)
- `runtime/context_request_policy.py` (new, escalation approval)
- `runtime/memory_selection_policy.py` (new, memory filtering)
- `runtime/tool_exposure_enforcement.py` (new, tool exposure)
- `runtime/schema_validation_policy.py` (new, schema validation + retry)
- `runtime/token_budget_policy.py` (new, budget enforcement)
- `tests/test_context_policy.py` (new)
- `tests/test_context_gates.py` (new)
- `tests/test_context_request_policy.py` (new)
- `tests/test_memory_selection_policy.py` (new)
- `tests/test_tool_exposure_enforcement.py` (new)
- `tests/test_schema_validation_policy.py` (new)
- `tests/test_token_budget_policy.py` (new)
- `tests/test_cluster_2_integration.py` (new)

Minimal changes to:
- `runtime/llm_runtime_controller.py` (call policy modules, thin)

---

## Forbidden Files and Actions

- ✗ `agent.py` (no broad changes; thin orchestration only)
- ✗ `server.py`
- ✗ `runtime/` (no changes to existing except llm_runtime_controller.py minimal)
- ✗ `frontend/`
- ✗ `tests/` (no changes to existing except minimal controller fix if needed)
- ✗ Paid LLM tests (Cluster 1/2 are control plane only)
- ✗ Browser E2E tests (Cluster 1/2 are control plane only)
- ✗ Page Intelligence live invocation (that's Cluster 3)
- ✗ Journey planner implementation (that's Cluster 4)
- ✗ Replay repair implementation (that's Cluster 8)
- ✗ Modifying Sprint 5 tests

---

## Tests-First Policy

Every Cluster 2 story must:

1. **Design tests BEFORE implementation**
2. **Unit tests**: Test each policy module (context builders, gates, validators, etc.)
3. **Contract tests**: Test integration with controller and purpose registry
4. **Integration tests**: Test multiple policies working together
5. **No implementation without tests**
6. **95% coverage minimum for new modules**
7. **No paid LLM or browser E2E**

---

## 95% Coverage Rule

Every new module must reach 95% coverage:

```bash
python -m pytest tests/ --cov=runtime.context_policy --cov=runtime.context_gates --cov-fail-under=95 -q
```

If below 95%, investigate and add tests. Do not lower requirement.

---

## Required Regression Guard

After Cluster 2 complete, run full regression guard:

```bash
python -m pytest tests/test_backend_event_sequences.py tests/test_event_contract.py tests/test_recording_codegen_truth_contract.py tests/test_llm_runtime_controller_contract.py tests/test_prompt_pack_builder.py tests/test_prompt_pack_safety_rules.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_planning_convergence_contract.py tests/test_page_intelligence_schema.py tests/test_page_intelligence_fake_integration.py tests/test_replay_one.py tests/test_deterministic_fast_path.py tests/test_dom_locator_contracts.py tests/test_frontend_plan_recovery_rendering.py tests/test_frontend_recorded_code_rendering.py -q
```

Expected: 365+ tests passing, all S5 behavior unchanged.

---

## Definition of Done

Cluster 2 is complete and ready for Cluster 3 only when:

- [ ] All 8 stories marked Done
- [ ] Context levels L0–L5 enforced per purpose default
- [ ] Sufficiency gates implemented for all purpose families
- [ ] Context escalation requests backend-approved (unscoped denied)
- [ ] Memory selection prevents full-history prompting
- [ ] Tool exposure strictly matched to purpose policy
- [ ] Schema validation with retry/fail-closed implemented
- [ ] Token budgets enforced with compaction/clarification
- [ ] Unknown/malformed purpose fails closed
- [ ] All policies work together (S6-0208 integration tests pass)
- [ ] 95% coverage for all new/modified modules
- [ ] Regression guard passes (all 365+ tests)
- [ ] No paid LLM/E2E run
- [ ] No regressions vs Sprint 5 (S5 tests still pass)
- [ ] All story commits approved
- [ ] No product behavior changes implemented (policies enforced but no new flows)

---

## Stop Conditions

Stop and ask for clarification if:

- A context level cannot be built (e.g., L3 requires Page Intelligence but it's not live yet)
- Gate logic is ambiguous for a purpose
- Cannot define clear token budgets
- Sufficiency gates and context escalation conflict
- Coverage requirement cannot be met
- Regression guard fails (stop, fix before proceeding)
- S5 convergence tests fail (cannot change convergence narrowing behavior)

---

## Execution Notes

### One Story at a Time

Give Claude Code one story at a time, in order:

```
S6-0201 → S6-0202 → S6-0203 → S6-0204 → S6-0205 → S6-0206 → S6-0207 → S6-0208
```

Each story depends on prior ones.

### Commit After Each Story

```bash
git commit -m "feat: s6-0201 context level enforcement

Implemented L0-L5 context builders and defaults per purpose.
Tests: [count] unit, [count] contract. Coverage: 96%.
Regression guard: passed."
```

### Review Between Stories

After each story:
1. Coverage ≥95%?
2. Tests pass?
3. Regression guard pass?
4. If all yes → approve next story
5. If any no → stop, fix

---

## Multi-Story Dependencies

```
S6-0201 (context levels)
  → S6-0202 (gates)
    → S6-0203 (escalation)
      → S6-0204 (memory)
        → S6-0205 (tools)
          → S6-0206 (schema)
            → S6-0207 (tokens)
              → S6-0208 (integration)
```

S6-0201 output (context builders) feeds into S6-0202 gates. S6-0203 escalation uses gates. Etc.

---

## What Cluster 2 Does NOT Include

- ✗ Page Intelligence live invocation (Cluster 3)
- ✗ Journey planner (Cluster 4)
- ✗ Plan discussion/correction UI (Cluster 5)
- ✗ Locator recovery/update flow (Cluster 6)
- ✗ Replay repair product behavior (Cluster 8)
- ✗ Anything that changes LLM call semantics (just enforce policies)
- ✗ Frontend UI changes (just control plane)

Cluster 2 is enforcement-only. No new features, no new flows, just policy enforcement.

---

## After Cluster 2

Cluster 3 uses the enforced policies to implement Page Intelligence live invocation:

```
Cluster 3 = Live Page Intelligence Injection

Uses:
- S6-0201 context levels (Page Intel is L3 context)
- S6-0202 gates (Page Intel available? yes → proceed)
- S6-0203 escalation (if Page Intel insufficient, request escalation)
- S6-0204 memory (previous Page Intel selections)
- S6-0205 tools (Page Intel is context only, no tools)
- S6-0206 schema (Page Intel schema from Sprint 5)
- S6-0207 tokens (Page Intel packet token budget)
```

Cluster 3 is first feature work. Cluster 1–2 are foundational policy work.

---

## Open Questions

- Is L3 (page intelligence) always available, or should gates check? (Decide in S6-0202)
- Should unknown context level be L0 or error? (Should be error, fail closed)
- Can context be compacted below minimum? (Decide in S6-0207: no, fail instead)
- Should retry happen silently or log? (Should log: allows debugging)

---

## Validation Checklist

Before approving Cluster 2, verify:

- [ ] All 8 story files exist and readable
- [ ] Each story follows S6-0005 template
- [ ] Each story has explicit tests-first section
- [ ] Each story forbids paid LLM/E2E
- [ ] Each story forbids broad agent.py changes
- [ ] Context levels L0–L5 clearly defined
- [ ] Purpose context defaults table included
- [ ] Sufficiency gates per purpose defined
- [ ] Tool exposure matrix defined
- [ ] Token budgets per purpose defined
- [ ] Regression guard passes S5 tests
- [ ] Definition of Done is specific
- [ ] Stop conditions are clear
- [ ] No product code changes in planning files

---

## Notes

- Cluster 2 enforces Cluster 1 policies. Cannot proceed without Cluster 1 complete.
- Cluster 2 is foundational for all future feature work (Cluster 3+).
- Cluster 2 is low-risk (enforcement only, no behavioral changes unless policy violated).
- Cluster 2 unblocks Cluster 3 (Page Intelligence live) and all downstream clusters.
- Cluster 1 + Cluster 2 together establish the complete control plane for Complete LLM Mode.
