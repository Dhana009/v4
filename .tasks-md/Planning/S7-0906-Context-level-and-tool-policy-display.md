# S7-0906 — Context Level and Tool Policy Display

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0901]

---

## Objective

Show context level and tool policy used by LLM call or runtime phase in Trace. Display context level (L0–L5), exposed tools summary (safe, no raw schema dump), and skill policy where provided. Missing policy shows "not available", not fake data.

After S7-0906:
- Context level visible in trace event or detail
- Exposed tools summarized safely
- Skill policy visible where provided
- No raw full tool schema dump by default
- Missing data shows "not available" clearly

---

## Source Rules

- PRD-02-LLM-RUNTIME-001: Context levels and safety policies
- PRD-02-LLM-RUNTIME-002: Tool exposure policy and safe defaults

---

## Tests First

### Component Tests

```python
test_context_level_displays()  # PRD-02-LLM-RUNTIME-001
test_tool_summary_safe_display()  # PRD-02-LLM-RUNTIME-002
test_skill_policy_displays()  # PRD-02-LLM-RUNTIME-002
test_missing_policy_safe()  # PRD-02-LLM-RUNTIME-001
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/trace/ContextPolicyRow.jsx (new)
- tests/test_frontend_artifacts.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/context_policy.py (read-only)
- frontend_new_design_prototype/
```

---

## Stop Conditions

Stop if:

- Context level schema incomplete in trace
- Coverage below 95%

