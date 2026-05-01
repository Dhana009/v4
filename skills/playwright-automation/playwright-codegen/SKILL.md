---
name: playwright-codegen
description: Generate clean Playwright TypeScript test scripts from recorded steps. Single file output.
category: playwright-automation
tags: [codegen, recording, step-recording, overlay, test-generation]
triggers:
  - User provides element data from codegen/recording
  - User provides natural language intent + selected element (JSON)
  - Multi-step test combining assertions and actions in one request
  - Step-by-step recording workflow on a page
  - Building a test script from interactive exploration
---

# Playwright Codegen — Step Recording Workflow

Records test steps from live browser interaction and generates clean Playwright TypeScript output.

## Intent-to-Plan Workflow (Natural Language Intents)

When the user provides a **natural language intent** (e.g. "assert the text and click the button") along with a selected element JSON, follow this **analysis-first** workflow BEFORE generating a plan.

### Phase 1: Analyze Intent & Element

1. **Read the selected element** — Check `tag`, `class`, `text`, `href`, `role`, `aria_label`
2. **Read the user's intent** — Understand what they want to do (assert? click? fill? select?)
3. **Check for ambiguity** — If the selected element is a **structural container** (`<div>`, `<section>`, `<header>`, `<main>`, `<article>`) and the intent mentions an action on a different kind of element ("click the button" on a `div` container), the target is likely **inside** the container, not the container itself.

### Phase 2: Inspect Containers

When the selected element is a container and the intent is ambiguous:

1. Call `dom_extract(scope="<container-selector>")` to list all interactive children inside the container
2. Review the returned elements — look for `<a>`, `<button>`, `<input>`, `<select>` tags that match the user's intent
3. Identify the most likely target based on context (e.g., "Get started" CTA is usually the primary button)

### Phase 3: Clarify Ambiguous Intents (Limit to 1–2 Rounds)

If after inspection the target is still unclear, ask **ONE focused question** using the clarification overlay:

**⚠️ Limit clarification to 1–2 rounds max.** After that, proceed with your best judgment using the available information. Repeatedly asking the same user the same question is counterproductive.

**Heuristics for when the user says "click this" / "click the button" on a container:**
- The user selected a container (`<div>`, `<section>`) and wants you to click something inside it
- Identify the **primary call-to-action** — typically the most prominent interactive element (largest `a`/`button` with CTA text like "Get started", "Sign up", "Learn more")
- Do NOT ask "which one" — inspect with `dom_extract` and proceed with the CTAs
- The user's "click this" means "the clickable thing inside the thing I selected, figure it out"

```javascript
send_to_overlay(
  message_type="clarification_needed",
  payload={
    "question": "<single focused question>",
    "options": ["<option 1>", "<option 2>", "<option 3: Let me inspect>"]
  }
)
```

Rules:
- Ask at most one question per round
- Never repeat the same question
- Provide concrete options when possible (e.g., list the buttons found by `dom_extract`)
- Never execute actions during this phase

### Phase 4: Generate the Plan

Once the intent is clear, build a **multi-step plan** using `plan_ready`:

```javascript
send_to_overlay(
  message_type="plan_ready",
  payload={
    "summary": "I will:\\n1. Assert the hero text is visible\\n2. Click the \\\"Get started\\\" CTA button",
    "steps": [
      {
        "number": 1,
        "action": "assertion",
        "element_name": "<human-readable name>",
        "locator": "",
        "code": "await expect(page.getByText('...')).toBeVisible();"
      },
      {
        "number": 2,
        "action": "click",
        "element_name": "<human-readable name>",
        "locator": "",
        "code": "await page.getByRole('link', { name: '...' }).click();"
      }
    ],
    "instruction": "Type /go to execute this plan"
  }
)
```

For multi-step plans:
- List each step with a number, action type, element name, and clean TypeScript code
- Use robust locator strategies: prefer `getByRole`, `getByText`, `getByTestId` over raw CSS
- The `locator` field stays empty in the plan — it will be populated during execution
- After the user types `/go`, proceed to the execution phase below

## Workflow

When the user provides element data from codegen (a JSON blob with `tag`, `text`, `class`, `bounding_box`, `scoped_html`, etc.), follow this sequence:

### 1. Inspect the element data

The element JSON typically contains:
- `tag` — HTML tag name
- `text` — visible text content
- `class` — CSS class(es)  
- `id`, `role`, `aria_label`, `data_testid`, `data_cy`, `data_qa` — attribute hints
- `bounding_box` — `{x, y, w, h}` coordinates
- `parent_tag`, `parent_id` — parent context
- `scoped_html` — raw HTML snippet for context

Determine the intended action from the user's instructions:
- **Assert presence/visibility** → `action_assert` with `visible`
- **Click** → `action_click`
- **Fill text** → `action_fill`
- **Select option** → use dedicated dropdown skill

### 2. Find a stable locator

Use `locator_find` with key element data fields:

```
element_data = {"tag": "...", "text": "...", "class": "...", "parent_tag": "..."}
locator_find(element_data)
```

The tool returns the best locator strategy (prefers `get_by_role`, `get_by_test_id`, `get_by_text`, then CSS fallback).

### 3. Validate the locator

Always run `locator_validate` before using:

```
locator_validate(locator="get_by_text(\"...\", exact=False)")
```

Confirm: `valid: true`, `count: 1`.

### 4. Execute the action

Use the appropriate action tool:

| Intended action | Tool | Example |
|---|---|---|
| Assert visible | `action_assert` with `assertion: "visible"` | `action_assert(locator="...", assertion="visible")` |
| Click | `action_click` | `action_click(locator="...")` |
| Fill | `action_fill` with `value` | `action_fill(locator="...", value="text")` |

### 5. Send overlay messages

After successful execution, send **two** overlay messages:

**Step recording:**
```
send_to_overlay(
  message_type="step_recorded",
  payload={
    "step_number": <int>,
    "action": "<action_name>",
    "element_name": "<human-readable element name>",
    "locator": "<locator string>",
    "generated_line": "<TypeScript line>"
  }
)
```

**Code update:**
```
send_to_overlay(
  message_type="code_update",
  payload={
    "new_line": "<TypeScript line>",
    "step_number": <int>
  }
)
```

### Generated TypeScript patterns

| Action | Generated line |
|---|---|
| Assert visible | `await expect(page.{locator}).toBeVisible();` |
| Click | `await page.{locator}.click();` |
| Fill | `await page.{locator}.fill("{value}");` |

The locator method depends on strategy:
- `get_by_text("text", exact=False)` → `page.getByText("text", { exact: false })`
- `get_by_role("link", {name: "..."})` → `page.getByRole("link", { name: "..." })`
- `get_by_test_id("...")` → `page.getByTestId("...")`

## Pitfalls

- **Always validate after finding** — `locator_find` may return a brittle locator. `locator_validate` catches this.
- **Partial vs exact text** — `exact=False` is safer for elements that may have surrounding whitespace or hidden characters (e.g. `&nbsp;`). Only use exact when you need to distinguish similar elements.
- **Overlay order matters** — send `step_recorded` before `code_update`. The overlay UI expects recording metadata first.
- **Check `browser_get_state` first** — confirm the page URL matches what the element came from. The browser may have moved since the element was captured.
- **Scoped HTML is diagnostic** — use it to understand element context, not to build locators. Never hardcode CSS paths from scoped HTML.
- **`action_assert` auto-retries** — it's already wrapped in Playwright's auto-waiting. No need for additional waits.
- **Don't over-clarify** — Limit clarification rounds to 1–2 max. If the user says "click this" while a container is selected, inspect the container and act on the primary CTA. Repeated questions frustrate the user and waste time. When the user gives the same answer twice (e.g., repeating "click this" or re-stating their original intent), that's a signal to stop asking and proceed with your best judgment.
- **`locator_find` may return child-element text locators** — When the input element is a structural container (`<div>`, `<section>`, `<header>`, etc.), `locator_find` matches text from descendant elements, not the container itself. The returned locator (e.g., `get_by_text(...)`) targets a child, not the container you're trying to assert. Always review the returned strategy: if it's text-based and your element is a container, prefer a structural CSS selector like `parent_tag .class_name` to target the container directly. Validate with `locator_validate` before use.
- **Multi-step intents on containers** — When a user says "assert the text and click the button" on a container element, the two targets are different: the text is in the container, the button is a child inside it. Do NOT try to find one locator for both. Plan two separate steps (assert → click) with independent locators.
- **Don't assume the button** — When the selected element is a container and the intent is "click the button", use `dom_extract` first. The container may contain multiple interactive elements (e.g., "Get started", language tabs, social links). Never guess — extract and present options.
- **Clarify once, then act** — Ask at most one clarification question per round. If the answer resolves the ambiguity, proceed to plan generation. If not, ask one more follow-up. Never loop indefinitely.

## Verification

After each step:
1. `action_assert(locator, "visible")` passed without timeout
2. Both overlay messages returned `{"sent": true}`
3. Step number increments correctly in payloads
