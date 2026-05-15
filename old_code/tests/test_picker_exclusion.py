"""
tests/test_picker_exclusion.py

Sprint 7 Cluster 4 — S7-0408: Picker exclusion for AutoWorkbench UI.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")
LAYOUT_DIR = os.path.join(FRONTEND_SRC, "layout")
PICKER_PATH = os.path.join(LAYOUT_DIR, "picker-exclusion.js")
HOST_PATH = os.path.join(FRONTEND_SRC, "host", "host.jsx")


def _picker() -> str:
    return open(PICKER_PATH, encoding="utf-8").read()


def _host() -> str:
    return open(HOST_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0408 — picker-exclusion.js exists
# ---------------------------------------------------------------------------

def test_picker_exclusion_js_exists():
    assert os.path.exists(PICKER_PATH), "frontend/src/layout/picker-exclusion.js missing"


def test_picker_exclusion_not_empty():
    assert os.path.getsize(PICKER_PATH) > 100


# ---------------------------------------------------------------------------
# S7-0408 — Exclusion selector
# ---------------------------------------------------------------------------

def test_picker_exclusion_exports_selector():
    content = _picker()
    assert "PICKER_EXCLUSION_SELECTOR" in content, \
        "picker-exclusion.js must export PICKER_EXCLUSION_SELECTOR"


def test_picker_exclusion_selector_includes_shadow_host():
    content = _picker()
    assert "aw-shadow-host" in content or "#autoworkbench-root" in content, \
        "PICKER_EXCLUSION_SELECTOR must exclude aw-shadow-host"


def test_picker_exclusion_exports_is_excluded():
    content = _picker()
    assert "isExcluded" in content, \
        "picker-exclusion.js must export isExcluded(element) function"


def test_picker_exclusion_exports_get_exclusion_filter():
    content = _picker()
    assert "getExclusionFilter" in content or "createFilter" in content or "isExcluded" in content, \
        "picker-exclusion.js must export a filter/check function"


# ---------------------------------------------------------------------------
# S7-0408 — Host element has aw-autoworkbench attribute
# ---------------------------------------------------------------------------

def test_host_marks_elements_with_aw_attribute():
    content = _host()
    # Host elements must be marked with a data attribute for picker exclusion
    has_marker = (
        "data-autoworkbench" in content
        or "data-aw-" in content
        or "aw-no-pick" in content
        or "aw-ui" in content
    )
    assert has_marker, "host.jsx must mark elements with data-autoworkbench attribute for picker exclusion"


# ---------------------------------------------------------------------------
# S7-0408 — Exclusion works in all dock modes
# ---------------------------------------------------------------------------

def test_picker_exclusion_applies_to_all_modes():
    content = _picker()
    # Must not have mode-specific conditions that would skip exclusion
    has_mode_bypass = re.search(r"if.*floating.*return.*true|if.*hidden.*return.*false", content)
    assert not has_mode_bypass, \
        "picker-exclusion must apply regardless of dock mode"


# ---------------------------------------------------------------------------
# S7-0408 — isExcluded logic
# ---------------------------------------------------------------------------

def test_picker_exclusion_checks_ancestor():
    content = _picker()
    # Must check if element is inside aw shadow host (not just direct host check)
    has_ancestor_check = (
        "closest" in content
        or "contains" in content
        or "parentNode" in content
        or "ancestor" in content.lower()
    )
    assert has_ancestor_check, "isExcluded must check if element is inside aw shadow host"


def test_picker_exclusion_no_backend_imports():
    content = _picker()
    bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
    assert not bad, "picker-exclusion.js must not import from backend"


def test_picker_exclusion_no_demo_constants():
    content = _picker()
    assert "DEMO_" not in content and "MOCK_" not in content
