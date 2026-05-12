# S6-0203 Structured context request and escalation

**Sprint:** Sprint 6  
**Cluster:** 2 (Context/Memory/Token/Tool/Schema Policy Enforcement)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Runtime Policy  
**Blocks:** S6-0204, S6-0207, S6-0208  
**Blocked by:** S6-0202  

---

## Purpose

Allow LLM to request more context ONLY through backend-approved context_request tool. Backend denies unscoped requests (e.g., "send me more context") and broad requests (e.g., "full DOM"). Approved escalations are logged with reason.

---

## Source rules

- Runtime Policy Spec: LLM context_request must include type/reason/scope
- Runtime Policy Spec: backend denies context request if purpose disallows
- Runtime Policy Spec: backend denies broad/unscoped full DOM request
- Runtime Policy Spec: approved request logs escalation reason
- Coverage requirement: 95%

---

## Current evidence

### What exists

- `runtime/context_policy.py` (from S6-0201)
- `runtime/context_gates.py` (from S6-0202)
- Tool schema infrastructure (from Sprint 5)

### What gaps exist

- No context_request tool
- No backend approval logic for escalation
- No escalation logging

---

## Desired behavior

### context_request tool schema

```python
{
  "name": "context_request",
  "parameters": {
    "requested_context_type": "enum[L1|L2|L3|L4|L5]",
    "reason": "string (max 100 chars)",
    "scope": "string (optional, e.g. 'failing_element' or 'entire_page')"
  }
}
```

### Approval logic

- If purpose forbids escalation → deny + log
- If requested type > purpose max level → deny + log
- If scope is unscoped/broad → deny + log
- Else → approve + escalate + log reason

### Denied escalation response

Backend returns:
```python
{
  "approved": False,
  "reason": "cannot escalate to full DOM for planning purpose",
  "fallback": "ask_user"
}
```

Approved escalation:
```python
{
  "approved": True,
  "escalated_context": "...",
  "escalation_reason": "user_requested_full_dom_for_recovery"
}
```

---

## Out of scope

- Do not implement full DOM sending (just gating)
- Do not change Page Intelligence invocation
- Do not run paid LLM

---

## Allowed files

- `runtime/context_request_policy.py` (new)
- `runtime/context_escalation_logger.py` (new, if modular)
- `tests/test_context_request_policy.py` (new)

---

## Forbidden files

- ✗ agent.py
- ✗ Tool schema modifications (use existing framework)

---

## Tests first

### Unit tests

- `test_context_request_must_include_type_and_reason()`
- `test_context_request_rejects_unscoped_scope()`
- `test_context_request_rejects_escalation_beyond_purpose_max()`
- `test_context_request_rejects_broad_full_dom_request()`
- `test_context_request_approves_scoped_escalation()`
- `test_approved_escalation_is_logged()`
- `test_denied_escalation_is_logged()`
- `test_fallback_issued_on_denial()`

### Contract tests

- `test_controller_routes_context_request_to_policy()`
- `test_planning_purpose_cannot_escalate_to_l5()`
- `test_recovery_purpose_can_escalate_to_l4()`

File: `tests/test_context_request_policy.py`

---

## Implementation notes

### Approach

1. Create `context_request_policy.py`:
   ```python
   PURPOSE_MAX_CONTEXT_LEVEL = {
     "intent_classifier": "L0",
     "page_validation_recommender": "L3",
     "recovery_diagnoser": "L4",
     ...
   }
   
   def process_context_request(purpose_id, requested_type, reason, scope):
       max_allowed = PURPOSE_MAX_CONTEXT_LEVEL[purpose_id]
       if requested_type > max_allowed:
           return {"approved": False, "reason": "exceeds purpose max"}
       if scope is None or scope == "":
           return {"approved": False, "reason": "scope required"}
       # Approve and escalate
       return {"approved": True, "escalated_context": build_context(requested_type, scope)}
   ```

2. Add escalation logging:
   - Log approved escalations with reason
   - Log denied escalations with purpose/reason
   - Include tokens spent

3. Integrate with controller (minimal call)

4. Write tests (8+ unit, 2+ contract)

### Key invariants

- No free-form "send more context" prose (requires structured request)
- Planning purposes have hard ceiling (no L5)
- Recovery/debug purposes can escalate higher
- All escalations logged

---

## Coverage requirement

95% for context_request_policy.py.

---

## Validation commands

```bash
python -m pytest tests/test_context_request_policy.py -q
python -c "
from runtime.context_request_policy import PURPOSE_MAX_CONTEXT_LEVEL
for p in ['intent_classifier', 'recovery_diagnoser', 'page_validation_recommender']:
  print(f'{p}: max level = {PURPOSE_MAX_CONTEXT_LEVEL.get(p)}')
"
```

---

## Artifact/evidence requirement

- [ ] `runtime/context_request_policy.py` — approval logic
- [ ] Escalation logging (approved + denied)
- [ ] 10+ tests passing
- [ ] Coverage ≥95%
- [ ] Commit message references context escalation

---

## Stop conditions

- Cannot define which purposes can escalate (clarify spec)
- Coverage below 95%

---

## Sign-off

- [x] Story focused (context request approval)
- [x] Tests verify strict approval rules
- [x] All escalations logged
