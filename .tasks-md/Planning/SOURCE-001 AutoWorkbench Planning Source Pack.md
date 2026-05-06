# SOURCE-001 AutoWorkbench Planning Source Pack

**Type:** Source Pack  
**Status:** Planning  
**Priority:** P0  
**Owner:** Planning Brain  
**Applies To:** All AutoWorkbench Complete LLM Mode work  
**Implementation Ready:** Not applicable — this is planning/source material  

---

## 1. Purpose

This file is the root source pack for AutoWorkbench / Playwright Automation Co-pilot planning.

The board is not only a tracker. It is the shared implementation memory for:

- ChatGPT planning sessions
- Codex implementation workers
- four-developer branch split
- future handoff documents
- regression decisions
- source-of-truth architecture

Every story must be traceable to this source pack and must explain its contribution to the final product.

---

## 2. Final product goal

AutoWorkbench Complete LLM Mode should support this user journey:

```text
User describes what they want to automate/test
→ system gathers page/element/section context
→ system asks clarification if needed
→ LLM proposes plan only
→ backend stores active plan as runtime truth
→ frontend shows plan review
→ user corrects/confirms
→ backend validates confirmed execution contract
→ backend executes safe browser operations
→ backend records executed evidence
→ deterministic Playwright code is generated
→ trace explains what happened
→ replay/repair can be built on top of recorded truth
```

The user-facing result is:

```text
A QA/SDET can describe browser test intent in natural language and get safe, reviewable, replayable, code-generating Playwright automation.
```

---

## 3. Source hierarchy

Use this order when deciding architecture:

| Rank | Source | Role |
|---:|---|---|
| 1 | PRD v2.3 modular docs | Primary product/architecture source |
| 2 | Complete LLM Mode P0 / Architecture Spec | Complete LLM Mode scenario and runtime rules |
| 3 | Frontend/UI Spec | Shadow DOM and frontend rendering rules |
| 4 | LLM Runtime Policy Spec | LLM routing, skills, schema, token policy |
| 5 | Three-part handoff | Current implementation lessons and known traps |
| 6 | Hardened repo-local skills | Codex instruction packs |
| 7 | Current implementation code | Reality to inspect, not source of truth when conflicting |
| 8 | Fresh implementation judgment | Allowed only inside approved boundaries |

Conflict rule:

```text
PRD/spec/handoff wins over current implementation.
If two source docs conflict, stop and create a GAP item.
If code conflicts with source, story must name the migration path.
```

---

## 4. Non-negotiable architecture contract

### 4.1 LLM thinks and proposes

LLM may:

- classify user intent
- ask clarification
- propose plan
- propose structured correction diff
- suggest locator candidates
- diagnose failure
- suggest recovery
- summarize trace

LLM must not:

- decide runtime truth
- mutate active plan directly
- mark execution success
- mark step recorded
- emit final completion
- bypass backend validation
- own replay truth

### 4.2 Backend validates and owns truth

Backend owns:

- lifecycle state
- active plan identity/version
- plan mutation acceptance
- confirmed execution contract
- step identity
- operation identity
- locator validation truth
- action/assertion execution permission
- execution evidence
- recording truth
- code_update trigger
- replay operation truth
- failure/recovery/completion truth
- capability gap truth

Backend must be able to answer:

```text
What is the active run?
What plan/version is active?
Is user confirmation valid?
Which step and operation are expected next?
Is this LLM-proposed tool call allowed?
Can this operation be recorded?
Can the run complete now?
```

### 4.3 Frontend renders and collects input

Frontend may:

- render typed backend state
- collect user instructions/corrections/confirmations
- display plan, recorded steps, code, trace
- expose recovery/clarification controls

Frontend must not:

- infer lifecycle from LLM prose
- infer completion from local UI state
- mutate runtime truth directly
- simulate replay
- treat overlay/DOM flags as authoritative backend state

### 4.4 Event-driven contract is mandatory

Every important lifecycle change must become a typed backend event.

Event families:

```text
ready
run_started
plan_ready
clarification_needed
recovery_needed
step_validating
step_executing
step_recorded
step_failed
step_skipped
code_update
replay_started
replay_result
run_completed
session_state
capability_gap_recorded
```

Command families:

```text
run_steps / llm_run
confirmed
correction
option_selected
replay_step
replay_operation
replay_all
skip_step
stop_run
save_session
load_session
update_locator
```

### 4.5 Shadow DOM-first frontend

New frontend work targets Shadow DOM.

The current injected overlay is legacy/transitional only.

Do not grow new product architecture around legacy overlay assumptions.

### 4.6 Deterministic-first locator policy

Before LLM escalation, try deterministic evidence:

- role/name
- label
- placeholder
- alt/title
- data-testid
- scoped text
- stable id
- scoped CSS
- page/section context
- live validation count

LLM may suggest; backend validates.

### 4.7 Human clarification beats guessing

If target, scope, expected outcome, test data, locator, page state, permission, or capability support is unclear:

```text
do not guess
stop
ask user / emit clarification / record capability gap
```

---

## 5. Story contribution requirement

Every story must explain:

| Required question | Why it matters |
|---|---|
| What final product workflow does this support? | Prevents isolated engineering tasks |
| What product capability does this unlock? | Shows contribution to user value |
| What system layer owns it? | Prevents ownership drift |
| What other stories depend on it? | Enables four-developer parallel planning |
| What can run in parallel? | Avoids blocking all developers unnecessarily |
| What must not be touched? | Prevents broad rewrites |
| What tests prove it? | Makes TDD real |
| What evidence must be returned? | Makes review objective |

---

## 6. Universal stop condition

Stop if:

- required source evidence is missing
- source docs conflict
- current code conflicts and migration path is unclear
- tests cannot be written first
- story would require broad rewrite
- LLM/frontend would own backend truth
- unsupported capability would be guessed
- dependency/ownership is unclear

Report:

```text
files inspected
current behavior observed
source rule
conflict/gap
missing evidence
proposed narrow next step
```
