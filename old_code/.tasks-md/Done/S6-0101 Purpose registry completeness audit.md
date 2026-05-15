# S6-0101 Purpose registry completeness audit

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 1 (core)  
**Type:** Discovery / Documentation  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** S6-0102, S6-0103, S6-0104, S6-0105, S6-0106, S6-0107  
**Blocked by:** (none)  

---

## Purpose

Audit current repo reality: which LLM purposes exist, how they're called, which have controller coverage, which are missing. Output mapping identifies gaps before writing code.

---

## Source rules

- Runtime Policy Spec: every LLM call must go through LLMRuntimeController
- Runtime Policy Spec: every purpose must have model/context/skill/tool/schema/validator/fallback policy
- Sprint 5 completion: model_router.py and llm_runtime_controller.py exist, partially wired
- Cluster 1 goal: all 14 required LLM purposes declared in typed policy registry

---

## Current evidence

### What exists in the repo

- `runtime/llm_runtime_controller.py` — controller exists, partially wired
- `runtime/model_router.py` — routing logic for cheap/main/debug classes
- `runtime/skill_policy.py` — skill loading logic
- `runtime/tool_schema_policy.py` — tool filtering by purpose
- `runtime/prompt_pack_builder.py` — prompt pack construction
- `agent.py` — orchestration, multiple LLM call sites
- `tests/test_llm_runtime_controller_contract.py` — controller tests exist
- S5-013 convergence narrowing — pass/fail behavior verified in test_planning_convergence_contract.py

### What gaps exist

- No unified LLM purpose registry (all 14 purposes listed in one place with complete metadata)
- No inventory of where each purpose is called (agent.py, locator, replay, etc.)
- Controller wiring incomplete (some call sites bypass or partially wrap controller)
- Unknown if all required purposes (intent_classifier, journey_planner, recovery_diagnoser, etc.) are even present
- No mapping of purpose → model class → context level → skills → tools → schema → validator → fallback

### Test status

- Controller contract tests exist but sparse (focused on call/dispatch only)
- No purpose registry tests (will come in S6-0102)
- No paid LLM tests for each purpose (will come in later clusters)

---

## Desired behavior

### High-level expectation

Audit produces a definitive mapping of:

1. Every LLM purpose required by Runtime Policy Spec
2. Current call site(s) in repo
3. Controller ownership status (yes/no/partial)
4. Required metadata (model, context, skills, tools, schema, validator, fallback)
5. Coverage status (Done / Partial / Missing / Unknown)
6. Test evidence for each purpose

### Output

```
.tasks-md/Planning/S6-0101-PURPOSE-REGISTRY-AUDIT.md
```

### Required audit matrix

Each purpose row:

```
| Purpose ID | Current call site | Controller-owned? | Model class | Context level | Skills | Tools | Schema | Validator | Fallback | Tests found | Gaps |
```

### Audit scope

Read-only inspection of:

```
runtime/llm_runtime_controller.py
runtime/model_router.py
runtime/tool_schema_policy.py
runtime/skill_policy.py
runtime/prompt_pack_builder.py
runtime/prompt_packs.py
runtime/telemetry.py
runtime/page_intelligence_schema.py
agent.py (all LLM call sites)
recording/codegen.py
recording/replay.py
locator/engine.py
tests/test_llm_runtime_controller_contract.py
tests/test_planning_convergence_contract.py
tests/test_page_intelligence_fake_integration.py
.tasks-md/RUNTIME-POLICY-SPEC.md (source)
PRD v2.3 (reference)
```

---

## Out of scope

- Do not modify any code (read-only audit)
- Do not create tests
- Do not run paid LLM
- Do not implement missing purposes

---

## Allowed files

- `.tasks-md/Planning/S6-0101-PURPOSE-REGISTRY-AUDIT.md` (new, output only)

---

## Forbidden files

- No changes to runtime/
- No changes to agent.py
- No test implementations
- No product code changes

---

## Tests first (audit phase)

Not applicable. Discovery story produces documentation, not code.

---

## Implementation notes

### Approach

1. List all 14 required LLM purposes from Runtime Policy Spec
2. For each purpose, search repo for call sites:
   - `grep` for purpose name in agent.py, recording/, locator/, runtime/
   - Identify function that calls LLM (with or without controller)
   - Check if controller.call(purpose=...) pattern is used
3. Extract metadata for each purpose:
   - Model class (cheap/main/debug or literal model name)
   - Context level (L0–L5 or unknown)
   - Skills (from skill_policy.py)
   - Tools (from tool_schema_policy.py)
   - Schema (from prompt_pack_builder or inline)
   - Validator (exists? yes/no)
   - Fallback (defined? yes/no)
4. Count tests per purpose (unit/contract/integration/E2E)
5. Classify each purpose: Done / Partial / Missing / Unknown
6. List gaps for Cluster 1 implementation

### Key invariants

- Audit is objective (grep + file read only, no guessing)
- Mapping is complete (all 14 purposes present, even if missing)
- Coverage baseline established before S6-0102

---

## Coverage requirement

Not applicable (discovery, no code).

---

## Validation commands

```bash
# Verify all policy files exist and are readable
ls -la runtime/llm_runtime_controller.py runtime/model_router.py runtime/tool_schema_policy.py runtime/skill_policy.py runtime/prompt_pack_builder.py

# Verify audit output created
ls -la .tasks-md/Planning/S6-0101-PURPOSE-REGISTRY-AUDIT.md

# Spot-check one purpose in audit (should show call site, metadata, gaps)
grep -A5 "intent_classifier" .tasks-md/Planning/S6-0101-PURPOSE-REGISTRY-AUDIT.md
```

---

## Artifact/evidence requirement

- [ ] `.tasks-md/Planning/S6-0101-PURPOSE-REGISTRY-AUDIT.md` created
- [ ] All 14 purposes listed
- [ ] Each purpose classified (Done/Partial/Missing/Unknown)
- [ ] Call sites identified
- [ ] Metadata extracted
- [ ] Gaps clearly noted

---

## Stop conditions

- Cannot determine if controller wraps a purpose (unclear code)
- Call site is in external file (not in .tasks-md scope)
- Purpose listed in PRD but not found anywhere in repo (check PRD version)

---

## Sign-off

- [x] Story is specific (produce audit matrix)
- [x] Scope is read-only (discovery)
- [x] Output is actionable (drives S6-0102 story)
- [x] Blocks are clear (all Cluster 1 stories depend on output)
