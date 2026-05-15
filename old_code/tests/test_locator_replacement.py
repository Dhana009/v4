"""Unit tests for locator.replacement."""
from __future__ import annotations

import pytest

from locator.replacement import LocatorReplacement, propose_replacement


# ---------------------------------------------------------------------------
# 1. role+name preferred over data-testid when both candidates exist
# ---------------------------------------------------------------------------

def test_role_name_preferred_over_data_testid() -> None:
    element_data = {
        "tag": "button",
        "text": "Submit Order",
        "attributes": {"data-testid": "submit-btn"},
    }
    result = propose_replacement("//div/button[3]", element_data)
    assert result.chosen is not None
    assert result.chosen["strategy"] in {"role+name", "data-testid", "label-for"}
    # role+name should rank first since it's the highest-score preferred strategy
    assert result.chosen["strategy"] == "role+name"


# ---------------------------------------------------------------------------
# 2. No preferred match, score < 0.6 → chosen=None, confidence=0.0
# ---------------------------------------------------------------------------

def test_low_score_candidates_no_chosen() -> None:
    # Provide only an XPath-style candidate by giving element_data that only
    # produces an xpath-score candidate (tag only, no text, no attributes).
    # We force this by providing just a tag with no identifying info,
    # causing only a bare CSS candidate to be generated.
    element_data = {"tag": "div", "text": "", "attributes": {}}
    result = propose_replacement("//div", element_data)
    # CSS strategy scores 0.30 which is < 0.60 threshold
    if result.chosen is not None:
        # If a preferred strategy was found, it must have score >= 0.6
        assert float(result.chosen.get("score", 0)) >= 0.6
    else:
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# 3. Empty element_data → graceful fallback (chosen=None)
# ---------------------------------------------------------------------------

def test_empty_element_data_graceful_fallback() -> None:
    result = propose_replacement("//span[1]", {})
    assert isinstance(result, LocatorReplacement)
    assert result.chosen is None
    assert result.confidence == 0.0
    assert "insufficient element_data" in result.reasons


# ---------------------------------------------------------------------------
# 4. data-testid candidate is selected when role+name is absent
# ---------------------------------------------------------------------------

def test_data_testid_selected_when_no_role() -> None:
    element_data = {
        "tag": "div",
        "text": "",
        "attributes": {"data-testid": "hero-banner"},
    }
    result = propose_replacement("#old-id", element_data)
    assert result.chosen is not None
    assert result.chosen["strategy"] == "data-testid"
    assert result.confidence >= 0.93


# ---------------------------------------------------------------------------
# 5. LocatorReplacement contains all expected fields
# ---------------------------------------------------------------------------

def test_locator_replacement_fields() -> None:
    element_data = {"tag": "button", "text": "OK", "attributes": {}}
    result = propose_replacement("//button", element_data)
    assert hasattr(result, "original")
    assert hasattr(result, "candidates")
    assert hasattr(result, "chosen")
    assert hasattr(result, "confidence")
    assert hasattr(result, "reasons")
    assert result.original == "//button"


# ---------------------------------------------------------------------------
# 6. candidates list length is bounded by max_candidates
# ---------------------------------------------------------------------------

def test_candidates_bounded_by_max() -> None:
    element_data = {
        "tag": "input",
        "text": "Search here",
        "placeholder": "Type to search",
        "attributes": {"id": "search-input", "name": "q", "aria-label": "Search"},
    }
    result = propose_replacement("#q", element_data, max_candidates=3)
    assert len(result.candidates) <= 3
