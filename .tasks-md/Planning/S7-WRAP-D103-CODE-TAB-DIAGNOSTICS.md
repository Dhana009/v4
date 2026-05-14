# D-103 Code Tab — Export and Diagnostics Mini-Spec

**Status:** ACTIVE  
**Branch:** `s7/clusters-6-11-complete-llm-mode`  
**Spec authored at HEAD:** `6c34187`  
**Date:** 2026-05-14  
**Master spec:** `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md` §13

---

## Decision Summary (4 lines)

`code_update`-only rendering is WORKING — CodeTab reads store truth; no
frontend codegen path exists or is needed. `code-copy` is ACTIVE — clipboard
local, no backend command required. `code-save` is BUILD_P0_SEAM — `onExportCode`
is undefined at runtime (`runtime.onExportCode` has no definition in `main.jsx`),
and no backend handler for `export_code` exists in `agent.py`, `server.py`, or
`browser.py`. Diagnostics rendering from backend payload is ACTIVE but needs
additional jsdom coverage for warning-level rows.

---

## Current State

`CodeTab` in `frontend/src/v4/secondary-tabs.jsx:889` renders backend
`code_update` payloads via the `codePreview` and `codeDiagnostics` props. Basic
render, empty state, and copy-button dispatch are working and covered by existing
jsdom tests. The save button emits `{type:"export_code"}` via `onSave` which is
wired in `frontend/aw-ide-panel.jsx:380` to `runtime.onExportCode`. That
property does not exist anywhere in `frontend/src/main.jsx`'s runtime object
definition — the click handler is a no-op. No backend command handler for
`export_code` exists.

Master spec §6 inventory row for `code-save`:
`DISPATCH_PRESENT / BACKEND_VERIFY → VERIFY_THEN_WIRE`.
After grep verification: backend has **zero** hits for `export_code` in
`agent.py`, `server.py`, `browser.py`, `runtime/`. Fate resolves to
`BUILD_P0_SEAM`.

---

## 1. `code_update`-Only Rendering

### Confirmed behavior

`CodeTab` accepts `codePreview` (string or `{file, code}` object) and
`codeDiagnostics` (array of diagnostic objects). It does NOT generate code
internally. An explicit info strip at render-top states:

> "Code is rendered from `code_update` events. Frontend does not generate code."

The store reducer at `frontend/src/store/reducer.js:222` handles
`EVENT_TYPES.code_update` and updates the store slice read by the panel.
`frontend/src/main.jsx:653` includes `code_update` in its known-event set.
`frontend/aw-ide-panel.jsx:233` reads `runtime.codePreview` and passes it to
`CodeTab`.

### Source-pattern requirement

No test or CI check currently enforces the no-frontend-codegen rule. A
source-pattern test must assert:

- No string template literals that produce TypeScript (`import {`, `test(`,
  `await page.`, `await expect(`) appear in `frontend/src/v4/secondary-tabs.jsx`
  outside of `<pre>` / render-only context.
- No `eval()`, `new Function()`, or dynamic script injection occurs in the
  frontend code path.

This is a jsdom source-pattern check (read the source string; assert absence of
codegen patterns) analogous to the source-pattern test added for D-102 in
`frontend/tests-dom/secondary-tabs.test.jsx`.

### Existing tests that cover this area

- `secondary-tabs.test.jsx:868` — empty state, copy disabled before payload
- `secondary-tabs.test.jsx:874` — renders `codePreview`, diagnostics list,
  copy dispatch
- `panel-integration.test.jsx:152–155` — `code_update` event → store → Code
  tab renders preview, copy enabled

These tests are sufficient evidence that the render-from-backend path is ACTIVE.
No changes needed to existing tests.

---

## 2. Copy / Save / Export Controls

### 2-a. `code-copy` — ACTIVE — `KEEP_ACTIVE`

**Fate:** `KEEP_ACTIVE`

`secondary-tabs.jsx:922–926` — button dispatches
`{type:"copy_code", code: text}` to `onCopy`. In `aw-ide-panel.jsx:379`,
`onCopy` is wired to `runtime.handleCopyRecordedStep ?? runtime.onCopyCode`.
`handleCopyRecordedStep` is defined in `main.jsx:2121` as a `useCallback`.

Clipboard write is a local browser operation. No backend command required.
PRD `05 §Save options` lists clipboard as user convenience, not a backend
command. PRD Hard rule #8 does not restrict clipboard-local copy of the
rendered code string (the code already uses `process.env.XXX` references, not
inline secrets — see §5 below).

**jsdom coverage required:** copy dispatch test exists at
`secondary-tabs.test.jsx:885` (`onCopy` called with `{type:"copy_code"}`).
No new test needed. Verify in acceptance evidence.

### 2-b. `code-save` — DEAD_CONTROL → `BUILD_P0_SEAM`

**Fate:** `BUILD_P0_SEAM`

**What exists:**
- Frontend: `secondary-tabs.jsx:929–932` — button calls `onSave({type:"export_code", code: text})`
- Panel: `aw-ide-panel.jsx:380` — `onSave={runtime.onExportCode}`
- `main.jsx` runtime object — `onExportCode` is **not defined**. The prop
  resolves to `undefined`. Click does nothing silently.

**What does not exist:**
- No `onExportCode` or `handleExportCode` in `main.jsx`
- No `export_code` handler in `agent.py`, `server.py`, `browser.py`
- No WebSocket message dispatch on save click

**PRD basis:**
- `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` Must-have v1 #6 "Live Code View —
  TypeScript updating in real time" (WORKING) and #8 "Save/Load Sessions —
  Save `.spec.ts` + `.session.json`" (PARTIAL — save_session from CardCompleted
  wired; code-specific export not wired)
- `05_CODEGEN_REPLAY_PERSISTENCE.md §Save options` — `[Save]` saves to default
  workspace path; `[Save As]` allows custom path. Both require backend to write
  the file; the frontend cannot write the filesystem.
- `06 §Acceptance matrix — Codegen / Storage` — P0
- `06 §Phase 3 Recording/save/replay` — P0

**Seam to build (minimum viable):**

1. **Frontend side** — define `onExportCode` in `main.jsx` runtime object.
   It must dispatch `{type: "export_code", code: <string>, path: null}` (or
   a save-as dialog value) via the typed WebSocket dispatcher. Until save-as
   dialog exists, `path: null` tells backend to use workspace default.
2. **Backend side** — add a `case "export_code":` branch in the WebSocket
   command router (likely `browser.py` WS handler near line 701 where
   `code_update` is already handled). Handler should:
   - Accept `{type, code, path?}`.
   - Write the code string to workspace default path
     (`<workspace>/autoworkbench-output/<session-name>.spec.ts`) or the given
     `path` if provided.
   - Emit an ack event `{type: "export_code_result", ok: true, path: "<written-path>"}` or
     `{type: "export_code_result", ok: false, error: "<message>"}`.
3. **Frontend ack** — store reducer handles `export_code_result` to show a
   brief success/failure notice on the Code tab (a `data-testid="code-save-result"`
   strip, hidden when `null`).

**Backend seam scope** — touches one command-router entry in `browser.py` plus
a file-write helper. Does not touch `agent.py`, `llm_runtime_controller.py`,
or recording pipeline. Well within the two-module limit from master spec §15.

**Save As and Save Copy** — PRD §05 describes three save variants. For Sprint 7,
implement only the default-path `[Save]` variant. Disable or hide `Save As` and
`Save Copy` controls (they do not yet exist in the UI, so nothing to disable).
Document as `DEFER_TO_SPRINT_8` with a ticket note.

**Contract test required** — see §6.

### 2-c. Export controls (additional) — `HIDE_AS_NON_P0` for Sprint 7

Master spec §6 row: `Code export controls (additional)` — status `MISSING`,
fate `BUILD_P0_SEAM`. These are the "full-spec / step-line / regenerate"
buttons referenced in `V4_TESTID_CONTRACT.md §8` as `PLANNED_D103`.

After cross-walking PRD:
- "Full spec export" = the same `[Save]` path implemented under §2-b.
- "Step-line mapping" (per-step line number display in preview) — PRD `04
  §code_update` payload includes `step_id?` and `operation_id?` per update,
  but a per-line step annotation UI is not named in PRD Must-have v1 #1–#18.
  It appears in `S6-1007 Code tab` planning doc but not in `06 §Acceptance`.
  Fate: `HIDE_AS_NON_P0` for Sprint 7; `DEFER_TO_SPRINT_8`.
- "Regenerate" button — triggers a new `code_update` from backend. No PRD
  Must-have entry for a user-triggered regenerate button. Fate:
  `HIDE_AS_NON_P0`; `DEFER_TO_SPRINT_8`.

No new UI controls to add in Sprint 7 beyond the wired `code-save`.

---

## 3. Diagnostics / Warnings Panel

### Current state

`CodeTab` renders a `<ul data-testid="code-diagnostics">` when
`codeDiagnostics.length > 0`. Each row is `<li data-testid="code-diagnostic-${i}">`.
The level field (`d.level ?? d.severity ?? d.kind ?? "info"`) drives a CSS
class: `warning`/`warn`/`error` → `className="no"`. The message field
(`d.message ?? d.text ?? d.reason`) is the display text.

The `codeDiagnostics` prop flows from `main.jsx:1783` (`useState` initialized
from `config.codeDiagnostics`), updated when the store receives `code_update`
and the payload contains `diagnostics[]`. PRD `04 §code_update` payload
contract:

```
code_update: step_id?, operation_id?, lines[], full_spec_preview, diagnostics[]
```

Backend `agent.py:8323` (`_build_code_update_payload`) is where diagnostics
are assembled. The PRD codegen reviewer rule (`05 §v2.3 codegen reviewer rule`)
says the reviewer is triggered on fragile-locator warnings.

### Warning types to cover in tests

Three specific warnings that backend may emit and UI must render correctly:

1. **Fragile-locator warning** — triggered when a fragile locator is used
   (per `05 §Structure`, the generated code includes a `⚠ Fragile locator`
   comment; the `diagnostics[]` array should include a `{level:"warning",
   message:"Fragile locator — no stable attributes found. Consider adding
   data-testid."}`).
2. **Missing `code_update` warning** — shown in the empty strip (`code-empty`
   testid) when no payload has arrived yet. This is a UI-level notice, not a
   backend diagnostic. Already rendered; needs a test asserting the exact
   testid and that it disappears once `code_update` payload arrives.
3. **Capability-gap warning** — `capability_gap_recorded` events include
   `gap_id` and `needed_capability`. The frontend may surface relevant gaps
   as a diagnostic row in CodeTab when the gap relates to codegen (e.g. an
   iframe or download action that codegen cannot fully represent). This is
   backend-driven; frontend only renders when the payload is present.
   For Sprint 7, add one jsdom test asserting a `code_update` with a
   `{level:"warning", message:"capability gap: ..."}` diagnostic renders
   correctly.

### Render rule (invariant)

Diagnostics panel renders only when backend emits `diagnostics[]` with at
least one entry. Frontend never invents diagnostic rows. An absent or empty
`diagnostics` array means no panel renders. Test must assert panel is absent
when `codeDiagnostics=[]`.

---

## 4. Placeholder / Missing-Code States

### `code-empty` strip

Rendered at `secondary-tabs.jsx:937–940` when `!hasCode`. Carries
`data-testid="code-empty"`. Content: "Awaiting code_update event. No code
rendered yet." This is the correct pre-payload empty state.

**Invariant from master spec §3:** "No `code_update` before `step_recorded`
for the same operation." Frontend does not enforce this — it is a backend
invariant. Frontend simply renders what backend sends. Test confirms that
`codePreview={null}` produces `code-empty` visible + `code-copy` disabled.

### Pre-`step_recorded` guard

Frontend must never render a `code-preview` based on anything other than a
received `code_update` payload. The store reducer at `reducer.js:222` only
sets `codePreview` on `EVENT_TYPES.code_update`. No other event type or local
state should produce a non-null `codePreview`. Source-pattern test (see §1)
covers this.

**Malformed payload safety:** If `code_update` arrives with `code: null` or
`code: undefined`, `CodeTab` falls back to `""` via the `useMemo` at line 890
(`codePreview.code ?? codePreview.content ?? ""`), producing `hasCode = false`
and showing `code-empty`. This is correct. Add one jsdom test for malformed
payload.

---

## 5. Secrets Policy

### Rule

PRD `02_LLM_RUNTIME.md` Hard rule #8:

> "Never log or display secret values. `.env` values never appear in chat or logs."

PRD `05_CODEGEN_REPLAY_PERSISTENCE.md §Secrets rule`:

> Values from `.env` are NEVER shown in chat, logs, or generated code.
> Generated code references env var names, not values:
> ```typescript
> await emailInput.fill(process.env.TEST_EMAIL ?? '')
> await passwordInput.fill(process.env.TEST_PASSWORD ?? '')
> ```

### Enforcement

Secrets redaction is **backend-owned**. The backend codegen pipeline
(`recording/codegen.py`, `agent.py::_build_code_update_payload`) must emit
`process.env.VAR_NAME` references, never inline secret strings. Frontend
renders the string it receives — it does not re-redact.

Frontend responsibility is:
1. Never add any UI path that would re-inject an env value from local state
   into the code preview.
2. The clipboard copy (`code-copy`) copies the exact rendered string. If
   backend has correctly emitted `process.env.TEST_EMAIL`, the copy will
   contain that reference — correct.

### Test required

One jsdom test ("env-var redaction in preview"):
- Render `CodeTab` with `codePreview={{ code: "await fill(process.env.SECRET_KEY ?? '')" }}`.
- Assert `code-preview` text contains `process.env.SECRET_KEY`.
- Assert `code-preview` text does NOT contain any inline value pattern
  (no quoted string of length > 8 that is not a Playwright API call).
- This is a render-truthfulness test, not a runtime redaction test. The
  runtime redaction test lives in backend pytest suite.

---

## 6. Tests Required

### 6-a. jsdom tests (`frontend/tests-dom/secondary-tabs.test.jsx`)

All existing Code tab tests must remain green. New tests to add:

| Test description | Testid / assertion | New? |
|---|---|---|
| Empty state shows `code-empty`, `code-copy` disabled, `code-save` disabled | `code-empty` present; both buttons `disabled` | Already partially covered; add explicit `code-save` disabled assertion |
| Malformed `code_update` payload (`code: null`) shows `code-empty` | `code-empty` present | NEW |
| `code_update` with diagnostics: warning row renders with correct level class | `code-diagnostic-0` has "warning" level text | Already covered for one case; add `error`-level variant |
| Fragile-locator warning renders | `code-diagnostic-0` text contains "Fragile locator" | NEW |
| Capability-gap warning renders | `code-diagnostic-0` text contains "capability gap" | NEW |
| `code-copy` dispatches `{type:"copy_code"}` | `onCopy` called | Covered; keep |
| `code-save` dispatches `{type:"export_code"}` when `onSave` provided | `onSave` called with correct type | NEW |
| `code-save` disabled when no code | `code-save` disabled | NEW explicit assertion |
| `code-save` ack strip shows on `export_code_result` ok | `code-save-result` visible | NEW (after seam built) |
| `code-save` ack strip shows error on `export_code_result` ok=false | `code-save-result` error text | NEW (after seam built) |
| Env-var reference renders verbatim in preview (no inline secret) | `code-preview` text check | NEW |
| Source-pattern: no TypeScript codegen string in secondary-tabs.jsx | string-search of source file | NEW |
| Diagnostics panel absent when `codeDiagnostics=[]` | `code-diagnostics` not in document | NEW |

### 6-b. Backend contract test (after seam built)

Add a pytest test in `tests/test_export_code_handler.py` (or inline in an
existing handler test file):

- Send `{type:"export_code", code:"test('x',()=>{})", path:null}` to the
  WebSocket command router.
- Assert the handler writes a file to workspace default path.
- Assert the handler emits `{type:"export_code_result", ok:true, path:...}`.
- Assert the handler rejects malformed payloads (missing `code` key) with
  `{type:"export_code_result", ok:false, error:...}`.

This test must NOT use a live browser or paid LLM. Use a fake/mock WebSocket
harness consistent with existing backend command tests.

### 6-c. Source-pattern test

A string-search test reads the raw source of `frontend/src/v4/secondary-tabs.jsx`
and asserts absence of TypeScript-generating template patterns
(e.g. strings containing `import { test`, `await page.`, `await expect(`
outside of comment or string-literal render contexts). This mirrors the
pattern used for D-102 evidence. Add to `secondary-tabs.test.jsx` as a
`describe("source-pattern")` block.

---

## 7. E2E Tests

**Verdict: NO new E2E tests for Sprint 7.**

jsdom + smoke is sufficient for Sprint 7 code-tab closure per master spec §10
(smoke tests #1–#2 cover Code tab render; jsdom covers save dispatch).

Sprint 8 may add a local-fixture E2E test that:
- Completes a minimal LLM flow
- Verifies `code_update` arrives and `code-preview` renders
- Clicks `code-save` and confirms the file lands in the workspace

This is deferred. No paid LLM or live-website involvement required.

---

## 8. Acceptance Criteria

1. `code-empty` renders when `codePreview` is `null` or contains no usable
   code string; `code-copy` and `code-save` are both `disabled`.
2. `code-preview` renders the exact string from the backend `code_update`
   payload; no frontend transformation except whitespace-preserving `<pre>`.
3. `code-copy` click calls `onCopy({type:"copy_code", code:<string>})`; local
   clipboard write succeeds without a backend round-trip.
4. `code-save` click calls `onSave({type:"export_code", code:<string>})`,
   which dispatches to the backend WebSocket; backend writes the file and
   emits `export_code_result`; a result strip (`code-save-result`) appears
   with success or error text.
5. `code-diagnostics` list renders only when backend `code_update` payload
   includes at least one diagnostic; each row carries `level` and `message`
   text; panel is absent when `codeDiagnostics=[]`.
6. No inline secret value appears in `code-preview` or clipboard output;
   all credential references render as `process.env.VAR_NAME`.
7. All 13+ new jsdom tests described in §6-a pass; existing Code tab tests
   remain green; `npm test` exits 0.

---

## 9. Stop Conditions

Stop work and ask user when:

- Backend `export_code` seam would require touching more than `browser.py`
  plus one helper module (e.g. if file-write logic forces changes to
  `agent.py` core loop or `llm_runtime_controller.py`).
- The workspace-path logic conflicts with PRD `05 §Workspace-based storage
  rule` in a way that requires a new storage module beyond Sprint 7 scope.
- A jsdom test must be weakened to match broken UI behavior.
- Any paid LLM call would otherwise execute during test.
- PRD `05 §Save As` dialog behavior is required for the default `[Save]`
  path (it should not be — default path requires no dialog).
- `onExportCode` fix propagates into `main.jsx` in a way that changes
  unrelated runtime object members, risking regression in existing tests.

---

## 10. Final Handoff Evidence

At handoff, the following evidence must be recorded in
`SPRINT-007-HANDOFF.md §D-103`:

- [ ] `git log --oneline` commit for `feat(v4): code tab export and diagnostics payload`
- [ ] `npm test` stdout showing all Code tab jsdom tests green (count delta
  from baseline 79 → N)
- [ ] `pytest tests/test_export_code_handler.py -v` stdout showing backend
  contract tests pass
- [ ] `code-save` manual smoke: click saves file to workspace path; result
  strip appears; file contents match `code-preview` text exactly
- [ ] Source-pattern test output showing no TypeScript codegen in
  `secondary-tabs.jsx`
- [ ] `V4_TESTID_CONTRACT.md §8` updated: `code-save-result` row added;
  `PLANNED_D103` export-controls row resolved to `HIDE_AS_NON_P0`
- [ ] `UI_DEFECTS.md` D-103 row updated from Open to Fixed with commit SHA

---

## Files Likely Touched

| File | Change |
|---|---|
| `frontend/src/v4/secondary-tabs.jsx` | Add `code-save-result` ack strip (after seam built); no other structural change |
| `frontend/src/main.jsx` | Define `onExportCode` in runtime object; handle `export_code_result` in event reducer to update `codeSaveResult` slice |
| `frontend/src/store/reducer.js` | Add `export_code_result` case to update `codeSaveResult` state |
| `frontend/src/store/types.js` | Add `export_code_result` to `EVENT_TYPES` |
| `frontend/aw-ide-panel.jsx` | Pass `codeSaveResult` to `CodeTab` as `saveResult` prop |
| `browser.py` | Add `export_code` command case in WS handler; call file-write helper |
| `tests/test_export_code_handler.py` | New backend contract test file |
| `frontend/tests-dom/secondary-tabs.test.jsx` | New jsdom tests per §6-a |
| `.tasks-md/Audit/V4_TESTID_CONTRACT.md §8` | Add `code-save-result` row; resolve `PLANNED_D103` |
| `.tasks-md/Audit/UI_DEFECTS.md` | Close D-103 at handoff |

**Do not touch:** `agent.py` core loop, `llm_runtime_controller.py`,
`recording/codegen.py`, `recording/replay.py`, `runtime/` modules (unless
`browser.py` delegation requires a one-line import from an already-existing
helper).
