from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE = REPO_ROOT / "frontend/package.json"
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"
FRONTEND_HEADER = REPO_ROOT / "frontend/aw-header.jsx"
FRONTEND_TABS = REPO_ROOT / "frontend/aw-tabs.jsx"
E2E_HARNESS = REPO_ROOT / "tests/e2e/harness.py"

PLANNED_ROOT_HOOKS = (
    'data-testid="aw-root"',
    "data-testid='aw-root'",
    'id="aw-root"',
    "id='aw-root'",
    "aw-root",
)
PLANNED_TAB_HOOKS = {
    "LLM": (
        "LLM",
        'data-testid="llm-tab"',
        'data-testid="llm"',
        'aria-label="LLM"',
    ),
    "Steps": (
        "Steps",
        'data-testid="steps-tab"',
        'data-testid="steps"',
        'aria-label="Steps"',
    ),
    "Recorded": (
        "Recorded",
        'data-testid="recorded-tab"',
        'data-testid="recorded"',
        'aria-label="Recorded"',
    ),
    "Code": (
        "Code",
        'data-testid="code-tab"',
        'data-testid="code"',
        'aria-label="Code"',
    ),
    "Trace": (
        "Trace",
        'data-testid="trace-tab"',
        'data-testid="trace"',
        'aria-label="Trace"',
    ),
}
PLANNED_SURFACE_HOOKS = {
    "plan review": (
        'data-testid="plan-review"',
        'aria-label="plan review"',
        "plan review",
    ),
    "clarification": (
        'data-testid="clarification"',
        'aria-label="clarification"',
        "clarification needed",
        "clarification",
    ),
    "recovery": (
        'data-testid="recovery"',
        'aria-label="recovery"',
        "recovery needed",
        "recovery",
    ),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def test_current_frontend_inventory_matches_the_legacy_bootstrap_path() -> None:
    package = json.loads(_read(FRONTEND_PACKAGE))
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)
    header = _read(FRONTEND_HEADER)
    tabs = _read(FRONTEND_TABS)
    harness = _read(E2E_HARNESS)

    assert {"clean", "build"}.issubset(set(package["scripts"]))
    assert "createRoot" in main
    assert "resolveMountNode" in main
    assert "window.IDEPanel" in main
    assert "autoworkbench-root" in main
    assert "#autoworkbench-root .ide-panel" in harness
    assert "workbench" in header
    assert "steps" in header
    assert "code" in header
    assert "debug" in header or "Debug" in tabs
    assert "// plan review" in panel
    assert "// clarification needed" in panel
    assert "// recovery needed" in panel
    assert "// recorded steps" in panel
    assert "// code preview" in panel


def test_frontend_shadow_dom_host_mount_contract_is_explicit() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)
    combined = "\n".join([main, panel])

    missing = []
    if not _has_any(combined, ("attachShadow", "shadowRoot")):
        missing.append("shadow DOM host mount")
    if "#autoworkbench-root" in main and not _has_any(combined, ("attachShadow", "shadowRoot")):
        missing.append("legacy-only #autoworkbench-root overlay mount")
    if not missing:
        assert _has_any(combined, ("attachShadow", "shadowRoot"))
        assert "#autoworkbench-root" not in main or _has_any(combined, ("attachShadow", "shadowRoot"))
        return

    pytest.xfail("FE-001/FE-010 contract not implemented yet: " + ", ".join(missing))


def test_planned_root_and_core_region_hooks_are_stable() -> None:
    sources = "\n".join(
        [
            _read(FRONTEND_MAIN),
            _read(FRONTEND_PANEL),
            _read(FRONTEND_HEADER),
            _read(FRONTEND_TABS),
        ]
    )

    missing = []
    if not _has_any(sources, PLANNED_ROOT_HOOKS):
        missing.append("aw-root root hook")

    for region, needles in PLANNED_TAB_HOOKS.items():
        if not _has_any(sources, needles):
            missing.append(f"{region} tab/root hook")

    for surface, needles in PLANNED_SURFACE_HOOKS.items():
        if not _has_any(sources, needles):
            missing.append(f"{surface} surface hook")

    if not missing:
        assert _has_any(sources, PLANNED_ROOT_HOOKS)
        for needles in PLANNED_TAB_HOOKS.values():
            assert _has_any(sources, needles)
        for needles in PLANNED_SURFACE_HOOKS.values():
            assert _has_any(sources, needles)
        return

    pytest.xfail("FE-009 planned hook contract not implemented yet: " + ", ".join(missing))


def test_frontend_product_ui_is_expected_to_mount_inside_shadow_dom_root() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)
    combined = "\n".join([main, panel])

    render_into_match = re.search(r"function renderInto\(node, config\) \{(?P<body>.*?)\n\}\n\nfunction mount", main, re.S)
    assert render_into_match is not None, "renderInto() body not found in frontend/src/main.jsx"
    render_into_body = render_into_match.group("body")

    missing = []
    if not _has_any(combined, ("attachShadow", "shadowRoot")):
        missing.append("Shadow DOM host adapter")
    if "createRoot(node)" in render_into_body and not _has_any(
        render_into_body,
        (
            "createRoot(shadow",
            "createRoot(mount",
            "createRoot(root",
            "shadowRoot.getElementById",
            "shadowRoot.querySelector",
            "shadowMount",
        ),
    ):
        missing.append("React mount still targets the generic host node instead of a shadow-root mount container")

    if not missing:
        assert _has_any(combined, ("attachShadow", "shadowRoot"))
        assert not ("createRoot(node)" in render_into_body and not _has_any(render_into_body, ("shadowMount", "shadowRoot.getElementById", "shadowRoot.querySelector")))
        return

    pytest.xfail("FE-001 actual Shadow DOM React mount not implemented yet: " + ", ".join(missing))
