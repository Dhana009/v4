"""
tests/test_frontend_build.py

Sprint 7 Cluster 3 — S7-0301: Frontend architecture audit build verification.
TDD: written before implementation; build tests should pass currently.
"""
from __future__ import annotations

import os
import subprocess

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
FRONTEND_SRC = os.path.join(FRONTEND_DIR, "src")


# ---------------------------------------------------------------------------
# S7-0301 — Entry point and build system
# ---------------------------------------------------------------------------

def test_frontend_src_entry_point_exists():  # S7-0301
    assert os.path.exists(os.path.join(FRONTEND_SRC, "main.jsx"))


def test_frontend_package_json_exists():  # S7-0301
    assert os.path.exists(os.path.join(FRONTEND_DIR, "package.json"))


def test_frontend_package_json_has_build_script():  # S7-0301
    import json
    pkg = json.load(open(os.path.join(FRONTEND_DIR, "package.json")))
    assert "build" in pkg.get("scripts", {})


def test_frontend_build_command_is_esbuild():  # S7-0301
    import json
    pkg = json.load(open(os.path.join(FRONTEND_DIR, "package.json")))
    build_cmd = pkg["scripts"]["build"]
    assert "esbuild" in build_cmd


def test_frontend_has_react_dependency():  # S7-0301
    import json
    pkg = json.load(open(os.path.join(FRONTEND_DIR, "package.json")))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert "react" in deps


def test_frontend_entry_point_imports_styles():  # S7-0301
    entry = open(os.path.join(FRONTEND_SRC, "main.jsx")).read()
    assert "styles.css" in entry or "style" in entry.lower()


def test_frontend_entry_point_has_shadow_dom_host():  # S7-0301
    entry = open(os.path.join(FRONTEND_SRC, "main.jsx")).read()
    assert "attachShadow" in entry or "shadowRoot" in entry or "SHADOW" in entry


def test_frontend_entry_point_has_websocket_transport():  # S7-0301
    entry = open(os.path.join(FRONTEND_SRC, "main.jsx")).read()
    assert "WebSocket" in entry


def test_frontend_entry_point_has_command_builder():  # S7-0301
    entry = open(os.path.join(FRONTEND_SRC, "main.jsx")).read()
    assert "buildFrontendCommandEnvelope" in entry or "command" in entry.lower()


def test_frontend_main_jsx_line_count_exceeds_200():  # S7-0301 — monolith risk doc
    lines = open(os.path.join(FRONTEND_SRC, "main.jsx")).readlines()
    assert len(lines) > 200, "Expected monolith (>200 lines) to document for split"


def test_frontend_prototype_exists():  # S7-0301
    proto = os.path.join(REPO_ROOT, "frontend_new_design_prototype")
    assert os.path.exists(proto)


def test_frontend_prototype_has_llm_tab():  # S7-0301
    llm_tab = os.path.join(REPO_ROOT, "frontend_new_design_prototype", "llm-tab.jsx")
    assert os.path.exists(llm_tab)


def test_frontend_prototype_has_app():  # S7-0301
    app = os.path.join(REPO_ROOT, "frontend_new_design_prototype", "app.jsx")
    assert os.path.exists(app)


# ---------------------------------------------------------------------------
# Build execution test (runs npm build — slow but required for Cluster 3 evidence)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_frontend_npm_build_succeeds():  # S7-0301
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"Build failed:\n{result.stderr}"


@pytest.mark.slow
def test_frontend_build_produces_js_bundle():  # S7-0301
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, capture_output=True, timeout=120)
    dist_js = os.path.join(FRONTEND_DIR, "dist", "autoworkbench.js")
    assert os.path.exists(dist_js), "dist/autoworkbench.js missing after build"


@pytest.mark.slow
def test_frontend_build_produces_css():  # S7-0301
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, capture_output=True, timeout=120)
    dist_css = os.path.join(FRONTEND_DIR, "dist", "autoworkbench.css")
    assert os.path.exists(dist_css), "dist/autoworkbench.css missing after build"
