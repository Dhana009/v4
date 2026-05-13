"""
tests/test_frontend_picker_candidate_ui.py

V4 picker/locator-candidate contract.

The legacy monolith embedded picker candidate rendering in
`aw-ide-panel.jsx`; the v4 panel delegates that responsibility to
`frontend/src/v4/llm-cards.jsx::CardLocatorAmbiguity`. This test
asserts the new surface is backend-driven and never activates a
locator locally.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"
V4_LLM = REPO_ROOT / "frontend/src/v4/llm-cards.jsx"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_picker_surface_is_shadow_dom_ready_and_hooked() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)
    llm = _read(V4_LLM)

    assert "normalizeElementCandidate" in main
    assert "selectElementInfoCandidate" in main
    assert "selected_candidate_index" in main
    assert "element_picked" in main

    assert "buildAmbiguity" in panel
    assert "storePendingRecovery" in panel

    assert 'data-testid="card-locator-ambiguity"' in llm
    assert 'data-testid="locator-candidates"' in llm
    assert "choose_locator_candidate" in llm
    assert "setActiveLocator" not in llm


def test_picker_candidate_metadata_is_rendered_as_display_only_details() -> None:
    llm = _read(V4_LLM)

    for token in ("scope", "locator", "risk", "confidence", "candidate_id"):
        assert token in llm, f"v4 locator card missing display token: {token}"
    assert "setRecordedSteps" not in llm
    assert "setCodePreview" not in llm
    assert "setActiveLocator" not in llm


def test_picker_selection_remains_proposal_only_and_does_not_mutate_lifecycle_truth() -> None:
    main = _read(FRONTEND_MAIN)

    assert "selectElementInfoCandidate(step.element_info ?? step.elementInfo ?? null, selectedCandidateIndex);" in main
    assert "selectElementInfoCandidate(elementInfo, elementInfo?.selected_candidate_index);" in main

    picked_start = main.find('        case "element_picked": {')
    assert picked_start != -1
    picked_end = main.find("        default:", picked_start)
    snippet = main[picked_start:picked_end] if picked_end != -1 else main[picked_start:picked_start + 4000]
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet


def test_picker_surface_does_not_call_backend_locator_implementation_directly() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)
    llm = _read(V4_LLM)

    for forbidden in ("locator_validate(", "locator_find(", "dom_extract(", "action_click("):
        assert forbidden not in main
        assert forbidden not in panel
        assert forbidden not in llm
