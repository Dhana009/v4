from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable, Optional

from dotenv import load_dotenv
from playwright.async_api import BrowserContext, Page, async_playwright


_lock = asyncio.Lock()
_pw: Any | None = None
_context: BrowserContext | None = None
_active_page: Page | None = None
_port: int | None = None
_start_url: str | None = None

# Picker state: armed for exactly one click, then disarmed.
_picker_step_id: str | None = None
_picker_send: Optional[Callable[[dict], Awaitable[None]]] = None


def _read_port() -> int:
    global _port
    if _port is not None:
        return _port
    load_dotenv(override=True)
    _port = int(os.getenv("PORT", "8765"))
    return _port


def _read_start_url() -> str:
    global _start_url
    if _start_url is not None:
        return _start_url
    load_dotenv(override=True)
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
        _context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
        )

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
    Injects a floating in-page overlay with the full panel UI and a WebSocket client.
    Uses add_init_script so it survives navigations.
    """
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
          max-height: 130px;
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
          <button type="button" class="ac-correct">Correct</button>
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
          understandingEl.value = parts.join("\\n").trim();
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

  function snapshot(el) {
    const attrs = {};
    try {
      for (const a of Array.from(el.attributes || [])) attrs[a.name] = a.value;
    } catch (_) {}
    let text = "";
    try { text = (el.innerText || el.textContent || "").trim().slice(0, 200); } catch (_) {}
    return {
      tag: (el.tagName || "").toLowerCase(),
      id: el.id || "",
      class: el.className || "",
      text,
      attributes: attrs,
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

  function cleanup() {
    armed = false;
    try {
      document.removeEventListener("mousemove", onMove, true);
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("keydown", onKey, true);
    } catch (_) {}
    try {
      if (lastEl && prevOutline !== null) {
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
