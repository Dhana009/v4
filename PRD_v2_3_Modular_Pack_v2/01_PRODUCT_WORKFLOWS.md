# 01 — Product Workflows

> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance.


## v2.3 product workflow clarification

The core product is not only one LLM execution run. The complete product loop is:

```text
record flow
→ save session and generated spec
→ replay later
→ if replay breaks, LLM repairs the failing step/operation
→ user guides or confirms when needed
→ validated fix updates the recording
→ save new version
```

LLM Mode is the brain behind this loop. Manual Mode and Replay Mode should reuse the same Step Runner, Tool Runtime, Context Manager, Recovery Manager, and Codegen architecture.

## Priority order

1. Stabilize backend/frontend foundation and typed event contract.
2. Complete LLM Mode MVP.
3. Complete recording/save/replay/repair workflow.
4. Manual Mode using the same runtime and recovery layer.
5. Advanced actions, persistence hardening, page maps, and polish.

## LLM Mode daily-use scenarios

### Scenario 1 — single picked element, one action

User picks a button and says `click this button`.

Expected flow:

```text
element captured
→ locator found and validated
→ plan shown
→ user confirms
→ click executes
→ step recorded
→ code_update emitted
```

### Expected criteria

- One confirmed action becomes one recorded parent step with one child operation.
- The locator resolves to exactly one element before execution.
- The UI shows plan, execution status, recorded result, and generated code line.


### Scenario 2 — single picked element, assertion

User picks a heading and says `assert this text exists`.

Expected flow:

```text
selected element descriptor
→ expected text preview
→ locator validation
→ plan confirmation
→ normalized text assertion
→ recorded assertion
→ generated expect(...) line
```

### Expected criteria

- Text assertions normalize `&nbsp;`, child span text, whitespace, and control characters.
- The user sees the expected text before execution when the text is derived from DOM.
- Duplicate matching elements are resolved before recording.


### Scenario 3 — selected section, multiple actions/checks

User selects a section/container and says `validate this section and click the CTA`.

Expected model:

```text
Parent recorded step: Validate selected section and open CTA
  ✓ assert heading text
  ✓ assert CTA visible
  ✓ click CTA
```

The LLM must decompose broad intent into ordered child operations. The user confirms/corrects the proposed plan before any operation executes.

### Expected criteria

- A multi-action intent is represented as one parent step with child operations/checks.
- The plan card shows child operations in order before execution.
- The user can correct the order before execution.
- Codegen expands child operations into separate Playwright lines.


### Scenario 4 — multiple queued steps

User builds a queue:

```text
Step 1: assert homepage heading
Step 2: click Get started
Step 3: assert docs page heading
```

Expected flow:

```text
Run All
→ Step Runner processes steps in order
→ each step gets pending/executing/recorded/failed/skipped status
→ navigation invalidates stale DOM
→ next step uses current page context
```

### Expected criteria

- Recorded steps do not rerun unless replay is explicitly requested.
- A navigation/click that changes page state forces revalidation or replanning for later operations.
- Step state survives recovery and correction.


### Scenario 5 — correction before execution

If the LLM proposes the wrong plan order, user sends correction.

Expected flow:

```text
plan_ready
→ user sends correction
→ old plan discarded
→ revised plan shown
→ user confirms revised plan
→ only corrected plan executes
```

### Expected criteria

- Confirm means accept plan.
- Send Correction means reject/modify plan.
- Old plan never executes after correction.
- The UI mode remains `plan_review` until the revised plan is confirmed.


### Scenario 6 — correction during recovery

If execution fails, the LLM diagnoses and asks for user guidance only when needed.

Expected flow:

```text
tool/action fails
→ recovery_needed
→ LLM explains concise cause and next options
→ user gives recovery instruction
→ agent continues from current browser state
→ fixed operation is recorded or step is skipped
```

### Expected criteria

- Agent never finalizes while a failed step is unresolved.
- Recovery stays anchored to the original failed step unless user explicitly changes intent.
- User sees what failed, what was tried, and what help is needed.


### Scenario 7 — replay repair

User loads an older recording and clicks replay.

Expected flow:

```text
load session
→ replay recorded steps
→ broken locator/action detected
→ LLM repair loop starts
→ user confirms/corrects if needed
→ repaired step updates recording and code
→ save new version
```

### Expected criteria

- Replay failure triggers the same recovery architecture as LLM Mode execution.
- The user can save repaired recording as a new version.
- Old locator/action history is retained for traceability.


### Scenario 8 — locator update / replacement

User says `do not use this CSS locator; find a more stable locator`.

Expected flow:

```text
locator update request
→ alternatives generated and scored
→ each candidate validated count == 1
→ user confirms selected replacement
→ recorded step, locator library, and code update
```

### Expected criteria

- User can replace locator for one step, one child operation, or selected group.
- Old locator remains in history.
- New locator must validate exactly one element before becoming active.
- Generated code and replay use the updated locator.


### Scenario 9 — missing capability

User asks for a capability that is not yet implemented.

Expected behavior:

```text
agent detects missing capability
→ explains limitation clearly
→ records capability gap under active workspace
→ continues any supported parts if safe
```

### Expected criteria

- The agent never fakes unsupported behavior.
- Capability gaps are saved under the active workspace, not a hardcoded global folder.
- Gap entry includes user intent, URL, missing capability, available tools, and suggested future work.


### Scenario 10 — destructive/external-impact action

Examples: delete user, send email, submit payment, publish, checkout.

### Expected criteria

- Destructive or external-impact actions require an extra explicit confirmation gate.
- The plan clearly labels the destructive operation before execution.
- The operation is not executed merely because it appears inside a broad instruction.


---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 product/mode sections

Automation testers waste enormous time on things that should be automatic:

| Problem | Impact |
|---|---|
| **Intent Communication** | No reliable way to express intent clearly. Natural language is ambiguous. No structured way to point at what you mean on the page. |
| **Intent vs Reality Mismatch** | System interprets what user said but does not ground it against what actually exists in the DOM. Acts on assumptions, not reality. |
| **Locator Quality** | Finding *a* locator is easy. Finding the *right* one — stable, unique, resilient to page changes — is the actual hard problem. |
| **Locator Validation Gap** | No way to know if a locator works until execution fails. No real-time feedback between "found" and "confirmed working." |
| **No Interactive Recovery** | When something breaks, the only option is restart. No way to fix, correct, or continue in place. |
| **Uncontrolled Execution** | System wanders, makes assumptions, loses track of the original goal without checkpoints. |
| **Unusable Output** | Final generated code needs cleanup before it is actually useful. Not directly runnable. |

**The goal:** Reduce human effort to the minimum. Human tells the system what to test. System figures out how, validates it, fixes failures, and produces clean runnable Playwright TypeScript. Human stays in control but does none of the mechanical work.

---

**An AI-powered browser automation co-pilot for Playwright automation testers.**

The user opens a browser, points at things on the page, describes what they want, and the system produces clean, validated, directly runnable Playwright TypeScript test scripts.

Two modes. One output. Zero mechanical work for the human.

### Core principles

- **Human effort is minimized, not eliminated.** Human tells what. System figures out how.
- **Everything is live.** Browser is always open. Every locator is validated against the real DOM right now.
- **LLM is intelligence, not a crutch.** Programmatic solutions first. LLM only when code cannot solve it.
- **Never crash. Always recover.** Failures trigger the recovery loop. Browser never closes.
- **Output is immediately usable.** Generated TypeScript runs with `npx playwright test`. No cleanup needed.

---

### Mode 1 — Manual Mode

**Who uses it:** User who wants precise, predictable control over every action.

**How it works:**
```
User activates Pick tool
        ↓
User clicks element on page
        ↓
System captures element descriptor
  (tag, id, role, aria-label, text, parent, siblings)
        ↓
System runs locator waterfall immediately (programmatic, no LLM)
        ↓
Panel shows: best locator found + confidence score
User sees element highlighted on page
        ↓
User selects action from dropdown
  (all Playwright actions available — see Section 8)
User enters value if needed
        ↓
System validates immediately:
  Executes action against live browser
  Checks result
        ↓
PASS → step appended to session
FAIL → LLM kicks in for THIS problem only:
  Sends: element snapshot + error + what was tried
  LLM suggests fix
  System tries fix
  Still failing → recovery loop (see Section 10)
        ↓
Step confirmed → code view updates live
```

**Key distinction:** In Manual mode, the LLM is only called when something fails. The human explicitly chose every action. The LLM is the repair mechanic, not the driver.

**Special case handling in Manual mode:**  
The system detects special cases from the action chosen and element context, and handles them automatically:

| User action | System detects | System does automatically |
|---|---|---|
| Click on element that triggers popup | popup/dialog skill | Registers `page.on('dialog')` handler BEFORE click |
| Click on link that opens new tab | new tab skill | Sets up `context.waitForPage()` BEFORE click |
| Upload action | upload skill | Selects correct upload strategy (input/chooser/drag) |
| Click inside iframe | iframe skill | Enters frame context first |
| Select from dynamic dropdown | dropdown skill | Click trigger → wait for options → click option |

User does not need to know any of this. They just pick the action. The system handles the complexity.

---

### Mode 2 — LLM Mode

**Who uses it:** User who wants to describe intent in plain English and let the system figure out everything.

**How the user builds steps — the multi-element flow:**

In LLM mode, the user builds a step list BEFORE hitting run. Each step can optionally have an element picked for context. This is the key workflow:

```
BUILDING PHASE (before hitting Run):

User adds Step 1:
  (Optional) Click [🔍 Pick] → click element on page
  Panel shows picked element as context
  User types intent in the step input:
    "click this login button"
  [+ Add Step] — step added to queue, NOT executed yet

User adds Step 2:
  (Optional) Click [🔍 Pick] → click different element
  User types intent:
    "fill this email field with test@example.com"
  [+ Add Step]

User adds Step 3:
  No element picked (not always needed)
  User types intent:
    "assert the dashboard heading is visible"
  [+ Add Step]

User adds Step 4:
  User types multi-action intent (no element needed):
    "go to the results page, explore all sections,
     and add assertions for every visible heading
     and every data count badge"
  [+ Add Step]

Step queue now shows:
  1. [🔵 Login button] "click this login button"
  2. [🔵 Email field]  "fill email with test@example.com"
  3. [no element]      "assert dashboard heading is visible"
  4. [no element]      "explore results page, add assertions..."

User reviews the queue. Can:
  - Edit any step's intent text
  - Re-pick the element for any step
  - Delete any step
  - Reorder steps

User clicks [▶ Run All]
        ↓
LLM Agent Loop starts — processes ALL steps in sequence
```

**The step input UI in LLM mode:**

```
┌──────────────────────────────────────────────────┐
│ LLM MODE — Build your steps                      │
├──────────────────────────────────────────────────┤
│ [🔍 Pick element] (optional — gives LLM context) │
│ Selected: Login button (button#login-btn)         │
│                                                  │
│ What should happen with this?                    │
│ [click this login button               ]         │
│                                                  │
│ [+ Add Step]                                     │
├──────────────────────────────────────────────────┤
│ STEP QUEUE:                                      │
│ 1. 🔵 Login btn  "click this login button"  [✏️🗑] │
│ 2. 🔵 Email fld  "fill email with test@..."  [✏️🗑] │
│ 3.    —          "assert dashboard visible" [✏️🗑] │
│ 4.    —          "explore results page..."  [✏️🗑] │
│                                                  │
│ [▶ Run All]  [Clear Queue]                       │
└──────────────────────────────────────────────────┘
```

**Element context is optional — the LLM decides when it needs it:**
- Simple action + picked element → LLM uses element data directly for locator
- Complex intent + no element → LLM explores the page to find what it needs
- Page-level intent (explore, assert all, etc.) → element not needed at all

**How it works after [Run All]:**
```
LLM Agent Loop starts:

  STEP 1: Context Manager builds prompt context
    Load compact core rules
    Load skill index always
    Load compact skill summaries for relevant intents
    Load full skill details only when needed
    Load validated locator library for this domain
    Load page map if fresh and relevant
    Load compact run/session memory
        ↓
  STEP 2: Build managed LLM input
    [system]: persona + hard rules + selected skill depth
    [context]: step state + current page state + validated locators
    [user]: queued steps with element data + intent text
    [history]: compact summary of prior tool results, not raw full history
        ↓
  STEP 3: The loop
    LLM processes steps one by one
    For each step:
      finds locator (uses element data if provided)
      handles special cases (popups, iframes, tabs)
      executes action
      validates result
      appends to messages[]
    If step fails → recovery loop
    If genuinely stuck → asks user ONE question
    Continues until all steps complete
        ↓
  STEP 4: Output
    All steps validated
    TypeScript generated
    Locator library updated
    Memory updated
    Panel shows results
```

**The LLM persona:**  
The LLM does not behave as a generic assistant. It has a specific persona baked into the system prompt:

```
You are a senior Playwright automation engineer with deep expertise in:
- Finding stable, resilient locators for any element on any page
- Handling every Playwright edge case: iframes, popups, new tabs,
  dynamic dropdowns, file uploads, SPAs, shadow DOM
- Writing clean, maintainable TypeScript test scripts
- Understanding what QA engineers actually need to test
- Interpreting natural language test descriptions precisely

When you receive a test intent:
1. Think like a QA engineer: what is the user actually trying to verify?
2. Use the element data and DOM context to find the best locator
3. Handle all edge cases proactively (popups, waits, frames)
4. If the intent is unclear, ask ONE specific clarifying question
5. Never assume and proceed wrong
6. Suggest assertions the user may have missed
7. Always produce clean, directly runnable TypeScript

You have access to tools. Use them. Do not just describe what to do — do it.
```

**LLM Mode exploration example:**
```
User step: "Go to this results page and explore all sections.
            Understand the layout. Then suggest assertions."

LLM actions:
  1. Calls dom_snapshot(scope="full_page")
  2. Calls page_map_read(url=current_url) — check if already explored
  3. If not cached: systematically reads each section
  4. Sends back to panel:
     "I found 4 sections:
      1. Header — title, export button, breadcrumb
      2. Filter bar — 6 filter inputs, reset button
      3. Results table — 8 columns, pagination
      4. Footer — count badge, total value
      
      Suggested assertions:
      - Header title is visible and not empty
      - Filter bar has exactly 6 inputs
      - Table has at least 1 row
      - Count badge contains a number (not zero)
      - Export button is enabled
      
      Want me to add these?"
        
User: "Yes, add those. Also assert the URL contains /results"

LLM: generates all assertions with validated locators
     adds to step list
     shows code preview
```

---