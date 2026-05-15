from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from dotenv import load_dotenv
from playwright.async_api import BrowserContext, Page, async_playwright


USE_AUTOWORKBENCH_UI = True
AUTOWORKBENCH_ROOT_ID = "autoworkbench-root"
AUTOWORKBENCH_STYLE_ID = "autoworkbench-style"
AUTOWORKBENCH_DEFAULT_CONFIG: dict[str, Any] = {
    "state": "idle",
    "tab": "workbench",
    "panelWidth": 420,
    "density": "compact",
}
AUTOWORKBENCH_ASSETS_MISSING_MESSAGE = (
    "AutoWorkbench assets not found. Run npm run build in frontend/."
)

_lock = asyncio.Lock()
_pw: Any | None = None
_context: BrowserContext | None = None
_active_page: Page | None = None
_port: int | None = None
_start_url: str | None = None

# Picker state: armed for exactly one click, then disarmed.
_picker_step_id: str | None = None
_picker_send: Optional[Callable[[dict], Awaitable[None]]] = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _read_frontend_asset(relative_path: str) -> str | None:
    asset_path = _repo_root() / relative_path
    try:
        return asset_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _read_remote_debugging_port() -> int | None:
    raw_port = os.getenv("AUTOWORKBENCH_REMOTE_DEBUGGING_PORT", "").strip()
    if not raw_port:
        return None
    try:
        return int(raw_port)
    except ValueError as exc:
        raise ValueError("AUTOWORKBENCH_REMOTE_DEBUGGING_PORT must be an integer") from exc


def _build_missing_assets_injection_script(message: str) -> str:
    return f"""
(() => {{
  if (window.top !== window) return;
  const ROOT_ID = {json.dumps(AUTOWORKBENCH_ROOT_ID)};
  const MESSAGE = {json.dumps(message)};

  function ensure() {{
    let root = document.getElementById(ROOT_ID);
    if (!root) {{
      root = document.createElement("div");
      root.id = ROOT_ID;
      (document.body || document.documentElement).appendChild(root);
    }}
    root.style.cssText = [
      "position:fixed",
      "top:16px",
      "right:16px",
      "z-index:2147483647",
      "width:320px",
      "padding:14px 16px",
      "border-radius:12px",
      "border:1px solid rgba(148,163,184,.28)",
      "background:rgba(15,23,42,.96)",
      "color:#e5eef9",
      "box-shadow:0 20px 60px rgba(0,0,0,.4)",
      "font:12px/1.5 ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
    ].join(";");
    root.innerHTML = `
      <div style="font-weight:700;margin-bottom:6px;">AutoWorkbench</div>
      <div>${{MESSAGE}}</div>
    `;
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", ensure, {{ once: true }});
  }} else {{
    ensure();
  }}
}})();
"""


def _build_autoworkbench_injection_script() -> str:
    css_text = _read_frontend_asset("frontend/dist/autoworkbench.css")
    if css_text is None:
        return _build_missing_assets_injection_script(AUTOWORKBENCH_ASSETS_MISSING_MESSAGE)

    port = _read_port()
    config = dict(AUTOWORKBENCH_DEFAULT_CONFIG)
    config.update(
        {
            "wsUrl": f"ws://127.0.0.1:{port}/ws",
            "wsPort": port,
        }
    )

    return f"""
(() => {{
  if (window.top !== window) return;
  const ROOT_ID = {json.dumps(AUTOWORKBENCH_ROOT_ID)};
  const STYLE_ID = {json.dumps(AUTOWORKBENCH_STYLE_ID)};
  const CSS_TEXT = {json.dumps(css_text)};
  const CONFIG = {json.dumps(config)};

  function ensureRoot() {{
    let root = document.getElementById(ROOT_ID);
    if (!root) {{
      root = document.createElement("div");
      root.id = ROOT_ID;
      (document.body || document.documentElement).appendChild(root);
    }}
    return root;
  }}

  function ensureStyles() {{
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = CSS_TEXT;
    (document.head || document.documentElement).appendChild(style);
  }}

  function mountIfReady() {{
    if (!window.AutoWorkbench || typeof window.AutoWorkbench.mount !== "function") {{
      return false;
    }}
    window.AutoWorkbench.mount(ensureRoot(), CONFIG);
    return true;
  }}

  function boot(retries = 40) {{
    ensureStyles();
    if (mountIfReady()) return;
    if (retries > 0) {{
      window.setTimeout(() => boot(retries - 1), 25);
    }}
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", () => boot(), {{ once: true }});
  }} else {{
    boot();
  }}
}})();
"""


def _read_port() -> int:
    global _port
    if _port is not None:
        return _port
    load_dotenv(override=False)
    _port = int(os.getenv("PORT", "8765"))
    return _port


def _read_start_url() -> str:
    global _start_url
    if _start_url is not None:
        return _start_url
    # override=False so explicit shell exports (scripts/launch.sh) win over .env.
    load_dotenv(override=False)
    _start_url = os.getenv("START_URL", "https://example.com").strip() or "https://example.com"
    return _start_url


def get_page() -> Page:
    if _active_page is None:
        raise RuntimeError("browser not launched yet; call launch_browser() first")
    return _active_page


async def launch_browser() -> Page:
    """
    Launch headed Chromium with persistent context and keep it alive forever.
    Opens START_URL from env.
    """
    global _pw, _context, _active_page
    async with _lock:
        if _active_page is not None:
            return _active_page

        _pw = await async_playwright().start()
        chromium = _pw.chromium

        user_data_dir = os.path.abspath("./.pw-user-data")
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": user_data_dir,
            "headless": False,
        }
        remote_debugging_port = _read_remote_debugging_port()
        if remote_debugging_port is not None:
            launch_kwargs["args"] = [
                f"--remote-debugging-port={remote_debugging_port}",
                "--remote-debugging-address=127.0.0.1",
            ]
        _context = await chromium.launch_persistent_context(**launch_kwargs)

        async def on_page(page: Page) -> None:
            global _active_page
            _active_page = page
            await inject_panel(page)
            await _ensure_picker_binding(page)

        _context.on("page", lambda p: asyncio.create_task(on_page(p)))

        if _context.pages:
            _active_page = _context.pages[-1]
        else:
            _active_page = await _context.new_page()

        await inject_panel(_active_page)
        await _ensure_picker_binding(_active_page)
        await _active_page.goto(_read_start_url())

        return _active_page


async def inject_panel(page: Page) -> None:
    """
    Injects the built AutoWorkbench bundle into the page and keeps it alive across navigations.
    The legacy raw overlay remains available behind USE_AUTOWORKBENCH_UI = False.
    """
    if USE_AUTOWORKBENCH_UI:
        js_bundle = _read_frontend_asset("frontend/dist/autoworkbench.js")
        if js_bundle is None:
            script = _build_missing_assets_injection_script(AUTOWORKBENCH_ASSETS_MISSING_MESSAGE)
            await page.add_init_script(script)
            try:
                await page.evaluate(script)
            except Exception:
                pass
            return

        bootstrap_script = _build_autoworkbench_injection_script()
        await page.add_init_script(js_bundle)
        await page.add_init_script(bootstrap_script)
        try:
            await page.evaluate(js_bundle)
        except Exception:
            pass
        try:
            await page.evaluate(bootstrap_script)
        except Exception:
            pass
        return

    port = _read_port()
    ws_url = f"ws://localhost:{port}/ws"

    script = f"""
(() => {{
  const WS_URL = {ws_url!r};
  const ROOT_ID = "__automation_copilot_root__";

  function ensure() {{
    if (document.getElementById(ROOT_ID)) return;

    const root = document.createElement("div");
    root.id = ROOT_ID;
    root.innerHTML = `
      <style>
        #${{ROOT_ID}} {{
          position: fixed;
          top: 16px;
          right: 16px;
          width: 350px;
          max-height: calc(100vh - 32px);
          z-index: 2147483647;
          background: linear-gradient(180deg, rgba(9,15,27,.98), rgba(15,24,42,.96));
          color: #e5eef9;
          border: 1px solid rgba(148, 163, 184, 0.24);
          border-radius: 14px;
          box-shadow: 0 20px 60px rgba(0,0,0,.45);
          font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          overflow: hidden;
          backdrop-filter: blur(8px);
        }}
        #${{ROOT_ID}} * {{ box-sizing: border-box; }}
        #${{ROOT_ID}} .ac-head {{
          padding: 12px 14px;
          font-size: 13px;
          font-weight: 700;
          letter-spacing: .2px;
          border-bottom: 1px solid rgba(148,163,184,.18);
        }}
        #${{ROOT_ID}} .ac-body {{ padding: 10px; }}
        #${{ROOT_ID}} .ac-section-title {{
          margin: 0 0 8px 0;
          font-size: 11px;
          text-transform: uppercase;
          color: #9fb0c7;
          letter-spacing: .6px;
        }}
        #${{ROOT_ID}} .ac-steps {{
          max-height: 190px;
          overflow: auto;
          margin-bottom: 10px;
        }}
        #${{ROOT_ID}} .ac-recorded-steps {{
          max-height: 180px;
          overflow-y: auto;
          margin-bottom: 10px;
          padding-right: 2px;
        }}
        #${{ROOT_ID}} .ac-step {{
          border: 1px solid rgba(148,163,184,.16);
          border-radius: 10px;
          padding: 8px;
          margin-bottom: 8px;
          background: rgba(15, 23, 42, .72);
        }}
        #${{ROOT_ID}} .ac-step-head {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
          font-size: 11px;
          color: #9fb0c7;
        }}
        #${{ROOT_ID}} textarea {{
          width: 100%;
          border: 1px solid rgba(148,163,184,.16);
          border-radius: 8px;
          background: rgba(2,6,23,.72);
          color: #e5eef9;
          padding: 8px;
          resize: vertical;
          min-height: 56px;
        }}
        #${{ROOT_ID}} .ac-row {{
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-top: 8px;
        }}
        #${{ROOT_ID}} button {{
          border: 1px solid rgba(148,163,184,.18);
          border-radius: 8px;
          background: rgba(15, 23, 42, .85);
          color: #e5eef9;
          padding: 7px 9px;
          cursor: pointer;
          font-size: 11px;
        }}
        #${{ROOT_ID}} button:hover {{
          border-color: rgba(125, 211, 252, .7);
        }}
        #${{ROOT_ID}} .ac-run {{
          width: 100%;
          margin-top: 6px;
          color: #9ae6b4;
        }}
        #${{ROOT_ID}} .ac-pill {{
          display: inline-block;
          max-width: 100%;
          padding: 5px 7px;
          border-radius: 999px;
          border: 1px solid rgba(148,163,184,.16);
          font-size: 10px;
          color: #a8bad0;
          background: rgba(2,6,23,.6);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }}
        #${{ROOT_ID}} .ac-code {{
          margin-top: 6px;
          padding: 7px 8px;
          border-radius: 8px;
          border: 1px solid rgba(148,163,184,.12);
          background: rgba(2,6,23,.55);
          color: #d7e3f2;
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: 10px;
          line-height: 1.4;
          white-space: pre-wrap;
          word-break: break-word;
        }}
        #${{ROOT_ID}} .ac-understanding,
        #${{ROOT_ID}} .ac-correction {{
          min-height: 88px;
        }}
        #${{ROOT_ID}} .ac-options {{
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 8px;
        }}
        #${{ROOT_ID}} .ac-log {{
          margin-top: 10px;
          border-top: 1px solid rgba(148,163,184,.16);
          padding-top: 8px;
          max-height: 90px;
          overflow: auto;
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: 11px;
          line-height: 1.45;
        }}
        #${{ROOT_ID}} .ac-log-line {{
          color: #c8d6e7;
          margin-bottom: 4px;
        }}
        #${{ROOT_ID}} .ac-log-line.err {{
          color: #fca5a5;
        }}
      </style>
      <div class="ac-head">Automation Co-pilot</div>
      <div class="ac-body">
        <div class="ac-section-title">Step Queue</div>
        <div class="ac-steps"></div>
        <div class="ac-section-title" style="margin-top:10px;">Recorded Steps</div>
        <div class="ac-recorded-steps"></div>
        <div class="ac-row">
          <button type="button" class="ac-add">Add Step</button>
        </div>
        <button type="button" class="ac-run">Run</button>
        <div class="ac-section-title" style="margin-top:10px;">LLM Understanding</div>
        <textarea class="ac-understanding" readonly></textarea>
        <textarea class="ac-correction" placeholder="Type correction if needed..."></textarea>
        <div class="ac-options"></div>
        <div class="ac-row">
          <button type="button" class="ac-confirm">Confirm</button>
          <button type="button" class="ac-correct">Send Correction</button>
        </div>
        <div class="ac-log"></div>
      </div>
    `;
    document.documentElement.appendChild(root);

    const stepsEl = root.querySelector(".ac-steps");
    const recordedStepsEl = root.querySelector(".ac-recorded-steps");
    const addBtn = root.querySelector(".ac-add");
    const runBtn = root.querySelector(".ac-run");
    const confirmBtn = root.querySelector(".ac-confirm");
    const correctBtn = root.querySelector(".ac-correct");
    const understandingEl = root.querySelector(".ac-understanding");
    const correctionEl = root.querySelector(".ac-correction");
    const optionsEl = root.querySelector(".ac-options");
    const logEl = root.querySelector(".ac-log");

    const state = {{
      ws: null,
      steps: [],
      pendingMode: null,
    }};

    function uid() {{
      return Math.random().toString(36).slice(2, 9);
    }}

    function appendLog(msg, isError = false) {{
      const line = document.createElement("div");
      line.className = "ac-log-line" + (isError ? " err" : "");
      line.textContent = "[" + new Date().toLocaleTimeString() + "] " + msg;
      logEl.appendChild(line);
      logEl.scrollTop = logEl.scrollHeight;
    }}

    function send(msg) {{
      if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {{
        appendLog("WebSocket not connected.", true);
        return;
      }}
      state.ws.send(JSON.stringify(msg));
    }}

    function renderOptions(options) {{
      optionsEl.innerHTML = "";
      (options || []).forEach((option) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = option;
        button.addEventListener("click", () => {{
          send({{ type: "option_selected", answer: option }});
          state.pendingMode = null;
          correctionEl.value = "";
          optionsEl.innerHTML = "";
          appendLog("Clarification answer sent: " + option);
        }});
        optionsEl.appendChild(button);
      }});
    }}

    function createStep() {{
      state.steps.push({{ id: uid(), intent: "", element_info: null, recorded: false }});
      renderSteps();
    }}

    function renderSteps() {{
      stepsEl.innerHTML = "";
      recordedStepsEl.innerHTML = "";
      const pendingSteps = state.steps.filter((step) => !step.recorded);
      const recordedSteps = state.steps.filter((step) => step.recorded);

      pendingSteps.forEach((step, idx) => {{
        const card = document.createElement("div");
        card.className = "ac-step";
        const badge = step.element_info
          ? step.element_info.tag + (step.element_info.id ? ("#" + step.element_info.id) : "")
          : "No element attached";
        card.innerHTML = `
          <div class="ac-step-head">
            <span>Step ${{idx + 1}}</span>
            <button type="button" data-del="${{step.id}}">Delete</button>
          </div>
          <textarea data-intent="${{step.id}}" placeholder="Describe intent...">${{step.intent || ""}}</textarea>
          <div class="ac-row">
            <button type="button" data-pick="${{step.id}}">Attach Element</button>
            <span class="ac-pill">${{badge}}</span>
          </div>
        `;
        stepsEl.appendChild(card);
      }});

      recordedSteps.forEach((step, idx) => {{
        const card = document.createElement("div");
        card.className = "ac-step";
        const meta = step.recordedMeta || {{}};
        const action = meta.action || step.intent || `Step ${{idx + 1}}`;
        const elementName = meta.element_name || "";
        const locator = meta.locator || "";
        const generatedLine = meta.generated_line || "";
        card.innerHTML = `
          <div class="ac-step-head">
            <span>✅ ${{action}}</span>
            <button type="button" data-del-rec="${{step.id}}">Delete</button>
          </div>
          ${{elementName ? `<div class="ac-pill">${{elementName}}</div>` : ""}}
          ${{locator ? `<div class="ac-pill">${{locator}}</div>` : ""}}
          ${{generatedLine ? `<div class="ac-code"></div>` : ""}}
          <div class="ac-row">
            <button type="button" data-replay="${{step.id}}" disabled>Replay</button>
          </div>
        `;
        if (generatedLine) {{
          const codeEl = card.querySelector(".ac-code");
          if (codeEl) codeEl.textContent = generatedLine;
        }}
        recordedStepsEl.appendChild(card);
      }});

      stepsEl.querySelectorAll("[data-del]").forEach((btn) => {{
        btn.addEventListener("click", () => {{
          const id = btn.getAttribute("data-del");
          state.steps = state.steps.filter((s) => s.id !== id);
          renderSteps();
        }});
      }});

      stepsEl.querySelectorAll("textarea[data-intent]").forEach((input) => {{
        input.addEventListener("input", () => {{
          const id = input.getAttribute("data-intent");
          const step = state.steps.find((s) => s.id === id);
          if (step) step.intent = input.value;
        }});
      }});

      stepsEl.querySelectorAll("[data-pick]").forEach((btn) => {{
        btn.addEventListener("click", () => {{
          const id = btn.getAttribute("data-pick");
          appendLog("Picker armed for step " + id + ". Click target element.");
          send({{ type: "arm_picker", step_id: id }});
        }});
      }});

      recordedStepsEl.querySelectorAll("[data-del-rec]").forEach((btn) => {{
        btn.addEventListener("click", () => {{
          const id = btn.getAttribute("data-del-rec");
          state.steps = state.steps.filter((s) => s.id !== id);
          renderSteps();
        }});
      }});

      recordedStepsEl.querySelectorAll("[data-replay]").forEach((btn) => {{
        btn.addEventListener("click", () => {{
          appendLog("Replay not implemented yet.");
        }});
      }});
    }}

    function connectWs() {{
      try {{
        state.ws = new WebSocket(WS_URL);
      }} catch (err) {{
        appendLog("WebSocket open failed. Retrying...", true);
        window.setTimeout(connectWs, 1000);
        return;
      }}

      state.ws.addEventListener("open", () => appendLog("Connected."));
      state.ws.addEventListener("close", () => {{
        appendLog("Disconnected. Reconnecting...", true);
        window.setTimeout(connectWs, 1000);
      }});
      state.ws.addEventListener("message", (evt) => {{
        let msg;
        try {{
          msg = JSON.parse(evt.data);
        }} catch (_) {{
          appendLog("Invalid server message", true);
          return;
        }}
        if (msg.type === "confirm") {{
          understandingEl.value = msg.message || "";
          state.pendingMode = "confirm";
          optionsEl.innerHTML = "";
          appendLog("LLM understanding received.");
          return;
        }}
        if (msg.type === "llm_thinking") {{
          appendLog("⏳ " + (msg.message || msg.summary || "LLM is thinking..."));
          return;
        }}
        if (msg.type === "plan_ready") {{
          const parts = [];
          if (msg.summary) parts.push(msg.summary);
          if (Array.isArray(msg.steps) && msg.steps.length) {{
            parts.push("");
            parts.push(msg.steps.map((step) => {{
              const number = step.number ?? "?";
              const action = step.action ?? "step";
              const name = step.element_name ?? "";
              return number + ". " + action + (name ? " — " + name : "");
            }}).join("\\n"));
          }}
          if (msg.instruction) parts.push("\\n" + msg.instruction);
          understandingEl.value = [
            "Here is what I understood. Confirm if correct. If not, type correction and click Send Correction.",
            "",
            ...parts,
          ].join("\\n").trim();
          correctionEl.value = "";
          state.pendingMode = "confirm";
          optionsEl.innerHTML = "";
          appendLog("Plan ready. Awaiting confirmation.");
          return;
        }}
        if (msg.type === "clarification_needed") {{
          const question = msg.question || "Clarification needed.";
          const options = Array.isArray(msg.options) ? msg.options : [];
          understandingEl.value = question + (options.length ? "\\n\\nOptions:\\n- " + options.join("\\n- ") : "");
          state.pendingMode = "clarification";
          renderOptions(options);
          appendLog("⏳ Clarification requested.");
          return;
        }}
        if (msg.type === "step_recorded") {{
          const payload = msg.payload && typeof msg.payload === "object" && Object.keys(msg.payload).length ? msg.payload : msg;
          let step = null;
          if (payload.step_id) {{
            step = state.steps.find((s) => s.id === payload.step_id && s.recorded !== true) || null;
          }}
          const stepNumber = Number(payload.step_number || 0);
          if (!step && stepNumber > 0) {{
            step = state.steps.find((s, index) => index === stepNumber - 1 && s.recorded !== true) || null;
          }}
          if (step) {{
            step.recorded = true;
            step.recordedMeta = {{
              action: payload.action || "step",
              element_name: payload.element_name || "",
              locator: payload.locator || "",
              generated_line: payload.generated_line || "",
              status: payload.status || "recorded",
            }};
            if (!state.steps.some((s) => !s.recorded)) {{
              createStep();
            }} else {{
              renderSteps();
            }}
          }} else {{
            appendLog("step_recorded received but no matching pending step was found.", true);
            return;
          }}
          const action = payload.action || "step";
          const elementName = payload.element_name || "";
          appendLog("✅ Recorded: " + action + (elementName ? " — " + elementName : ""));
          return;
        }}
        if (msg.type === "code_update") {{
          return;
        }}
        if (msg.type === "llm_result") {{
          if (msg.message) understandingEl.value = msg.message;
          appendLog((msg.success === false ? "❌ " : "✅ ") + (msg.message || "Run finished."), msg.success === false);
          return;
        }}
        if (msg.type === "status") {{
          appendLog(msg.message || "");
          return;
        }}
        if (msg.type === "error") {{
          appendLog("❌ " + (msg.message || "Unknown error"), true);
          return;
        }}
        if (msg.type === "element_picked") {{
          const step = state.steps.find((s) => s.id === msg.step_id);
          if (step) {{
            step.element_info = msg.element_info || null;
            renderSteps();
          }}
          appendLog("Element captured for step " + msg.step_id);
        }}
      }});
    }}

    addBtn.addEventListener("click", createStep);
    runBtn.addEventListener("click", () => {{
      const readySteps = state.steps
        .filter((s) => (s.intent || "").trim() && s.recorded !== true)
        .map((s) => ({{
          id: s.id,
          intent: (s.intent || "").trim(),
          element_info: s.element_info || null,
        }}));
      if (!readySteps.length) {{
        appendLog("Add at least one step intent before running.", true);
        return;
      }}
      send({{ type: "run_steps", steps: readySteps }});
      appendLog("Run requested with " + readySteps.length + " step(s).");
    }});

    confirmBtn.addEventListener("click", () => {{
      if (state.pendingMode === "confirm") {{
        send({{ type: "confirmed" }});
        state.pendingMode = null;
        appendLog("Confirmation sent.");
        return;
      }}
      if (state.pendingMode === "clarification") {{
        const answer = correctionEl.value.trim();
        if (!answer) {{
          appendLog("Type an answer or click an option.", true);
          return;
        }}
        send({{ type: "option_selected", answer }});
        state.pendingMode = null;
        correctionEl.value = "";
        optionsEl.innerHTML = "";
        appendLog("Clarification answer sent.");
        return;
      }}
      appendLog("No pending confirmation.", true);
    }});

    correctBtn.addEventListener("click", () => {{
      if (state.pendingMode !== "confirm") {{
        appendLog("No pending correction.", true);
        return;
      }}
      const message = correctionEl.value.trim();
      if (!message) {{
        appendLog("Correction is empty.", true);
        return;
      }}
      send({{ type: "correction", message }});
      state.pendingMode = null;
      correctionEl.value = "";
      appendLog("Correction sent.");
    }});

    createStep();
    connectWs();
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", ensure, {{ once: true }});
  }} else {{
    ensure();
  }}
}})();
"""
    await page.add_init_script(script)
    # Try to inject immediately for the current document too.
    try:
        await page.evaluate(script)
    except Exception:
        # Don't block on injection errors for edge documents like about:blank.
        pass


async def arm_picker(step_id: str, send_to_panel: Callable[[dict], Awaitable[None]]) -> None:
    """
    Arms the picker for exactly one click on the active page, then disarms.
    send_to_panel will be called with: {type:"element_picked", step_id, element_info}
    """
    global _picker_step_id, _picker_send
    _picker_step_id = step_id
    _picker_send = send_to_panel

    page = get_page()
    await _ensure_picker_binding(page)
    await _install_picker_overlay(page)


async def _ensure_picker_binding(page: Page) -> None:
    # Expose binding once per page.
    if await page.evaluate("() => Boolean(window.__picker_binding_ready__)"):
        return

    async def on_picked(source: Any, payload: dict) -> None:  # noqa: ARG001
        global _picker_step_id, _picker_send
        if not _picker_step_id or _picker_send is None:
            return
        step_id = _picker_step_id
        _picker_step_id = None
        send = _picker_send
        _picker_send = None

        try:
            from runtime.locator_intelligence import (
                LocatorStrength,
                classify_locator_strength,
            )

            attrs = payload.get("attributes") if isinstance(payload, dict) else None
            if isinstance(attrs, dict):
                strength = classify_locator_strength(attrs)
                kind_map = {
                    LocatorStrength.STRONG: ("ok", "uses strong identifier"),
                    LocatorStrength.MEDIUM: ("med", "uses accessible label / role"),
                    LocatorStrength.WEAK: ("warn", "no strong identifier — relies on class / tag"),
                }
                kind, reason = kind_map[strength]
                payload.setdefault("locator_kind", kind)
                payload.setdefault("locator_strength", strength.value)
                payload.setdefault("locator_reason", reason)
        except Exception:
            # Classification is metadata only; never block the pick.
            pass

        await send(
            {
                "type": "element_picked",
                "step_id": step_id,
                "element_info": payload,
            }
        )

        # Best-effort cleanup: remove overlay after pick.
        try:
            await page.evaluate("() => window.__pickerCleanup__ && window.__pickerCleanup__()")
        except Exception:
            pass

    await page.expose_binding("__pickerPicked__", on_picked)
    await page.add_init_script("window.__picker_binding_ready__ = true;")
    try:
        await page.evaluate("window.__picker_binding_ready__ = true;")
    except Exception:
        pass


async def _install_picker_overlay(page: Page) -> None:
    # Installs capture listeners and hover outline. One-click pick, then calls __pickerPicked__.
    script = r"""
(() => {
  if (window.__pickerInstalled__) {
    if (window.__pickerArm__) window.__pickerArm__();
    return;
  }
  window.__pickerInstalled__ = true;

  let armed = false;
  let lastEl = null;
  let prevOutline = null;
  let prevOutlineOffset = null;
  let prevCursor = null;
  let selectedEl = null;
  let selectedOutline = null;
  let selectedOutlineOffset = null;
  let selectedBoxShadow = null;
  let selectedBadge = null;
  let selectedTimer = null;

  const MAX_ANCESTOR_DEPTH = 6;
  const MAX_CANDIDATE_TEXT_LENGTH = 500;
  const MAX_OPTION_TEXT_LENGTH = 120;
  const INTERACTIVE_TAGS = new Set(["button", "a", "input", "select", "textarea"]);
  const INTERACTIVE_ROLES = new Set([
    "button",
    "link",
    "tab",
    "checkbox",
    "radio",
    "switch",
    "menuitem",
    "option",
    "textbox",
    "combobox",
    "slider",
    "spinbutton",
  ]);

  function normalizeSpace(value, limit = MAX_CANDIDATE_TEXT_LENGTH) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!text) {
      return "";
    }
    return text.length > limit ? text.slice(0, limit) : text;
  }

  function getTag(el) {
    return normalizeSpace((el && el.tagName) || "", 48).toLowerCase();
  }

  function getClassName(el) {
    if (!el) {
      return "";
    }
    if (typeof el.className === "string") {
      return normalizeSpace(el.className, 220);
    }
    return "";
  }

  function getRole(el, tag) {
    if (!el) {
      return "";
    }
    const explicitRole = normalizeSpace(el.getAttribute && el.getAttribute("role"), 80).toLowerCase();
    if (explicitRole) {
      return explicitRole;
    }
    const inputType = normalizeSpace(el.getAttribute && el.getAttribute("type"), 40).toLowerCase();
    if (tag === "button") {
      return "button";
    }
    if (tag === "a" && el.hasAttribute && el.hasAttribute("href")) {
      return "link";
    }
    if (tag === "select") {
      return "combobox";
    }
    if (tag === "textarea") {
      return "textbox";
    }
    if (tag === "input") {
      if (["button", "submit", "reset"].includes(inputType)) return "button";
      if (inputType === "checkbox") return "checkbox";
      if (inputType === "radio") return "radio";
      return "textbox";
    }
    if (tag === "li") {
      return "listitem";
    }
    if (tag === "tr") {
      return "row";
    }
    return "";
  }

  function collectAttributes(el, tag, role, className) {
    const attrs = {};
    const allowed = new Set([
      "id",
      "class",
      "className",
      "role",
      "aria-label",
      "aria-labelledby",
      "aria-describedby",
      "aria-modal",
      "aria-selected",
      "aria-expanded",
      "aria-pressed",
      "aria-current",
      "data-testid",
      "data-test-id",
      "data-test",
      "data-qa",
      "data-cy",
      "type",
      "name",
      "placeholder",
      "value",
      "href",
      "title",
      "alt",
      "for",
      "disabled",
      "readonly",
      "checked",
      "selected",
      "contenteditable",
    ]);
    try {
      for (const attr of Array.from(el && el.attributes ? el.attributes : [])) {
        if (!attr || !attr.name || !allowed.has(attr.name)) {
          continue;
        }
        attrs[attr.name] = attr.value;
      }
    } catch (_) {}
    if (className && !attrs.class) {
      attrs.class = className;
    }
    if (className && !attrs.className) {
      attrs.className = className;
    }
    if (role && !attrs.role) {
      attrs.role = role;
    }
    return attrs;
  }

  function inferSemanticType(tag, role, category, className) {
    if (role === "button" || tag === "button") return "button";
    if (role === "link" || tag === "a") return "link";
    if (role === "checkbox") return "checkbox";
    if (role === "radio") return "radio";
    if (role === "combobox" || tag === "select") return "combobox";
    if (role === "textbox" || tag === "textarea" || tag === "input") return "textbox";
    if (category === "exact_element") {
      if (tag === "code") return "code block";
      if (tag === "pre") return "pre block";
      if (tag === "span" || tag === "p" || tag === "label" || tag === "strong" || tag === "em" || tag === "b" || tag === "i") {
        return "text node parent";
      }
      return tag || "exact element";
    }
    if (category === "code_block") return "code block";
    if (category === "pre_block") return "pre block";
    if (category === "tab_panel") return "tab panel";
    if (category === "dialog") return "dialog";
    if (category === "form") return "form";
    if (category === "section") return "section";
    if (category === "card") return "card";
    if (category === "list_item") return "list item";
    if (category === "table_row") return "table row";
    if (category === "text_node_parent") return "text node parent";
    if (className && /(?:code|language|prism|token|codeblock)/i.test(className)) return "code block";
    return category || "container";
  }

  function classifyCandidate(el, level, tag, role, attrs, text, className, childCount) {
    const ariaModal = normalizeSpace(attrs["aria-modal"] || "", 32).toLowerCase() === "true";
    const codeLike = tag === "code" || tag === "pre" || /(?:code|language|prism|token|codeblock)/i.test(className);
    if (level === 0) {
      const exactSemanticType = inferSemanticType(tag, role, "exact_element", className);
      const exactReason = role || tag ? "clicked element" : "clicked element";
      return {
        category: "exact_element",
        semanticType: exactSemanticType,
        reason: exactReason,
      };
    }
    if (codeLike) {
      return {
        category: tag === "pre" ? "pre_block" : "code_block",
        semanticType: tag === "pre" ? "pre block" : "code block",
        reason: tag === "pre" ? "pre ancestor" : "code ancestor",
      };
    }
    if (role === "tabpanel") {
      return {
        category: "tab_panel",
        semanticType: "tab panel",
        reason: "role=tabpanel",
      };
    }
    if (role === "dialog" || ariaModal || tag === "dialog") {
      return {
        category: "dialog",
        semanticType: "dialog",
        reason: ariaModal ? "aria-modal=true" : "dialog ancestor",
      };
    }
    if (tag === "form" || role === "form") {
      return {
        category: "form",
        semanticType: "form",
        reason: "form ancestor",
      };
    }
    if (tag === "li" || role === "listitem" || role === "menuitem" || role === "tab") {
      return {
        category: "list_item",
        semanticType: tag === "li" ? "list item" : role,
        reason: "list or menu ancestor",
      };
    }
    if (tag === "tr" || role === "row") {
      return {
        category: "table_row",
        semanticType: "table row",
        reason: "table row ancestor",
      };
    }
    if (tag === "section" || tag === "article" || tag === "main" || tag === "aside") {
      return {
        category: "section",
        semanticType: "section",
        reason: "section-style container",
      };
    }
    if (tag === "div" && /(?:card|panel|sheet|tile)/i.test(className)) {
      return {
        category: "card",
        semanticType: "card",
        reason: "card-like class",
      };
    }
    if (tag === "div" && /(?:container|wrapper|content|panel|section)/i.test(className)) {
      return {
        category: "container",
        semanticType: text ? "container" : "container",
        reason: "container-like class",
      };
    }
    if (text && childCount <= 4 && (tag === "span" || tag === "p" || tag === "label" || tag === "strong" || tag === "em" || tag === "b" || tag === "i")) {
      return {
        category: "text_node_parent",
        semanticType: "text node parent",
        reason: "text-bearing parent",
      };
    }
    if (text && (tag === "div" || tag === "section" || tag === "article" || tag === "main" || tag === "aside")) {
      return {
        category: "container",
        semanticType: "container",
        reason: "meaningful container",
      };
    }
    if (INTERACTIVE_TAGS.has(tag) || INTERACTIVE_ROLES.has(role)) {
      return {
        category: "container",
        semanticType: inferSemanticType(tag, role, "container", className),
        reason: "interactive control",
      };
    }
    return {
      category: "container",
      semanticType: "container",
      reason: "generic container",
    };
  }

  function buildSelectorHint(tag, role, attrs, semanticType) {
    const dataTestId = normalizeSpace(attrs["data-testid"] || attrs["data-test-id"] || attrs["data-test"] || attrs["data-qa"] || attrs["data-cy"], 120);
    if (dataTestId) {
      return `[data-testid="${dataTestId}"]`;
    }
    const ariaLabel = normalizeSpace(attrs["aria-label"], 120);
    if (ariaLabel && (semanticType === "button" || semanticType === "link" || semanticType === "checkbox" || semanticType === "radio" || semanticType === "combobox" || semanticType === "textbox")) {
      return `[aria-label="${ariaLabel}"]`;
    }
    if (tag === "code" || tag === "pre" || tag === "section" || tag === "article" || tag === "main" || tag === "aside" || tag === "form" || tag === "li" || tag === "tr") {
      return tag;
    }
    if (role) {
      return `[role="${role}"]`;
    }
    if (tag) {
      return tag;
    }
    return "element";
  }

  function quoteLocator(value) {
    return JSON.stringify(String(value || ""));
  }

  function buildLocatorHint(tag, role, attrs, cleanText, semanticType) {
    const dataTestId = normalizeSpace(attrs["data-testid"] || attrs["data-test-id"] || attrs["data-test"] || attrs["data-qa"] || attrs["data-cy"], 120);
    if (dataTestId) {
      return `get_by_test_id(${quoteLocator(dataTestId)})`;
    }
    const ariaLabel = normalizeSpace(attrs["aria-label"], 120);
    if (ariaLabel && (semanticType === "button" || semanticType === "link" || semanticType === "checkbox" || semanticType === "radio" || semanticType === "combobox" || semanticType === "textbox")) {
      return `get_by_label(${quoteLocator(ariaLabel)})`;
    }
    if ((semanticType === "button" || semanticType === "link" || semanticType === "checkbox" || semanticType === "radio" || semanticType === "combobox" || semanticType === "textbox") && cleanText) {
      const roleName = semanticType === "textbox" ? "textbox" : semanticType;
      return `get_by_role(${quoteLocator(roleName)}, name=${quoteLocator(cleanText)})`;
    }
    if (semanticType === "tab panel" || semanticType === "dialog" || semanticType === "form") {
      return buildSelectorHint(tag, role, attrs, semanticType);
    }
    if ((semanticType === "code block" || semanticType === "pre block") && cleanText && cleanText.length <= MAX_OPTION_TEXT_LENGTH) {
      return `get_by_text(${quoteLocator(cleanText)}, exact=True)`;
    }
    if (cleanText && cleanText.length <= MAX_OPTION_TEXT_LENGTH) {
      return `get_by_text(${quoteLocator(cleanText)}, exact=True)`;
    }
    const selectorHint = buildSelectorHint(tag, role, attrs, semanticType);
    if (selectorHint) {
      return selectorHint;
    }
    return "";
  }

  function scoreCandidate(candidate) {
    if (!candidate) {
      return -1;
    }
    const tag = normalizeSpace(candidate.tag || "", 48).toLowerCase();
    const role = normalizeSpace(candidate.role || "", 48).toLowerCase();
    const className = normalizeSpace(candidate.className || "", 220);
    const text = normalizeSpace(candidate.cleanText || candidate.text || "", MAX_CANDIDATE_TEXT_LENGTH);
    const attrs = candidate.attributes && typeof candidate.attributes === "object" ? candidate.attributes : {};
    const semanticType = normalizeSpace(candidate.semanticType || candidate.category || "", 80).toLowerCase();
    let score = 0;

    if (candidate.level === 0) {
      score += 100;
    }

    if (INTERACTIVE_TAGS.has(tag) || INTERACTIVE_ROLES.has(role) || semanticType === "button" || semanticType === "link" || semanticType === "checkbox" || semanticType === "radio" || semanticType === "combobox" || semanticType === "textbox") {
      score += 300;
    }
    if (semanticType === "code block" || semanticType === "pre block" || tag === "code" || tag === "pre" || /(?:code|language|prism|token|codeblock)/i.test(className)) {
      score += 260;
    }
    if (semanticType === "tab panel" || role === "tabpanel") {
      score += 240;
    }
    if (semanticType === "dialog" || role === "dialog" || normalizeSpace(attrs["aria-modal"], 16).toLowerCase() === "true") {
      score += 230;
    }
    if (semanticType === "form" || tag === "form" || role === "form") {
      score += 220;
    }
    if (semanticType === "section") {
      score += 200;
    }
    if (semanticType === "card") {
      score += 190;
    }
    if (semanticType === "list item") {
      score += 180;
    }
    if (semanticType === "table row") {
      score += 170;
    }
    if (semanticType === "text node parent") {
      score += 150;
    }
    if (semanticType === "container") {
      score += 120;
    }
    if (text) {
      score += Math.min(40, Math.floor(text.length / 10));
    }
    if (candidate.id) {
      score += 20;
    }
    if (candidate.ariaLabel) {
      score += 20;
    }
    if (attrs["data-testid"] || attrs["data-test-id"] || attrs["data-test"] || attrs["data-qa"] || attrs["data-cy"]) {
      score += 25;
    }
    score -= Math.min(30, Math.max(0, Number(candidate.level) || 0) * 2);
    return score;
  }

  function pickCandidateIndex(candidates) {
    let bestIndex = 0;
    let bestScore = -1;
    for (let index = 0; index < candidates.length; index += 1) {
      const score = scoreCandidate(candidates[index]);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    }
    return bestIndex;
  }

  function buildCandidate(el, level) {
    if (!el || el.nodeType !== 1) {
      return null;
    }
    const tag = getTag(el);
    if (!tag || tag === "html" || tag === "body") {
      return null;
    }
    const className = getClassName(el);
    const role = getRole(el, tag);
    const attrs = collectAttributes(el, tag, role, className);
    let text = "";
    try {
      text = normalizeSpace(el.innerText || el.textContent || "", MAX_CANDIDATE_TEXT_LENGTH);
    } catch (_) {}
    const childCount = el.children ? el.children.length : 0;
    const classification = classifyCandidate(el, level, tag, role, attrs, text, className, childCount);
    const semanticType = classification.semanticType || inferSemanticType(tag, role, classification.category, className);
    const selectorHint = buildSelectorHint(tag, role, attrs, semanticType);
    const locatorHint = buildLocatorHint(tag, role, attrs, text, semanticType);
    const reason = classification.reason || "generic container";
    const candidate = {
      level,
      tag,
      role,
      ariaLabel: normalizeSpace(attrs["aria-label"] || "", 160),
      text,
      cleanText: text,
      className,
      id: normalizeSpace(attrs.id || "", 120),
      attributes: attrs,
      selectorHint,
      locatorHint,
      reason,
      category: classification.category || "container",
      semanticType,
    };
    if (candidate.category === "container" && !candidate.text && !candidate.id && !candidate.className && !candidate.role && !candidate.selectorHint && !candidate.locatorHint) {
      return null;
    }
    return candidate;
  }

  function snapshot(el) {
    const candidates = [];
    let current = el;
    let level = 0;
    while (current && level <= MAX_ANCESTOR_DEPTH) {
      const candidate = buildCandidate(current, level);
      if (candidate) {
        candidates.push(candidate);
      }
      current = current.parentElement;
      level += 1;
    }

    const selectedCandidateIndex = candidates.length > 0 ? pickCandidateIndex(candidates) : 0;
    const selectedCandidate = candidates[selectedCandidateIndex] || candidates[0] || null;
    if (!selectedCandidate) {
      return {
        tag: "element",
        id: "",
        class: "",
        className: "",
        text: "",
        clean_text: "",
        cleanText: "",
        role: "",
        ariaLabel: "",
        semantic_type: "",
        selector_hint: "",
        locator_hint: "",
        attributes: {},
        selected_candidate_index: 0,
        candidates: [],
      };
    }
    return {
      tag: selectedCandidate.tag || "element",
      id: selectedCandidate.id || "",
      class: selectedCandidate.className || "",
      className: selectedCandidate.className || "",
      text: selectedCandidate.text || "",
      clean_text: selectedCandidate.cleanText || "",
      cleanText: selectedCandidate.cleanText || "",
      role: selectedCandidate.role || "",
      ariaLabel: selectedCandidate.ariaLabel || "",
      semantic_type: selectedCandidate.semanticType || selectedCandidate.category || "",
      selector_hint: selectedCandidate.selectorHint || "",
      locator_hint: selectedCandidate.locatorHint || "",
      attributes: selectedCandidate.attributes || {},
      selected_candidate_index: selectedCandidateIndex,
      candidates,
    };
  }

  function highlight(el) {
    try {
      if (lastEl && prevOutline !== null) {
        lastEl.style.outline = prevOutline;
        lastEl.style.outlineOffset = prevOutlineOffset;
        lastEl.style.cursor = prevCursor;
      }
    } catch (_) {}
    lastEl = el;
    try {
      prevOutline = el.style.outline;
      prevOutlineOffset = el.style.outlineOffset;
      prevCursor = el.style.cursor;
      el.style.outline = "2px solid #7dd3fc";
      el.style.outlineOffset = "2px";
      el.style.cursor = "crosshair";
    } catch (_) {}
  }

  function clearSelection() {
    try {
      if (selectedTimer) {
        clearTimeout(selectedTimer);
        selectedTimer = null;
      }
    } catch (_) {}
    try {
      if (selectedEl) {
        selectedEl.style.outline = selectedOutline;
        selectedEl.style.outlineOffset = selectedOutlineOffset;
        selectedEl.style.boxShadow = selectedBoxShadow;
      }
    } catch (_) {}
    try {
      if (selectedBadge && selectedBadge.parentNode) {
        selectedBadge.parentNode.removeChild(selectedBadge);
      }
    } catch (_) {}
    selectedEl = null;
    selectedOutline = null;
    selectedOutlineOffset = null;
    selectedBoxShadow = null;
    selectedBadge = null;
    lastEl = null;
    prevOutline = null;
    prevOutlineOffset = null;
    prevCursor = null;
  }

  function confirmSelection(el) {
    clearSelection();
    selectedEl = el;
    try {
      selectedOutline = el.style.outline;
      selectedOutlineOffset = el.style.outlineOffset;
      selectedBoxShadow = el.style.boxShadow;
      el.style.outline = "3px solid #22c55e";
      el.style.outlineOffset = "2px";
      el.style.boxShadow = "0 0 0 4px rgba(34, 197, 94, 0.18)";
    } catch (_) {}
    try {
      const rect = el.getBoundingClientRect();
      if (rect && rect.width > 0 && rect.height > 0 && document.body) {
        const badge = document.createElement("div");
        badge.textContent = "Attached";
        badge.setAttribute("data-autoworkbench-picker", "selected");
        badge.style.position = "fixed";
        badge.style.zIndex = "2147483647";
        badge.style.pointerEvents = "none";
        badge.style.padding = "4px 8px";
        badge.style.borderRadius = "999px";
        badge.style.background = "#22c55e";
        badge.style.color = "#fff";
        badge.style.font = "600 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        badge.style.boxShadow = "0 6px 18px rgba(34, 197, 94, 0.35)";
        badge.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - 88))}px`;
        badge.style.top = `${Math.max(8, rect.top - 8)}px`;
        badge.style.transform = "translateY(-100%)";
        document.body.appendChild(badge);
        selectedBadge = badge;
      }
    } catch (_) {}
    try {
      selectedTimer = window.setTimeout(() => {
        clearSelection();
      }, 1200);
    } catch (_) {}
  }

  function cleanup() {
    armed = false;
    try {
      document.removeEventListener("mousemove", onMove, true);
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("keydown", onKey, true);
    } catch (_) {}
    try {
      if (lastEl && lastEl !== selectedEl && prevOutline !== null) {
        lastEl.style.outline = prevOutline;
        lastEl.style.outlineOffset = prevOutlineOffset;
        lastEl.style.cursor = prevCursor;
      }
    } catch (_) {}
    lastEl = null;
  }

  function onMove(e) {
    if (!armed) return;
    const el = e.target;
    if (!el || el === document.documentElement || el === document.body) return;
    highlight(el);
  }

  async function onClick(e) {
    if (!armed) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    const el = e.target;
    confirmSelection(el);
    cleanup();
    try {
      await window.__pickerPicked__(snapshot(el));
    } catch (_) {}
  }

  function onKey(e) {
    if (!armed) return;
    if (e.key === "Escape") {
      cleanup();
    }
  }

  function arm() {
    clearSelection();
    cleanup();
    armed = true;
    document.addEventListener("mousemove", onMove, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKey, true);
  }

  window.__pickerCleanup__ = cleanup;
  window.__pickerArm__ = arm;
  arm();
})();
"""
    await page.add_init_script(script)
    try:
        await page.evaluate(script)
    except Exception:
        pass
