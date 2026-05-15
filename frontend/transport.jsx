// transport.jsx — minimal WS read-path bridge (T-1 from the master
// integration map, docs/superpowers/specs/2026-05-15-frontend-backend-
// integration-map.md §6 T-1).
//
// Opens ws://<host>/ws on page load, parses every typed envelope from
// the backend, and translates a curated subset into edits on the same
// useTweaks value bag the Tweaks dev panel already mutates. The
// translation is one-way (server → UI). No buttons are wired here; T-2
// and onward will add the outbound surface.
//
// Why a CustomEvent ('aw:set')? useTweaks lives inside a React tree;
// we can't import its setter from this file. The Tweaks panel already
// exposes itself via a window event for its own host protocol, so we
// reuse the same shape: dispatch `aw:set` with a `detail` object of
// edits, and the useTweaks effect folds them into state.

(function () {
  var AW = (window.AW = window.AW || {});
  AW.connection = "connecting";
  AW.lastEvent = null;

  // ---- event → tweak-edit map ------------------------------------------------
  // Each entry receives the full envelope and returns an edits object to
  // dispatch via 'aw:set', or null/undefined to skip. Keep this table the
  // single source of truth for the read path; do not scatter mapping logic
  // across other files.
  var EVENT_MAP = {
    ready: function (e) {
      var backend = e && e.backend_ready;
      var browser = e && e.browser_ready;
      // If either degraded flag is set, the dedicated event still arrives
      // separately and will override this. Default to idle when both are
      // truthy or unspecified.
      if (backend === false) return null;
      if (browser === false) return { state: "nobrowser" };
      return { state: "idle" };
    },
    api_key_required: function () { return { state: "apikey" }; },
    no_browser: function () { return { state: "nobrowser" }; },
    run_started: function () { return { state: "exec" }; },
    page_analysis_started: function () { return { state: "planning" }; },
    page_summary_ready: function () { return { state: "recommend" }; },
    recommendation_ready: function () { return { state: "recommend" }; },
    plan_ready: function () { return { state: "plan" }; },
    clarification_needed: function () { return { state: "clarify" }; },
    human_input_required: function () { return { state: "otp" }; },
    plan_diff_proposed: function () { return { state: "diff" }; },
    permission_required: function () { return { state: "permit" }; },
    step_executing: function () { return { state: "exec" }; },
    step_failed: function () { return { state: "recover" }; },
    precondition_failed: function () { return { state: "recover" }; },
    recovery_needed: function () { return { state: "recover" }; },
    recovery_needed_structured: function () { return { state: "recover" }; },
    locator_update_request: function () { return { state: "locator" }; },
    locator_candidates_ready: function () { return { state: "locator" }; },
    run_completed: function () { return { state: "done" }; },
    e2e_pending: function () { return { state: "e2e" }; },
    schema_error: function () { return { state: "schema" }; },
    provider_error: function () { return { state: "schema" }; },
    malformed_output_error: function () { return { state: "schema" }; },
  };

  function dispatchSet(edits) {
    if (!edits) return;
    try {
      window.dispatchEvent(new CustomEvent("aw:set", { detail: edits }));
    } catch (err) {
      // Older WebKit needs the constructor polyfill, but every supported
      // browser ships CustomEvent. Swallow rather than crash transport.
    }
  }

  function applyEvent(envelope) {
    if (!envelope || typeof envelope !== "object") return;
    AW.lastEvent = envelope;
    var t = String(envelope.type || "");
    var mapper = EVENT_MAP[t];
    if (mapper) dispatchSet(mapper(envelope));

    // Surface a few non-state events for future consumers without
    // forcing them through aw:set.
    if (t === "agent_settings") AW.agentSettings = envelope;
    if (t === "endpoint_registry") AW.endpoints = envelope;
    if (t === "session_state") AW.sessionState = envelope;
    if (t === "token_report") AW.tokenReport = envelope;
    if (t === "runtime_rejected") AW.lastRejection = envelope;

    // Fan-out for arbitrary listeners (future cards / tabs).
    var list = AW._listeners && AW._listeners[t];
    if (list) list.forEach(function (fn) { try { fn(envelope); } catch (_) {} });
    var any = AW._listeners && AW._listeners["*"];
    if (any) any.forEach(function (fn) { try { fn(envelope); } catch (_) {} });
  }

  // ---- socket lifecycle -----------------------------------------------------
  var ws = null;
  var backoff = 500;
  var stopped = false;

  function wsUrl() {
    // Overlay injection (browser.py) passes ws URL via window.AW.wsUrl.
    // When the extension overlay runs on an external site (playwright.dev,
    // etc.) location.host is the wrong target; we must use the configured
    // backend URL. Falls back to same-origin for the dev panel served by
    // server.py, then to 127.0.0.1:8765 for file:// fixtures.
    if (AW && typeof AW.wsUrl === "string" && AW.wsUrl) return AW.wsUrl;
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    var host = location.host || "127.0.0.1:8765";
    return proto + "//" + host + "/ws";
  }

  function setConn(label) {
    AW.connection = label;
    dispatchSet({ connection: label });
  }

  function open() {
    if (stopped) return;
    setConn("connecting");
    try {
      ws = new WebSocket(wsUrl());
    } catch (err) {
      console.warn("[transport] WS construct failed:", err);
      scheduleReconnect();
      return;
    }

    ws.addEventListener("open", function () {
      backoff = 500;
      setConn("connected");
      console.log("[transport] WS open");
    });

    ws.addEventListener("message", function (ev) {
      var payload = null;
      try { payload = JSON.parse(ev.data); } catch (_) { return; }
      applyEvent(payload);
    });

    ws.addEventListener("close", function () {
      setConn("offline");
      dispatchSet({ state: "offline" });
      scheduleReconnect();
    });

    ws.addEventListener("error", function (err) {
      console.warn("[transport] WS error:", err);
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
    try {
      ws.send(JSON.stringify(msg));
      return true;
    } catch (err) {
      console.warn("[transport] send threw:", err);
      return false;
    }
  };

  AW.on = function on(type, fn) {
    AW._listeners = AW._listeners || {};
    (AW._listeners[type] = AW._listeners[type] || []).push(fn);
    return function off() {
      var list = AW._listeners[type];
      if (!list) return;
      var i = list.indexOf(fn);
      if (i >= 0) list.splice(i, 1);
    };
  };

  AW.stop = function stop() {
    stopped = true;
    if (ws) try { ws.close(); } catch (_) {}
  };

  // T-6: explicit reconnect. Cancels the current backoff timer (if any),
  // resets the delay, closes any lingering socket, and opens a fresh one
  // immediately. Safe to call from any state.
  AW.reconnect = function reconnect() {
    stopped = false;
    backoff = 500;
    if (ws) {
      try { ws.close(); } catch (_) {}
      ws = null;
    }
    open();
  };

  // Kick connection once the document is ready so we don't race with the
  // shadow / babel pipeline.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", open, { once: true });
  } else {
    open();
  }
})();
