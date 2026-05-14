# BUG-S7-V4-001 — v4 Steps tab is missing the deep "intent → attach → outcome → run" workflow

**Severity:** medium
**Status:** Open
**Cluster:** Sprint 8 Integration Pass (deep workflow port)
**Filed:** 2026-05-14

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
