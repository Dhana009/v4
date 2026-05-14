# D-108 — Mock / Static Gating Audit
**Sprint 7 Wrap-Up mini-spec**
**Ticket:** D-108
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Spec authored at HEAD:** `6c34187`
**Date:** 2026-05-14

---

## Decision Summary

REMEDIATION_REQUIRED — one runtime-reachable mock data source confirmed
(`DEFAULT_AGENTS`). All other surveyed constants are label / enum maps or
UI-only display defaults with no mock runtime data semantics.

`CardOffline` and `CardSchemaError` are already payload-gated (return null
unless prop present). No additional mock-copy gates required for those cards.

`agentsSummary` in `aw-ide-panel.jsx` is a computed display hint derived from
`phase` — it is NOT mock agent data. Label-safe, keep as-is.

---

## 1. Audit Verdict

**REMEDIATION_REQUIRED**

| Row | Identifier | Why |
|---|---|---|
| `frontend/src/v4/chrome.jsx:208` | `DEFAULT_AGENTS` fallback renders 5 hardcoded agent objects when `agents` prop is empty | Runtime-reachable every time the popover opens before backend emits `agent_settings` |

All other constants are CLEAN (label tables, enum maps, UI display defaults).

---

## 2. Audit Checklist Table

| File:line | Identifier | Reach | Category | Fate | Ticket |
|---|---|---|---|---|---|
| `frontend/src/v4/chrome.jsx:281–287` | `DEFAULT_AGENTS` (5 agent objects) | YES | MOCK_DATA | GATE_ON_PAYLOAD | D-108 |
| `frontend/src/v4/chrome.jsx:208` | `DEFAULT_AGENTS` fallback branch in `AgentsPopover` | YES | MOCK_DATA | GATE_ON_PAYLOAD | D-108 |
| `frontend/aw-ide-panel.jsx:287–295` | `agentsSummary` computed from `phase` ("on"/"off"/"run" strings) | NO — derived from real `storeState.phase` | LABEL | KEEP | — |
| `frontend/aw-ide-panel.jsx:460` | `runtime.storeState?.agents ?? []` passed to `AgentsPopover` | NO — payload or empty array; fallback is empty not mock | EMPTY_STATE | KEEP | — |
| `frontend/src/v4/chrome.jsx:6–11` | `STATUS_MAP` (connected/busy/reconnect/offline/error) | NO — lookup table, keys are backend-emitted status strings | LABEL | KEEP | — |
| `frontend/src/v4/chrome.jsx:24` | `agentsSummary = ["on","on","on","off","off"]` default prop on `Header` | NO — prop default never reached at runtime; caller always supplies computed value | LABEL | KEEP | — |
| `frontend/src/v4/llm-cards.jsx:831–857` | `CardOffline` | NO — gated `if (!connection \|\| connection.connected) return null` | EMPTY_STATE | KEEP | — |
| `frontend/src/v4/llm-cards.jsx:862–895` | `CardSchemaError` | NO — gated `if (!rejection) return null` | EMPTY_STATE | KEEP | — |
| `frontend/src/main.jsx:25–30` | `DEFAULT_CONFIG` (state/tab/panelWidth/density) | NO — UI layout defaults, no runtime data semantics | LABEL | KEEP | — |
| `frontend/src/v4/secondary-tabs.jsx:449` | `placeholder="click Get started"` | NO — HTML placeholder attr, not data | LABEL | KEEP | — |
| `frontend/src/v4/secondary-tabs.jsx:573` | `placeholder="Filter steps…"` | NO — HTML placeholder attr | LABEL | KEEP | — |
| `frontend/src/v4/secondary-tabs.jsx:995` | `placeholder="Filter events…"` | NO — HTML placeholder attr | LABEL | KEEP | — |

---

## 3. Remediation Paragraphs

### `DEFAULT_AGENTS` — `frontend/src/v4/chrome.jsx:208,281`

**What to gate on:** `AgentsPopover` must not render mock agent rows when the
backend has not emitted `agent_settings`. Gate the popover body on
`agents.length > 0`: when the prop is empty, render an explicit empty state
("No agent data received yet — waiting for backend.") rather than falling
through to `DEFAULT_AGENTS`.

**Payload key:** `agent_settings` event sets `storeState.agents` (array of
agent objects with `key`, `name`, `status`, etc.). The parent `aw-ide-panel.jsx`
already passes `runtime.storeState?.agents ?? []`; the problem is the fallback
inside `AgentsPopover` itself.

**Fallback empty state:** if `agents` prop is an empty array, render a single
informational row with text "Agent data not yet available" and no interactive
controls — no `DEFAULT_AGENTS` substitution. This satisfies D-106
`DISABLE_WITH_REASON` fate: agent rows remain disabled but their content comes
from backend or shows an honest empty state.

**Commit:** `chore(v4): gate DEFAULT_AGENTS on payload — D-108`

---

## 4. CardSchemaError / CardOffline Mock-Copy Gates

Per UI_DEFECTS.md D-108 note: "some [cards] still render mock copy because
LlmThread checks state-only gates without payload presence."

Current source (verified at HEAD):

| Card | Gate in source | Status |
|---|---|---|
| `CardOffline` (`llm-cards.jsx:831`) | `if (!connection \|\| connection.connected) return null` — renders only when `connection.connected === false` | CLEAN — no mock copy; renders backend `connection.last_event` or null |
| `CardSchemaError` (`llm-cards.jsx:862`) | `if (!rejection) return null` — renders only when `rejection` prop is truthy | CLEAN — renders `rejection.reason ?? rejection.message ?? "The LLM response did not validate."` (last fallback is a valid error-state string, not mock data) |

Both cards are already correctly payload-gated. No additional action required
for D-108. The D-108 note in UI_DEFECTS.md predates the gating commits for
`CardRecommendation` and `CardPlanDiff`; those were fixed in prior passes.

Remaining copy in `CardSchemaError` line 873:
`"The LLM response did not validate."` — this is a valid fallback error string,
not mock data. Fate: **KEEP**.

---

## 5. Source-Pattern Test Proposed

### Regex guard (whitelist approach)

Only `frontend/src/v4/chrome.jsx` may declare `DEFAULT_AGENTS`. Any other file
declaring a runtime-default agent list or referencing `DEFAULT_AGENTS` outside
that file is a defect.

**Pattern A — guard new declarations:**

```
# Fail if any file OTHER than chrome.jsx declares an array named DEFAULT_AGENTS
grep -rn "DEFAULT_AGENTS" frontend/src/ \
  --include="*.jsx" --include="*.js" \
  | grep -v "frontend/src/v4/chrome.jsx" \
  | grep -v "\.test\." \
  | grep -q . && echo "FAIL: DEFAULT_AGENTS declared outside chrome.jsx" && exit 1 \
  || echo "OK"
```

**Pattern B — guard render-path reference without payload check:**

The specific defect pattern is: `DEFAULT_AGENTS` used as a fallback when
`agents` prop is empty without showing an explicit empty state. After the
remediation commit the pattern `|| DEFAULT_AGENTS` must not exist:

```
grep -n "|| DEFAULT_AGENTS\|?? DEFAULT_AGENTS" frontend/src/v4/chrome.jsx \
  | grep -q . && echo "FAIL: DEFAULT_AGENTS used as runtime fallback" && exit 1 \
  || echo "OK"
```

**Whitelist file** (optional, for CI): `.tasks-md/Audit/mock-data-whitelist.txt`
listing each allowed declaration with file and reason — seeded with one entry:

```
# File that may declare agent label defaults (D-108 — becomes empty-state after gating)
frontend/src/v4/chrome.jsx  DEFAULT_AGENTS  LABEL_ONLY_AFTER_GATING
```

---

## 6. Tests Required

### Source-pattern tests (shell / Jest)

| Test ID | File | Assert |
|---|---|---|
| SP-D108-01 | New `frontend/tests/source-patterns/mock-gating.test.js` | `DEFAULT_AGENTS` declared only in `chrome.jsx`; no other file references it |
| SP-D108-02 | Same file | `|| DEFAULT_AGENTS` and `?? DEFAULT_AGENTS` strings absent from `chrome.jsx` after remediation |
| SP-D108-03 | Same file | `AgentsPopover` renders an element with `data-testid="aw-agents-empty"` when `agents` prop is `[]` |

### jsdom tests

| Test ID | File | Assert |
|---|---|---|
| JD-D108-01 | `frontend/tests/chrome.test.jsx` | `AgentsPopover` with `agents=[]` renders `[data-testid="aw-agents-empty"]`, does NOT render `[data-testid^="aw-agent-row-"]` |
| JD-D108-02 | `frontend/tests/chrome.test.jsx` | `AgentsPopover` with valid `agents` array renders correct rows, no DEFAULT_AGENTS bleed-through |
| JD-D108-03 | `frontend/tests/chrome.test.jsx` | `AgentsPopover` empty-state row has no interactive `<button>` elements (all controls absent when no payload) |

### E2E: NO (per spec instruction)

---

## 7. Acceptance Criteria

1. `DEFAULT_AGENTS` array is still declared in `chrome.jsx` but is NOT used as
   a runtime fallback in any render path. It may remain as a label reference or
   be removed entirely.
2. `AgentsPopover` with an empty `agents` prop renders a non-mock empty state
   (text "Agent data not yet available" or equivalent), no agent rows.
3. `AgentsPopover` with a populated `agents` prop (from `storeState.agents`)
   renders exactly those rows and no hardcoded rows.
4. Source-pattern tests SP-D108-01 and SP-D108-02 pass.
5. jsdom tests JD-D108-01..03 pass.
6. `npm test` green, `npm run build` clean.
7. No mock agent data visible in the panel at any runtime phase before
   `agent_settings` is received from the backend.

---

## 8. Stop Conditions

Stop and escalate to user if:

- Gating `DEFAULT_AGENTS` requires changes to the `agent_settings` backend
  event schema beyond what `storeState.agents` already supports.
- Removing `DEFAULT_AGENTS` visually breaks a D-106 acceptance criterion
  (agent popover must still render, just empty).
- Any grep reveals additional MOCK_DATA hits outside `chrome.jsx` — audit must
  be expanded before proceeding.
- PRD §07 or §03 §Agent Control Center imposes a specific empty-state
  requirement that conflicts with the "no mock rows" fate.

---

## 9. Final Handoff Evidence (§13 citation)

Handoff §13 D-108 slot must record:

- Verdict: REMEDIATION_REQUIRED → RESOLVED
- Commit SHA of `chore(v4): gate DEFAULT_AGENTS on payload — D-108`
- Zero MOCK_DATA rows remaining in audit checklist table (§2)
- SP-D108-01, SP-D108-02 pass evidence (grep stdout)
- JD-D108-01..03 pass evidence (Jest output line count)
- `AgentsPopover` empty-state screenshot or jsdom assertion evidence
- Confirmation that `CardOffline` and `CardSchemaError` gates verified CLEAN

§13 must cite **zero MOCK_DATA rows** with `Reach: YES`. One row existed at
audit open; it must be closed by the remediation commit before this slot can
be marked DONE.
