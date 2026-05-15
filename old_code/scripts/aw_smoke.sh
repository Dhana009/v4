#!/usr/bin/env bash
# Sprint-7 smoke gate. Runs jsdom + build + cheap backend + fake-stream E2E.
# Exits non-zero on the first failure so CI / pre-commit can chain it.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== [1/4] frontend jsdom ==="
( cd frontend && npm test -- --run )

echo "=== [2/4] frontend build ==="
( cd frontend && npm run build )

echo "=== [3/4] backend cheap regression (no e2e) ==="
unset OPENAI_API_KEY || true
python -m pytest --tb=short -q --ignore=tests/e2e

echo "=== [4/4] fake-stream E2E smoke ==="
AUTOWORKBENCH_E2E_MODE=fake_llm \
AUTOWORKBENCH_LLM_MODE=complete_llm \
python -m pytest \
  tests/e2e/test_v4_panel_smoke.py \
  tests/e2e/test_mvp_001_lifecycle_smoke.py -q

echo "OK"
