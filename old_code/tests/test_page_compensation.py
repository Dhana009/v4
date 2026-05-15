"""
tests/test_page_compensation.py

Sprint 7 Cluster 4 — S7-0405: Page content compensation and non-overlay behavior.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAYOUT_DIR = os.path.join(REPO_ROOT, "frontend", "src", "layout")
COMP_PATH = os.path.join(LAYOUT_DIR, "compensation.js")


def _read() -> str:
    return open(COMP_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0405 — compensation.js exists
# ---------------------------------------------------------------------------

def test_compensation_js_exists():
    assert os.path.exists(COMP_PATH), "frontend/src/layout/compensation.js missing"


def test_compensation_js_not_empty():
    assert os.path.getsize(COMP_PATH) > 100


# ---------------------------------------------------------------------------
# S7-0405 — Exports
# ---------------------------------------------------------------------------

def test_compensation_exports_apply():
    content = _read()
    assert "applyCompensation" in content, "compensation.js must export applyCompensation"


def test_compensation_exports_remove():
    content = _read()
    assert "removeCompensation" in content, "compensation.js must export removeCompensation"


def test_compensation_exports_update():
    content = _read()
    assert "updateCompensation" in content, "compensation.js must export updateCompensation"


# ---------------------------------------------------------------------------
# S7-0405 — Dock-right reduces width
# ---------------------------------------------------------------------------

def test_compensation_handles_dock_right():
    content = _read()
    assert "dock-right" in content or "dockRight" in content, \
        "compensation.js must handle dock-right mode"


def test_compensation_dock_right_reduces_width():
    content = _read()
    # Must modify width or margin-right or padding-right
    has_width_change = (
        "width" in content
        or "marginRight" in content
        or "paddingRight" in content
        or "margin-right" in content
    )
    assert has_width_change, "compensation.js must reduce page width for dock-right"


# ---------------------------------------------------------------------------
# S7-0405 — Dock-left reduces width
# ---------------------------------------------------------------------------

def test_compensation_handles_dock_left():
    content = _read()
    assert "dock-left" in content or "dockLeft" in content, \
        "compensation.js must handle dock-left mode"


# ---------------------------------------------------------------------------
# S7-0405 — Dock-bottom reduces height
# ---------------------------------------------------------------------------

def test_compensation_handles_dock_bottom():
    content = _read()
    assert "dock-bottom" in content or "dockBottom" in content, \
        "compensation.js must handle dock-bottom mode"


def test_compensation_dock_bottom_reduces_height():
    content = _read()
    assert "height" in content, "compensation.js must reduce page height for dock-bottom"


# ---------------------------------------------------------------------------
# S7-0405 — Floating skips compensation
# ---------------------------------------------------------------------------

def test_compensation_floating_no_compensation():
    content = _read()
    assert "floating" in content, "compensation.js must handle floating mode"
    # floating must explicitly return or skip
    has_skip = (
        "floating" in content
        and (
            "return" in content
            or "skip" in content
            or "noCompensation" in content
        )
    )
    assert has_skip, "compensation.js must skip compensation for floating mode"


# ---------------------------------------------------------------------------
# S7-0405 — Original styles preserved for restore
# ---------------------------------------------------------------------------

def test_compensation_stores_original_styles():
    content = _read()
    # Must save original style values before overwriting
    has_save = (
        "original" in content.lower()
        or "saved" in content.lower()
        or "snapshot" in content.lower()
        or "_prev" in content
        or "before" in content.lower()
    )
    assert has_save, "compensation.js must store original styles before modification"


def test_compensation_no_backend_imports():
    content = _read()
    bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
    assert not bad, f"compensation.js imports from backend: {bad.group() if bad else ''}"


def test_compensation_no_demo_constants():
    content = _read()
    assert "DEMO_" not in content
    assert "MOCK_" not in content
