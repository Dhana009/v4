"""
capture_fe_baselines.py
=======================
Playwright-based capture script for AutoWorkbench FE baseline screenshots.

Loads the frontend via a local HTTP server (http://127.0.0.1:PORT/index.html)
using the current sources in frontend/.  A local server is required because
index.html loads React/Babel from CDN and local JSX files via relative paths
which do not work from file://.

For each of the 17 canonical FE states, injects JS to set the tweak state
via window.dispatchEvent('aw:set'), then screenshots the .aw-panel element.
Writes: tests/fixtures/fe_states/<state>/baseline.png

Usage:
    python scripts/capture_fe_baselines.py

Requirements:
    pip install playwright && playwright install chromium
    pip install Pillow   # optional, only needed by the test harness
"""

from __future__ import annotations

import http.server
import pathlib
import socket
import sys
import threading
import time

# ---------------------------------------------------------------------------
# Playwright availability check
# ---------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
except ImportError:
    print(
        "ERROR: playwright is not installed.\n"
        "Fix: pip install playwright && playwright install chromium"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "fe_states"

if not FRONTEND_DIR.exists():
    print(f"ERROR: frontend/ directory not found at {FRONTEND_DIR}")
    sys.exit(1)

INDEX_HTML = FRONTEND_DIR / "index.html"
if not INDEX_HTML.exists():
    print(f"ERROR: frontend/index.html not found at {INDEX_HTML}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Viewport
# ---------------------------------------------------------------------------
VIEWPORT = {"width": 1440, "height": 900}

# ---------------------------------------------------------------------------
# State definitions
# Mapping: (test_state, app_state, app_tab, extra_js)
#   test_state : directory name under tests/fixtures/fe_states/
#   app_state  : value for the "state" tweak (matches STATE_META keys in app.jsx)
#   app_tab    : value for the "tab" tweak ("llm" | "steps" | "rec" | "code" | "trace")
#   extra_js   : optional JS to inject after setting state (or None)
# ---------------------------------------------------------------------------

_TOKEN_REPORT_EVENT = """{
    "type": "token_report",
    "input_tokens": 6200,
    "output_tokens": 1850,
    "estimated_cost": 0.12,
    "model": "gpt-4o-2024-11-20",
    "run_id": "run_a91b"
}"""

_CLARIFICATION_EVENT = """{
    "type": "clarification_needed",
    "question": "Should I run smoke, sanity, or exhaustive regression checks?",
    "options": ["Smoke (~30s)", "Sanity (~2min)", "Exhaustive regression (~10min)"]
}"""

STATE_CONFIGS: list[tuple[str, str, str, str | None]] = [
    # (test_state,        app_state,   app_tab, extra_js)
    ("idle",              "idle",      "llm",   None),
    ("clarification",     "clarify",   "llm",   f"window.AW._applyEvent({_CLARIFICATION_EVENT})"),
    ("planReady",         "plan",      "llm",   None),
    ("permission",        "permit",    "llm",   None),
    ("recommendation",    "recommend", "llm",   None),
    ("execution",         "exec",      "llm",   None),
    ("recovery",          "recover",   "llm",   None),
    ("locatorAmbiguity",  "locator",   "llm",   None),
    ("schemaError",       "schema",    "llm",   None),
    ("completed",         "done",      "llm",   None),
    ("noBrowser",         "nobrowser", "llm",   None),
    ("apiKey",            "apikey",    "llm",   None),
    ("offline",           "offline",   "llm",   None),
    ("tokenReport",       "idle",      "llm",   f"window.AW._applyEvent({_TOKEN_REPORT_EVENT})"),
    ("pagePicker",        "nobrowser", "llm",   None),   # CardNoBrowser: attach/launch UI
    ("traceTab",          "exec",      "trace", None),
    ("recordedTab",       "done",      "rec",   None),
]


# ---------------------------------------------------------------------------
# Local HTTP server
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(directory: pathlib.Path, port: int) -> http.server.HTTPServer:
    """Start a simple static HTTP file server in a background daemon thread."""

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass  # suppress access logs

        def translate_path(self, path: str) -> str:
            import posixpath, urllib.parse, os
            path = urllib.parse.unquote(path)
            path = posixpath.normpath(path)
            parts = [p for p in path.split("/") if p and p not in (os.curdir, os.pardir) and not os.path.dirname(p)]
            result = directory
            for part in parts:
                result = result / part
            return str(result)

    server = http.server.HTTPServer(("127.0.0.1", port), QuietHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inject_aw_apply(page: "Page") -> None:
    """Expose window.AW._applyEvent for optional event-injection payloads."""
    page.evaluate("""() => {
        const AW = window.AW = window.AW || {};
        if (typeof AW._applyEvent !== 'function') {
            AW._applyEvent = function(envelope) {
                if (!envelope || typeof envelope !== 'object') return;
                AW.lastEvent = envelope;
                var t = String(envelope.type || '');
                var list = AW._listeners && AW._listeners[t];
                if (list) list.forEach(function(fn) { try { fn(envelope); } catch(_) {} });
                var any = AW._listeners && AW._listeners['*'];
                if (any) any.forEach(function(fn) { try { fn(envelope); } catch(_) {} });
                if (t === 'token_report') AW.tokenReport = envelope;
                if (t === 'session_state') AW.sessionState = envelope;
            };
        }
    }""")


def _set_state(page: "Page", app_state: str, app_tab: str) -> None:
    """Dispatch aw:set to update the state + tab tweaks atomically."""
    page.evaluate(f"""() => {{
        window.dispatchEvent(new CustomEvent('aw:set', {{
            detail: {{ state: '{app_state}', tab: '{app_tab}' }}
        }}));
    }}""")


def _wait_for_panel(page: "Page", timeout_ms: int = 30000) -> None:
    page.wait_for_selector(".aw-panel", state="visible", timeout=timeout_ms)


def _screenshot_panel(page: "Page", out_path: pathlib.Path) -> None:
    """Screenshot the .aw-panel element at VIEWPORT dimensions."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    el = page.query_selector(".aw-panel")
    if el is None:
        print("  WARNING: .aw-panel not found — full-viewport fallback")
        page.screenshot(path=str(out_path), clip={
            "x": 0, "y": 0,
            "width": VIEWPORT["width"],
            "height": VIEWPORT["height"],
        })
        return

    box = el.bounding_box()
    if box is None:
        page.screenshot(path=str(out_path), clip={
            "x": 0, "y": 0,
            "width": VIEWPORT["width"],
            "height": VIEWPORT["height"],
        })
        return

    clip = {
        "x": max(0.0, box["x"]),
        "y": max(0.0, box["y"]),
        "width": min(box["width"], float(VIEWPORT["width"] - max(0, box["x"]))),
        "height": min(box["height"], float(VIEWPORT["height"] - max(0, box["y"]))),
    }
    page.screenshot(path=str(out_path), clip=clip)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    port = _find_free_port()
    server_url = f"http://127.0.0.1:{port}/index.html"

    print(f"Starting local HTTP server on port {port}, serving: {FRONTEND_DIR}")
    server = _start_server(FRONTEND_DIR, port)
    time.sleep(0.3)

    print(f"Loading: {server_url}")
    print(f"Writing baselines to: {FIXTURES_ROOT}")
    print()

    passed: list[str] = []
    failed: list[tuple[str, str]] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context: BrowserContext = browser.new_context(viewport=VIEWPORT)

            page = context.new_page()

            # Suppress WebSocket attempts (transport.jsx opens ws://<host>/ws
            # where <host> is the page's own origin — the HTTP server does not
            # speak the AW WebSocket protocol, so abort the upgrade).
            page.route("ws://**", lambda route: route.abort())
            page.route("wss://**", lambda route: route.abort())
            page.on("console", lambda m: None)

            print("Opening frontend/index.html …")
            page.goto(server_url, wait_until="networkidle", timeout=60000)

            try:
                _wait_for_panel(page, timeout_ms=30000)
            except Exception as exc:
                print(f"FATAL: .aw-panel never appeared: {exc}")
                browser.close()
                sys.exit(1)

            _inject_aw_apply(page)
            # Allow Babel transpilation + React initial render + WebSocket
            # failure to settle before we start dispatching state changes.
            page.wait_for_timeout(1200)

            for test_state, app_state, app_tab, extra_js in STATE_CONFIGS:
                out_path = FIXTURES_ROOT / test_state / "baseline.png"
                print(f"  [{test_state}]  state={app_state}  tab={app_tab}")
                try:
                    _set_state(page, app_state, app_tab)
                    if extra_js:
                        page.evaluate(f"() => {{ {extra_js}; }}")
                    # Wait for React + Babel to re-render.  600ms is generous
                    # but necessary because Babel compiles JSX at runtime.
                    page.wait_for_timeout(600)
                    # Dispatch again to ensure the state is applied after any
                    # transport.jsx "offline" override (WS close fires aw:set
                    # with {state:"offline"} shortly after page load).
                    _set_state(page, app_state, app_tab)
                    page.wait_for_timeout(400)
                    _screenshot_panel(page, out_path)
                    size_kb = out_path.stat().st_size // 1024
                    print(f"    -> {out_path.relative_to(REPO_ROOT)}  ({size_kb} KB)")
                    passed.append(test_state)
                except Exception as exc:
                    print(f"    FAIL: {exc}")
                    failed.append((test_state, str(exc)))

            browser.close()

    finally:
        server.shutdown()

    print()
    print(f"Done.  {len(passed)}/17 states captured.")
    if failed:
        print("Failed states:")
        for s, e in failed:
            print(f"  {s}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
