"""
tests/test_frontend_a11y.py

Sprint 7 Cluster 3 — S7-0308: Frontend data-testid and accessibility baseline.
TDD: written before implementation.
"""
from __future__ import annotations

import os
import re

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")
PRIMITIVES_DIR = os.path.join(FRONTEND_SRC, "components", "primitives")


def _primitives_exist():
    return os.path.isdir(PRIMITIVES_DIR)


# ---------------------------------------------------------------------------
# S7-0308 — Primitive components have data-testid
# ---------------------------------------------------------------------------

def test_button_primitive_has_data_testid():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Button.jsx")
    if not os.path.exists(path):
        pytest.skip("Button.jsx not yet created")
    content = open(path).read()
    assert "data-testid" in content, "Button.jsx must include data-testid"


def test_card_primitive_has_data_testid():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Card.jsx")
    if not os.path.exists(path):
        pytest.skip("Card.jsx not yet created")
    content = open(path).read()
    assert "data-testid" in content, "Card.jsx must include data-testid"


def test_badge_primitive_has_data_testid():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Badge.jsx")
    if not os.path.exists(path):
        pytest.skip("Badge.jsx not yet created")
    content = open(path).read()
    assert "data-testid" in content, "Badge.jsx must include data-testid"


def test_empty_state_has_data_testid():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "EmptyState.jsx")
    if not os.path.exists(path):
        pytest.skip("EmptyState.jsx not yet created")
    content = open(path).read()
    assert "data-testid" in content, "EmptyState.jsx must include data-testid"


def test_inline_alert_has_data_testid():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "InlineAlert.jsx")
    if not os.path.exists(path):
        pytest.skip("InlineAlert.jsx not yet created")
    content = open(path).read()
    assert "data-testid" in content, "InlineAlert.jsx must include data-testid"


# ---------------------------------------------------------------------------
# S7-0308 — Button supports aria-label (accessibility)
# ---------------------------------------------------------------------------

def test_button_supports_aria_label():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Button.jsx")
    if not os.path.exists(path):
        pytest.skip("Button.jsx not yet created")
    content = open(path).read()
    assert "aria-label" in content or "ariaLabel" in content, (
        "Button.jsx must support aria-label prop"
    )


def test_button_supports_disabled_state():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Button.jsx")
    if not os.path.exists(path):
        pytest.skip("Button.jsx not yet created")
    content = open(path).read()
    assert "disabled" in content, "Button.jsx must support disabled state"


def test_button_supports_onClick():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Button.jsx")
    if not os.path.exists(path):
        pytest.skip("Button.jsx not yet created")
    content = open(path).read()
    assert "onClick" in content, "Button.jsx must support onClick handler"


# ---------------------------------------------------------------------------
# S7-0308 — Primitives use design tokens (not hardcoded colors)
# ---------------------------------------------------------------------------

_HARDCODED_COLOR_RE = re.compile(r"(?<!\-\-)(?<!var\()#[0-9a-fA-F]{3,8}")


def test_button_uses_css_vars_not_hardcoded_colors():  # S7-0308, S7-0303
    path = os.path.join(PRIMITIVES_DIR, "Button.jsx")
    if not os.path.exists(path):
        pytest.skip("Button.jsx not yet created")
    content = open(path).read()
    inline_styles = re.findall(r"style=\{[^}]+\}", content)
    combined = " ".join(inline_styles)
    hardcoded = _HARDCODED_COLOR_RE.findall(combined)
    assert not hardcoded, f"Button.jsx has hardcoded colors in inline styles: {hardcoded}"


# ---------------------------------------------------------------------------
# S7-0308 — data-testid naming convention check
# ---------------------------------------------------------------------------

_TESTID_RE = re.compile(r'data-testid=["\']([^"\']+)["\']')


def test_button_testid_follows_naming_convention():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "Button.jsx")
    if not os.path.exists(path):
        pytest.skip("Button.jsx not yet created")
    content = open(path).read()
    testids = _TESTID_RE.findall(content)
    if not testids:
        return
    for testid in testids:
        assert " " not in testid, f"testid must not contain spaces: {testid}"
        assert testid == testid.lower() or "{" in testid, (
            f"testid should be lowercase or dynamic: {testid}"
        )


# ---------------------------------------------------------------------------
# S7-0308 — All primitive files exist
# ---------------------------------------------------------------------------

_EXPECTED_PRIMITIVES = [
    "Button.jsx",
    "Card.jsx",
    "Badge.jsx",
    "StatusPill.jsx",
    "EmptyState.jsx",
    "InlineAlert.jsx",
    "ActionRow.jsx",
    "CodeBlock.jsx",
    "TimelineRow.jsx",
    "CandidateCard.jsx",
]


def test_all_expected_primitives_exist():  # S7-0307, S7-0308
    if not _primitives_exist():
        pytest.skip("primitives/ not yet created")
    missing = []
    for fname in _EXPECTED_PRIMITIVES:
        if not os.path.exists(os.path.join(PRIMITIVES_DIR, fname)):
            missing.append(fname)
    assert not missing, f"Missing primitive components: {missing}"


def test_each_primitive_is_under_100_lines():  # GOV-S7-C3 — no monolith primitives
    if not _primitives_exist():
        pytest.skip("primitives/ not yet created")
    oversized = []
    for fname in os.listdir(PRIMITIVES_DIR):
        if not fname.endswith(".jsx"):
            continue
        fpath = os.path.join(PRIMITIVES_DIR, fname)
        line_count = len(open(fpath).readlines())
        if line_count > 100:
            oversized.append(f"{fname}: {line_count} lines")
    assert not oversized, f"Primitive components exceed 100 lines: {oversized}"


# ---------------------------------------------------------------------------
# S7-0308 — StatusPill covers lifecycle states
# ---------------------------------------------------------------------------

def test_status_pill_covers_key_states():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "StatusPill.jsx")
    if not os.path.exists(path):
        pytest.skip("StatusPill.jsx not yet created")
    content = open(path).read()
    for state in ("completed", "running", "failed"):
        assert state in content, f"StatusPill.jsx missing state: {state}"


# ---------------------------------------------------------------------------
# S7-0308 — CodeBlock has accessible structure
# ---------------------------------------------------------------------------

def test_code_block_uses_pre_or_code_element():  # S7-0308
    path = os.path.join(PRIMITIVES_DIR, "CodeBlock.jsx")
    if not os.path.exists(path):
        pytest.skip("CodeBlock.jsx not yet created")
    content = open(path).read()
    assert "<pre" in content or "<code" in content, (
        "CodeBlock.jsx must use <pre> or <code> for accessibility"
    )
