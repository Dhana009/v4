# AutoWorkbench Complete LLM Mode — LLM Runtime Policy Spec

## 1. Purpose

This document defines how AutoWorkbench should call LLMs in Complete LLM Mode.

The goal is to prevent the system from becoming one broad `main_orchestrator` loop that loads too much context, too many skills, too many tools, and makes too many calls.

The LLM layer must be:

```text
purpose-specific
token-controlled
skill-controlled
tool-controlled
schema-bound
backend-validated
observable
```

Core rule:

```text
User can speak freely.
Backend classifies and controls.
LLM thinks within a bounded purpose.
Backend validates and decides.
```

---

## 2. Core LLM architecture decision

All LLM calls must go through the LLM Runtime Controller.

No runtime subsystem should make ad-hoc LLM calls directly.

Subsystems that must route through the controller:

```text
planning
page intelligence
steps mode
plan correction
locator repair
custom assertion planning
execution assistance
recovery/debugging
replay repair
user-facing explanation
```

---

## 3. LLM Runtime Controller

The LLM Runtime Controller is the backend control plane for LLM usage.

For every possible LLM call, it decides:

```text
whether an LLM call is needed
LLM purpose
model class
persona/system prompt
skills to load
context level
context payload
tools exposed
token budget
output schema
retry policy
escalation policy
backend validator
trace/telemetry fields
```

Runtime flow:

```text
user input / backend event / failure
→ classify situation
→ select LLM policy
→ check if deterministic path is enough
→ build minimal context
→ load only required skills
→ expose only allowed tools
→ call selected model
→ validate output schema
→ backend validates semantic/runtime correctness
→ emit typed event
→ update trace/telemetry
```

---

## 4. Deterministic-first rule

The LLM should not be called if deterministic backend logic can complete the task reliably.

Deterministic-first applies to:

```text
locator generation
locator validation
page-state checks
permission checks
step dependency checks
recording
code_update
replay precondition checks
simple error classification
simple command parsing
```

Examples:

```text
If a locator candidate is generated and validates with count == 1, do not call LLM.
If a step precondition fails because current URL is wrong, emit precondition_failed; do not call LLM.
If required test data is missing, ask user directly; do not let LLM invent it.
```

---

## 5. LLM purpose taxonomy

Every LLM call must have one explicit purpose.

Allowed purposes:

```text
intent_classifier
clarification_generator
page_intelligence_summarizer
page_validation_recommender
journey_planner
step_plan_normalizer
plan_diff_editor
locator_specialist
custom_assertion_planner
execution_driver
recovery_diagnoser
replay_repair_specialist
user_response_writer
trace_summarizer
```

If a new purpose is needed, it must define:

```text
persona
model class
context policy
skill policy
tool policy
schema
budget
validator
fallback
```

---

## 6. Model routing policy

Use models by responsibility, not by convenience.

### 6.1 Cheap/small model

Use for:

```text
intent classification
simple clarification drafting
page/DOM summarization
candidate grouping
trace compression
failure summary
low-risk structure extraction
```

Cheap model must not make final runtime decisions.

### 6.2 Main model

Use for:

```text
full journey planning
page validation recommendation
ambiguous plan correction
custom assertion design
complex locator reasoning
complex recovery reasoning
user-facing explanation when nuance matters
```

### 6.3 No model

Use deterministic backend only for:

```text
locator candidate generation when reliable
locator validation
execution contract validation
permission checks
precondition checks
recording
code_update
replay execution
simple state transitions
```

---

## 7. Persona/system prompt policy

System prompts should be compact and purpose-specific.

Do not use one large universal persona for every call.

### 7.1 Common compact core

Every LLM call may receive a compact core rule block:

```text
You are part of AutoWorkbench, a Playwright automation co-pilot.
LLM proposes; backend validates and owns truth.
Return only the required schema.
Do not claim execution success.
Ask for clarification if required data is missing.
Do not invent locators, data, pages, or capabilities.
Use minimal assumptions.
```

This core must stay short.

### 7.2 Purpose-specific personas

Examples:

```text
intent_classifier: classify user intent into allowed enums only.
clarification_generator: ask one focused question to remove ambiguity.
page_validation_recommender: act as a QA test strategist.
journey_planner: act as a senior QA automation flow planner.
step_plan_normalizer: convert focused user steps into executable plan structure.
plan_diff_editor: produce structured diffs only.
locator_specialist: propose robust Playwright locator strategy.
custom_assertion_planner: design supported Playwright assertion logic.
recovery_diagnoser: diagnose failure and propose bounded repair.
execution_driver: emit only the next allowed operation, if needed.
```

### 7.3 User-loaded persona boundaries

User may choose or add a testing persona, such as:

```text
strict regression tester
smoke test planner
accessibility-focused tester
lead-magnet flow tester
CRM validation tester
```

User persona may influence:

```text
recommendation style
assertion priority
strictness
coverage preference
explanation tone
```

User persona must not override:

```text
backend truth
execution contract
tool permissions
schema requirements
safety rules
permission policy
token budgets
capability limits
```

---

## 8. Skill loading policy

Skills are external task knowledge loaded only when relevant.

### 8.1 Skill levels

```text
none
core_compact
skill_summary
full_skill
debug_skill
capability_skill
```

### 8.2 Loading rules

```text
intent_classifier → none or tiny core only
clarification_generator → core_compact only
page_validation_recommender → assertions_summary + locator_summary
journey_planner → planning_summary + actions_summary + assertions_summary + test_data_summary
step_plan_normalizer → actions_summary + assertions_summary, locator_summary only if needed
plan_diff_editor → correction_diff_skill only
locator_specialist → locator_skill, full only if compact insufficient
custom_assertion_planner → assertions_skill + relevant data/table/timer skill
execution_driver → minimal execution rules only
recovery_diagnoser → debug_skill + relevant capability skill only
replay_repair_specialist → replay_repair_skill + locator/assertion skill as needed
```

### 8.3 Full skill escalation

Full skill is allowed only when:

```text
compact skill is insufficient
failure type specifically requires it
custom capability reasoning is required
token budget allows it
controller logs escalation reason
```

---

## 9. Context policy

Every LLM call must declare a context level.

### 9.1 Context levels

```text
L0: user message + UI/backend state summary
L1: selected element descriptor
L2: selected section summary
L3: page intelligence summary
L4: focused debug/locator packet
L5: capped raw DOM/full snapshot fallback
```

### 9.2 Context rules

```text
Start with the smallest sufficient context.
Escalate only when a sufficiency gate fails.
Escalate one level at a time where practical.
Never send full raw DOM by default.
Never send secrets/raw credentials by default.
Never send full conversation history by default.
Always log context level and escalation reason.
```

### 9.3 What should not be sent by default

```text
full raw DOM
full chat history
all tool results
secrets/credentials/OTP
full uploaded file contents
irrelevant previous plans
terminal logs
large screenshots as text
unbounded trace logs
```

---

## 10. Context sufficiency gates

Backend decides context sufficiency using gates.

LLM may request more context, but backend approves or rejects the request.

### 10.1 General gate fields

```text
user goal clear?
target scope known?
required data available?
page state known?
locator candidates available?
ambiguities listed?
capability supported?
token budget available?
```

### 10.2 Page recommendation gate

Requires:

```text
page summary exists
sections detected
headings/CTAs/forms extracted
semantic quality score/risk available
important ambiguities listed
candidate locator summary available
```

If missing:

```text
run page intelligence
or ask user to scope request
or escalate context
```

### 10.3 Journey planning gate

Requires:

```text
start page known
user goal clear
required test data known or marked missing
permission needs identified
current page summary available
capability gaps known
end validation goal known or clarification pending
```

### 10.4 Steps planning gate

Requires:

```text
pending steps available
stable step ids
step order available
element/section info available where needed
expected outcome/postcondition available or marked unsure
locator status available
page-state/dependency warnings available
```

### 10.5 Locator specialist gate

Requires:

```text
current locator
validation count/status
candidate locators tried
nearby ancestor/section summary
failure/ambiguity reason
user preference if provided
page state compatibility known
```

### 10.6 Recovery gate

Requires:

```text
failed operation
failure classification
expected vs actual
what deterministic recovery already tried
current page state
focused locator/page evidence
artifact refs if available
```

---

## 11. Page Intelligence policy

Page Intelligence prepares compact page/section context before Main LLM sees it.

### 11.1 Deterministic extraction first

Backend should extract programmatically where possible:

```text
URL/title
landmarks
headings
sections
buttons/links
forms/inputs
labels/placeholders
tables/lists
visible text snippets
candidate locators
semantic quality
risk flags
duplicate text/ambiguous targets
```

### 11.2 Cheap model summarization

Cheap model may be used to compress or classify complex DOM into:

```text
page_summary
section summaries
important actions
recommended scopes
semantic quality notes
ambiguity notes
candidate locator groups
```

### 11.3 Page Intelligence output contract

```text
page_id
url
title
summary
sections[]
forms[]
ctas[]
tables[]
modals_or_dynamic_ui[]
important_text_blocks[]
candidate_locator_groups[]
semantic_quality
ambiguities[]
risk_flags[]
token_estimate
source: deterministic | cheap_model | mixed
```

Main LLM should receive this output, not raw DOM by default.

---

## 12. Tool policy

Tools are exposed based on LLM purpose and backend phase.

LLM never directly owns browser control.

### 12.1 Tool groups

```text
inspection_tools:
  browser_get_state
  page_summary_get
  element_context_get
  section_context_get

locator_tools:
  locator_candidates_get
  locator_find
  locator_validate

safe_browser_tools:
  scroll_into_view
  hover
  focus

action_tools:
  click
  fill
  press
  select_option
  upload_file

navigation_tools:
  go_back
  go_forward
  reload
  navigate_to_url

diagnostic_tools:
  screenshot_take
  console_errors_get
  trace_get

replay_tools:
  replay_one
  replay_all
```

### 12.2 Tool exposure matrix

```text
intent_classifier → no tools
clarification_generator → no tools
page_intelligence_summarizer → inspection tools only
page_validation_recommender → page summary only, no browser-changing tools
journey_planner → page summary only, no execution tools
step_plan_normalizer → locator status/context only, no browser-changing tools
plan_diff_editor → no browser tools
locator_specialist → locator tools + element/section context only
custom_assertion_planner → inspection/context tools only
execution_driver → only next confirmed operation tool
recovery_diagnoser → diagnostic tools + focused repair tools only
replay_repair_specialist → replay evidence + locator/assertion tools only
user_response_writer → no tools
```

### 12.3 Tool call validation

Every tool call is validated by backend:

```text
purpose allowed?
phase allowed?
tool allowed by policy?
precondition satisfied?
permission granted?
confirmed execution contract matched?
step/operation id matched?
```

If not:

```text
tool_call_blocked
```

---

## 13. Purpose policy matrix

### 13.1 intent_classifier

```text
Model: cheap
Persona: strict classifier
Context: L0
Skills: none or tiny core
Tools: none
Output schema: intent category, confidence, missing_fields, target_scope
Backend validation: enum only
Fallback: ask clarification
Token budget: very small
```

### 13.2 clarification_generator

```text
Model: cheap/main depending ambiguity
Persona: scope clarifier
Context: missing fields + user request
Skills: core_compact
Tools: none
Output schema: one focused question + options
Backend validation: question maps to missing field
Fallback: deterministic clarification template
Token budget: small
```

### 13.3 page_intelligence_summarizer

```text
Model: cheap
Persona: DOM/page summarizer
Context: deterministic page extraction, capped DOM snippets if needed
Skills: page_summary skill
Tools: inspection only
Output schema: page intelligence contract
Backend validation: required fields present
Fallback: deterministic summary only or ask user to scope
Token budget: medium, capped
```

### 13.4 page_validation_recommender

```text
Model: main
Persona: QA test strategist
Context: L3 page intelligence summary + user scope
Skills: assertion_summary + locator_summary
Tools: no browser-changing tools
Output schema: grouped validation recommendations
Backend validation: maps to supported assertion/capability categories
Fallback: ask user to narrow scope
Token budget: medium
```

### 13.5 journey_planner

```text
Model: main
Persona: senior QA automation flow planner
Context: goal + data availability + page summary + capability/risk info
Skills: planning_summary + actions_summary + assertions_summary + test_data_summary
Tools: no execution tools
Output schema: draft plan with steps, preconditions, postconditions, risk, required data
Backend validation: plan schema, dependencies, capabilities, missing data
Fallback: clarification_needed or capability_gap
Token budget: medium/high with cap
```

### 13.6 step_plan_normalizer

```text
Model: main or cheap depending complexity
Persona: strict step planner
Context: pending steps + element/section info + locator status + postconditions
Skills: action/assertion summaries; locator summary only if needed
Tools: no browser-changing tools
Output schema: plan_ready or clarification_needed
Backend validation: step ids preserved, no silent drops, dependencies valid
Fallback: ask clarification
Token budget: small/medium
```

### 13.7 plan_diff_editor

```text
Model: main or cheap depending edit complexity
Persona: structured plan editor
Context: active plan version + user edit instruction + allowed mutations
Skills: correction_diff_skill
Tools: none
Output schema: plan_diff only
Backend validation: diff validity, no silent drop, dependency impact
Fallback: one schema retry, then fail closed/ask user
Token budget: small
```

### 13.8 locator_specialist

```text
Model: main for ambiguous/semantic cases; cheap for simple grouping
Persona: Playwright locator expert
Context: L4 focused locator packet
Skills: locator skill summary/full as needed
Tools: locator/context tools only
Output schema: locator alternatives + strategy + fragility notes
Backend validation: every locator validates live or against approved snapshot
Fallback: ask user to choose candidate or mark fragile
Token budget: small/medium
```

### 13.9 custom_assertion_planner

```text
Model: main
Persona: Playwright assertion designer
Context: target scope + user logic + extracted values + supported assertion capabilities
Skills: assertion skill + relevant capability/data skill
Tools: inspection/context tools only
Output schema: structured assertion plan
Backend validation: supported capability, expected values, locators, wait strategy
Fallback: ask user for expected value or capability_gap
Token budget: medium
```

### 13.10 execution_driver

```text
Model: cheap/main only if backend cannot execute deterministically
Persona: next-operation executor
Context: current confirmed operation only + current page state
Skills: minimal execution rules
Tools: only next allowed operation tool
Output schema: one tool call or safe failure
Backend validation: execution contract strict
Fallback: recovery_needed
Token budget: small
```

### 13.11 recovery_diagnoser

```text
Model: main for complex failure; cheap for summary/compression
Persona: debugging specialist
Context: L4 focused failure packet
Skills: debugging skill + relevant capability skill only
Tools: diagnostic + focused repair tools only
Output schema: repair proposal | ask_user | capability_gap | stop
Backend validation: repair validates before execution
Fallback: ask user or fail safely
Token budget: medium with escalation cap
```

### 13.12 replay_repair_specialist

```text
Model: main if repair requires reasoning
Persona: replay repair specialist
Context: recorded operation + replay failure + current candidates + stored snapshot summary
Skills: replay_repair + locator/assertion skill as needed
Tools: replay evidence + locator tools only
Output schema: repair diff
Backend validation: repaired step validates, versioned update only
Fallback: user choice or capability_gap
Token budget: small/medium
```

### 13.13 user_response_writer

```text
Model: cheap/main depending complexity
Persona: concise product assistant
Context: backend decision/result summary only
Skills: none or core compact
Tools: none
Output schema: user-facing message
Backend validation: must not claim unsupported success
Fallback: deterministic template
Token budget: very small
```

---

## 14. Token budget policy

Every call must log estimated and actual token usage where available.

Fields:

```text
call_id
purpose
model
context_level
skill_tokens
tool_tokens
message_tokens
estimated_input_tokens
actual_input_tokens
output_tokens
total_tokens
latency_ms
```

### Budget guidance

```text
intent_classifier: very small
clarification_generator: small
plan_diff_editor: small
locator_specialist: small/medium
step_plan_normalizer: small/medium
page_validation_recommender: medium
journey_planner: medium/high capped
custom_assertion_planner: medium
recovery_diagnoser: medium capped
```

### Budget enforcement

If budget would be exceeded:

```text
compact context
load summary skill instead of full skill
drop irrelevant history
ask clarification instead of exploring
use cheaper summarizer first
reject full DOM escalation unless justified
```

---

## 15. Output schema and retry policy

Every LLM purpose must have a schema.

If schema fails:

```text
retry once with schema reminder
if still invalid, fail closed or ask user
never silently continue with prose
```

Examples:

```text
plan_diff_editor must return plan_diff
locator_specialist must return locator alternatives
recovery_diagnoser must return repair_proposal | ask_user | capability_gap | stop
```

---

## 16. Backend validation after LLM

LLM output is never directly trusted.

Backend validates:

```text
schema correctness
step identity preservation
operation identity preservation
locator validity
capability support
permission requirements
page-state dependencies
pre/postconditions
risk classification
no silent drops/reorders
```

If validation fails:

```text
validation_failed
→ retry if allowed
→ clarification/recovery/fail-safe
```

---

## 17. Context request and escalation by LLM

LLM may request more context only through a structured request:

```text
context_request
requested_context_type
reason
scope
```

Backend approves only if:

```text
purpose allows it
token budget allows it
scope is specific
request is relevant
user/security rules allow it
```

If rejected:

```text
context_request_denied
reason
fallback action
```

---

## 18. Memory and Human Feedback Policy

The LLM layer must not behave like a stateless one-shot prompt.

AutoWorkbench should preserve useful session/project knowledge while still sending only the smallest relevant context to the LLM.

Core rule:

```text
Backend stores durable useful memory.
LLM receives only selected relevant memory for the current purpose.
Human feedback is preferred over guessing when ambiguity is real.
```

### 18.1 Human feedback first

Human feedback is a first-class control mechanism.

When ambiguity, missing data, risk, or low confidence exists, the system should ask the user instead of guessing.

Common human-feedback triggers:

```text
unclear scope
missing test data
duplicate locator candidates
risky submit/upload/download action
unsupported capability
unclear plan correction
recovery may change user intent
low-confidence locator or assertion
conflicting user instructions
```

Every LLM purpose may return one of these safe outputs:

```text
need_user_input
need_more_context
cannot_safely_continue
capability_gap
```

Examples:

```text
duplicate Get started buttons
→ ask user to choose header / hero / footer

resume upload required but file missing
→ ask user for file reference

submit action required but permission missing
→ ask user for permission

locator specialist cannot find reliable locator
→ show candidates and ask user instead of inventing XPath
```

### 18.2 Stored memory is not prompt context

The backend may store detailed memory, but the LLM should not receive all memory on every call.

```text
stored memory = durable backend/session/project knowledge
prompt context = selected subset chosen by LLM Runtime Controller
```

Store useful memory:

```text
conversation history
conversation summaries
accepted plans
rejected plans
plan versions
user corrections
clarifications
permissions
test data references
locator decisions
rejected locator candidates
failure/recovery attempts
recorded steps
code versions
trace summaries
page/section summaries
capability gaps
```

Do not send by default:

```text
full chat history
all tool calls
all trace logs
all DOM extracts
all old plans
raw files/secrets
```

### 18.3 Memory layers

Use layered memory so retrieval stays precise.

```text
working_memory
session_memory
artifact_memory
project_memory
skill_memory
```

#### working_memory

Short-lived current task state:

```text
current user request
active step
active plan
current page state
current failure
open clarification
open permission request
```

#### session_memory

Current conversation/run memory:

```text
conversation summary
accepted/rejected user decisions
plan versions
current run history
permissions granted for run
recent recovery attempts
```

#### artifact_memory

Reference-heavy technical artifacts:

```text
page summaries
section snapshots
locator candidate sets
recorded steps
generated code
screenshots
trace artifacts
replay results
```

Artifacts should usually be passed by reference or summarized, not pasted into every prompt.

#### project_memory

Longer-lived project/user preferences:

```text
preferred locator style
avoid XPath preference
testing persona
app-specific known patterns
common staging URLs
known weak DOM patterns
prior repaired locators
```

#### skill_memory

Reusable procedural knowledge:

```text
locator ambiguity handling
dynamic dropdown strategy
table assertion strategy
WordPress/Elementor weak DOM strategy
resume upload flow strategy
result page validation patterns
```

### 18.4 Memory retrieval by LLM purpose

Each LLM policy must declare memory scope.

Examples:

```text
intent_classifier
→ current user message + compact UI state only

journey_planner
→ active goal + project preferences + page summary + test data requirements

step_plan_normalizer
→ pending steps + accepted/rejected step decisions + locator states

plan_diff_editor
→ active plan version + user correction + accepted/rejected prior plan decisions

locator_specialist
→ current locator + rejected locators + candidate list + section/page snapshot ref

recovery_diagnoser
→ failed operation + prior recovery attempts + focused trace summary

replay_repair_specialist
→ recorded operation + replay failure + prior repairs/rejected locator choices
```

### 18.5 Context condensation

When sessions grow, older conversation should be condensed into structured memory.

Policy:

```text
keep recent relevant turns verbatim
summarize older decisions into conversation_summary
keep large artifacts as references
preserve accepted/rejected decisions explicitly
preserve unresolved items explicitly
```

Do not rely on raw chat history as memory.

### 18.6 Rejected decision memory

Rejected choices are important.

Store:

```text
rejected locator candidates
rejected plan changes
denied permissions
failed recovery attempts
user-disliked locator styles
capability choices the user declined
```

Purpose:

```text
avoid repeating the same bad suggestion
explain why a previous path was not reused
improve future suggestions within the same session/project
```

### 18.7 Skill learning / skill update policy

Skills are reusable procedural knowledge.

P0 rule:

```text
Do not auto-mutate production skills during normal execution.
```

Allowed in P0:

```text
suggest_skill_update
log_skill_gap
manual approval before updating skill docs
```

Future rule:

```text
After repeated successful repairs or repeated user corrections, suggest creating/updating a skill.
```

Examples of skill candidates:

```text
Playwright docs code block validation
WordPress/Elementor weak DOM locator strategy
AI Salary Analyzer result validation
Dynamic dropdown handling
Table row assertion strategy
```

### 18.8 Memory safety boundaries

Memory can guide the LLM, but memory is not runtime truth.

Backend still validates:

```text
locators
permissions
preconditions
postconditions
capabilities
schemas
execution outcomes
recording
code_update
```

User/project memory must not override:

```text
backend execution contract
safety rules
tool restrictions
permission policy
schema requirements
token budgets
```

### 18.9 Memory observability

Each LLM call trace should include:

```text
memory_scope_used
memory_items_retrieved
artifact_refs_used
conversation_summary_version
skills_retrieved
estimated_memory_tokens
why memory was retrieved
```

Trace tab should show this compactly so token usage and agent behavior are explainable.

---

## 19. Observability and Trace UI requirements

Trace tab should show:

```text
LLM purpose
model used
persona/policy id
skills loaded
context level
why LLM was called
why context escalated
tools exposed
token usage
schema validation result
backend validation result
failure/fallback path
```

This should be compact and filterable.

---

## 19. Main anti-patterns to prevent

```text
one main_orchestrator for everything
loading actions/assertions/debugging skills by default
exposing all tools during execution
sending full DOM by default
sending full history by default
LLM emitting lifecycle truth
LLM mutating plan directly
LLM recording success
LLM choosing locator without backend validation
unbounded recovery loops
schema failures becoming prose handling
```

---

## 20. Compatibility with backend/frontend specs

### Backend compatibility

This policy plugs into backend as:

```text
runtime/llm_controller.py
runtime/context_policy.py
runtime/skill_manager.py
runtime/model_router.py
runtime/tool_policy.py
runtime/schema_validator.py
```

It consumes existing backend state:

```text
conversation_state
plan_state
plan_diff_state
step_state
locator_state
permission_state
test_data_requirements
page_state
trace_summary
```

### Frontend compatibility

Frontend does not need prompt details.

Frontend receives:

```text
llm_call_started
llm_call_completed
llm_call_failed
skill_load_state
context_policy_used
token_usage_updated
trace_summary_updated
```

Primary UI destinations:

```text
LLM tab compact activity
Trace tab detailed LLM report
Global header for blocking failures
```

---

## 21. Final principle

The LLM layer should feel intelligent to the user because the system is controlled underneath.

```text
Classify first.
Use deterministic backend first.
Call purpose-specific LLM only when needed.
Send smallest sufficient context.
Load only relevant skills.
Expose only allowed tools.
Validate every output.
Trace every decision.
```

