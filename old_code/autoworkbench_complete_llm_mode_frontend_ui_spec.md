# AutoWorkbench Complete LLM Mode — Frontend/UI Spec

## 1. Purpose

This document defines the frontend architecture and UI behavior for AutoWorkbench Complete LLM Mode.

The UI must make the product usable, debuggable, and predictable while preserving the core architecture rule:

```text
Backend decides.
Frontend renders typed backend truth and collects user input.
LLM thinks and proposes.
```

The frontend must not infer lifecycle truth from LLM prose, CSS state, loose text, or local assumptions.

---

## 2. Core UI goals

The UI must support these user workflows:

```text
1. Free LLM/agent workflow
2. Scoped Steps workflow
3. Plan review and correction
4. Locator inspection and improvement
5. Execution progress and recovery
6. Recorded step inspection
7. Code review/export
8. Trace/debug investigation
```

The UI must make it clear:

```text
what the system is doing
what it needs from the user
what has been planned
what has been confirmed
what is executing
what was recorded
what code was generated
what failed and why
what the user can do next
```

---

## 3. Main tab structure

The frontend should use five main tabs:

```text
LLM | Steps | Recorded | Code | Trace
```

### 3.1 Why not many tabs

Plan, correction, clarification, permission, and recovery are all part of the LLM interaction loop. They should not be separate top-level tabs.

Recorded output should be separate from Steps because pending steps and recorded evidence are different concepts.

---

## 4. Host architecture: Shadow DOM first

The next frontend implementation target is Shadow DOM.

The current overlay exists, but new UI work should be designed and implemented for a Shadow DOM host first, not the legacy overlay path.

### 4.1 Primary target

```text
Primary: Shadow DOM host
Secondary/later: docked/devtools-style panel
Future: browser extension panel
Legacy/transitional: current injected overlay
```

### 4.2 Product UI vs host adapter

Frontend must separate product UI from host mounting.

```text
Product UI
- tabs
- cards
- plan review
- steps builder
- recorded/code/trace views
- typed state rendering

Transport/state layer
- backend events
- frontend commands
- state normalization
- typed store

Host adapter
- Shadow DOM mount
- overlay mount if still needed temporarily
- future docked/extension mount
```

Product components should not depend directly on overlay-only globals, page CSS, or injection-specific layout assumptions.

### 4.3 Shadow DOM requirements

The Shadow DOM host should provide:

```text
style isolation from target website
stable root container
backend websocket config
mount/unmount lifecycle
z-index and layout isolation
safe event handling
keyboard/focus handling
resize support
```

The UI should remain functional when embedded inside a constrained right-side panel.

### 4.4 Legacy overlay rule

Existing overlay behavior can be used as reference, but new architecture should not optimize around it.

Rules:

```text
Do not add new product logic to browser.py legacy overlay path.
Do not duplicate React UI behavior in fallback overlay code.
Keep current overlay only as temporary compatibility until Shadow DOM host is ready.
```

### 4.5 Testability across hosts

All product UI components must expose stable test hooks that work in Shadow DOM.

Required:

```text
data-testid for important controls
host-aware E2E selectors
shadow-root aware test helpers
same backend event assertions regardless of host
```

---

## 5. Global shell layout

The panel should have common areas across all tabs.

### 4.1 Global header

The global header should show:

```text
connection status
backend phase
current URL
active run/session
active plan/version if any
current blocking state if any
compact error/status indicator
```

Examples:

```text
Connected · Planning · /ai-salary-analyzer · Run #12
Waiting for clarification
Executing Step 2/5
API key missing
```

### 4.2 Global compact activity area

A compact collapsible activity strip may appear under the header.

It should show the latest meaningful state:

```text
Classifying request
Analyzing page
Preparing plan
Waiting for permission
Executing operation
Recording step
Code updated
Recovery needed
```

This is not the full trace. Full details live in the Trace tab.

### 4.3 Global footer/actions

Common actions may include:

```text
New session
Save recording/session
Load recording/session
Run / Stop
Permission mode
Settings
```

These should be visible only when relevant and should not clutter the primary workflow.

---

## 5. LLM tab

The LLM tab is the main agent workspace.

It supports:

```text
chat
plan mode
recommendation mode
plan correction/discussion
clarification prompts
permission prompts
recovery prompts
execution progress
```

### 5.1 LLM tab sections

Recommended vertical layout:

```text
1. Compact live status / current task
2. Conversation history
3. Active cards: clarification / recommendation / plan / permission / recovery
4. Chat input at bottom
```

### 5.2 Chat history

The chat history should show:

```text
user messages
assistant/LLM responses
system clarification questions
plan revision discussions
permission requests
recovery messages
important execution summaries
```

Chat history must be backed by `conversation_state`, not only local UI state.

### 5.3 Plan Mode inside LLM tab

Plan Mode should support:

```text
plan draft
recommendation list
plan version
plan diff preview
confirm plan
apply/reject proposed changes
continue discussion
```

Plan Mode must distinguish:

```text
discussion / rethink
from
applied plan mutation
```

User examples:

```text
What if we remove this assertion?
Remove this assertion and apply it.
Move this step after the submit action.
Only update Step 3.
```

### 5.4 Direct plan editing

The user may directly edit plan content in UI.

Direct edits must still become backend-validated diffs.

Frontend should send structured edit intent; backend validates and returns:

```text
plan_diff_proposed
plan_diff_validated
plan_diff_applied
plan_invalidated
```

### 5.5 LLM command shortcuts

The LLM input may support slash commands as shortcuts:

```text
/plan Build a test for this page
/recommend assertions for this section
/apply Update the plan
/improve-locator step 3
/recover Try another locator
/trace Show last failure
```

Rules:

```text
commands help classification only
commands do not bypass backend validation
normal natural language must still work
```

### 5.6 Clarification cards

When backend emits `clarification_needed`, LLM tab should show a clear card:

```text
question
options if provided
free-text answer if needed
target step/operation if relevant
```

Examples:

```text
What should I validate: visible content, exact text, CTA behavior, or full section?
Which Get started button should I use: header, hero, or footer?
```

### 5.7 Permission cards

When backend emits `permission_required`, LLM tab should show:

```text
risk level
operation requiring permission
why permission is needed
available choices
```

Actions:

```text
Allow once
Allow for this run
Deny
Edit plan
```

### 5.8 Recovery cards

When backend emits `recovery_needed`, LLM tab should show:

```text
what failed
why it failed
what was expected
suggested recovery actions
user input area
link to Trace details
```

Recovery should not hide failure evidence.

---

## 6. Steps tab

The Steps tab is for scoped, user-guided automation.

It supports:

```text
add focused steps
pick element/section
edit intent
set expected outcome/postcondition
manage test data
inspect locator status
improve/revalidate locator
reorder/delete/duplicate steps
run selected/all steps through LLM planning
```

### 6.1 Step card fields

Each step card should show:

```text
step order
intent
selected target/section summary
locator status
expected outcome
postcondition
required page state
warnings
status badge
```

### 6.2 Step editing actions

User can:

```text
add step before/after
add step at end
delete step
move/reorder step
duplicate step
edit step intent
edit expected outcome/postcondition
attach/pick element
attach/pick section
add test data reference
```

### 6.3 Step identity rule

Frontend must not treat display order as identity.

```text
step_id is stable
step_order changes when reordered
```

### 6.4 Dependency warnings

When the user reorders/deletes/edits steps, backend may emit:

```text
dependency_warning
blocking_error
plan_invalidated
```

UI should show warnings inline on affected steps.

Example:

```text
This change may break the flow. Step 4 requires the result page, but the step that navigates to the result page was moved after it.
```

Possible user actions:

```text
Undo
Continue anyway if allowed
Ask LLM to adjust dependencies
Recalculate plan
```

### 6.5 Expected outcome/postcondition UI

Each action step should capture what should happen next.

Options:

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

For stronger reliability, allow postcondition details:

```text
URL contains /result
heading visible: Analysis Results
modal title equals Checkout
success toast contains Saved
```

### 6.6 Locator state in Steps tab

Each step/operation should show compact locator state:

```text
Locator: getByRole('button', { name: 'Get started' })
Status: validated / ambiguous / fragile / stale / not validated
Scope: hero section
Confidence: high / medium / low
```

Actions:

```text
Revalidate
Improve
Change scope
View candidates
Use LLM
```

### 6.7 Locator update page-state behavior

If the user requests locator update but browser is on the wrong page, UI should show:

```text
This step belongs to: <required page/state>
Current browser page: <current page/state>
Live validation is unavailable until page state matches.
```

Actions:

```text
Navigate to required page
Replay dependency steps
I moved browser manually, recheck
Use stored snapshot only
Cancel
```

### 6.8 Run from Steps tab

When the user clicks Run LLM / Run selected / Run all:

```text
Steps tab sends structured pending steps
backend enters planning
UI should focus or switch to LLM tab if clarification/plan review is needed
Steps tab keeps step-level status badges
```

---

## 7. Recorded tab

The Recorded tab shows what actually happened and what was recorded.

It is evidence/history, not draft intent.

### 7.1 Recorded step card

Each recorded parent step should show:

```text
recorded step title
source step id / plan id if useful
status
precondition
postcondition
expected outcome
observed outcome
child operations
locator details
code snippet
replay status
repair status
```

### 7.2 Child operation display

Each child operation should show:

```text
operation type
locator used
assertion/value if applicable
status
observed result
code line
```

### 7.3 Recorded actions

Actions:

```text
Replay step
Replay all
Copy step code
Inspect details
Repair locator
Improve locator
```

### 7.4 Immutable evidence rule

Recorded steps are not silently mutated.

If repair/update happens, UI should show:

```text
new version
repair applied
previous version available
```

---

## 8. Code tab

The Code tab shows generated Playwright code.

### 8.1 Code display

Should show:

```text
full generated spec preview
latest code_update
source recorded steps
warnings
```

### 8.2 Code actions

Actions:

```text
Copy all
Copy selected step
Export/save
Regenerate code if backend supports it
```

### 8.3 Code warnings

Show clear warnings:

```text
fragile locator used
unsupported capability skipped
partial code generated
recorded step missing code_update
```

---

## 9. Trace tab

Trace tab is the observability workspace.

It must not be raw terminal spam.

### 9.1 Trace sections

Trace should include:

```text
event timeline
LLM calls and token estimates
context policy used
locator decisions
permission decisions
precondition checks
failures and recoveries
artifacts/screenshots/log paths
backend/frontend connection status
```

### 9.2 Trace filters

Filters:

```text
Errors
LLM calls
Locators
Permissions
Recovery
Codegen
Replay
WebSocket
```

### 9.3 Failure detail view

For each failure, show:

```text
what failed
where it failed
expected
actual
evidence
attempted recoveries
next allowed actions
artifact links
```

---

## 10. Negative and edge-case UI requirements

### 10.1 Backend/API/LLM failures

If backend is down, API key missing, API key invalid, browser launch failed, or LLM provider times out:

Show global blocking error with:

```text
what failed
what user can do
retry action
Trace details
```

### 10.2 Over-broad request

For requests like:

```text
Test everything on this website.
```

Show scope clarification options:

```text
current page
selected section
one user journey
forms only
CTAs only
```

### 10.3 Conflicting instruction

For conflicts like:

```text
Validate the result page but do not submit the form.
```

Show conflict explanation and options.

### 10.4 Long-running operation

Show:

```text
waiting condition
elapsed time
timeout threshold
cancel/extend wait if supported
```

### 10.5 LLM schema failure

Show:

```text
Retrying model response...
```

If still failing:

```text
Could not produce valid plan/change.
Try again
Edit instruction
View trace
```

### 10.6 WebSocket disconnect / page navigation

Show:

```text
Reconnecting...
Run preserved / Run lost
```

### 10.7 Recorded succeeded but code failed

Show:

```text
Recorded successfully
Code generation failed
Retry code generation
View trace
```

---

## 11. Backend event to UI destination mapping

| Backend event/state | Primary UI destination | Secondary UI destination |
|---|---|---|
| runtime_config_error | Global header / LLM | Trace |
| status / phase_update | Global header | Trace |
| conversation_state | LLM | Trace |
| clarification_needed | LLM | Steps if target step exists |
| permission_required | LLM | Trace |
| page_analysis_started | LLM | Trace |
| recommendation_ready | LLM | Trace |
| plan_ready | LLM | Steps if created from steps |
| plan_diff_proposed | LLM | Trace |
| plan_invalidated | LLM / Steps | Trace |
| steps_updated | Steps | Trace |
| dependency_warning | Steps | LLM if user action needed |
| locator_ambiguous | Steps / LLM | Trace |
| locator_update_result | Steps | Trace |
| precondition_failed | Steps / LLM | Trace |
| execution_started | Global header / LLM | Trace |
| operation_started | Global compact activity | Trace |
| operation_failed | LLM | Trace |
| recovery_needed | LLM | Trace |
| step_recorded | Recorded | Steps, Code, Trace |
| code_update | Code | Recorded, Trace |
| replay_started/result | Recorded | Trace |
| capability_gap_recorded | LLM / Recorded | Trace |
| run_completed | Global header / Recorded | Code, Trace |

---

## 12. Frontend implementation principles

```text
Frontend renders typed backend state.
Frontend does not decide lifecycle truth.
Frontend does not infer completion from LLM prose.
Frontend actions become typed backend commands.
Frontend must show clear next action for blocking states.
Frontend must separate draft steps, confirmed plan, and recorded evidence.
Frontend must support stable test selectors/data-testid hooks.
Frontend should reuse current visual style where possible.
```

---

## 13. Required testability improvements

The current React UI has few/no stable data-testid hooks.

Add stable hooks for:

```text
tab buttons
LLM chat input
plan card
confirm plan
correction input
clarification card
permission card
recovery card
step card
locator status
improve locator
revalidate locator
recorded step card
replay button
code preview
trace event row
```

E2E tests should not rely only on fragile CSS/classes or changing text.

---

## 14. Open questions before implementation

```text
1. Should Run Pending Steps auto-switch to LLM tab every time, or only when plan/clarification appears?
2. Should Save/Load live in global footer, Code tab, or Recorded tab?
3. Should plan direct-edit UI be enabled in V1, or only natural language correction first?
4. Should permission mode be global setting, per-run setting, or both?
5. Should locator candidate preview highlight candidates on the live page?
6. Should Trace tab store only current run or session history?
7. Should Recorded tab show previous repaired versions immediately in P0 or defer to P1?
```

