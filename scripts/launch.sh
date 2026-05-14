#!/usr/bin/env bash
# scripts/launch.sh — canonical single-window local launch of AutoWorkbench.
#
# Usage:
#   bash scripts/launch.sh                         # opens local fixture page
#   bash scripts/launch.sh https://playwright.dev  # opens any URL behind the panel
#
# Behavior:
#   - Kills anything bound to :8765 (backend) and :8000 (fixture static server).
#   - Wipes .pw-user-data so Chromium starts from a clean profile (no stale tabs).
#   - If no URL arg and no $START_URL in env, serves the bundled fixture app
#     on http://127.0.0.1:8000 and uses that as START_URL so the user always
#     lands on a page that exercises the v4 panel.
#   - Execs `python server.py` in the foreground so all logs (panel/runtime/LLM)
#     stream to the terminal. Backend's headed Chromium opens automatically;
#     the v4 bundle auto-injects via inject_panel. One window. One process tree.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- choose START_URL -------------------------------------------------------
CLI_URL="${1:-}"
ENV_URL="${START_URL:-}"
FIXTURE_PATH="$REPO_ROOT/tests/e2e/fixtures/test_app/index.html"

FIXTURE_SERVER_PID=""
trap 'if [ -n "$FIXTURE_SERVER_PID" ]; then kill "$FIXTURE_SERVER_PID" 2>/dev/null || true; fi' EXIT

if [ -n "$CLI_URL" ]; then
  TARGET_URL="$CLI_URL"
elif [ -n "$ENV_URL" ]; then
  TARGET_URL="$ENV_URL"
else
  if [ ! -f "$FIXTURE_PATH" ]; then
    echo "[launch] fixture index.html missing at $FIXTURE_PATH" >&2
    exit 1
  fi
  TARGET_URL="http://127.0.0.1:8000/index.html"
fi

# --- free ports + reset chromium profile -----------------------------------
echo "[launch] freeing :8765 and :8000"
for port in 8765 8000; do
  pids="$(lsof -ti :$port 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "[launch] killing pid(s) $pids on :$port"
    kill -9 $pids 2>/dev/null || true
  fi
done

if [ -d "$REPO_ROOT/.pw-user-data" ]; then
  echo "[launch] removing stale .pw-user-data"
  rm -rf "$REPO_ROOT/.pw-user-data"
fi

# --- optionally start the fixture static server ----------------------------
if [[ "$TARGET_URL" == "http://127.0.0.1:8000/"* ]] || [[ "$TARGET_URL" == "http://localhost:8000/"* ]]; then
  echo "[launch] starting fixture static server on http://127.0.0.1:8000"
  (cd "$REPO_ROOT/tests/e2e/fixtures/test_app" && python -m http.server 8000 --bind 127.0.0.1) \
    >/tmp/aw-fixture-static.log 2>&1 &
  FIXTURE_SERVER_PID=$!
  # wait up to 5s for the server to come up
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sSf "http://127.0.0.1:8000/index.html" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

# --- ensure frontend bundle is built ---------------------------------------
if [ ! -f "$REPO_ROOT/frontend/dist/autoworkbench.js" ] || [ ! -f "$REPO_ROOT/frontend/dist/autoworkbench.css" ]; then
  echo "[launch] frontend bundle missing — building"
  (cd "$REPO_ROOT/frontend" && npm run build) || {
    echo "[launch] frontend build failed" >&2
    exit 1
  }
fi

# --- run the backend (one process tree; backend launches headed Chromium) --
echo "[launch] START_URL=$TARGET_URL"
echo "[launch] running: python server.py"
export START_URL="$TARGET_URL"
exec python server.py
