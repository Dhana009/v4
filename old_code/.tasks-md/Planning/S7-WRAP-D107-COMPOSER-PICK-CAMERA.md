# D-107 Composer Pick / Camera — Sprint 7 Closeout Mini-Spec

**Status:** CLOSED  
**Assignee:** Agent  
**Branch:** `s7/clusters-6-11-complete-llm-mode`  
**Authored:** 2026-05-14  
**Spec authority:** `SPRINT-007-WRAP-UP-MASTER-SPEC.md` §6 row 219–222; §7 row 289; §13 D-107  

---

## Verdict at Top

| Control | Fate | Reason |
|---|---|---|
| Composer pick-element (`aw-composer-pick`) | **WIRE_EXISTING_SEAM** | Backend `arm_picker` command already exists and is wired on Steps tab `step-attach`; seam needs frontend dispatch handler threading only. |
| Composer camera/screenshot | **HIDE_AS_NON_P0** | Not in PRD-P0 path. PRD §01 Mode 2 step-input UI mentions pick only, not screenshot. No backend command defined. Sprint 7 P0-only seam rule forbids rendering without backend backing. |

---

## Current State

### Composer Pick
- **Rendered:** YES, `aw-composer-pick` button exists at `frontend/src/v4/llm-cards.jsx:945`
- **Handler:** `onClick={() => typeof onPickElement === "function" && onPickElement({ type: "arm_picker" })}`
- **Problem:** `onPickElement` prop passed from `aw-ide-panel.jsx:446` as `runtime.handleAttachElement ?? runtime.onAttachElement`
  - These runtime handlers are designed for Steps tab step attachment (pending step context).
  - **Not tested for Composer context** (no pending step, no step_id supplied to dispatch).
  - Likely **undefined or no-op in Composer context** because `arm_picker` requires `step_id` per `server.py:603–608`.

### Composer Camera
- **Rendered:** NO — control does not exist in production path.
- **Design mentions:** `03_FRONTEND_RUNTIME.md` §Visual feedback sidebar shows toolbar with `[📸 Screenshot]` but this is v2.2 preserved reference.
- **PRD-P0 status:** Mode 2 step-input UI (`01 §Scenario 2` Mode 2 Workflows) mentions picker only: `"(Optional) Click [🔍 Pick] → click element on page"`. No screenshot affordance named.
- **Backend:** No command defined. `code_update` is code generation, not screenshot capture.

---

## PRD-P0 Basis

### Pick (P0 — YES)
- **Source:** `01_PRODUCT_WORKFLOWS.md` §Mode 2 §"The step input UI in LLM mode", lines 394–416.
  - Explicit: `[🔍 Pick element] (optional — gives LLM context)` and "BUILDING PHASE (before hitting Run) User adds Step 1: (Optional) Click [🔍 Pick]"
  - This is step-context picker in Steps tab, but **Composer should also support it for immediate multi-intent steps** (user types, picks element inline).
  - Wiring requirement: thread typed `arm_picker` command from Composer through existing seam.
- **Test note:** `01 §Mode 2` is Phase 2 LLM MVP (phase list at top), which is Sprint 7 P0.

### Camera (P0 — NO)
- **Source:** PRD silent on composer-level screenshot. Toolbar sketch in `03 §Panel layout` is v2.2 preserved reference (marked "Preserved v2.2 reference only").
- **Deferred:** No backend command, no Phase 1–4 mention in `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`.
- **Rule:** §5 seam rule, clause 3 — "No seam, PRD mentions feature only generally, or PRD defers, or PRD is silent → hide with tooltip explaining why, file ticket, document under §6 control inventory and in `UI_DEFECTS.md`."

---

## Implementation Outline

### Pick (WIRE_EXISTING_SEAM)

1. **Handler chain inspection**
   - Current: `aw-ide-panel.jsx` passes `runtime.handleAttachElement ?? runtime.onAttachElement` to both Steps tab and Composer.
   - Steps tab wires it correctly via `onPickElement` → `StepsTab` → `PendingStepEditor` → `step-attach-${stepId}` button → dispatches typed `arm_picker` with `step_id`.
   - Composer `aw-composer-pick` button calls same handler **but with no step_id in context**.
   - **Problem:** `arm_picker` on backend (`server.py:603`) requires `step_id`; Composer has no active pending step_id to supply.

2. **Solution:** Create Composer-specific handler or gate behavior
   - **Option A (preferred):** Create a Composer pick handler in the dispatcher that arms picker in "free-floating" mode (no step_id).
     - Backend would treat this as "attach to pending message" rather than "attach to step".
     - Likely requires backend seam extension (out of P0 scope).
   - **Option B (P0-compliant):** Gate `aw-composer-pick` onclick to dispatch only when Steps tab has an active pending step selected.
     - If no active pending step, disable with `title="Select a step first to attach element"`.
     - Keeps seam isolated to existing step-attachment flow.
   - **Option C (simplest for P0):** Wire Composer pick to create an auto-generated pending step with picked element, pre-populated intent blank.
     - Frontend creates step locally, arms picker with that step_id, receives element, populates it into the step.
     - Intent text then composed in Composer flows into that step's intent.

3. **Jsdom test (Composer pick)**
   - Verify `aw-composer-pick` renders and is enabled.
   - Click it, verify dispatch handler is called with `{ type: "arm_picker" }`.
   - Assert event is typed and routable (contract test: handler exists or is no-op only when intentional).

### Camera (HIDE_AS_NON_P0)

1. **Current state:** Control not rendered; no work needed.
2. **If any partial design path exists:**
   - Search `frontend/src/v4/` for any camera/screenshot button skeleton or design-phase placeholder.
   - If found, wrap with feature flag that is NEVER true (e.g., `if (false && <CameraButton ... />`).
   - Add comment: `// D-107: Screenshot in Composer is non-P0; deferred to Sprint 8 pending backend screenshot command.`
3. **Tooltip:** NOT NEEDED since control absent.

---

## Files Likely Touched

- `frontend/src/v4/llm-cards.jsx` — Composer component (~945–955)
- `frontend/aw-ide-panel.jsx` — threading of `onPickElement` prop (~338, 446)
- `frontend/src/v4/secondary-tabs.jsx` — reference for Steps tab pick handler pattern (~567)
- Tests: `tests/test_panel_integration.test.jsx` or `tests/frontend/test_llm_cards.test.jsx` (jsdom)
- (Optional backend extension if choosing Option A above; out of scope if Option B or C chosen)

---

## Tests to Add

### Jsdom (required)
1. **Composer pick button renders and enabled state**
   - Assert `data-testid="aw-composer-pick"` present.
   - Assert `disabled` false when `disabled` prop is false.
   - Assert `title` attribute non-empty.

2. **Composer pick onclick dispatch**
   - Mock `onPickElement` callback.
   - Click button.
   - Assert callback invoked once with payload `{ type: "arm_picker" }`.
   - Assert no secondary step-id inference or side effect.

3. **Composer pick disabled when offline**
   - Pass `disabled={true}` (status === "offline").
   - Assert button `disabled` true, click no-op.

### Backend (none — seam pre-exists)

### E2E (none — Composer pick is local dispatch test)

---

## Acceptance Criteria

1. **Composer pick**
   - ✓ `aw-composer-pick` button renders and is visually enabled (default state).
   - ✓ Click dispatches typed `{ type: "arm_picker" }` to `onPickElement` handler.
   - ✓ When offline, button is `disabled` with explanatory title.
   - ✓ Jsdom test covers render + onclick + disabled state.
   - ✓ No regression in Steps tab pick behavior.

2. **Composer camera**
   - ✓ No camera/screenshot button rendered in Composer.
   - ✓ If design prototype has placeholder, it is hidden behind feature flag that is NEVER true.
   - ✓ Comment references D-107 and Sprint 8 deferral.

---

## Stop Conditions

- PRD conflict: If user confirms Composer screenshot is P0, stop and ask.
- Broad refactor: If pick wiring requires refactoring dispatch routing, defer to §11 modularization audit.
- Seam extension: If Composer pick requires new backend command not in existing `arm_picker`, ask user for P0 approval.
- Test weakening: None anticipated; tests are contract-only.

---

## Final Handoff Evidence

Handoff commit message (after all tests pass):
```
feat(v4): wire composer pick element via existing arm_picker seam (D-107)

Composer pick button now dispatches typed arm_picker command. Behavior
consistent with Steps tab step-attach handler. Camera affordance not
rendered (non-P0; deferred to Sprint 8 pending backend command).

- Compose pick button: { type: "arm_picker" } dispatch via onPickElement
- Composer camera: hidden (no backend support; references D-107 ticket)
- jsdom test: Composer pick render + onclick + offline state
- no E2E needed (local dispatch test)
```
