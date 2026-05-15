# AutoWorkbench v4

Docked Shadow-DOM panel that plans, runs, records, and repairs Playwright
flows. Backend events drive lifecycle truth; the frontend renders typed
cards and routes typed commands.

## Run modes

The backend boots in two supported modes. **Lifespan never crashes on
missing config**; if a prerequisite is absent the frontend renders the
matching state card instead.

### 1. Real mode — full LLM + Playwright

```bash
# 1. Env
export OPENAI_API_KEY="sk-…"      # required for LLM mode

# 2. Backend (one-time setup)
python -m pip install -r requirements.txt
python -m playwright install chromium

# 3. Frontend (one-time build)
cd frontend
npm install
npm run build
cd ..

# 4. Boot
python -m uvicorn server:app --reload --port 8765
```

Open `http://127.0.0.1:8765/` (or attach the bookmarklet to any page).
You should see:

- `Connected` status pill in the header
- Honest-empty LLM tab welcome with 4 suggestion chips
- Agents popover with `Main Orchestrator` + `Page Intelligence` rows
- Token pill and provider badge

### 2. Stub mode — panel + UI without LLM / browser

Use this when you want to exercise layout, state cards, dock modes,
recording UI, etc. without an OpenAI key or a Playwright browser.

```bash
export AUTOWORKBENCH_STUB_MODE=1
python -m uvicorn server:app --reload --port 8765
```

What happens:

- Lifespan skips the OPENAI_API_KEY check.
- Lifespan skips `launch_browser()`.
- On every WS connect the server emits:
  - `api_key_required` event → `CardApiKey` renders with provider name,
    missing env-var name, and a setup-hint link. Inputs are NOT
    collected (no secure store in S7).
  - `no_browser` event → `CardNoBrowser` renders with a recoverable
    advisory. The relaunch button stays disabled-with-reason until a
    real launch path lands.

State cards live in the LLM tab; the rest of the panel (Steps, Recorded,
Code, Trace) still works against the typed event stream.

### 3. Partial degradation — both modes mid-session

The boot helper records the cause of each missing prerequisite (key /
browser) and emits the matching event on every WS connect. Reconnecting
after fixing the env clears the card automatically — there is no
frontend cache that can lie about the backend state.

## Smoke check

```bash
scripts/aw_smoke.sh
```

Runs:

1. `cd frontend && npm test -- --run` (jsdom)
2. `cd frontend && npm run build`
3. `python -m pytest --tb=short -q --ignore=tests/e2e` (backend contract)
4. `AUTOWORKBENCH_E2E_MODE=fake_llm AUTOWORKBENCH_LLM_MODE=complete_llm`
   pytest `tests/e2e/test_v4_panel_smoke.py` +
   `tests/e2e/test_mvp_001_lifecycle_smoke.py` (fake-stream E2E)

All four must exit 0 before a sprint is considered ship-ready.

## Architecture

| Layer | File |
|---|---|
| Backend HTTP / WS | `server.py` |
| Agent loop | `agent.py` |
| Browser surface | `browser.py` |
| Event / command contracts | `runtime/event_contracts.py` |
| Frontend mount + transport | `frontend/src/main.jsx` |
| Shadow DOM host | `frontend/src/host/host.jsx` |
| Panel chrome | `frontend/src/v4/chrome.jsx` |
| LLM-tab cards | `frontend/src/v4/llm-cards.jsx` |
| Steps / Recorded / Code / Trace | `frontend/src/v4/secondary-tabs.jsx` |
| Store / reducer | `frontend/src/store/` |
| v4 stylesheet (Shadow-aware) | `frontend/v4.css` |

## Design reference

- `yui (1)/v4/` — the canonical jsx + css design source the production
  panel is replicated from.
- `1AutoWorkbench — print.pdf` — printable 16-frame walkthrough of every
  v4 state.
- `.tasks-md/Audit/FRONTEND_ACTIONS_AUDIT.md` — control-by-control audit
  of every clickable surface in production.
- `.tasks-md/Audit/V4_TESTID_CONTRACT.md` — the data-testid contract
  every jsdom + Playwright test targets.

## What does NOT exist (yet) in production

See `.tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md` for the
batch-by-batch completion plan.

Cleared in Sprint 7:
- E0 plan doc, E1 agent settings, E2 state cards, E3 stub-action wires,
  E4 execution lifecycle contracts, F1 graceful boot, F2 shadow font.

Outstanding (S8 / post-sprint):
- E5 composer paperclip / camera / provider badge / file-upload endpoint
- E6 recorded repair-diff widget, code syntax highlight, trace download
- E7 prompt-side redaction sweep, dock/resize localStorage, agent
  toggle semantics
- E8 final acceptance + handoff
