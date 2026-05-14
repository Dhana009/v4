# D-105 Manual Mode Classification — Sprint 7 Wrap-Up Mini-Spec

**Classification verdict: B — DISABLED_WITH_REASON**

Reason (precise): PRD Phase 4 is a separate numbered phase after Phase 3 and
carries no explicit "must be working by Sprint 7 closure" language. Sprint 7
cluster plan (clusters 0–11) places Manual Mode in cluster 7 scope, but the
PRD acceptance criteria for Phase 4 is standalone — it is not listed in the
Phase 1–3 MVP acceptance tests or the "Tests that must exist before calling LLM
Mode MVP complete" checklist (06 §Tests 1–12). The existing Manual Mode
components (`ManualActionBuilder`, `ManualAssertionBuilder`, `ManualModeToggle`)
are isolated under `frontend/src/components/manual/` and are NOT imported
anywhere in the v4 production path (`chrome.jsx`, `llm-cards.jsx`,
`secondary-tabs.jsx`, `main.jsx`). Backend has zero handlers for
`manual_action_draft`, `manual_assertion_draft`, or `set_mode` — `server.py`
returns `COMMAND_NOT_SUPPORTED` for any of these. No end-to-end path exists
without new backend work. Therefore classification A (WORKING_FOUNDATION) would
require new backend seam work that is not unambiguously demanded for Sprint 7
closure. Per master §9 default rule and §15 stop condition ("Manual Mode
classification A would require new backend work that is not explicitly
PRD-P0 acceptance"), classification is B.

**User approval required at handoff §15 to confirm class B.**
If user overrides to A, see §6 foundation plan below.

---

## 1. Classification Verdict

| Field | Value |
|---|---|
| Class | **B — DISABLED_WITH_REASON** |
| PRD basis | 06 Phase 4 + Must-have v2.2 #1; Phase 4 is a *separate phase after Phase 3* with no "Sprint 7 closure" deadline language |
| Sprint 7 cluster scope | Cluster 7 spec (S7-0708/0709/0710) implemented component stubs; components are NOT wired into v4 production render path |
| Backend seam status | ABSENT — no `set_mode`, `manual_action`, `manual_assertion`, or `manual_action_draft` handler in `server.py` or `agent.py` |
| Class A path viability | Requires new backend seam (`set_mode` routing + `manual_action_draft`/`manual_assertion_draft` validation/recording) — blocked by §15 stop condition |
| Unblocking condition | User explicitly approves class A at handoff §15 OR Sprint 8 ticket closes |

---

## 2. Current State

The v4 header (`chrome.jsx`) renders a static `<span className="aw-status-pill mode">LLM</span>` badge with no toggle affordance. There is no mode-switch button or toggle in the production v4 render path.

Three components exist under `frontend/src/components/manual/`:
- `ManualModeToggle.jsx` — checkbox toggle, guards blocked phases, emits `set_manual_mode` draft — **never imported in v4 path**
- `ManualActionBuilder.jsx` — action/target/value form, emits `manual_action_draft` — **never imported in v4 path**
- `ManualAssertionBuilder.jsx` — assertion type/target/expected form, emits `manual_assertion_draft` — **never imported in v4 path**

`tests/test_frontend_steps_manual_cards.py` has source-pattern tests asserting the components exist and contain specific text patterns; these pass because the files exist. These tests do NOT assert the components are wired into any rendered surface or that a backend command round-trip works.

The v4 control inventory (master §6) records the mode toggle row as:
> `Manual Mode toggle (header) | chrome.jsx (mode toggle) | tbd | Header | local setMode no-op | none | INERT | classify per §9`

and:
> `Manual Mode builder card | not rendered | n/a | StepsTab / dedicated | n/a | manual_action / manual_assertion (defined, FE not wiring) | MISSING | classify per §9`

Neither row has been resolved. This spec resolves both as class B.

---

## 3. PRD-P0 Basis

### Phase 4 in 06_BUILD_ROADMAP_AND_ACCEPTANCE.md

Phase 4 is explicitly titled "Manual Mode using same runtime" and lists:
- manual pick/action/assert controls
- manual validation
- same Step Runner
- same codegen
- LLM repair only on failure or explicit request

Expected criteria: Manual Mode reuses Step Runner, Tool Runtime, Recorder, and Codegen. Manual steps can be replayed and repaired like LLM-recorded steps.

**Phase 4 is numbered after Phase 3 (Recording/save/replay/repair/versioning).** The PRD says "Build in this order. Each phase is independently testable." There is no statement that Phase 4 must be complete before Sprint 7 closes.

### Must-have v2.2 #1

Manual Mode is Must-have #1 in the preserved v2.2 list. However, v2.2 roadmap Phases 1–2 in that document describe "Week 1–3" with Manual Mode complete, then LLM Mode in Phase 3 (Week 4–5). This is the v2.2 priority order, which v2.3 superseded — v2.3 §01 explicitly lists:

> Priority order: 1. Stabilize foundation. 2. Complete LLM Mode MVP. 3. Complete recording/save/replay/repair. **4. Manual Mode using the same runtime.**

Manual Mode is fourth in v2.3 priority. The "Tests that must exist before calling LLM Mode MVP complete" (06 §Acceptance) contains 12 tests — none mention Manual Mode.

### Sprint 7 cluster scope note

`SPRINT-007-HANDOFF.md` (per master §4 reference) lists clusters 0–11. Cluster 7 specs (S7-0708/0709/0710) are listed as Done in S7-0708 evidence block — the commit `1e8c736` created components under `frontend/src/components/manual/`. However "Done" for cluster 7 means component stubs written and source-pattern tests pass; it does NOT mean end-to-end integration into the v4 production surface or backend wiring.

The master §9 default rule is:
> "Default fate is **B** unless §13 D-105 mini-spec proves a minimal **A** path lands cleanly without new backend work and within the PRD-P0-only seam rule."

A landing without new backend work is not possible (see §4).

---

## 4. Backend Grep Results

**Grep scope:** `agent.py`, `server.py`, `runtime/*.py` for strings:
`manual_action`, `manual_assertion`, `manual_mode`, `set_mode`, `manual_action_draft`, `manual_assertion_draft`, `"manual"`

**Results — all absent in production Python:**

| Target | File | Present? | Evidence |
|---|---|---|---|
| `manual_action` handler | `server.py` | NO | zero matches |
| `manual_assertion` handler | `server.py` | NO | zero matches |
| `set_mode` handler | `server.py` | NO | zero matches |
| `manual_action_draft` command routing | `server.py` | NO | zero matches |
| `manual_assertion_draft` command routing | `server.py` | NO | zero matches |
| any `"manual"` string | `agent.py` | NO | zero matches |
| any `manual_*` | `runtime/*.py` | NO | zero matches |

`server.py` falls through to `COMMAND_NOT_SUPPORTED` for any unrecognized type. Any `manual_action_draft` or `set_mode` command sent by the frontend today receives a rejection event back.

**PRD 04_BACKEND_EVENT_CONTRACT.md (preserved v2.2 section)** lists `set_mode | { mode: "manual"|"llm" } | Switch mode` in the Panel → Backend table. This is a v2.2 schema reference, not a v2.3 implemented handler. The v2.3 typed command table (the authoritative section above the preserved block) does NOT list `set_mode`, `manual_action`, or `manual_assertion` as a Required frontend → backend command.

**Conclusion:** Backend handlers do not exist. This rules out class A without new seam work.

---

## 5. Class B — Disabled-Control Plan (per master §8)

### 5a. Toggle disabled-with-reason

The v4 header currently shows a static `LLM` pill badge with no clickable affordance. The D-105 resolution does not need to add a toggle to the header; it must ensure:

1. The LLM pill badge (`<span>LLM</span>` in `chrome.jsx:58`) is documented as the mode indicator and carries a `title` explaining Manual Mode is coming.
2. If a mode toggle button is rendered, it must have `disabled` attribute and a `title` citing D-105.
3. No clickable no-op mode switch is left reachable.

**Proposed control state:**
```html
<!-- In chrome.jsx Header, replacing or annotating the LLM pill -->
<span
  className="aw-status-pill mode"
  title="Mode: Complete LLM Mode — Manual Mode coming in Sprint 8 (D-105)"
  data-testid="aw-mode-pill"
>
  <span className="aw-dot" />
  LLM
</span>
```

No toggle button is rendered. The pill is read-only. If user later chooses class A override, a disabled toggle is added; this spec records the B path only.

**If a toggle exists and must be disabled (per §8 checklist):**
- `disabled` attribute set
- `title="Manual Mode not available — backend seam required. See D-105 / BUG-S8-MANUAL-001."`
- Label text: `Manual Mode (Sprint 8)` — does not imply it works
- jsdom test asserts: rendered, `disabled=true`, `title` non-empty, click is no-op

### 5b. ManualBuilder card — hidden

`ManualActionBuilder`, `ManualAssertionBuilder`, and `ManualModeToggle` remain in `frontend/src/components/manual/` but are NOT imported or rendered in any v4 surface. No partial render. The `StepsTab` in `secondary-tabs.jsx` must not conditionally reveal them under any current state.

Verify: `grep -r "ManualAction\|ManualAssertion\|ManualModeToggle" frontend/src/v4/ frontend/src/main.jsx` returns zero results. Already confirmed zero at spec authoring.

### 5c. Sprint 8 ticket

**Ticket ID proposed: BUG-S8-MANUAL-001**

**Title:** Implement Manual Mode working foundation (D-105 class A)

**Acceptance criteria:**
1. `set_mode` command is handled in `server.py`; backend validates `mode ∈ {"llm","manual"}`; emits `mode_changed` event or equivalent to frontend.
2. `manual_action_draft` command is handled; backend validates `action`, `target`, required `value`; dispatches into Step Runner as a deterministic step (same path as LLM-recorded step); emits `step_recorded` on success.
3. `manual_assertion_draft` command is handled; backend validates `assertion_type`, `target`, required `expected`; dispatches into Step Runner; emits `step_recorded`.
4. Frontend v4: mode toggle renders in Steps tab (not header) — `disabled` during run/recovery/save-load; emits `set_mode` command on toggle; gate is `mode === "manual"` from backend `mode_changed` event (not local state only).
5. `ManualActionBuilder` wired into Steps tab under `mode === "manual"` gate; submits `manual_action_draft` via typed dispatcher.
6. `ManualAssertionBuilder` wired under same gate; submits `manual_assertion_draft`.
7. jsdom tests cover: toggle disabled states, builder dispatch, `mode_changed` reducer, no auto-LLM in manual mode.
8. At least one local-fixture E2E smoke: toggle → add manual action → `step_recorded` arrives → recorded tab shows entry.
9. No fork of Step Runner architecture; same Recorder/Codegen path as LLM steps.

**File scope (S8 estimate):**
- `server.py`: add `set_mode`, `manual_action_draft`, `manual_assertion_draft` handlers
- `runtime/event_contracts.py`: add `manual_action` / `manual_assertion` typed command validators
- `frontend/src/v4/secondary-tabs.jsx`: wire `ManualModeToggle` into `StepsTab` under mode gate
- `frontend/src/main.jsx` or store: add `mode_changed` reducer
- Tests: `tests/test_manual_mode_backend.py` (new), `frontend/src/v4/secondary-tabs.test.jsx` (extend)

### 5d. jsdom test for disabled assertion

File: `frontend/src/v4/chrome.test.jsx` (or `secondary-tabs.test.jsx` if toggle is in StepsTab).

Required assertions (class B path):
```js
// D-105 class B — mode pill is read-only, no clickable toggle
it('mode pill is present and non-interactive', () => {
  render(<Header ... />);
  const pill = screen.getByTestId('aw-mode-pill');
  expect(pill).toBeInTheDocument();
  expect(pill.tagName).not.toBe('BUTTON');  // not a button
  expect(pill).toHaveAttribute('title', expect.stringContaining('D-105'));
});

// If a disabled toggle is rendered instead:
it('manual mode toggle is disabled with reason title', () => {
  render(<ManualModeToggle phase="idle" disabledReason="Backend seam required (D-105)" />);
  const checkbox = screen.getByTestId('manual-mode-checkbox');
  expect(checkbox).toBeDisabled();
  expect(checkbox).not.toBeChecked();
  // click has no effect
  fireEvent.click(checkbox);
  // onToggle must not have been called
});
```

---

## 6. Class A Path — Minimal Foundation Plan (user override only)

This section is informational. Execute only if user approves class A at handoff §15.

### 6a. Mode-state wiring

- Add `mode_changed` event to `runtime/event_contracts.py`:
  ```python
  {"type": "mode_changed", "mode": "llm"|"manual"}
  ```
- Add `set_mode` handler in `server.py` (after `arm_picker` block):
  - Validates `mode ∈ {"llm","manual"}`
  - Emits `mode_changed` event immediately (no run required)
  - Does NOT disrupt active run_id or recorded steps
- Add `mode_changed` case to frontend reducer in `main.jsx`:
  - `state.mode = action.payload.mode`
  - No side-effects on `recordedSteps` or `runState`

### 6b. ManualBuilder card location

Wire into `StepsTab` section in `secondary-tabs.jsx` under `mode === "manual"` gate — NOT into the header. Renders below the existing `PendingStepEditor` section when mode is manual.

Controls:
1. `ManualModeToggle` — emits `set_mode` via typed dispatcher; disabled during `executing/recovery/saving/loading` phases
2. `ManualActionBuilder` (element pick → action select → value → submit `manual_action_draft`)
3. `ManualAssertionBuilder` (assertion type → target → expected → submit `manual_assertion_draft`)

No element picker re-architecture required — reuse existing `arm_picker` seam.

### 6c. Backend commands used (existing seams only)

| Command dispatched | Seam status | Note |
|---|---|---|
| `set_mode` | MUST BUILD — not in `server.py` | Minimal: validate, emit `mode_changed`, done |
| `arm_picker` | EXISTING — `server.py:603` | Reuse for element pick in manual builder |
| `manual_action_draft` | MUST BUILD | Validate action/target/value; route to Step Runner |
| `manual_assertion_draft` | MUST BUILD | Validate type/target/expected; route to Step Runner |

Step Runner routing: identical to LLM step submission path — no new recording fork.

### 6d. Tests required (class A)

- jsdom: toggle disable states, `set_mode` dispatch, `mode_changed` reducer update, builder submit dispatch, no auto-LLM, no local `step_recorded` fabrication
- backend pytest: `set_mode` validation, `manual_action_draft` validation (valid/invalid payloads), `manual_assertion_draft` validation
- local-fixture E2E smoke: one passing scenario (toggle → add click action → `step_recorded` arrives)

---

## 7. Tests Required (class B path)

| Test | File | What it asserts |
|---|---|---|
| `test_mode_pill_is_present` | `chrome.test.jsx` | `data-testid="aw-mode-pill"` exists in Header |
| `test_mode_pill_has_d105_title` | `chrome.test.jsx` | `title` attr contains "D-105" or "Manual Mode" + sprint ref |
| `test_mode_pill_not_clickable` | `chrome.test.jsx` | tagName is SPAN not BUTTON; no onClick that changes state |
| `test_manual_components_not_in_steps_tab` | `secondary-tabs.test.jsx` | rendering StepsTab with any state does not show `manual-action-builder` or `manual-assertion-builder` testids |
| `test_manual_mode_toggle_not_rendered_in_v4` | `secondary-tabs.test.jsx` | `manual-mode-toggle` testid absent from StepsTab render |

---

## 8. E2E

**Class B: NO E2E.** Manual Mode is disabled; no user-visible path to test.

If class A is approved (Sprint 8 or user override this sprint): minimal local-fixture smoke — one scenario, no paid LLM, no live website.

---

## 9. Acceptance Criteria (class B closure)

- [ ] `data-testid="aw-mode-pill"` present in Header with `title` containing "D-105" or "Manual Mode Sprint 8"
- [ ] No clickable mode toggle rendered in v4 production path
- [ ] `ManualActionBuilder`, `ManualAssertionBuilder`, `ManualModeToggle` are not imported in any v4 surface file
- [ ] jsdom test asserts pill non-interactive and title content
- [ ] jsdom test asserts manual builder testids absent from StepsTab render
- [ ] `BUG-S8-MANUAL-001` ticket created with acceptance criteria from §5c
- [ ] D-105 row in master §7 PRD reconciliation updated: `Final = DISABLED_WITH_REASON`
- [ ] D-105 row in master §6 control inventory: fate = `DISABLE_WITH_REASON`, ticket = `BUG-S8-MANUAL-001`
- [ ] User approval recorded in master §15 for class B selection

---

## 10. Stop Conditions

- If user explicitly selects class A at handoff §15 → stop this spec and follow §6 instead; new backend seam work required; estimate 1 additional pass
- If backend `manual_action`/`manual_assertion` handlers are discovered to already exist in a branch or module not grepped → re-classify as potentially class A; re-run grep, update §4, escalate to user
- If any jsdom test must be weakened to pass → STOP, fix product code, do not weaken assertion
- Do not add `set_mode` to `server.py` or wire any manual component into v4 under class B — that is Sprint 8 work

---

## 11. Final Handoff Evidence

When class B is complete, record under `SPRINT-007-HANDOFF.md §14 Disabled controls`:

```
D-105 Manual Mode
  Control: mode pill in Header (aw-mode-pill) — static read-only span, no toggle
  Reason: Backend seam (set_mode / manual_action_draft / manual_assertion_draft)
          absent in server.py; PRD Phase 4 is post-Phase-3 phase not required
          for Sprint 7 LLM Mode MVP closure
  PRD ref: 06 Phase 4 / Must-have v2.2 #1 / priority #4 in v2.3
  Ticket: BUG-S8-MANUAL-001
  Tests: chrome.test.jsx (mode pill non-interactive, D-105 title)
         secondary-tabs.test.jsx (manual builder testids absent)
  User approval: [to be recorded at handoff §15]
```

Commit message for class B implementation:
```
chore(v4): disable manual mode with reason (D-105)

Mode pill in Header is read-only span with D-105 title.
Manual builder components not wired in v4 surface.
Sprint 8 ticket BUG-S8-MANUAL-001 created.
```
