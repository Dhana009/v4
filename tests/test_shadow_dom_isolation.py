"""
tests/test_shadow_dom_isolation.py

Sprint 7 Cluster 4 — S7-0407: Shadow DOM style isolation and host-page safety.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")
HOST_PATH = os.path.join(FRONTEND_SRC, "host", "host.jsx")
TOKENS_PATH = os.path.join(FRONTEND_SRC, "styles", "tokens.css")
GLOBALS_PATH = os.path.join(FRONTEND_SRC, "styles", "globals.css")
LAYOUT_DIR = os.path.join(FRONTEND_SRC, "layout")


def _host() -> str:
    return open(HOST_PATH, encoding="utf-8").read()


def _tokens() -> str:
    return open(TOKENS_PATH, encoding="utf-8").read()


def _globals() -> str:
    return open(GLOBALS_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0407 — CSS variable namespacing
# ---------------------------------------------------------------------------

def test_tokens_all_vars_use_aw_prefix():
    content = _tokens()
    var_lines = [l.strip() for l in content.splitlines() if l.strip().startswith("--")]
    non_aw_vars = [l for l in var_lines if not l.startswith("--aw-")]
    assert len(non_aw_vars) == 0, \
        f"All CSS variables must use --aw- prefix. Violations:\n" + "\n".join(non_aw_vars)


def test_globals_uses_host_selector_for_isolation():
    content = _globals()
    assert ":host" in content, "globals.css must use :host selector for Shadow DOM isolation"


def test_globals_has_all_initial():
    content = _globals()
    assert "all: initial" in content or "all:initial" in content, \
        "globals.css must reset page styles via 'all: initial' in :host"


# ---------------------------------------------------------------------------
# S7-0407 — Shadow DOM style scoping
# ---------------------------------------------------------------------------

def test_host_uses_shadow_dom_not_regular_dom():
    content = _host()
    assert "attachShadow" in content, "host.jsx must use Shadow DOM (attachShadow)"


def test_host_no_global_style_injection():
    content = _host()
    # Must not inject <style> into document.head (would leak styles globally)
    assert "document.head" not in content or "style" not in content, \
        "host.jsx must not inject styles into document.head (use Shadow DOM)"


def test_host_shadow_mode_is_open():
    content = _host()
    assert 'mode: "open"' in content or "mode: 'open'" in content, \
        "Shadow DOM must use open mode for testability"


# ---------------------------------------------------------------------------
# S7-0407 — Z-index safety
# ---------------------------------------------------------------------------

def test_tokens_has_z_index_panel():
    content = _tokens()
    assert "--aw-z-panel" in content, "tokens.css must define --aw-z-panel z-index"


def test_tokens_z_index_panel_high_value():
    content = _tokens()
    # Panel z-index must be >= 10000 per spec
    match = re.search(r"--aw-z-panel:\s*(\d+)", content)
    if match:
        value = int(match.group(1))
        assert value >= 10000, f"--aw-z-panel must be >= 10000, got {value}"
    else:
        assert False, "--aw-z-panel not found or not a plain number"


# ---------------------------------------------------------------------------
# S7-0407 — No CSS leakage
# ---------------------------------------------------------------------------

def test_layout_files_no_document_head_style_injection():
    for fname in os.listdir(LAYOUT_DIR):
        if not fname.endswith(".js"):
            continue
        path = os.path.join(LAYOUT_DIR, fname)
        content = open(path, encoding="utf-8").read()
        assert "document.head" not in content, \
            f"{fname} injects into document.head (style leak risk)"


def test_host_no_unscoped_css_in_source():
    content = _host()
    # No raw CSS property assignments on page-level elements except for compensation tracking
    # (compensation.js owns page style mutations, not host.jsx)
    page_style_mutation = re.search(r"document\.(body|documentElement|html)\.style\.", content)
    if page_style_mutation:
        # OK if it's just removing a style (setting to "")
        assert False, \
            "host.jsx must not mutate document.body.style directly — use compensation.js"
