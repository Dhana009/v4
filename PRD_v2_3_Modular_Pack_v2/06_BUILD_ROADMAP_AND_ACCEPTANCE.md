# 06 — Build Roadmap and Acceptance

> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance.


## v2.3 implementation phases

### Phase 1 — Core runtime + frontend/backend contract

Goal: stabilize the foundation used by all modes.

Scope:

```text
browser launch
AutoWorkbench UI injection
typed WebSocket event contract
Step Runner basic lifecycle
Tool Runtime safety
frontend interaction modes
recorded parent/child data model
```

### Expected criteria

- Frontend and backend agree through typed events/commands.
- Plan, clarification, recovery, executing, and completed modes are visually distinct.
- Backend is source of truth for step lifecycle.
- Docked panel direction is documented; MVP injection continues working.


### Phase 2 — Complete LLM Mode MVP

Goal: make the brain work reliably.

Scope:

```text
single-step flow
section multi-action flow
queued step flow
plan correction
recovery correction
capability gap logging
code_update for successful operations
```

### Expected criteria

- Single picked element action records and generates code.
- Selected section with multiple goals decomposes into child operations.
- Wrong plan can be corrected before execution.
- Failure enters recovery and does not finalize unresolved.
- Missing capabilities are recorded under workspace gap log.


### Phase 3 — Recording, save, replay, repair, versioning

Goal: complete the actual product loop.

Scope:

```text
start/stop recording
save session/spec
load session
replay one/all
LLM repair during replay
locator replacement flow
save version
```

### Expected criteria

- User can record a flow and save it to the active workspace.
- User can load a previous recording and replay it.
- Broken replay step invokes LLM repair.
- Validated repair updates recording/code and can be saved as a new version.


### Phase 4 — Manual Mode using same runtime

Goal: provide precise manual control without duplicating architecture.

Scope:

```text
manual pick/action/assert controls
manual validation
same Step Runner
same codegen
LLM repair only on failure or explicit request
```

### Expected criteria

- Manual Mode reuses Step Runner, Tool Runtime, Recorder, and Codegen.
- Manual steps can be replayed and repaired like LLM-recorded steps.
- Manual Mode does not fork a separate incompatible architecture.


### Phase 5 — Advanced actions, persistence, and polish

Scope:

```text
upload/download/popup/iframe/dropdown/network/auth hardening
page maps
persistent locator library
session_state reconnect
Shadow DOM + docked layout host
UX polish
```

### Expected criteria

- Advanced Playwright vocabulary is supported in both LLM and Manual flows.
- Reconnect restores UI from session_state.
- Panel can dock/resize without covering page content.
- Token telemetry and context governance are measurable.



## Multi-model implementation track

Multi-model orchestration is not required before the base LLM Mode MVP works, but the architecture must remain compatible with it.

Recommended order:

```text
1. Token/cost telemetry for every model call
2. Deterministic extractor and Context Manager cleanup
3. Page Intelligence / Locator Agent using nano model
4. Agent Control Center UI visibility/toggles
5. Debug Agent specialization
6. Codegen Reviewer Agent
7. Optional Judge/Risk Agent
```

### Expected criteria

- Token telemetry exists before adding specialist model calls.
- Page Intelligence / Locator Agent can be disabled without breaking core LLM Mode.
- Nano model produces structured page intelligence, not free-form final decisions.
- Step Runner validates all candidates produced by nano model.
- Debug Agent activates only on failure/replay repair/explicit debug request.
- Codegen Reviewer reviews deterministic output; it does not replace backend-owned codegen.
- UI shows agent activity, reason, cost/latency, and result summary.


## Acceptance matrix

| Area | Working means |
|---|---|
| LLM Mode | single step, multi-action section, queued steps, correction, recovery, recording, code_update pass |
| Recording | parent step + child operations stored with locators, status, generated lines, and history |
| Replay | replay one/all, failure repair, validated update, version save |
| Locator update | alternatives generated/scored/validated; chosen locator updates code/replay |
| Frontend | interaction modes correct; no state inferred from prose; clear UX feedback |
| Backend contract | typed events/commands; session_state later for reconnect/load |
| Codegen | generated TypeScript runs without manual cleanup |
| Storage | output defaults to active workspace; custom save path supported |
| Capability gaps | unsupported feature recorded, visible, and non-blocking |
| Multi-model | optional agents have clear scope/triggers; Page Intelligence uses nano model; all outputs are validated by Step Runner |

## Tests that must exist before calling LLM Mode MVP complete

1. Pick one button → click → confirm → recorded → code line.
2. Pick one heading → has_text assertion with `&nbsp;` → recorded → code line.
3. Select section → request multiple assertions/actions → parent step + child operations.
4. Wrong plan order → correction before execution → revised plan executes only.
5. Click navigates before old-page assertion → recovery asks/repairs → no finalization while unresolved.
6. Replay saved flow → broken locator → LLM repair → save new version.
7. User requests better locator → alternatives validated → code/replay updated.
8. Missing capability → gap logged under workspace.
9. WebSocket reconnect → session_state restores frontend state.
10. Docked UI mode → panel does not cover target content.
11. Disable Page Intelligence Agent → core LLM Mode still works with deterministic extraction/main model fallback.
12. Bad div/span page → nano Page Intelligence Agent proposes candidates; Step Runner validates; fragile warning shown if needed.

## What not to build yet

- Do not restart UI from scratch.
- Do not replace AutoWorkbench with a giant browser.py string UI.
- Do not implement full extension architecture in this version.
- Do not build every advanced action before LLM/record/replay core works.
- Do not let frontend simulate backend truth.
- Do not let LLM final prose be source of truth.

---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 roadmap/scope sections

### Must have (v1 required)

| # | Feature | Description |
|---|---|---|
| 1 | **Manual Mode** | Full Playwright vocabulary, element picker, dropdown action selector, immediate validation |
| 2 | **LLM Mode** | Plain English steps, full LLM agent loop, all actions handled automatically |
| 3 | **Locator Engine** | 11-strategy programmatic waterfall + LLM fallback, confidence scoring |
| 4 | **Validation** | Immediate live validation on every step, unified pipeline |
| 5 | **Recovery Loop** | 4-stage repair cascade, LLM fallback, human escalation as last resort |
| 6 | **Live Code View** | TypeScript updating in real time as steps are added |
| 7 | **Replay** | Full replay with auto-fix, per-step replay, range replay |
| 8 | **Save/Load Sessions** | Save `.spec.ts` + `.session.json`, load and continue |
| 9 | **Version Snapshots** | Named versions in SQLite, save/load/delete |
| 10 | **Pause/Stop/Continue/Skip** | Full execution controls at any time |
| 11 | **Persistent Locator Library** | Remembers validated locators across sessions |
| 12 | **Page Maps** | Explore once, store, reuse — zero re-exploration cost |
| 13 | **Session Memory** | MEMORY.md, error patterns — gets smarter every session |
| 14 | **Skills System** | 24 SKILL.md files loaded contextually into LLM prompts |
| 15 | **Overlay Panel** | Iframe injection, docking, element picker, highlight layer |
| 16 | **Auth State Management** | Save/load storage state, multi-user support |
| 17 | **Step Management** | Add/edit/delete/reorder steps without re-executing |
| 18 | **Locator Inspector** | Inspect any element's locator options without recording |

### Should have (v1 if time, v2 otherwise)

| # | Feature | Description |
|---|---|---|
| 19 | **Self-healing Tests** | When replay fails due to locator change, auto-find new locator |
| 20 | **Assertion Builder** | Visual guided assertion creation in panel |
| 21 | **Network Capture Panel** | View/filter captured API calls, generate assertions and mocks |
| 22 | **Smart Suggestions** | Proactive suggestions after actions (save auth, add assertion) |

### Deferred (v2+)

Exploration mode (full systematic), Debug mode, Accessibility testing, Test parameterization, Test tagging/filtering, Import existing tests, Visual diff/baseline screenshots, Smart wait analyzer, Test diff viewer, Annotations on steps.

---

These components are solid, async-native, and should be used as-is:

| Component | File | Reason to keep |
|---|---|---|
| `BrowserSession` | `execution/browser.py` | Reliable async Playwright browser lifecycle |
| `ToolRuntime` | `execution/tools.py` | Complete Playwright action vocabulary, all edge cases |
| `StepGraphRunner` | `execution/runner.py` | Step loop with retries, events, checkpoints |
| `LocatorEngine` | `locator/engine.py` | Multi-strategy ranking with confidence scoring |
| `StepGraph models` | `stepgraph/models.py` | Clean data model for steps |
| `force_fix` | `healing/force_fix.py` | 4-stage repair cascade — exactly what we designed |
| `llm_assist` | `healing/llm_assist.py` | Multi-attempt LLM repair with history |
| `LLMOrchestrator` | `llm/orchestrator.py` | The tool-calling loop — wire it to the panel |
| LLM providers | `llm/openai.py`, `llm/anthropic.py`, `llm/openai_compatible.py` | Provider abstraction is correct |
| `LLMContext` tiered builder | `llm/context.py` | Tiered DOM/context escalation — refine and use |
| Storage repos | `storage/repos/*.py` | SQLite persistence is solid |
| DB migrations | `storage/migrations/*.sql` | Keep schema, run migrations cleanly |

---

These components have fundamental problems and must be rebuilt:

| Component | Problem | Rebuild as |
|---|---|---|
| Panel protocol | No typed schema, frontend/backend drift, `openUploadFix` not defined | Typed message contract (Section 14), strict schema validation |
| Validation pipeline | Panel validate and runner validate have different behavior | One unified validation path: all validation goes through ToolRuntime |
| LLM mode architecture | 3 separate disconnected paths (`force_fix`, `llm_assist`, `llm_build_step`) | One `LLMAgentLoop` class connected to `LLMOrchestrator` |
| Execution path | Panel replay, runner replay, dashboard replay, orchestrator — all doing different things | One canonical path: Panel → PanelBridge → single execution handler |
| `agent ui` dashboard | Duplicates panel functionality, adds complexity | Remove or fold into panel |
| Panel frontend (panel.html) | Prototype quality, no state management, missing handlers | Clean rebuild with typed state, typed WebSocket contract |
| Config/security | API keys in plaintext `~/.agent/llm_config.json` | Env vars only, never persist keys to disk |
| Platform coupling | macOS-only file picker (AppleScript) | Cross-platform solution |

---

```
.hermes/
  ├── auth/
  │   ├── storageState.json          ← default user auth
  │   ├── admin-storageState.json
  │   └── user-storageState.json
  │
  ├── uploads/                       ← user drops files here
  │
  ├── output/                        ← generated test files
  │   ├── 2026-04-30-login-flow.spec.ts
  │   └── 2026-04-30-login-flow.session.json
  │
  ├── traces/                        ← auto-deleted on pass
  │   └── session-id.zip
  │
  ├── test-data/
  │   └── data.json
  │
  ├── locators/
  │   └── app-example-com.json       ← persistent locator library
  │
  ├── page-maps/
  │   └── app-example-com/
  │       └── login-page.json        ← explored page structures
  │
  ├── reports/
  │   └── index.html
  │
  ├── skills/
  │   └── playwright-automation/
  │       ├── core/SKILL.md          ← human editable only
  │       └── [24 skill files]
  │
  ├── memories/
  │   ├── MEMORY.md                  ← persistent facts
  │   ├── USER.md                    ← user preferences
  │   └── error-patterns.json        ← known fixes
  │
  ├── .env                           ← secrets (gitignored)
  │   BASE_URL=https://staging.example.com
  │   TEST_EMAIL=user@company.com
  │   LLM_API_KEY=sk-...
  │   LLM_BASE_URL=https://api.openai.com/v1
  │   LLM_MODEL=gpt-4o
  │
  ├── .hermesignore                  ← files agent never touches
  │   node_modules/
  │   .git/
  │   *.secret
  │   *.pem
  │   *.key
  │
  └── config.yaml                    ← co-pilot configuration
```

---

Build in this order. Each phase is independently testable.

### Phase 1 — Core execution (Week 1-2)

Goal: Browser opens, overlay appears, element picker works, manual mode validates a click.

1. Port/clean `BrowserSession` + `ToolRuntime` from existing codebase
2. Rebuild `PanelBridge` with typed WebSocket schema
3. Rebuild `panel.html` with clean state management
4. Wire: pick_start → element descriptor → locator candidates → panel display
5. Wire: validate_step → ToolRuntime → validate_result
6. Wire: append_step → step list → code view updates

**Acceptance test:** User opens browser, picks a button, system finds locator, validates it, records step, code view shows TypeScript.

### Phase 2 — Manual mode complete (Week 3)

Goal: All Playwright actions work in manual mode.

1. Full action dropdown (all actions from Section 8)
2. Special case auto-detection (popup, new tab, iframe, upload, dropdown)
3. Recovery loop for manual mode failures
4. Replay with pause/stop/continue/skip
5. Save/load sessions

**Acceptance test:** User records a complete login flow manually. Replays it. One step fails. System auto-fixes. All steps pass.

### Phase 3 — LLM mode (Week 4-5)

Goal: User describes steps in plain English. The LLM plans and reasons, while the runtime controls state, execution, recovery, recording, and code output.

1. Wire `LLMOrchestrator` to `PanelBridge` as the LLM agent loop
2. Build Step Runner lifecycle: pending → planning → confirmed → executing → recovery_pending → recorded/skipped
3. Build Context Manager: managed history, token telemetry, DOM modes, locator/page-map injection
4. Build progressive skills system: skill index → compact summary → full skill only when needed
5. Build DOM strategy: adaptive snapshot, page maps, debug mode, full-DOM fallback rules
6. Build tool registry with lifecycle guards and tool preconditions
7. Wire `plan_ready`, `correction`, `step_recorded`, and `code_update` typed events
8. Build live code preview for every recorded step
9. LLM persona + compact system prompt

**Acceptance test:** User says "go to login page, fill email with test@test.com, click login, assert dashboard is visible." The system plans, asks for confirmation, validates locators, executes safely, recovers if needed, records steps, and shows clean Playwright TypeScript.

### Phase 4 — Memory & persistence (Week 6)

Goal: System gets smarter every session.

1. Locator library — save and inject on session start
2. Page maps — explore once, store, reuse
3. MEMORY.md — update after every session
4. Error patterns — build and use fix history
5. Version snapshots — save/load named versions

**Acceptance test:** Session 1 finds locators from scratch. Session 2 for the same app reuses all known locators. Zero re-discovery.

### Phase 5 — Polish & remaining features (Week 7-8)

1. Self-healing tests during replay
2. Assertion builder in panel
3. Network capture panel
4. Locator inspector tool
5. Smart suggestions
6. Cross-platform file picker (replace AppleScript)
7. Security hardening (remove plaintext key storage)

---

*End of PRD v2*

---