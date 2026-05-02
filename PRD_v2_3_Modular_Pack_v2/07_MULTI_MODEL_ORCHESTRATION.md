# 07 — Multi-Model Orchestration

> PRD v2.3 addendum. This document defines the optional/stabilized multi-model architecture for LLM Mode. It does not replace the Step Runner, Tool Runtime, Context Manager, or existing LLM Runtime. It clarifies how multiple model-backed agents can cooperate without creating chaos.

## 1. Why this document exists

The LLM layer is the core product brain, but one model should not perform every task directly:

```text
raw DOM reading
page understanding
locator candidate generation
failure diagnosis
high-level planning
code generation review
risk checking
user-facing explanation
```

These tasks have different cost, latency, and reasoning requirements. Sending raw DOM, full history, and every skill to the main reasoning model is expensive and can reduce quality by flooding the model with irrelevant context.

The multi-model architecture exists to preserve quality while controlling cost:

```text
cheap/nano models prepare structured page intelligence
main model reasons and orchestrates
debug model analyzes failures
codegen reviewer checks generated code when needed
Step Runner remains the source of truth
```

## 2. Non-negotiable principles

| Principle | Meaning |
|---|---|
| Step Runner owns truth | No agent decides that a step is complete. Only validated runtime state does. |
| Agents suggest, runtime proves | Model outputs are proposals. Locators/actions are always validated live. |
| Main Orchestrator owns intent | Sub-agents do not silently change user intent. |
| Frontend must show activity | When an agent runs, UI must show which agent, why it ran, and what it produced. |
| Cost must be visible | Every model call logs model, purpose, input/output tokens, estimated cost, and latency. |
| Agents are optional/configurable | User can turn non-essential agents on/off from UI. |
| Deterministic first when reliable | Do not call a model if a deterministic rule can safely solve the task. |
| Quality before token savings | Token optimization must never remove context required for correctness. |

## 3. Agent map

### 3.1 Main Orchestrator Agent

**Purpose:** Understand user intent, plan execution, coordinate sub-agents, and decide when user input is needed.

**Recommended model:** Stronger reasoning model, configurable by user.

**In scope:**

```text
- interpret natural-language test intent
- decompose user steps into child operations
- decide execution order
- request page intelligence when needed
- request debug analysis when failure happens
- request code review when code is complex/high risk
- ask one precise clarification question when needed
- preserve user intent during recovery
- approve or reject sub-agent suggestions
```

**Out of scope:**

```text
- execute browser actions directly
- decide final step completion
- record steps directly
- generate final TypeScript as the only source of truth
- mutate frontend state directly
- ignore Step Runner validation results
```

**Activated when:**

```text
- user runs LLM Mode
- user corrects a plan
- user provides recovery guidance
- sub-agent output needs interpretation
- Step Runner reports unresolved work
```

**Expected output:** structured plan, clarification request, recovery instruction, or tool strategy. Never raw uncontrolled prose as the source of runtime truth.

---

### 3.2 Page Intelligence / Locator Agent

**Purpose:** Cheap/nano model that understands page structure, poor DOM, section context, and locator candidates.

**Recommended model:** Nano/low-cost extraction model.

**Core reason:** Pages may have no good semantics. They may be built entirely from `div` and `span`, with generated classes and no `role`, `aria-label`, `id`, or `data-testid`. The system must still produce the best possible strategy.

**In scope:**

```text
- summarize selected section/page structure
- classify div/span elements into likely semantic roles
- infer element purpose from visible text, layout, behavior, and nearby context
- build page map candidates
- propose locator candidates with confidence/risk
- explain why each locator candidate is stable or fragile
- identify weak semantic areas
- produce compact context for Main Orchestrator
```

**Out of scope:**

```text
- execute Playwright actions
- record steps
- decide final locator truth
- ask the user directly
- change step order
- make destructive/action decisions
```

**Inputs:**

```text
- selected element descriptor
- selected section cleaned DOM
- accessibility snapshot when available
- visible text map
- bounding boxes
- computed visibility/clickability hints
- nearby labels/sibling/parent context
- current URL/title
- existing page map and locator library
```

**Output schema:**

```json
{
  "page_or_section_summary": "string",
  "semantic_quality": "good | mixed | poor",
  "elements": [
    {
      "semantic_name": "Submit button",
      "element_type_guess": "button-like div",
      "section": "login form",
      "visible_text": "Submit",
      "signals_used": ["visible_text", "nearby_password_field", "cursor_pointer", "form_footer_position"],
      "locator_candidates": [
        {
          "locator": "get_by_text('Submit', exact=True)",
          "scope": "login form section",
          "confidence": 0.72,
          "risk": "medium",
          "reason": "Text is unique inside selected form; no semantic attributes exist."
        }
      ],
      "recommendation": "validate_candidates_live"
    }
  ],
  "questions_for_orchestrator": [],
  "capability_gaps": []
}
```

**Expected criteria:**

- On a page built mostly from `div`/`span`, it still produces meaningful element identities and locator candidates.
- It never claims a locator is final; it marks candidates as needing live validation.
- It returns structured JSON, not free-form advice.
- It includes risk and reasoning for fragile candidates.
- It helps the main model avoid receiving raw full DOM in normal flows.

---

### 3.3 Debug Agent

**Purpose:** Diagnose failures and propose recovery strategy.

**Recommended model:** Stronger than nano when needed. Can be the main model initially, then split later.

**In scope:**

```text
- analyze action/assertion/locator failures
- compare original intent vs current browser state
- detect navigation mismatch
- detect stale DOM/locator issues
- analyze replay failures
- propose recovery steps
- decide whether human input is needed
- produce concise user-facing diagnosis
```

**Out of scope:**

```text
- execute recovery actions directly
- record fixed steps
- silently change user intent
- loop indefinitely
- ask broad questions like "what should I do?"
```

**Activated when:**

```text
- deterministic recovery fails
- action/assertion fails
- locator candidate count is 0 or >1 after retries
- replay step fails
- browser state differs from expected state
- user explicitly asks to debug/fix
```

**Output schema:**

```json
{
  "root_cause": "click navigated before old-page assertion",
  "failed_step_id": "step_2",
  "original_intent": "assert homepage Playwright heading",
  "current_state": {
    "url": "https://playwright.dev/docs/intro",
    "title": "Installation"
  },
  "recommended_recovery": [
    {"action": "page_go_back"},
    {"action": "assert", "target": "homepage heading"},
    {"action": "click", "target": "Get started"}
  ],
  "requires_user": false,
  "user_question": null,
  "confidence": 0.84
}
```

**Expected criteria:**

- It stays anchored to the original failed step.
- It explains what failed, why, and what will be tried next.
- It escalates to the user only with one precise question.
- It never allows finalization while failure remains unresolved.

---

### 3.4 Codegen Reviewer Agent

**Purpose:** Review generated Playwright TypeScript when deterministic codegen needs quality checking.

**Important decision:** Code generation is deterministic-first. The Codegen Reviewer Agent does not own final code generation.

**In scope:**

```text
- review generated TypeScript for readability and correctness
- detect invalid locator conversion
- suggest better comments for fragile locators
- review complex flows: popup, download, iframe, auth, network
- check that generated code reflects recorded child operations
```

**Out of scope:**

```text
- invent steps not recorded
- replace backend codegen as source of truth
- change runtime behavior
- execute tests directly
```

**Activated when:**

```text
- user exports final spec
- code_update contains complex operation type
- fragile locator is used
- locator update modifies generated code
- replay repair changes a recorded step
- user explicitly asks for code review
```

**Expected criteria:**

- Deterministic codegen remains primary.
- Reviewer catches Python-style locator strings or invalid Playwright TypeScript.
- Reviewer can suggest improvements, but backend codegen applies approved deterministic transformations.

---

### 3.5 Judge / Risk Agent — optional later

**Purpose:** Review high-risk actions and complex plans.

**Activated when:**

```text
- destructive action detected: delete, remove, publish, send email, submit payment
- external-impact action detected
- plan has low confidence
- recovery may change user intent
- model disagreement exists between agents
```

**Out of scope for MVP:** Not required for initial LLM Mode MVP.

**Expected criteria when added:**

- High-risk actions require explicit confirmation.
- Judge Agent never executes actions.
- Judge Agent can block or request confirmation, but Step Runner still owns truth.

## 4. Trigger matrix

| Scenario | Page Intelligence / Locator | Debug | Codegen Reviewer | Judge/Risk |
|---|---:|---:|---:|---:|
| Single element with strong data-testid | No | No | No | No |
| Single element with weak/no semantics | Yes | No unless failure | No | No |
| Selected section with multiple goals | Yes | No unless failure | Maybe after code_update | No |
| Full-page exploration | Yes | No unless failure | Maybe | No |
| Locator count = 0 or >1 | Yes | Maybe | No | No |
| Action/assertion failure | Maybe | Yes | No | No |
| Replay failure | Yes | Yes | Maybe after fix | Maybe if risky |
| Locator update requested | Yes | No unless failed | Yes after code update | No |
| Download/upload/popup/iframe complex code | Maybe | Maybe | Yes | No |
| Destructive action | Maybe | No | No | Yes |
| User turns off Page Intelligence Agent | No, unless required and user confirms | No | No | No |

## 5. When the nano model runs

### 5.1 Default: lazy/on-demand

Nano model does not run blindly on every page load. It runs when the system needs page intelligence.

Triggers:

```text
- user selects a section/container
- user asks page-level or broad intent
- DOM semantic quality is poor
- locator confidence is below threshold
- deterministic locator waterfall fails
- replay failure needs current page understanding
- context compaction is needed after large tool outputs
```

### 5.2 Optional: idle background preparation

When enabled in UI:

```text
page navigation completes
→ wait for page idle/stable DOM
→ if page map missing/stale and LLM Mode active
→ run cheap page intelligence in background
```

Rules:

```text
- must not block user actions
- must be cancellable
- must be rate-limited per page URL/DOM version
- must stop if user disables the agent
- must reuse cached page intelligence when fresh
```

### 5.3 Debug/replay trigger

When failure happens:

```text
failure captured
→ deterministic failure context built
→ nano model may summarize current page difference
→ Debug Agent receives compact failure context
```

### 5.4 When nano must not run

```text
- every tiny click
- every assertion
- every page load when user is only browsing
- if strong validated locator exists
- if fresh page map exists
- if deterministic extraction is enough
- if user disabled Page Intelligence Agent
```

## 6. Bad DOM strategy

The system must not depend on good frontend semantics.

For `div`/`span` heavy pages, collect multiple signals:

```text
visible text
nearby text
parent/sibling context
bounding box and visual position
computed style hints such as cursor:pointer
clickability/tabindex
href/onClick-like behavior when safely detectable
form/table/card section context
screenshot/vision fallback when needed
```

Locator preference for poor DOM:

```text
1. scoped text/context locator inside selected section
2. relational locator based on nearby labels/headings
3. role/behavior inferred candidate, if validation proves it
4. stable attribute if any exists
5. relative XPath only as last resort
6. coordinate or JS expression only with explicit fragile warning
```

Expected criteria:

- Poor DOM does not immediately block automation.
- System produces best-available candidate and clearly marks risk.
- User sees fragile warning if locator quality is low.
- Locator update flow can replace weak locator later.

## 7. Agent UI controls

The frontend must expose agent visibility and controls.

### Agent Control Center

UI should include a compact agent/status panel:

```text
Agents
[ON] Page Intelligence / Locator Agent   idle / running / disabled
[ON] Debug Agent                         idle / running / waiting
[ON] Codegen Reviewer                    idle / running / disabled
[OFF] Judge Agent                         optional later
Main Orchestrator                         required in LLM Mode
Step Runner                               system runtime, cannot disable
```

### Controls

| Control | Behavior |
|---|---|
| Toggle Page Intelligence Agent | Enables/disables nano page intelligence. If disabled, system falls back to deterministic extraction + main model. |
| Toggle Debug Agent | Enables/disables specialist debug model. If disabled, main model handles recovery. |
| Toggle Codegen Reviewer | Enables/disables model-based code review. Deterministic codegen still runs. |
| Run Page Intelligence Now | Manually builds/refreshes page intelligence for current page/section. |
| Clear Page Intelligence Cache | Clears cached page map/intelligence for current URL. |
| Show Agent Trace | Shows recent agent calls, token/cost/latency, purpose, and summary. |

### Visibility rules

When any agent runs, UI must show:

```text
- agent name
- why it was triggered
- what input it received at a summary level
- status: queued/running/done/failed/cancelled
- output summary
- confidence/risk if applicable
- token/cost/latency if available
```

Expected criteria:

- User can tell which agent is working and why.
- User can disable optional agents without breaking core runtime.
- Main Orchestrator and Step Runner cannot be disabled in active LLM Mode.
- Agent traces do not expose secrets or full raw DOM by default.

## 8. Backend event contract additions

Multi-model orchestration adds events and commands to the backend/frontend contract.

### Frontend → Backend commands

```json
{ "type": "set_agent_enabled", "agent": "page_intelligence", "enabled": true }
{ "type": "run_page_intelligence", "scope": "current_page | selected_section" }
{ "type": "clear_page_intelligence_cache", "url": "current" }
{ "type": "get_agent_trace", "run_id": "..." }
```

### Backend → Frontend events

```json
{ "type": "agent_started", "agent": "page_intelligence", "reason": "selected_section_multi_action" }
{ "type": "agent_progress", "agent": "page_intelligence", "stage": "summarizing_dom" }
{ "type": "agent_result", "agent": "page_intelligence", "summary": "3 sections, 8 actions, 12 candidates" }
{ "type": "agent_failed", "agent": "debug", "error": "model_timeout" }
{ "type": "agent_trace", "items": [] }
```

Expected criteria:

- UI does not infer agent activity from logs.
- Every agent activity has typed start/result/failure events.
- Agent toggles persist for the active session.

## 9. Model routing policy

The Model Router decides which model to call.

Inputs:

```text
agent role
task type
risk level
context size
user settings
available models
budget limits
latency target
```

Rules:

```text
- Use nano model for page intelligence, locator candidate generation, and compaction.
- Use main model for planning, ambiguity, and high-level recovery.
- Use debug model only after failure or explicit debug request.
- Use codegen reviewer only for complex/high-risk code or final export.
- Escalate to stronger model if cheap model confidence is low.
- Never run multiple expensive agents in parallel unless explicitly needed.
```

Expected criteria:

- Every model call has a declared purpose.
- Model choice is logged.
- If an optional model is unavailable, system degrades gracefully.
- User can configure provider/model per role later.

## 10. Scenario behavior

### Scenario A — Good semantic button

```text
User: click this Login button
DOM: button role/name or data-testid exists
```

Expected:

```text
- deterministic locator finds candidate
- nano agent not called
- main orchestrator confirms plan
- Step Runner validates and executes
```

### Scenario B — Div/span button with no semantics

```text
User picks div that visually acts as Submit
DOM has no role/id/data-testid/stable class
```

Expected:

```text
- extractor collects text, box, nearby form context, clickability hints
- Page Intelligence Agent classifies it as button-like div
- candidates are generated with risk labels
- Step Runner validates candidates
- if only fragile fallback works, UI shows fragile warning
```

### Scenario C — Section with multiple goals

```text
User selects entire card/form/section and says: validate important text and click submit
```

Expected:

```text
- Page Intelligence Agent summarizes section
- Main Orchestrator decomposes into child operations
- UI shows parent plan with child operations
- Step Runner executes and records parent + children
```

### Scenario D — Replay fails because app changed

Expected:

```text
- replay_result failed
- Page Intelligence Agent compares current page signals/page map
- Debug Agent diagnoses changed locator/page state
- Main Orchestrator proposes fix
- user confirms if needed
- repaired locator/step is validated and versioned
```

### Scenario E — User disables Page Intelligence Agent

Expected:

```text
- system uses deterministic extraction and main model only
- if quality is low, UI warns that Page Intelligence is disabled
- user may re-enable or continue with fragile fallback
```

### Scenario F — Code export for complex flow

Expected:

```text
- deterministic codegen creates code
- Codegen Reviewer checks only if complexity/risk threshold met
- backend applies approved deterministic fixes
- user sees code_update and any warnings
```

## 11. Cost and latency expectations

Expected criteria:

- Nano/page intelligence calls reduce main-model raw DOM usage in complex flows.
- Background intelligence never blocks immediate user action.
- Agent calls are cached by URL, DOM version, and selected-section hash when possible.
- System logs model, tokens, cost, latency, and reason for every call.
- If token/cost budget is exceeded, system compacts context or asks user before expensive full-DOM fallback.

## 12. Implementation priority

Do not build all agents first.

Recommended order:

```text
1. Token/cost telemetry for all model calls
2. Deterministic extractor and context manager cleanup
3. Page Intelligence / Locator Agent using nano model
4. Agent Control Center UI visibility/toggles
5. Debug Agent specialization
6. Codegen Reviewer Agent
7. Optional Judge/Risk Agent
```

Expected criteria before calling this architecture complete:

```text
- optional agents can be toggled
- nano agent produces structured page intelligence
- main model receives compact page intelligence, not raw full DOM, in eligible flows
- Step Runner validates all locator/action truth
- debug agent handles failure without changing original intent
- codegen reviewer does not replace deterministic codegen
- UI shows agent activity clearly
```
