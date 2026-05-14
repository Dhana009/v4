# Sprint 8 — Bug / Deferred Work Tickets

This file collects bugs and deferred work surfaced during Sprint 7 closeout
that require backend or cross-stack work in Sprint 8. Each entry has its own
heading; agents owning a Sprint 8 cluster append (do not rewrite) sections
here as new tickets are filed.

---

## BUG-S8-AGENT-001 — Wire Agent Control Center (backend events + frontend toggles)

**Filed by:** D-106 closeout (Sprint 7 wrap, Batch C Part 2).
**Status:** OPEN.
**PRD references:** `03 §Agent Control Center`, `07 §7 Agent Control Center`,
`04 §Multi-model event additions` (lines 92–107), `07 §8 Backend event
contract additions`, `06 §Multi-model`.
**Sprint 7 closure verdict:** `DISABLED_WITH_REASON` (see D-106 in
`.tasks-md/Audit/UI_DEFECTS.md`). Fake `DEFAULT_AGENTS` fallback removed from
production runtime; popover renders honest empty/read-only state until this
ticket lands.

### Why this is deferred to Sprint 8

The multi-model Agent Control Center UI was classified non-P0 for Sprint 7
closure (master spec §5 negative indicator: "07 Multi-model orchestration
agent control center → non-P0 for Sprint 7 closeout"). Page Intelligence
*runtime* IS P0 (Phase 2 LLM MVP depends on it) and its backend seam is
already wired (S7-0203), but the *multi-model UI surfacing* — agent registry
events, per-agent progress/result/failure events, agent enable/disable
commands, and trace view — is not. Today the backend emits **zero**
`agent_settings / agent_progress / agent_result / agent_failed / agent_trace`
events (grep evidence: no hits in `runtime/`, `agent.py`, `server.py`,
`frontend/src/`) and `server.py` has no handler for `set_agent_enabled`.

### Scope

Backend agent registry events + frontend store handling + agent control
commands + Agent Control Center popover wiring.

### Acceptance criteria

1. Backend emits `agent_settings` on WebSocket connect with
   `{ type: "agent_settings", agents: [ { key, name, required, enabled, model, status } ] }`.
2. Backend emits `agent_started / agent_progress / agent_result / agent_failed`
   events per agent run with typed payloads per `04 §agent_*`.
3. `server.py` handles `set_agent_enabled` command; validates agent key;
   rejects attempts to disable required agents; broadcasts updated
   `agent_settings`.
4. `runtime/event_contracts.py` adds `set_agent_enabled` to
   `SUPPORTED_FRONTEND_COMMAND_TYPES`; adds `agent_settings`,
   `agent_started`, `agent_progress`, `agent_result`, `agent_failed`,
   `agent_trace` to the typed backend event contract.
5. Frontend reducer processes `agent_settings` → updates `store.agents`.
6. Frontend reducer processes `agent_started / agent_progress / agent_result
   / agent_failed` → updates per-agent status in `store.agents`.
7. `AgentsPopover` continues to read `agents` from store (already wired in
   D-106); empty-state branch yields only when backend has not yet emitted
   `agent_settings`.
8. Non-required toggles dispatch typed `set_agent_enabled` on click; remain
   disabled while a request is in flight and re-enable on
   `agent_settings` broadcast.
9. Required toggles remain locked (already correct in D-106).
10. Header count strip derives from live store state (currently the
    `aw-agents-sprint8-badge` is shown in its place — replace with a live
    `N active · M off` strip backed by `store.agents`).
11. `agent_trace` event populates a trace view (design TBD; coordinate with
    Trace tab D-104 scope to avoid duplication).
12. jsdom tests cover: `agent_settings` reducer, toggle dispatch, required-
    locked behavior, empty-state branch when no `agent_settings` received.
13. Backend contract tests cover: `set_agent_enabled` accepts valid keys,
    rejects required-disable attempts and unknown keys; `agent_settings`
    emitted on connect; per-agent progress/result/failed events round-trip.

### Out of scope for this ticket

- Run Page Intelligence Now, Clear Cache, Show Agent Trace full view,
  Judge/Risk Agent — all deferred to Sprint 9 per `07 §Phase 5`.
- Any UI for editing agent model assignments (separate ticket).

### Evidence required at close

1. `grep -rn "agent_settings\|agent_progress\|agent_result\|agent_failed\|agent_trace\|set_agent_enabled" runtime/ agent.py server.py frontend/src/`
   returns non-zero hits across all four paths.
2. Backend contract tests GREEN.
3. jsdom tests GREEN; new tests cover registry, dispatch, empty-state branch.
4. `AgentsPopover` `aw-agents-empty` testid disappears once backend emits
   `agent_settings` in the smoke flow.
5. UI_DEFECTS.md D-106 row updated to point at this ticket as ENABLED.

### Architecture invariants (must hold)

- Backend owns runtime truth.
- Frontend never invents agent state.
- No dead clickable controls.
- No paid LLM calls in tests; no live website in tests.
- No test weakening.
