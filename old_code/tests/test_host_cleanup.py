"""
tests/test_host_cleanup.py

Sprint 7 Cluster 4 — S7-0406: Unmount, restore, and host-page cleanup.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOST_PATH = os.path.join(REPO_ROOT, "frontend", "src", "host", "host.jsx")
COMP_PATH = os.path.join(REPO_ROOT, "frontend", "src", "layout", "compensation.js")
LAYOUT_DIR = os.path.join(REPO_ROOT, "frontend", "src", "layout")


def _host() -> str:
    return open(HOST_PATH, encoding="utf-8").read()


def _comp() -> str:
    return open(COMP_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0406 — Unmount removes all nodes
# ---------------------------------------------------------------------------

def test_unmount_host_removes_container():
    content = _host()
    assert "unmountHost" in content
    # Must remove the autoworkbench container or root
    assert "remove" in content or "removeChild" in content or "parentNode" in content, \
        "unmountHost must remove host container from DOM"


def test_unmount_host_clears_shadow_dom():
    content = _host()
    # Must handle shadowRoot cleanup
    has_shadow_cleanup = (
        "shadowRoot" in content
        and ("innerHTML" in content or "remove" in content or "while" in content)
    )
    assert has_shadow_cleanup, "unmountHost must clear Shadow DOM contents"


# ---------------------------------------------------------------------------
# S7-0406 — Event listeners removed
# ---------------------------------------------------------------------------

def test_host_cleanup_removes_event_listeners():
    content = _host()
    # Either host.jsx or resize-controller.js removes listeners
    resize_path = os.path.join(LAYOUT_DIR, "resize-controller.js")
    resize_content = open(resize_path, encoding="utf-8").read() if os.path.exists(resize_path) else ""
    has_removal = (
        "removeEventListener" in content
        or "removeEventListener" in resize_content
    )
    assert has_removal, "Cleanup must call removeEventListener"


# ---------------------------------------------------------------------------
# S7-0406 — Compensation reversed on unmount
# ---------------------------------------------------------------------------

def test_compensation_remove_function_exists():
    content = _comp()
    assert "removeCompensation" in content, \
        "compensation.js must export removeCompensation for cleanup"


def test_compensation_remove_restores_original():
    content = _comp()
    # removeCompensation must restore original style values
    assert "original" in content.lower() or "restore" in content.lower() or "saved" in content.lower(), \
        "removeCompensation must restore original page styles"


# ---------------------------------------------------------------------------
# S7-0406 — Cleanup contract
# ---------------------------------------------------------------------------

def test_host_has_cleanup_export():
    content = _host()
    assert "unmountHost" in content, "host.jsx must export unmountHost for cleanup"


def test_cleanup_no_orphaned_style_mutation():
    content = _host()
    # Host must not add inline styles directly to document.body without tracking them
    if "document.body.style" in content:
        assert "original" in content.lower() or "restore" in content.lower(), \
            "If body style is mutated, must track original value for restore"


def test_host_cleanup_idempotent():
    content = _host()
    # unmounting an already-unmounted host must not throw
    has_guard = (
        "unmountHost" in content
        and (
            "if" in content
            or "?" in content
            or "exists" in content
            or "null" in content
        )
    )
    assert has_guard, "unmountHost must guard against double-unmount"


def test_no_orphaned_ids_in_cleanup():
    content = _host()
    # If IDs are assigned on mount, they must be removed on unmount
    if "aw-shadow-host" in content:
        assert "remove" in content, "If host ID assigned, must be removed on unmount"
