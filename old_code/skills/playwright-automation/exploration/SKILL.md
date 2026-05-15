---
name: playwright-exploration
description: Systematically explore pages, understand structure, reveal hidden DOM, generate page maps.
version: 1.0.0
metadata:
  hermes:
    tags: [explore, analyze, understand, map]
    category: playwright-automation
    triggers: [explore, understand page, analyze,
               what is on this page, map page,
               explore page, page structure,
               what sections, what elements,
               discover, investigate page]
---

# Playwright Page Exploration

## When This Skill Is Needed
User says "explore this page" or
"what is on this page" or
"understand the page structure".
Agent drives. User just observes.

## Phase 1 — Outer Shell Only
Do NOT go deep yet.
Get the high level structure first.

  Run browser_get_state() for current URL.
  Run dom_extract() to get all elements.
  Count elements by type:
    buttons, inputs, links, selects
  Identify major sections:
    navigation, header, main content, footer
  Note page title and URL.

## Phase 2 — One Level Deeper
For each major section identified:
  What type of elements are in it?
  Are there forms? Tables? Lists? Cards?

  Run dom_extract(scope=".section-selector")
  for each section.

## Phase 3 — Reveal Hidden DOM
Some content only appears after interaction.
Identify elements that likely reveal more:
  Buttons that say "Show", "Expand", "More"
  Accordion headers
  Tab panels
  Dropdown menus
  Modal triggers

For each: click → observe → capture → go back.
Be systematic. Not random.

  For each reveal trigger:
  1. Take screenshot before
  2. Click trigger
  3. Run dom_extract() on revealed content
  4. Take screenshot after
  5. Go back or close revealed content
  6. Continue to next trigger

## Phase 4 — Build Structured Report
Compile everything discovered.

Report structure:
  Page: [URL]
  Title: [page title]

  SECTIONS FOUND:
  [section name]:
    Interactive elements: [list]
    Hidden elements: [revealed by what]

  DYNAMIC ELEMENTS:
  [description of what reveals what]

  SUGGESTED AUTOMATION FLOWS:
  1. [flow name] — [brief description]
  2. [flow name] — [brief description]

  GAPS / NEEDS MORE EXPLORATION:
  [anything that could not be accessed]

## Saving Exploration Report
After exploration completes:

  import os
  os.makedirs(".hermes/output/exploration",
    exist_ok=True)

  Write report to:
  .hermes/output/exploration/[page-name]-map.md

## Exploration to Recording Bridge
After exploration user says:
  "Start recording the [flow name] flow"

Agent uses exploration map as context.
Already knows page structure.
Goes directly to interactive recording.
No re-exploring needed.

## Signal Mapping
"explore this page"          → run all 4 phases
"what is on this page"       → run all 4 phases
"understand the structure"   → phase 1 + 2
"reveal all hidden content"  → phase 3
"generate page map"          → phase 4 report
"explore then record [flow]" → explore then
                               bridge to recording

