# S7-0908 — Compact Agent Activity View

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Planning
**Blocks:** []
**Blocked by:** [S7-0500 (event store)]

---

## Objective

Show limited agent/runtime activity based on available telemetry/events. Display Main Orchestrator, Page Intelligence, Step Runner, Recovery/Debug (if available), Codegen Reviewer (if available). Show active/idle/unavailable labels. Missing backend agent events show "Not wired yet" or unavailable. No fake active agent in live mode.

After S7-0908:
- Agent Activity view renders from real telemetry/events
- Agent status clear (active/idle/unavailable)
- User can open trace details
- Cannot disable required agents without backend support
- No fake activity log in live mode

---

## Source Rules

- PRD-07-AGENT-001: Agent roles and lifecycle (limited in Sprint 7)
- PRD-07-AGENT-C9-002 (Cluster 9): Agent visibility limited to available telemetry; no overclaim

---

## Current Known Context

### What exists
- Backend agents exist but lifecycle events may be incomplete
- No frontend Agent Activity view

### What gaps exist
- Agent lifecycle events may not be fully wired
- No activity display component
- Unclear which agents should show in Sprint 7

---

## Tests First

### Component Tests

```python
test_agent_activity_view_renders()  # PRD-07-AGENT-001
test_agent_status_displays_active_idle_unavailable()  # PRD-07-AGENT-001
test_main_orchestrator_always_visible()  # PRD-07-AGENT-001
test_page_intelligence_visible_if_wired()  # PRD-07-AGENT-001
test_missing_agent_events_show_not_wired()  # PRD-07-AGENT-C9-002
test_can_open_trace_details()  # PRD-07-AGENT-001
```

### Negative Tests

```python
test_no_fake_agent_activity_in_live_mode()  # PRD-07-AGENT-C9-002
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/agents/AgentActivityView.jsx (new)
- frontend/src/components/agents/AgentStatusRow.jsx (new)
- tests/test_frontend_agents.py (new)
```

### Forbidden Files

```
- agent.py
- runtime/
- frontend_new_design_prototype/
```

---

## Implementation Notes

1. Show agent status based on available backend events
2. Display "Not wired yet" if backend events incomplete
3. Link to trace for full activity context
4. Do not show fake logs in live mode

---

## Stop Conditions

Stop if:

- Agent lifecycle events missing from backend
- Coverage below 95%

