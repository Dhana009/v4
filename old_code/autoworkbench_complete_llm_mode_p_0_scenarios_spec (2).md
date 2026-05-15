# AutoWorkbench Complete LLM Mode P0 — Scenario and Architecture Spec

## 1. Purpose

This document defines the practical Complete LLM Mode scope for AutoWorkbench.

The goal is not only to support simple click/assert flows. The goal is to build a reliable browser automation agent that can:

```text
understand broad user intent
→ clarify ambiguity
→ analyze page/section context
→ recommend or draft a plan
→ allow user revision
→ validate final plan through backend contracts
→ execute safely
→ record reliable Playwright steps
→ generate runnable code
→ recover or stop predictably when failures happen
```

This document is scenario-driven. Each scenario is used to expose architecture needs, event states, ownership boundaries, failure paths, and required tests.

---

## 2. Core product interpretation

Complete LLM Mode is a browser automation agent.

It is not primarily for single simple actions like:

```text
click this button
assert this text
```

Those are supported as atomic operations, but Manual Mode is better suited for deterministic one-off recording.

LLM Mode is mainly for:

```text
full user journeys
page/section validation recommendations
multi-step flows
plan discussion and correction
weak DOM locator reasoning
multi-page automation
failure recovery
recording complete usable automation
```

---

## 3. Non-negotiable architecture decisions

### 3.1 Backend owns runtime truth

The LLM may reason, propose, explain, and repair.

The backend owns:

```text
lifecycle state
plan mutation acceptance
execution contract
step identity
locator validation
recording
code_update
completion/failure truth
```

The frontend renders backend state and collects user input.

### 3.2 Event-driven lifecycle

Any lifecycle change must become a typed event.

No hidden state transition should exist only in logs or LLM prose.

Core event categories:

```text
user input events
intent classification events
clarification events
page intelligence events
plan/recommendation events
plan revision events
confirmation events
execution events
precondition events
locator events
recovery events
recording events
codegen events
capability gap events
completion events
```

### 3.3 Plan Mode before broad execution

For broad or ambiguous work, the system must enter Plan Mode before execution.

Examples:

```text
build this full flow
validate this page
recommend assertions
check this properly
upload this file and validate results
```

Plan Mode must clarify scope before expensive DOM exploration or browser-changing actions.

### 3.4 Discussion is not mutation

The user may brainstorm or ask the LLM to rethink a plan.

Examples:

```text
what if we remove this?
maybe add salary range validation
can you rethink this?
```

These should not mutate the active executable plan.

Only explicit apply language should mutate the plan:

```text
update the plan
apply this
make these changes
confirm this version
```

### 3.5 Every LLM call must use a context policy

No LLM call should receive raw full DOM or full history by default.

Every LLM call must declare:

```text
purpose
allowed context
input budget
required output schema
allowed tools
fallback if invalid
```

### 3.6 Page Intelligence before Main LLM for DOM-heavy work

For DOM-heavy work, the backend should first produce a compact page/section intelligence summary.

The Main LLM should receive structured summaries, not huge DOM dumps.

### 3.7 Locator ambiguity is first-class

Locator failure and ambiguity are expected real-world cases, not exceptions.

The system must classify locator issues explicitly:

```text
locator_not_found
locator_matches_multiple
locator_matches_wrong_element
locator_unstable
locator_hidden
locator_detached
locator_scope_missing
locator_text_mismatch
locator_requires_frame_or_shadow
```

### 3.8 Page-state and dependency awareness

Every step should know its page/state assumptions.

A planned operation should carry:

```text
required_page_state
precondition
postcondition
expected_outcome
depends_on_step_ids
locator_scope
```

### 3.9 Permission/autonomy mode

The user should control how much the agent can do without asking.

Suggested modes:

```text
strict: ask before every browser-changing action
balanced: auto-run safe actions, ask for risky actions
auto: run confirmed plan, ask only for high-risk/destructive actions
```

Suggested risk categories:

```text
safe: analyze, read, assert
medium: click, fill, navigation
high: submit, upload, download, new tab, external side effects
destructive: delete, payment, irreversible changes, production data mutation
```

### 3.10 Deterministic-first locator resolution is global

Locator resolution must be deterministic-first across all modes.

This rule applies to:

```text
manual_mode
steps_mode
free_llm_mode
replay_repair_mode
```

The system should not call the LLM for locator selection when a reliable locator can be generated and validated programmatically.

Global locator flow:

```text
element_info / section_info / page_summary
→ generate locator candidates programmatically
→ rank by semantic reliability
→ pick best candidate
→ validate live in browser
→ if count == 1 and action/assertion compatibility passes, use locator
→ if invalid, ambiguous, low-confidence, or user requests improvement, call LLM with focused locator context
→ backend validates any LLM-suggested locator before activation
```

Default semantic priority:

```text
role + accessible name
label
placeholder
alt/title
stable data-testid
aria attributes
stable scoped text
stable id
scoped CSS
XPath only as last resort
```

### 3.10.1 Duplicate handling uses scoped/chained locators first

If a locator candidate matches multiple elements, the backend should not immediately call the LLM.

It should first attempt programmatic scoping and chaining.

Duplicate resolution flow:

```text
candidate locator count > 1
→ identify nearest useful scope/container
→ try section/card/form/dialog/table-row/list-item scope
→ try ancestor heading/label relation
→ try Playwright filter/has/hasText patterns
→ validate chained locator
→ if unique, use without LLM
→ if still ambiguous, ask user to choose or call LLM with focused ambiguity context
```

Preferred uniqueness strategy:

```text
scope by meaningful container
→ chain child locator inside scope
→ filter by nearby text/label/row/card content
→ validate count == 1
```

Avoid fragile fallback unless explicitly needed:

```text
nth/index locator only as last resort
mark as fragile
prefer user confirmation before activation
```

Examples of desired Playwright-style strategy:

```text
section scope → button inside section
card/list item scope → CTA inside matching card
table row scope → cell/action inside matching row
dialog scope → field/button inside dialog
```

### 3.10.2 User-requested locator improvement

The user should be able to request a better locator at any stage for a specific step or operation.

Examples:

```text
I am not happy with this locator.
Find a better locator for this step.
Use the section scope instead of global text.
Avoid XPath for this operation.
Use the table row as scope.
```

Flow:

```text
user requests locator improvement
→ backend identifies target step/operation
→ backend loads stored locator context
→ backend regenerates deterministic candidates first
→ backend validates candidates live
→ if user explicitly asks LLM or deterministic candidates are weak, call LLM with focused locator packet
→ LLM proposes locator alternatives/strategy
→ backend validates each proposed locator
→ user selects/accepts candidate
→ backend updates step/operation locator
→ code_update/replay archive uses updated locator
```

Focused locator packet sent to LLM should include only:

```text
step_id / operation_id
target semantic name
current locator and validation result
candidate locators already tried
nearby element/ancestor summary
section/page scope summary
user preference, such as avoid XPath or use section scope
failure/ambiguity reason
```

It should not include full raw DOM unless escalation policy allows it.

Each operation should store locator context for future validation, repair, replay, and update:

```text
original element_info
candidate locator list
selected locator
validation count
semantic name
risk/confidence
locator_scope
nearby ancestor summaries
page_snapshot_ref or section_snapshot_ref when available
```

This prevents unnecessary LLM calls, reduces token usage, and keeps locator behavior consistent across Manual Mode and LLM Mode.

### 3.11 Observability is part of architecture

Each run must produce structured trace evidence.

Minimum trace fields:

```text
run_id
plan_id
step_id
operation_id
phase
event_type
status
reason
duration_ms
llm_purpose
estimated_tokens
artifact_path on failure
```

Failures must answer:

```text
what was expected?
what happened?
which layer failed?
what evidence exists?
what is the next legal action?
```

---

## 4. Core states

The frontend/backend should align around these user-visible/runtime states:

```text
idle
planning
clarification
analysis
recommendation_review
plan_review
plan_revision_discussion
awaiting_confirmation
executing
recovery
recording
completed
failed
```

### State meanings

| State | Meaning | User action allowed |
|---|---|---|
| idle | no active run | add step, start plan, load session |
| planning | backend/LLM preparing plan | wait, cancel |
| clarification | system needs user input | answer question, choose option |
| analysis | page/section intelligence running | wait, cancel |
| recommendation_review | LLM suggested validations/actions | accept, remove, revise, discuss |
| plan_review | executable plan shown | confirm, send correction |
| plan_revision_discussion | user is discussing possible plan change | continue discussion, apply diff |
| awaiting_confirmation | corrected/final plan ready | confirm or correct |
| executing | backend executing confirmed plan | stop/pause only |
| recovery | operation failed and needs repair/user decision | provide recovery instruction, skip, stop |
| recording | backend converting evidence to recorded step/code | wait |
| completed | run finished | save, replay, export |
| failed | unrecoverable or stopped | inspect artifacts, retry/edit |

---

## 5. Classification-first architecture

The system must not create a unique custom solution for every user request.

Every user input, plan edit, locator issue, failure, and capability request should first be classified into a finite event/category. The classified category decides the next pipeline.

### 5.1 User intent classifications

```text
single_action
single_assertion
section_validation
page_validation_recommendation
full_journey_automation
queued_multi_step_flow
plan_revision_discussion
plan_correction_apply
clarification_answer
recovery_instruction
locator_update_request
capability_request
unsupported_or_out_of_scope
stop_or_cancel
```

### 5.2 Plan edit classifications

```text
discuss_only
add_operation
remove_operation
reorder_operations
replace_target
change_expected_outcome
split_step
merge_steps
skip_step
apply_revision
reject_revision
```

### 5.3 Locator issue classifications

```text
locator_not_found
locator_matches_multiple
locator_matches_wrong_element
locator_unstable
locator_hidden
locator_detached
locator_scope_missing
locator_text_mismatch
locator_requires_frame_or_shadow
```

### 5.4 Execution failure classifications

```text
precondition_failed
permission_required
assertion_timeout
action_timeout
navigation_timeout
element_not_interactable
page_state_mismatch
unsupported_capability
llm_schema_invalid
tool_contract_mismatch
unknown_runtime_error
```

### 5.5 Capability/risk classifications

```text
safe_read_or_assert
medium_browser_action
high_risk_submit_upload_download
destructive_or_external_side_effect
unsupported_capability
requires_human_input
```

### 5.6 Classification rule

```text
request/event/failure
→ classify
→ choose pipeline
→ prepare minimal context policy
→ execute deterministic checks first
→ call LLM only when required
→ backend validates result
→ emit typed event
```

This prevents one-off logic and keeps the architecture predictable.

---

## 6. Core event pipeline

General pipeline:

```text
user_input_received
→ intent_classified
→ clarification_needed OR page_analysis_requested OR draft_plan_requested
→ page_summary_ready / section_summary_ready
→ recommendations_ready OR draft_plan_ready
→ user_review / plan_revision_discussion
→ plan_diff_proposed
→ plan_diff_applied
→ plan_confirmed
→ execution_started
→ operation_precondition_check
→ operation_locator_validated
→ operation_executed OR operation_failed
→ observed_outcome_captured
→ step_recorded
→ code_update
→ run_completed OR recovery_needed
```

---

## 6. Scenario 1 — Full journey automation

### User story

```text
Build a test for AI Salary Analyzer.
Upload a resume, complete the form, submit it, and validate the result page.
```

### Why this matters

This is a true LLM Mode use case. It is broad, multi-step, multi-page, data-driven, and can include file upload and result-page validation.

### Initial handling

The system must not immediately execute.

It enters Plan Mode.

### Events

```text
user_input_received
intent_classified: full_journey_automation
clarification_needed
plan_scope_confirmed
page_analysis_requested
page_summary_ready
journey_plan_draft_ready
recommendation_review / plan_review
plan_confirmed
execution_started
...
```

### Required clarification

Ask only what is needed:

```text
Which resume file should I use?
What test data should I use for form fields?
What should be validated on the result page?
Should I validate only UI, or also CRM/API side effects?
Can I submit the form, or should I ask before submit?
```

### Backend stores

```text
run_id
goal
permission_mode
resume_file_reference
test_data
page_summaries
candidate locators
draft_plan
plan_versions
confirmed_plan
step_dependencies
preconditions/postconditions
execution evidence
recorded steps
code lines
```

### Context sent to LLM

For clarification:

```text
user goal + missing required fields
```

For planning:

```text
confirmed scope
current page summary
available actions/forms/sections
candidate locator summary
permission policy
required output schema
```

### Risk → handling

| Risk | Handling |
|---|---|
| upload handling | permission mode + capability gap if unsupported |
| form data generation | ask user or propose editable test data |
| submit permission | high-risk action; confirm unless allowed |
| multi-page transition | precondition/postcondition dependency model |
| result page wait | planned wait strategy before assertion |
| result validation | Page Intelligence recommends sections/assertions |
| token explosion | context policy + Page Intelligence summary |
| unsupported CRM/API side effects | capability_gap_recorded |
| weak locator | locator ambiguity pipeline |

### Required tests

```text
clarification before upload/submit
plan includes editable test data
submit permission required in strict/balanced mode
result page wait strategy appears in plan
recording preserves multi-step parent/children
code_update includes upload/fill/submit/assertions when supported
capability gap when unsupported behavior is requested
```

---

## 7. Scenario 2 — Page/section validation recommendations

### User story

```text
Go through this page and recommend what assertions we should add.
```

### Why this matters

This is one of the strongest LLM Mode use cases. The user wants the agent to reduce thinking effort, not simply execute a known click.

### Events

```text
user_input_received
intent_classified: recommend_validations
clarification_needed if scope unclear
page_analysis_requested
page_summary_ready
validation_recommendations_ready
recommendation_review
plan_diff_applied after user accepts
plan_ready
```

### Clarification examples

```text
Should I focus on visible content, CTA behavior, form behavior, or all important sections?
Should I recommend only high-value assertions or exhaustive assertions?
Is this for smoke, sanity, or regression coverage?
```

### Page Intelligence output needed

```text
sections[]
headings[]
ctas[]
forms[]
important text blocks[]
code blocks[]
risk flags[]
semantic quality
candidate locators summary
recommended assertions by section
```

### Main LLM receives

```text
user goal
page/section summary
recommended assertions
risk flags
allowed recommendation schema
```

Not raw full DOM by default.

### Risk → handling

| Risk | Handling |
|---|---|
| recommends too many assertions | group by priority: critical/useful/optional |
| weak DOM | Page Intelligence marks semantic_quality and risk |
| unclear scope | clarification before analysis |
| duplicates | locator ambiguity events |
| recommendation accidentally becomes execution | recommendation_review state, no execution until confirm |

### Required tests

```text
broad request triggers recommendation mode, not execution
recommendations grouped by section
user can remove/add/reorder recommendations
accepted recommendations become executable plan
unaccepted recommendations do not execute
```

---

## 8. Scenario 3 — Weak DOM and duplicate locator ambiguity

### Deterministic-first locator rule

Locator resolution must be deterministic first.

The system should not call the LLM if a stable locator can be found and validated programmatically.

Programmatic locator flow:

```text
element_info / section_info / page_summary
→ generate candidates programmatically
→ rank by stability
→ validate live in browser
→ if count == 1 and action/assertion compatibility passes, use locator
→ no LLM call
```

Candidate priority should include:

```text
role + accessible name
label
placeholder
alt/title
stable data-testid
aria attributes
scoped text
stable id
scoped CSS
XPath only as last resort
```

The LLM is used only when:

```text
no valid locator is found
multiple candidates remain ambiguous
the chosen locator is valid but low-confidence/fragile
user explicitly asks for a better locator
locator repair is needed after failure
semantic interpretation is needed for weak DOM
```

### Locator update / improvement flow

The user may request a better locator for a specific recorded step or operation.

Example:

```text
This locator works, but I want a better one.
Find another locator for this step.
Use the section scope instead of global text.
```

Flow:

```text
user requests locator update
→ backend loads step/operation context
→ backend uses stored element_info / section_snapshot_ref / page_snapshot_ref
→ deterministic candidates are regenerated first
→ candidates are validated live
→ if user asks for LLM help or deterministic candidates are weak, LLM receives compact locator context
→ LLM proposes alternatives
→ backend validates alternatives
→ user confirms preferred locator
→ recording/code_update/replay archive use updated locator
```

Important rule:

```text
LLM can suggest locator strategy, but backend validates uniqueness and compatibility before activation.
```

Each step/operation should retain enough locator context for future repair/update:

```text
original element_info
selected candidate
candidate locator list
section/page scope
page_snapshot_ref or section_snapshot_ref
validated locator
validation count
semantic name
risk/confidence
```

This allows locator updates without resending the full DOM to the LLM.


### User story

```text
Validate this section and click the correct Get started button.
```

Page contains multiple Get started buttons and weak div/span markup.

### Events

```text
user_input_received
intent_classified: section_multi_action
section_context_requested
section_summary_ready
locator_candidates_generated
locator_ambiguous if needed
clarification_needed / candidate_choice_needed
plan_ready
```

### Locator ambiguity flow

```text
locator candidates generated
→ backend validates counts
→ if count == 1, continue
→ if count == 0, locator_not_found
→ if count > 1, locator_matches_multiple
→ try scoped locator
→ try ancestor/container scope
→ if still ambiguous, ask user to choose candidate
```

### User-facing ambiguity question

```text
I found multiple Get started buttons. Which one should I use?
1. Header CTA
2. Hero CTA
3. Footer CTA
```

### Risk → handling

| Risk | Handling |
|---|---|
| duplicate text | candidate choice or scoped locator |
| bad div/span DOM | Page Intelligence semantic classification |
| picker selected inner span | ancestor candidate selection required |
| locator matches wrong thing | validation + user-visible candidate summary |
| full DOM token explosion | send candidate summary only |

### Required tests

```text
duplicate text triggers ambiguity handling
scoped section locator preferred over global text locator
weak div/span candidate gets semantic name
backend never executes with count > 1 unless user explicitly chooses a candidate
```

---

## 9. Scenario 4 — Plan revision like ChatGPT/Cursor

### User story

User sees a proposed plan:

```text
1. Assert banner
2. Assert heading
3. Click Get started
4. Assert docs page
```

User says:

```text
Remove banner assertion, add exact command text validation, and click OpenCode before validating the command.
```

### Events

```text
user_input_received
intent_classified: plan_revision
plan_revision_discussion OR plan_diff_requested
plan_diff_proposed
plan_diff_validated
plan_diff_applied
updated_plan_ready
```

### Important distinction

Discussion is not mutation.

The plan is changed only after explicit apply/update instruction or user confirmation.

### Backend validation

Before applying diff:

```text
explicit removal intent exists
added operation has target/page context
operation order is valid
no silent child drop
no silent split/merge
existing locators reused unless target changes
unsupported mutation fails safely
```

### Risk → handling

| Risk | Handling |
|---|---|
| LLM drops click silently | backend diff validation blocks |
| user is brainstorming | plan_revision_discussion, no mutation |
| added target not grounded | ask clarification or run locator candidate flow |
| order invalid across pages | dependency/precondition validation |
| repeated correction loop | schema retry once, then clarification/fail-safe |

### Required tests

```text
assert-first-then-click correction preserves click
remove operation only works with explicit remove intent
brainstorming question does not mutate active plan
invalid diff fails closed
corrected plan executes only after confirmation
```

---

## 10. Scenario 5 — Multi-page flow with wrong current browser state

### User story

The user has a plan that starts on the landing page, but the browser is currently on the result page.

Plan:

```text
1. upload resume on landing page
2. submit form
3. validate result page
```

### Events

```text
execution_started
step_precondition_check_started
precondition_failed
precondition_resolution_options_ready
user_choice_received OR deterministic_resolution_selected
execution_resumed
```

### Precondition handling

Backend checks:

```text
current_url/current_page_state matches step.required_page_state?
```

If not, options:

```text
navigate to expected start URL
replay dependency steps
ask user to move browser manually
skip step
stop run
```

LLM should not be called unless the decision is ambiguous.

### Risk → handling

| Risk | Handling |
|---|---|
| validating step on wrong page | precondition check before locator/action |
| unnecessary LLM call | deterministic resolution first |
| user does not want navigation | permission/autonomy mode |
| dependency unknown | ask user or mark plan incomplete |
| state restore not implemented | clearly show supported options only |

### Required tests

```text
wrong page triggers precondition_failed
safe navigation can be suggested but not silently executed in strict mode
dependency chain is respected
LLM not called for deterministic precondition mismatch
```

---

## 11. Scenario 6 — Failure mid-execution and recovery

### User story

Execution fails because:

```text
locator count = 3
element hidden
timeout waiting for result
page did not load
```

### Events

```text
operation_failed
failure_classified
deterministic_recovery_attempted
recovery_needed
repair_diff_proposed
repair_validated
user_confirmed_if_intent_changes
execution_resumed OR step_skipped OR run_failed
```

### Failure categories

```text
locator_not_found
locator_matches_multiple
locator_hidden
locator_detached
assertion_timeout
navigation_timeout
page_state_mismatch
unsupported_capability
permission_required
```

### Context sent to LLM for repair

Only after deterministic recovery fails:

```text
failed operation
original user intent
current page summary
candidate locators
what was tried
allowed repair schema
```

Not raw full DOM unless explicitly escalated.

### Risk → handling

| Risk | Handling |
|---|---|
| infinite loops | bounded retry policy |
| LLM changes goal | repair diff limited to failed operation |
| full DOM token explosion | failure-context policy |
| user intent change needed | ask user before mutation |
| fake success | backend validates repaired action before recording |

### Required tests

```text
locator count > 1 triggers recovery, not random click
retry limit stops loops
repair only changes failed operation
user confirmation required for intent change
failed unresolved step does not record/code_update
```

---

## 12. Scenario 7 — Permission/autonomy control

### User story

User asks:

```text
Build and run the full flow.
```

The plan includes submit/upload/download/external side effects.

### Events

```text
risk_classified
permission_required
permission_granted / permission_denied
execution_continued / plan_paused
```

### Permission modes

```text
strict: ask before every browser-changing action
balanced: safe actions auto-run; risky actions ask
auto: confirmed plan runs; destructive/high-risk actions ask
```

### Risk classification

```text
safe: assert/read/analyze
medium: click/fill/navigation
high: submit/upload/download/new tab/external side effect
destructive: delete/payment/send email/irreversible production change
```

### Required tests

```text
submit requires confirmation in strict/balanced mode
assertion does not require confirmation
destructive action is blocked or requires explicit confirmation
permission decision is logged in trace
```

---

## 13. Scenario 8 — Unsupported capability / gap logging

### User story

```text
Download the PDF and verify file contents.
```

If file-content verification is unsupported, system must not fake success.

### Events

```text
capability_checked
capability_gap_recorded
partial_plan_ready
```

### Behavior

System may say:

```text
I can verify that the download was triggered, but file-content verification is not supported yet.
```

### Gap entry includes

```text
timestamp
url
user_intent
failed_step_id / operation_id
needed_capability
available_tools
suggested_future_work
```

No secrets.

### Required tests

```text
unsupported action logs capability gap
partial supported work can continue if safe
no fake recorded success
frontend shows non-blocking limitation
```

---

## 14. Possible missing scenarios to review

These may need discussion before finalizing P0/P1:

### 14.1 Auth/login precondition

User asks to validate dashboard but is logged out.

Possible handling:

```text
ask user to login manually
use saved auth state if available
start from public flow only
```

### 14.2 Sensitive/test data handling

User uploads resume or enters phone/email.

Need rules for:

```text
secrets masking
logs redaction
test data visibility
no accidental generated code with private values unless allowed
```

### 14.3 Environment-specific behavior

Different region, staging vs production, mobile vs desktop.

Need plan metadata:

```text
environment
viewport
region/auth state
```

### 14.4 Long-running async result generation

Example: resume analysis takes 60 seconds.

Need:

```text
wait strategy
timeout policy
progress feedback
no premature assertion failure
```

### 14.5 Human-in-the-loop during execution

Examples:

```text
OTP
captcha
manual login
file chooser if automation blocked
```

Need recovery/clarification event support.

---

## 15. Backend/runtime intake model

Complete LLM Mode must support multiple user entry paths without creating separate backend architectures.

### 15.1 Entry paths

```text
manual_mode
steps_mode
free_llm_mode
replay_repair_mode
```

### 15.2 Entry path meanings

| Entry path | User behavior | Backend interpretation |
|---|---|---|
| manual_mode | user explicitly chooses action/assertion | deterministic operation with LLM only for repair/failure |
| steps_mode | user adds focused pending steps, often with picked element/section | structured pending steps submitted to LLM for planning/validation |
| free_llm_mode | user asks broad agent task in chat | classify intent, clarify, analyze, recommend/plan, then execute only after confirmation |
| replay_repair_mode | user replays old recording and it breaks | classify replay failure, repair recorded operation through validated diff |

### 15.3 Unified backend rule

All entry paths must converge into the same backend runtime primitives:

```text
classified_intent
context_policy
plan_or_operation
precondition
capability_handler
execution_contract
recording
code_update
trace_event
```

This prevents Manual Mode, Steps Mode, and Free LLM Mode from becoming incompatible systems.

### 15.4 Steps Mode rule

Steps Mode is for focused user-guided automation.

The user may add:

```text
single picked element step
selected section step
multi-action step
multi-step queue
expected outcome metadata
test data references
```

Backend must preserve step identity and page context from draft to plan to execution to recording.

### 15.5 Free LLM Mode rule

Free LLM Mode is for broad work completion.

Examples:

```text
build a full journey test
recommend validations for this page
explore this page and create assertions
repair this flow
```

It must start with classification and clarification before expensive analysis or execution.

### 15.6 Page ownership rule

Every step or operation that depends on page state must store enough page context for backend validation:

```text
source_page_url
required_page_state
precondition
postcondition
expected_outcome
depends_on_step_ids
locator_scope
page_snapshot_ref or section_snapshot_ref when available
```

The backend should validate the current page state before executing each operation. If the browser is on the wrong page, emit `precondition_failed` and use deterministic options before calling the LLM.

---

## 16. Capability framework for actions, assertions, and browser behaviors

The system must not create separate architecture for every Playwright feature.

Every supported or future Playwright behavior should use a common capability contract.

### 15.1 Capability contract

```text
capability_type
category
required_inputs
risk_level
preconditions
handler_strategy
postconditions
recording_shape
codegen_template
recovery_strategy
capability_gap_if_unsupported
```

### 15.2 Capability categories

```text
action_capabilities
assertion_capabilities
navigation_capabilities
input_data_capabilities
browser_context_capabilities
file_capabilities
popup_tab_dialog_capabilities
table_list_capabilities
network_wait_capabilities
auth_session_capabilities
visual_debug_capabilities
```

### 15.3 Action capabilities

Examples:

```text
click
fill
press
hover
scroll
select_option
check/uncheck
upload_file
drag_drop
submit
```

Each action must define:

```text
required input
risk level
locator requirement
precondition
postcondition
recorded operation
codegen template
```

### 15.4 Assertion capabilities

Assertions are first-class capabilities, not generic text checks.

Assertion types:

```text
visible
hidden
enabled
disabled
has_text
exact_text
contains_text
has_value
checked
unchecked
url_matches
title_matches
count_equals
table_contains
list_contains
attribute_equals
css_state
```

Each assertion must define:

```text
target type
expected value needed or not
normalization rules
locator scope
failure type
codegen template
```

Example:

```text
exact_text
required_inputs: target + exact expected text
normalization: whitespace/control character handling
handler: expect(locator).toHaveText(...) or equivalent
failure: assertion_text_mismatch / assertion_timeout
```

### 15.5 Browser/context capabilities

Examples:

```text
new_tab
popup_window
modal_dialog
iframe
shadow_dom
download
auth_required
otp_required
long_running_result
```

These usually need pre-registration or user input.

Example:

```text
new_tab
precondition: waitForPage registered before click
postcondition: new page URL/title/locator validated
recording: new_tab operation with child actions
codegen: Promise.all([context.waitForEvent('page'), click])
```

### 15.6 Tables/lists/data extraction

Tables and lists need structured extraction capabilities.

Examples:

```text
extract_table
assert_table_row
assert_table_cell
assert_list_item
count_rows
filter_table
```

The LLM should receive compact table summaries unless exact table data is required.

---

## 16. Test data management

Test data is a first-class part of LLM Mode.

The system must know when data is required, how to collect it, how to store it safely, and how to pass only safe references to the LLM.

### 16.1 Test data classifications

```text
text_value
email
phone
name
number
salary_range
file_reference
resume_file
credentials
otp_or_manual_code
dropdown_option
table_expected_value
api_or_crm_expected_value
generated_safe_test_data
sensitive_secret
```

### 16.2 Test data events

```text
test_data_required
test_data_proposed
test_data_collected
test_data_validated
test_data_redacted_for_logs
test_data_missing
test_data_rejected
```

### 16.3 Collection rules

If required data is missing, ask before execution.

Examples:

```text
resume upload requires file_reference
form fill requires field values or permission to generate safe test data
OTP requires human input
credentials require secret-safe handling
salary/result validation requires expected ranges or generated validation rules
```

### 16.4 Storage and safety rules

```text
store file references, not file content, unless needed
never print secrets or full credentials
redact sensitive values in logs and traces
show generated test data to user before execution
allow user to edit generated data
record enough data for codegen only if user permits
```

### 16.5 LLM context rules for test data

Send only what the LLM needs.

```text
For planning: send data type and availability, not secret values.
For execution repair: send failed field/operation and redacted value description.
For codegen: backend decides whether to inline, fixture-reference, or placeholder.
```

---

## 17. Adaptive context escalation

Context must be progressive. The backend should not send full DOM/history by default.

### 17.1 Context levels

```text
L0: intent-only context
L1: selected element descriptor
L2: selected section summary
L3: page intelligence summary
L4: focused debug context
L5: capped raw DOM/full snapshot fallback
```

### 17.2 Escalation policy

```text
start with smallest sufficient context
if locator not found → add nearby candidates/section summary
if multiple locators → add scoped candidate list
if assertion mismatch → add target text/current text/normalization info
if recovery fails → add focused debug context
use raw DOM only as last resort
```

### 17.3 Each LLM call declares

```text
purpose
context_level
input_budget
included_context
excluded_context
required_schema
allowed_tools
retry_policy
```

This makes token usage measurable and controllable.

---

## 18. Progressive skill loading

Skills must load based on task/capability, not all at once.

### 18.1 Skill loading levels

```text
core_rules: always loaded, compact
skill_index: always loaded, compact
skill_summary: loaded for relevant capability
full_skill: loaded only when required
failure_skill: loaded only during recovery/debug
```

### 18.2 Examples

```text
simple assertion → assertion summary only
upload flow → upload skill + form skill
new tab → popup/new-tab skill
iframe issue → iframe skill during planning/recovery
dropdown issue → dropdown/autocomplete skill
```

---

## 19. Unsupported capability and boundary handling

If a request is outside current capability, the system must not fake success.

### 19.1 Events

```text
capability_checked
capability_supported
capability_unsupported
capability_gap_recorded
partial_plan_ready
```

### 19.2 Behavior

If partially supported:

```text
explain supported part
explain unsupported part
record capability gap
continue only if safe and user agrees
```

Example:

```text
I can verify the download starts, but PDF content verification is not supported yet.
```

---

## 20. Error, edge-case, and negative-path handling

Failures must be classified before recovery.

### 20.1 Error classifications

```text
locator_not_found
locator_matches_multiple
locator_wrong_target
assertion_timeout
assertion_text_mismatch
action_timeout
element_not_interactable
element_hidden
element_detached
navigation_timeout
page_state_mismatch
permission_required
test_data_missing
unsupported_capability
llm_schema_invalid
tool_contract_mismatch
websocket_disconnect
unknown_runtime_error
```

### 20.2 Error handling rule

```text
classify failure
→ emit typed failure event
→ attach compact evidence
→ deterministic recovery first
→ LLM repair only if needed
→ user confirmation if intent/risk changes
→ record only after validated success
```

### 20.3 Observability for errors

Each error must include:

```text
error_type
failed_stage
expected
actual
evidence
attempted_recoveries
next_allowed_actions
artifact_path
```

No swallowed exceptions.

---

## 21. Steps Mode locator update and page-state contract

Steps Mode needs a dedicated locator update flow because the user may be unhappy with the locator chosen for one specific pending step or operation.

This is not only a UI feature. It is a backend/frontend contract.

### 21.1 Per-step locator actions

Each pending step or child operation should support these actions when applicable:

```text
revalidate_locator
improve_locator
change_scope
view_candidates
use_llm_for_locator
```

These actions apply to one specific `step_id` and optionally one specific `operation_id`.

### 21.2 Locator update request flow

```text
user clicks Improve locator / Revalidate / Change scope on a specific step
→ frontend sends locator_update_request(step_id, operation_id, requested_action, user_hint?)
→ backend loads stored step/operation locator context
→ backend checks required_page_state against current_page_state
→ if current page/state is wrong, emit precondition_failed_for_locator_update
→ if page/state is correct, regenerate deterministic candidates
→ validate candidates live in browser
→ if valid candidate exists, return candidate list without LLM
→ if candidates are weak/ambiguous or user explicitly requests LLM, call LLM with focused locator packet
→ backend validates all LLM-suggested locators
→ frontend shows candidates for user acceptance
→ user accepts candidate
→ backend updates step/operation locator
→ code_update/replay archive use updated locator where relevant
```

### 21.3 Page-state requirement for live locator validation

A locator cannot be live-validated unless the browser is in the correct page/state for that step.

Required backend check:

```text
current_page_state matches step.required_page_state?
```

If false, backend must not pretend validation is live.

Emit:

```text
precondition_failed_for_locator_update
```

Payload should include:

```text
step_id
operation_id
required_page_state
current_page_state
required_url_or_pattern
current_url
available_resolution_options
```

Suggested resolution options:

```text
navigate_to_required_page
replay_dependency_steps
ask_user_to_move_browser_manually
update_using_stored_snapshot_only
cancel_locator_update
```

### 21.4 Stored locator context per step/operation

To support locator update without full DOM resend, each step/operation should store:

```text
original element_info
selected locator
candidate locator list
validation count
semantic name
risk/confidence
locator_scope
nearby ancestor summaries
section_snapshot_ref
page_snapshot_ref
required_page_state
precondition
postcondition
expected_outcome
```

### 21.5 Focused LLM locator packet

If LLM help is required, backend sends only focused locator context:

```text
step_id / operation_id
target semantic name
current locator
validation result
candidate locators already tried
nearby element/ancestor summary
section/page scope summary
required_page_state and current_page_state summary
user preference or hint
failure/ambiguity reason
```

Do not send full raw DOM unless adaptive context escalation allows it.

### 21.6 Steps tab locator state

The frontend should render compact locator state per step/operation:

```text
Locator: getByRole('button', { name: 'Get started' })
Status: validated / ambiguous / fragile / stale / not validated
Scope: hero section
Page state: home page
```

Available actions:

```text
Revalidate
Improve
Change scope
View candidates
Use LLM
```

If page state is wrong, show:

```text
This step belongs to: <required page/state>
Current browser page: <current page/state>
Live validation is unavailable until page state matches.
```

### 21.7 Expected outcome and postcondition redesign

For step creation, expected outcome should become explicit postcondition metadata.

Examples:

```text
click Submit
expected_outcome: result page appears
postcondition: URL contains /result or heading visible
```

Supported expected outcome/postcondition categories:

```text
navigation
modal opens
dropdown opens
new tab opens
content changes
toast/message appears
file picker opens
download starts
no visible change
unsure
```

This connects directly to page-state dependency and later replay/repair.

### 21.8 Per-step action rule

Any per-step action in Steps Mode must be page-state aware.

This includes:

```text
locator update
locator validation
expected outcome validation
operation preview
run step
```

If current page does not match the step’s required page state, the backend must emit a precondition event and present resolution options instead of performing misleading live validation.

---

## 22. LLM command/intention model

The LLM chat input can support slash-style commands, but commands are shortcuts only. Natural language must still work.

Examples:

```text
/plan Build a test for this page
/recommend assertions for this section
/apply Update the plan
/improve-locator step 3
/recover Try another locator
/trace Show last failure
```

Backend flow:

```text
chat_message_submitted
→ classify as command or natural language
→ intent_classified
→ route to plan/recommend/correction/locator/recovery pipeline
```

A command must not bypass backend validation. It only helps classification and routing.

---

## 23. Backend/UI state contract for Complete LLM Mode

The frontend must not infer product truth from text, CSS, or LLM prose.

The backend must expose typed state objects that the UI can render consistently across LLM, Steps, Recorded, Code, and Trace tabs.

### 23.1 Backend state objects exposed to UI

```text
conversation_state
plan_state
plan_versions
plan_diff_state
step_state
locator_state
recorded_step_detail
code_state
trace_summary
permission_state
test_data_requirements
page_state
replay_state
```

### 23.2 conversation_state

Purpose: preserve the LLM Mode workspace like a ChatGPT-style session.

Required fields:

```text
conversation_id
run_id
messages[]
active_goal
active_mode
last_user_intent
active_plan_id
active_plan_version_id
open_clarifications[]
open_permissions[]
open_recovery_items[]
created_at
updated_at
```

Rules:

```text
conversation history is durable within the session
LLM chat history and runtime events are linked but not the same thing
backend decides what part of conversation is sent to the LLM through context policy
frontend renders conversation_state only
```

### 23.3 plan_state and plan_versions

Purpose: support plan discussion, direct edits, LLM-driven changes, and auditability.

Required fields:

```text
plan_id
current_version_id
status: draft | recommendation | review | confirmed | stale | executing | completed | failed
versions[]
source: free_llm_mode | steps_mode | replay_repair_mode
created_from_step_ids[]
confirmed_at
invalidated_reason
```

Each plan version should include:

```text
plan_version_id
parent_plan_id
summary
steps[]
created_by: user | llm | backend
change_reason
based_on_version_id
created_at
```

Rules:

```text
plan drafts are editable
confirmed plan becomes execution contract
plan edits create new versions
old versions remain inspectable
confirmed plan cannot be silently mutated
pending step changes invalidate stale plan versions
```

### 23.4 plan_diff_state

Purpose: distinguish discussion from applied plan mutation.

Required fields:

```text
diff_id
plan_id
base_version_id
target_scope: whole_plan | step_id | operation_id | locator_only | assertion_only | result_page_only
status: proposed | validated | rejected | applied | failed
mutations[]
validation_errors[]
created_by: user_direct_edit | llm_instruction | backend_repair
```

Supported mutation types:

```text
add_step
remove_step
move_step
update_step
add_operation
remove_operation
move_operation
replace_target
replace_locator
change_expected_outcome
change_postcondition
change_test_data
change_permission_requirement
```

Rules:

```text
discussion does not mutate the plan
only validated diffs can be applied
backend validates no silent step/operation drops
backend validates dependency and page-state impact
frontend shows diff preview before apply when user confirmation is required
```

### 23.5 step_state

Purpose: expose pending step state, page dependency, and editability to the UI.

Required fields:

```text
step_id
step_order
intent
status: draft | needs_target | needs_clarification | ready | planned | executing | recorded | failed | skipped
source: user | llm | imported | replay_repair
element_info
section_info
expected_outcome
postcondition
required_page_state
depends_on_step_ids
locator_state
linked_plan_id
linked_plan_version_id
warnings[]
created_at
updated_at
```

Rules:

```text
step_id is stable and must not change on reorder
step_order can change
pending steps are editable drafts
confirmed plan steps are locked unless changed through validated diff
recorded steps are evidence/history and are not silently mutated
```

### 23.6 Editable step operations

The backend should support structured edit operations for Steps Mode:

```text
add_step_before
add_step_after
delete_step
move_step
duplicate_step
update_step
update_expected_outcome
update_postcondition
update_test_data_reference
update_locator_reference
```

Every edit should emit:

```text
steps_updated
```

If dependencies may break, also emit:

```text
dependency_warning
```

If a confirmed/draft plan becomes stale, emit:

```text
plan_invalidated
reason: pending_steps_changed | dependency_changed | locator_changed | test_data_changed | page_state_changed
```

### 23.7 Dependency validation after step edits

After add/delete/reorder/update, backend checks:

```text
whether any later step depends on deleted/moved step
whether required_page_state still matches prior postcondition
whether locator scope belongs to the expected page/section
whether test data required by a step still exists
whether step order can produce the required state transitions
```

Possible results:

```text
valid
warning
blocking_error
```

Examples:

```text
warning: Moving Step 3 before Step 1 may fail because Step 3 requires /result page.
blocking_error: Step 4 depends on deleted Step 2.
```

### 23.8 locator_state

Purpose: expose locator confidence and update actions to Steps and Recorded tabs.

Required fields:

```text
step_id
operation_id
selected_locator
candidate_locators[]
validation_status: validated | ambiguous | fragile | stale | not_validated | failed
validation_count
semantic_name
locator_scope
confidence
risk_flags[]
last_validated_page_state
can_live_validate
requires_page_state
improvement_available
```

Rules:

```text
live locator validation requires correct page state
LLM locator improvement is optional and targeted
backend validates any selected or LLM-suggested locator
```

### 23.9 recorded_step_detail

Purpose: allow Recorded tab to inspect actual recorded evidence.

Required fields:

```text
recorded_step_id
source_step_id
source_plan_id
source_plan_version_id
status
parent_intent
children[]
precondition
postcondition
expected_outcome
observed_outcome
locator_details[]
code_lines[]
replay_status
repair_status
created_at
```

Rules:

```text
recorded steps come from execution evidence only
recorded steps are immutable by default
repair creates a new version or explicit update event
```

### 23.10 code_state

Purpose: expose generated Playwright code and warnings.

Required fields:

```text
code_version_id
source_recorded_step_ids[]
lines[]
full_spec_preview
warnings[]
fragile_locator_warnings[]
incomplete_capability_warnings[]
updated_at
```

### 23.11 trace_summary

Purpose: provide UI-visible observability without terminal dependency.

Required fields:

```text
run_id
current_phase
latest_event
event_counts
llm_call_count
estimated_input_tokens
estimated_output_tokens
locator_attempt_count
last_error
artifact_paths[]
```

Trace tab can request expanded trace details, but compact trace_summary should be available globally.

### 23.12 permission_state

Purpose: support safe autonomy.

Required fields:

```text
permission_mode: strict | balanced | auto
pending_permission_requests[]
granted_for_run[]
denied_actions[]
risk_classifications[]
```

### 23.13 test_data_requirements

Purpose: collect and track required input data before execution.

Required fields:

```text
requirement_id
step_id
operation_id
data_type
label
required
sensitive
status: missing | proposed | provided | validated | rejected
value_ref
redaction_policy
```

Rules:

```text
backend stores references for files/secrets where possible
frontend shows missing/proposed/provided state
LLM receives data availability and safe descriptions, not secrets by default
```

### 23.14 page_state

Purpose: make execution, locator update, and replay page-aware.

Required fields:

```text
current_url
current_title
page_state_id
page_summary_ref
known_page_type
navigation_history_summary
active_frame_or_context
matches_required_state
```

---

## 24. Backend rules for UI-driven step editing

### 24.1 User freedom in Steps Mode

The user can:

```text
add a step anywhere
delete any pending step
move/reorder pending steps
duplicate a step
edit intent/target/outcome/test data
request locator improvement for one step
```

### 24.2 Backend validation after edit

The frontend may request edits, but backend decides whether the edited structure is valid, risky, or blocked.

Flow:

```text
frontend sends step_edit_request
→ backend applies edit to draft state
→ backend validates dependency/page-state impact
→ backend emits steps_updated
→ backend emits dependency_warning or blocking_error if applicable
→ backend invalidates stale plan if needed
```

### 24.3 User warning rule

If order changes may break the test, backend should emit a user-facing warning instead of silently accepting as safe.

Example:

```text
This change may break the flow. Step 4 requires the result page, but the step that navigates to the result page was moved after it.
```

Suggested actions:

```text
Undo
Continue anyway
Ask LLM to adjust dependencies
Recalculate plan
```

### 24.4 Plan invalidation rule

If pending steps change after a plan is created:

```text
active plan status = stale
```

The UI should require:

```text
rerun planning
apply validated diff
or explicitly confirm execution despite warnings if allowed
```

---

## 25. Required architecture components

### Backend modules

```text
runtime/step_runner.py
runtime/planner.py
runtime/plan_store.py
runtime/plan_correction.py
runtime/execution_contract.py
runtime/dependency_graph.py
runtime/page_state.py
runtime/context_policy.py
runtime/page_intelligence.py
runtime/locator_service.py
runtime/recovery.py
runtime/recording.py
runtime/codegen.py
runtime/gap_logger.py
runtime/trace.py
```

### Frontend modules

```text
frontend/transport
frontend/state_store
frontend/components/PlanMode
frontend/components/RecommendationReview
frontend/components/PlanReview
frontend/components/Clarification
frontend/components/Recovery
frontend/components/RecordedSteps
frontend/components/CodePreview
frontend/components/DebugTrace
frontend/components/PermissionPrompt
```

### Browser/picker modules

```text
browser/launcher
browser/panel_bootstrap
browser/picker_bridge
browser/element_snapshot
browser/page_snapshot
```

---

## 16. P0 scope

P0 should include:

```text
Plan Mode for broad tasks
clarification loop
page/section recommendation flow
plan review and correction
locator ambiguity handling
page-state/dependency model
backend-owned execution/recording/code_update
context policy for all LLM calls
Page Intelligence summary contract
permission/autonomy checks for risky actions
observability trace
real-world fixture test suite
```

---

## 17. P1 scope

P1 should include:

```text
save/load recording
replay one/all
replay repair
locator replacement flow
versioned repaired recording
basic session restore
```

---

## 18. P2/P3 parking lot

```text
full manual mode expansion
advanced upload/download/iframe/popup/dropdown hardening
persistent page maps/locator library
full Shadow DOM/docked panel
browser extension packaging
full multi-model agent control center
codegen reviewer/debug agent as separate UI-visible agents
```

---

## 19. Testing strategy

Test layers:

```text
unit tests for each backend module
contract tests for events/commands
integration tests for plan/correction/execution/recording
frontend state/mode tests
real E2E tests with overlay/backend/browser/LLM
real-world fixture suite
```

Critical real-world fixtures:

```text
Playwright docs-like page
weak DOM div/span page
multi-section marketing/result page
form/upload page
modal/dropdown page
multi-page journey fixture
long-running result fixture
```

---

## 20. Final principle

Complete LLM Mode must be reliable because the system is predictable.

```text
Every user input is classified.
Every ambiguous input asks clarification.
Every LLM call has a context policy.
Every plan mutation is backend-validated.
Every operation has preconditions.
Every locator ambiguity has a path.
Every failure has a typed recovery route.
Every recording comes from execution evidence.
Every important event is traceable.
```

