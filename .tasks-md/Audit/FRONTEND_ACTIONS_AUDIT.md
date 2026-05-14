# Frontend Actions Audit — Every button/action in production v4

**Date:** 2026-05-14
**HEAD:** `09bcd53`
**Reference:** `yui (1)/v4/` + `1AutoWorkbench — print.pdf`
**Scope:** every clickable surface in v4 production; verify wiring end-to-end.

This is the **systematic-debugging Phase 1** companion to `FRONTEND_DESIGN_AUDIT.md`. The design audit checked structure / styling. This one checks behavior: does every button do what it advertises?

## Status legend

- ✅ **WORKS** — onClick wired, handler reaches backend or local state correctly
- ⚠️ **BROKEN** — onClick wired but downstream wiring incomplete, click does not produce expected effect
- 💀 **DEAD** — no onClick at all; clicking does nothing
- ❌ **MISSING** — design has it, production does not render the control
- 🚫 **DISABLED-WITH-REASON** — intentional Sprint 7 lock (D-105/D-106/etc.)
- 🆗 **SEMANTIC-NO-OP** — clicking the already-active state legitimately does nothing

---

## A. Header (`frontend/src/v4/chrome.jsx::Header`)

### Top row

| # | Element | Source | Wiring | Status |
|---|---|---|---|---|
| H1 | Logo + "AutoWorkbench" text | `aw-brand` `aw-logo` | no onClick (not interactive) | ✅ |
| H2 | brand-divider | `aw-brand-divider` | n/a | ✅ |
| H3 | Connection status pill | `aw-status-pill` w/ `data-status` | reads `status` prop | ✅ |
| H4 | aw-mode-llm | `data-testid="aw-mode-llm"` | no onClick; `aria-pressed="true"` always | 🆗 — Sprint 7 D-105 lock (LLM always active) |
| H5 | aw-mode-manual | `data-testid="aw-mode-manual"` | `disabled` + title cites Sprint 8 | 🚫 — D-105 |
| H6 | aw-agents-toggle | `data-testid="aw-agents-toggle"` | `setAgentsOpen(!agentsOpen)` | ✅ |
| H7 | Page URL pill | `aw-status-pill shrinkable` | reads `pageUrl` prop | ✅ |
| H8 | Tokens pill | `aw-run-pill` | reads `tokenInfo` prop | ✅ |
| **H9** | **Dock-right** | `data-testid="aw-dock-right"` | `setDock("right")` — local `useState` only | ⚠️ **BROKEN** |
| **H10** | **Dock-left** | `data-testid="aw-dock-left"` | `setDock("left")` — local `useState` only | ⚠️ **BROKEN** |
| **H11** | **Dock-top** | `data-testid="aw-dock-top"` | `setDock("top")` — local `useState` only | ⚠️ **BROKEN** |
| **H12** | **Dock-float** | `data-testid="aw-dock-float"` | `setDock("float")` — local `useState` only | ⚠️ **BROKEN** |
| H13 | Collapse | `data-testid="aw-collapse"` | `setCollapsed(!collapsed)` | ✅ |
| **H14** | **Settings (gear icon)** | no testid | **no onClick at all** | 💀 **DEAD** |

### Dock-button root cause (H9–H12 BROKEN)

Two parallel dock systems are not integrated:

1. **`frontend/src/layout/dock-controller.js`** owns real dock behavior via `applyDock(hostElement, mode)` which sets classes `aw-dock-right` / `aw-dock-left` / `aw-dock-bottom` / `aw-floating` on the **shadow host element** (outside the shadow DOM). Persisted via `localStorage["aw-dock-mode"]`. Invoked exactly once at `main.jsx:3349` during mount.

2. **`frontend/aw-ide-panel.jsx:222`** has `const [dock, setDock] = useState("right")` — local component state. Header dock buttons call `setDock(kind)`. Result: the panel's inner `aside.aw-panel` gets class `dock-${kind}` (e.g. `dock-left`), but:
   - The shadow host's class stays at whatever `applyDock` set at mount.
   - The CSS rules at `v4.css:134-136` are `.dock-left .aw-panel` (descendant selector). They expect a parent with `.dock-left`. Production puts the class on the panel itself, not the parent. **Rule never matches.**
   - No call to `applyDock(hostNode, newMode)`.
   - No call to `setDockMode(newMode)` to persist.

**Effect:** clicking dock buttons changes the `active` highlight in the header but **the panel does not move**. The persisted dock mode from `localStorage` is ignored by the Header buttons.

Fix needed: pipe `setDock` callback up to `main.jsx` where the host element is available, then call `applyDock(hostElement, "aw-dock-" + kind)` and `setDockMode(...)`.

---

## B. TabStrip (`chrome.jsx::TabStrip`)

| # | Tab | Wiring | Status |
|---|---|---|---|
| T1 | LLM | `setTab("llm")` | ✅ |
| T2 | Steps | `setTab("steps")` | ✅ |
| T3 | Recorded (rec) | `setTab("rec")` | ✅ |
| T4 | Code | `setTab("code")` | ✅ |
| T5 | Trace | `setTab("trace")` | ✅ |
| T6 | Badge counts | reads `counts` prop | ✅ (auto-switch on plan_ready, commit `6c05920`) |

---

## C. NowStrip primary action (`chrome.jsx::NowStrip`)

Wired to `onPrimary` callback. RC3 fix `a5e4278` widened the state guard to accept both `awaiting_confirmation` and alias `await`. ✅

---

## D. Resize handle

| # | Element | Source | Status |
|---|---|---|---|
| **R1** | `<div className="aw-resize" />` | `aw-ide-panel.jsx:422` | 💀 **DEAD** — drag-to-resize handle has **no event handlers**. `createResizeController` is defined in `frontend/src/layout/resize-controller.js:44` but **never instantiated** in `main.jsx`. The handle is purely cosmetic. |

Effect: User cannot resize the panel by dragging the edge.

---

## E. CollapsedRail (`chrome.jsx::CollapsedRail`)

| # | Element | Wiring | Status |
|---|---|---|---|
| CR1 | Expand button | `setCollapsed(false)` | ✅ |
| CR2 | 5 tab icons | `setTab(it.id)` (each also expands) | ✅ |
| CR3 | Status dot | read-only | ✅ |

---

## F. AgentsPopover (`chrome.jsx::AgentsPopover`)

Per D-106: all rows are EMPTY when backend has no `agent_settings` event. Toggles are disabled.

| # | Element | Wiring | Status |
|---|---|---|---|
| AG1 | Close X (`aw-agents-close`) | `onClose` callback | ✅ |
| AG2 | Per-agent toggle | `disabled` + Sprint 8 title | 🚫 D-106 |
| AG3 | Per-agent locked toggle (required) | `disabled` + "Required — always on" | 🚫 D-106 |
| **AG4** | **Footer link "Open agent trace"** in design | production has different copy "BUG-S8-AGENT-001" | ❌ MISSING (intentional per D-106) |

---

## G. LLM tab — empty state (`LlmEmpty`)

| # | Element | Wiring | Status |
|---|---|---|---|
| E1 | 4 suggestion chips (post-`42fb98d`) | each calls `onSeed(text)` → `dispatchers.onSendUserMessage` | ✅ |

---

## H. LLM tab — Composer (`Composer`)

| # | Element | Wiring | Status |
|---|---|---|---|
| C1 | Pick element (mouse) `aw-composer-pick` | `onPickElement({type:"arm_picker"})` | ✅ D-107 |
| C2 | Send `aw-composer-send` | `send()` → `onSend({type:"user_message", message_text})` | ✅ |
| C3 | textarea | controlled `setText`; Enter submits | ✅ |
| **C4** | **Paperclip attach** (design) | n/a — production doesn't render | ❌ MISSING — filed as `BUG-S8-COMPOSER-ATTACH-001` |
| **C5** | **Context chips row** (design: page URL · selected · file) | n/a | ❌ MISSING — filed as `BUG-S8-COMPOSER-CONTEXT-CHIPS-001` |
| C6 | Camera/screenshot button | absent in production | 🚫 D-107 (hidden as non-P0; needs backend seam) |
| **C7** | **Provider badge** (design: "complete-llm · gpt-class") | n/a | ❌ MISSING (P2) |

---

## I. LLM tab — Card primary actions (`llm-cards.jsx`)

### CardClarification
| Button | Wiring | Status |
|---|---|---|
| `clarification-option-${id}` | `setPick(id)` local | ✅ |
| `clarification-submit` | `disabled` until pick; on click `onAnswer({type:"option_selected", question_id, answer})` | ✅ |
| `clarification-let-llm` | calls `onLetLLMDecide` callback or falls through to `onAnswer({type:"let_llm_decide"})` | ✅ |

### CardRecommendation
| Button | Wiring | Status |
|---|---|---|
| Per-item checkbox | local `toggle(id)` | ✅ |
| `recommendation-accept` | `disabled={!recommendations.length}`; on click `onAccept({type:"recommendation_accepted", ids})` | ✅ |
| `recommendation-add-own` | `onAddOwn()` | ✅ |

### CardPlanDiff
| Button | Wiring | Status |
|---|---|---|
| `plan-diff-apply` | `disabled={!diff_id}`; calls `onApply({type:"plan_diff_apply", diff_id})` | ✅ |
| `plan-diff-reject` | `disabled={!diff_id}`; calls `onReject` | ✅ |

### CardPlanReady
| Button | Wiring | Status |
|---|---|---|
| `plan-confirm` | `disabled={!plan?.plan_id}`; on click `onConfirm({type:"plan_confirmed", plan_id})` | ✅ |
| `plan-correction` (Send Correction) | `onEdit({type:"correction_requested"})` | ✅ |
| `plan-partial-run` | `onPartialRun({type:"run_steps", mode:"selected"})` | ✅ |

### CardPermission
| Button | Wiring | Status |
|---|---|---|
| Allow Once / Allow for plan / Deny | each dispatches `onDecision({type:"permission_decision", decision, ...})` | ✅ |

### CardExecution
| Button | Wiring | Status |
|---|---|---|
| Pause | `onPause` callback | ✅ |
| Stop | `onStop` callback | ✅ |

### CardLocatorAmbiguity
| Button | Wiring | Status |
|---|---|---|
| Per-candidate Select | `setPicked` local + `onChoose({type:"choose_locator_candidate", candidate_id})` | ✅ |
| Highlight (per-candidate) | currently a stub button | ⚠️ — design has it; no production handler. Cosmetic-only. Worth filing. |
| Ask LLM for better locator | `onAskLLM` | ✅ |
| Change scope | `onChangeScope` | ✅ |
| `locator-stop` Stop | disabled when no handler | ✅ |
| `locator-confirm` Use candidate | disabled when no pick | ✅ |
| `Show/Hide per-candidate diagnostics` link | local `setShowDiag` | ✅ |

### CardRecovery
| Button | Wiring | Status |
|---|---|---|
| Apply LLM repair | `onApplyRepair` | ✅ |
| Retry | `onRetry` | ✅ |
| Choose another locator | `onChooseLocator` | ✅ |
| Stop | `onStop` | ✅ |

### CardCompleted
| Button | Wiring | Status |
|---|---|---|
| Replay all | `onReplayAll` | ✅ |
| Save as suite | `onSaveSession` | ✅ |
| Open code | `onOpenCode` | ✅ |
| Download trace | `onDownloadTrace` | ✅ |

### CardOffline
| Button | Wiring | Status |
|---|---|---|
| Reconnect | `onReconnect` | ✅ |
| View connection log | currently a stub | ⚠️ no handler |
| Switch endpoint | currently a stub | ⚠️ no handler |

### CardSchemaError
| Button | Wiring | Status |
|---|---|---|
| Ask LLM to repair plan | `onAskRepair` | ✅ |
| Edit plan manually | stub | ⚠️ no handler |
| Open raw response | stub | ⚠️ no handler |

### Missing cards entirely
| Card | Status |
|---|---|
| CardNoBrowser | ✅ ACTIVE (E2/B2) — backend builder ships; auto-emission deferred to a later batch. `llm-cards.jsx::CardNoBrowser`. |
| CardApiKey | ✅ ACTIVE (E2/B2) — backend builder ships with secret-strip; no key collection in frontend. `llm-cards.jsx::CardApiKey`. |
| CardOtp | ✅ ACTIVE (E2/B2) — sensitive-gated render; no value input field. `llm-cards.jsx::CardOtp`. |
| CardE2EPending | ✅ ACTIVE (E2/B2) — advisory-only card. `llm-cards.jsx::CardE2EPending`. |

---

## J. Steps tab (`secondary-tabs.jsx::StepsTab` + `StepRow`)

### Toolbar
| Element | Wiring | Status |
|---|---|---|
| `steps-add` Add step | `onAdd({type:"add_step"})` | ✅ |
| `steps-pick` Pick element | `onPickElement({type:"arm_picker"})` | ✅ |
| `steps-filter` Filter input | local `setFilter` controls in-memory filter | ✅ |
| **Filter icon button** (design has separate icon) | absent in production | ❌ MISSING (P2) |

### Info-strip Run buttons
| Element | Wiring | Status |
|---|---|---|
| `steps-run-all` Run Pending Steps | `disabled={blocked \|\| list.length===0}`; on click `onRunAll()` → `handleRunPendingSteps` → sends `{type:"run_steps", steps:[]}` | ✅ |
| `steps-run-selected` Run selected | `disabled={blocked \|\| selectedStepIds.length===0}`; on click `onRunSelected()` | ✅ |

### Per-step (StepRow) actions
| Element | Wiring | Status |
|---|---|---|
| `step-input-${id}` intent input | `onChangeIntent` | ✅ |
| `step-status-${id}` ide-badge | read-only | ✅ |
| `step-id-${id}` mono small id | read-only (added `42fb98d`) | ✅ |
| `step-target-${id}` summary | read-only | ✅ |
| StepLocatorChip + `step-improve-locator-${id}` + `step-view-candidates-${id}` | `onImproveLocator` / `onViewCandidates` typed commands | ✅ D-101 |
| StepKindChip | read-only | ✅ |
| StepChildCountBadge | read-only | ✅ |
| StepBlockedStrip + `step-blocked-action-${id}` button | `onResolveBlocked` reason router | ✅ D-101 |
| StepPreconditionStrip + `step-precondition-action-${id}` + `step-navigate-expected-${id}` | `onChangePrecondition` / `onNavigateToExpected` | ✅ D-101 |
| StepChildrenList | read-only | ✅ |
| picker-candidate-select | `onChangeElementTarget` | ✅ |
| Outcome chips `step-outcome-chip-${type}-${id}` | `onChangeExpectedOutcome` | ✅ |
| `step-attach-${id}` Attach Element | `onAttachElement(stepId)` (`runtime.handleAttachElement`) | ✅ |
| `step-duplicate-${id}` | `onDuplicate(stepId)` | ✅ |
| `step-remove-${id}` (need to verify) | look up in code |

---

## K. Recorded tab (`secondary-tabs.jsx::RecordedTab`)

| Element | Wiring | Status |
|---|---|---|
| `recorded-replay-all` | `onReplayAll({type:"replay_session"})` | ✅ |
| Per-row Replay (`recorded-replay-${id}`) | `disabled` when no backend id or no `onReplayOne`; on click `onReplayOne({type:"replay_one", step_id})` | ✅ |
| `recorded-row-${id}` rendered fields | read from backend payload | ✅ |
| Repair diff render | absent | ❌ MISSING — `BUG-S8-RECORDED-REPAIR-DIFF-001` |
| Screenshot visual tile | absent (text link only) | ❌ MISSING — `BUG-S8-RECORDED-SCREENSHOT-TILE-001` |

---

## L. Code tab (`secondary-tabs.jsx::CodeTab`)

| Element | Wiring | Status |
|---|---|---|
| `code-copy` Copy | `disabled={!hasCode}`; on click `onCopy()` → clipboard | ✅ |
| `code-save` Save | `disabled={!hasCode}`; on click `onSave({type:"export_code"})` | ✅ D-103 |
| `code-save-result` chip | read from `codeSaveResult` payload | ✅ |
| Syntax highlighting on `<pre>` | absent — raw text | ❌ MISSING — `BUG-S8-CODE-SYNTAX-HIGHLIGHT-001` |
| Top badges row (fragile/placeholder/mapped) | absent | ❌ MISSING (P2) |
| Per-line warnings | absent | ❌ MISSING (P2) |

---

## M. Trace tab (`secondary-tabs.jsx::TraceTab`)

| Element | Wiring | Status |
|---|---|---|
| Search input | local `setText` filter | ✅ D-104 |
| Filter chips (7: all/llm/step/permission/error/code/gap) | local `setFilter` | ✅ D-104 |
| `trace-failure-detail-${i}` | read from `step_failed` payload | ✅ |
| `trace-artifact-list-${i}` w/ artifact links | read from payload | ✅ |
| `trace-llm-unavailable-${i}` honest fallback | read from payload | ✅ |
| `trace-gap-card-${i}` (capability gap) | read from `capability_gap_recorded` | ✅ |
| `trace-redaction-chip-${i}` | read from payload | ✅ |
| **Download trace button** (design has it) | absent | ❌ MISSING (P2) — could file `BUG-S8-TRACE-DOWNLOAD-001` |

---

## N. Dark mode

**Status:** NOT in v4 design. NOT in production.

Evidence: `grep "dark\|theme\|night" yui (1)/v4/styles.css yui (1)/v4/app.jsx frontend/v4.css` → zero hits. `yui (1)/v4/tweaks-panel.jsx:17-41` has dark-mode toggle **commented out**.

User mention of dark mode appears to be from earlier yui iterations (v1/v2/v3) which had it; v4 dropped it. **No action required** unless user wants to re-add it.

---

## O. TweaksPanel (prototype-only)

Design has a TweaksPanel for changing state/dock/tab live during demo. Production correctly omits it (it's a prototype dev tool, not a product feature). No action.

---

## P. Aggregate counts

| Status | Count |
|---|---|
| ✅ WORKS | ~60 controls |
| 🆗 SEMANTIC-NO-OP | 1 (LLM mode active button) |
| 🚫 DISABLED-WITH-REASON | 6 (Manual mode, agent toggles, camera) |
| ⚠️ BROKEN | **5** (4 dock buttons + Highlight/View-log/Switch-endpoint/Edit-plan/Open-raw stub buttons — see below) |
| 💀 DEAD | **2** (Settings gear, Resize handle) |
| ❌ MISSING | 11 (4 missing cards + paperclip + context chips + provider badge + screenshot tile + repair diff + syntax highlight + filter icon + trace download) |

### Confirmed BROKEN controls (5+)
1. **Header dock-right** — `setDock` is local state, no host applyDock call → panel doesn't move
2. **Header dock-left** — same
3. **Header dock-top** — same
4. **Header dock-float** — same
5. CardLocatorAmbiguity "Highlight" per-candidate — design has it, production stub `onClick={(e) => e.stopPropagation()}` only
6. CardOffline "View connection log" — stub
7. CardOffline "Switch endpoint" — stub
8. CardSchemaError "Edit plan manually" — stub
9. CardSchemaError "Open raw response" — stub

### Confirmed DEAD controls (2)
1. **Header Settings (gear icon)** `chrome.jsx:144` — no `onClick`, no `data-testid`. Pure decoration. Same in design (`yui (1)/v4/chrome.jsx:60`).
2. **Resize handle** `<div className="aw-resize" />` `aw-ide-panel.jsx:422` — controller defined in `resize-controller.js:44` but never instantiated. Drag-to-resize does not work.

---

## Q. Root-cause classification (Phase 1 of systematic-debugging)

| Root cause | Affected controls | Layer | Fix layer |
|---|---|---|---|
| **Local `useState` not propagated to host applyDock** | H9 H10 H11 H12 dock buttons | frontend (panel ↔ main.jsx integration) | aw-ide-panel.jsx ↔ main.jsx callback or shared dock state |
| **Resize controller defined but never instantiated** | R1 resize handle | frontend main.jsx mount | call `createResizeController(hostElement, onResize)` in `mount()` after `applyDock` |
| **Settings button has no implementation** | H14 | frontend (and design — both lack it) | needs product decision — settings panel UI; defer S8 |
| **Stub onClick handlers in cards** | Highlight, View log, Switch endpoint, Edit plan, Open raw response | frontend cards | wire to backend events or hide buttons until implemented |
| **Missing cards** | NoBrowser/ApiKey/Otp/E2EPending | frontend + backend events | already filed Sprint 8 tickets |
| **Missing controls** | paperclip, context chips, screenshot tile, repair diff, syntax highlight, filter icon, trace download | frontend or frontend+backend | already filed Sprint 8 tickets |

---

## R. Priority for Phase 4 fixes

**P0 (Sprint 7 blocker — actual broken behavior the user can hit RIGHT NOW):**
1. **Dock buttons broken (H9–H12)** — wire `setDock` callback up to `main.jsx`, call `applyDock(node, mode)` and `setDockMode(mode)`. Add jsdom test that clicking dock buttons changes the host class.
2. **Resize handle dead (R1)** — call `createResizeController(hostElement, onResize)` in `mount()` after `applyDock`. Add jsdom + manual visual test.
3. **Settings button dead (H14)** — either remove from header, or wire to a Sprint 8 placeholder (e.g. open a "Settings — coming in Sprint 8" minimal popover, disabled controls only).
4. **Stub card buttons** — either delete them, disable with reason, or wire them. Decide per button.

**P1:**
5. CardLocatorAmbiguity Highlight button — useful UX, backend already knows the locator; add typed `highlight_locator` command.
6. CardOffline "View connection log" / "Switch endpoint" — currently misleading affordances; either implement or remove.

**S8 (already filed):**
- All missing cards + composer chips + paperclip + recorded repair-diff + screenshot tile + code syntax highlight + auto-scroll + agent control center.

**Out of scope:**
- Dark mode (not in v4 design).
- TweaksPanel (prototype-only).

---

## S. Test gates needed after P0 fixes

```bash
cd frontend && npm test                                                # jsdom suite
cd frontend && npm run build                                           # bundle clean
python -m pytest --tb=short -q --ignore=tests/e2e                      # backend contract
python -m pytest tests/e2e/test_v4_panel_smoke.py -q                   # docked smoke
```

New jsdom tests required:
- Clicking dock-left calls `applyDock(node, "aw-dock-left")` and `setDockMode("aw-dock-left")`.
- Resize handle `mousedown` triggers controller start; mousemove resizes; mouseup persists.
- Settings button either absent OR opens Settings popover.
- Stub buttons either absent OR have honest disabled state with title.

---

**End of Phase 1 actions audit.** No code changed. Findings ready for Phase 3 hypothesis + Phase 4 fix sequence.
