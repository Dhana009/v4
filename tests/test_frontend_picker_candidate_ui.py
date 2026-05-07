from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


def test_picker_surface_is_shadow_dom_ready_and_hooked() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "normalizeElementCandidate" in main
    assert "selectElementInfoCandidate" in main
    assert "selected_candidate_index" in main
    assert "element_picked" in main
    assert "candidateList" in panel
    assert 'data-testid="picker-candidates"' in panel
    assert 'aria-label="Locator candidates"' in panel
    assert 'data-testid="picker-candidate-select"' in panel
    assert 'aria-label="Choose locator candidate"' in panel


def test_picker_candidate_metadata_is_rendered_as_display_only_details() -> None:
    panel = _read(FRONTEND_PANEL)

    for token in (
        "summarizePickerCandidateMetadata",
        "summarizePickerCandidateWarning",
        "candidate_id",
        "locator",
        "strategy",
        "source",
        "confidence",
        "score",
        "count",
        "visibility",
        "hidden",
        "scope",
        "container",
        "risk_flags",
        "risk",
        "evidence_ref",
    ):
        assert token in panel

    assert "Multiple candidates require backend validation" in panel
    assert "Hidden candidate requires validation." in panel
    assert "Low confidence candidate" in panel
    assert "Evidence ref missing." in panel
    assert "Candidate type missing." in panel


def test_picker_selection_remains_proposal_only_and_does_not_mutate_lifecycle_truth() -> None:
    main = _read(FRONTEND_MAIN)

    update_snippet = _snippet_between(
        main,
        "  const updatePendingStepElementTarget = useCallback((stepId, selectedCandidateIndex) => {",
        "  const removePendingStep = useCallback(",
    )
    picked_snippet = _snippet_between(
        main,
        '        case "element_picked": {',
        "        default:",
    )

    assert "selectElementInfoCandidate(step.element_info ?? step.elementInfo ?? null, selectedCandidateIndex);" in update_snippet
    assert "setRunState(" not in update_snippet
    assert "setInteractionMode(" not in update_snippet
    assert "setRecordedSteps(" not in update_snippet
    assert "setCodePreview(" not in update_snippet
    assert "setPendingCommands(" not in update_snippet

    assert "selectElementInfoCandidate(elementInfo, elementInfo?.selected_candidate_index);" in picked_snippet
    assert "setRunState(" not in picked_snippet
    assert "setInteractionMode(" not in picked_snippet
    assert "setRecordedSteps(" not in picked_snippet
    assert "setCodePreview(" not in picked_snippet
    assert "setPendingCommands(" not in picked_snippet


def test_picker_surface_does_not_call_backend_locator_implementation_directly() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    for forbidden in ("locator_validate(", "locator_find(", "dom_extract(", "action_click("):
        assert forbidden not in main
        assert forbidden not in panel

