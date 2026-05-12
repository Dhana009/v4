# S6-0301 Page Intelligence live invocation before planning

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 1 (core)  
**Type:** Feature / Integration  
**Status:** Planning  
**Owner:** Runtime Integration  
**Blocks:** S6-0302, S6-0303  
**Blocked by:** S6-0102  

---

## Purpose

Wire existing Page Intelligence schema/fake integration into the live planning path. Detect when page/section intelligence is needed, call deterministic extraction first, build PageIntelligenceSchema, and pass compact packet to LLMRuntimeController context. No raw full DOM by default.

---

## Source rules

- Runtime Policy Spec: Page Intelligence prepares compact context before Main LLM
- S5-009 Page Intelligence schema exists (page_intelligence_schema.py)
- S5-010 fake integration exists (page_intelligence_fake_integration.py)
- Step Plan Normalizer must receive PAGE_INTELLIGENCE_PACKET not raw DOM
- Cluster 2 policy enforcement is in place (S6-0102 through S6-0208)

---

## What it contains

```
- detect when page/section intelligence is needed
- call deterministic page/section extraction first
- build PageIntelligenceSchema
- convert to PAGE_INTELLIGENCE_PACKET
- pass compact packet to LLMRuntimeController context
- log page intelligence telemetry
- graceful fallback if Page Intelligence fails
```

---

## What it must NOT contain

```
- no raw full DOM by default
- no broad agent.py refactor
- no new browser-changing tools
- no plan execution
- no frontend UI implementation
- no paid E2E
```

---

## Tests first

### Unit tests

```
- weak DOM context triggers Page Intelligence packet creation
- normal semantic page can skip or produce minimal packet
- schema failure falls back safely
- packet is JSON-only and HTML-free
```

### Contract tests

```
- packet uses PAGE_INTELLIGENCE_PACKET format
- token estimate stays within configured limit
- no raw DOM included
- telemetry records page_intelligence_summarizer purpose/context level
```

### Integration tests

```
- step_plan_normalizer receives Page Intelligence packet
- S5-013 convergence behavior still passes
- ambiguous action still asks user safely
```

### Regression tests

```
- existing Page Intelligence schema/fake integration tests
- planning convergence tests
- tool policy tests
```

Coverage: **95% for new/changed Page Intelligence wiring module**

---

## Out of scope

- Do not refactor agent.py broadly (only thin orchestration wiring allowed)
- Do not implement paid LLM calls (use fake integration)
- Do not execute plans (planning only)
- Do not change browser-changing tool set

---

## Allowed files

```
runtime/page_intelligence_live.py (new)
tests/test_page_intelligence_live.py (new)
Minor edits to:
  - runtime/llm_runtime_controller.py (thin call site)
  - runtime/step_plan_normalizer.py (receive packet)
```

---

## Forbidden files

- No changes to runtime/page_intelligence_schema.py (S5-009 contract)
- No changes to runtime/page_intelligence_fake_integration.py (S5-010)
- No broad agent.py refactor
- No frontend code

---

## Implementation notes

### Approach

1. Read `runtime/page_intelligence_schema.py` to understand existing PageIntelligenceSchema format
2. Read `runtime/page_intelligence_fake_integration.py` to understand fake integration contract
3. Create `runtime/page_intelligence_live.py` with:
   - `needs_page_intelligence(context, last_page_url)` → bool
   - `invoke_page_intelligence(page_url, selected_section)` → PAGE_INTELLIGENCE_PACKET
   - Fallback to deterministic extraction if schema fails
4. Update `runtime/llm_runtime_controller.py` to call page_intelligence_live.invoke() when needed
5. Update `runtime/step_plan_normalizer.py` to accept PAGE_INTELLIGENCE_PACKET parameter
6. Add telemetry logging for page_intelligence_summarizer purpose usage
7. Write unit/contract/integration tests

### Key invariants

- Page Intelligence packet is always JSON, never raw HTML
- Packet token size is estimated and logged
- Fallback to deterministic extraction is transparent (no LLM call)
- Existing S5-013 convergence tests still pass

---

## Validation commands

```bash
# Verify Page Intelligence packet format
python -m pytest tests/test_page_intelligence_live.py::test_packet_format -v

# Verify no raw DOM in packet
python -m pytest tests/test_page_intelligence_live.py::test_no_html_in_packet -v

# Verify convergence still passes
python -m pytest tests/test_planning_convergence_contract.py -v

# Check coverage
coverage run -m pytest tests/test_page_intelligence_live.py
coverage report --include=runtime/page_intelligence_live.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/page_intelligence_live.py` created
- [ ] `tests/test_page_intelligence_live.py` created (unit + contract + integration)
- [ ] PAGE_INTELLIGENCE_PACKET flows from detection → invocation → controller → normalizer
- [ ] Fallback to deterministic extraction verified
- [ ] No raw HTML in packet (contract test enforces)
- [ ] 95% coverage for new module
- [ ] S5-013 convergence tests pass
- [ ] Telemetry records page intelligence purpose usage

---

## Stop conditions

- Cannot determine if existing schema is complete (read S5-009 spec)
- Fallback extraction fails (defer to S6-0302)
- Convergence tests fail (investigate + fix before closing story)

---

## Sign-off

- [x] Story is specific (wire Page Intelligence into planning)
- [x] Scope is bounded (no raw DOM, no execution)
- [x] Tests are first (unit → contract → integration)
- [x] Blocks are clear (S6-0302 depends on this)
