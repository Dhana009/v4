"""
tests/test_frontend_styles.py

Sprint 7 Cluster 3 — S7-0303: Design token extraction and style system.
TDD: written before implementation; token tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")
TOKENS_PATH = os.path.join(FRONTEND_SRC, "styles", "tokens.css")


# ---------------------------------------------------------------------------
# S7-0303 — tokens.css exists
# ---------------------------------------------------------------------------

def test_tokens_css_exists():  # S7-0303
    assert os.path.exists(TOKENS_PATH), "frontend/src/styles/tokens.css missing"


def test_tokens_css_is_not_empty():  # S7-0303
    assert os.path.getsize(TOKENS_PATH) > 100


# ---------------------------------------------------------------------------
# S7-0303 — CSS custom property coverage
# ---------------------------------------------------------------------------

def _tokens_content():
    return open(TOKENS_PATH, encoding="utf-8").read()


def test_tokens_css_defines_css_custom_properties():  # S7-0303
    content = _tokens_content()
    assert "--" in content, "tokens.css must define CSS custom properties (--var-name)"


def test_tokens_css_has_color_tokens():  # S7-0303
    content = _tokens_content()
    has_color = (
        "--aw-grn" in content
        or "--aw-red" in content
        or "--aw-ink" in content
        or "--color" in content
        or "--aw-color" in content
        or "--clr" in content
    )
    assert has_color, "tokens.css must define color custom properties (--aw-grn/red/ink)"


def test_tokens_css_has_spacing_tokens():  # S7-0303
    content = _tokens_content()
    has_spacing = (
        "--aw-space" in content
        or "--space" in content
        or "--spacing" in content
        or "--gap" in content
        or "--pad" in content
    )
    assert has_spacing, "tokens.css must define spacing custom properties (--aw-space-*)"


def test_tokens_css_has_typography_tokens():  # S7-0303
    content = _tokens_content()
    has_type = (
        "--aw-font" in content
        or "--aw-text" in content
        or "--font" in content
        or "--text" in content
        or "--type" in content
    )
    assert has_type, "tokens.css must define typography custom properties (--aw-font-*)"


def test_tokens_css_has_root_selector():  # S7-0303
    content = _tokens_content()
    assert ":root" in content or ":host" in content, (
        "tokens.css must define vars under :root or :host for Shadow DOM"
    )


def test_tokens_css_no_hardcoded_hex_outside_vars():  # S7-0303
    content = _tokens_content()
    var_lines = [l for l in content.splitlines() if l.strip().startswith("--")]
    # Count hex colors that appear on non-variable-definition lines
    non_var_hex_lines = [
        l for l in content.splitlines()
        if re.search(r"#[0-9a-fA-F]{3,8}", l) and not l.strip().startswith("--")
    ]
    assert len(non_var_hex_lines) == 0, (
        f"Hex colors on non-token lines found:\n" + "\n".join(non_var_hex_lines)
    )


# ---------------------------------------------------------------------------
# S7-0303 — globals.css exists (Shadow DOM scoped globals)
# ---------------------------------------------------------------------------

def test_globals_css_exists():  # S7-0303
    globals_path = os.path.join(FRONTEND_SRC, "styles", "globals.css")
    assert os.path.exists(globals_path), "frontend/src/styles/globals.css missing"


# ---------------------------------------------------------------------------
# S7-0303 — Prototype styles are reference, not copied verbatim
# ---------------------------------------------------------------------------

def test_tokens_css_does_not_contain_tweak_panel_vars():  # S7-0303 — proto isolation
    content = _tokens_content()
    assert "TweakPanel" not in content
    assert "tweak-panel" not in content


def test_tokens_css_does_not_contain_website_vars():  # S7-0303 — proto isolation
    content = _tokens_content()
    assert "aw-site" not in content
    assert "aw-stage" not in content
