# S7 Mock / Static Gating Audit — D-108 Findings

**Sprint:** 7 Wrap-Up — Batch C Part 3
**Ticket:** D-108
**Date:** 2026-05-14
**Audit HEAD baseline:** `c3115f070b4d937f5fb865d36dcf7601620b8224`
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Spec:** `.tasks-md/Planning/S7-WRAP-D108-MOCK-STATIC-GATING-AUDIT.md`

---

## Verdict

**CLEAN — no remediation required.**

The major runtime-reachable mock (`DEFAULT_AGENTS` array in `chrome.jsx`)
was already removed during D-106. A second-pass scan across the production
frontend surface confirms no other fabricated step / recorded / code / trace /
agent / plan data is reachable from a runtime render path. Reducer initial
state is honest empty everywhere (null plan, empty arrays for steps /
recorded / trace / recommendations).

A source-pattern jsdom guard test (`frontend/tests-dom/static-audit.test.jsx`)
is added to prevent regression — it scans every production source file for a
forbidden-identifier list and asserts each main tab renders empty-state
markers when fed empty props.

---

## Files Scanned

Production frontend surface (audit scope):

| # | File | LOC | Result |
|---|------|-----|--------|
| 1 | `frontend/aw-ide-panel.jsx` | 486 | CLEAN |
| 2 | `frontend/src/main.jsx` | 3361 | CLEAN |
| 3 | `frontend/src/v4/chrome.jsx` | 376 | CLEAN (DEFAULT_AGENTS removed in D-106) |
| 4 | `frontend/src/v4/llm-cards.jsx` | 1105 | CLEAN |
| 5 | `frontend/src/v4/secondary-tabs.jsx` | 1434 | CLEAN |
| 6 | `frontend/src/v4/icons.jsx` | 63 | CLEAN (SVG paths only) |
| 7 | `frontend/src/store/reducer.js` | 245 | CLEAN (initial state empty) |
| 8 | `frontend/src/store/selectors.js` | 54 | CLEAN |
| 9 | `frontend/src/store/types.js` | 56 | CLEAN |
| 10 | `frontend/src/commands/command-builder.js` | — | CLEAN |
| 11 | `frontend/src/commands/dispatcher.js` | — | CLEAN |
| 12 | `frontend/src/commands/validation.js` | — | CLEAN |
| 13 | `frontend/src/layout/dock-controller.js` | — | CLEAN (UI default only) |
| 14 | `frontend/src/layout/panel-modes.js` | — | CLEAN (UI default only) |

Out of scope (allowed): `frontend_new_design_prototype/**`,
`frontend/tests-dom/**`, `frontend/src/components/manual/**` (unimported S8
stubs).

---

## Scan Method

```
grep -rEn "DEFAULT_|SAMPLE_|MOCK_|FAKE_|DEMO_|PROTOTYPE_" \
  frontend/src/ frontend/aw-ide-panel.jsx
```

Filtered through `grep -v node_modules`, `grep -v tests-dom`,
`grep -v components/manual`.

### Matches by category

| File:line | Identifier | Category | Verdict |
|---|---|---|---|
| `frontend/src/main.jsx:25` | `DEFAULT_CONFIG` | UI layout default (state/tab/panelWidth/density) — no runtime data semantics | KEEP |
| `frontend/src/main.jsx:106..111` | `DEFAULT_CONFIG.*` usage | Fallback for missing config field, value is a string/number — not fabricated data | KEEP |
| `frontend/src/layout/dock-controller.js:5,13,30` | `DEFAULT_DOCK_MODE` | Layout mode enum value (`"dock-right"`) | KEEP |
| `frontend/src/layout/panel-modes.js:10,30,47` | `DEFAULT_PANEL_MODE` | Layout mode enum value (`PANEL_MODES.expanded`) | KEEP |
| `frontend/src/v4/chrome.jsx:241` | comment "no DEFAULT_AGENTS in production path" | Audit trail comment (only DEFAULT_AGENTS reference in tree) | KEEP |

Second-pass scan for fake-data comments
(`grep -rEn "// (TODO\|FIXME\|XXX\|mock\|fake\|stub\|demo\|prototype)"`):
no runtime-relevant hits in production files.

Third-pass scan for top-level array/object constants
(`grep -nE "^const [A-Z_]+ *= *\[|^const [A-Z_]+ *= *\{"`):

| File:line | Const | Category | Verdict |
|---|---|---|---|
| `frontend/src/v4/chrome.jsx:6` | `STATUS_MAP` | Status-code label table | KEEP |
| `frontend/src/main.jsx:25` | `DEFAULT_CONFIG` | UI default (already covered) | KEEP |
| `frontend/src/main.jsx:38` | `RUN_STATE_ALIASES` | Backend phase alias map | KEEP |
| `frontend/src/main.jsx:55` | `INTERACTION_MODE_ALIASES` | Backend mode alias map | KEEP |
| `frontend/src/main.jsx:473` | `EXPECTED_OUTCOME_TYPES` | Enum value list for chips | KEEP |
| `frontend/src/main.jsx:667` | `TRACE_ARTIFACT_LABELS` | Artifact-kind label map | KEEP |
| `frontend/src/v4/secondary-tabs.jsx:17` | `EXPECTED_OUTCOME_TYPES` | Enum value list | KEEP |
| `frontend/src/v4/secondary-tabs.jsx:54` | `_STEP_KIND_LABELS` | Step kind label map | KEEP |
| `frontend/src/v4/secondary-tabs.jsx:213` | `_BLOCKED_REASON_LABELS` | Blocked reason label map | KEEP |
| `frontend/aw-ide-panel.jsx:35` | `TAB_ALIAS` | Tab key alias map | KEEP |
| `frontend/aw-ide-panel.jsx:51` | `PHASE_META` | Phase → display meta map | KEEP |
| `frontend/aw-ide-panel.jsx:64` | `PANEL_STATE_ALIAS` | Panel state alias map | KEEP |

All matches are enum tables, label maps, alias maps, or UI defaults. None
fabricate step/recorded/code/trace/agent payload.

---

## Reducer Initial State Verification

`createInitialState()` in `frontend/src/store/reducer.js:10-30`:

```
connected: false
run_id: null
phase: "idle"
plan: null
pending_steps: []
recorded_steps: []
pending_clarification: null
pending_permission: null
pending_recovery: null
pending_recommendations: []
code_preview: null
code_save_result: null
trace_entries: []
errors: []
interaction_mode: "idle"
last_error: null
session_metadata: null
```

No `agents` key seeded. `aw-ide-panel.jsx` passes
`runtime.storeState?.agents ?? []` into `AgentsPopover`, which gates on
`length > 0` and renders `aw-agents-empty` otherwise. Honest path verified.

---

## Findings

**Zero actionable findings.** No fake runtime data, no fabricated rows, no
hardcoded plan_id/run_id/step_id, no inline mock arrays in JSX.

## Remediations Applied

**None — audit clean.** Only test infrastructure added (regression guard).

---

## Regression Guard Test

**File:** `frontend/tests-dom/static-audit.test.jsx`

Sections:

1. **Source-pattern guards** — for each of 12 production source files and
   each of 21 forbidden identifiers (`DEFAULT_AGENTS`, `SAMPLE_STEPS`,
   `MOCK_PLAN`, `FAKE_RECORDED`, `DEMO_AGENTS`, `PROTOTYPE_STEPS`, …),
   asserts the identifier is absent from non-comment source. Plus a
   targeted guard against `|| DEFAULT_AGENTS` / `?? DEFAULT_AGENTS`
   fallback usage.
2. **Reducer initial state** — asserts every fabricatable field is empty/
   null. Catches a future change that seeds e.g. a default plan.
3. **Tab empty-state render** — renders `StepsTab`, `RecordedTab`,
   `CodeTab`, `TraceTab`, `AgentsPopover` each with empty props and
   asserts the canonical empty-state testid (`steps-empty`,
   `recorded-empty`, `code-empty`, `trace-empty`, `aw-agents-empty`)
   is present and no `step-row-*` / `recorded-row-*` / `trace-row-*` /
   `aw-agent-row-*` fabricated rows are rendered.

---

## Validation

- jsdom: **403 passed** (was 159 baseline; +244 new audit assertions —
  per-identifier × per-file source-pattern checks)
- `npm run build`: clean (1.4 mb js, 81.4 kb css, 5 warnings unchanged)
- pytest: **2638 passed, 1 skipped, 2 xfailed** (unchanged from baseline)

---

## D-108 Status

**CLOSED — clean audit + regression guard installed.**

Evidence:
- This file: `.tasks-md/Audit/S7_MOCK_AUDIT_FINDINGS.md`
- Guard test: `frontend/tests-dom/static-audit.test.jsx`
- D-106 already removed `DEFAULT_AGENTS` from production path
- `CardOffline` / `CardSchemaError` payload-gated as documented in
  `S7-WRAP-D108-MOCK-STATIC-GATING-AUDIT.md` §4
