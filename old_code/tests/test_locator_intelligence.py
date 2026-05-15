"""
tests/test_locator_intelligence.py

Tests for Cluster 6: Locator Intelligence + Locator Update.
S6-0601 through S6-0608.
"""
from __future__ import annotations

import pytest
from runtime.locator_intelligence import (
    LocatorCandidate,
    LocatorCandidatePipeline,
    LocatorAmbiguity,
    LocatorAmbiguityType,
    build_locator_candidates,
    scope_and_chain_candidates,
    classify_locator_strength,
    LocatorStrength,
)
from runtime.locator_update import (
    LocatorUpdateRequest,
    LocatorUpdateResult,
    LocatorHistory,
    process_locator_update,
    check_locator_update_precondition,
)


def _make_element(tag: str, attrs: dict) -> dict:
    return {"tag": tag, **attrs}


# ---------------------------------------------------------------------------
# S6-0601: Deterministic locator candidate pipeline
# ---------------------------------------------------------------------------

def test_deterministic_locator_candidates_built():
    elements = [
        _make_element("button", {"data-testid": "submit-btn", "text": "Submit"}),
        _make_element("input", {"name": "username", "type": "text"}),
    ]
    pipeline = build_locator_candidates(elements)
    assert isinstance(pipeline, LocatorCandidatePipeline)
    assert len(pipeline.candidates) >= 1


def test_data_testid_preferred_over_class():
    elements = [
        _make_element("button", {"data-testid": "btn-1", "class": "btn btn-primary", "text": "OK"}),
    ]
    pipeline = build_locator_candidates(elements)
    candidate = pipeline.candidates[0]
    # data-testid should be ranked highest
    assert "data-testid" in candidate.locator or candidate.strength == LocatorStrength.STRONG


def test_weak_dom_candidates_classified():
    elements = [
        _make_element("div", {"class": "clickable", "text": "Click me"}),
    ]
    pipeline = build_locator_candidates(elements)
    assert pipeline.candidates[0].strength in (LocatorStrength.WEAK, LocatorStrength.MEDIUM)


def test_candidates_are_bounded():
    elements = [
        _make_element("button", {"data-testid": f"btn-{i}", "text": f"Btn {i}"})
        for i in range(30)
    ]
    pipeline = build_locator_candidates(elements)
    assert len(pipeline.candidates) <= 20


# ---------------------------------------------------------------------------
# S6-0602: Duplicate locator scoping and chaining
# ---------------------------------------------------------------------------

def test_duplicate_scoping_resolves_ambiguity():
    elements = [
        _make_element("button", {"text": "Submit", "aria_label": "Submit form 1", "section": "login"}),
        _make_element("button", {"text": "Submit", "aria_label": "Submit form 2", "section": "checkout"}),
    ]
    pipeline = build_locator_candidates(elements)
    result = scope_and_chain_candidates(pipeline)
    # Duplicate Submit buttons should be disambiguated by section
    assert result.has_ambiguity is False or result.disambiguation_applied is True


# ---------------------------------------------------------------------------
# S6-0603: Weak DOM semantic classification path
# ---------------------------------------------------------------------------

def test_strong_locator_classification():
    strength = classify_locator_strength({"data-testid": "submit-btn"})
    assert strength == LocatorStrength.STRONG


def test_medium_locator_classification():
    strength = classify_locator_strength({"aria-label": "Submit"})
    assert strength == LocatorStrength.MEDIUM


def test_weak_locator_classification():
    strength = classify_locator_strength({"class": "btn"})
    assert strength == LocatorStrength.WEAK


def test_weak_dom_candidates_are_not_truth():
    """Weak DOM candidates must not be marked as confirmed/final."""
    elements = [_make_element("div", {"class": "click-me"})]
    pipeline = build_locator_candidates(elements)
    for candidate in pipeline.candidates:
        assert not getattr(candidate, "is_final", False)
        assert not getattr(candidate, "confirmed", False)


# ---------------------------------------------------------------------------
# S6-0604: Locator ambiguity candidate choice contract
# ---------------------------------------------------------------------------

def test_ambiguity_is_typed():
    amb = LocatorAmbiguity(
        ambiguity_type=LocatorAmbiguityType.DUPLICATE_TEXT,
        candidates=["btn-1", "btn-2"],
        message="Multiple buttons with same text",
    )
    assert amb.ambiguity_type == LocatorAmbiguityType.DUPLICATE_TEXT
    assert len(amb.candidates) == 2


def test_ambiguity_requires_user_resolution():
    amb = LocatorAmbiguity(
        ambiguity_type=LocatorAmbiguityType.MULTIPLE_MATCHES,
        candidates=["input-1", "input-2", "input-3"],
        message="Multiple matches found",
    )
    # Ambiguity must be user-visible (has message)
    assert amb.message is not None


# ---------------------------------------------------------------------------
# S6-0607: User-requested locator update flow
# ---------------------------------------------------------------------------

def test_locator_update_request_is_processed():
    history = LocatorHistory(step_id="s1", locator_versions=[
        {"locator": "[data-testid=old-btn]", "version": 1}
    ])
    req = LocatorUpdateRequest(
        step_id="s1",
        new_locator="[data-testid=new-btn]",
        reason="element changed after deploy",
        current_page="login",
        required_page="login",
    )
    result = process_locator_update(req, history)
    assert isinstance(result, LocatorUpdateResult)
    assert result.updated is True
    assert len(result.history.locator_versions) == 2


def test_locator_update_preserves_history():
    history = LocatorHistory(step_id="s1", locator_versions=[
        {"locator": "[name=username]", "version": 1}
    ])
    req = LocatorUpdateRequest(
        step_id="s1",
        new_locator="[data-testid=username-input]",
        reason="improved locator",
        current_page="login",
        required_page="login",
    )
    result = process_locator_update(req, history)
    # Old locator must still be in history
    old_locators = [v["locator"] for v in result.history.locator_versions]
    assert "[name=username]" in old_locators


# ---------------------------------------------------------------------------
# S6-0608: Wrong-page locator update precondition flow
# ---------------------------------------------------------------------------

def test_wrong_page_blocks_locator_update():
    req = LocatorUpdateRequest(
        step_id="s1",
        new_locator="[data-testid=btn]",
        reason="update",
        current_page="dashboard",
        required_page="login",
    )
    check = check_locator_update_precondition(req)
    assert check.blocked is True
    assert check.reason is not None


def test_correct_page_allows_locator_update():
    req = LocatorUpdateRequest(
        step_id="s1",
        new_locator="[data-testid=btn]",
        reason="update",
        current_page="login",
        required_page="login",
    )
    check = check_locator_update_precondition(req)
    assert check.blocked is False
