// Unified frontend logger. Ships every log line both to the browser console and
// to the backend /api/log endpoint so /tmp/aw-launch.log captures the full
// stack trace (backend + frontend) in one file.
//
// Format mirrors runtime/log.py: each emitted record is `{category, level, ...kv}`.
// Backend re-emits as `[ISO] [FRONT] [CATEGORY] key=val ...`.
//
// Levels:
//   info  — high-signal (default).
//   debug — firehose, opt-in via window.__awLogLevel = "debug" or
//           ?aw_log=debug on the host URL.
//
// Ring buffer is kept on window.__awLog__ (last 500 records) so audit_walk.py
// can dump it from the page without listening for individual frames.

const RING_SIZE = 500;
const ENDPOINT = "/api/log";

const INFO_CATEGORIES = new Set([
  "WS_RECV", "WS_SEND", "WS_OPEN", "WS_CLOSE", "WS_ERROR",
  "REDUCER", "STATE", "COMMAND", "PANEL", "PHASE",
  "ERROR",
]);

function resolveLevel() {
  try {
    if (typeof window !== "undefined") {
      const fromWin = window.__awLogLevel;
      if (typeof fromWin === "string") return fromWin.toLowerCase();
      const params = new URLSearchParams(window.location?.search || "");
      const fromParam = (params.get("aw_log") || "").toLowerCase();
      if (fromParam) return fromParam;
    }
  } catch (_) {}
  return "info";
}

function ringPush(record) {
  try {
    if (typeof window === "undefined") return;
    if (!Array.isArray(window.__awLog__)) window.__awLog__ = [];
    window.__awLog__.push(record);
    if (window.__awLog__.length > RING_SIZE) window.__awLog__.shift();
  } catch (_) {}
}

function shouldEmit(level, category) {
  if (level === "error") return true;
  if (resolveLevel() === "debug") return true;
  return INFO_CATEGORIES.has(category);
}

function backendUrl() {
  try {
    if (typeof window === "undefined") return ENDPOINT;
    // when panel is injected into a third-party host, /api/log resolves against
    // the host page, which has no backend route. Build an absolute URL.
    const wsUrl = window.__awBackendBaseUrl__ || null;
    if (wsUrl) return wsUrl.replace(/\/$/, "") + ENDPOINT;
    return ENDPOINT;
  } catch (_) { return ENDPOINT; }
}

function postToBackend(record) {
  try {
    if (typeof fetch !== "function") return;
    const url = backendUrl();
    // fire-and-forget; keepalive lets it survive a navigation.
    fetch(url, {
      method: "POST",
      keepalive: true,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(record),
    }).catch(() => {});
  } catch (_) {}
}

function consoleEmit(record) {
  try {
    const line = `[${record.category}]`;
    if (record.level === "error") {
      // eslint-disable-next-line no-console
      console.error(line, record);
    } else {
      // eslint-disable-next-line no-console
      console.log(line, record);
    }
  } catch (_) {}
}

export function log(category, kv) {
  const record = {
    category: String(category || "FRONT"),
    level: "info",
    ts: Date.now(),
    ...(kv && typeof kv === "object" ? kv : {}),
  };
  ringPush(record);
  if (!shouldEmit("info", record.category)) return;
  consoleEmit(record);
  postToBackend(record);
}

export function logError(category, message, kv) {
  const err = (kv && kv.error) || null;
  const stack = err && err.stack ? String(err.stack).split("\n").slice(0, 12).join("\\n") : null;
  const record = {
    category: String(category || "ERROR"),
    level: "error",
    ts: Date.now(),
    message: String(message || ""),
    stack,
    ...(kv && typeof kv === "object" ? kv : {}),
  };
  // strip non-serialisable error before posting
  delete record.error;
  ringPush(record);
  consoleEmit(record);
  postToBackend(record);
}

export function attachGlobalHandlers() {
  if (typeof window === "undefined") return;
  if (window.__awLogHandlersInstalled__) return;
  window.__awLogHandlersInstalled__ = true;
  window.addEventListener("error", (e) => {
    logError("WINDOW_ERROR", String(e?.message || "window error"), {
      filename: e?.filename, lineno: e?.lineno, colno: e?.colno,
      stack: e?.error?.stack ? String(e.error.stack).slice(0, 1200) : null,
    });
  });
  window.addEventListener("unhandledrejection", (e) => {
    const reason = e?.reason;
    logError("UNHANDLED_REJECTION", String(reason?.message || reason || "unhandled rejection"), {
      stack: reason?.stack ? String(reason.stack).slice(0, 1200) : null,
    });
  });
}

export default { log, logError, attachGlobalHandlers };
