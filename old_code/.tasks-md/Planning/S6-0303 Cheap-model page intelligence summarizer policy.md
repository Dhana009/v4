# S6-0303 Cheap-model page intelligence summarizer policy

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 1 (core)  
**Type:** Feature / Policy  
**Status:** Planning  
**Owner:** LLM Policy  
**Blocks:** S6-0304, S6-0305  
**Blocked by:** S6-0302  

---

## Purpose

Add or complete the `page_intelligence_summarizer` model path for cases deterministic extraction is insufficient. Purpose policy, cheap model class, L3 context, inspection-only tools, output schema, backend validator, and deterministic fallback. No main orchestrator planning, no final locator truth, no execution.

---

## Source rules

- Cluster 2 policy enforcement exists (S6-0202 through S6-0207)
- `page_intelligence_summarizer` purpose must be declared in typed registry (S6-0102)
- Purpose must have: model class, context level, tools, schema, validator, fallback
- Fallback is deterministic extraction from S6-0302

---

## What it contains

```
- purpose policy usage (from S6-0102 registry)
- cheap model class definition
- L3 context level
- inspection-only tools if needed
- page intelligence output schema
- backend validator
- deterministic fallback
```

---

## What it must NOT contain

```
- no main orchestrator planning
- no final locator truth
- no execution
- no user-facing plan generation
```

---

## Tests first

### Unit tests

```
- summarizer policy resolves correctly
- cheap model class instantiated
- allowed tools are inspection-only
- schema validator rejects incomplete summary
- deterministic fallback used on failure
```

### Contract tests

```
- cheap model output cannot mark locator final
- source field is deterministic / cheap_model / mixed
- semantic quality and ambiguity fields required
- no tool_choice=required for non-critical tools
```

### Integration tests

```
- fake cheap model creates valid summary
- malformed cheap model output retries once then falls back
- fallback extraction is used when summarizer times out
```

Coverage: **95% for page_intelligence_summarizer policy**

---

## Out of scope

- Do not refactor broader LLM policy (S6-0102 registry exists)
- Do not run paid LLM
- Do not change main planning path

---

## Allowed files

```
runtime/llm_policy_registry.py (extend with summarizer policy)
tests/test_page_intelligence_summarizer_policy.py (new)
Minor edits to:
  - runtime/llm_runtime_controller.py
  - runtime/page_intelligence_live.py
```

---

## Forbidden files

- No changes to broader policy framework (Cluster 2 rules)
- No paid LLM integration

---

## Implementation notes

### Approach

1. In `runtime/llm_policy_registry.py` (or policy module), add `page_intelligence_summarizer` purpose with:
   - Model class: cheap (from model_router.py)
   - Context level: L3 (bounded extraction context)
   - Skills: inspection-only (no action/click/form skills)
   - Tools: inspection tools only (locator_hints, page_semantics, no browser-changing)
   - Output schema: PageIntelligenceSummary
   - Validator: schema validation + required field checks
   - Fallback: deterministic extraction (S6-0302)

2. Create `tests/test_page_intelligence_summarizer_policy.py`:
   - Policy resolution tests
   - Cheap model class tests
   - Tool filtering tests (no execution tools)
   - Schema validation tests
   - Fallback behavior tests

3. Update `runtime/page_intelligence_live.py` to use policy:
   - Call controller.call(purpose="page_intelligence_summarizer", ...)
   - On failure, fall back to deterministic extraction
   - Log retry/fallback telemetry

### Key invariants

- Cheap model cannot mark locator as final/confirmed
- Source field indicates origin (deterministic/cheap_model/mixed)
- No execution tools available
- Fallback is automatic and transparent

---

## Validation commands

```bash
python -m pytest tests/test_page_intelligence_summarizer_policy.py::test_policy_resolves -v
python -m pytest tests/test_page_intelligence_summarizer_policy.py::test_cheap_model_class -v
python -m pytest tests/test_page_intelligence_summarizer_policy.py::test_inspection_only_tools -v
python -m pytest tests/test_page_intelligence_summarizer_policy.py::test_fallback -v
coverage run -m pytest tests/test_page_intelligence_summarizer_policy.py
```

---

## Artifact/evidence requirement

- [ ] `page_intelligence_summarizer` policy declared in registry
- [ ] Tests verify cheap model class
- [ ] Tests verify inspection-only tools
- [ ] Tests verify schema validation
- [ ] Tests verify fallback to deterministic extraction
- [ ] 95% coverage
- [ ] Policy correctly documented

---

## Stop conditions

- Registry structure unclear (read S6-0102)
- Cheap model class not available (check model_router.py)
- Fallback fails (coordinate with S6-0302)

---

## Sign-off

- [x] Story is specific (add summarizer policy)
- [x] Scope is bounded (policy only, no execution)
- [x] Tests are first
- [x] Depends on S6-0302 (fallback target)
