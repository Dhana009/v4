# D-106 — Agent Popover Policy (Sprint 7 Closeout)

**Status:** DISABLED_WITH_REASON — Sprint 7 closeout. All non-required toggles
disabled. Required rows locked. Popover carries "Read-only — Sprint 8" badge.
No fake agent activity. Agent Control Center controls deferred to Sprint 8
(BUG-S8-AGENT-001).

**Master spec:** `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md`
**Fate code:** `DISABLE_WITH_REASON` (§5 rule 3 + §7 row "Agent visibility /
control center")
**Branch:** `s7/clusters-6-11-complete-llm-mode`

---

## Decision Summary

Agent Control Center is a **non-P0 feature for Sprint 7 closure.** Per master
§7, the row is already classified `DEFERRED_TO_SPRINT_8`. Per master §5 P0
negative indicator: "07 Multi-model orchestration agent control center → non-P0
for Sprint 7 closeout." Page Intelligence *runtime* IS P0 (Phase 2 LLM MVP
depends on it); the *multi-model UI surfacing* — including toggle controls,
status display, and event binding — is not.

Backend emits **zero** `agent_settings / agent_progress / agent_result /
agent_failed / agent_trace` events today (confirmed by grep: no hits in
`runtime/`, `agent.py`, `server.py`). Frontend has no reducer for any
`agent_*` event. The non-required toggle buttons (`aw-agent-toggle-${key}`)
carry no `onClick` handler and no `disabled` attribute — they are dead controls
in the §5 sense.

**Chosen approach: Option B — label-only read-only popover.**
Keep `DEFAULT_AGENTS` as a label-source (names, initials, required flag) but
treat it as display scaffolding, not runtime truth. All toggles are disabled
with explanatory `title`. Required-agent rows show "Always on" badge. Header
carries "Read-only — Sprint 8" badge. This preserves UX consistency while
satisfying the §8 disabled-control requirements without hiding the surface
entirely.

---

## 1. Verdict

**DISABLED_WITH_REASON — Sprint 7 closeout.**

- All non-required agent toggles are disabled (`disabled` attribute present).
- Required-agent toggles remain locked-disabled (already the case).
- Popover header shows "Read-only — Sprint 8" badge.
- No agent activity is simulated, inferred, or animated.
- Sprint 8 ticket: **BUG-S8-AGENT-001** (see §6).

---

## 2. Current State

File: `frontend/src/v4/chrome.jsx`

| Element | Line | testid | Handler | disabled? |
|---|---|---|---|---|
| `AgentsPopover` component | 207 | `aw-agents-popover` | `onClose` prop | — |
| Popover close X | 228 | `aw-agents-close` | `onClose` | no |
| Required toggle (locked) | 261 | none | none | YES (hardcoded) |
| Non-required toggle | 263 | `aw-agent-toggle-${key}` | **none** | NO (missing) |
| Popover header count strip | 227 | none | — | derives from DEFAULT_AGENTS |

`AgentsPopover` fallback (line 208):

```js
const list = Array.isArray(agents) && agents.length ? agents : DEFAULT_AGENTS;
```

When backend sends no `agents` prop (always today), `DEFAULT_AGENTS` is used as
runtime truth — a mock-data-as-live-state violation per master §14 and §3
invariants. The five hardcoded agent objects are:

```
orch  — Main Orchestrator  — required
pi    — Page Intelligence  — not required
sr    — Step Runner        — required
dbg   — Debug Agent        — not required
cg    — Codegen Reviewer   — not required
```

Three non-required toggles (`pi`, `dbg`, `cg`) have no handler and no
`disabled` attribute → dead clickable controls per master §8 rule "No dead
clickable controls."

The header count strip (`{list.filter(...).length} active · ... off`) always
reads from `DEFAULT_AGENTS` → emits `"2 active · 0 off"` regardless of backend
state — a false status display.

---

## 3. PRD-P0 Basis

### What IS P0

- `PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md` Phase 1–4,
  Must-have #1–#18 — these define Sprint 7 P0 scope.
- Page Intelligence runtime (`07 §3.2`, Phase 2 LLM MVP) — Page Intelligence
  *runs* as a backend subsystem. Its backend seam is WORKING (S7-0203). That
  is P0.

### What is NOT P0

- `07_MULTI_MODEL_ORCHESTRATION.md §7` Agent Control Center UI — toggles,
  status display, trace view, enable/disable commands.
- `03_FRONTEND_RUNTIME.md §Agent Control Center` — same scope.
- `06 Phase 5` advanced/polish → explicitly non-P0.
- `06 §Should have` and `06 §Deferred v2+` items.
- Master §5 negative indicator (verbatim): "07 Multi-model orchestration agent
  control center → non-P0 for Sprint 7 closeout (Page Intelligence usage IS P0
  because Phase 2 LLM MVP depends on it; the multi-model UI surfacing is not)."

**Conclusion:** Wiring `agent_settings / agent_progress / agent_result /
agent_failed / agent_trace` events and the `set_agent_enabled` command is
Sprint 8 scope. The popover popover surface itself can remain visible in a
read-only, honestly-labelled state.

---

## 4. Backend Status (Grep Evidence)

Search scope: `runtime/`, `agent.py`, `server.py`, `frontend/src/`

```
grep -rn "agent_settings|agent_progress|agent_result|agent_failed|agent_trace|set_agent_enabled" runtime/ agent.py server.py frontend/src/
```

**Result: zero hits across all four paths.**

No `agent_settings` event is emitted on connect.
No `agent_progress / agent_result / agent_failed / agent_trace` events are
emitted during any run.
No handler for `set_agent_enabled` command exists in `server.py` or `agent.py`.
No frontend reducer processes any `agent_*` event type.

The `04_BACKEND_EVENT_CONTRACT.md` §Multi-model additions defines these at
lines 92–107 as required contract items, but none are implemented.
`07_MULTI_MODEL_ORCHESTRATION.md §8` defines the same event/command shapes.

---

## 5. Plan — What to Change

### Approach: Option B (label-only read-only)

`DEFAULT_AGENTS` stays as the label source (names, initials, required flag).
It is NOT runtime truth. The fallback path `agents.length ? agents : DEFAULT_AGENTS`
continues to serve the label source role, but the header count strip and status
display must not imply live backend state.

### Changes to `AgentsPopover` in `chrome.jsx`

1. **Header badge.** Add `<span className="aw-agents-sprint8-badge">Read-only — Sprint 8</span>` in `aw-agents-head`, replacing or supplementing the active/off count strip. The count strip must be removed or hidden (it currently shows false live counts from `DEFAULT_AGENTS`).

2. **Required-agent rows.** Toggle remains `disabled` (already locked). Add `title="Required — always on"` for accessibility. No change to lock icon or "Required" badge.

3. **Non-required toggles.** Add:
   - `disabled` attribute (boolean, always present)
   - `title="Agent controls deferred to Sprint 8 (BUG-S8-AGENT-001)"`
   - Remove misleading active/standby status dot behavior (status dot may stay but must not imply a live signal)

4. **`last:` field.** Remove or replace with static `"—"` placeholder while backend emits no events. Do not display `DEFAULT_AGENTS` `last` strings as live state.

5. **`aw-agent-status` dot.** Set all non-required rows to `standby` class statically. Do not derive from `DEFAULT_AGENTS.status` as if it were live.

### Result testid surface (unchanged from existing)

| testid | Role | After change |
|---|---|---|
| `aw-agents-popover` | Popover container | unchanged |
| `aw-agents-close` | Close X | unchanged |
| `aw-agent-row-${key}` | Per-row container | unchanged |
| `aw-agent-toggle-${key}` | Non-required toggle | `disabled=true` + `title=` added |
| (none) | Required toggle | `disabled=true` + `title="Required — always on"` |

### Files to touch

- `frontend/src/v4/chrome.jsx` — `AgentsPopover` function only (lines 207–278)
- `frontend/src/v4/chrome.jsx` — `DEFAULT_AGENTS` label comment update (line 281)

No backend files. No new files. No new event types.

### Commit

```
chore(v4): disable agent popover controls with reason (D-106)
```

---

## 6. Sprint 8 Ticket — BUG-S8-AGENT-001

**Title:** Wire Agent Control Center — backend events + frontend toggles

**Scope:** Multi-model orchestration UI surfacing deferred from Sprint 7.

### Acceptance criteria

1. Backend emits `agent_settings` on WebSocket connect with `{ agents: [ { key, name, required, enabled, model, status } ] }`.
2. Backend emits `agent_started / agent_progress / agent_result / agent_failed` events per agent run with typed payloads per `04 §agent_*`.
3. `server.py` handles `set_agent_enabled` command; validates agent key; rejects attempt to disable required agents; broadcasts updated `agent_settings`.
4. Frontend reducer processes `agent_settings` → updates `store.agents`.
5. Frontend reducer processes `agent_started / agent_progress / agent_result / agent_failed` → updates per-agent status in `store.agents`.
6. `AgentsPopover` receives `agents` prop from store; `DEFAULT_AGENTS` fallback is removed or gated on empty store (not empty prop).
7. Non-required toggles are re-enabled; `onClick` dispatches `set_agent_enabled`.
8. Header count strip derives from live store, not static array.
9. Required toggles remain locked.
10. `agent_trace` event populates a trace view (design TBD in Sprint 8 spec).
11. jsdom tests cover: `agent_settings` reducer, toggle dispatch, required-locked behavior, disabled-fallback when no event received.
12. Backend contract tests cover: `set_agent_enabled` accepts/rejects, `agent_settings` emitted on connect.

**PRD references:** `03 §Agent Control Center`, `07 §7 Agent Control Center`,
`04 §Multi-model event additions` (lines 92–107), `07 §8 Backend event contract
additions`.

**Not in scope for BUG-S8-AGENT-001:** Run Page Intelligence Now, Clear Cache,
Show Agent Trace full view, Judge/Risk Agent (all deferred to S9 per `07 §Phase
5`).

---

## 7. Tests Required

### jsdom (required before D-106 commit)

File: `frontend/src/v4/__tests__/chrome.test.jsx` (or existing chrome test file)

| Test | Assertion |
|---|---|
| "AgentsPopover non-required toggles are disabled with title" | All `aw-agent-toggle-${key}` elements have `disabled=true` and `title` containing "BUG-S8-AGENT-001" |
| "AgentsPopover required toggles are locked-disabled" | Required-row toggle has `disabled=true` |
| "AgentsPopover non-required click does nothing" | Simulate click on disabled toggle; assert no dispatch called |
| "AgentsPopover header shows Sprint 8 badge" | Element with class `aw-agents-sprint8-badge` or `data-testid="aw-agents-sprint8-badge"` is present |
| "AgentsPopover renders all five DEFAULT_AGENTS rows" | Five `aw-agent-row-*` elements present when no agents prop passed |

All five tests must pass before the D-106 commit lands. No test weakening.
No xfail. No skip.

### E2E

**NO E2E for D-106.** The popover is a read-only label surface. E2E coverage of
agent toggles waits for BUG-S8-AGENT-001 when backend events exist.

---

## 8. Acceptance Criteria (D-106 done when all true)

1. `AgentsPopover` non-required toggles all have `disabled` attribute.
2. Non-required toggles have `title="Agent controls deferred to Sprint 8 (BUG-S8-AGENT-001)"`.
3. Required toggles have `disabled` and `title="Required — always on"`.
4. Header count strip removed or replaced with "Read-only — Sprint 8" badge — no false live counts.
5. `last:` field shows `"—"` placeholder, not `DEFAULT_AGENTS` live-state strings.
6. `DEFAULT_AGENTS` comment updated to clarify it is a label source, not runtime truth.
7. All five jsdom tests (§7) pass.
8. `npm test` green (zero regressions vs 79/79 baseline).
9. `npm run build` clean.
10. BUG-S8-AGENT-001 ticket filed under `.tasks-md/Bugs/BUG-S8-AGENT-001.md`.
11. Master §7 row "Agent visibility / control center" `Final` column updated to `DISABLED_WITH_REASON`.
12. Handoff §14 "Disabled controls and reasons" entry added for `aw-agent-toggle-*`.

---

## 9. Stop Conditions

Stop and ask user if any of:

- A new backend event type would need to be emitted before popover renders correctly at this step.
- Disabling the toggles requires touching any file outside `chrome.jsx` + its test file.
- PRD interpretation of "Agent Control Center" changes from non-P0 to P0 for Sprint 7 closure.
- Test suite drops below 79/79 after D-106 changes.
- The `AgentsPopover` refactor risks breaking the `aw-agents-toggle` open/close behavior in `Header`.

None of the above are expected given Option B scope.

---

## 10. Final Handoff Evidence Required

After D-106 commit:

1. `git log --oneline -3` showing commit `chore(v4): disable agent popover controls with reason (D-106)`.
2. `npm test` output: 79/79 (or higher if D-106 adds tests) passed, 0 failed.
3. `npm run build` output: clean, no warnings on D-106 paths.
4. Grep confirmation: `grep -n "disabled" frontend/src/v4/chrome.jsx` shows `disabled` on all toggle buttons in `AgentsPopover`.
5. BUG-S8-AGENT-001 ticket file exists at `.tasks-md/Bugs/BUG-S8-AGENT-001.md`.
6. Master §7 "Agent visibility / control center" row `Final` = `DISABLED_WITH_REASON`.
