"""
tests/test_frontend_accessibility_focus.py

V4 accessibility / focus contract.

After the Sprint 7 integration pass, the live panel lives in
`frontend/aw-ide-panel.jsx` and the cards live under `frontend/src/v4/`.
This test verifies that the v4 surface keeps Shadow DOM hooks intact,
exposes typed testids, and never mutates lifecycle state from buttons.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN = REPO_ROOT / "frontend/src/main.jsx"
PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"
V4_LLM = REPO_ROOT / "frontend/src/v4/llm-cards.jsx"
V4_CHROME = REPO_ROOT / "frontend/src/v4/chrome.jsx"


def _r(p):
    return p.read_text(encoding="utf-8")


def test_shadow_dom_root_and_primary_surface_hooks_stay_stable() -> None:
    main = _r(MAIN)
    panel = _r(PANEL)
    chrome = _r(V4_CHROME)
    llm = _r(V4_LLM)

    assert "function ensureShadowHost(host) {" in main
    assert "function ensureShadowMount(shadowRoot) {" in main
    assert 'marker.setAttribute("data-testid", "aw-shadow-host");' in main
    assert 'mount.setAttribute("data-testid", "aw-shadow-mount");' in main

    # New v4 panel exposes the canonical stage + panel testids
    assert 'data-testid="aw-stage"' in panel
    assert 'data-testid="aw-panel"' in panel
    assert 'data-testid="aw-panel-body"' in panel

    # Tab strip + per-tab testids live in v4/chrome.jsx
    assert 'data-testid="aw-tabs"' in chrome
    for tab in ("llm", "steps", "rec", "code", "trace"):
        assert f'data-testid={{`aw-tab-${{t.id}}`}}' in chrome or f'aw-tab-{tab}' in chrome

    # Cards expose typed testids
    for card_id in (
        "card-clarification",
        "card-plan-ready",
        "card-recovery",
        "card-locator-ambiguity",
        "card-permission",
        "card-completed",
    ):
        assert f'data-testid="{card_id}"' in llm


def test_critical_actions_have_accessible_names_and_button_semantics() -> None:
    llm = _r(V4_LLM)

    # All primary buttons are real <button type="button" /> with testids
    for testid in (
        "clarification-submit",
        "recommendation-accept",
        "plan-confirm",
        "permission-allow-once",
        "permission-deny",
        "locator-confirm",
        "recovery-retry",
        "completed-replay-all",
        "aw-composer-send",
    ):
        assert f'data-testid="{testid}"' in llm
    # Buttons declare a type attribute (no implicit form submit semantics)
    assert llm.count('type="button"') >= 10


def test_clarification_and_recovery_cards_expose_focus_targets() -> None:
    llm = _r(V4_LLM)

    # Clarification card: typed answer dispatch, no local lifecycle mutation
    assert 'data-testid="card-clarification"' in llm
    assert 'data-testid="clarification-submit"' in llm
    assert "option_selected" in llm
    assert "setRunState(" not in llm
    assert "setInteractionMode(" not in llm

    # Recovery card: typed retry/stop, evidence read-only
    assert 'data-testid="card-recovery"' in llm
    assert "retry_recovery" in llm
    assert "stop_run" in llm
    assert "setResolved" not in llm
    assert "setRecoveryResolved" not in llm


def test_focus_hooks_remain_backend_driven_and_shadow_dom_compatible() -> None:
    main = _r(MAIN)
    panel = _r(PANEL)

    # main.jsx still wires Shadow DOM + storeState into runtime prop
    assert "const panelState = toPanelState(transport.runState || normalized.panelState);" in main
    assert "state={panelState}" in main
    assert "runtime={{" in main
    assert "ensureShadowHost" in main
    assert "ensureShadowMount" in main
    assert "attachShadow" in main
    assert "shadowRoot" in main

    # Panel reads conditional content from runtime / storeState only
    assert "storePendingClarification" in panel
    assert "storePendingRecovery" in panel
    assert "storePendingPermission" in panel
    assert "interaction_mode" not in panel or "storeInteractionMode" in panel
