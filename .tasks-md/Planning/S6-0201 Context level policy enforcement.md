# S6-0201 Context level policy enforcement

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Runtime Policy  
**Blocks:** S6-0202, S6-0203, S6-0204, S6-0205, S6-0206, S6-0207, S6-0208  
**Blocked by:** S6-0107 (Cluster 1 complete)  

---

## Purpose

Implement L0–L5 context level enforcement. Ensure planning/recommendation purposes never receive raw DOM by default; recovery/debug purposes receive focused packets only. Backend builds context, controller enforces level.

---

## Source rules

- Runtime Policy Spec: context levels L0–L5 defined with strict rules
- Runtime Policy Spec: full raw DOM not sent by default
- Runtime Policy Spec: escalation only when sufficiency gates fail
- Coverage requirement: 95% for new policy modules
- Modularization rule: policy logic in runtime/ modules

---

## Current evidence

### What exists

- `runtime/llm_purpose_registry.py` — purposes defined (from Cluster 1)
- `runtime/llm_purpose_policy.py` — 14 purpose policies (from Cluster 1)
- `agent.py` — currently builds ad-hoc context for LLM calls
- Page intelligence schema exists (Sprint 5)

### What gaps exist

- No L0–L5 context level policy enforcement
- No default context level per purpose
- No escalation logic (stay at L0 until gates fail)
- No raw DOM rejection (currently sent in some paths)

---

## Desired behavior

### Context levels defined

```
L0: user message + minimal UI state (current phase, modal state)
L1: selected element descriptor (tag, class, text, position)
L2: selected section summary (nearby elements, visual context)
L3: page intelligence summary (page structure, heading hierarchy, DOM strength)
L4: focused debug packet (specific failure evidence, locator packets, traces)
L5: capped raw DOM (with secrets/credential redaction, max 50KB)
```

### Purpose defaults

```
intent_classifier      → L0
clarification_generator → L0
page_validation_recommender → L3 (needs page summary)
journey_planner        → L1
step_plan_normalizer   → L1
plan_diff_editor       → L2
locator_specialist     → L2 (section summary)
execution_driver       → L0 (confirmed operation only)
recovery_diagnoser     → L4 (focused error packet)
replay_repair_specialist → L4 (replay evidence)
custom_assertion_planner → L1
user_response_writer   → L0
trace_summarizer       → L2
page_intelligence_summarizer → L1
```

### Out of scope

- Do not wire Page Intelligence live yet (that's Cluster 3)
- Do not implement context request handler (that's S6-0203)
- Do not build context escalation logic (that's S6-0202)
- Do not run paid LLM

---

## Allowed files

- `runtime/context_policy.py` (new)
- `runtime/context_levels.py` (new)
- `runtime/dom_summarizer.py` (new, if modular, for section summaries)
- `tests/test_context_policy.py` (new)

---

## Forbidden files

- ✗ agent.py (no orchestration changes)
- ✗ Page Intelligence live invocation
- ✗ Existing tests
- ✗ Context request handler (comes in S6-0203)

---

## Tests first

### Unit tests

- `test_intent_classifier_gets_l0_default()`
- `test_page_validation_recommender_gets_l3_default()`
- `test_recovery_diagnoser_gets_l4_default()`
- `test_context_level_includes_only_authorized_data()`
- `test_l5_excludes_secrets_and_credentials()`
- `test_l5_caps_raw_dom_at_50kb()`
- `test_planning_purpose_never_gets_raw_dom()`
- `test_execution_driver_never_gets_raw_dom()`
- `test_context_builder_respects_level_ceiling()`

### Contract tests

- `test_purpose_policy_has_context_level()`
- `test_controller_uses_purpose_default_context_level()`
- `test_l0_contains_no_dom()`
- `test_l3_contains_page_intelligence()`
- `test_l4_contains_focused_error_packet()`

File: `tests/test_context_policy.py`

---

## Implementation notes

### Approach

1. Create `context_levels.py`:
   ```python
   CONTEXT_LEVELS = {
     "L0": {"name": "user_message_only", "includes": ["phase", "modal_state"]},
     "L1": {"name": "element_descriptor", "includes": ["tag", "text", "position"]},
     "L2": {"name": "section_summary", ...},
     ...
   }
   ```

2. Create `context_policy.py`:
   ```python
   PURPOSE_CONTEXT_DEFAULTS = {
     "intent_classifier": "L0",
     "page_validation_recommender": "L3",
     ...
   }
   
   def get_context_for_purpose(purpose_id: str, level: str = None):
       if level is None:
           level = PURPOSE_CONTEXT_DEFAULTS[purpose_id]
       return build_context(level, exclude_secrets=True)
   ```

3. Create context builders for each level:
   - L0: build minimal state message
   - L1: extract element descriptor from page state
   - L2: build section summary (maybe use existing DOM utilities)
   - L3: get page intelligence summary (when available)
   - L4: build focused debug packet (error evidence)
   - L5: build raw DOM (with redaction + capping)

4. Add validators:
   - L0 contains no DOM
   - L5 has secrets redacted
   - L5 is capped at 50KB

5. Write tests (9+ unit, 5+ contract)

### Key invariants

- Planning purposes default to L0–L2 (never L5)
- Recovery purposes default to L4 (focused, not raw)
- Escalation logic is separate (comes in S6-0202)
- Secrets/credentials always redacted

---

## Coverage requirement

95% for context policy modules.

---

## Validation commands

```bash
python -m pytest tests/test_context_policy.py -q
python -c "
from runtime.context_policy import PURPOSE_CONTEXT_DEFAULTS
for p_id in ['intent_classifier', 'page_validation_recommender', 'recovery_diagnoser']:
  print(f'{p_id}: {PURPOSE_CONTEXT_DEFAULTS[p_id]}')
"
```

---

## Artifact/evidence requirement

- [ ] `runtime/context_levels.py` — L0–L5 definitions
- [ ] `runtime/context_policy.py` — purpose defaults + builders
- [ ] Context builders for each level (functions or classes)
- [ ] Validators (no raw DOM for planning, etc.)
- [ ] 14+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references context level enforcement

---

## Stop conditions

- Cannot define clear secrets redaction (clarify policy)
- L3 requires Page Intelligence (but PI not yet live — handle gracefully)
- Existing tests fail
- Coverage below 95%

---

## Sign-off

- [x] Story focused (L0–L5 enforcement)
- [x] Tests verify no raw DOM leaks
- [x] Secrets redaction included
- [x] Defaults per purpose clear
