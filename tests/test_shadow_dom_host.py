"""
tests/test_shadow_dom_host.py

Sprint 7 Cluster 4 — S7-0401: Shadow DOM host cleanup and mount lifecycle.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOST_PATH = os.path.join(REPO_ROOT, "frontend", "src", "host", "host.jsx")


def _host_content() -> str:
    return open(HOST_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0401 — host.jsx structure
# ---------------------------------------------------------------------------

def test_host_jsx_exists():
    assert os.path.exists(HOST_PATH), "frontend/src/host/host.jsx missing"


def test_host_jsx_not_stub():
    content = _host_content()
    assert "SHADOW_HOST_ID" in content
    assert len(content.splitlines()) > 15, "host.jsx still a stub (too few lines)"


def test_host_jsx_exports_create_host():
    content = _host_content()
    assert "createHost" in content, "host.jsx must export createHost"


def test_host_jsx_exports_mount_host():
    content = _host_content()
    assert "mountHost" in content, "host.jsx must export mountHost"


def test_host_jsx_exports_unmount_host():
    content = _host_content()
    assert "unmountHost" in content, "host.jsx must export unmountHost"


def test_host_jsx_exports_get_host_root():
    content = _host_content()
    assert "getHostRoot" in content, "host.jsx must export getHostRoot"


def test_host_jsx_exports_get_host_container():
    content = _host_content()
    assert "getHostContainer" in content, "host.jsx must export getHostContainer"


def test_host_jsx_exports_shadow_host_id():
    content = _host_content()
    assert "SHADOW_HOST_ID" in content


def test_host_jsx_exports_shadow_mount_id():
    content = _host_content()
    assert "SHADOW_MOUNT_ID" in content


# ---------------------------------------------------------------------------
# S7-0401 — Idempotency contract
# ---------------------------------------------------------------------------

def test_host_jsx_has_idempotent_mount_check():
    content = _host_content()
    # Must check for existing host before creating new one
    has_idempotent = (
        "shadowRoot" in content
        and ("getElementById" in content or "querySelector" in content)
    )
    assert has_idempotent, "host.jsx must check for existing host (idempotency)"


def test_host_jsx_attach_shadow_mode_open():
    content = _host_content()
    assert 'mode: "open"' in content or "mode:'open'" in content or "mode: 'open'" in content, \
        "host.jsx must use attachShadow({mode: 'open'})"


# ---------------------------------------------------------------------------
# S7-0401 — Cleanup contract
# ---------------------------------------------------------------------------

def test_host_jsx_has_cleanup_in_unmount():
    content = _host_content()
    # unmountHost must contain removal logic
    assert "remove" in content or "removeChild" in content, \
        "unmountHost must remove DOM nodes"


def test_host_jsx_no_backend_imports():
    content = _host_content()
    bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
    assert not bad, f"host.jsx imports from backend module: {bad.group() if bad else ''}"


def test_host_jsx_no_demo_constants():
    content = _host_content()
    assert "DEMO_" not in content
    assert "MOCK_" not in content
    assert "FAKE_" not in content


def test_host_jsx_under_200_lines():
    content = _host_content()
    lines = [l for l in content.splitlines() if l.strip() and not l.strip().startswith("//")]
    assert len(lines) <= 200, f"host.jsx has {len(lines)} non-comment lines; max 200"


def test_host_jsx_data_testid_present():
    content = _host_content()
    assert "data-testid" in content, "host.jsx must set data-testid on host element"
