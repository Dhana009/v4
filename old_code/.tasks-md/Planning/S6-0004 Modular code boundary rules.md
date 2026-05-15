# S6-0004 Modular code boundary rules

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Architecture  

---

## Purpose

Define clear module boundaries to prevent `agent.py` and `server.py` from becoming monolithic. Ensure new features go into focused, testable modules.

---

## Source docs

- Current repo structure: `runtime/`, `recording/`, `locator/`, `llm/`, `event/`, `frontend/`, `tests/`
- Sprint 5 examples: `runtime/page_intelligence_schema.py`, `runtime/model_router.py`
- Agent orchestration: `agent.py` (9800+ lines)

---

## Current evidence

### Agent.py ownership drift

- `agent.py` handles: planning, correction, recovery, execution, recording, replay, codegen, telemetry, DOM extraction, locator, tool dispatch, state management
- Size: 9800+ lines (too large for single-pass code review)
- Risk: New features added directly to agent.py instead of focused modules

### Good module examples

- `runtime/skill_selector.py` — focused skill selection logic
- `runtime/model_router.py` — model routing decisions
- `recording/codegen.py` — code generation
- `locator/engine.py` — locator ranking

### Drift risk examples

- Page Intelligence: already built in `runtime/page_intelligence_schema.py` (correct)
- But if live invocation adds directly to `agent.py`, pattern breaks

---

## Desired behavior

Output: `.tasks-md/Planning/S6-MODULARIZATION-RULES.md`

### Rule 1: LLM Runtime Logic

```
✗ NOT: Add controller logic, policy enforcement, or context building directly to agent.py
✓ YES: Create runtime/llm_<feature>.py focused module

Examples:
  - Page Intelligence live trigger → runtime/page_intelligence_live.py
  - Journey Planner → runtime/journey_planner.py or runtime/multi_step_planner.py
  - New skill loading strategy → runtime/skill_policy.py (already exists)
  - New token attribution → runtime/token_report.py (already exists)

Ownership:
  - agent.py calls the module
  - Module owns the logic
  - Module is independently testable
  - Module is independently replaceable
```

### Rule 2: Recording/Codegen Logic

```
✗ NOT: Add recording state or codegen rules to agent.py
✓ YES: recording/recorder.py and recording/codegen.py own the logic

Examples:
  - Step finalization → recording/recorder.py
  - Code line generation → recording/codegen.py
  - Version save → recording/persistence.py (new module if needed)
  - Replay repair → recording/replay.py (already exists)

Ownership:
  - agent.py calls recording APIs
  - Recording modules own state and logic
```

### Rule 3: Locator Logic

```
✗ NOT: Add locator strategies or scoring directly to agent.py
✓ YES: locator/engine.py owns the logic

Examples:
  - Locator discovery → locator/engine.py (already exists)
  - Weak locator recovery → locator/weak_locator_recovery.py (new if needed)
  - Locator update → locator/locator_update.py (new if needed)

Ownership:
  - agent.py calls locator APIs
  - Locator modules own strategies
```

### Rule 4: Frontend Event/Command Handling

```
✗ NOT: Add UI state inference directly to agent.py
✓ YES: event/backend_event.py emits typed events; frontend reads them

Examples:
  - Plan review state → event/plan_ready_event.py logic (backend builds event; agent.py calls event builder)
  - Clarification needed → event/clarification_event.py
  - Recording finalized → event/recorded_step_event.py (already exists)

Ownership:
  - agent.py emits events
  - Event builders own payload structure
  - Frontend owns state interpretation
```

### Rule 5: Test File Placement

```
✗ NOT: Long monolithic test_agent_full_flow.py
✓ YES: Focused test_<module>_contract.py files

Examples:
  - Page Intelligence invocation → tests/test_page_intelligence_live_contract.py
  - Journey planning → tests/test_journey_planner_contract.py
  - Step finalization → tests/test_recording_step_finalization_contract.py

Ownership:
  - Each module has its own test file
  - Focused, fast test suite per module
  - No cross-cutting monolithic E2E test for everything
```

### Rule 6: agent.py and server.py Responsibility

```
agent.py owns:
  - Main planning/execution loop orchestration
  - Calling controllers, managers, event builders
  - Handling WebSocket commands
  - Phase progression
  - State transitions

agent.py DOES NOT own:
  - Business logic for skills, tools, policies, locators
  - Recording state or codegen rules
  - Frontend state interpretation
  - LLM routing or prompt building

server.py owns:
  - WebSocket server setup
  - Command routing
  - Session management
  - Persistence APIs (save/load)

server.py DOES NOT own:
  - Recording logic (call recording/ modules)
  - Planning logic (call runtime/ modules)
  - Frontend UI components
```

---

## Module creation checklist

When adding a new feature, ask:

1. Is this business logic (not orchestration)? → New module in `runtime/`, `recording/`, `locator/`, etc.
2. Does it have state or policy? → Separate module, not direct agent.py code
3. Is it testable in isolation? → Yes → Own module. No → Rethink.
4. Can it be replaced/disabled? → Yes → Own module. No → Should be infrastructure.

If all answers are yes → Create the module. agent.py calls it.

---

## Max responsibility per file

```
agent.py     → 10,000 lines max (orchestration only)
server.py    → 2,000 lines max (WebSocket + persistence)
runtime/llm_runtime_controller.py → 1,000 lines (one controller)
runtime/*.py → 500–1000 lines (focused feature/policy)
recording/*.py → 500–1000 lines (focused recording/codegen/replay)
locator/*.py → 500–1000 lines (focused locator logic)
tests/test_*.py → 500 lines per test file (focused contract/unit)
```

If a file exceeds its max, split it.

---

## Diagram: Module responsibility

```
┌─────────────────────────────────────┐
│        agent.py (orchestration)     │
└─────────────────────────────────────┘
            ↓ calls ↓
       ┌─────────────────────────────────────────┐
       │                                         │
    ┌──┴──────────┐  ┌──────────────┐  ┌─────────┴──┐
    │   runtime/  │  │  recording/  │  │  locator/  │
    │   (policy)  │  │  (state)     │  │  (logic)   │
    └─────────────┘  └──────────────┘  └────────────┘
       ↓ ↓ ↓            ↓ ↓ ↓            ↓ ↓ ↓
    (LLMRuntime)   (Codegen)        (Engine)
    (PromptPack)   (Recorder)       (Strategies)
    (SkillPolicy)  (Replay)         (Ranking)
    (ToolPolicy)   (Repair)         (Update)
    (ModelRouter)  (Persistence)    (Contract)
    etc.           etc.             etc.

    ↓ emits ↓
    
    event/ (typed backend events)
    
    ↓ sends ↓
    
    frontend/ (reads events, renders state)
```

---

## Out of scope

- No code refactoring yet.
- No moving existing code.
- No behavior changes.
- No product feature work.

---

## Allowed files

- `.tasks-md/Planning/S6-MODULARIZATION-RULES.md` (output)

---

## Forbidden files

- No changes to agent.py or server.py.
- No changes to runtime/recording/locator modules.
- No test changes.

---

## Acceptance criteria

- [ ] Clear rules for each module domain (LLM runtime, recording, locator, frontend, test)
- [ ] agent.py/server.py responsibility is defined (orchestration only)
- [ ] Module creation checklist is provided
- [ ] Max responsibility per file is specified
- [ ] Ownership diagram is clear
- [ ] Rules prevent monolith growth
- [ ] Document is stored in `.tasks-md/Planning/S6-MODULARIZATION-RULES.md`

---

## Validation

Spot-check existing modules:

```bash
# Count lines per file
wc -l agent.py  # Should be <10k
wc -l runtime/llm_runtime_controller.py  # Should be <1500
wc -l recording/codegen.py  # Should be <1000
```

---

## Stop conditions

- Cannot define clear module boundaries
- Existing modules already exceed max lines
- Rules conflict with current codebase structure
