"""
tests/test_frontend_recorded_code_rendering.py

V4 Recorded / Code rendering contract.

After the v4 integration pass:
- Recorded surface lives in `frontend/src/v4/secondary-tabs.jsx::RecordedTab`
- Code surface lives in `frontend/src/v4/secondary-tabs.jsx::CodeTab`
- `frontend/aw-ide-panel.jsx` mounts both based on the active tab and the
  live store props threaded from `frontend/src/main.jsx`.

The Sprint-7-era backend-truth-only invariants still apply.
"""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"
V4_SECONDARY = REPO_ROOT / "frontend/src/v4/secondary-tabs.jsx"
RECORDED_STEP_MODEL = REPO_ROOT / "tests/test_recorded_step_model.py"
CODE_UPDATE_TEST = REPO_ROOT / "tests/test_code_update.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


def test_frontend_recorded_code_surface_is_source_anchored() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)
    secondary = _read(V4_SECONDARY)

    # main.jsx still owns event handling that updates recorded/code state.
    assert "setRecordedSteps" in main
    assert "setCodePreview" in main
    assert "setCodeDiagnostics" in main
    assert "codeDiagnostics" in main
    assert 'case "step_recorded":' in main
    assert 'case "code_update":' in main

    # Panel imports and renders v4 RecordedTab/CodeTab when the right tab is active.
    assert "RecordedTab" in panel
    assert "CodeTab" in panel
    assert "recordedSteps" in panel
    assert "codePreview" in panel
    assert "codeDiagnostics" in panel

    # Secondary tabs file defines both views with stable testids.
    assert 'data-testid="recorded-tab"' in secondary
    assert 'data-testid="code-tab"' in secondary
    assert 'data-testid="code-preview"' in secondary
    assert 'data-testid="code-diagnostics"' in secondary


def test_step_recorded_event_drives_recorded_read_model_and_preserves_backend_ordering() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "step_recorded": {', '        case "code_update": {')

    assert "const nextRecordedStep = buildRecordedStepFromPayload(" in snippet
    assert "setRecordedSteps((current) => mergeRecordedStepList(current, nextRecordedStep));" in snippet
    assert "const nextPlan = updatePlanAfterRecordedStep(planRef.current, {" in snippet
    assert 'setRunState((current) => (current === "completed" ? current : planCompleted ? "completed" : "executing"));' in snippet
    assert 'setInteractionMode(planCompleted ? "completed" : "executing");' in snippet
    assert "acknowledgePendingCommands(type," in snippet
    assert "recorded_step_id: firstNonEmptyText(nextRecordedStep.id, nextRecordedStep.step_id)," in snippet
    assert "setCodePreview(" not in snippet
    assert "setCodeDiagnostics(" not in snippet


def test_code_update_event_drives_code_read_model_without_faking_recorded_truth() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "code_update": {', '        case "replay_started": {')

    assert "const nextCode = extractCodePreview(payload);" in snippet
    assert "setCodePreview(nextCode);" in snippet
    assert "setCodeDiagnostics(" in snippet
    assert "normalizeCodeDiagnostics(" in snippet
    assert "acknowledgePendingCommands(type," in snippet
    assert 'appendTimeline(text || "Code updated", "ok");' in snippet
    assert "setRecordedSteps(" not in snippet
    assert "mergeRecordedStepList(" not in snippet
    assert "updatePlanAfterRecordedStep(" not in snippet
    assert "setRunState(" not in snippet


def test_code_update_diagnostics_are_visibly_rendered_and_remain_display_only() -> None:
    secondary = _read(V4_SECONDARY)

    code_snippet = _snippet_between(
        secondary,
        "export function CodeTab(",
        "export function TraceTab(",
    )

    # Render-only: diagnostics list with typed testids.
    assert 'data-testid="code-diagnostics"' in code_snippet
    assert "code-diagnostic-" in code_snippet
    assert "Awaiting code_update" in code_snippet
    # Display-only: never mutates lifecycle state.
    assert "setRunState(" not in code_snippet
    assert "setInteractionMode(" not in code_snippet
    assert "setRecordedSteps(" not in code_snippet
    assert "setPendingCommands(" not in code_snippet


def test_recorded_step_child_structure_is_preserved_and_not_reinterpreted() -> None:
    main = _read(FRONTEND_MAIN)
    secondary = _read(V4_SECONDARY)

    build_snippet = _snippet_between(
        main,
        "function buildRecordedStepFromPayload(payload, matchedStep, matchIndex, recordedStepId, recordedStepNumber, recordedStepIndex) {",
        "function isPlanStepCompleted(step) {",
    )
    normalize_snippet = _snippet_between(
        main,
        "function normalizeRecordedStep(step, index) {",
        "function sortRecordedSteps(steps) {",
    )
    recorded_snippet = _snippet_between(
        secondary,
        "export function RecordedTab(",
        "export function CodeTab(",
    )

    # main.jsx still preserves backend-shaped child payloads.
    assert 'children: source.children.map((child) => (child && typeof child === "object" ? { ...child } : child)),' in build_snippet
    assert "expected_outcome:" in normalize_snippet

    # v4 RecordedTab renders the child operations the backend supplies.
    assert "asArray(s.children)" in recorded_snippet
    assert "child.operation" in recorded_snippet
    assert "child.generated_line" in recorded_snippet
    assert "child.description" in recorded_snippet

    # Frontend never invents the legacy synthetic fields.
    assert "expected_value" not in main
    assert "exact_text" not in main


def test_backend_contract_inventory_covers_exact_text_visible_and_diagnostics_cases() -> None:
    recorded_step_model = _read(RECORDED_STEP_MODEL)
    code_update = _read(CODE_UPDATE_TEST)

    assert "exact_text" in recorded_step_model
    assert "visible" in recorded_step_model
    assert "expected_value" in recorded_step_model
    assert "diagnostics" in code_update


def test_shadow_dom_runtime_bridge_exposes_recorded_and_code_surfaces() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "function AutoWorkbenchRuntime({ config }) {" in main
    assert "const hostResult = createHost(node);" in main
    assert "const mountNode = shadowRoot ? ensureShadowMount(shadowRoot) : node;" in main
    assert "runtime={{" in main
    assert "recordedSteps," in main
    assert "codePreview," in main
    assert "codeDiagnostics," in main
    assert "state={panelState}" in main
    assert "aw-shadow-host" in main
    assert "aw-shadow-mount" in main

    assert "RecordedTab" in panel
    assert "CodeTab" in panel
