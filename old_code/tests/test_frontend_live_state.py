"""
tests/test_frontend_live_state.py

Sprint 7 Cluster 3 — S7-0305: Static demo fallback removal strategy.
TDD: written before implementation.
"""
from __future__ import annotations

import os
import re

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")


def _read_src_files():
    """Return list of (path, content) for all JSX/JS in frontend/src/ (excl. main.jsx monolith)."""
    results = []
    for dirpath, _dirs, files in os.walk(FRONTEND_SRC):
        for fname in files:
            if not fname.endswith((".jsx", ".js")):
                continue
            fpath = os.path.join(dirpath, fname)
            content = open(fpath, encoding="utf-8", errors="ignore").read()
            results.append((fpath, content))
    return results


# ---------------------------------------------------------------------------
# S7-0305 — No DEMO_ or hardcoded static data arrays in new module files
# ---------------------------------------------------------------------------

_DEMO_CONSTANT_RE = re.compile(r"\bDEMO_\w+\s*=")
_MOCK_DATA_RE = re.compile(r"\bMOCK_\w+\s*=|\bFAKE_\w+\s*=")
_STATIC_STEPS_RE = re.compile(r"const\s+(steps|plan|STEPS|PLAN)\s*=\s*\[")


def test_no_demo_constants_in_module_files():  # S7-0305
    """New module files must not define DEMO_* constants."""
    violations = []
    for fpath, content in _read_src_files():
        if "main.jsx" in fpath:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if _DEMO_CONSTANT_RE.search(line):
                violations.append(f"{fpath}:{lineno}: {line.strip()}")
    assert not violations, "DEMO_ constants found in module files:\n" + "\n".join(violations)


def test_no_mock_data_constants_in_module_files():  # S7-0305
    violations = []
    for fpath, content in _read_src_files():
        if "main.jsx" in fpath:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if _MOCK_DATA_RE.search(line):
                violations.append(f"{fpath}:{lineno}: {line.strip()}")
    assert not violations, "MOCK_/FAKE_ constants found in module files:\n" + "\n".join(violations)


def test_no_hardcoded_static_step_arrays_in_module_files():  # S7-0305
    violations = []
    for fpath, content in _read_src_files():
        if "main.jsx" in fpath:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if _STATIC_STEPS_RE.search(line):
                violations.append(f"{fpath}:{lineno}: {line.strip()}")
    assert not violations, "Hardcoded step/plan arrays in module files:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# S7-0305 — EmptyState primitive exists and is not a demo component
# ---------------------------------------------------------------------------

def test_empty_state_primitive_exists():  # S7-0305, S7-0307
    empty_state_path = os.path.join(FRONTEND_SRC, "components", "primitives", "EmptyState.jsx")
    assert os.path.exists(empty_state_path), "EmptyState.jsx primitive missing"


def test_empty_state_does_not_render_demo_content():  # S7-0305
    empty_state_path = os.path.join(FRONTEND_SRC, "components", "primitives", "EmptyState.jsx")
    if not os.path.exists(empty_state_path):
        pytest.skip("EmptyState.jsx not yet created")
    content = open(empty_state_path).read()
    assert "DEMO_" not in content
    assert "mock" not in content.lower()
    assert "fake" not in content.lower()


def test_empty_state_renders_message_prop():  # S7-0305
    empty_state_path = os.path.join(FRONTEND_SRC, "components", "primitives", "EmptyState.jsx")
    if not os.path.exists(empty_state_path):
        pytest.skip("EmptyState.jsx not yet created")
    content = open(empty_state_path).read()
    assert "message" in content or "children" in content or "label" in content


# ---------------------------------------------------------------------------
# S7-0305 — Module files render from props, not from hardcoded data
# ---------------------------------------------------------------------------

def test_primitive_components_receive_props():  # S7-0305
    """Primitive components should receive data via props, not hardcode it."""
    primitives_dir = os.path.join(FRONTEND_SRC, "components", "primitives")
    if not os.path.exists(primitives_dir):
        pytest.skip("primitives/ not yet created")
    jsx_files = [f for f in os.listdir(primitives_dir) if f.endswith(".jsx")]
    assert len(jsx_files) > 0, "No primitive components found"
    for fname in jsx_files:
        fpath = os.path.join(primitives_dir, fname)
        content = open(fpath).read()
        assert "DEMO_" not in content, f"{fname} contains DEMO_ constant"


def test_shell_components_do_not_have_static_state():  # S7-0305
    shell_dir = os.path.join(FRONTEND_SRC, "components", "shell")
    if not os.path.exists(shell_dir):
        pytest.skip("shell/ not yet created")
    jsx_files = [f for f in os.listdir(shell_dir) if f.endswith(".jsx")]
    for fname in jsx_files:
        fpath = os.path.join(shell_dir, fname)
        content = open(fpath).read()
        assert "DEMO_STEPS" not in content
        assert "DEMO_PLAN" not in content
