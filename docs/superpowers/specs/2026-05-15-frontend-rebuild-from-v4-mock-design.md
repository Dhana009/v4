# Frontend rebuild from v4 mock — design spec

Date: 2026-05-15
Branch: `s7/clusters-6-11-complete-llm-mode`
Safe-point commit: `3eaae8c` (pre-rebuild snapshot pushed to origin)

## Problem

The previous `frontend/` directory had grown into an entangled mix of `panel-v2`,
`host`, `layout`, `v4`, and legacy folders. Tests reported green while the UI
was visibly broken. Every fix to the panel/live-theme integration revealed a
new breakage somewhere else — classic architectural rot (Phase-4.5 indicator
from systematic-debugging).

A clean reference exists in two places, both approved:

* `source_mock_fonrtend/v4/` — latest hand-built React mock (CDN React 18 +
  Babel-standalone runtime, no bundler), with a `Tweaks` panel that drives a
  17-state lifecycle deterministically.
* `AutoWorkbench.html` (191 lines) — a smaller HTML shell that pins layout /
  styles to the same visual target.

The decision is to delete the broken frontend and rebuild from the v4 mock,
preserving the **shadow-DOM mount** concept that the previous frontend used to
isolate panel styles from the host page.

## Goals

1. Pixel-parity with `source_mock_fonrtend/v4/` for all 17 lifecycle states.
2. Backend integration through `/ws` with the existing typed-envelope protocol
   in `server.py` (no protocol changes this pass).
3. Style isolation via Shadow DOM so the panel can later be injected into an
   arbitrary host page without leaking or absorbing styles.
4. Single-origin static serving from FastAPI — no separate `:8000` dev server,
   no CORS in production.
5. No build step. Babel-standalone transpiles JSX in the browser; we trade
   first-paint cost for zero tooling and zero drift from the mock.

## Non-goals (this pass)

* Refactoring `server.py` / `agent.py` / `executor.py`.
* Resurrecting the deleted `tests-dom/`, `test_full_audit.py`, or
  `test_live_theme.py`. They lied green and are kept only in git history.
* Wiring every typed command (`stop_run`, `permission_decision`, etc.) into
  buttons. Phase 1 ships the read path (server→UI) and `window.AW.send` for
  Phase 2 buttons.

## Architecture

```
┌──────────── browser tab ────────────┐
│ document                            │
│   <head> Geist fonts                │
│   <body>                            │
│     <div id="aw-host">              │
│       └─ shadowRoot (open)          │
│           ├─ <style>styles.css</style>
│           └─ <div id="root">        │
│                 React tree from     │
│                 v4 jsx files        │
│                 (chrome, llm-tab,   │
│                  secondary-tabs,    │
│                  website, tweaks)   │
│  <script> Babel-standalone          │
│  <script type="text/babel">         │
│     tweaks → icons → website →      │
│     chrome → llm-tab → secondary →  │
│     transport → app                 │
└─────────────────────────────────────┘
            │  ws://host/ws
            ▼
┌──────── FastAPI (server.py) ────────┐
│ /ws       typed envelope protocol   │
│ /api/log  frontend log ingest       │
│ /         StaticFiles(frontend/)    │
└─────────────────────────────────────┘
```

### File inventory (new `frontend/`)

| File                  | Origin                          | Modification                       |
|-----------------------|---------------------------------|------------------------------------|
| `index.html`          | rewritten                       | shadow-DOM bootstrap, script order |
| `styles.css`          | `source_mock_fonrtend/v4/`      | verbatim copy                       |
| `app.jsx`             | `source_mock_fonrtend/v4/`      | render target → `window.AW_ROOT`   |
| `chrome.jsx`          | `source_mock_fonrtend/v4/`      | verbatim                            |
| `icons.jsx`           | `source_mock_fonrtend/v4/`      | verbatim                            |
| `llm-tab.jsx`         | `source_mock_fonrtend/v4/`      | verbatim                            |
| `secondary-tabs.jsx`  | `source_mock_fonrtend/v4/`      | verbatim                            |
| `website.jsx`         | `source_mock_fonrtend/v4/`      | verbatim                            |
| `tweaks-panel.jsx`    | `source_mock_fonrtend/v4/`      | `useTweaks` listens to `aw:set` event so transport can drive state |
| `transport.jsx`       | new                             | WS bridge: typed event → state, `window.AW.send` |

### Shadow DOM mount

`index.html` runs a small plain-JS bootstrap **before** Babel scripts execute:

```js
const host = document.getElementById('aw-host');
const shadow = host.attachShadow({ mode: 'open' });
const root = document.createElement('div');
root.id = 'root';
shadow.appendChild(root);
window.AW_SHADOW = shadow;
window.AW_ROOT = root;
fetch('styles.css').then(r => r.text()).then(css => {
  const s = document.createElement('style');
  s.textContent = css;
  shadow.insertBefore(s, root);
});
```

`app.jsx`'s final line was:

```js
ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
```

…now:

```js
(function () {
  var target = window.AW_ROOT || document.getElementById("root");
  ReactDOM.createRoot(target).render(<App/>);
})();
```

The light-DOM fallback keeps the file usable inside the standalone mock harness
(`source_mock_fonrtend/v4/index.html`).

### Transport bridge

`transport.jsx` opens `/ws`, normalises typed envelopes from the backend into
state updates on the v4 tweak bag. Mapping (extend as features land):

| Backend event              | Drives `state` →   |
|----------------------------|--------------------|
| `ready` (both ready)       | `idle`             |
| `api_key_required`         | `apikey`           |
| `no_browser`               | `nobrowser`        |
| `page_analysis_started`    | `planning`         |
| `page_summary_ready` / `recommendation_ready` | `recommend` |
| `plan_ready`               | `plan`             |
| `plan_diff`                | `diff`             |
| `permission_required`      | `permit`           |
| `human_input_required`     | `otp`              |
| `run_started` / `step_executing` | `exec`       |
| `step_failed` / `precondition_failed` / `recovery_needed` | `recover` |
| `locator_update_request`   | `locator`          |
| `run_completed`            | `done`             |
| `e2e_pending`              | `e2e`              |
| `schema_error` / `provider_error` / `malformed_output_error` | `schema` |
| WS close                   | `offline`          |

`useTweaks` was extended with a `window.addEventListener('aw:set', …)` shim so
transport can fold `{ state: 'plan' }` into the same value bag the
`TweaksPanel` already mutates — no app-level prop drilling required.

`window.AW.send(msg)` is exposed for Phase-2 button handlers.
`window.AW.on(type, fn)` lets feature code subscribe without ripping open the
mapping table.

### Backend static mount

`server.py` mounts `frontend/` last so `/ws` and `/api/log` retain priority:

```py
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
```

## Phasing

| Phase | Scope                                                                 | Done? |
|-------|-----------------------------------------------------------------------|-------|
| 0     | Push safe-point snapshot to origin                                    | ✅    |
| 1     | Nuke `frontend/`, paste v4 mock, shadow-DOM mount, static serve, transport read path | ✅    |
| 2     | Wire Composer + decision-card buttons to `window.AW.send(...)` commands | TBD |
| 3     | Reintroduce browser-driven tests (Playwright) against real selectors  | TBD   |
| 4     | Backend / agent code cleanup (separate pass — out of scope here)      | TBD   |

## Risks & mitigations

* **Babel-standalone first-paint slowness.** Acceptable trade for now; if it
  hurts later, swap to a Vite build that emits the same script tags.
* **Shadow DOM + fonts.** Font `@font-face` is loaded in the document head and
  inherits into the shadow root via the default font-family declaration on
  `body` — verified by the v4 mock running in this mode.
* **`useTweaks` posts to `window.parent`** for the legacy edit-mode bridge.
  When mounted standalone (no parent frame) `window.parent === window`, the
  message is harmless. Kept verbatim to preserve mock behaviour.

## Verification (Phase 1)

Static checks (passed):
* `GET /` returns 200, contains `#aw-host` + `attachShadow`.
* `GET /transport.jsx`, `/app.jsx`, `/styles.css` all return 200 with expected
  markers (`AW_ROOT`, large CSS).
* Server boots in `AUTOWORKBENCH_STUB_MODE=1` without errors.

Manual smoke (deferred to user):
* Open `http://127.0.0.1:8765/` in a browser, confirm panel renders inside the
  shadow root, cycle the 17 states using the Tweaks panel.

Out-of-band:
* Old `tests-dom/` and root `test_*.py` probes were deleted in safe-point
  commit `3eaae8c` and are not part of this verification.
