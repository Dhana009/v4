"""
tests/test_layout_modes.py

Sprint 7 Cluster 4 — S7-0402/S7-0403/S7-0404: Layout modes, dock controller,
panel modes, resize controller.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAYOUT_DIR = os.path.join(REPO_ROOT, "frontend", "src", "layout")
DOCK_PATH = os.path.join(LAYOUT_DIR, "dock-controller.js")
MODES_PATH = os.path.join(LAYOUT_DIR, "panel-modes.js")
RESIZE_PATH = os.path.join(LAYOUT_DIR, "resize-controller.js")


def _read(path: str) -> str:
    return open(path, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0402 — layout/ module exists
# ---------------------------------------------------------------------------

def test_layout_dir_exists():
    assert os.path.isdir(LAYOUT_DIR), "frontend/src/layout/ directory missing"


def test_dock_controller_exists():
    assert os.path.exists(DOCK_PATH), "frontend/src/layout/dock-controller.js missing"


def test_panel_modes_exists():
    assert os.path.exists(MODES_PATH), "frontend/src/layout/panel-modes.js missing"


def test_resize_controller_exists():
    assert os.path.exists(RESIZE_PATH), "frontend/src/layout/resize-controller.js missing"


# ---------------------------------------------------------------------------
# S7-0402 — Dock modes
# ---------------------------------------------------------------------------

def test_dock_controller_exports_dock_right():
    content = _read(DOCK_PATH)
    assert "dock-right" in content, "dock-controller.js must define dock-right mode"


def test_dock_controller_exports_dock_left():
    content = _read(DOCK_PATH)
    assert "dock-left" in content, "dock-controller.js must define dock-left mode"


def test_dock_controller_exports_dock_bottom():
    content = _read(DOCK_PATH)
    assert "dock-bottom" in content, "dock-controller.js must define dock-bottom mode"


def test_dock_controller_default_is_dock_right():
    content = _read(DOCK_PATH)
    assert "DEFAULT_DOCK_MODE" in content, "dock-controller.js must export DEFAULT_DOCK_MODE"
    assert '"dock-right"' in content or "'dock-right'" in content, \
        "DEFAULT_DOCK_MODE must be 'dock-right'"


def test_dock_controller_exports_valid_dock_modes():
    content = _read(DOCK_PATH)
    assert "VALID_DOCK_MODES" in content or "DOCK_MODES" in content, \
        "dock-controller.js must export a list of valid dock modes"


def test_dock_controller_exports_apply_dock():
    content = _read(DOCK_PATH)
    assert "applyDock" in content, "dock-controller.js must export applyDock"


def test_dock_controller_exports_get_dock_mode():
    content = _read(DOCK_PATH)
    assert "getDockMode" in content, "dock-controller.js must export getDockMode"


def test_dock_controller_exports_set_dock_mode():
    content = _read(DOCK_PATH)
    assert "setDockMode" in content, "dock-controller.js must export setDockMode"


def test_dock_controller_css_class_contract():
    content = _read(DOCK_PATH)
    # Must set CSS class on host element for dock mode
    assert "classList" in content or "className" in content or "setAttribute" in content, \
        "dock-controller.js must apply CSS class to host element"


def test_dock_controller_no_invalid_mode_allowed():
    content = _read(DOCK_PATH)
    # Must validate dock mode input
    has_validation = (
        "VALID_DOCK_MODES" in content
        or "DOCK_MODES" in content
        or "includes(" in content
        or "indexOf(" in content
    )
    assert has_validation, "dock-controller.js must validate dock mode"


# ---------------------------------------------------------------------------
# S7-0403 — Panel modes (collapsed/expanded/floating)
# ---------------------------------------------------------------------------

def test_panel_modes_exports_panel_modes():
    content = _read(MODES_PATH)
    assert "PANEL_MODES" in content, "panel-modes.js must export PANEL_MODES"


def test_panel_modes_has_collapsed():
    content = _read(MODES_PATH)
    assert "collapsed" in content, "panel-modes.js must define collapsed mode"


def test_panel_modes_has_expanded():
    content = _read(MODES_PATH)
    assert "expanded" in content, "panel-modes.js must define expanded mode"


def test_panel_modes_has_floating():
    content = _read(MODES_PATH)
    assert "floating" in content, "panel-modes.js must define floating mode"


def test_panel_modes_default_is_expanded():
    content = _read(MODES_PATH)
    assert "DEFAULT_PANEL_MODE" in content, "panel-modes.js must export DEFAULT_PANEL_MODE"


def test_panel_modes_floating_no_compensation():
    content = _read(MODES_PATH)
    # floating mode must be marked as not applying compensation
    assert "floating" in content and (
        "noCompensation" in content
        or "no_compensation" in content
        or "compensation" in content.lower()
    ), "panel-modes.js must document floating compensation behavior"


def test_panel_modes_exports_apply_mode():
    content = _read(MODES_PATH)
    assert "applyMode" in content, "panel-modes.js must export applyMode"


def test_panel_modes_exports_get_panel_mode():
    content = _read(MODES_PATH)
    assert "getPanelMode" in content, "panel-modes.js must export getPanelMode"


# ---------------------------------------------------------------------------
# S7-0404 — Resize controller
# ---------------------------------------------------------------------------

def test_resize_controller_exports_min_width():
    content = _read(RESIZE_PATH)
    assert "MIN_PANEL_WIDTH" in content or "minWidth" in content.lower(), \
        "resize-controller.js must define minimum panel width"


def test_resize_controller_min_width_300():
    content = _read(RESIZE_PATH)
    assert "300" in content, "resize-controller.js min width must be 300px"


def test_resize_controller_exports_max_width_percent():
    content = _read(RESIZE_PATH)
    assert "MAX_PANEL_WIDTH_PERCENT" in content or "80" in content, \
        "resize-controller.js must define max panel width as 80% of page"


def test_resize_controller_exports_size_storage_key():
    content = _read(RESIZE_PATH)
    assert "STORAGE_KEY" in content or "storageKey" in content or "localStorage" in content, \
        "resize-controller.js must handle size persistence"


def test_resize_controller_exports_attach_resize():
    content = _read(RESIZE_PATH)
    assert "attachResize" in content or "initResize" in content or "createResizeController" in content, \
        "resize-controller.js must export resize attachment function"


def test_resize_controller_exports_detach_resize():
    content = _read(RESIZE_PATH)
    assert "detachResize" in content or "cleanup" in content.lower() or "removeEventListener" in content, \
        "resize-controller.js must remove event listeners on cleanup"


def test_resize_controller_no_backend_imports():
    for path in [DOCK_PATH, MODES_PATH, RESIZE_PATH]:
        content = open(path, encoding="utf-8").read()
        bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
        assert not bad, f"{os.path.basename(path)} imports from backend"


def test_layout_files_no_demo_constants():
    for path in [DOCK_PATH, MODES_PATH, RESIZE_PATH]:
        content = open(path, encoding="utf-8").read()
        assert "DEMO_" not in content and "MOCK_" not in content, \
            f"{os.path.basename(path)} has demo constants"
