# S6-0107 Controller call-site inventory and migration guard

**Sprint:** Sprint 6  
**Cluster:** 1 (LLM Runtime Purpose Coverage)  
**Tier:** 2 (supporting)  
**Type:** Discovery / Documentation  
**Status:** Done  
**Owner:** Runtime Policy  
**Blocks:** (none, closes Cluster 1)  
**Blocked by:** S6-0106  

---

## Purpose

Audit every LLM call site in repo. Classify as: controller-owned, deterministic/no-model, pending migration, or obsolete. Output migration inventory for future work.

---

## Source rules

- Runtime Policy Spec: all LLM calls must go through LLMRuntimeController
- Runtime Policy Spec: unknown purpose fails closed (from S6-0102)
- Cluster 1 goal: all 14 purposes have policy (S6-0102 through S6-0106)
- Cluster 2 goal: enforce policies at runtime (will use this inventory)

---

## Current evidence

### What exists

- `runtime/llm_runtime_controller.py` — controller (partially wired)
- `agent.py` — main orchestration (multiple LLM call sites)
- `recording/codegen.py` — code generation (possible LLM calls)
- `locator/engine.py` — locator logic (possible LLM-driven locator)
- `runtime/page_intelligence_schema.py` — page intelligence (LLM-driven summarization)
- Grep hints: search for "call_llm", "openai", "model=", "purpose=" patterns

### What gaps exist

- No unified inventory of all LLM call sites
- Unknown if all call sites use controller or bypass it
- Unknown which call sites need migration to use S6-0102+ purposes
- Some deterministic/non-LLM "calls" may be listed as LLM calls (need filtering)

---

## Desired behavior

### High-level expectation

Audit produces:

1. Complete inventory of every LLM call site (file + line)
2. Classification of each (controller-owned / deterministic / pending / obsolete)
3. Migration mapping (pending sites → which purpose from S6-0102+)
4. Risk assessment (what breaks if we enforce controller-only)
5. Proposed migration order (Cluster 2+ work)

### Output

```
.tasks-md/Planning/S6-0107-CONTROLLER-CALLSITE-INVENTORY.md
```

### Inventory matrix

```
| File | Line | Function | LLM call pattern | Current status | Classification | Purpose (if applicable) | Blocker | Notes |
```

### Status classifications

- **controller-owned**: already goes through LLMRuntimeController
- **deterministic/no-model**: not an LLM call (e.g., local computation, regex)
- **pending-migration**: needs to be moved to controller + one of 14 purposes
- **obsolete/dead**: code is unreachable or commented out

---

## Out of scope

- Do not modify code (read-only audit)
- Do not implement migrations (that's Cluster 2 or later)
- Do not run paid LLM
- Do not run tests (analysis only)

---

## Allowed files

- `.tasks-md/Planning/S6-0107-CONTROLLER-CALLSITE-INVENTORY.md` (new, output only)

---

## Forbidden files

- No code changes
- No test changes

---

## Tests first (audit phase)

Not applicable. Discovery story.

---

## Implementation notes

### Approach

1. Search for LLM call patterns in entire repo:
   - `grep -r "call_llm" .`
   - `grep -r "openai\|anthropic" . --include="*.py"`
   - `grep -r "model=" . --include="*.py"`
   - `grep -r "llm\(" . --include="*.py"`
   - `grep -r "purpose=" . --include="*.py"`

2. For each result, inspect code:
   - Confirm it's an actual LLM call (not string comment, not test mock)
   - Identify function/module that makes the call
   - Check if call is already wrapped in controller.call_llm()
   - If not, determine which of 14 purposes it should use
   - Check if target purpose is ready (S6-0102+ complete)

3. Classify each:
   - If wrapped in controller + valid purpose → controller-owned
   - If wrapped in controller + invalid purpose → pending-migration
   - If not wrapped → pending-migration
   - If it's deterministic (no model involved) → filter out
   - If code is dead (commented, in xfail, in skip) → obsolete

4. Build inventory table with all info

5. Propose migration order:
   - Phase 1 (low-risk): deterministic + low-risk purposes
   - Phase 2 (medium-risk): planning purposes
   - Phase 3 (high-risk): execution/recovery purposes
   - Phase 4 (deferred): future/experimental purposes

### Key invariants

- Audit is non-invasive (grep + inspect only)
- Every call site has a row
- Classification is objective (controller or not, purpose assigned or not)
- Dead code is removed from inventory

---

## Coverage requirement

Not applicable (discovery).

---

## Validation commands

```bash
# Verify repo can be searched
find . -name "*.py" | head -10

# Verify audit file created
ls -la .tasks-md/Planning/S6-0107-CONTROLLER-CALLSITE-INVENTORY.md

# Spot-check: count LLM-related lines
grep -r "call_llm" . --include="*.py" | wc -l
```

---

## Artifact/evidence requirement

- [ ] `.tasks-md/Planning/S6-0107-CONTROLLER-CALLSITE-INVENTORY.md` created
- [ ] All LLM call sites identified (>5 expected)
- [ ] Each classified (controller-owned/deterministic/pending/obsolete)
- [ ] Purpose assignments clear (which of 14 purposes)
- [ ] Migration order proposed (phased)
- [ ] Risk assessment included (what breaks if enforced)

---

## Stop conditions

- Grep patterns miss major LLM call sites (validate manually)
- Cannot determine if call is real LLM or mock/test
- Call sites reference external APIs (not in .tasks-md scope)
- Classification is ambiguous (likely needs clarification from user)

---

## Sign-off

- [x] Audit is comprehensive (all call sites)
- [x] Classification is objective (controller or not)
- [x] Migration path is clear (purpose assignments)
- [x] Risk is assessed (enforcement impact)
