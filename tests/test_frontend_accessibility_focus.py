from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"
FRONTEND_HEADER = REPO_ROOT / "frontend/aw-header.jsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


def test_shadow_dom_root_and_primary_surface_hooks_stay_stable() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "function ensureShadowHost(host) {" in main
    assert "function ensureShadowMount(shadowRoot) {" in main
    assert 'marker.setAttribute("data-testid", "aw-shadow-host");' in main
    assert 'mount.setAttribute("data-testid", "aw-shadow-mount");' in main
    assert 'id="aw-root"' in panel
    assert 'data-testid="aw-root"' in panel
    assert 'aria-label="AutoWorkbench"' in panel
    assert 'testId="llm"' in panel
    assert 'testId="steps"' in panel
    assert 'testId="recorded"' in panel
    assert 'testId="code"' in panel
    assert 'data-testid="trace"' in panel
    assert 'ariaLabel="LLM"' in panel
    assert 'ariaLabel="Steps"' in panel
    assert 'ariaLabel="Recorded"' in panel
    assert 'ariaLabel="Code"' in panel
    assert 'aria-label="Trace"' in panel
    assert 'testId="plan-review"' in panel
    assert 'testId="clarification"' in panel
    assert 'testId="recovery"' in panel


def test_critical_actions_have_accessible_names_and_button_semantics() -> None:
    panel = _read(FRONTEND_PANEL)

    assert "Confirm Plan" in panel
    assert "Send Correction" in panel
    assert "Send Answer" in panel
    assert "Send Recovery Instruction" in panel
    assert 'type="button"' in panel
    assert 'placeholder="Type correction…"' in panel
    assert 'placeholder="Answer clarification…"' in panel
    assert 'placeholder="Tell the agent how to recover..."' in panel


def test_clarification_and_recovery_cards_expose_focus_targets() -> None:
    panel = _read(FRONTEND_PANEL)
    clarification = _snippet_between(panel, "function IDEClarificationCard({", "function IDERecovery({")
    recovery = _snippet_between(panel, "function IDERecovery({", "function IDETimeline({")

    assert "const answerRef = React.useRef(null);" in clarification
    assert "answerRef.current?.focus?.();" in clarification
    assert "ref={answerRef}" in clarification
    assert 'data-testid="clarification-answer"' in clarification
    assert 'aria-label="Clarification answer"' in clarification
    assert "setRunState(" not in clarification
    assert "setInteractionMode(" not in clarification

    assert "const recoveryRef = React.useRef(null);" in recovery
    assert "recoveryRef.current?.focus?.();" in recovery
    assert "ref={recoveryRef}" in recovery
    assert 'data-testid="recovery-instruction"' in recovery
    assert 'aria-label="Recovery instruction"' in recovery
    assert "setRunState(" not in recovery
    assert "setInteractionMode(" not in recovery


def test_focus_hooks_remain_backend_driven_and_shadow_dom_compatible() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "const panelState = toPanelState(transport.runState || normalized.panelState);" in main
    assert 'state={panelState}' in main
    assert "runtime={{" in main
    assert "showClarification" in panel
    assert "showRecovery" in panel
    assert "interactionMode === \"clarification\"" in panel
    assert "interactionMode === \"recovery\"" in panel
    assert "ensureShadowHost" in main
    assert "ensureShadowMount" in main
    assert "attachShadow" in main
    assert "shadowRoot" in main
