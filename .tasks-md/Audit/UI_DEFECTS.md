# UI Defects — Tab-by-Tab Shadow DOM Audit

Tracking visible defects in the v4 panel after the design port. Each defect
includes the screenshot path used as evidence, the root cause, and the fix
status.

Audit method:
- `bash scripts/launch.sh` with `AUTOWORKBENCH_REMOTE_DEBUGGING_PORT=9222`.
- `python tools/audit_walk.py initial walk_tabs` produces a screenshot per tab
  under `/tmp/aw-audit/tab_*.png`.
- Verify against design source `frontend_new_design_prototype/yui/project/*`.

## Fixed

| ID | Tab | Symptom | Root cause | Fix |
|----|-----|---------|------------|-----|
| D-001 | All | Footer reads "PLANNING / LAST: TIMELINE" on fresh load | `useState` defaults for `runState` + `interactionMode` set to `"planning"` instead of `"idle"`; backend `AUTOWORKBENCH_DEFAULT_CONFIG` also seeded `state: "planning"` | `frontend/src/main.jsx` defaults flipped to `"idle"`; `toPanelState` default branch returns `"idle"`; `browser.py` bootstrap config now `state: "idle"` |
| D-002 | LLM | Now strip shows "Backend is drafting a plan." at idle | Side effect of D-001 (state=planning → meta.kind=run → strip rendered) | Resolved by D-001 |
| D-003 | LLM | `DraftPendingPanel` ("Run Pending Steps" card) renders before any user activity | Auto-created empty pending step satisfied the old condition `pendingSteps.length > 0` | `LlmThread` now checks `pendingSteps.some(s => s.intent.trim() || s.element_info)` so empty drafts stay hidden |
| D-004 | All | `harness.py` selectors targeted legacy `#aw-root` shadow id that does not exist in v4 | v4 host id is `#autoworkbench-root` with `#aw-shadow-mount` inside the shadow root | `find_autoworkbench_panel`/`find_autoworkbench_state_locator`/`wait_for_autoworkbench_ready` use the v4 ids |
| D-005 | Backend | `[FRONT]` log lines not visible in `/tmp/aw-launch.log` | No frontend → backend log ingest path | Added `runtime/log.py` + `POST /api/log` + `frontend/src/log.js` with ring buffer, console, and backend POST |

## Open

| ID | Tab | Symptom | Root cause | Plan |
|----|-----|---------|------------|------|
| D-101 | Steps | Design's per-row state badges (strong/weak locator, section step, missing-data block, wrong-page warning, child-op count) are not rendered | `frontend/src/v4/secondary-tabs.jsx::StepsTab` is the pre-design layout; backend doesn't yet emit the underlying signals | **Deep workflow portion fixed in Pass 4a** (intent input, outcome chips, Attach Element → `arm_picker`, target summary, ready badge, typed `run_steps` dispatch, Run-selected, Run-blocked, malformed-step safety — covered by jsdom in `panel-integration.test.jsx::Steps tab deep workflow*` and `secondary-tabs.test.jsx::StepsTab*`). **Visual design-state port deferred to Pass 4b** (one sub-pass per backend seam): `step.locator.strength` (strong/weak), `step.kind` (atomic/loop/section), `step.children[]` (section child ops), `step.blocked.reason` + refs, `step.precondition` (expected vs current URL), `step.child_op_count`. Frontend must not invent these — see Pass 1B rule against static-mock-as-live-state. |
| D-102 | Recorded | Tab body renders the legacy minimal list ("No recorded steps yet. They appear here after `step_recorded`…") instead of the design's per-row evidence card (locator used, validation count, observed vs expected, screenshot link, replay status) | `RecordedTab` not redesigned | Port design `RecordedTab` when backend emits richer `step_recorded` payload |
| D-103 | Code | Code tab shows "Awaiting code_update event. No code rendered yet." with minimal controls; design has copy/save/file-path/diagnostics panel | `CodeTab` not redesigned | Port design `CodeTab` when backend emits expanded `code_update` payload |
| D-104 | Trace | Trace tab shows raw event list ("ready", "session_state"). Design wants filter chips by category + structured rows + failure detail panel | `TraceTab` not redesigned | Port design `TraceTab`. Backend already emits sufficient trace entries |
| D-105 | Header | "LLM/Manual" mode toggle renders but flipping does nothing visible | `setMode` only updates panel local state, doesn't show `ManualBuilder` (design's manual step composer) | Either wire `ManualBuilder` (design) into Steps tab, or remove the toggle until backend supports manual-mode commands |
| D-106 | Header | Agents popover lists default DEFAULT_AGENTS mock; backend doesn't emit `agent_settings` so toggles dispatch no command | Backend lacks agent registry events | Document as orphan; render real list once backend grows the contract |
| D-107 | Composer | Pick element / camera buttons in Composer have no handler | Pickelement wiring lives only on the Steps tab | Either wire Composer pick button to `runtime.handleAttachElement`, or remove them |
| D-108 | LlmThread | `CardRecommendation`, `CardPlanDiff`, `CardSchemaError`, `CardOffline` cards exist with mock content; some still render mock copy because LlmThread checks state-only gates without payload presence | Orphan cards before backend event contracts exist | Already gated `CardRecommendation` and `CardPlanDiff` on payload; do same for any remaining mock-only cards |

## How to reproduce

```
# fresh launch with debug port + headed Chromium
lsof -ti:8765 | xargs kill -9 2>/dev/null
rm -rf .pw-user-data
AUTOWORKBENCH_REMOTE_DEBUGGING_PORT=9222 bash scripts/launch.sh > /tmp/aw-launch.log 2>&1 &
sleep 12
python tools/audit_walk.py initial walk_tabs
# Screenshots: /tmp/aw-audit/tab_*.png
# Backend log: /tmp/aw-launch.log (includes frontend ingest via /api/log)
```
