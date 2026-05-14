# D-104 — Trace Tab: Filters, Failure Detail, Telemetry, Artifacts, Capability Gaps

**Status:** PLANNING
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Parent spec:** `SPRINT-007-WRAP-UP-MASTER-SPEC.md`
**Defect entry:** `UI_DEFECTS.md` D-104
**PRD sources:** `FE §9` (Trace tab), `02 §26.7 Token telemetry`, `02 Hard rule #8`, `04 §step_failed / capability_gap_recorded / agent_trace`

---

## Decision Summary

| Item | Decision |
|---|---|
| Filter chips | KEEP_ACTIVE — already rendered from hardcoded category set; verified correct |
| Structured event rows | KEEP_ACTIVE — rows render from `traceEntries` store prop; no raw prose |
| Failure detail panel | WIRE_EXISTING_SEAM — `step_failed` payload exists; panel is MISSING; add render only |
| LLM telemetry detail | WIRE_EXISTING_SEAM — `token_budget_policy.py` logs telemetry; backend does NOT currently emit a typed frontend event; render "unavailable" state honestly until wired |
| Artifact list | WIRE_EXISTING_SEAM — `normalizeTraceArtifacts` + `TRACE_ARTIFACT_LABELS` already parse artifacts from trace entries; add render in TraceTab |
| Redaction status | WIRE_EXISTING_SEAM — `normalizeTraceEntry` already extracts `redactionStatus`/`redactionWarning`; add chip render; never claim redaction worked if field absent |
| Capability-gap entries | WIRE_EXISTING_SEAM — reducer wires `capability_gap_recorded` to `trace_entries`; add category chip "gap" + card render |
| New backend events | NONE — no new events proposed; PRD gap (telemetry event) noted but classified non-blocking for Sprint 7 |

All fates are WIRE_EXISTING_SEAM or KEEP_ACTIVE. No new backend seams required for Sprint 7 acceptance.

---

## 1. Current State

`TraceTab` in `frontend/src/v4/secondary-tabs.jsx:977` renders:
- A text filter input (`trace-filter`)
- Six category chips (`trace-filter-${k}` for `all / llm / step / permission / error / code`)
- A list of flat `trace-row-${i}` divs showing `timestamp · type · description`

What is absent:
- No expanded row / detail panel for `step_failed` events
- No LLM telemetry row (model, tokens, cost, latency)
- No artifact list with `data-artifact-href` links
- No redaction status chip
- No capability-gap category or card
- No "unavailable" honest state for missing telemetry

Store pipeline is healthy: `main.jsx::normalizeTraceEntry` already extracts `redactionStatus`, `redactionWarning`, `evidenceRef`, `artifacts[]`, `severity`, `diagnostic` from every entry. `TraceTab` ignores all of those fields — it only reads `r.type`, `r.text`, `r.description`, `r.timestamp`, `r.severity`.

---

## 2. Control Inventory (Trace Tab Only)

| Control | data-testid | Source line | Current state | Fate |
|---|---|---|---|---|
| Text filter input | `trace-filter` | `secondary-tabs.jsx:995` | ACTIVE | KEEP_ACTIVE |
| Category chip — all | `trace-filter-all` | `secondary-tabs.jsx:1003` | ACTIVE | KEEP_ACTIVE |
| Category chip — llm | `trace-filter-llm` | `secondary-tabs.jsx:1003` | ACTIVE | KEEP_ACTIVE |
| Category chip — step | `trace-filter-step` | `secondary-tabs.jsx:1003` | ACTIVE | KEEP_ACTIVE |
| Category chip — permission | `trace-filter-permission` | `secondary-tabs.jsx:1003` | ACTIVE | KEEP_ACTIVE |
| Category chip — error | `trace-filter-error` | `secondary-tabs.jsx:1003` | ACTIVE | KEEP_ACTIVE |
| Category chip — code | `trace-filter-code` | `secondary-tabs.jsx:1003` | ACTIVE | KEEP_ACTIVE |
| Category chip — gap (new) | `trace-filter-gap` | to be added | MISSING | WIRE_EXISTING_SEAM |
| Trace row | `trace-row-${i}` | `secondary-tabs.jsx:1026` | ACTIVE | KEEP_ACTIVE |
| Failure detail panel | (none) | — | MISSING | WIRE_EXISTING_SEAM |
| Telemetry row | (none) | — | MISSING | WIRE_EXISTING_SEAM |
| Artifact list | (none) | — | MISSING | WIRE_EXISTING_SEAM |
| Redaction chip | (none) | — | MISSING | WIRE_EXISTING_SEAM |
| Capability-gap card | (none) | — | MISSING | WIRE_EXISTING_SEAM |

### Filter chip category set — verified

Hardcoded in `secondary-tabs.jsx:999`:
```js
["all", "llm", "step", "permission", "error", "code"]
```
Filter logic at line 983: `type.startsWith(kind)`.

Known event types (`KNOWN_TYPES` set at line 969) cover: `run_started`, `plan_ready`, `clarification_needed`, `recommendation_ready`, `permission_required`, `locator_ambiguous`, `recovery_needed`, `step_validating`, `step_executing`, `step_failed`, `step_skipped`, `step_recorded`, `code_update`, `replay_started`, `replay_result`, `run_completed`, `runtime_rejected`, `session_state`, `schema_error`, `error`.

Category "gap" must be added as a seventh chip. Filter match: `type === "capability_gap_recorded"` (exact match, not prefix, since no other events start with "gap"). Implementation: extend the chip array and add a `gap` branch in the filter predicate.

---

## 3. Structured Event Rows

Rows already render from `traceEntries` prop, which is sourced from:
- `main.jsx:1773` — local `traceEntries` state (built by `normalizeTraceEntries`)
- `aw-ide-panel.jsx:235` — falls back to `runtime.storeTraceEntries` (from `transport.storeState?.trace_entries`)

`normalizeTraceEntry` (main.jsx:726) produces a rich object including `type`, `category`, `timestamp`, `source`, `summary`, `evidenceRef`, `redactionStatus`, `redactionWarning`, `rejectionReason`, `artifacts[]`, `diagnostic`, `severity`. Frontend never fabricates events — all fields come from backend message or are left empty.

PRD §04 requirement: "Frontend should ignore unknown events only after logging them visibly for developers." Current code satisfies this: unknown events get `data-known="0"` and a diagnostic label.

No change required to the row rendering pipeline. The expansion panels proposed below attach to the existing row divs.

---

## 4. Failure Detail Panel — WIRE_EXISTING_SEAM

### Current `step_failed` payload (verified from `event_contracts.py:491`)

```json
{
  "type": "step_failed",
  "step_id": "<str>",
  "run_id": "<str>",
  "error": "<str>",
  "status": "recovery_pending | failed",
  "operation_id": "<str | absent>"
}
```

`agent.py:3714` emits this payload via `build_step_failed_payload`. The error string is `context["last_error"]` — a plain English description of what went wrong. No `locator_tried`, `expected_vs_observed`, or `recovery_state` fields are in the current contract.

### What to render

The failure detail panel renders inline below the `trace-row-${i}` div when `r.type === "step_failed"` and the row is expanded (click-to-expand). Fields:

| Field | Source in normalized entry | Render rule |
|---|---|---|
| step_id | `r.raw.step_id` or `r.raw.payload.step_id` | Always show if present |
| error message | `r.summary` (already extracted by normalizeTraceEntry from payload.error) | Always show |
| status | `r.raw.payload.status ?? r.raw.status` | Show as badge |
| operation_id | `r.raw.payload.operation_id` | Show if present; omit if absent |
| locator tried | absent from current contract | Omit; no fabrication |
| expected vs observed | absent from current contract | Omit; no fabrication |
| recovery state | absent from current contract | Show "Recovery entered — see Recovery card" as static note |
| artifact links | `r.artifacts[]` from normalizeTraceEntry | Show if non-empty |

### New test-ids (trace contract additions)

| Element | data-testid | Condition |
|---|---|---|
| Expanded detail wrapper | `trace-failure-detail-${i}` | row expanded + type === step_failed |
| Step id field | `trace-failure-step-${i}` | present in payload |
| Error text | `trace-failure-error-${i}` | always when panel shown |
| Status badge | `trace-failure-status-${i}` | always when panel shown |
| Operation id (if present) | `trace-failure-op-${i}` | only if operation_id present |

Expansion state: local React `useState` per row or a single `expandedRow` index in the component. Click toggles. No new backend seam required.

### Stop condition

If a future backend seam adds `locator_tried`, `expected_url`, `observed_url`, `recovery_state` to `step_failed`, extend this panel then. Do not pre-build fields that have no payload source.

---

## 5. LLM Call / Token / Context / Tool-Policy Details — WIRE_EXISTING_SEAM (honest unavailable)

### What backend currently emits

`runtime/token_budget_policy.py` maintains an in-process `_telemetry_log` and logs `[LLM_TELEMETRY]` lines to stdout. It does NOT emit a typed WebSocket event to the frontend. `runtime/telemetry.py::_format_telemetry_line` prints to stdout only.

`04_BACKEND_EVENT_CONTRACT.md` defines `agent_trace { items[] }` with model, tokens, cost, latency. This event is not yet emitted for regular Step Runner LLM calls (only the multi-agent control center path would emit it). This is not PRD-P0 for Sprint 7 standalone — the acceptance matrix does not name a frontend token display as Phase 1–4 requirement.

### Render rule

When a `trace-row-${i}` has `r.type` that starts with `llm` (e.g. `llm_thinking`, `llm_result`) or is `agent_trace`:
- If `r.raw.payload.model` or `r.raw.model` present: show model id
- If `r.raw.payload.input_tokens` or `r.raw.payload.total_input_tokens` present: show token counts
- If `r.raw.payload.output_tokens` present: show output tokens
- If `r.raw.payload.estimated_cost` present: show cost
- If `r.raw.payload.latency_ms` present: show latency
- If none present: render `data-testid="trace-llm-unavailable-${i}"` with text "LLM telemetry not in this event payload"

This is an honest "unavailable" state. Frontend must not infer or synthesize token counts.

### New test-ids

| Element | data-testid | Condition |
|---|---|---|
| Telemetry section | `trace-llm-telemetry-${i}` | type starts with llm or is agent_trace, expanded |
| Model id | `trace-llm-model-${i}` | payload.model present |
| Input tokens | `trace-llm-input-tokens-${i}` | payload.input_tokens present |
| Output tokens | `trace-llm-output-tokens-${i}` | payload.output_tokens present |
| Cost estimate | `trace-llm-cost-${i}` | payload.estimated_cost present |
| Latency | `trace-llm-latency-${i}` | payload.latency_ms present |
| Unavailable notice | `trace-llm-unavailable-${i}` | none of the above present |

---

## 6. Artifact / Redaction Status — WIRE_EXISTING_SEAM

### Current pipeline

`main.jsx::normalizeTraceEntry` already extracts:
- `artifacts[]` — array of `{ key, label, path?, status?, note? }` objects via `normalizeTraceArtifacts`
- `redactionStatus` — from `payload.redaction_status` / `payload.redaction_report` / etc.
- `redactionWarning` — from `payload.redaction_warning` / etc.

`TRACE_ARTIFACT_LABELS` (main.jsx:666) maps known artifact keys to human labels: `manifest`, `test_result`, `summary`, `events`, `commands`, `rejections`, `redaction_report`.

`TraceTab` currently ignores all of these. Adding render is purely additive.

### Render rule — artifact list

When `r.artifacts.length > 0` (rendered in expanded row or unconditionally as a sub-section):
```
[artifact.label]  [→ link]
```
- `data-testid="trace-artifact-list-${i}"`
- Per item: `data-testid="trace-artifact-${i}-${artifact.key}"` with `data-artifact-href="${artifact.path}"`.
- If `artifact.path` absent: render label only, no link. Never fabricate a URL.
- If `artifact.status` present: render `data-testid="trace-artifact-status-${i}-${artifact.key}"` with `data-status="${artifact.status}"` as an inline chip.

### Render rule — redaction status

When `r.redactionStatus` is non-empty:
- Render `data-testid="trace-redaction-chip-${i}"` with `data-status="${r.redactionStatus}"`.
- If `r.redactionWarning` non-empty: render `data-testid="trace-redaction-warning-${i}"` with the warning text.

When `r.redactionStatus` is absent and the event type is `step_recorded` or `code_update`: render nothing. Do not claim "redaction applied" without evidence.

---

## 7. Capability-Gap Entries — WIRE_EXISTING_SEAM

### Backend state

`capability_gap_recorded` appears in `KNOWN_TRACE_EVENT_TYPES` (main.jsx:656). The reducer at `main.jsx:833` includes it in the set that triggers evidence-required behavior. The event is listed in PRD `04` lifecycle events table. Backend `capability_registry.py` defines the gap structure. The gap event is not yet emitted as a standalone WebSocket event by the Step Runner directly (it is produced inside `dom_locator_contract.py` as an internal classification). S7-0208 is cited in master §7 as WORKING for the reducer side.

Fate per master §7: `CONTRACT_ONLY (reducer wired; visible card minimal)`.

### Render rule

Add `gap` as a seventh filter chip (`trace-filter-gap`). Filter predicate: `type === "capability_gap_recorded"`.

When `r.type === "capability_gap_recorded"` and row is expanded:
- `data-testid="trace-gap-card-${i}"`
- Gap id: `data-testid="trace-gap-id-${i}"` — from `r.raw.payload.gap_id`
- Capability needed: `data-testid="trace-gap-capability-${i}"` — from `r.raw.payload.needed_capability`
- Path: `data-testid="trace-gap-path-${i}"` — from `r.raw.payload.path`
- All fields conditional on payload presence; no fabrication.
- Non-blocking notice label: "Capability gap logged — non-blocking"

---

## 8. Tests Required

### 8a. jsdom tests (new, in `secondary-tabs.test.jsx`)

All tests use JSDOM + React Testing Library. No paid LLM, no live browser.

| Test | Description |
|---|---|
| `filter chip — default is all` | render TraceTab with entries; verify `trace-filter-all` has active class; others inactive |
| `filter chip — select step` | click `trace-filter-step`; verify only `step_*` type entries visible |
| `filter chip — gap added` | verify `trace-filter-gap` renders; click it; only `capability_gap_recorded` entries visible |
| `filter chip — text filter` | type in `trace-filter` input; verify rows filtered by summary text |
| `failure detail — expand on step_failed` | render trace with `step_failed` entry; click row; verify `trace-failure-detail-${i}` renders with `trace-failure-step-${i}`, `trace-failure-error-${i}`, `trace-failure-status-${i}` |
| `failure detail — no fabricated fields` | same; verify no `locator_tried` / `expected_url` / `observed_url` elements exist |
| `telemetry — unavailable state` | render entry with `type=llm_thinking` and no token fields; expand; verify `trace-llm-unavailable-${i}` renders |
| `telemetry — model and tokens` | render entry with `type=llm_result`, `payload.model="claude-3-5-haiku"`, `input_tokens=1200`, `output_tokens=80`; verify `trace-llm-model-${i}`, `trace-llm-input-tokens-${i}`, `trace-llm-output-tokens-${i}` present |
| `artifact list — renders with href` | render entry with `artifacts=[{key:"redaction_report", path:"/tmp/r.json"}]`; verify `trace-artifact-redaction_report` with `data-artifact-href="/tmp/r.json"` |
| `artifact list — no link when path absent` | artifact without `path`; verify no `<a>` or href attribute |
| `redaction chip — shows when status present` | entry with `redactionStatus="clean"`; verify `trace-redaction-chip-${i}` with `data-status="clean"` |
| `redaction chip — absent when field missing` | entry with no redactionStatus on step_recorded; verify no `trace-redaction-chip-${i}` |
| `capability gap card` | render entry with `type=capability_gap_recorded`, `gap_id="g1"`, `needed_capability="hover"`; expand; verify `trace-gap-card-${i}`, `trace-gap-id-${i}`, `trace-gap-capability-${i}` |

### 8b. Source-pattern test

Add one test asserting no `traceEntries` fixture fabricates events with mock data — all trace entries must come from the store prop or be empty. Pattern: grep the test file and verify no hardcoded `type: "step_failed"` objects without a corresponding `step_id` + `error` field (confirms the contract is respected in test fixtures too).

---

## 9. E2E

NO. jsdom is sufficient for Sprint 7. Trace tab E2E deferred to Sprint 8 per master §2 (E2E expansion is Sprint 8 scope).

---

## 10. Acceptance Criteria

1. Category chips `all / llm / step / permission / error / code / gap` render; clicking each filters `trace-row-${i}` entries to matching `type` prefix (or exact match for `gap`); `trace-filter` text input further narrows by summary.
2. `step_failed` rows are expandable; the failure detail panel (`trace-failure-detail-${i}`) renders `step_id`, `error`, `status`, and `operation_id` (if present) from the backend payload; no field is fabricated or inferred when absent from payload.
3. LLM-type rows render telemetry fields (model, tokens, cost, latency) when present in payload; when absent, `trace-llm-unavailable-${i}` renders with an honest "not available" label; no synthesized token counts appear.
4. Artifact list (`trace-artifact-list-${i}`) renders for every entry that has `r.artifacts.length > 0`; each item carries `data-artifact-href` only when backend provides a path; no href is fabricated.
5. Redaction chip (`trace-redaction-chip-${i}`) renders only when `r.redactionStatus` is non-empty; absent on entries where the backend has not provided a redaction status; never claims "clean" without evidence.
6. `capability_gap_recorded` events render under the `gap` filter chip; expanded card shows `gap_id`, `needed_capability`, `path` from payload; non-blocking label present.
7. All 13 new jsdom tests pass; `npm test` stays green; `npm run build` clean; no new skips or xfails.

---

## 11. Stop Conditions

Stop and escalate to user when any of:

- Extending `step_failed` payload with `locator_tried` / `expected_vs_observed` / `recovery_state` would require touching more than `event_contracts.py` + `agent.py` + one test file — that is broader than this defect's scope.
- Backend telemetry event (`agent_trace`) emission from the Step Runner path requires changes to `llm_runtime_controller.py` and would add a new emitted event that the PRD does not explicitly name as Phase 1–4 Sprint 7 acceptance — classify as Sprint 8 and document under §15 of master spec.
- Any jsdom test requires weakening an existing assertion to pass.
- `npm test` or `npm run build` fails after the render changes and the root cause is not in this file.

---

## 12. Files Likely Touched

| File | Change |
|---|---|
| `frontend/src/v4/secondary-tabs.jsx` | Add: gap chip, expand state, failure-detail panel, telemetry section, artifact list, redaction chip, gap card |
| `frontend/tests-dom/secondary-tabs.test.jsx` | Add: 13 new trace tab tests |
| `.tasks-md/Audit/V4_TESTID_CONTRACT.md` §9 | Add: all new trace testids in same commit |

No backend changes. No new store reducer cases. `normalizeTraceEntry` in `main.jsx` already produces all needed fields.

---

## 13. Final Handoff Evidence Required

- [ ] `npm test` output showing all new trace tests passing (green summary line)
- [ ] `npm run build` output — clean, no warnings about trace-related imports
- [ ] Source diff of `secondary-tabs.jsx` showing no hardcoded mock trace events
- [ ] `V4_TESTID_CONTRACT.md §9` updated with all new testids
- [ ] `UI_DEFECTS.md` D-104 row moved from Open to Fixed with this spec referenced
