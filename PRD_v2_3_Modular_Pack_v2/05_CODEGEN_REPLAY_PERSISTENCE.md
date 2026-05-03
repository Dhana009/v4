# 05 — Codegen, Replay, and Persistence

> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance.


## v2.3 recording model

A recorded step is a parent object representing user intent. It may contain one or more child operations.

```json
{
  "step_id": "step_1",
  "intent": "assert hero text and click Get started",
  "status": "recorded",
  "children": [
    {
      "operation_id": "op_1",
      "type": "assert",
      "locator": "get_by_text(...)",
      "assertion": "has_text",
      "expected": "Playwright enables...",
      "status": "recorded",
      "code_lines": ["await expect(...).toContainText(...)"]
    },
    {
      "operation_id": "op_2",
      "type": "click",
      "locator": "get_by_text('Get started')",
      "status": "recorded",
      "code_lines": ["await page.getByText('Get started').click()"]
    }
  ]
}
```

### Expected criteria

- Multi-action user intent is not flattened into an opaque single card.
- Replay can target parent step or child operation.
- Codegen can produce one or more lines per child operation.
- Recovery can update only the failed child operation when appropriate.


## Workspace-based storage rule

User-facing outputs save under the active workspace by default, not hardcoded `.hermes`.

Default examples:

```text
<workspace>/autoworkbench-output/
<workspace>/tests/generated/
<workspace>/.autoworkbench/sessions/
```

The exact folder can be configured, but the default must be relative to where the application/project is running.

Hidden internal metadata may use:

```text
<workspace>/.autoworkbench/
```

but generated specs, saved recordings, versions, and exports belong to the user’s workspace.

### Expected criteria

- Save works without forcing `.hermes/output`.
- User can choose custom folder/name.
- Session JSON and generated spec stay together unless user chooses otherwise.
- Secrets are never written to generated code or logs.


## Replay and repair contract

Replay is a backend operation, not a frontend simulation.

```text
frontend sends replay_step / replay_operation / replay_all
→ backend loads recorded step/operation
→ backend revalidates locator
→ backend executes
→ backend emits replay_result
→ if failure, backend emits recovery_needed
→ LLM repair loop runs
→ user confirms/corrects if needed
→ backend updates recorded step and code
→ user can save new version
```

### Expected criteria

- Replay failure invokes the same recovery principles as live LLM Mode.
- A repaired replay can update the recording only after successful validation.
- User can save repaired flow as a new version.
- Replay does not mutate the recording unless a validated repair is accepted.


## Locator update / replacement flow

A user can request locator replacement for one operation, one parent step, or a selected group.

Expected flow:

```text
user requests locator update
→ backend finds alternatives
→ candidates scored for stability
→ each candidate validated count == 1
→ user confirms preferred candidate or system selects best stable candidate
→ recording, locator library, and code update
```

### Expected criteria

- Old locator remains in history with reason for replacement.
- New locator is validated before activation.
- Generated TypeScript updates immediately after replacement.
- Replay uses the updated locator.


## v2.3 codegen reviewer rule

Code generation is backend-owned and deterministic first. The Codegen Reviewer Agent, defined in `07_MULTI_MODEL_ORCHESTRATION.md`, may review generated TypeScript for complex or high-risk flows, but it does not replace deterministic codegen.

Triggered when:

```text
- exporting final spec
- popup/download/iframe/network/auth code is generated
- locator replacement changes code
- replay repair modifies recorded operations
- fragile locator warning exists
```

Expected criteria:

- Recorded operation → deterministic Playwright TypeScript line remains the primary path.
- Reviewer catches invalid locator syntax or missing waits in complex flows.
- Reviewer suggestions are applied only through backend codegen rules, not copied blindly.


---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 persistence/code sections

Three levels of memory. Each serves a different purpose.

### Level 1 — Managed run memory

Scope: One agent run (one set of steps submitted in LLM Mode).

```python
run_state = {
    "messages": [],              # active LLM message window
    "history_summary": "",       # compacted prior tool history
    "step_state": {},            # pending/executing/recovery_pending/recorded/skipped
    "validated_locators": {},    # locator choices confirmed in this run
    "page_state": {},            # current URL/title/dom_version
    "unresolved_failure": None,
}
```

Used for: preserving all relevant state while preventing raw DOM/tool outputs from growing without limit. The LLM sees the current message window plus structured summaries, not unlimited raw history.

### Level 2 — Session memory (Python objects)

Scope: One session (from launch to exit)

```python
session = {
    "run_id": "...",
    "steps": [],          # recorded steps
    "current_url": "",
    "domain": "",
    "locators": {},       # locators found this session
    "page_maps": {},      # pages explored this session
}
```

Used for: step list, current state, locators found during this session.

### Level 3 — Persistent memory (files)

Scope: Across sessions

**Locator library** — `.hermes/locators/[domain].json`
```json
{
  "app.example.com": {
    "login-page": {
      "email-input":    "getByLabel('Email')",
      "password-input": "getByLabel('Password')",
      "login-button":   "getByRole('button', {name: 'Login'})"
    },
    "dashboard": {
      "heading": "getByRole('heading', {name: 'Dashboard'})"
    }
  }
}
```

When a session starts, the locator library for the current domain is injected into the LLM system prompt. The LLM reuses known locators instead of re-discovering them.

**Page maps** — `.hermes/page-maps/[domain]/[path-hash].json`
```json
{
  "url": "https://app.example.com/results",
  "explored_at": "2026-04-30T10:00:00Z",
  "sections": { ... },
  "summary": "Results page with filter bar, data table, pagination"
}
```

**Session memory** — `.hermes/memories/MEMORY.md`
```
# Memory — app.example.com

## Locator patterns that work
- Login button: getByRole('button', {name: 'Login'}) — always stable
- Email input: getByLabel('Email') — stable

## Patterns that failed
- data-testid='login-btn' changed to data-testid='btn-login' on 2026-04-15

## App behavior notes
- After login, redirects to /dashboard with 1-2s delay
- Filter bar requires waitForLoadState('networkidle') after each change
```

**Error patterns** — `.hermes/memories/error-patterns.json`
```json
{
  "Element not interactable": {
    "seen_count": 12,
    "best_fix": "scroll into view then retry",
    "success_rate": "91%"
  },
  "Timeout exceeded": {
    "seen_count": 8,
    "best_fix": "waitForLoadState networkidle",
    "success_rate": "88%"
  }
}
```

When an error occurs, the system checks error patterns first and tries the best known fix immediately.

**Auto-update after every session:**
- Confirmed locators → saved to locator library
- New fix patterns → saved to error patterns
- App behavior notes → appended to MEMORY.md

---

### One session = one output file

```
Session start:
  Backend asks (or auto-detects from first URL):
  "What are we testing today?"
  Answer → test name + file name

Auto-naming format:
  .hermes/output/[YYYY-MM-DD]-[session-name].spec.ts
  Example: 2026-04-30-login-flow.spec.ts

Session JSON (for reload/replay):
  .hermes/output/[YYYY-MM-DD]-[session-name].session.json
  {
    "name": "login flow",
    "url": "https://app.example.com",
    "date": "2026-04-30",
    "steps": [...],
    "locators": {...}
  }
```

### Save options

```
[💾 Save]
  → Saves to default auto-named location
  → .hermes/output/[date]-[name].spec.ts
  → Overwrites if file already exists

[💾 Save As]
  → User picks custom name + custom folder
  → Can save to any location on disk:
    ~/tests/smoke/login.spec.ts
    ~/projects/myapp/tests/login.spec.ts
  → Both .spec.ts and .session.json saved together
  → Panel shows save dialog:
    Name: [login-flow          ]
    Path: [.hermes/output/     ] [Browse]
    [Save] [Cancel]

[📋 Save Copy]
  → Save a copy to new location
  → Continue working on original session
  → Useful for checkpointing
```

### Load options

```
[📂 Load Recording]
  → Shows recent recordings list:
    📄 login-flow       2026-04-30  12 steps  ✅
    📄 checkout-flow    2026-04-29   8 steps  ❌
    📄 settings-update  2026-04-28  15 steps  ✅
    [Search recordings...]
    [Browse for file...]

  User can:
  → Pick from recent list (loaded from .hermes/output/)
  → Browse filesystem for any .session.json anywhere
  → Load any past recording from any location

  After load:
    Steps loaded into step panel
    Browser navigates to session's starting URL
    User decides: [▶ Replay] or [Continue adding steps]
    Steps loaded but NOT auto-executed

[📂 Load from path]
  → User types or pastes path directly:
    /load ~/Downloads/old-test.session.json
    /load ~/projects/myapp/tests/checkout.session.json
```

### Version snapshots

At any point the user can save a named version:
```
/versions → save version "before-assertions"
Later: /versions → load version "before-assertions"
Stored in SQLite — not just files
```

### Step management rules

- **Add step** → appended to list. Browser state unchanged.
- **Delete step** → removed from list only. Browser stays at current state.
- **Edit step** → modified in list. Re-validated immediately.
- **Reorder step** → reordered in list. No re-execution.
- **None of these operations re-execute in browser unless user explicitly asks.**

### Auto-save

Session auto-saves to `.session.json` after every confirmed step. If user force-quits, nothing is lost. Last state is always recoverable.

### Parallel sessions

```
Terminal 1 → session 1 → browser 1 → file 1
Terminal 2 → session 2 → browser 2 → file 2
No shared state. No interference.
```

---

| Method | How | Example |
|---|---|---|
| **Plain text in chat** | Type directly | "fill email with test@example.com" |
| **Environment variables** | `.hermes/.env` (gitignored) | "use credentials from env" → reads `TEST_EMAIL` |
| **File drop zone** | Drop file in `.hermes/uploads/` | "use the resume in uploads" |
| **JSON test data** | `.hermes/test-data/data.json` | "use user data from test data file" |
| **Direct file path** | Type path | "upload the file at ~/Documents/resume.pdf" |
| **Auto-generated (Faker)** | No data provided | "fill name field" → `faker.person.fullName()` |

**Faker behavior:**  
Agent always tells user what it generated. Never uses Faker silently.  
"I used: generated-email@example-faker.com"

**Secrets rule:**  
Values from `.env` are NEVER shown in chat, logs, or generated code.  
Generated code references env var names, not values:
```typescript
await emailInput.fill(process.env.TEST_EMAIL ?? '')
await passwordInput.fill(process.env.TEST_PASSWORD ?? '')
```

---

**User controls auth completely. Agent never touches it unless explicitly asked.**

```
FLOW 1 — First time setup:
  User logs in manually in browser
  User says: "save storage state" or /save-auth
  Agent saves:
    await context.storageState({
      path: '.hermes/auth/storageState.json'
    })
  Confirms: "Storage state saved ✅"

FLOW 2 — Every session after:
  User says: "load auth" or /load-auth
  Agent creates context with saved state:
    browser.newContext({
      storageState: '.hermes/auth/storageState.json'
    })
  Navigate → already logged in ✅

FLOW 3 — Auth expires:
  Agent detects: redirect to login OR 401 response
  Tells user: "Auth expired — please log in again"
  User logs in → agent saves new state → continues

FLOW 4 — No auth needed:
  User never mentions auth
  Agent never touches it

MULTIPLE USERS:
  .hermes/auth/admin-storageState.json
  .hermes/auth/user-storageState.json
  User specifies which to load explicitly
```

---

### Structure

```typescript
// ============================================
// Generated by Playwright Co-pilot
// Session: 2026-04-30T10:00:00Z
// App: https://app.example.com
// Test: login flow
// ============================================

import { test, expect } from '@playwright/test'

// === LOCATORS ===
// All locators defined here for easy maintenance
// Update locators here when app changes

const emailInput    = page.getByLabel('Email')
const passwordInput = page.getByLabel('Password')
const loginButton   = page.getByRole('button', { name: 'Login' })
const dashboard     = page.getByRole('heading', { name: 'Dashboard' })

// ⚠ Fragile locator — no stable attributes found
// Consider adding data-testid to this element
const submitBtn = page.locator('//form/div[3]/button')

// === TEST ===
test('login flow', async ({ page }) => {
  await page.goto(process.env.BASE_URL ?? 'https://app.example.com')
  await emailInput.fill(process.env.TEST_EMAIL ?? 'test@example.com')
  await passwordInput.fill(process.env.TEST_PASSWORD ?? '')
  await loginButton.click()
  await expect(dashboard).toBeVisible()
})
```

### Why locators at the top

- Easy to update when app changes
- Clear separation from test logic
- Standard pattern every Playwright engineer knows
- One place to fix when locators break

### Auto-generated Playwright config (if missing)

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.hermes/output',
  timeout: 30000,
  retries: 1,
  reporter: [
    ['html', { outputFolder: '.hermes/reports' }],
    ['list']
  ],
  use: {
    baseURL: process.env.BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } }
  ]
})



Below is the PRD patch to add. Do **not** implement yet. First add this section to the PRD.

---

# PRD Addendum — Expected Outcome Capture / Interaction Outcome Model

## 1. Problem

A picked element alone is not enough to create reliable automation.

Today the recorder captures:

```text
target element
action
locator
generated code
```

But it does not reliably capture:

```text
what the user expects to happen after the action
what actually happened after the action
whether the action changed page/application state
```

This causes failures in flows where one step changes the application state for the next step.

Example:

```text
Step 1: assert homepage heading
Step 2: click Get started
Step 3: assert Installation heading
```

The click in Step 2 navigates to a new page. Without capturing that expected outcome, the system may validate or replay later steps from the wrong page/state. The latest manual run showed this class of issue clearly: actions were valid, but the runtime did not have a stable model of which page/state each later step belonged to. 

This is not only a navigation issue. Real applications can change state in many ways:

```text
navigation
modal/dialog opened
dropdown/menu opened
new tab opened
toast/message shown
content changed
download started
file picker opened
iframe changed
no visible change
```

So the product needs a generic model, not one-off navigation handling.

---

## 2. Core Concept

Introduce an **Expected Outcome Capture** model.

Every meaningful interaction should be represented as:

```text
Target + Action + Expected Outcome + Observed Outcome
```

Example:

```json
{
  "target": "Get started",
  "action": "click",
  "expected_outcome": {
    "type": "navigation",
    "source": "user",
    "description": "Should go to the docs intro page"
  },
  "observed_outcome": {
    "type": "navigation",
    "before_url": "https://playwright.dev/",
    "after_url": "https://playwright.dev/docs/intro",
    "matched_expected": true
  }
}
```

---

## 3. Product Principle

The system should not force the user into heavy manual entry, but it should collect critical expected-outcome information when the action is likely to change application state.

### Required for click actions

For `click`, expected outcome should be required before the step is finalized.

Reason:

```text
click is the highest-risk action because it commonly changes state
```

### Optional for non-click actions

For actions like `assert`, `fill`, `select`, expected outcome should be optional but supported.

Reason:

```text
these actions may still change state, but not always
```

---

## 4. Frontend UX Requirement

When a user picks an element or adds an interaction, show an **Expected Outcome** section.

### For click actions

Show:

```text
After clicking this, what should happen?
```

Quick options:

```text
Navigate to another page
Open modal/dialog
Open dropdown/menu
Open new tab
Show toast/message
Change page content
Start download
Open file picker
No visible change
Not sure / let agent detect
```

Also provide an optional text field:

```text
Expected outcome details
```

Examples:

```text
Should go to /docs/intro
Should open the login modal
Should show success message
Should open the country dropdown
```

### For non-click actions

Show the same field as optional.

---

## 5. Backend Data Model

Each pending/recorded step should support:

```json
{
  "expected_outcome": {
    "type": "navigation | modal | dropdown | new_tab | toast | content_change | download | file_picker | no_visible_change | not_sure",
    "description": "optional user-provided detail",
    "source": "user | inferred | unknown",
    "required": true
  }
}
```

Each executed operation may later include:

```json
{
  "observed_outcome": {
    "type": "navigation | modal | dropdown | new_tab | toast | content_change | download | file_picker | no_visible_change | unknown",
    "before_url": "...",
    "after_url": "...",
    "before_title": "...",
    "after_title": "...",
    "evidence": [],
    "matched_expected": true
  }
}
```

Do not store full DOM snapshots in the step payload. Store compact evidence only.

---

## 6. Runtime Behavior

For each action execution:

```text
1. Capture compact before-state
2. Execute action
3. Wait for page/app to settle
4. Capture compact after-state
5. Classify observed outcome
6. Compare expected_outcome vs observed_outcome
7. Store observed_outcome with the operation
```

Compact state may include:

```text
url
title
page/tab count
visible dialog candidates
visible menu/listbox candidates
visible toast/alert/message candidates
top headings
small DOM signature
```

---

## 7. Replay Behavior

Replay should not only execute actions. It should also validate expected outcomes.

Replay flow:

```text
1. Restore starting page/state where possible
2. Replay operation
3. Wait for expected outcome
4. Compare observed outcome
5. Continue only when outcome is satisfied
```

Examples:

```text
expected_outcome = navigation
→ wait for URL/title/page state change

expected_outcome = modal
→ wait for visible dialog/modal

expected_outcome = dropdown
→ wait for menu/listbox/options

expected_outcome = toast
→ wait for visible toast/message

expected_outcome = not_sure
→ use current replay behavior
```

---

## 8. Repair Behavior

If replay or execution sees a mismatch:

```text
expected: modal opened
observed: navigation occurred
```

then repair context should include:

```text
expected_outcome
observed_outcome
mismatch reason
operation metadata
current browser state
```

The LLM should repair using this information instead of guessing from locator/code alone.

---

## 9. Save Snapshot Behavior

Save snapshots must serialize:

```text
expected_outcome
observed_outcome
outcome mismatch status if any
```

This is required for future:

```text
Replay Repair
Save Repaired Version
Artifact Versioning
```

---

## 10. MVP Scope

### Expected Outcome Capture v1

Implement only the smallest useful version:

```text
1. Add expected_outcome to pending step model.
2. Add frontend expected-outcome input/chips.
3. Require expected_outcome for click actions.
4. Store expected_outcome in plan_ready / step_recorded / save snapshot.
5. Include expected_outcome in LLM context.
6. Do not require full observed_outcome detection yet.
```

### v1 supported outcome types

```text
navigation
modal
dropdown
new_tab
toast_or_message
content_change
download
file_picker
no_visible_change
not_sure
```

### v1 replay usage

For v1, replay should at least use:

```text
navigation → restore start URL and/or wait for URL/title change
not_sure → current behavior
```

Other types can be stored first and used by later detection.

---

## 11. Out of Scope for v1

Do not implement in v1:

```text
perfect modal/dropdown/toast detection
full DOM diff storage
cross-browser state persistence
multi-tab repair
download/file upload repair
visual comparison
branching repaired snapshot versions
```

---

## 12. Acceptance Criteria

Expected Outcome Capture v1 is complete when:

```text
1. Click steps require expected_outcome before final add/confirm.
2. Non-click steps can optionally store expected_outcome.
3. expected_outcome is present in backend pending-step state.
4. expected_outcome appears in plan/record/step payloads where relevant.
5. expected_outcome is saved in spec snapshot.
6. LLM prompt/context includes expected_outcome.
7. Existing single-action and multi-action flows still pass.
8. Replay All has enough data to know the intended state transition for click steps.
```

---

## 13. Implementation Order

```text
1. Add expected_outcome data model.
2. Add frontend capture UI.
3. Require it for click actions.
4. Pass it through backend planning/recording.
5. Save it in snapshot.
6. Add LLM instruction to use expected outcome and avoid guessing.
7. Add basic replay usage for navigation/not_sure.
8. Later: add observed_outcome capture.
```

PRD Addendum — Replay Precondition Guard v1
1. Problem

Replay cannot safely execute a recorded step only because the locator/action exists.

A recorded step belongs to a specific application state. That state may include:

URL
page title
modal open/closed state
dropdown/menu state
target element visibility
form/page content state
tab/window context
iframe context

URL alone is not enough.

Example:

Step 1: Click “Open Modal”
Expected outcome: modal opens

Step 2: Fill input inside modal
Precondition: modal is already open

Both steps may have the same URL. If the user clicks Replay Step 1 while already inside the modal, the original “Open Modal” button may not be visible or may no longer be actionable. Blind replay can fail incorrectly or falsely pass.

Therefore, replay must validate the recorded step’s precondition before executing.

2. Core Principle

Replay must prefer clear failure over false success.

If the current app state does not match the recorded precondition, replay must not blindly execute.

Replay should return a clear failure:

replay_precondition_failed

instead of pretending the step passed.

3. Replay Precondition Model

Each recorded step should support a derived or stored replay precondition.

For v1, derive it from existing recorded data:

{
  "replay_precondition": {
    "before_url": "...",
    "before_title": "...",
    "target_locator": "...",
    "target_must_be_visible": true,
    "expected_context": "page | modal | dropdown | unknown"
  }
}

In v1, this does not need to be a separate persisted field if it can be derived from:

observed_outcome.before_url
observed_outcome.before_title
locator
expected_outcome.type
4. Replay One Behavior

Replay One is diagnostic and should not auto-navigate by default.

Before replaying a single step:

1. Check current URL/title against recorded before_url/before_title when available.
2. Check target locator exists and is actionable/visible.
3. If the precondition does not match, block replay with replay_precondition_failed.
4. Do not mutate the recorded step.
5. Do not enter live recovery.

Example failure payload:

{
  "ok": false,
  "reason": "replay_precondition_failed",
  "step_id": "pending-step-...",
  "expected": {
    "before_url": "https://playwright.dev/",
    "before_title": "Fast and reliable end-to-end testing for modern web apps | Playwright"
  },
  "actual": {
    "url": "https://playwright.dev/docs/intro",
    "title": "Installation | Playwright"
  },
  "message": "Cannot replay this step from the current app state. Return to the recorded start state or use Replay All."
}
5. Replay All Behavior

Replay All is flow-level replay.

Replay All should attempt to start from the beginning of the recorded flow.

For v1:

1. Find the first recorded step.
2. If the first step has observed_outcome.before_url, navigate to that URL before replaying.
3. Replay steps in recorded archive order.
4. Before each step, validate replay precondition.
5. If a precondition fails, stop and return replay_precondition_failed.
6. Do not silently continue after a precondition mismatch.

Replay All may auto-navigate only for simple same-tab URL restoration.

Replay All must not attempt unsafe automatic recovery such as:

closing modals
opening dropdowns
resetting forms
switching tabs
repairing iframes
undoing app-side mutations

If those states are required and cannot be safely restored, Replay All should fail clearly.

6. Same-URL UI State Handling

For same-URL states like modal/dropdown/drawer:

URL match is not enough.

Replay should also validate that the target element for the step is present and actionable.

Examples:

If replaying “Open Modal” but modal is already open and the open button is not visible:
→ replay_precondition_failed

If replaying “Fill modal input” but modal is closed:
→ replay_precondition_failed

If replaying “Open dropdown” but dropdown is already open or trigger is hidden:
→ replay_precondition_failed

V1 should not attempt to fix these automatically.

7. V1 Scope

Replay Precondition Guard v1 includes:

Replay One precondition check
Replay All start URL restore for first step
Replay All per-step precondition check
target locator/actionability validation
clear replay_precondition_failed result
backend logs for pass/fail
no mutation of recorded artifacts
8. Out of Scope for v1

Do not implement in v1:

automatic modal close/open recovery
automatic dropdown state repair
new-tab restoration
iframe replay repair
form reset
auth/session reset
visual diffing
LLM replay repair
save repaired version
branching snapshot versioning
9. Acceptance Criteria

Replay Precondition Guard v1 is complete when:

1. Replay One blocks if current URL/title does not match recorded before state.
2. Replay One blocks if target locator is missing/not actionable.
3. Replay All navigates to the first step’s recorded before_url when available.
4. Replay All stops on the first precondition failure.
5. Replay All does not falsely pass when current state is wrong.
6. Same-URL modal/dropdown cases fail clearly instead of silently passing.
7. replay_precondition_failed is visible in backend result/logs.
8. recorded steps, code updates, and snapshots are not mutated by replay.
10. Short Summary
Replay Precondition Guard ensures replay starts from the correct recorded app state before executing a step. It prevents false replay success by checking URL/title and target actionability, while safely failing on unsupported same-page state mismatches like modal/dropdown conditions.

---

## Short PRD summary line

```text
Expected Outcome Capture ensures every picked interaction records not only the target and action, but also what the user expects to happen after the action. This reduces LLM guessing and provides the foundation for reliable replay and repair.
```


```

---