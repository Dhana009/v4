# S7-0909 — Agent Control Center Placeholder / Limited Live View

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 3 (polish)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0908]

---

## Objective

Provide Agent Control Center surface that shows current live-supported agent info and disables unsupported toggles with reason. Page Intelligence "run now" disabled if backend command missing. Clear cache disabled if backend command missing. Future multi-agent controls documented as unavailable. No production fake controls.

After S7-0909:
- Agent Control Center displays
- Unsupported controls clearly disabled with reason
- Required agents cannot be disabled
- Placeholder text accurately says backend not wired
- No static fake agent logs
- No command sent for unsupported toggle

---

## Source Rules

- PRD-07-AGENT-CONTROL-001: Agent control surface (limited in Sprint 7)
- PRD-07-AGENT-C9-002: Limited view; placeholder for missing backend

---

## Current Known Context

### What exists
- Backend agents and policies exist
- No Agent Control Center frontend component
- Multi-agent orchestration backend may not be wired

### What gaps exist
- No Agent Control Center UI
- Unclear which controls are supported in Sprint 7
- Backend command handlers may be missing

---

## Tests First

### Component Tests

```python
test_agent_control_center_renders()  # PRD-07-AGENT-CONTROL-001
test_unsupported_control_disabled_with_reason()  # PRD-07-AGENT-C9-002
test_page_intelligence_run_now_disabled_if_no_backend()  # PRD-07-AGENT-CONTROL-001
test_required_agents_cannot_disable()  # PRD-07-AGENT-CONTROL-001
test_placeholder_text_accurate()  # PRD-07-AGENT-C9-002
```

### Negative Tests

```python
test_no_fake_agent_controls()  # PRD-07-AGENT-C9-002
test_unsupported_command_not_sent()  # PRD-07-AGENT-C9-002
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/agents/AgentControlCenter.jsx (new)
- frontend/src/commands/agentCommands.js (new — optional; may be empty)
- tests/test_frontend_agents.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Create Agent Control Center surface
2. List required agents (cannot be disabled)
3. Show supported optional controls
4. Disable unsupported controls with reason
5. Document future features clearly
6. Do not send commands for disabled controls

---

## Stop Conditions

Stop if:

- Backend agent command handlers missing (mark as disabled)
- Coverage below 95%

