# BUG-S7-V4-001 — v4 Steps tab is missing the deep "intent → attach → outcome → run" workflow

**Severity:** medium
**Status:** Done — closed in Sprint 7 Stabilization Pass 4a (2026-05-14)
**Cluster:** Sprint 8 Integration Pass (deep workflow port)
**Filed:** 2026-05-14
**Closed:** 2026-05-14 at HEAD post-`76ac354`

## Summary

The new v4 Steps tab (`frontend/src/v4/secondary-tabs.jsx::StepsTab`)
renders the live pending-step list, supports add/edit/delete/reorder/
duplicate via typed commands, and surfaces Run all / Run selected. It
does NOT yet expose the legacy monolith's deep workflow:

- `Attach Element` button that arms the picker for a specific step
- `Click page element…` chrome that appears between arm and pick
- `.ide-step-input` (intent input) per pending step
- `.ide-step-outcome` chip group (navigation / visible / count / etc.)
- `.ide-badge.b-ready` ready-state badge
- `.ide-step-target-summary` for the picked element preview

These were part of `frontend/legacy/aw-ide-panel-legacy-monolith.jsx`.
The legacy `tests/e2e/test_mvp_001_lifecycle_smoke.py` E2E drives this
exact workflow, so it cannot pass against the v4 panel without those
controls in place.

## Impact

- `tests/e2e/test_mvp_001_lifecycle_smoke.py` fails at the
  `overlay_loaded` / `picker_armed` stages: it cannot find
  `Attach Element` or `.ide-step-input` in the v4 panel.
- The v4 surface still supports add/run/replay through typed commands,
  so the broader Sprint 7 integration is not blocked, but the deep
  user flow is.

## Required fix (Sprint 8)

Port the deep workflow into the v4 Steps tab:

1. Per-step intent editor (textarea + outcome chip group).
2. `Attach Element` button → dispatches `arm_picker` with step_id.
3. `.aw-step-target-summary` (or v4-equivalent testid) once an element
   is picked.
4. Ready-state badge once intent + outcome + element are present.
5. Map the `run_steps` command emitted by `Run Pending Steps` so the
   legacy E2E selector `Run Pending Steps` continues to work (or
   rewrite the E2E to call the v4 `steps-run-all` testid).

## Workaround

Frontend integration of the v4 panel is delivered without this deep
workflow. The Cluster-7 modular cards (Steps/Manual/Picker/Locator)
under `frontend/src/components/{steps,manual,picker,locator}/` exist
as reusable parts and can be composed into the v4 Steps tab in
Sprint 8.

A v4-aware smoke test
(`tests/e2e/test_v4_panel_smoke.py`) verifies the v4 panel mounts,
renders the docked Shadow DOM host, switches tabs, and shows the
empty-state messages without requiring the deep workflow.

## Closure (Pass 4a)

Audit on 2026-05-14 found the deep workflow surface was already wired in
`frontend/src/v4/secondary-tabs.jsx::StepsTab` and the matching
`useAutoWorkbenchTransport` callbacks in `frontend/src/main.jsx`:

- `step-input-${stepId}` (intent textarea) →
  `runtime.updatePendingStepIntent(stepId, intent)`
- `step-outcome-chip-${type}-${stepId}` (10 outcome chips) →
  `runtime.updatePendingStepExpectedOutcome(stepId, {type, source, …})`
- `step-attach-${stepId}` (Attach Element) →
  `runtime.handleAttachElement(stepId)` →
  `sendPayload({type: "arm_picker", step_id})` (`main.jsx:2142-2165`)
- `step-target-${stepId}` (target summary) renders once `element_info`
  arrives from the backend's `picker_picked` event.
- `step-status-${stepId}` (ready badge) renders `ready / draft /
  picking… / needs outcome` purely from local pending step state — no
  fake completion inference.
- `steps-run-all` / `steps-run-selected` → `runtime.handleRunPendingSteps`
  → `sendPayload({type: "run_steps", steps: [...]})` (`main.jsx:2167-2210`)
- Run buttons disable when `blocked` or list empty; `steps-blocked`
  notice surfaces the recovery/permission reason.
- `aria-label="Run Pending Steps"` is preserved on the v4 button so
  the legacy E2E selector continues to anchor.

Coverage added in Pass 4a:

- `frontend/tests-dom/panel-integration.test.jsx`:
  - "Steps tab deep workflow: intent edit, outcome chip, attach, and
    run dispatch through runtime" — drives all four contracts through
    `IDEPanel` + mocked `runtime` and asserts each typed callback.
  - "Steps tab Run-all is disabled and shows blocker copy when blocked
    by pending recovery" — verifies blocked dispatch is suppressed.
  - "Steps tab renders safely when a pending step has no stable id" —
    guards against malformed step state.
- `frontend/tests-dom/secondary-tabs.test.jsx`:
  - Run-selected typed `run_steps` payload.
  - Stable step id used in testids regardless of display order.
  - Run-all suppressed when `blocked=true`.
  - Malformed step never claims "ready".

jsdom: 42 / 42 passed (was 35; +7 from Pass 4a).
Python non-E2E: 2480 / 2480 passed.
E2E `test_v4_panel_smoke.py`: PASS.
E2E `test_mvp_001_lifecycle_smoke.py`: PASS (tab-navigation smoke; deep
workflow round-trip through real backend remains gated by Sprint 7's
"no paid LLM" policy — covered by legacy `test_basic_click_flow.py` if
ever re-enabled with a fake-LLM seam).

What is NOT closed by this bug

The design's per-row visual state badges (strong/weak locator chip,
section-step children, missing-test-data block, wrong-current-page
warning, child-op count) remain unrendered. Those need backend signals
that don't exist yet and are tracked under D-101 (Pass 4b, one
sub-pass per backend seam):

- `step.locator.strength` (strong/weak)
- `step.kind` (atomic / loop / section)
- `step.children[]`
- `step.blocked.reason` + refs
- `step.precondition.{expected_url, current_url}`
- `step.child_op_count`

These are NOT part of BUG-S7-V4-001 by definition (the bug was about the
"intent → attach → outcome → run" workflow); they get their own track.
