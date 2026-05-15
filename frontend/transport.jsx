// transport.jsx — WS bridge between the FastAPI backend and the v4 UI.
//
// Backend (server.py) emits typed envelopes; we translate them into the v4
// state-machine knobs (TWEAK keys) that drive the panel. This file is the ONE
// place where wire protocol meets UI state — keep all event→state mapping
// here so app.jsx / chrome.jsx never reach for WebSocket directly.
//
// Wire model:
//   server → client : { type: "<event>", payload: {...}, ... }
//   client → server : { type: "<command>", ... }
//
// Phase-1 surface:
//   • Auto-connect on load, exponential backoff on close.
//   • Map a curated subset of typed events to v4 state strings.
//   • Expose window.AW.send(msg)  for buttons / Composer.
//   • Expose window.AW.setTweak(k,v) (already installed by tweaks-panel).

(function () {
  const AW = (window.AW = window.AW || {});
  AW.connection = "connecting";
  AW.lastEvent = null;

  // ── event → state map ─────────────────────────────────────────────────
  // Backend event types that should switch the v4 state machine. Functions
  // receive the full envelope and return either a state string or null.
  const EVENT_TO_STATE = {
    ready: (e) => {
      const ok = e && e.backend_ready && e.browser_ready !== false;
      return ok ? "idle" : null;
    },
    api_key_required: () => "apikey",
    no_browser: () => "nobrowser",
    run_started: () => "exec",
    page_analysis_started: () => "planning",
    page_summary_ready: () => "recommend",
    recommendation_ready: () => "recommend",
    plan_ready: () => "plan",
    plan_diff: () => "diff",
    permission_required: () => "permit",
    human_input_required: () => "otp",
    step_executing: () => "exec",
    step_failed: () => "recover",
    precondition_failed: () => "recover",
    recovery_needed: () => "recover",
    locator_update_request: () => "locator",
    run_completed: () => "done",
    e2e_pending: () => "e2e",
    schema_error: () => "schema",
    provider_error: () => "schema",
    malformed_output_error: () => "schema",
  };

  function dispatchSet(edits) {
    window.dispatchEvent(new CustomEvent("aw:set", { detail: edits }));
  }

  function applyEvent(envelope) {
    if (!envelope || typeof envelope !== "object") return;
    AW.lastEvent = envelope;
    const t = String(envelope.type || "");
    const mapper = EVENT_TO_STATE[t];
    if (mapper) {
      const next = mapper(envelope);
      if (next) dispatchSet({ state: next });
    }
    // Surface registry / settings for future popovers without touching state.
    if (t === "agent_settings") AW.agentSettings = envelope;
    if (t === "endpoint_registry") AW.endpoints = envelope;
    // Fan out to any user listeners (window.AW.on("<type>", fn)).
    const list = AW._listeners && AW._listeners[t];
    if (list) list.forEach((fn) => { try { fn(envelope); } catch (_) {} });
    const any = AW._listeners && AW._listeners["*"];
    if (any) any.forEach((fn) => { try { fn(envelope); } catch (_) {} });
  }

  // ── socket lifecycle ──────────────────────────────────────────────────
  let ws = null;
  let backoff = 500;
  let stopped = false;

  function wsUrl() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return proto + "//" + location.host + "/ws";
  }

  function setConn(label) {
    AW.connection = label;
    dispatchSet({ connection: label });
  }

  function open() {
    if (stopped) return;
    try {
      ws = new WebSocket(wsUrl());
    } catch (e) {
      console.warn("[transport] WS construct failed:", e);
      scheduleReconnect();
      return;
    }
    setConn("connecting");

    ws.addEventListener("open", () => {
      backoff = 500;
      setConn("connected");
      console.log("[transport] WS open");
    });

    ws.addEventListener("message", (ev) => {
      let payload = null;
      try { payload = JSON.parse(ev.data); } catch (_) { return; }
      applyEvent(payload);
    });

    ws.addEventListener("close", () => {
      setConn("offline");
      dispatchSet({ state: "offline" });
      scheduleReconnect();
    });

    ws.addEventListener("error", (e) => {
      console.warn("[transport] WS error:", e);
    });
  }

  function scheduleReconnect() {
    if (stopped) return;
    setTimeout(open, backoff);
    backoff = Math.min(backoff * 2, 8000);
  }

  AW.send = function send(msg) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn("[transport] send while closed:", msg);
      return false;
    }
    ws.send(JSON.stringify(msg));
    return true;
  };

  AW.on = function on(type, fn) {
    AW._listeners = AW._listeners || {};
    (AW._listeners[type] = AW._listeners[type] || []).push(fn);
    return () => {
      const list = AW._listeners[type];
      if (!list) return;
      const i = list.indexOf(fn);
      if (i >= 0) list.splice(i, 1);
    };
  };

  AW.stop = function stop() { stopped = true; if (ws) ws.close(); };

  // Kick connection after the page parses.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", open, { once: true });
  } else {
    open();
  }
})();
